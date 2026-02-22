"""
持仓模型 — 活跃持仓状态机

⚠️ 不可变原则: 本表绝不使用 DELETE 操作。
   平仓逻辑: 提交反向订单 → 系统自动将 net_quantity 归零。
   net_quantity = 0 表示已平仓, 保留历史记录用于审计与 P&L 计算。
   正数 = 多头 (Long), 负数 = 空头 (Short/Written)
"""

import uuid
from datetime import date, datetime

from sqlalchemy import (
    Date, DateTime, Enum, ForeignKey, Integer,
    Numeric, String, UniqueConstraint, func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.order_leg import OptionRight


class Position(Base):
    __tablename__ = "user_positions"
    __table_args__ = (
        UniqueConstraint("user_id", "occ_symbol", name="uq_user_position"),
    )

    position_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.user_id", ondelete="RESTRICT"),
        nullable=False, index=True,
    )
    occ_symbol: Mapped[str] = mapped_column(
        String(32), nullable=False, index=True,
        comment="OCC 合约代码",
    )
    underlying: Mapped[str] = mapped_column(
        String(10), nullable=False, index=True,
        comment="标的 Ticker (冗余, 方便按标的查询)",
    )
    right_type: Mapped[OptionRight | None] = mapped_column(
        Enum(OptionRight), nullable=True,
        comment="CALL/PUT (NULL = 股票持仓)",
    )
    strike_price: Mapped[float | None] = mapped_column(
        Numeric(12, 4), nullable=True,
    )
    expiration_date: Mapped[date | None] = mapped_column(
        Date, nullable=True,
    )

    # ── 持仓核心字段 — 悲观锁的锁定目标 ──
    net_quantity: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0,
        comment="正=多头, 负=空头, 0=已平仓",
    )
    average_cost: Mapped[float] = mapped_column(
        Numeric(12, 4), nullable=False, default=0,
    )
    realized_pnl: Mapped[float] = mapped_column(
        Numeric(14, 4), nullable=False, default=0,
    )

    # 关联开仓订单 (可追溯)
    opening_order_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("orders_master.order_id"),
        nullable=True,
    )

    # 环境标记 (兼容旧代码)
    env_mode: Mapped[str] = mapped_column(
        String(8), nullable=False, default="paper",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(),
    )

    def __repr__(self) -> str:
        return f"<Position {self.underlying} qty={self.net_quantity}>"
