"""
高级运营路由 — 智能推荐 + Ticker 搜索

提供:
  GET /api/v1/strategy/top-picks   — 财报排雷 Top 3 推荐
  GET /api/v1/strategy/search?q=   — Ticker 模糊搜索
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone

import yfinance as yf
from fastapi import APIRouter
from sqlalchemy import select

from app.adapters.yahoo import YahooFinanceAdapter
from app.db.session import get_async_session
from app.models.watchlist import WatchlistTicker

logger = logging.getLogger("alphatheta.router.advanced_ops")
router = APIRouter()

_yahoo = YahooFinanceAdapter()

# ── 财报排雷窗口 (天) ──
_EARNINGS_BLACKOUT_DAYS = 14
_TICKER_TIMEOUT_SECONDS = 10  # 单标的超时上限


async def _get_earnings_date(ticker: str) -> datetime | None:
    """从 yfinance 获取下一个财报日期 — 带超时保护"""
    try:
        def _fetch():
            t = yf.Ticker(ticker)
            cal = t.earnings_dates
            if cal is None or cal.empty:
                return None
            now = datetime.now(timezone.utc)
            future_dates = []
            for d in cal.index:
                try:
                    dt = d.to_pydatetime()
                    if dt.tzinfo is None:
                        from zoneinfo import ZoneInfo
                        dt = dt.replace(tzinfo=ZoneInfo("UTC"))
                    if dt > now:
                        future_dates.append(dt)
                except Exception:
                    continue
            if not future_dates:
                return None
            return min(future_dates)

        return await asyncio.wait_for(
            asyncio.to_thread(_fetch),
            timeout=_TICKER_TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError:
        logger.warning(f"[TopPicks] ⏱ Earnings lookup TIMEOUT for {ticker} (>{_TICKER_TIMEOUT_SECONDS}s)")
        return None
    except Exception as e:
        logger.debug(f"[TopPicks] earningsDates lookup failed for {ticker}: {e}")
        return None


async def _get_premium_yield(ticker: str) -> dict | None:
    """获取标的的 ATM premium yield — 带超时保护"""
    try:
        async def _inner():
            chain = await _yahoo.get_option_chain(ticker)
            if not chain:
                return None
            quote = await _yahoo.get_quote(ticker)
            spot = quote.get("price", 0) if quote else 0
            if spot <= 0:
                return None
            atm_put = min(chain, key=lambda c: abs(c.get("strike", 0) - spot))
            mid = (atm_put.get("bid", 0) + atm_put.get("ask", 0)) / 2
            premium_yield = (mid / spot) * 100 if spot > 0 else 0
            return {
                "ticker": ticker,
                "current_price": round(spot, 2),
                "atm_strike": atm_put.get("strike", 0),
                "atm_premium": round(mid, 2),
                "premium_yield": round(premium_yield, 2),
                "dte": atm_put.get("dte", 30),
                "delta": atm_put.get("delta", 0),
            }

        return await asyncio.wait_for(
            _inner(),
            timeout=_TICKER_TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError:
        logger.warning(f"[TopPicks] ⏱ Premium yield TIMEOUT for {ticker} (>{_TICKER_TIMEOUT_SECONDS}s)")
        return None
    except Exception as e:
        logger.warning(f"[TopPicks] Premium yield calc failed for {ticker}: {e}")
        return None


@router.get("/top-picks")
async def get_top_picks():
    """
    智能推荐 Top 3 — 财报排雷 + Premium Yield 排序

    容错保证:
    - 单标的超时/异常 → 安全跳过, 绝不会 500
    - Watchlist 为空 / 全部被过滤 → 返回 200 + []
    - 任何未知异常 → 全局兜底, 返回 200 + []
    """
    try:
        # Step 1: 获取候选标的
        async with get_async_session() as session:
            result = await session.execute(
                select(WatchlistTicker.ticker)
                .where(WatchlistTicker.is_active == True)
                .where(WatchlistTicker.supports_options == True)
            )
            candidates = [r[0] for r in result.all()]

        if not candidates:
            return {"picks": [], "message": "票池为空，请先添加标的", "scanned": 0}

        logger.info(f"[TopPicks] Scanning {len(candidates)} candidates: {candidates}")

        # Step 2 & 3: 并行获取财报日期 (每个 ticker 独立超时)
        now = datetime.now(timezone.utc)
        blackout_cutoff = now + timedelta(days=_EARNINGS_BLACKOUT_DAYS)

        earnings_results = await asyncio.gather(
            *[_get_earnings_date(t) for t in candidates],
            return_exceptions=True,
        )

        safe_tickers = []
        for ticker, earnings in zip(candidates, earnings_results):
            if isinstance(earnings, Exception) or earnings is None:
                safe_tickers.append({"ticker": ticker, "next_earnings": None, "reasoning": "无财报数据，视为安全"})
            elif earnings <= blackout_cutoff:
                logger.info(f"[TopPicks] {ticker} excluded: earnings on {earnings.date()} within {_EARNINGS_BLACKOUT_DAYS}d window")
            else:
                safe_tickers.append({
                    "ticker": ticker,
                    "next_earnings": earnings.isoformat(),
                    "reasoning": f"财报安全窗口: {earnings.date()} (>{_EARNINGS_BLACKOUT_DAYS}天)",
                })

        if not safe_tickers:
            return {"picks": [], "message": "所有标的均在财报窗口内，暂无推荐", "scanned": len(candidates)}

        # Step 4: 并行计算 premium yield (每个 ticker 独立超时)
        yield_results = await asyncio.gather(
            *[_get_premium_yield(t["ticker"]) for t in safe_tickers],
            return_exceptions=True,
        )

        scored = []
        for meta, yld in zip(safe_tickers, yield_results):
            if isinstance(yld, Exception) or yld is None:
                logger.debug(f"[TopPicks] {meta['ticker']} skipped: yield unavailable")
                continue
            scored.append({
                **yld,
                "next_earnings": meta["next_earnings"],
                "reasoning": meta["reasoning"],
                "score": yld["premium_yield"],
            })

        # Step 5: 降序取 Top 3
        scored.sort(key=lambda x: x["score"], reverse=True)
        picks = scored[:3]

        logger.info(f"[TopPicks] Result: {len(picks)} picks from {len(candidates)} scanned")

        return {
            "picks": picks,
            "scanned": len(candidates),
            "passed_filter": len(safe_tickers),
            "scored": len(scored),
        }

    except Exception as e:
        # ══ 全局兜底 — 绝不返回 500 ══
        logger.error(f"[TopPicks] ⚠️ GLOBAL FALLBACK triggered: {e}", exc_info=True)
        return {"picks": [], "message": f"服务异常: {str(e)[:100]}", "scanned": 0}


@router.get("/search")
async def search_tickers(q: str = ""):
    """
    Ticker 模糊搜索 — 前端防抖下拉补全

    查询 yfinance 获取 ticker + 公司名，返回最多 8 条
    """
    q = q.strip().upper()
    if len(q) < 1:
        return {"results": []}

    try:
        def _search():
            import yfinance as yf
            # yfinance doesn't have a search API, so we do a ticker info lookup
            # For broader search, we check if the ticker is valid
            results = []
            # Try exact match first
            try:
                t = yf.Ticker(q)
                info = t.info
                if info and info.get("regularMarketPrice"):
                    results.append({
                        "ticker": q,
                        "name": info.get("shortName", info.get("longName", "")),
                        "exchange": info.get("exchange", ""),
                        "price": info.get("regularMarketPrice", 0),
                    })
            except Exception:
                pass

            # Try common suffixes for partial matches
            if len(q) >= 2:
                common_tickers = [
                    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA",
                    "AMD", "INTC", "NFLX", "DIS", "PYPL", "SQ", "SHOP",
                    "SPY", "QQQ", "IWM", "DIA", "VTI", "ARKK",
                    "JPM", "BAC", "GS", "V", "MA", "BRK-B",
                    "XOM", "CVX", "PFE", "JNJ", "UNH", "ABBV",
                    "PLTR", "SOFI", "COIN", "HOOD", "SNAP", "PINS",
                    "BA", "CAT", "DE", "GE", "HON", "LMT", "RTX",
                    "CRM", "ORCL", "ADBE", "NOW", "SNOW", "DDOG",
                ]
                for sym in common_tickers:
                    if sym.startswith(q) and sym != q:
                        try:
                            t = yf.Ticker(sym)
                            info = t.info
                            if info and info.get("regularMarketPrice"):
                                results.append({
                                    "ticker": sym,
                                    "name": info.get("shortName", info.get("longName", "")),
                                    "exchange": info.get("exchange", ""),
                                    "price": info.get("regularMarketPrice", 0),
                                })
                        except Exception:
                            pass
                    if len(results) >= 8:
                        break

            return results[:8]

        results = await asyncio.to_thread(_search)
        return {"results": results}

    except Exception as e:
        logger.warning(f"Ticker search failed for '{q}': {e}")
        return {"results": [], "error": str(e)}
