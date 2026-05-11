#!/usr/bin/env python3
"""Compare AkShare data sources for A-share **sector / board** intraday-style fund flow.

What this tests (AkShare 1.18+):

  **同花顺 (10jqka)** — same family as production ``akshare_fetcher``:
  - ``stock_fund_flow_industry(symbol="即时")``  (column 行业 / 净额, 净额 in 亿元)
  - ``stock_fund_flow_concept(symbol="即时")``   (概念, 净额 in 亿元)

  **东方财富 (East Money)** — board ranking, ``indicator="今日"`` ≈ session cumulative:
  - ``stock_sector_fund_flow_rank(indicator="今日", sector_type="行业资金流")``
  - ``stock_sector_fund_flow_rank(indicator="今日", sector_type="概念资金流")``
  - ``stock_sector_fund_flow_rank(indicator="今日", sector_type="地域资金流")``  (optional)

EM ``今日主力净流入-净额`` is treated as **yuan** and converted to 亿元 (÷1e8), matching THS scale.

**Not** included (different granularity / not sector intraday board ranking):

- ``stock_fund_flow_individual`` (stocks)
- ``stock_main_fund_flow`` / ``stock_individual_fund_flow_rank`` (stocks)
- ``stock_market_fund_flow`` (whole market)
- THS ``3日/5日/...`` (not intraday)

Run (from ``backend/``)::

  uv run python scripts/compare_akshare_intraday_sources.py

During **trading hours (Asia/Shanghai)** overlap and value checks are most meaningful.
"""

from __future__ import annotations

import argparse
import json
import time
from dataclasses import asdict, dataclass
from typing import Any, Callable

import akshare as ak
import pandas as pd

# East Money 主力净流入 is in 元; convert to 亿元 to align with 同花顺 净额
YUAN_PER_YI = 100_000_000.0


@dataclass
class SourceResult:
    name: str
    ok: bool
    error: str | None
    seconds: float
    row_count: int
    columns: list[str]
    # name -> net 亿元
    series: dict[str, float]


def _strip_yi(s) -> float | None:
    if s is None:
        return None
    if isinstance(s, (int, float)) and not isinstance(s, bool):
        if pd.isna(s):
            return None
        return round(float(s), 6)
    s = str(s).strip().replace(",", "")
    if s.endswith("亿"):
        s = s[:-1].strip()
    try:
        v = float(s)
    except ValueError:
        return None
    if pd.isna(v):
        return None
    return round(v, 6)


def ths_to_series(df: pd.DataFrame, name_col: str, net_col: str) -> dict[str, float]:
    if df is None or df.empty or name_col not in df.columns or net_col not in df.columns:
        return {}
    out: dict[str, float] = {}
    for _, row in df.iterrows():
        name = str(row.get(name_col, "")).strip()
        if not name:
            continue
        v = _strip_yi(row.get(net_col))
        if v is not None:
            out[name] = v
    return out


def em_today_to_series(df: pd.DataFrame) -> dict[str, float]:
    if df is None or df.empty:
        return {}
    if "名称" not in df.columns or "今日主力净流入-净额" not in df.columns:
        return {}
    s = pd.to_numeric(df["今日主力净流入-净额"], errors="coerce")
    names = df["名称"].astype(str).str.strip()
    out: dict[str, float] = {}
    for n, y in zip(names, s):
        if not n or pd.isna(y):
            continue
        out[n] = round(float(y) / YUAN_PER_YI, 6)
    return out


def fetch_with_time(
    name: str,
    fn: Callable[[], pd.DataFrame],
    normalize: Callable[[pd.DataFrame], dict[str, float]],
    *,
    retries: int = 3,
    retry_delay_s: float = 2.0,
) -> SourceResult:
    t0 = time.perf_counter()
    err: str | None = None
    df: pd.DataFrame | None = None
    for attempt in range(1, retries + 1):
        try:
            df = fn()
            break
        except Exception as exc:  # pragma: no cover - network
            err = f"{type(exc).__name__}: {exc}"
            if attempt < retries:
                time.sleep(retry_delay_s)
    else:
        return SourceResult(
            name=name,
            ok=False,
            error=err,
            seconds=time.perf_counter() - t0,
            row_count=0,
            columns=[],
            series={},
        )
    elapsed = time.perf_counter() - t0
    cols = list(df.columns) if df is not None else []
    series = normalize(df) if df is not None else {}
    return SourceResult(
        name=name,
        ok=True,
        error=None,
        seconds=elapsed,
        row_count=len(df) if df is not None else 0,
        columns=cols,
        series=series,
    )


def jaccard_names(a: dict[str, float], b: dict[str, float]) -> float:
    sa, sb = set(a), set(b)
    if not sa and not sb:
        return 1.0
    u = sa | sb
    if not u:
        return 0.0
    return len(sa & sb) / len(u)


def compare_pairs(sa: dict[str, float], sb: dict[str, float]) -> dict[str, float | int]:
    keys = sorted(set(sa) & set(sb))
    if not keys:
        return {"overlap_count": 0, "mae_yi": float("nan"), "spearman": float("nan")}
    va = pd.Series([sa[k] for k in keys])
    vb = pd.Series([sb[k] for k in keys])
    mae = float((va - vb).abs().mean())
    if len(keys) < 3:
        spearman = float("nan")
    else:
        # Spearman = Pearson on ranks; avoids optional scipy dependency
        spearman = float(va.rank().corr(vb.rank()))
    return {"overlap_count": len(keys), "mae_yi": mae, "spearman": spearman}


INTRADAY_SOURCES_BASE: list[tuple[str, Callable[[], pd.DataFrame], Callable[[pd.DataFrame], dict[str, float]]]] = [
    (
        "ths_industry_即时",
        lambda: ak.stock_fund_flow_industry(symbol="即时"),
        lambda df: ths_to_series(df, "行业", "净额"),
    ),
    (
        "ths_concept_即时",
        lambda: ak.stock_fund_flow_concept(symbol="即时"),
        lambda df: ths_to_series(df, "行业", "净额"),
    ),
    (
        "em_sector_今日_行业资金流",
        lambda: ak.stock_sector_fund_flow_rank(indicator="今日", sector_type="行业资金流"),
        em_today_to_series,
    ),
    (
        "em_sector_今日_概念资金流",
        lambda: ak.stock_sector_fund_flow_rank(indicator="今日", sector_type="概念资金流"),
        em_today_to_series,
    ),
]

OPTIONAL_EM_REGION = (
    "em_sector_今日_地域资金流",
    lambda: ak.stock_sector_fund_flow_rank(indicator="今日", sector_type="地域资金流"),
    em_today_to_series,
)


def all_sources(include_em_region: bool) -> list[tuple[str, Callable[[], pd.DataFrame], Callable[[pd.DataFrame], dict[str, float]]]]:
    out = list(INTRADAY_SOURCES_BASE)
    if include_em_region:
        out.append(OPTIONAL_EM_REGION)
    return out


def run_all(delay_s: float, include_em_region: bool = False, retries: int = 3) -> list[SourceResult]:
    results: list[SourceResult] = []
    for name, fn, norm in all_sources(include_em_region):
        results.append(fetch_with_time(name, fn, norm, retries=retries, retry_delay_s=min(delay_s, 3.0)))
        if delay_s > 0:
            time.sleep(delay_s)
    return results


def print_report(results: list[SourceResult]) -> None:
    print("\n=== Per-source ===")
    for r in results:
        status = "OK" if r.ok else "FAIL"
        print(f"  [{status}] {r.name}  rows={r.row_count}  time={r.seconds:.2f}s")
        if not r.ok:
            print(f"        {r.error}")
        elif r.series:
            top = sorted(r.series.items(), key=lambda x: abs(x[1]), reverse=True)[:5]
            sample = ", ".join(f"{n}:{v:.4f}" for n, v in top)
            print(f"        top|net|(亿元): {sample}")

    ok_results = [r for r in results if r.ok and r.series]
    name_by_idx = {r.name: r for r in ok_results}

    pairs_to_compare = [
        ("ths_industry_即时", "em_sector_今日_行业资金流"),
        ("ths_concept_即时", "em_sector_今日_概念资金流"),
    ]

    print("\n=== Cross-source (same sector type: THS 即时 vs EM 今日) ===")
    for a, b in pairs_to_compare:
        if a not in name_by_idx or b not in name_by_idx:
            print(f"  skip {a} vs {b}: missing OK result")
            continue
        sa, sb = name_by_idx[a].series, name_by_idx[b].series
        jc = jaccard_names(sa, sb)
        cmpd = compare_pairs(sa, sb)
        print(f"  {a}  vs  {b}")
        print(f"    name Jaccard (overlap/union): {jc:.4f}")
        print(f"    overlap_count: {cmpd['overlap_count']}  MAE(亿元): {cmpd['mae_yi']:.6f}  Spearman: {cmpd['spearman']}")

    print("\n=== How to pick \"best\" ===")
    print("  - Lower latency + stable OK → better for collectors.")
    print("  - Higher THS↔EM Spearman & lower MAE on overlapping names → consistent boards.")
    print("  - Production uses 同花顺 即时 (ths_*); EM is useful as cross-check or fallback.")
    print("  - Definitions differ slightly (即时 snapshot vs 今日 cumulative); exact match is not expected.\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare AkShare sector intraday fund-flow sources.")
    parser.add_argument(
        "--delay",
        type=float,
        default=2.0,
        help="Seconds between HTTP-heavy AkShare calls (default 2).",
    )
    parser.add_argument(
        "--with-em-region",
        action="store_true",
        help="Also fetch East Money 地域资金流 (extra request; sometimes flaky).",
    )
    parser.add_argument(
        "--retries",
        type=int,
        default=3,
        help="Retries per source on network failure (default 3).",
    )
    parser.add_argument(
        "--json",
        type=str,
        default="",
        help="Optional path to write JSON summary (sources + pairwise stats).",
    )
    args = parser.parse_args()

    results = run_all(delay_s=args.delay, include_em_region=args.with_em_region, retries=max(1, args.retries))

    print_report(results)

    if args.json:
        payload: dict[str, Any] = {
            "sources": [asdict(r) for r in results],
            "pairs": [],
        }
        ok_map = {r.name: r.series for r in results if r.ok}
        for a, b in [
            ("ths_industry_即时", "em_sector_今日_行业资金流"),
            ("ths_concept_即时", "em_sector_今日_概念资金流"),
        ]:
            if a in ok_map and b in ok_map:
                payload["pairs"].append(
                    {
                        "a": a,
                        "b": b,
                        "jaccard": jaccard_names(ok_map[a], ok_map[b]),
                        **compare_pairs(ok_map[a], ok_map[b]),
                    }
                )
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        print(f"Wrote {args.json}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
