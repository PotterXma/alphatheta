"""Tick 数据模型 — TimescaleDB Hypertable"""

from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class TickData(Base):
    """
    时序行情数据 — TimescaleDB hypertable
    创建后需执行:
      SELECT create_hypertable('tick_data', 'time', chunk_time_interval => INTERVAL '7 days');
    """

    __tablename__ = "tick_data"

    time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), primary_key=True, server_default=func.now()
    )
    ticker: Mapped[str] = mapped_column(String(16), primary_key=True, index=True)
    bid: Mapped[float] = mapped_column(Float, nullable=False)
    ask: Mapped[float] = mapped_column(Float, nullable=False)
    last: Mapped[float] = mapped_column(Float, nullable=False)
    volume: Mapped[int] = mapped_column(Integer, nullable=True)
