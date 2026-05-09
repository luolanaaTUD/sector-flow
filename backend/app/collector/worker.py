"""APScheduler-based collection worker.

Runs every minute during A-share trading hours:
  Morning:   09:30 – 11:30
  Afternoon: 13:00 – 15:00 (China Standard Time, UTC+8)
"""

from __future__ import annotations

import logging
import time
from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.collector.akshare_fetcher import fetch_concept_fund_flow, fetch_industry_fund_flow
from app.collector.persistence import upsert_rows
from app.config import settings

logger = logging.getLogger(__name__)

_scheduler: BackgroundScheduler | None = None


def _is_trading_time() -> bool:
    """Check if current CST time is within trading windows."""
    now = datetime.now()  # expects server clock in CST (UTC+8)
    h, m = now.hour, now.minute
    morning = (h == 9 and m >= 30) or (h == 10) or (h == 11 and m <= 30)
    afternoon = (h == 13) or (h == 14) or (h == 15 and m == 0)
    return morning or afternoon


def collect_once() -> None:
    """Single collection run – fetches all configured sector types and persists."""
    if not _is_trading_time():
        logger.debug("Outside trading hours, skipping collection.")
        return

    start = time.monotonic()
    total_inserted = 0
    errors = 0

    sector_types = settings.sector_type_list
    delay = settings.AKSHARE_REQUEST_DELAY

    for stype in sector_types:
        try:
            if stype == "industry":
                rows = fetch_industry_fund_flow(delay=delay)
            elif stype == "concept":
                rows = fetch_concept_fund_flow(delay=delay)
            else:
                logger.warning("Unknown sector type: %s", stype)
                continue

            n = upsert_rows(rows)
            total_inserted += n
            logger.info("Collected %s: %d rows", stype, n)
        except Exception as exc:
            logger.error("Collection error for %s: %s", stype, exc)
            errors += 1

    elapsed = time.monotonic() - start
    logger.info(
        "Collection round done in %.2fs – inserted %d rows, %d errors",
        elapsed,
        total_inserted,
        errors,
    )


def start_scheduler() -> None:
    global _scheduler
    if _scheduler is not None and _scheduler.running:
        logger.warning("Scheduler already running.")
        return

    _scheduler = BackgroundScheduler(timezone="Asia/Shanghai")

    # Run every minute during morning session (9:30–11:30)
    _scheduler.add_job(
        collect_once,
        CronTrigger(day_of_week="mon-fri", hour="9-11", minute="*", timezone="Asia/Shanghai"),
        id="collect_morning",
        replace_existing=True,
    )
    # Run every minute during afternoon session (13:00–15:00)
    _scheduler.add_job(
        collect_once,
        CronTrigger(day_of_week="mon-fri", hour="13-14", minute="*", timezone="Asia/Shanghai"),
        id="collect_afternoon",
        replace_existing=True,
    )
    # Catch 15:00 exactly
    _scheduler.add_job(
        collect_once,
        CronTrigger(day_of_week="mon-fri", hour="15", minute="0", timezone="Asia/Shanghai"),
        id="collect_close",
        replace_existing=True,
    )

    _scheduler.start()
    logger.info("APScheduler started with trading-hour jobs.")


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("APScheduler stopped.")
