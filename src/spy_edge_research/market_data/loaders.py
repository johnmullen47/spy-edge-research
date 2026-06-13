"""CSV loading utilities for local OHLCV market data."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from spy_edge_research.market_data.validators import validate_ohlcv_schema


def load_ohlcv_csv(
    path: str | Path,
    symbol: str = "SPY",
    timezone: str = "America/New_York",
) -> pd.DataFrame:
    """Load and validate a local OHLCV CSV file.

    Column names are normalized to lowercase, timestamps are parsed, timezone-naive
    timestamps are localized to ``timezone``, and rows are sorted by timestamp.
    """
    raw = pd.read_csv(path)
    raw.columns = [column.strip().lower() for column in raw.columns]

    if "timestamp" not in raw.columns:
        return validate_ohlcv_schema(raw, symbol=symbol)

    timestamps = pd.to_datetime(raw["timestamp"])
    if timestamps.dt.tz is None:
        timestamps = timestamps.dt.tz_localize(timezone)
    else:
        timestamps = timestamps.dt.tz_convert(timezone)

    raw["timestamp"] = timestamps
    raw = raw.sort_values("timestamp", kind="mergesort").reset_index(drop=True)
    return validate_ohlcv_schema(raw, symbol=symbol)
