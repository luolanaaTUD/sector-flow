"""Idempotent upsert of collected rows into the database."""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.fund_flow import Sector, SectorFundFlowMinute

logger = logging.getLogger(__name__)


def upsert_rows(rows: list[dict[str, Any]]) -> int:
    """Insert rows, ignoring duplicates (UNIQUE constraint on date+ts+sector).

    Returns number of rows inserted.
    """
    if not rows:
        return 0

    inserted = 0
    db: Session = SessionLocal()
    try:
        dialect_name = db.bind.dialect.name if db.bind else "sqlite"
        sector_map: dict[str, int] = {}
        for row in rows:
            sector_name = row["sector_name"]
            sector_type = row["sector_type"]

            if sector_name not in sector_map:
                if dialect_name == "postgresql":
                    sector_stmt = (
                        postgresql_insert(Sector)
                        .values(name=sector_name, sector_type=sector_type)
                        .on_conflict_do_update(
                            index_elements=["name"],
                            set_={"sector_type": sector_type},
                        )
                    )
                else:
                    sector_stmt = (
                        sqlite_insert(Sector)
                        .values(name=sector_name, sector_type=sector_type)
                        .on_conflict_do_update(
                            index_elements=["name"],
                            set_={"sector_type": sector_type},
                        )
                    )
                db.execute(sector_stmt)
                sector_id = db.execute(select(Sector.id).where(Sector.name == sector_name)).scalar_one()
                sector_map[sector_name] = sector_id

            sector_id = sector_map[sector_name]
            payload = {
                "trade_date": row["trade_date"],
                "ts": row["ts"],
                "sector_id": sector_id,
                "net_inflow_yi": row["net_inflow_yi"],
            }

            if dialect_name == "postgresql":
                stmt = (
                    postgresql_insert(SectorFundFlowMinute)
                    .values(**payload)
                    .on_conflict_do_update(
                        index_elements=["trade_date", "ts", "sector_id"],
                        set_={
                            "net_inflow_yi": row["net_inflow_yi"],
                        },
                    )
                )
            else:
                stmt = (
                    sqlite_insert(SectorFundFlowMinute)
                    .values(**payload)
                    .on_conflict_do_update(
                        index_elements=["trade_date", "ts", "sector_id"],
                        set_={
                            "net_inflow_yi": row["net_inflow_yi"],
                        },
                    )
                )
            db.execute(stmt)
            inserted += 1
        db.commit()
    except Exception as exc:
        db.rollback()
        logger.error("Upsert failed: %s", exc)
        inserted = 0
    finally:
        db.close()
    return inserted
