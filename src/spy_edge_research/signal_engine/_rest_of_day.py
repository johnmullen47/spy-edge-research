"""Shared causal rest-of-day predictor context (M122).

F3 (VIX gate), F4 (overnight-gap conditioner) and F5 (FOMC-eve calendar) are all
conditioners on the **same** Baltussen Config-A predictor as
``mim_baltussen_features`` (``r_rod`` = prior close→15:30, trade 15:30→16:00). This
helper computes that predictor and the per-session overnight gap once, strictly
causally, so the three F-modules share identical, no-lookahead inputs.

Research-only feature engineering: descriptive context columns, no authorization.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

CONFIG_A_CUTOFF = "15:30"
CONFIG_A_HOLD_MINUTES = 29  # 15:30 -> 15:59 (the vendor's last bar ~ 16:00 print)


@dataclass(frozen=True)
class RestOfDayContext:
    """Causal Config-A predictor inputs, all aligned to the source frame index."""

    trading_date: pd.Series
    minute_of_day: pd.Series
    in_session: pd.Series
    decision_bar: pd.Series  # bool: first regular bar at/after the cutoff, per day
    r_rod: pd.Series  # rest-of-day log return at the decision bar (NaN off-bar)
    overnight_gap: pd.Series  # log(open_t / close_{t-1}) at the decision bar
    per_date_last_close: pd.Series  # date-indexed
    hold_minutes: int


def build_rest_of_day_context(
    df: pd.DataFrame,
    *,
    cutoff_time: str = CONFIG_A_CUTOFF,
    hold_minutes: int = CONFIG_A_HOLD_MINUTES,
    timestamp_col: str = "timestamp",
    open_col: str = "open",
    close_col: str = "close",
    timezone: str = "America/New_York",
    session_open: str = "09:30",
    session_close: str = "16:00",
) -> RestOfDayContext:
    require_columns(df, [timestamp_col, open_col, close_col])
    open_min = minute_of_day_from_clock(session_open, "session_open")
    cutoff_min = minute_of_day_from_clock(cutoff_time, "cutoff_time")
    close_min = minute_of_day_from_clock(session_close, "session_close")
    if not open_min < cutoff_min < close_min:
        raise ValueError("must satisfy session_open < cutoff_time < session_close")

    local = local_datetime(df[timestamp_col], timezone)
    trading_date = pd.Series(local.dt.date, index=df.index)
    minute_of_day = pd.Series(local.dt.hour * 60 + local.dt.minute, index=df.index)
    in_session = (minute_of_day >= open_min) & (minute_of_day <= close_min)

    close_in_session = df[close_col].where(in_session)
    open_in_session = df[open_col].where(in_session)
    per_date_last = close_in_session.groupby(trading_date).last()
    per_date_first_open = open_in_session.groupby(trading_date).first()
    prior_close_by_date = per_date_last.shift(1)
    prior_session_close = trading_date.map(prior_close_by_date)

    # Overnight gap (causal; known at 09:30): log(first open / prior close).
    gap_by_date = np.log(
        per_date_first_open.div(prior_close_by_date.replace(0, np.nan))
    )

    decision_bar = first_bar_at_or_after(
        in_session=in_session,
        minute_of_day=minute_of_day,
        trading_date=trading_date,
        minute=cutoff_min,
    )

    cutoff_close = df[close_col].where(decision_bar)
    ratio = cutoff_close.div(prior_session_close.where(decision_bar).replace(0, np.nan))
    r_rod = np.log(ratio.where(ratio > 0))

    overnight_gap = pd.Series(np.nan, index=df.index, dtype="float64")
    dec_idx = decision_bar[decision_bar].index
    overnight_gap.loc[dec_idx] = trading_date.loc[dec_idx].map(gap_by_date).to_numpy()

    return RestOfDayContext(
        trading_date=trading_date,
        minute_of_day=minute_of_day,
        in_session=in_session,
        decision_bar=decision_bar,
        r_rod=r_rod,
        overnight_gap=overnight_gap,
        per_date_last_close=per_date_last,
        hold_minutes=hold_minutes,
    )


def map_date_flag_to_decision_bar(
    flag_by_date: pd.Series,
    *,
    decision_bar: pd.Series,
    trading_date: pd.Series,
    index: pd.Index,
) -> pd.Series:
    """Broadcast a per-date boolean onto the decision-bar rows (False elsewhere)."""
    active = decision_bar & trading_date.map(flag_by_date).fillna(False).astype(bool)
    return pd.Series(active, index=index).fillna(False).astype(bool)


def gt_trailing_quantile(
    series: pd.Series, *, lookback: int, quantile: float
) -> pd.Series:
    """Boolean: value strictly exceeds its trailing rolling quantile (causal)."""
    thresh = series.rolling(lookback, min_periods=lookback).quantile(quantile).shift(1)
    return (series > thresh).fillna(False).astype(bool)


def lt_trailing_quantile(
    series: pd.Series, *, lookback: int, quantile: float
) -> pd.Series:
    """Boolean: value strictly below its trailing rolling quantile (causal)."""
    thresh = series.rolling(lookback, min_periods=lookback).quantile(quantile).shift(1)
    return (series < thresh).fillna(False).astype(bool)


def gt_trailing_median(series: pd.Series, *, lookback: int) -> pd.Series:
    """Boolean: value strictly exceeds its trailing rolling median (causal)."""
    return gt_trailing_quantile(series, lookback=lookback, quantile=0.5)


def first_bar_at_or_after(
    *,
    in_session: pd.Series,
    minute_of_day: pd.Series,
    trading_date: pd.Series,
    minute: int,
) -> pd.Series:
    at_or_after = in_session & (minute_of_day >= minute)
    previously = at_or_after.groupby(trading_date).shift(1).fillna(False).astype(bool)
    return at_or_after & (~previously)


def local_datetime(timestamps: pd.Series, timezone: str) -> pd.Series:
    parsed = pd.to_datetime(timestamps)
    if parsed.dt.tz is None:
        parsed = parsed.dt.tz_localize(timezone)
    else:
        parsed = parsed.dt.tz_convert(timezone)
    return pd.Series(parsed, index=timestamps.index)


def minute_of_day_from_clock(clock: str, name: str) -> int:
    try:
        hour_str, minute_str = clock.split(":")
        hour, minute = int(hour_str), int(minute_str)
    except (ValueError, AttributeError) as exc:
        raise ValueError(f"{name} must be a 'HH:MM' clock string") from exc
    if not (0 <= hour < 24 and 0 <= minute < 60):
        raise ValueError(f"{name} must be a valid 'HH:MM' clock time")
    return hour * 60 + minute


def safe_bool(values: pd.Series, index: pd.Index) -> pd.Series:
    return pd.Series(values, index=index).fillna(False).astype(bool)


def require_columns(df: pd.DataFrame, columns: list[str]) -> None:
    missing = [c for c in columns if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")


def threshold_tag(tau: float) -> str:
    """Compact basis-point tag for a threshold, e.g. 0.0025 -> ``t25``."""
    return f"t{int(round(tau * 10000))}"


def validate_thresholds(thresholds: tuple[float, ...]) -> None:
    for tau in thresholds:
        if not isinstance(tau, (int, float)) or isinstance(tau, bool) or tau < 0:
            raise ValueError("thresholds must be non-negative numbers")


def validate_positive_int(value: int, name: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise ValueError(f"{name} must be an integer greater than or equal to 1")
