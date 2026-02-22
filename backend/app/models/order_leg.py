"""
订单腿模型 — 期权合约级明细

设计要点:
1. 每条腿对应一个 OCC 标准化合约代码 (21 字符)
2. entry_greeks JSONB 快照开仓时 Greeks (Delta/Theta/IV)
3. trade_action (BUY/SELL) + option_right (CALL/PUT) 枚举
4. 数量/价格使用精确类型 (INT / Numeric)
"""

import enum
import uuid
from datetime import date, datetime

from sqlalchemy import (
    Date, DateTime, Enum, ForeignKey, Integer,
    Numeric, SmallInteger, String, func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class TradeAction(str, enum.Enum):
    BUY = "buy"
    SELL = "sell"


class OptionRight(str, enum.Enum):
    CALL = "call"
    PUT = "put"


class OrderLeg(Base):
    __tablename__ = "order_legs"

    leg_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
    )
    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("orders_master.order_id", ondelete="RESTRICT"),
        nullable=False, index=True,
    )
    leg_index: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, default=1,
        comment="腿序号 (1,2,3,4)",
    )

    # ⚠️ OCC 标准化合约代码 — 期权行业的"身份证"
    # 格式: "AAPL  270115C00250000" (标的6字符+到期日6位+C/P+行权价8位)
    occ_symbol: Mapped[str] = mapped_column(
        String(32), nullable=False, index=True,
        comment="OCC 标准化合约代码",
    )

    action: Mapped[TradeAction] = mapped_column(
        Enum(TradeAction), nullable=False,
    )
    right_type: Mapped[OptionRight] = mapped_column(
        Enum(OptionRight), nullable=False,
    )
    underlying: Mapped[str] = mapped_column(
        String(10), nullable=False, index=True,
        comment="标的 Ticker",
    )
    strike_price: Mapped[float] = mapped_column(
        Numeric(12, 4), nullable=False,
    )
    expiration_date: Mapped[date] = mapped_column(
        Date, nullable=False,
    )
    quantity: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1,
    )
    limit_price: Mapped[float | None] = mapped_column(
        Numeric(12, 4), nullable=True,
    )
    filled_price: Mapped[float | None] = mapped_column(
        Numeric(12, 4), nullable=True,
    )
    filled_quantity: Mapped[int | None] = mapped_column(
        Integer, default=0,
    )

    # 开仓时的 Greeks 快照
    # 格式: {"delta": -0.35, "gamma": 0.02, "theta": -0.15, "vega": 0.08, "iv": 0.28}
    entry_greeks: Mapped[dict | None] = mapped_column(
        JSONB, default=dict,
        comment="开仓时 Greeks 快照 (Delta/Gamma/Theta/Vega/IV)",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(),
    )

    # ── Relationship ──
    order = relationship("Order", back_populates="legs")

    def __repr__(self) -> str:
        return f"<Leg {self.action.value} {self.quantity}x {self.occ_symbol}>"
