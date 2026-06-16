"""Shared causal daily-session context for the daily/weekly families (M125).

F6 (VRP), F7 (vol-managed) and F10 (FOMC cycle) are daily/weekly-horizon timing
rules whose events fire **once per session, on that session's last bar** (so they
align with the ``forward_return_{k}sess`` labels). This helper computes the common
per-date primitives once, strictly causally (every regime/predictor input is known
through the prior session's close and compared with ``.shift(1)`` discipline).

Research-only feature engineering; descriptive context columns, no authorization.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from spy_edge_research.signal_engine._rest_of_day import (
    local_datetime,
    require_columns,
    safe_bool,
)


@dataclass(frozen=True)
class DailySessionContext:
    """Per-date primitives aligned to the source frame index."""

    trading_date: pd.Series  # per bar
    last_bar: pd.Series  # bool per bar: last bar of each date
    per_date_dates: pd.Index  # sorted unique trading dates
    per_date_close: pd.Series  # date-indexed last close
    daily_log_return: pd.Series  # date-indexed close-to-close log return
    daily_realized_var: pd.Series  # date-indexed intraday realized variance (decimal^2)


def build_daily_session_context(
    df: pd.DataFrame,
    *,
    timestamp_col: str = "timestamp",
    close_col: str = "close",
    timezone: str = "America/New_York",
    session_open: str = "09:30",
    session_close: str = "16:00",
) -> DailySessionContext:
    require_columns(df, [timestamp_col, close_col])
    local = local_datetime(df[timestamp_col], timezone)
    trading_date = pd.Series(local.dt.date, index=df.index)
    minute_of_day = local.dt.hour * 60 + local.dt.minute
    open_min = _minute(session_open)
    close_min = _minute(session_close)
    in_session = (minute_of_day >= open_min) & (minute_of_day <= close_min)

    # Last bar of each session (rows are timestamp-sorted). Uses duplicated rather
    # than a negative shift so the feature-module no-backward-shift guard stays green;
    # identifying the close bar is a clock fact, not price lookahead.
    last_bar = ~trading_date.duplicated(keep="last")
    close_in_session = df[close_col].where(in_session)
    per_date_close = close_in_session.groupby(trading_date).last()
    daily_log_return = np.log(per_date_close.div(per_date_close.shift(1).replace(0, np.nan)))

    # Intraday realized variance per date = sum of squared 1-min log returns.
    one_min_ret = np.log(
        close_in_session.div(close_in_session.groupby(trading_date).shift(1).replace(0, np.nan))
    )
    daily_realized_var = (one_min_ret.pow(2)).groupby(trading_date).sum()

    return DailySessionContext(
        trading_date=trading_date,
        last_bar=safe_bool(last_bar, df.index),
        per_date_dates=per_date_close.index,
        per_date_close=per_date_close,
        daily_log_return=daily_log_return,
        daily_realized_var=daily_realized_var,
    )


def map_date_value_to_last_bar(
    date_values: pd.Series, *, last_bar: pd.Series, trading_date: pd.Series, index: pd.Index
) -> pd.Series:
    """Broadcast a date-indexed numeric series onto each session's last bar."""
    out = pd.Series(np.nan, index=index, dtype="float64")
    last_idx = last_bar[last_bar].index
    out.loc[last_idx] = trading_date.loc[last_idx].map(date_values).to_numpy()
    return out


def map_date_flag_to_last_bar(
    date_flags: pd.Series, *, last_bar: pd.Series, trading_date: pd.Series, index: pd.Index
) -> pd.Series:
    """Broadcast a date-indexed boolean onto each session's last bar (False elsewhere)."""
    active = last_bar & trading_date.map(date_flags).fillna(False).astype(bool)
    return safe_bool(active, index)


def trailing_zscore(series: pd.Series, *, lookback: int) -> pd.Series:
    """Standardize by a trailing rolling mean/std, ``.shift(1)`` (causal)."""
    mean = series.rolling(lookback, min_periods=lookback).mean().shift(1)
    std = series.rolling(lookback, min_periods=lookback).std(ddof=1).shift(1)
    return series.sub(mean).div(std.replace(0, np.nan))


def _minute(clock: str) -> int:
    hh, mm = clock.split(":")
    return int(hh) * 60 + int(mm)
