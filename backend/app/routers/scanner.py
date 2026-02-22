"""
Scanner 状态路由 — 供前端系统健康检查使用

GET /api/v1/scanner/status
  → 读取 Redis scanner:heartbeat key
  → 返回 {status, watchlist_count, last_scan}
"""

import json
import logging

from fastapi import APIRouter

logger = logging.getLogger("alphatheta.router.scanner")
router = APIRouter()


async def _get_db_watchlist_count() -> int:
    """从 DB 获取实际票池数量 (fallback)"""
    try:
        from sqlalchemy import select, func
        from app.db.session import get_async_session
        from app.models.watchlist import WatchlistTicker
        async with get_async_session() as session:
            result = await session.execute(
                select(func.count()).select_from(WatchlistTicker).where(WatchlistTicker.is_active == True)
            )
            return result.scalar() or 0
    except Exception:
        return 0


@router.get("/status")
async def scanner_status():
    """Scanner Daemon 健康状态 — Redis heartbeat + DB fallback"""
    watchlist_count = await _get_db_watchlist_count()

    try:
        from app.dependencies import get_redis
        redis = await get_redis()
        raw = await redis.get("scanner:heartbeat")

        if raw:
            data = json.loads(raw)
            return {
                "status": "running",
                "watchlist_count": data.get("watchlist_count", watchlist_count),
                "redis_ok": data.get("redis_ok", True),
                "last_scan": data.get("ts", "N/A"),
            }
        else:
            return {
                "status": "idle",
                "watchlist_count": watchlist_count,
                "last_scan": "N/A",
                "message": "Scanner daemon not running",
            }
    except Exception as e:
        logger.warning(f"Scanner status check failed: {e}")
        return {
            "status": "unknown",
            "watchlist_count": watchlist_count,
            "last_scan": "N/A",
            "message": str(e),
        }
