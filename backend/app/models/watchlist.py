"""
关注票池模型 — 多租户个性化票池

设计要点:
1. user_id FK — 每用户独立票池, 互不可见
2. UNIQUE(user_id, ticker) — 同一用户不可重复添加
3. risk_limit_pct — 单票最大仓位占比, CHECK 0-100
4. auto_trade_enabled — 默认 False, 需人工开启
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean, DateTime, Float, ForeignKey,
    Numeric, String, UniqueConstraint, func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class UserWatchlist(Base):
    # 保留旧表名以兼容现有数据; auto_migrate 会自动补齐新字段
    __tablename__ = "watchlist_tickers"
    __table_args__ = (
        UniqueConstraint("user_id", "ticker", name="uq_user_ticker"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=True, index=True,  # nullable 直到前端 auth 接入
    )
    ticker: Mapped[str] = mapped_column(
        String(10), nullable=False,
        comment="美股 Ticker (如 AAPL, SPY)",
    )
    risk_limit_pct: Mapped[float] = mapped_column(
        Numeric(5, 2), nullable=False, default=5.0,
        comment="单票最大仓位占比 (%)",
    )
    auto_trade_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False,
        comment="自动下单开关 (默认关)",
    )
    option_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True,
        comment="是否启用期权扫描",
    )
    liquidity_threshold: Mapped[float] = mapped_column(
        Numeric(8, 2), nullable=False, default=100.0,
        comment="最低流动性阈值",
    )

    # 保留旧字段兼容
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true",
    )
    asset_class: Mapped[str] = mapped_column(
        String(20), default="equity",
    )
    notes: Mapped[str | None] = mapped_column(
        String(200), nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(),
    )

    # ── Relationship ──
    user = relationship("User", back_populates="watchlist_items")

    def __repr__(self) -> str:
        return f"<Watchlist {self.ticker} risk={self.risk_limit_pct}%>"


# ── 向后兼容别名 ──
# 旧代码使用 WatchlistTicker, 新代码使用 UserWatchlist
WatchlistTicker = UserWatchlist
