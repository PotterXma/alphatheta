"""
AlphaTheta Scanner Daemon — 两段式 LEAPS 黄金坑扫描引擎

7×24 守护进程:
  - 交易时段每 15 分钟扫描 Watchlist
  - 阶段 1: 轻量初筛 (RSI < 35 + IVR < 30)
  - 阶段 2: 重装深潜 (LEAPS 到期日 + 流动性校验 + Deep ITM Call)
  - 24h 冷却池去重
  - 三通道推送 (WebSocket + Email + 微信)
"""

import asyncio
import logging
import os
import random
import time as time_mod
from concurrent.futures import ThreadPoolExecutor

from app.services.market_calendar import (
    isUSMarketOpen,
    get_sleep_seconds,
    is_heartbeat_time,
    now_et,
)
from app.services.notification import NotificationManager, ScannerSignal

logger = logging.getLogger("alphatheta.scanner.daemon")

# ── 配置 ──────────────────────────────────────────────────────────

SCAN_INTERVAL = int(os.getenv("SCAN_INTERVAL_SECONDS", "900"))  # 15 min
COOLDOWN_HOURS = 24
COOLDOWN_SECONDS = COOLDOWN_HOURS * 3600
RSI_THRESHOLD = 35
IVR_THRESHOLD = 30
API_DELAY_MIN = 1.0
API_DELAY_MAX = 3.0
MAX_RETRIES = 3


# ── 冷却池 ────────────────────────────────────────────────────────

class AlertCooldown:
    """
    24h 信号冷却池 — 同一标的同方向信号去重

    内存存储 (进程重启清零, 可接受 — 只是通知去重)
    """

    def __init__(self, ttl: int = COOLDOWN_SECONDS):
        self._cache: dict[str, float] = {}
        self._ttl = ttl

    def _key(self, ticker: str, direction: str) -> str:
        return f"{ticker}:{direction}"

    def is_cooled(self, ticker: str, direction: str) -> bool:
        """检查是否在冷却期内"""
        key = self._key(ticker, direction)
        ts = self._cache.get(key)
        if ts is None:
            return False
        elapsed = time_mod.time() - ts
        if elapsed >= self._ttl:
            del self._cache[key]
            return False
        remaining = self._ttl - elapsed
        logger.info(
            f"🧊 冷却期内 [{ticker} {direction}]: "
            f"剩余 {remaining/3600:.1f}h, 已拦截"
        )
        return True

    def mark(self, ticker: str, direction: str):
        """标记推送时间"""
        self._cache[self._key(ticker, direction)] = time_mod.time()

    def size(self) -> int:
        return len(self._cache)


# ── yfinance 同步适配 (带重试) ──────────────────────────────────

def _fetch_ticker_data(ticker: str) -> dict:
    """
    同步获取标的基本数据 (在线程池中运行)

    返回: {price, rsi, ivr, expirations}
    """
    import yfinance as yf

    t = yf.Ticker(ticker)
    info = t.fast_info
    price = getattr(info, "last_price", None) or getattr(info, "previous_close", 0)

    # 简化 RSI 计算 (14 日)
    hist = t.history(period="1mo", interval="1d")
    rsi = 50.0  # fallback
    if len(hist) >= 14:
        delta = hist["Close"].diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain.iloc[-1] / loss.iloc[-1] if loss.iloc[-1] > 0 else 100
        rsi = 100 - (100 / (1 + rs))

    # IV Rank 简化 (用 VIX 近似, 实际应查 IV 历史分位)
    ivr = 25.0  # 默认中等
    try:
        vix_t = yf.Ticker("^VIX")
        vix_price = getattr(vix_t.fast_info, "last_price", 20)
        # 粗略映射: VIX 12=低 → IVR 10, VIX 20=中 → IVR 30, VIX 35=高 → IVR 70
        ivr = max(0, min(100, (vix_price - 10) * 3.0))
    except Exception:
        pass

    # 到期日列表
    expirations = list(t.options) if t.options else []

    return {
        "ticker": ticker,
        "price": price,
        "rsi": round(rsi, 2),
        "ivr": round(ivr, 2),
        "expirations": expirations,
    }


def _fetch_option_chain(ticker: str, date: str) -> dict:
    """同步获取期权链 (在线程池中运行)"""
    import yfinance as yf

    t = yf.Ticker(ticker)
    info = t.fast_info
    spot = getattr(info, "last_price", None) or getattr(info, "previous_close", 0)

    chain = t.option_chain(date)
    calls = []
    for _, row in chain.calls.iterrows():
        calls.append({
            "strike": float(row["strike"]),
            "bid": float(row.get("bid", 0)),
            "ask": float(row.get("ask", 0)),
        })

    return {"calls": calls, "spot": spot}


async def fetch_with_retry(fn, *args, max_retries: int = MAX_RETRIES) -> dict:
    """
    带指数退避重试的异步线程池调用

    重试: 1s → 2s → 4s
    """
    loop = asyncio.get_running_loop()

    for attempt in range(max_retries):
        try:
            with ThreadPoolExecutor(max_workers=1) as pool:
                future = loop.run_in_executor(pool, fn, *args)
                result = await asyncio.wait_for(future, timeout=15)
                return result
        except (asyncio.TimeoutError, TimeoutError) as e:
            wait = 2 ** attempt
            logger.warning(
                f"⏱️ 重试 {attempt + 1}/{max_retries} "
                f"(等待 {wait}s): {args[0] if args else fn.__name__} — {e}"
            )
            await asyncio.sleep(wait)
        except Exception as e:
            wait = 2 ** attempt
            logger.warning(
                f"⚠️ 重试 {attempt + 1}/{max_retries} "
                f"(等待 {wait}s): {args[0] if args else fn.__name__} — {e}"
            )
            await asyncio.sleep(wait)

    raise RuntimeError(f"API 请求失败 (已重试 {max_retries} 次)")


# ── LEAPS 工具函数 (从前端 JS 移植) ────────────────────────────

LEAPS_MIN_DTE = 270
LEAPS_MAX_DTE = 540
LEAPS_MAX_SPREAD_ABS = 3.00
LEAPS_MAX_SPREAD_PCT = 0.15


def find_leaps_expiration(expirations: list[str]) -> dict | None:
    """寻找 270-540d 最优到期日 (甜点 365d)"""
    from datetime import datetime, date

    today = date.today()
    best = None
    best_dte = 0
    best_dist = float("inf")

    for exp_str in expirations:
        exp_date = datetime.strptime(exp_str, "%Y-%m-%d").date()
        dte = (exp_date - today).days
        if LEAPS_MIN_DTE <= dte <= LEAPS_MAX_DTE:
            dist = abs(dte - 365)
            if dist < best_dist:
                best_dist = dist
                best = exp_str
                best_dte = dte

    if not best:
        return None

    return {"date": best, "dte": best_dte}


def validate_leaps_liquidity(bid: float, ask: float) -> bool:
    """验证远期流动性 (绝对 $3 + 相对 15%)"""
    if bid <= 0 or ask <= 0:
        return False
    spread = ask - bid
    if spread > LEAPS_MAX_SPREAD_ABS:
        return False
    if (spread / ask) > LEAPS_MAX_SPREAD_PCT:
        return False
    return True


def find_deep_itm_call(calls: list[dict], spot: float) -> dict | None:
    """寻找 Deep ITM Call (Δ≈0.80, strike ≈ spot × 0.80)"""
    target = spot * 0.80
    best = None
    best_dist = float("inf")

    for c in calls:
        dist = abs(c["strike"] - target)
        if dist < best_dist:
            best_dist = dist
            best = c

    if best and validate_leaps_liquidity(best.get("bid", 0), best.get("ask", 0)):
        return best

    return None


# ── 扫描主循环 ────────────────────────────────────────────────────

async def get_watchlist() -> list[str]:
    """从 DB 获取活跃 Watchlist"""
    try:
        from app.db.session import get_async_session
        from app.models.watchlist import WatchlistTicker
        from sqlalchemy import select

        async with get_async_session() as session:
            result = await session.execute(
                select(WatchlistTicker.ticker)
                .where(WatchlistTicker.is_active == True)
                .order_by(WatchlistTicker.ticker)
            )
            tickers = [r[0] for r in result.all()]
            return tickers if tickers else ["SPY", "QQQ", "AAPL", "MSFT", "NVDA", "AMZN"]
    except Exception as e:
        logger.warning(f"Watchlist 查询失败, 使用默认池: {e}")
        return ["SPY", "QQQ", "AAPL", "MSFT", "NVDA", "AMZN"]


async def check_redis_health() -> bool:
    """检查 Redis 连通性"""
    try:
        from app.dependencies import get_redis
        redis = await get_redis()
        await redis.ping()
        return True
    except Exception:
        return False


async def scanner_loop():
    """
    两段式 LEAPS 扫描主循环

    阶段 1: 轻量初筛 (RSI/IVR)
    阶段 2: 重装深潜 (LEAPS 到期 + 流动性 + Deep ITM)
    """
    notifier = NotificationManager()
    cooldown = AlertCooldown()
    heartbeat_sent_today = False

    logger.info("🚀 Scanner Daemon 启动")

    while True:
        try:
            et_now = now_et()

            # ── 每日心跳 (09:20 ET) ─────────────────────────────
            if is_heartbeat_time() and not heartbeat_sent_today:
                watchlist = await get_watchlist()
                redis_ok = await check_redis_health()
                await notifier.send_heartbeat(len(watchlist), redis_ok)

                # Redis heartbeat (for health monitoring)
                try:
                    from app.dependencies import get_redis
                    from app.services.signal_publisher import publish_heartbeat
                    redis = await get_redis()
                    await publish_heartbeat(redis, len(watchlist), redis_ok)
                except Exception as e:
                    logger.warning(f"Redis heartbeat 写入失败: {e}")

                heartbeat_sent_today = True

            # 日期切换时重置心跳标记
            if et_now.hour >= 17:
                heartbeat_sent_today = False

            # ── 闭市检测 → 休眠 ─────────────────────────────────
            if not isUSMarketOpen():
                sleep_secs = get_sleep_seconds(SCAN_INTERVAL)
                await asyncio.sleep(sleep_secs)
                continue

            # ── 获取 Watchlist ────────────────────────────────────
            watchlist = await get_watchlist()
            logger.info(
                f"📊 扫描开始 | {et_now.strftime('%H:%M ET')} | "
                f"{len(watchlist)} 只标的 | 冷却池: {cooldown.size()}"
            )

            signals_found = 0

            for ticker in watchlist:
                try:
                    # ── 阶段 1: 轻量初筛 ─────────────────────────
                    delay = random.uniform(API_DELAY_MIN, API_DELAY_MAX)
                    await asyncio.sleep(delay)

                    data = await fetch_with_retry(_fetch_ticker_data, ticker)
                    rsi = data["rsi"]
                    ivr = data["ivr"]
                    price = data["price"]

                    if rsi >= RSI_THRESHOLD or ivr >= IVR_THRESHOLD:
                        logger.debug(
                            f"  {ticker}: RSI={rsi:.1f} IVR={ivr:.1f} — 初筛未通过, skip"
                        )
                        continue

                    logger.info(
                        f"  🔍 {ticker}: RSI={rsi:.1f} IVR={ivr:.1f} — 初筛通过! 进入深潜"
                    )

                    # ── 冷却校验 ─────────────────────────────────
                    direction = "bullish"  # LEAPS 黄金坑 = 低 RSI + 低 IVR → bullish
                    if cooldown.is_cooled(ticker, direction):
                        continue

                    # ── 阶段 2: 重装深潜 ─────────────────────────
                    exps = data.get("expirations", [])
                    leaps = find_leaps_expiration(exps)
                    if not leaps:
                        max_dte = 0
                        if exps:
                            from datetime import datetime, date
                            today = date.today()
                            max_dte = max(
                                (datetime.strptime(e, "%Y-%m-%d").date() - today).days
                                for e in exps
                            )
                        logger.info(
                            f"  {ticker}: 无 LEAPS 到期日 (最远: {max_dte}d), skip"
                        )
                        continue

                    # 获取远期期权链
                    await asyncio.sleep(random.uniform(API_DELAY_MIN, API_DELAY_MAX))
                    chain = await fetch_with_retry(
                        _fetch_option_chain, ticker, leaps["date"]
                    )

                    calls = chain.get("calls", [])
                    spot = chain.get("spot", price)
                    deep_call = find_deep_itm_call(calls, spot)

                    if not deep_call:
                        logger.info(
                            f"  {ticker}: Deep ITM Call 流动性不足, skip"
                        )
                        continue

                    # ── 🎯 信号触发! ─────────────────────────────
                    signal = ScannerSignal(
                        ticker=ticker,
                        price=price,
                        rsi=rsi,
                        ivr=ivr,
                        direction=direction,
                        leaps_expiration=leaps["date"],
                        leaps_dte=leaps["dte"],
                        call_strike=deep_call["strike"],
                        call_ask=deep_call["ask"],
                        strategy="leaps_deep_itm_call",
                    )

                    logger.info(
                        f"  🎯 信号触发! {ticker} | ${price:.2f} | "
                        f"RSI={rsi:.1f} | Call ${deep_call['strike']} @ ${deep_call['ask']:.2f}"
                    )

                    # 推送 + 写入冷却池
                    await notifier.broadcast(signal)

                    # Redis pub/sub 广播 (for WebSocket feed)
                    try:
                        from app.dependencies import get_redis
                        from app.services.signal_publisher import publish_signal
                        redis = await get_redis()
                        await publish_signal(redis, {
                            "ticker": ticker, "price": price,
                            "rsi": rsi, "ivr": ivr,
                            "direction": direction,
                            "strategy": "leaps_deep_itm_call",
                            "leaps_expiration": leaps["date"],
                            "leaps_dte": leaps["dte"],
                            "call_strike": deep_call["strike"],
                            "call_ask": deep_call["ask"],
                        })
                    except Exception as e:
                        logger.warning(f"Redis 信号广播失败 (已降级): {e}")

                    cooldown.mark(ticker, direction)
                    signals_found += 1

                except Exception as e:
                    # 单标的异常隔离 — 绝不能崩掉整个循环
                    logger.error(f"  ❌ {ticker} 扫描异常 (已隔离): {e}")
                    continue

            logger.info(
                f"📊 扫描完成 | 触发信号: {signals_found} | "
                f"下次扫描: {SCAN_INTERVAL // 60} 分钟后"
            )

        except Exception as e:
            # 最外层保护 — 循环级异常也不能终止进程
            logger.critical(f"🔥 扫描循环异常 (进程存活): {e}", exc_info=True)

        # ── 休眠到下一轮 ─────────────────────────────────────────
        await asyncio.sleep(SCAN_INTERVAL)


# ── 入口 ──────────────────────────────────────────────────────────

async def main():
    """Scanner Daemon 入口"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    logger.info("═" * 60)
    logger.info("  AlphaTheta Scanner Daemon v1.0")
    logger.info(f"  扫描间隔: {SCAN_INTERVAL}s | 冷却时长: {COOLDOWN_HOURS}h")
    logger.info(f"  初筛: RSI < {RSI_THRESHOLD} + IVR < {IVR_THRESHOLD}")
    logger.info("═" * 60)

    await scanner_loop()
