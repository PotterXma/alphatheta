"""
Portfolio Router — 盯市净值曲线 API
"""
import logging
import math
from datetime import date, timedelta

from fastapi import APIRouter, Query
from sqlalchemy import select

from app.db.session import get_async_session
from app.models.portfolio_snapshot import PortfolioSnapshot

logger = logging.getLogger("alphatheta.router.portfolio")
router = APIRouter()


@router.get("/equity-curve")
async def get_equity_curve(days: int = Query(90, ge=1, le=365)):
    """
    GET /api/v1/portfolio/equity-curve
    返回盯市净值时间序列 + 摘要统计
    """
    cutoff = date.today() - timedelta(days=days)

    async with get_async_session() as session:
        result = await session.execute(
            select(PortfolioSnapshot)
            .where(PortfolioSnapshot.snapshot_date >= cutoff)
            .order_by(PortfolioSnapshot.snapshot_date.asc())
        )
        snapshots = result.scalars().all()

    if not snapshots:
        return {"curve": [], "summary": None}

    # ── 构建曲线数据 ──
    curve = []
    for s in snapshots:
        cash_ratio = (s.cash_balance / s.total_equity * 100) if s.total_equity else 0
        curve.append({
            "date": s.snapshot_date.isoformat(),
            "total_equity": round(s.total_equity, 2),
            "cash_balance": round(s.cash_balance, 2),
            "positions_value": round(s.positions_value, 2),
            "cash_ratio": round(cash_ratio, 2),
        })

    # ── 摘要统计 ──
    start_equity = snapshots[0].total_equity
    end_equity = snapshots[-1].total_equity
    total_return_pct = ((end_equity - start_equity) / start_equity * 100) if start_equity else 0

    # 最大回撤
    peak = snapshots[0].total_equity
    max_drawdown = 0
    for s in snapshots:
        if s.total_equity > peak:
            peak = s.total_equity
        dd = (s.total_equity - peak) / peak * 100 if peak else 0
        if dd < max_drawdown:
            max_drawdown = dd

    # 简化夏普比 (假设日收益率, rf=0)
    if len(snapshots) > 1:
        daily_returns = []
        for i in range(1, len(snapshots)):
            prev = snapshots[i - 1].total_equity
            curr = snapshots[i].total_equity
            if prev > 0:
                daily_returns.append((curr - prev) / prev)
        if daily_returns:
            mean_r = sum(daily_returns) / len(daily_returns)
            std_r = math.sqrt(sum((r - mean_r) ** 2 for r in daily_returns) / len(daily_returns))
            sharpe = (mean_r / std_r * math.sqrt(252)) if std_r > 0 else 0
        else:
            sharpe = 0
    else:
        sharpe = 0

    summary = {
        "start_equity": round(start_equity, 2),
        "end_equity": round(end_equity, 2),
        "total_return_pct": round(total_return_pct, 2),
        "max_drawdown_pct": round(max_drawdown, 2),
        "sharpe_ratio": round(sharpe, 2),
        "days": len(snapshots),
    }

    return {"curve": curve, "summary": summary}
