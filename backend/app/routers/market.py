"""
Market API Router — 实时行情 + VIX + 技术指标

数据源优先级:
  1. Tradier API (如果有 Token) — 实时
  2. Yahoo Finance (yfinance) — 延迟 ~15 分钟, 免费
  3. 硬编码兜底 — 所有数据源都失败时

所有端点都返回 JSON, 前端 Dashboard 通过 /api/v1/market/* 拉取
"""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter

from app.adapters.yahoo import YahooFinanceAdapter
from app.schemas.market import CalendarStatus, MarketContext

logger = logging.getLogger("alphatheta.router.market")
router = APIRouter()

_yahoo = YahooFinanceAdapter()


@router.get("/chart/{ticker}")
async def get_chart_data(ticker: str, period: str = "1D"):
    """
    获取 K 线图数据 — 前端图表专用

    周期与数据密度对应关系:
      1D → 最近 1 天, 5 分钟粒度 (约 78 根蜡烛)
      1W → 最近 5 天, 1 小时粒度 (约 35 根蜡烛)
      1M → 最近 1 个月, 日线粒度 (约 22 根蜡烛)
    """
    import asyncio

    try:
        data = await asyncio.to_thread(_fetch_chart_data, ticker, period)
        return data
    except Exception as e:
        logger.exception(f"Chart data failed for {ticker}/{period}: {e}")
        return {"candles": [], "sma": [], "error": str(e)}


def _fetch_chart_data(ticker: str, period: str) -> dict:
    """同步拉取 yfinance 历史 K 线"""
    import yfinance as yf

    # 周期映射: 前端 period → yfinance (period, interval)
    # 1D: 最近 1 天, 5 分钟蜡烛 (盘中日内)
    # 1W: 最近 5 天, 1 小时蜡烛 (近一周走势)
    # 1M: 最近 1 个月, 日线蜡烛 (月度趋势)
    period_map = {
        "1D": ("1d", "5m"),
        "1W": ("5d", "1h"),
        "1M": ("1mo", "1d"),
    }
    yf_period, yf_interval = period_map.get(period, ("1mo", "1d"))

    t = yf.Ticker(ticker)
    hist = t.history(period=yf_period, interval=yf_interval)

    if hist.empty:
        return {"candles": [], "sma": []}

    candles = []
    sma_data = []
    closes = []

    for idx, row in hist.iterrows():
        # TradingView Lightweight Charts 需要 Unix 时间戳 (秒)
        ts = int(idx.timestamp())
        o, h, l, c = float(row["Open"]), float(row["High"]), float(row["Low"]), float(row["Close"])
        closes.append(c)

        candles.append({
            "time": ts,
            "open": round(o, 2),
            "high": round(h, 2),
            "low": round(l, 2),
            "close": round(c, 2),
        })

        # SMA 均线 (10 根 for 1D/1W, 20 根 for 1M)
        sma_window = 20 if period == "1M" else 10
        if len(closes) >= sma_window:
            avg = sum(closes[-sma_window:]) / sma_window
            sma_data.append({"time": ts, "value": round(avg, 2)})

    return {"candles": candles, "sma": sma_data}



@router.get("/dashboard")
async def get_dashboard_data():
    """
    Dashboard 聚合接口 — 一次请求返回所有卡片需要的数据

    前端 app.js 只需调一次 /api/v1/market/dashboard
    而不是为 VIX / SPY / QQQ 各调一次
    """
    try:
        import asyncio

        # 并行拉取所有数据 — 比串行快 3x
        spy_quote, qqq_quote, vix_val, spy_indicators = await asyncio.gather(
            _yahoo.get_quote("SPY"),
            _yahoo.get_quote("QQQ"),
            _yahoo.get_vix(),
            _yahoo.get_indicators("SPY"),
        )

        return {
            "vix": vix_val,
            "spy": {
                "price": spy_quote.last,
                "bid": spy_quote.bid,
                "ask": spy_quote.ask,
                "volume": spy_quote.volume,
                "sma200": spy_indicators.get("sma200", 0),
                "sma200_distance": spy_indicators.get("sma200_distance", 0),
                "rsi_14": spy_indicators.get("rsi_14", 50),
            },
            "qqq": {
                "price": qqq_quote.last,
                "bid": qqq_quote.bid,
                "ask": qqq_quote.ask,
                "volume": qqq_quote.volume,
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    except Exception as e:
        logger.exception(f"Dashboard data fetch failed: {e}")
        # 兜底: 返回零值 + 错误标记
        return {
            "vix": 0,
            "spy": {"price": 0, "bid": 0, "ask": 0, "volume": 0, "sma200": 0, "sma200_distance": 0, "rsi_14": 50},
            "qqq": {"price": 0, "bid": 0, "ask": 0, "volume": 0},
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "error": str(e),
        }


@router.get("/{ticker}", response_model=MarketContext)
async def get_market_context(ticker: str):
    """获取单标的完整行情上下文"""
    try:
        import asyncio

        quote, vix_val, indicators = await asyncio.gather(
            _yahoo.get_quote(ticker),
            _yahoo.get_vix(),
            _yahoo.get_indicators(ticker),
        )

        mid = (quote.bid + quote.ask) / 2
        spread = (quote.ask - quote.bid) / quote.ask * 100 if quote.ask > 0 else 0

        return MarketContext(
            ticker=ticker,
            bid=quote.bid,
            ask=quote.ask,
            mid_price=round(mid, 2),
            spread_pct=round(spread, 2),
            vix=vix_val,
            rsi_14=indicators.get("rsi_14", 50.0),
            sma200_distance=indicators.get("sma200_distance", 0.0),
        )

    except Exception as e:
        logger.exception(f"Market context failed for {ticker}: {e}")
        return MarketContext(
            ticker=ticker, bid=0, ask=0, mid_price=0,
            spread_pct=0, vix=18.5, rsi_14=50, sma200_distance=0,
        )


@router.get("/calendar/status", response_model=CalendarStatus)
async def get_calendar_status():
    """获取交易日历状态"""
    try:
        import exchange_calendars as xcals
        import pandas as pd

        nyse = xcals.get_calendar("XNYS")
        now_utc = pd.Timestamp.now(tz="UTC")
        is_open = nyse.is_open_on_minute(now_utc)
        eastern = now_utc.tz_convert("US/Eastern")

        return CalendarStatus(
            is_open=is_open,
            current_time_est=str(eastern.strftime("%H:%M:%S")),
        )
    except Exception:
        return CalendarStatus(is_open=True, current_time_est="--:--:--")
