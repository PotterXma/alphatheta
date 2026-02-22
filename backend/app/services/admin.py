"""管理服务 — API Key 加密 + Kill Switch 双写 + 审计日志 + 高管报表"""

import logging
import uuid
from datetime import datetime, timezone

from cryptography.fernet import Fernet
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.api_key import ApiKey
from app.models.audit_log import AuditLog
from app.models.kill_switch import KillSwitchState
from app.schemas.admin import (
    ApiKeyCreate,
    ApiKeyResponse,
    DailyReport,
    KillSwitchStatus,
    KillSwitchToggle,
    LogEntry,
)

logger = logging.getLogger("alphatheta.admin")


class AdminService:
    def __init__(self, db: AsyncSession, redis=None):
        self.db = db
        self.redis = redis
        settings = get_settings()
        self._fernet = Fernet(settings.encryption_key.encode()) if settings.encryption_key else None

    # ── API Key CRUD ──

    async def create_api_key(self, req: ApiKeyCreate) -> ApiKey:
        if not self._fernet:
            raise RuntimeError("ENCRYPTION_KEY not configured")
        key = ApiKey(
            provider=req.provider,
            encrypted_key=self._fernet.encrypt(req.key.encode()).decode(),
            encrypted_secret=self._fernet.encrypt(req.secret.encode()).decode(),
            mode=req.mode,
            label=req.label,
        )
        self.db.add(key)
        await self.db.flush()
        return key

    async def list_api_keys(self) -> list[ApiKeyResponse]:
        result = await self.db.execute(select(ApiKey))
        keys = result.scalars().all()
        return [
            ApiKeyResponse(
                id=k.id, provider=k.provider,
                key_masked=f"****-{self._decrypt(k.encrypted_key)[-4:]}" if self._fernet else "****",
                mode=k.mode, label=k.label, created_at=k.created_at,
            )
            for k in keys
        ]

    def _decrypt(self, encrypted: str) -> str:
        if not self._fernet:
            return "????"
        return self._fernet.decrypt(encrypted.encode()).decode()

    # ── Kill Switch ──

    async def toggle_kill_switch(self, toggle: KillSwitchToggle) -> KillSwitchStatus:
        settings = get_settings()
        env = settings.env_mode.value

        # PG 更新
        result = await self.db.execute(
            select(KillSwitchState).where(KillSwitchState.env_mode == env)
        )
        state = result.scalar_one_or_none()
        if not state:
            state = KillSwitchState(env_mode=env)
            self.db.add(state)

        state.active = toggle.active
        state.reason = toggle.reason
        if toggle.active:
            state.activated_at = datetime.now(timezone.utc)
        else:
            state.deactivated_at = datetime.now(timezone.utc)

        await self.db.flush()

        # Redis 同步
        if self.redis:
            key = f"system:kill_switch:{env}"
            await self.redis.set(key, "1" if toggle.active else "0")

        # 审计日志
        await self.create_log(
            severity="CRITICAL" if toggle.active else "INFO",
            source="admin",
            message=f"Kill switch {'ACTIVATED' if toggle.active else 'DEACTIVATED'}: {toggle.reason or 'no reason'}",
        )

        action = "ACTIVATED" if toggle.active else "DEACTIVATED"
        logger.warning(f"Kill switch {action} [{env}]: {toggle.reason}")

        return KillSwitchStatus(
            active=state.active, activated_at=state.activated_at,
            reason=state.reason, env_mode=env,
        )

    async def get_kill_switch_status(self) -> KillSwitchStatus:
        settings = get_settings()
        result = await self.db.execute(
            select(KillSwitchState).where(KillSwitchState.env_mode == settings.env_mode.value)
        )
        state = result.scalar_one_or_none()
        return KillSwitchStatus(
            active=state.active if state else False,
            activated_at=state.activated_at if state else None,
            reason=state.reason if state else None,
            env_mode=settings.env_mode.value,
        )

    async def restore_kill_switch_to_redis(self):
        """启动时从 PG 恢复 Kill Switch 到 Redis"""
        status = await self.get_kill_switch_status()
        if self.redis:
            key = f"system:kill_switch:{status.env_mode}"
            await self.redis.set(key, "1" if status.active else "0")
            logger.info(f"Kill switch restored to Redis: active={status.active}")

    # ── 审计日志 ──

    async def create_log(self, severity: str, source: str, message: str, metadata: dict | None = None):
        settings = get_settings()
        log = AuditLog(
            severity=severity, source=source, message=message,
            metadata_json=metadata, env_mode=settings.env_mode.value,
        )
        self.db.add(log)
        await self.db.flush()
        return log

    async def get_logs(self, limit: int = 50, offset: int = 0) -> list[LogEntry]:
        result = await self.db.execute(
            select(AuditLog)
            .order_by(AuditLog.timestamp.desc())
            .limit(limit).offset(offset)
        )
        return [
            LogEntry(
                id=l.id, timestamp=l.timestamp, severity=l.severity,
                source=l.source, message=l.message, metadata_json=l.metadata_json,
            )
            for l in result.scalars().all()
        ]

    # ── 高管价值报表 ──

    async def generate_daily_report(self, date: str) -> DailyReport:
        """聚合当日指标 — 风控拦截数、展期次数、Premium 收入等"""
        settings = get_settings()
        # TODO: 实际查询聚合
        return DailyReport(
            date=date,
            risk_rejections=0,
            estimated_loss_avoided=0.0,
            rolls_executed=0,
            premium_collected=0.0,
            orders_processed=0,
            kill_switch_activations=0,
            system_uptime_hours=24.0,
        )
