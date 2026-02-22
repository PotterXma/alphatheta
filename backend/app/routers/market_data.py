"""
Market Data API — 期权链查询 + 策略模板

Strategy Studio 专用数据端点:
  GET /option_chain_mini?ticker=&date=  → 迷你期权链 (现价 ±5 档)
  GET /expirations?ticker=              → 可用到期日列表
  GET /templates                        → 策略组合模板 JSON
"""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query

logger = logging.getLogger("alphatheta.router.market_data")
router = APIRouter()


# ══════════════════════════════════════════════════════════════════
# GET /option_chain_mini — 迷你期权链 (T 型报价)
# ══════════════════════════════════════════════════════════════════


def _fetch_option_chain(ticker: str, date: str, n_strikes: int = 25) -> dict:
    """
    同步拉取 yfinance 期权链 — 在 asyncio.to_thread 中调用

    返回现价上下各 n_strikes 档的 Call/Put 数据:
      { calls: [...], puts: [...], spot: float, date: str }

    n_strikes 默认 25 — 覆盖 Deep ITM (LEAPS 需 spot×0.80)
    """
    import yfinance as yf

    t = yf.Ticker(ticker)

    # ── 获取现价 ──
    info = t.fast_info
    spot = getattr(info, "last_price", None) or getattr(info, "previous_close", 0)

    # ── 拉取期权链 ──
    try:
        chain = t.option_chain(date)
    except ValueError as e:
        # yfinance 在无效日期时抛 ValueError
        available = list(t.options) if t.options else []
        raise HTTPException(
            status_code=400,
            detail={
                "error": f"Invalid expiration date: {date}",
                "available_expirations": available,
                "message": str(e),
            },
        )

    calls_df = chain.calls
    puts_df = chain.puts

    if calls_df.empty and puts_df.empty:
        return {"calls": [], "puts": [], "spot": spot, "date": date}

    # ── 过滤: 现价 ±n_strikes 档 ──
    all_strikes = sorted(set(calls_df["strike"].tolist() + puts_df["strike"].tolist()))

    # 找 ATM 索引
    atm_idx = 0
    min_dist = abs(all_strikes[0] - spot)
    for i, k in enumerate(all_strikes):
        d = abs(k - spot)
        if d < min_dist:
            min_dist = d
            atm_idx = i

    lo = max(0, atm_idx - n_strikes)
    hi = min(len(all_strikes), atm_idx + n_strikes + 1)
    visible_strikes = set(all_strikes[lo:hi])

    # ── NaN-safe helpers ──
    import math

    def _safe_float(v, default=0.0):
        try:
            f = float(v)
            return default if math.isnan(f) or math.isinf(f) else f
        except (TypeError, ValueError):
            return default

    def _safe_int(v, default=0):
        try:
            f = float(v)
            return default if math.isnan(f) or math.isinf(f) else int(f)
        except (TypeError, ValueError):
            return default

    # ── 格式化 Calls ──
    calls = []
    for _, row in calls_df.iterrows():
        if row["strike"] not in visible_strikes:
            continue
        calls.append({
            "strike": _safe_float(row["strike"]),
            "bid": _safe_float(row.get("bid", 0)),
            "ask": _safe_float(row.get("ask", 0)),
            "lastPrice": _safe_float(row.get("lastPrice", 0)),
            "volume": _safe_int(row.get("volume", 0)),
            "openInterest": _safe_int(row.get("openInterest", 0)),
        })

    # ── 格式化 Puts ──
    puts = []
    for _, row in puts_df.iterrows():
        if row["strike"] not in visible_strikes:
            continue
        puts.append({
            "strike": _safe_float(row["strike"]),
            "bid": _safe_float(row.get("bid", 0)),
            "ask": _safe_float(row.get("ask", 0)),
            "lastPrice": _safe_float(row.get("lastPrice", 0)),
            "volume": _safe_int(row.get("volume", 0)),
            "openInterest": _safe_int(row.get("openInterest", 0)),
        })

    return {
        "calls": calls,
        "puts": puts,
        "spot": round(spot, 2),
        "date": date,
        "strikes": sorted(visible_strikes),
    }


CHAIN_CACHE_TTL = 14400  # 4 hours
CHAIN_FETCH_TIMEOUT = 90  # seconds — LEAPS chains can be very large


@router.get("/option_chain_mini")
async def get_option_chain_mini(
    ticker: str = Query("SPY", max_length=10),
    date: str = Query(..., description="Expiration date YYYY-MM-DD"),
):
    """
    迷你期权链 — Redis 缓存 4h, yfinance 超时 10s 降级
    """
    import asyncio
    import json
    from concurrent.futures import ThreadPoolExecutor

    from app.dependencies import get_redis

    cache_key = f"market:chain:{ticker.upper()}:{date}"

    # ── Step 1: Redis 缓存 ──
    redis = None
    cached_data = None
    try:
        redis = await get_redis()
        raw = await redis.get(cache_key)
        if raw:
            cached_data = json.loads(raw)
            logger.info(f"📋 Chain cache hit: {ticker}/{date}")
    except Exception as e:
        logger.warning(f"Redis read error (chain): {e}")

    # ── Step 2: yfinance 拉取 (带超时) ──
    try:
        loop = asyncio.get_running_loop()
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = loop.run_in_executor(pool, _fetch_option_chain, ticker, date)
            data = await asyncio.wait_for(future, timeout=CHAIN_FETCH_TIMEOUT)

        # 写入缓存
        if redis and data.get("calls"):
            try:
                await redis.set(cache_key, json.dumps(data), ex=CHAIN_CACHE_TTL)
                logger.info(f"📋 Chain cached: {ticker}/{date} (TTL=4h)")
            except Exception as e:
                logger.warning(f"Redis write error (chain): {e}")

        return data

    except HTTPException:
        raise
    except (asyncio.TimeoutError, TimeoutError):
        logger.warning(f"⏱️ yfinance chain timeout ({CHAIN_FETCH_TIMEOUT}s): {ticker}/{date}")
    except Exception as e:
        logger.warning(f"yfinance chain error: {ticker}/{date}: {e}")

    # ── Step 3: 降级到缓存 ──
    if cached_data:
        logger.info(f"📋 Chain fallback to cache: {ticker}/{date}")
        cached_data["_cached"] = True
        return cached_data

    raise HTTPException(status_code=504, detail=f"Option chain timeout and no cache: {ticker}/{date}")


# ══════════════════════════════════════════════════════════════════
# GET /expirations — 可用到期日列表 (Redis 缓存 + 超时降级)
# ══════════════════════════════════════════════════════════════════

EXPIRATIONS_CACHE_TTL = 86400  # 24 hours
EXPIRATIONS_FETCH_TIMEOUT = 8  # seconds


def _fetch_expirations(ticker: str) -> list[str]:
    """同步获取到期日列表"""
    import yfinance as yf

    t = yf.Ticker(ticker)
    return list(t.options) if t.options else []


@router.get("/expirations")
async def get_expirations(ticker: str = Query("SPY", max_length=10)):
    """返回该 Ticker 的所有可用期权到期日 — Redis 缓存 24h, yfinance 超时 8s 降级"""
    import asyncio
    import json
    from concurrent.futures import ThreadPoolExecutor

    from app.dependencies import get_redis

    cache_key = f"market:expirations:{ticker.upper()}"

    # ── Step 1: 尝试从 Redis 读缓存 ──
    redis = None
    cached_data = None
    try:
        redis = await get_redis()
        raw = await redis.get(cache_key)
        if raw:
            cached_data = json.loads(raw)
            logger.info(f"📋 Expirations cache hit: {ticker} ({len(cached_data)} dates)")
    except Exception as e:
        logger.warning(f"Redis read error (expirations): {e}")

    # ── Step 2: 尝试从 yfinance 拉取 (真超时) ──
    try:
        loop = asyncio.get_running_loop()
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = loop.run_in_executor(pool, _fetch_expirations, ticker)
            dates = await asyncio.wait_for(future, timeout=EXPIRATIONS_FETCH_TIMEOUT)

        if dates:
            # 写入 Redis 缓存
            if redis:
                try:
                    await redis.set(cache_key, json.dumps(dates), ex=EXPIRATIONS_CACHE_TTL)
                    logger.info(f"📋 Expirations cached: {ticker} ({len(dates)} dates, TTL=24h)")
                except Exception as e:
                    logger.warning(f"Redis write error (expirations): {e}")

            return {"ticker": ticker, "expirations": dates}

    except (asyncio.TimeoutError, TimeoutError):
        logger.warning(f"⏱️ yfinance timeout ({EXPIRATIONS_FETCH_TIMEOUT}s) for {ticker} expirations")
    except Exception as e:
        logger.warning(f"yfinance error for {ticker} expirations: {e}")

    # ── Step 3: 降级到 Redis 缓存 ──
    if cached_data:
        logger.info(f"📋 Expirations fallback to cache: {ticker} ({len(cached_data)} dates)")
        return {"ticker": ticker, "expirations": cached_data, "_cached": True}

    # ── Step 4: 无缓存也无法拉取 → 504 ──
    raise HTTPException(status_code=504, detail=f"yfinance timeout and no cache available for {ticker}")


# ══════════════════════════════════════════════════════════════════
# GET /templates — 策略组合模板
# ══════════════════════════════════════════════════════════════════

STRATEGY_TEMPLATES = [
    {
        "id": "buy-write",
        "name": "Buy-Write (备兑策略)",
        "description": "持有 100 股正股 + 卖出 1 份 OTM Covered Call",
        "legs": [
            {"type": "stock", "right": None, "action": "buy", "strikeStep": 0, "dteOffset": 0, "qty": 100},
            {"type": "option", "right": "call", "action": "sell", "strikeStep": 2, "dteOffset": 0, "qty": 1},
        ],
    },
    {
        "id": "cash-secured-put",
        "name": "Cash-Secured Put (现金担保看跌)",
        "description": "卖出 1 份 OTM Put，以现金担保行权风险",
        "legs": [
            {"type": "option", "right": "put", "action": "sell", "strikeStep": -1, "dteOffset": 0, "qty": 1},
        ],
    },
    {
        "id": "bull-put-spread",
        "name": "Bull Put Spread (牛市看跌价差)",
        "description": "卖出近价 Put + 买入远价 Put，净收取权利金",
        "legs": [
            {"type": "option", "right": "put", "action": "sell", "strikeStep": -1, "dteOffset": 0, "qty": 1},
            {"type": "option", "right": "put", "action": "buy", "strikeStep": -3, "dteOffset": 0, "qty": 1},
        ],
    },
    {
        "id": "iron-condor",
        "name": "Iron Condor (铁鹰式)",
        "description": "同时卖出 OTM Call 和 Put，各有保护腿，市场中性策略",
        "legs": [
            {"type": "option", "right": "put", "action": "buy", "strikeStep": -4, "dteOffset": 0, "qty": 1},
            {"type": "option", "right": "put", "action": "sell", "strikeStep": -2, "dteOffset": 0, "qty": 1},
            {"type": "option", "right": "call", "action": "sell", "strikeStep": 2, "dteOffset": 0, "qty": 1},
            {"type": "option", "right": "call", "action": "buy", "strikeStep": 4, "dteOffset": 0, "qty": 1},
        ],
    },
    {
        "id": "long-straddle",
        "name": "Long Straddle (买入跨式)",
        "description": "同时买入 ATM Call 和 ATM Put，赌标的大幅波动",
        "legs": [
            {"type": "option", "right": "call", "action": "buy", "strikeStep": 0, "dteOffset": 0, "qty": 1},
            {"type": "option", "right": "put", "action": "buy", "strikeStep": 0, "dteOffset": 0, "qty": 1},
        ],
    },
    {
        "id": "calendar-spread-put",
        "name": "Calendar Spread - Put (日历看跌价差)",
        "description": "卖出近端 ATM Put + 买入远端 ATM Put，赚取 Theta 差",
        "legs": [
            {"type": "option", "right": "put", "action": "sell", "strikeStep": 0, "dteOffset": 0, "qty": 1},
            {"type": "option", "right": "put", "action": "buy", "strikeStep": 0, "dteOffset": 30, "qty": 1},
        ],
    },
    {
        "id": "calendar-spread-call",
        "name": "Calendar Spread - Call (日历看涨价差)",
        "description": "卖出近端 ATM Call + 买入远端 ATM Call",
        "legs": [
            {"type": "option", "right": "call", "action": "sell", "strikeStep": 0, "dteOffset": 0, "qty": 1},
            {"type": "option", "right": "call", "action": "buy", "strikeStep": 0, "dteOffset": 30, "qty": 1},
        ],
    },
    {
        "id": "diagonal-spread",
        "name": "Diagonal Spread (对角价差)",
        "description": "卖出近端 OTM Call + 买入远端 ATM Call",
        "legs": [
            {"type": "option", "right": "call", "action": "sell", "strikeStep": 2, "dteOffset": 0, "qty": 1},
            {"type": "option", "right": "call", "action": "buy", "strikeStep": 0, "dteOffset": 30, "qty": 1},
        ],
    },
    {
        "id": "protective-put",
        "name": "Protective Put (保护性看跌)",
        "description": "持有正股 + 买入 OTM Put 作为下行保险",
        "legs": [
            {"type": "stock", "right": None, "action": "buy", "strikeStep": 0, "dteOffset": 0, "qty": 100},
            {"type": "option", "right": "put", "action": "buy", "strikeStep": -2, "dteOffset": 0, "qty": 1},
        ],
    },
]


@router.get("/templates")
async def get_strategy_templates():
    """返回所有策略组合模板"""
    return {"templates": STRATEGY_TEMPLATES}
