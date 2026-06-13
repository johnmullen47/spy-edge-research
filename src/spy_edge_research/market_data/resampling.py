"""Causal OHLCV resampling for bar-close timestamped data."""

from __future__ import annotations

import pandas as pd

from spy_edge_research.market_data.validators import validate_ohlcv_schema


def resample_ohlcv(
    df: pd.DataFrame,
    rule: str = "5min",
    drop_incomplete: bool = True,
) -> pd.DataFrame:
    """Resample 1-minute OHLCV bars into larger bar-close labeled candles.

    Resampling uses right-closed, right-labeled windows. For example, a candle
    labeled 09:35 contains only source bars with timestamps less than or equal
    to 09:35, and it is not complete until 09:35.
    """
    validated = validate_ohlcv_schema(df)
    if validated.empty:
        return validate_ohlcv_schema(validated, allow_empty=True)

    indexed = validated.set_index("timestamp")
    resampled = indexed.resample(rule, label="right", closed="right").agg(
        {
            "symbol": "first",
            "open": "first",
            "high": "max",
            "low": "min",
            "close": "last",
            "volume": "sum",
        }
    )

    source_counts = indexed["close"].resample(rule, label="right", closed="right").count()
    expected_count = _expected_source_count(rule)
    if drop_incomplete:
        resampled = resampled.loc[source_counts == expected_count]
    else:
        resampled = resampled.loc[source_counts > 0]

    resampled = resampled.dropna(subset=["symbol", "open", "high", "low", "close"])
    output = resampled.reset_index()
    return validate_ohlcv_schema(output, allow_empty=True)


def _expected_source_count(rule: str) -> int:
    """Return the expected number of 1-minute bars in a resampled candle."""
    offset = pd.tseries.frequencies.to_offset(rule)
    nanos_per_minute = pd.Timedelta(minutes=1).value
    if offset.nanos % nanos_per_minute != 0:
        raise ValueError("Resampling rule must resolve to whole minutes")

    minutes = offset.nanos // nanos_per_minute
    if minutes <= 0:
        raise ValueError("Resampling rule must be positive")
    return int(minutes)
