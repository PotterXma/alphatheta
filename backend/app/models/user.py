"""
用户模型 — 租户根实体 + 资金账户

设计要点:
1. user_id (UUID) 作为所有业务表的 FK 根
2. cash_balance / margin_used 使用 Numeric(14,4) + CHECK >= 0 防超卖
3. account_type 枚举: PAPER (模拟) / LIVE (实盘)
4. password_hash 由后端 bcrypt/argon2 生成, 绝不可明文
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class AccountType(str, enum.Enum):
    PAPER = "paper"
    LIVE = "live"


class User(Base):
    __tablename__ = "users"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
    )
    username: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False,
    )
    email: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True,
    )
    password_hash: Mapped[str] = mapped_column(
        String(255), nullable=False,
        comment="bcrypt/argon2 密文, 绝不可明文存储",
    )
    account_type: Mapped[AccountType] = mapped_column(
        Enum(AccountType), nullable=False, default=AccountType.PAPER,
    )

    # ── 资金核心字段 — 悲观锁的锁定目标 ──
    cash_balance: Mapped[float] = mapped_column(
        Numeric(14, 4), nullable=False, default=100000.0,
        comment="可用现金 (Paper 默认 $100,000)",
    )
    margin_used: Mapped[float] = mapped_column(
        Numeric(14, 4), nullable=False, default=0.0,
        comment="已用保证金",
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(),
    )

    # ── Relationships (延迟加载) ──
    broker_credentials = relationship(
        "UserBrokerCredentials", back_populates="user", uselist=False,
    )
    watchlist_items = relationship(
        "UserWatchlist", back_populates="user",
    )

    def __repr__(self) -> str:
        return f"<User {self.username} ({self.account_type.value})>"
