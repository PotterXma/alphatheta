"""
订单模型 — 不可变账本 (Immutable Ledger)

设计要点:
1. 表名 orders_master — 策略级容器 (一个 Iron Condor = 1 orders_master + 4 order_legs)
2. user_id FK — 多租户隔离
3. 价格字段使用 Numeric(12,4) — 金融精度
4. 禁止物理 DELETE — 取消通过 status='canceled' 实现
5. 状态机: PENDING → SUBMITTED → PARTIAL/FILLED/REJECTED/CANCELED/EXPIRED
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class OrderStatus(str, enum.Enum):
    PENDING = "pending"
    SUBMITTED = "submitted"
    PARTIAL = "partial"
    FILLED = "filled"
    CANCELED = "canceled"
    REJECTED = "rejected"
    EXPIRED = "expired"


# 合法状态流转表
VALID_TRANSITIONS: dict[OrderStatus, set[OrderStatus]] = {
    OrderStatus.PENDING: {OrderStatus.SUBMITTED, OrderStatus.CANCELED},
    OrderStatus.SUBMITTED: {
        OrderStatus.FILLED, OrderStatus.PARTIAL,
        OrderStatus.REJECTED, OrderStatus.CANCELED,
    },
    OrderStatus.PARTIAL: {OrderStatus.FILLED, OrderStatus.CANCELED},
    OrderStatus.FILLED: set(),      # 终态
    OrderStatus.REJECTED: set(),    # 终态
    OrderStatus.CANCELED: set(),    # 终态
    OrderStatus.EXPIRED: set(),     # 终态
}


class InvalidStateTransition(Exception):
    """非法状态流转异常"""
    def __init__(self, current: OrderStatus, target: OrderStatus):
        self.current = current
        self.target = target
        super().__init__(f"Invalid transition: {current.value} → {target.value}")


class Order(Base):
    """
    主订单表 (策略级)

    ⚠️ 不可变账本原则: 禁止 DELETE。取消 = status 设为 CANCELED。
    """
    __tablename__ = "orders_master"

    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.user_id", ondelete="RESTRICT"),
        nullable=False, index=True,
    )
    strategy_name: Mapped[str] = mapped_column(
        String(64), nullable=False,
        comment="策略标识: PMCC, Iron_Condor, Naked_Put, Covered_Call",
    )
    status: Mapped[OrderStatus] = mapped_column(
        Enum(OrderStatus), nullable=False, default=OrderStatus.PENDING, index=True,
    )
    net_premium: Mapped[float] = mapped_column(
        Numeric(12, 4), nullable=False, default=0,
        comment="整体净权利金 (正=收取, 负=支付)",
    )
    total_cost: Mapped[float] = mapped_column(
        Numeric(12, 4), nullable=False, default=0,
        comment="总成本 (资金占用)",
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

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
    filled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    canceled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )

    # ── Relationships ──
    legs = relationship("OrderLeg", back_populates="order", cascade="all, delete-orphan")

    def transition(self, target: OrderStatus) -> None:
        """严格状态机流转，非法流转抛异常"""
        if target not in VALID_TRANSITIONS.get(self.status, set()):
            raise InvalidStateTransition(self.status, target)
        self.status = target

    def __repr__(self) -> str:
        return f"<Order {self.order_id} [{self.strategy_name}] {self.status.value}>"
