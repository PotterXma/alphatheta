"""API Key 模型 — Fernet 加密存储"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ApiKey(Base):
    __tablename__ = "api_keys"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    provider: Mapped[str] = mapped_column(String(32), nullable=False)  # tradier, ibkr
    encrypted_key: Mapped[str] = mapped_column(String(512), nullable=False)
    encrypted_secret: Mapped[str] = mapped_column(String(512), nullable=False)
    mode: Mapped[str] = mapped_column(String(16), nullable=False, default="read-write")  # read-only | read-write
    label: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
