"""Loader for the normalized daily VIX term-structure CSV (M122).

Reads the ``data/raw/vix_daily.csv`` produced by ``scripts/fetch_vix.py`` (CBOE
daily VIX / VIX9D / VIX3M close levels) into a per-date frame, plus convenience
accessors for the single-level VIX series (the MIM-Baltussen regime gate) and the
term-structure sub-indices (the F3 gate).

Research-only: descriptive regime inputs, no trade signal or authorization.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

VIX_COLUMNS = ("vix", "vix9d", "vix3m")


def load_vix_daily(path: str | Path) -> pd.DataFrame:
    """Load the normalized daily VIX CSV into a date-indexed frame.

    Returns a frame indexed by ``datetime.date`` with float columns ``vix``,
    ``vix9d``, ``vix3m`` (close levels). Missing sub-index values stay NaN; the
    downstream regime gates treat NaN as "gate inactive".
    """
    raw = pd.read_csv(path)
    raw.columns = [c.strip().lower() for c in raw.columns]
    if "date" not in raw.columns:
        raise ValueError("vix_daily csv must have a 'date' column")
    index = pd.to_datetime(raw["date"]).dt.date
    frame = pd.DataFrame(index=index)
    for col in VIX_COLUMNS:
        frame[col] = pd.to_numeric(raw[col], errors="coerce").to_numpy() if col in raw.columns else float("nan")
    frame.index.name = "date"
    return frame.sort_index()


def vix_level_series(vix_frame: pd.DataFrame) -> pd.Series:
    """Return the daily VIX close level as a date-indexed Series."""
    return vix_frame["vix"].astype("float64")
