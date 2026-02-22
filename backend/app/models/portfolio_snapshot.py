"""
PortfolioSnapshot — 每日盯市净值快照
"""
import uuid
from datetime import datetime, date

from sqlalchemy import Column, Float, Integer, Date, DateTime
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import Base


class PortfolioSnapshot(Base):
    """投资组合每日快照 (后台跑批生成)"""
    __tablename__ = "portfolio_snapshots"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    snapshot_date = Column(Date, unique=True, nullable=False)
    cash_balance = Column(Float, nullable=False, default=0.0)
    positions_value = Column(Float, nullable=False, default=0.0)
    total_equity = Column(Float, nullable=False, default=0.0)
    position_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    def __repr__(self):
        return f"<Snapshot {self.snapshot_date} equity=${self.total_equity:.2f}>"
