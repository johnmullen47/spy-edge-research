"""Intraday VWAP calculations."""

from __future__ import annotations

import numpy as np
import pandas as pd


def calculate_intraday_vwap(
    df: pd.DataFrame,
    timezone: str = "America/New_York",
) -> pd.DataFrame:
    """Add causal intraday VWAP fields that reset by local trading date."""
    _require_columns(df, ["timestamp", "high", "low", "close", "volume"])

    result = df.copy()
    trading_date = _local_trading_dates(result["timestamp"], timezone)
    result["typical_price"] = (result["high"] + result["low"] + result["close"]) / 3

    price_volume = result["typical_price"] * result["volume"]
    cumulative_price_volume = price_volume.groupby(trading_date).cumsum()
    cumulative_volume = result["volume"].groupby(trading_date).cumsum()

    result["vwap"] = cumulative_price_volume.div(cumulative_volume.replace(0, np.nan))
    result["vwap_distance"] = result["close"] - result["vwap"]
    result["vwap_distance_pct"] = result["vwap_distance"].div(result["vwap"].replace(0, np.nan))
    result["vwap_slope"] = result["vwap"].diff()
    return result


def _local_trading_dates(timestamps: pd.Series, timezone: str) -> pd.Series:
    parsed = pd.to_datetime(timestamps)
    if parsed.dt.tz is None:
        parsed = parsed.dt.tz_localize(timezone)
    else:
        parsed = parsed.dt.tz_convert(timezone)
    return pd.Series(parsed.dt.date, index=timestamps.index)


def _require_columns(df: pd.DataFrame, columns: list[str]) -> None:
    missing = [column for column in columns if column not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")
