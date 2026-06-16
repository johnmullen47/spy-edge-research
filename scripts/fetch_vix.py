#!/usr/bin/env python3
"""Fetch CBOE daily VIX / VIX9D / VIX3M history and write a normalized CSV.

CBOE publishes free daily index history (back to 1990 for VIX). Polygon's free
tier is NOT entitled to index (`I:VIX`) data, so CBOE is the source. The output is
a single normalized daily CSV consumed by the research pipeline for the
MIM-Baltussen / F3 regime gates:

    data/raw/vix_daily.csv  ->  columns: date, vix, vix9d, vix3m  (close levels)

``vix9d`` / ``vix3m`` are the term-structure sub-indices (NaN before their CBOE
start dates: VIX9D 2011, VIX3M 2009). Research-only; no order routing.
"""

from __future__ import annotations

import argparse
import io
from pathlib import Path

import pandas as pd
import urllib.request

CBOE_BASE = "https://cdn.cboe.com/api/global/us_indices/daily_prices"
SYMBOLS = {"vix": "VIX", "vix9d": "VIX9D", "vix3m": "VIX3M"}


def _fetch_close(symbol: str, *, timeout: int = 60) -> pd.Series:
    url = f"{CBOE_BASE}/{symbol}_History.csv"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 (trusted CBOE host)
        raw = resp.read().decode("utf-8")
    df = pd.read_csv(io.StringIO(raw))
    df.columns = [c.strip().lower() for c in df.columns]
    df["date"] = pd.to_datetime(df["date"]).dt.date
    return pd.Series(df["close"].to_numpy(), index=df["date"], name=symbol)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="data/raw/vix_daily.csv")
    args = parser.parse_args()

    series = {name: _fetch_close(sym) for name, sym in SYMBOLS.items()}
    frame = pd.DataFrame(series).sort_index()
    frame.index.name = "date"
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    frame.reset_index().to_csv(out, index=False)
    print(f"wrote {out} rows={len(frame)} range={frame.index.min()}..{frame.index.max()}")
    print(frame.tail(3).to_string())


if __name__ == "__main__":
    main()
