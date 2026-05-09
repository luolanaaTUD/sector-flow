"""Quick manual check for EastMoney (EM) sector main-flow fields.

Run:
  uv run python test/em_mode_check.py
"""

from __future__ import annotations

import sys
import time
from typing import Callable

import akshare as ak
import pandas as pd


def _run_with_retries(fetcher: Callable[[], pd.DataFrame], retries: int = 3, delay_s: float = 2.0) -> pd.DataFrame:
    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            return fetcher()
        except Exception as exc:  # pragma: no cover - network variance
            last_error = exc
            print(f"[attempt {attempt}/{retries}] fetch failed: {type(exc).__name__}: {exc}")
            if attempt < retries:
                time.sleep(delay_s)
    raise RuntimeError(f"Fetch failed after {retries} attempts: {last_error}") from last_error


def _check_sector_type(sector_type: str) -> int:
    print(f"\n=== Checking EM sector type: {sector_type} ===")
    df = _run_with_retries(
        lambda: ak.stock_sector_fund_flow_rank(indicator="今日", sector_type=sector_type),
        retries=3,
        delay_s=2.0,
    )

    expected = [
        "名称",
        "今日主力净流入-净额",
        "今日主力净流入-净占比",
        "今日超大单净流入-净额",
        "今日大单净流入-净额",
        "今日中单净流入-净额",
        "今日小单净流入-净额",
    ]
    missing = [c for c in expected if c not in df.columns]

    print(f"rows: {len(df)}")
    print(f"columns: {list(df.columns)}")
    if missing:
        print(f"[ERROR] missing columns: {missing}")
        return 1

    if not df.empty:
        print("sample row:", df.head(1).to_dict("records")[0])
    print("[OK] main-flow columns present")
    return 0


def main() -> int:
    status = 0
    for sector_type in ("行业资金流", "概念资金流"):
        try:
            status |= _check_sector_type(sector_type)
        except Exception as exc:  # pragma: no cover - network variance
            print(f"[ERROR] {sector_type} check failed: {type(exc).__name__}: {exc}")
            status = 1
    return status


if __name__ == "__main__":
    raise SystemExit(main())
