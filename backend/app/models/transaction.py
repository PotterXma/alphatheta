"""
TransactionLedger — 每笔资金流水记录
"""
import uuid
import enum
from datetime import datetime

from sqlalchemy import Column, String, Float, Integer, Enum, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import Base


class LegType(str, enum.Enum):
    """交易腿类型"""
    OPEN = "open"
    CLOSE = "close"
    ROLL_CLOSE = "roll_close"
    ROLL_OPEN = "roll_open"


class TransactionLedger(Base):
    """交易流水账本"""
    __tablename__ = "transaction_ledger"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id = Column(UUID(as_uuid=True), nullable=False)
    ticker = Column(String(16), nullable=False)
    leg_type = Column(Enum(LegType, name="legtype"), nullable=False)
    quantity = Column(Integer, nullable=False, default=1)
    price = Column(Float, nullable=False)
    net_amount = Column(Float, nullable=False)  # quantity × price × 100 (合约乘数)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    def __repr__(self):
        return f"<Ledger {self.ticker} {self.leg_type.value} ${self.net_amount:.2f}>"
