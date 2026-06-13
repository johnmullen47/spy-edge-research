"""Volume indicator calculations."""

from __future__ import annotations

import numpy as np
import pandas as pd


def calculate_volume_features(
    df: pd.DataFrame,
    window: int = 20,
    timezone: str = "America/New_York",
    volume_col: str = "volume",
) -> pd.DataFrame:
    """Add trailing rolling volume stats and intraday expanding mean."""
    _validate_positive_int(window, "window")
    _require_columns(df, ["timestamp", volume_col])

    result = df.copy()
    sma_col = f"volume_sma_{window}"
    relative_col = f"relative_volume_{window}"
    zscore_col = f"volume_zscore_{window}"

    rolling = result[volume_col].rolling(window)
    result[sma_col] = rolling.mean()
    rolling_std = rolling.std()
    result[relative_col] = result[volume_col].div(result[sma_col].replace(0, np.nan))
    result[zscore_col] = (result[volume_col] - result[sma_col]).div(
        rolling_std.replace(0, np.nan)
    )

    trading_date = _local_trading_dates(result["timestamp"], timezone)
    result["volume_expanding_intraday_mean"] = (
        result[volume_col]
        .groupby(trading_date)
        .expanding()
        .mean()
        .reset_index(level=0, drop=True)
    )
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


def _validate_positive_int(value: int, name: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise ValueError(f"{name} must be an integer greater than or equal to 1")
