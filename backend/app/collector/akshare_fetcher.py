"""同花顺 (AkShare) intraday snapshot fetcher.

Uses ``stock_fund_flow_industry`` / ``stock_fund_flow_concept`` with ``symbol="即时"``
(data.10jqka.com.cn).  Table columns: **行业**, **净额** (亿元).

Longer-horizon views are built from data persisted by the collector (same DB rows), not
from a separate upstream history API.
"""

from __future__ import annotations

import logging
import time
from datetime import date, datetime
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)

_COL_THS_NAME = "行业"
_COL_THS_NET = "净额"


def _ths_net_to_yi(value) -> Optional[float]:
    """Parse 同花顺 净额 → 亿元 float (table values are 亿-scale)."""
    try:
        if value is None:
            return None
        if isinstance(value, str):
            s = value.strip().replace(",", "")
            if s.endswith("亿"):
                s = s[:-1].strip()
            v = float(s)
        else:
            v = float(value)
        if pd.isna(v):
            return None
        return round(v, 4)
    except (TypeError, ValueError):
        return None


def _infer_trade_date() -> date:
    """Best-effort session date (weekend → last weekday for A-share)."""
    today = datetime.now()
    weekday = today.weekday()
    if weekday == 5:
        return (today - pd.Timedelta(days=1)).date()
    if weekday == 6:
        return (today - pd.Timedelta(days=2)).date()
    return today.date()


def _snapshot_ts(trade_date: date) -> datetime:
    """Snapshot timestamp: live clock in session, else EOD 15:00."""
    now = datetime.now()
    h, m = now.hour, now.minute
    in_morning = (h == 9 and m >= 30) or (10 <= h <= 10) or (h == 11 and m <= 30)
    in_afternoon = (13 <= h <= 14) or (h == 15 and m == 0)
    if in_morning or in_afternoon:
        return now.replace(second=0, microsecond=0)
    return datetime(trade_date.year, trade_date.month, trade_date.day, 15, 0, 0)


def _normalize_ths_snapshot(df: pd.DataFrame, sector_type: str) -> list[dict]:
    if df is None or df.empty:
        return []
    if _COL_THS_NAME not in df.columns or _COL_THS_NET not in df.columns:
        logger.error("THS snapshot missing columns: %s", list(df.columns))
        return []
    trade_date = _infer_trade_date()
    ts = _snapshot_ts(trade_date)
    rows = []
    for _, row in df.iterrows():
        name = str(row.get(_COL_THS_NAME, "")).strip()
        if not name:
            continue
        yi = _ths_net_to_yi(row.get(_COL_THS_NET))
        rows.append(
            {
                "trade_date": trade_date,
                "ts": ts,
                "sector_name": name,
                "sector_type": sector_type,
                "net_inflow_yi": yi,
            }
        )
    return rows


def _fetch_ths_snapshot(sector_type: str) -> list[dict]:
    import akshare as ak

    if sector_type == "industry":
        df = ak.stock_fund_flow_industry(symbol="即时")
    elif sector_type == "concept":
        df = ak.stock_fund_flow_concept(symbol="即时")
    else:
        raise ValueError(f"Unknown sector_type: {sector_type!r}. Use 'industry' or 'concept'.")
    return _normalize_ths_snapshot(df, sector_type=sector_type)


def fetch_snapshot(sector_type: str, delay: float = 2.0) -> list[dict]:
    """Fetch latest fund-flow snapshot for industry or concept (同花顺 only)."""
    if sector_type not in ("industry", "concept"):
        raise ValueError(f"Unknown sector_type: {sector_type!r}. Use 'industry' or 'concept'.")
    try:
        rows = _fetch_ths_snapshot(sector_type)
        logger.info("Fetched %d %s sectors from THS (10jqka)", len(rows), sector_type)
        return rows
    except Exception as exc:
        logger.error("THS snapshot failed for %s: %s", sector_type, exc)
        return []
    finally:
        time.sleep(delay)


def fetch_industry_fund_flow(delay: float = 2.0) -> list[dict]:
    return fetch_snapshot("industry", delay=delay)


def fetch_concept_fund_flow(delay: float = 2.0) -> list[dict]:
    return fetch_snapshot("concept", delay=delay)
