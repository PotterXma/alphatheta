"""
券商凭证模型 — Fernet 加密存储

⚠️ 安全约束:
- api_secret_encrypted: 必须由后端使用 Fernet (AES-128-CBC + HMAC) 加密后写入
- webhook_tokens_encrypted: JSONB 中的值同样必须加密
- 绝不可在 API 响应中返回加密字段的原文
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class UserBrokerCredentials(Base):
    __tablename__ = "user_broker_credentials"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.user_id", ondelete="CASCADE"),
        unique=True, nullable=False,
    )
    broker_name: Mapped[str] = mapped_column(
        String(64), nullable=False, default="tastytrade",
    )
    api_key: Mapped[str | None] = mapped_column(
        String(512), nullable=True,
        comment="公钥 (可明文)",
    )
    api_secret_encrypted: Mapped[str | None] = mapped_column(
        String(1024), nullable=True,
        comment="🔐 Fernet 加密后的私钥, 绝不可明文",
    )
    webhook_tokens_encrypted: Mapped[dict | None] = mapped_column(
        JSONB, default=dict,
        comment="🔐 加密后的推送令牌 (ServerChan, Bark 等)",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(),
    )

    # ── Relationship ──
    user = relationship("User", back_populates="broker_credentials")

    def __repr__(self) -> str:
        return f"<BrokerCreds user={self.user_id} broker={self.broker_name}>"
