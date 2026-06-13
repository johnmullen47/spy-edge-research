"""Causal prior-day support/resistance level features."""

from __future__ import annotations

import pandas as pd


def add_prior_day_levels(
    df: pd.DataFrame,
    timestamp_col: str = "timestamp",
    high_col: str = "high",
    low_col: str = "low",
    close_col: str = "close",
    session_col: str | None = None,
    regular_session_value: str = "regular",
    timezone: str = "America/New_York",
) -> pd.DataFrame:
    """Add completed prior local trading-date high, low, and close levels."""
    required_columns = [timestamp_col, high_col, low_col, close_col]
    if session_col is not None:
        required_columns.append(session_col)
    _require_columns(df, required_columns)

    result = df.copy()
    trading_dates = _local_trading_dates(result[timestamp_col], timezone)

    level_source = result
    source_dates = trading_dates
    if session_col is not None:
        regular_rows = result[session_col] == regular_session_value
        level_source = result.loc[regular_rows]
        source_dates = trading_dates.loc[regular_rows]

    daily_levels = _daily_levels(level_source, source_dates, high_col, low_col, close_col)
    prior_levels = daily_levels.shift(1)

    result["prior_day_high"] = trading_dates.map(prior_levels["prior_day_high"])
    result["prior_day_low"] = trading_dates.map(prior_levels["prior_day_low"])
    result["prior_day_close"] = trading_dates.map(prior_levels["prior_day_close"])
    result["distance_to_prior_day_high"] = result[close_col] - result["prior_day_high"]
    result["distance_to_prior_day_low"] = result[close_col] - result["prior_day_low"]
    result["distance_to_prior_day_close"] = result[close_col] - result["prior_day_close"]
    result["above_prior_day_high"] = _safe_bool_series(
        result[close_col] > result["prior_day_high"], result.index
    )
    result["below_prior_day_low"] = _safe_bool_series(
        result[close_col] < result["prior_day_low"], result.index
    )
    return result


def _daily_levels(
    df: pd.DataFrame,
    trading_dates: pd.Series,
    high_col: str,
    low_col: str,
    close_col: str,
) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(
            columns=["prior_day_high", "prior_day_low", "prior_day_close"],
            index=pd.Index([], name="trading_date"),
        )

    daily = df.groupby(trading_dates, sort=True).agg(
        prior_day_high=(high_col, "max"),
        prior_day_low=(low_col, "min"),
        prior_day_close=(close_col, "last"),
    )
    daily.index.name = "trading_date"
    return daily


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


def _safe_bool_series(values: pd.Series, index: pd.Index) -> pd.Series:
    return pd.Series(values, index=index).fillna(False).astype(bool)
