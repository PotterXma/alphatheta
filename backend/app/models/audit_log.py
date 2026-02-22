"""审计日志模型 — 不可篡改 (Append-Only)"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, String, Text, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    severity: Mapped[str] = mapped_column(String(16), nullable=False, index=True)  # INFO, WARN, ERROR, CRITICAL
    source: Mapped[str] = mapped_column(String(32), nullable=False, index=True)  # risk_engine, order_manager, admin, reconciliation
    message: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    env_mode: Mapped[str] = mapped_column(String(8), nullable=False, default="paper")
