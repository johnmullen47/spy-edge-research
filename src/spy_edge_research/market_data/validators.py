"""Validation helpers for OHLCV market data."""

from __future__ import annotations

import pandas as pd

REQUIRED_COLUMNS: tuple[str, ...] = (
    "timestamp",
    "symbol",
    "open",
    "high",
    "low",
    "close",
    "volume",
)


def validate_ohlcv_schema(
    df: pd.DataFrame,
    symbol: str = "SPY",
    allow_empty: bool = False,
) -> pd.DataFrame:
    """Validate and return OHLCV data in canonical column order.

    The validator rejects data-quality issues instead of silently repairing them.
    It assumes timestamps are bar-close timestamps and requires them to be sorted.
    """
    missing = [column for column in REQUIRED_COLUMNS if column not in df.columns]
    if missing:
        raise ValueError(f"Missing required OHLCV columns: {missing}")

    clean = df.loc[:, REQUIRED_COLUMNS].copy()
    if clean.empty:
        if allow_empty:
            return clean
        raise ValueError("OHLCV data must not be empty")

    timestamps = pd.to_datetime(clean["timestamp"])
    if timestamps.dt.tz is None:
        raise ValueError("Timestamp column must be timezone-aware")

    if timestamps.duplicated().any():
        raise ValueError("Duplicate timestamps are not allowed")

    if not timestamps.is_monotonic_increasing:
        raise ValueError("Timestamps must be sorted in ascending order")

    if clean.loc[:, ["open", "high", "low", "close", "volume"]].isnull().any().any():
        raise ValueError("OHLCV columns must not contain null values")

    if (clean["symbol"] != symbol).any():
        raise ValueError(f"All rows must have symbol {symbol!r}")

    if (clean.loc[:, ["open", "high", "low", "close"]] <= 0).any().any():
        raise ValueError("Open, high, low, and close prices must be positive")

    if (clean["volume"] < 0).any():
        raise ValueError("Volume must be non-negative")

    invalid_ohlc = (
        (clean["high"] < clean["open"])
        | (clean["high"] < clean["close"])
        | (clean["high"] < clean["low"])
        | (clean["low"] > clean["open"])
        | (clean["low"] > clean["close"])
    )
    if invalid_ohlc.any():
        raise ValueError("Invalid OHLC relationships detected")

    clean["timestamp"] = timestamps
    return clean
