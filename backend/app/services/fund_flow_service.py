"""Query service for sector fund-flow data."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Optional
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.fund_flow import Sector, SectorFundFlowMinute
from app.services.time_axis import trading_minutes

_SHANGHAI = ZoneInfo("Asia/Shanghai")


def _to_shanghai_slot(ts) -> str:
    """Normalize DB timestamp to Shanghai wall-clock minute slot."""
    if ts.tzinfo is not None:
        ts = ts.astimezone(_SHANGHAI)
    elif not _is_trading_time(ts.hour, ts.minute):
        # Backward compatibility for previously persisted UTC-like naive rows.
        shifted = ts + timedelta(hours=8)
        if _is_trading_time(shifted.hour, shifted.minute):
            ts = shifted
    return ts.strftime("%H:%M:00")


def _is_trading_time(hour: int, minute: int) -> bool:
    morning = (hour == 9 and minute >= 30) or hour == 10 or (hour == 11 and minute <= 30)
    afternoon = hour == 13 or hour == 14 or (hour == 15 and minute == 0)
    return morning or afternoon


def get_sectors(db: Session, sector_type: Optional[str] = None) -> list[dict]:
    """Return distinct sector names with latest update time."""
    stmt = (
        select(
            Sector.name,
            Sector.sector_type,
            func.max(SectorFundFlowMinute.ts).label("last_updated"),
        )
        .join(Sector, Sector.id == SectorFundFlowMinute.sector_id)
        .group_by(Sector.name, Sector.sector_type)
        .order_by(Sector.sector_type, Sector.name)
    )
    if sector_type:
        stmt = stmt.where(Sector.sector_type == sector_type)

    rows = db.execute(stmt).all()
    return [
        {
            "name": r.name,
            "type": r.sector_type,
            "last_updated": r.last_updated.isoformat() if r.last_updated else None,
        }
        for r in rows
    ]


def get_intraday_series(
    db: Session,
    trade_date: date,
    sectors: list[str],
    max_sectors: int = 20,
) -> dict:
    """Return aligned time-series for requested sectors on the given date.

    Returns:
        {
          "timestamps": ["09:30:00", ...],
          "series": [{"name": "半导体", "data": [1.2, None, 3.1, ...]}, ...]
        }
    """
    sectors = sectors[:max_sectors]
    timestamps = trading_minutes(trade_date)

    if not sectors:
        return {"timestamps": timestamps, "series": []}

    rows = (
        db.execute(
            select(
                Sector.name,
                SectorFundFlowMinute.ts,
                SectorFundFlowMinute.net_inflow_yi,
            )
            .join(Sector, Sector.id == SectorFundFlowMinute.sector_id)
            .where(
                SectorFundFlowMinute.trade_date == trade_date,
                Sector.name.in_(sectors),
            )
            .order_by(Sector.name, SectorFundFlowMinute.ts)
        )
        .all()
    )

    # Build lookup: sector -> {time_slot: value}
    lookup: dict[str, dict[str, float | None]] = {s: {} for s in sectors}
    for row in rows:
        slot = _to_shanghai_slot(row.ts)
        lookup[row.name][slot] = row.net_inflow_yi

    series = []
    for sector in sectors:
        slot_map = lookup.get(sector, {})
        data = [slot_map.get(ts) for ts in timestamps]
        series.append({"name": sector, "data": data})

    return {"timestamps": timestamps, "series": series}


def get_ranking(db: Session, top_n: int = 10) -> dict:
    """Return latest-minute ranking by net_inflow_yi."""
    latest_ts_subq = select(func.max(SectorFundFlowMinute.ts)).scalar_subquery()

    rows = (
        db.execute(
            select(
                Sector.name,
                Sector.sector_type,
                SectorFundFlowMinute.net_inflow_yi,
                SectorFundFlowMinute.ts,
            )
            .join(Sector, Sector.id == SectorFundFlowMinute.sector_id)
            .where(SectorFundFlowMinute.ts == latest_ts_subq)
            .order_by(SectorFundFlowMinute.net_inflow_yi.desc())
        )
        .all()
    )

    all_rows = [
        {
            "sector_name": r.name,
            "sector_type": r.sector_type,
            "net_inflow_yi": r.net_inflow_yi,
            "ts": r.ts.isoformat() if r.ts else None,
        }
        for r in rows
    ]

    return {
        "inflow_top": all_rows[:top_n],
        "outflow_top": all_rows[-top_n:][::-1] if len(all_rows) >= top_n else list(reversed(all_rows)),
        "snapshot_ts": all_rows[0]["ts"] if all_rows else None,
    }
