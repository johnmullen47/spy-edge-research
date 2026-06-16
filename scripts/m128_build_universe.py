#!/usr/bin/env python3
"""M128 step 1A.3 — build the no-lookahead, survivorship-controlled stock universe.

Inputs:
  data/raw/m128/assets_roster.json         (symbol -> name/status/exchange)
  data/raw/m128/daily_dollar_volume.csv    (symbol, ym, sum_dv, n_days)

Rule (frozen in M128_PREREG.yaml):
  * Rebalance MONTHLY. Membership for month r uses ONLY data from the 12 calendar
    months strictly before r (months r-12 .. r-1) -> no lookahead.
  * ADV = sum(close*volume) / sum(trading_days) over that trailing window.
  * Require >= MIN_TRAILING_DAYS days of history in the window (drop thin/new names).
  * Exclude ETFs/ETNs/funds (mechanical name-token filter + explicit high-volume set);
    ETFs are M128 NEGATIVE CONTROLS, not members of the stock cross-section.
  * Rank surviving stocks by ADV desc; take TOP_N.
  * First rebalance = 2017-01 (2016 is the burn-in lookback). Last = 2026-06.

Outputs:
  data/raw/m128/universe_membership.csv   (rebalance_month, symbol, rank, adv_usd, n_days)
  data/raw/m128/universe_summary.json     (counts, turnover, distinct names, exits)

NOT a cross-sectional result; universe construction / data inventory (allowed pre-freeze).
Stdlib + pandas. Research-only.
"""
from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from pathlib import Path

import pandas as pd

TOP_N = 150
MIN_TRAILING_DAYS = 200          # ~10 months of history required in the 12m window
FIRST_REBAL = "2017-01"
LAST_REBAL = "2026-06"

# Mechanical ETF/fund name tokens (uppercased name match). Conservative: avoids generic
# 'TRUST'/'FUND' alone so operating companies and REITs are retained.
ETF_NAME_TOKENS = [
    "ETF", "ETN", "ISHARES", "SPDR", "POWERSHARES", "PROSHARES", "DIREXION",
    "INVESCO", "WISDOMTREE", "XTRACKERS", "GLOBAL X", "GLOBALX", "FIRST TRUST",
    "VANECK", "VAN ECK", "KRANESHARES", "GRANITESHARES", "VANGUARD", "ARK ",
    "AMPLIFY", "SPROTT", "ABRDN", "ULTRAPRO", "ULTRASHORT", "LEVERAGED",
    "INVERSE", " 2X ", " 3X ", "INDEX FUND", "INDEX TRUST", "BOND FUND",
    "CLOSED END", "CLOSED-END", "INCOME FUND", "MUNICIPAL", "PREFERRED",
]
# Explicit high-volume ETF/ETN tickers that may carry plain names.
ETF_SYMBOLS = {
    "SPY", "QQQ", "QQQM", "IWM", "DIA", "VOO", "VTI", "IVV", "EEM", "EFA", "VEA",
    "VWO", "AGG", "BND", "TLT", "IEF", "SHY", "HYG", "LQD", "GLD", "SLV", "GDX",
    "USO", "UNG", "XLF", "XLK", "XLE", "XLV", "XLI", "XLY", "XLP", "XLU", "XLB",
    "XLRE", "XLC", "SMH", "SOXX", "XBI", "IBB", "KRE", "KWEB", "FXI", "EWZ",
    "EWJ", "INDA", "ARKK", "ARKG", "ARKW", "TQQQ", "SQQQ", "SOXL", "SOXS",
    "UVXY", "VXX", "UVIX", "SVIX", "VIXY", "TNA", "TZA", "SPXL", "SPXS", "UPRO",
    "SDOW", "UDOW", "SH", "PSQ", "SDS", "SSO", "QLD", "TMF", "TMV", "LABU",
    "LABD", "NUGT", "DUST", "JNUG", "JDST", "BOIL", "KOLD", "FAS", "FAZ",
    "TECL", "TECS", "DRN", "WEBL", "BITO", "BITX", "ETHU", "MSTU", "MSTX",
    "NVDL", "TSLL", "TSLQ", "CONL", "GBTC", "IBIT", "FBTC", "VXUS", "SCHD",
    "JEPI", "JEPQ", "DVY", "VIG", "VYM", "RSP", "MDY", "IJR", "IJH", "VB",
    "VUG", "VTV", "IWF", "IWD", "MTUM", "QUAL", "USMV", "VLUE", "SIZE",
}


def is_etf(symbol: str, name: str | None) -> bool:
    if symbol in ETF_SYMBOLS:
        return True
    if not name:
        return False
    up = " " + name.upper() + " "
    return any(tok in up for tok in ETF_NAME_TOKENS)


def month_range(first: str, last: str) -> list[str]:
    out, (y, m) = [], (int(first[:4]), int(first[5:7]))
    ly, lm = int(last[:4]), int(last[5:7])
    while (y, m) <= (ly, lm):
        out.append(f"{y:04d}-{m:02d}")
        m += 1
        if m == 13:
            y, m = y + 1, 1
    return out


def trailing_months(rebal: str, n: int = 12) -> list[str]:
    y, m = int(rebal[:4]), int(rebal[5:7])
    out = []
    for _ in range(n):
        m -= 1
        if m == 0:
            y, m = y - 1, 12
        out.append(f"{y:04d}-{m:02d}")
    return out


def main() -> None:
    base = Path("data/raw/m128")
    roster = json.loads((base / "assets_roster.json").read_text())["roster"]
    dv = pd.read_csv(base / "daily_dollar_volume.csv", dtype={"ym": str})

    # symbol -> {ym -> (sum_dv, n_days)}
    by_sym: dict[str, dict[str, tuple[float, int]]] = defaultdict(dict)
    for r in dv.itertuples(index=False):
        by_sym[r.symbol][r.ym] = (float(r.sum_dv), int(r.n_days))

    stock_syms = {s for s in by_sym if not is_etf(s, (roster.get(s) or {}).get("name"))}
    etf_excluded = sorted(set(by_sym) - stock_syms)

    rebals = month_range(FIRST_REBAL, LAST_REBAL)
    rows = []
    members_by_month: dict[str, set[str]] = {}
    for rebal in rebals:
        window = set(trailing_months(rebal, 12))
        scored = []
        for sym in stock_syms:
            months = by_sym[sym]
            tot_dv = 0.0
            tot_days = 0
            for ym in window:
                if ym in months:
                    sdv, nd = months[ym]
                    tot_dv += sdv
                    tot_days += nd
            if tot_days >= MIN_TRAILING_DAYS:
                scored.append((tot_dv / tot_days, sym, tot_days))
        scored.sort(reverse=True)
        top = scored[:TOP_N]
        members_by_month[rebal] = {s for _, s, _ in top}
        for rank, (adv, sym, nd) in enumerate(top, start=1):
            rows.append(
                {"rebalance_month": rebal, "symbol": sym, "rank": rank,
                 "adv_usd": round(adv, 2), "n_days_trailing": nd}
            )

    out = pd.DataFrame(rows)
    out.to_csv(base / "universe_membership.csv", index=False)

    # Summary statistics
    distinct = sorted({r["symbol"] for r in rows})
    sizes = {m: len(s) for m, s in members_by_month.items()}
    turnovers = []
    prev = None
    for m in rebals:
        cur = members_by_month[m]
        if prev is not None and prev:
            churn = len(cur ^ prev) / (2 * len(prev))  # symmetric turnover fraction
            turnovers.append(churn)
        prev = cur
    # Delisting/exit exposure: of distinct names ever in-universe, how many are 'inactive'
    inactive_in_universe = [s for s in distinct if (roster.get(s) or {}).get("status") == "inactive"]
    # Names in-universe in their last membership month but gone afterward (proxy for exits)
    last_seen = {}
    for m in rebals:
        for s in members_by_month[m]:
            last_seen[s] = m
    exited_before_end = [s for s, m in last_seen.items() if m != LAST_REBAL]

    summary = {
        "top_n": TOP_N,
        "min_trailing_days": MIN_TRAILING_DAYS,
        "first_rebalance": FIRST_REBAL,
        "last_rebalance": LAST_REBAL,
        "n_rebalance_months": len(rebals),
        "universe_size_per_month_min": min(sizes.values()),
        "universe_size_per_month_max": max(sizes.values()),
        "universe_size_per_month_median": int(pd.Series(list(sizes.values())).median()),
        "distinct_symbols_ever": len(distinct),
        "mean_monthly_turnover_frac": round(sum(turnovers) / len(turnovers), 4) if turnovers else None,
        "etf_like_excluded_count": len(etf_excluded),
        "inactive_status_in_universe_count": len(inactive_in_universe),
        "inactive_status_in_universe_frac": round(len(inactive_in_universe) / len(distinct), 4),
        "names_exited_before_end_count": len(exited_before_end),
        "names_exited_before_end_frac": round(len(exited_before_end) / len(distinct), 4),
        "sample_top10_first_month": [r["symbol"] for r in rows if r["rebalance_month"] == rebals[0]][:10],
        "sample_top10_last_month": [r["symbol"] for r in rows if r["rebalance_month"] == LAST_REBAL][:10],
        "sample_inactive_in_universe": inactive_in_universe[:25],
    }
    (base / "universe_summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))
    print(f"\nWrote {len(rows)} membership rows; {len(distinct)} distinct symbols.")


if __name__ == "__main__":
    main()
