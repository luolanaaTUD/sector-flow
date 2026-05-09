import logging
import threading
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.collector.akshare_fetcher import fetch_snapshot
from app.collector.persistence import upsert_rows
from app.database import get_db
from app.models.fund_flow import SectorFundFlowMinute
from app.services.fund_flow_service import get_sectors

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/sectors", tags=["sectors"])

_bootstrap_lock = threading.Lock()
_bootstrapped = False


def _bootstrap_sectors_if_empty(db: Session) -> None:
    """If the DB has no sectors at all, trigger a live AkShare snapshot in the background."""
    global _bootstrapped
    if _bootstrapped:
        return

    count = db.execute(select(func.count()).select_from(SectorFundFlowMinute)).scalar_one()
    if count > 0:
        _bootstrapped = True
        return

    # Only one thread does the bootstrap; others skip.
    if not _bootstrap_lock.acquire(blocking=False):
        return

    def _run():
        global _bootstrapped
        try:
            logger.info("DB is empty — bootstrapping sector list from AkShare…")
            total = 0
            for stype in ("industry", "concept"):
                rows = fetch_snapshot(stype, delay=3.0)
                if rows:
                    n = upsert_rows(rows)
                    total += n
                    logger.info("Bootstrap: upserted %d %s rows", n, stype)
            logger.info("Bootstrap complete (%d total rows)", total)
            _bootstrapped = True
        except Exception as exc:
            logger.error("Bootstrap failed: %s", exc)
        finally:
            _bootstrap_lock.release()

    t = threading.Thread(target=_run, daemon=True, name="sector-bootstrap")
    t.start()


@router.get("")
def list_sectors(
    sector_type: Optional[str] = Query(None, description="Filter by type: industry | concept"),
    db: Session = Depends(get_db),
):
    """Return all known sector names with last update timestamp.

    On first call when the DB is empty, a background AkShare snapshot is
    triggered automatically so the list is populated on startup.
    """
    _bootstrap_sectors_if_empty(db)
    sectors = get_sectors(db, sector_type=sector_type)
    return {"code": 200, "data": sectors, "total": len(sectors)}
