from datetime import date, datetime

from sqlalchemy import (
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.database import Base


class Sector(Base):
    """Normalized sector dimension."""

    __tablename__ = "sectors"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(128), nullable=False, unique=True)
    sector_type = Column(String(32), nullable=False, default="industry")  # industry | concept
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class SectorFundFlowMinute(Base):
    """One row per (trade_date, ts, sector_id) – idempotent upserts keep it clean."""

    __tablename__ = "sector_fund_flow_minute"

    id = Column(Integer, primary_key=True, autoincrement=True)
    trade_date = Column(Date, nullable=False)
    ts = Column(DateTime, nullable=False)           # full datetime for sorting
    sector_id = Column(Integer, ForeignKey("sectors.id", ondelete="RESTRICT"), nullable=False)
    net_inflow_yi = Column(Float, nullable=True)    # 净流入 亿元
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    sector = relationship("Sector")

    __table_args__ = (
        UniqueConstraint("trade_date", "ts", "sector_id", name="uq_date_slot_sector"),
        Index("idx_date_sector_time", "trade_date", "sector_id", "ts"),
        Index("idx_ts_sector", "ts", "sector_id"),
    )
