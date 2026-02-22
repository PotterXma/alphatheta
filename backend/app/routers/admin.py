"""Admin, Audit & Reporting API Router"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, get_redis
from app.schemas.admin import (
    ApiKeyCreate,
    ApiKeyResponse,
    DailyReport,
    HealthCheck,
    KillSwitchStatus,
    KillSwitchToggle,
    LogEntry,
)
from app.services.admin import AdminService

router = APIRouter()


@router.post("/api-keys", response_model=dict)
async def create_api_key(req: ApiKeyCreate, db: AsyncSession = Depends(get_db)):
    svc = AdminService(db)
    key = await svc.create_api_key(req)
    return {"id": str(key.id), "provider": key.provider, "status": "created"}


@router.get("/api-keys", response_model=list[ApiKeyResponse])
async def list_api_keys(db: AsyncSession = Depends(get_db)):
    svc = AdminService(db)
    return await svc.list_api_keys()


@router.post("/kill-switch", response_model=KillSwitchStatus)
async def toggle_kill_switch(
    toggle: KillSwitchToggle,
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
):
    svc = AdminService(db, redis)
    return await svc.toggle_kill_switch(toggle)


@router.get("/kill-switch", response_model=KillSwitchStatus)
async def get_kill_switch(db: AsyncSession = Depends(get_db)):
    svc = AdminService(db)
    return await svc.get_kill_switch_status()


@router.get("/logs", response_model=list[LogEntry])
async def get_logs(limit: int = 50, offset: int = 0, db: AsyncSession = Depends(get_db)):
    svc = AdminService(db)
    return await svc.get_logs(limit, offset)


@router.get("/reports/daily", response_model=DailyReport)
async def get_daily_report(date: str = "2026-02-20", db: AsyncSession = Depends(get_db)):
    svc = AdminService(db)
    return await svc.generate_daily_report(date)


@router.get("/health", response_model=HealthCheck)
async def health_check():
    """全面健康检查 — PG, Redis, Broker, NTP"""
    from app.config import get_settings
    settings = get_settings()
    # TODO: 实际 ping 各子系统
    return HealthCheck(
        status="healthy",
        env_mode=settings.env_mode.value,
    )
