"""
系统设置路由 — Watchlist CRUD (DB-backed) + Wheel FSM 状态查询

提供:
  GET    /api/v1/settings/watchlist              — 获取全部关注标的
  POST   /api/v1/settings/watchlist              — 新增关注标的
  PUT    /api/v1/settings/watchlist/{ticker}      — 更新标的字段
  PUT    /api/v1/settings/watchlist/{ticker}/toggle — 切换启停状态
  DELETE /api/v1/settings/watchlist/{ticker}      — 硬删除标的
  GET    /api/v1/settings/wheel                  — 获取所有车轮 FSM 状态
  GET    /api/v1/settings/wheel/{ticker}         — 获取单个 FSM 状态
"""

import asyncio
import logging
import re

import yfinance as yf
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select, func as sa_func

from app.db.session import get_async_session
from app.models.watchlist import WatchlistTicker
from app.models.order import Order, OrderStatus
from app.strategy.wheel_machine import get_all_wheels, get_wheel

logger = logging.getLogger("alphatheta.router.settings")
router = APIRouter()


# ── 请求/响应 DTO ──

class WatchlistAddRequest(BaseModel):
    """新增关注标的请求"""
    ticker: str = Field(..., min_length=1, max_length=10, description="标的代码")
    asset_class: str = Field(default="equity", pattern=r"^(equity|etf|index)$")
    min_liquidity_score: float = Field(default=0.5, ge=0, le=1)

    @field_validator("ticker")
    @classmethod
    def validate_ticker(cls, v: str) -> str:
        v = v.upper().strip()
        if not re.match(r"^[A-Z\^]{1,10}$", v):
            raise ValueError(f"Invalid ticker format: '{v}'. Must be 1-10 uppercase letters.")
        return v


class WatchlistUpdateRequest(BaseModel):
    """更新标的字段请求"""
    min_liquidity_score: float | None = Field(default=None, ge=0, le=1)
    asset_class: str | None = Field(default=None, pattern=r"^(equity|etf|index)$")
    notes: str | None = Field(default=None, max_length=200)


# ── 辅助函数 ──

def _ticker_to_dict(t: WatchlistTicker) -> dict:
    """WatchlistTicker ORM → JSON-safe dict"""
    return {
        "ticker": t.ticker,
        "is_active": getattr(t, "is_active", True),
        "asset_class": getattr(t, "asset_class", None) or "equity",
        "supports_options": getattr(t, "option_enabled", None) if getattr(t, "option_enabled", None) is not None else True,
        "min_liquidity_score": float(getattr(t, "liquidity_threshold", None) or 100.0),
        "notes": getattr(t, "notes", None),
    }


async def _find_by_ticker(session, ticker: str) -> WatchlistTicker | None:
    """按 ticker 查找 (新模型使用 UUID PK, ticker 不再是 PK)"""
    result = await session.execute(
        select(WatchlistTicker).where(WatchlistTicker.ticker == ticker)
    )
    return result.scalar_one_or_none()


async def _check_options_support(ticker: str) -> bool:
    """用 yfinance 校验该标的是否有期权链"""
    try:
        def _check():
            t = yf.Ticker(ticker)
            options = t.options
            return bool(options and len(options) > 0)
        return await asyncio.to_thread(_check)
    except Exception:
        return False


# ── Watchlist CRUD (DB-backed) ──

@router.get("/watchlist")
async def get_watchlist():
    """获取全部关注标的 (含 inactive)"""
    async with get_async_session() as session:
        result = await session.execute(
            select(WatchlistTicker).order_by(WatchlistTicker.ticker)
        )
        tickers = [t for t in result.scalars().all() if t is not None]
        items = [_ticker_to_dict(t) for t in tickers]
        return {
            "tickers": items,
            "total": len(items),
            "active": sum(1 for t in items if t["is_active"]),
        }


@router.post("/watchlist", status_code=201)
async def add_watchlist_ticker(req: WatchlistAddRequest):
    """
    新增关注标的

    校验:
    1. Ticker 格式 (大写字母, 1-10位)
    2. 是否已存在 (幂等: 重复添加不报错, 重新激活)
    3. yfinance 校验是否支持期权交易
    """
    ticker = req.ticker

    async with get_async_session() as session:
        existing = await _find_by_ticker(session, ticker)

        if existing:
            # 幂等: 已存在则重新激活
            existing.is_active = True
            logger.info(f"[Settings] Re-activated {ticker}")
            return {"message": f"{ticker} already exists, re-activated", "ticker": _ticker_to_dict(existing)}

        # 校验期权支持
        supports_options = await _check_options_support(ticker)

        new_ticker = WatchlistTicker(
            ticker=ticker,
            is_active=True,
            asset_class=req.asset_class,
            option_enabled=supports_options,
            liquidity_threshold=req.min_liquidity_score * 200,  # 0-1 → 0-200 scale
        )
        session.add(new_ticker)
        logger.info(f"[Settings] Added {ticker} (options={supports_options})")
        return {
            "message": f"{ticker} added to watchlist",
            "ticker": _ticker_to_dict(new_ticker),
            "supports_options": supports_options,
        }


@router.put("/watchlist/{ticker}")
async def update_watchlist_ticker(ticker: str, req: WatchlistUpdateRequest):
    """更新标的字段 (min_liquidity_score, asset_class, notes)"""
    ticker = ticker.upper()

    async with get_async_session() as session:
        existing = await _find_by_ticker(session, ticker)
        if not existing:
            raise HTTPException(status_code=404, detail=f"Ticker {ticker} not in watchlist")

        if req.min_liquidity_score is not None:
            existing.liquidity_threshold = req.min_liquidity_score * 200
        if req.asset_class is not None:
            existing.asset_class = req.asset_class
        if req.notes is not None:
            existing.notes = req.notes

        logger.info(f"[Settings] Updated {ticker}")
        return {"message": f"{ticker} updated", "ticker": _ticker_to_dict(existing)}


@router.put("/watchlist/{ticker}/toggle")
async def toggle_watchlist_ticker(ticker: str):
    """切换标的 is_active 状态"""
    ticker = ticker.upper()

    async with get_async_session() as session:
        existing = await _find_by_ticker(session, ticker)
        if not existing:
            raise HTTPException(status_code=404, detail=f"Ticker {ticker} not in watchlist")

        existing.is_active = not existing.is_active
        new_state = existing.is_active
        logger.info(f"[Settings] Toggled {ticker} → {'active' if new_state else 'inactive'}")
        return {
            "message": f"{ticker} {'activated' if new_state else 'deactivated'}",
            "ticker": _ticker_to_dict(existing),
        }


@router.delete("/watchlist/{ticker}")
async def remove_watchlist_ticker(ticker: str):
    """硬删除标的 — 含孤儿订单防护"""
    ticker = ticker.upper()

    async with get_async_session() as session:
        existing = await _find_by_ticker(session, ticker)
        if not existing:
            raise HTTPException(status_code=404, detail=f"Ticker {ticker} not in watchlist")

        # ── 孤儿订单防护: 检查活跃持仓/挂单 ──
        from sqlalchemy import text
        active_count_result = await session.execute(
            text(
                "SELECT count(*) FROM orders_master "
                "WHERE ticker = :ticker AND status IN ('pending', 'partial_fill', 'draft')"
            ),
            {"ticker": ticker},
        )
        active_count = active_count_result.scalar() or 0

        if active_count > 0:
            raise HTTPException(
                status_code=400,
                detail=f"无法移除该标的！当前仍持有 {active_count} 笔活跃仓位，请先平仓以防止产生孤儿订单。",
            )

        await session.delete(existing)
        logger.info(f"[Settings] Deleted {ticker} from watchlist")
        return {"message": f"{ticker} removed from watchlist"}


# ── Wheel FSM 状态查询 ──

@router.get("/wheel")
async def get_wheel_status_all():
    """获取所有车轮 FSM 状态 — 供"全程跟踪"视图渲染"""
    return {"wheels": get_all_wheels()}


@router.get("/wheel/{ticker}")
async def get_wheel_status(ticker: str):
    """获取单个标的的车轮 FSM 状态"""
    ticker = ticker.upper()
    wheel = get_wheel(ticker)
    return wheel.get_status()
