"""
定时扫盘任务 — 仅轮询 Watchlist, 带并发控制

核心风控:
1. 绝不全市场扫盘 — 仅读取 WatchlistTicker.is_active=True
2. asyncio.Semaphore(3) — 最多 3 个并发 API 请求, 防 429 限流
3. 每次扫盘异常通过 NotificationService 报警
4. 扫盘结果交由策略引擎决策, 可执行信号推送到 OMS
"""

import asyncio
import logging
from datetime import datetime, timezone

from app.adapters.yahoo import YahooFinanceAdapter
from app.services.notifier import get_notifier
from app.services.strategy_entry import evaluate_market_entry
from app.schemas.strategy import StrategyMarketContext

logger = logging.getLogger("alphatheta.scanner")

# ── 并发控制: 限制同时对券商 API 的请求数 ──
# Tradier Sandbox: 60 req/min, Tradier Live: 120 req/min
# 设为 3 并发 → 即使 20 个标的, 也只有 3 个同时请求
_API_SEMAPHORE = asyncio.Semaphore(3)

_yahoo = YahooFinanceAdapter()


async def run_market_scanner(watchlist: list[dict] | None = None) -> list[dict]:
    """
    市场扫盘主任务 — 由 APScheduler 定时调用

    流程:
    1. 从数据库读取 is_active=True 的 Watchlist 标的
    2. 逐个获取行情 (受 Semaphore 并发限制)
    3. 交由策略引擎 evaluate_market_entry() 决策
    4. 可执行信号推送到对账结果列表
    """
    notifier = get_notifier()

    # ── Step 1: 获取关注池 ──
    if watchlist is None:
        watchlist = _get_active_watchlist()

    if not watchlist:
        logger.info("[Scanner] Watchlist is empty — nothing to scan")
        return []

    logger.info(f"[Scanner] Starting scan for {len(watchlist)} tickers")
    start_time = datetime.now(timezone.utc)

    # ── Step 2: 并发受限的扫盘 ──
    # asyncio.Semaphore(3) 保证最多 3 个同时请求
    # 即使 Watchlist 有 20+ 标的, 也不会触发券商 API 的 429 限流
    tasks = [
        _scan_single_ticker(item["ticker"], item.get("supports_options", True))
        for item in watchlist
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # ── Step 3: 处理结果 ──
    scan_results = []
    errors = []

    for item, result in zip(watchlist, results):
        ticker = item["ticker"]
        if isinstance(result, Exception):
            errors.append({"ticker": ticker, "error": str(result)})
            logger.error(f"[Scanner] {ticker} failed: {result}")
        elif result is not None:
            scan_results.append(result)

    # ── Step 4: 异常汇总报警 ──
    elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
    logger.info(
        f"[Scanner] Scan complete in {elapsed:.1f}s — "
        f"{len(scan_results)} results, {len(errors)} errors"
    )

    if errors:
        error_summary = "\n".join(f"• {e['ticker']}: {e['error']}" for e in errors)
        await notifier.send_critical_alert(
            title="扫盘部分失败",
            message=f"{len(errors)} 个标的获取行情失败:\n{error_summary}",
            severity="WARNING",
        )

    return scan_results


async def _scan_single_ticker(ticker: str, supports_options: bool = True) -> dict | None:
    """
    扫描单个标的 — 受 Semaphore 并发控制

    asyncio.Semaphore(3) 保证:
    - 最多 3 个 API 请求同时在飞
    - Semaphore 内部等待不消耗 CPU (event loop 友好)
    - 超时或失败的请求释放 permit, 不会阻塞其他标的
    """
    async with _API_SEMAPHORE:
        try:
            # ── 获取行情 ──
            quote = await _yahoo.get_quote(ticker)
            vix = await _yahoo.get_vix()
            indicators = await _yahoo.get_indicators(ticker)

            rsi_14 = indicators.get("rsi_14", 50.0)

            # ── 组装策略引擎输入 ──
            ctx = StrategyMarketContext(
                ticker=ticker,
                underlying_price=quote.last,
                vix=vix,
                rsi_14=rsi_14,
                has_position=False,  # TODO: 从持仓服务查询
                available_cash=45000.0,  # TODO: 从账户服务读取
            )

            # ── 策略引擎 AI 决策 ──
            decision = evaluate_market_entry(ctx)

            return {
                "ticker": ticker,
                "price": quote.last,
                "vix": vix,
                "rsi_14": rsi_14,
                "decision": {
                    "action_type": decision.action_type.value
                        if hasattr(decision.action_type, "value")
                        else str(decision.action_type),
                    "scene_label": decision.scene_label,
                    "confidence": decision.confidence,
                    "reasoning": decision.reasoning,
                },
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        except Exception as e:
            logger.error(f"[Scanner] Error scanning {ticker}: {e}")
            raise


def _get_active_watchlist() -> list[dict]:
    """
    获取活跃 Watchlist — 内存 fallback

    生产环境替换为:
        async with get_session() as db:
            result = await db.execute(
                select(WatchlistTicker).where(WatchlistTicker.is_active == True)
            )
            return [{"ticker": r.ticker, "supports_options": r.supports_options}
                    for r in result.scalars()]
    """
    return [
        {"ticker": "SPY", "supports_options": True},
        {"ticker": "QQQ", "supports_options": True},
        {"ticker": "AAPL", "supports_options": True},
        {"ticker": "MSFT", "supports_options": True},
    ]
