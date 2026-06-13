"""Causal same-day premarket level features."""

from __future__ import annotations

import pandas as pd

from spy_edge_research.market_data.sessions import classify_session


def add_premarket_levels(
    df: pd.DataFrame,
    timestamp_col: str = "timestamp",
    high_col: str = "high",
    low_col: str = "low",
    close_col: str = "close",
    session_col: str | None = None,
    premarket_session_value: str = "premarket",
    regular_session_value: str = "regular",
    timezone: str = "America/New_York",
) -> pd.DataFrame:
    """Add causal premarket high/low fields for each local trading date."""
    required_columns = [timestamp_col, high_col, low_col, close_col]
    if session_col is not None:
        required_columns.append(session_col)
    _require_columns(df, required_columns)

    result = df.copy()
    trading_dates = _local_trading_dates(result[timestamp_col], timezone)
    sessions = _sessions(result, timestamp_col, session_col, timezone)
    premarket_rows = sessions == premarket_session_value
    regular_rows = sessions == regular_session_value

    result["premarket_high_so_far"] = pd.Series(float("nan"), index=result.index)
    result["premarket_low_so_far"] = pd.Series(float("nan"), index=result.index)
    result.loc[premarket_rows, "premarket_high_so_far"] = (
        result.loc[premarket_rows, high_col].groupby(trading_dates.loc[premarket_rows]).cummax()
    )
    result.loc[premarket_rows, "premarket_low_so_far"] = (
        result.loc[premarket_rows, low_col].groupby(trading_dates.loc[premarket_rows]).cummin()
    )

    completed_high = result.loc[premarket_rows].groupby(trading_dates.loc[premarket_rows])[
        high_col
    ].max()
    completed_low = result.loc[premarket_rows].groupby(trading_dates.loc[premarket_rows])[
        low_col
    ].min()

    result["premarket_high"] = pd.Series(float("nan"), index=result.index)
    result["premarket_low"] = pd.Series(float("nan"), index=result.index)
    result.loc[regular_rows, "premarket_high"] = trading_dates.loc[regular_rows].map(
        completed_high
    )
    result.loc[regular_rows, "premarket_low"] = trading_dates.loc[regular_rows].map(
        completed_low
    )

    result["distance_to_premarket_high"] = result[close_col] - result["premarket_high"]
    result["distance_to_premarket_low"] = result[close_col] - result["premarket_low"]
    result["above_premarket_high"] = _safe_bool_series(
        result[close_col] > result["premarket_high"], result.index
    )
    result["below_premarket_low"] = _safe_bool_series(
        result[close_col] < result["premarket_low"], result.index
    )
    return result


def _sessions(
    df: pd.DataFrame,
    timestamp_col: str,
    session_col: str | None,
    timezone: str,
) -> pd.Series:
    if session_col is not None:
        return df[session_col]
    return df[timestamp_col].map(lambda timestamp: classify_session(timestamp, timezone=timezone))


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
