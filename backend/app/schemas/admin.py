"""Pydantic schemas — Admin, Audit, Reporting DTOs"""

import uuid
from datetime import datetime

from pydantic import BaseModel


class ApiKeyCreate(BaseModel):
    provider: str
    key: str
    secret: str
    mode: str = "read-write"
    label: str | None = None


class ApiKeyResponse(BaseModel):
    id: uuid.UUID
    provider: str
    key_masked: str  # ****-XXXX
    mode: str
    label: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class KillSwitchToggle(BaseModel):
    active: bool
    reason: str | None = None


class KillSwitchStatus(BaseModel):
    active: bool
    activated_at: datetime | None
    reason: str | None
    env_mode: str


class LogEntry(BaseModel):
    id: uuid.UUID
    timestamp: datetime
    severity: str
    source: str
    message: str
    metadata_json: dict | None = None

    model_config = {"from_attributes": True}


class HealthCheck(BaseModel):
    status: str  # healthy | degraded
    postgres: str = "up"
    timescaledb: str = "up"
    redis: str = "up"
    broker: str = "up"
    ntp_sync: str = "ok"
    kill_switch: bool = False
    env_mode: str = "paper"


class DailyReport(BaseModel):
    date: str
    risk_rejections: int = 0
    estimated_loss_avoided: float = 0.0
    rolls_executed: int = 0
    premium_collected: float = 0.0
    orders_processed: int = 0
    kill_switch_activations: int = 0
    system_uptime_hours: float = 0.0
