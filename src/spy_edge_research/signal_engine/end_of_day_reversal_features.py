"""End-of-day reversal features (F2 — M116).

Path-2 sibling signal pre-registered in ``docs/PREREG_F2_end_of_day_reversal.md``
(lineage ``RESEARCH_F`` candidate F2). Mechanism: option-market-maker hedging and
leveraged-ETF rebalancing into the close generate a **reversal** — the pre-close
window return negatively predicts the last-window return (Baltussen, Da & Soebhag,
t = -6.28). This is a *price-only* signal on existing SPY 1-minute bars; unlike the
MIM family there is **no regime gate**.

Strictly causal / no-lookahead, mirroring the MIM construction:

- **Predictor.** ``r_pre`` = log return over the pre-close window (default
  14:00-15:00 ET), measured at the *decision bar* (the first bar at/after the
  window end, default 15:00). It uses only bars up to and including that bar.
- **Position.** ``-sign(r_pre)`` — trade *against* the pre-close move — emitted on
  the decision bar and held into the close (resolved by a separate to-close forward
  label, default 60 minutes → 16:00). No future bar touches the feature.
- **Secondary (pre-declared, counted in N).** The pre-registration's
  magnitude-scaled position ``-clip(r_pre / sigma_pre)``. Position *sizing* is a
  non-goal of this unit-position research harness, so the secondary is represented
  faithfully as a **conviction-gated** variant: the same ``-sign(r_pre)`` trade,
  fired only when the standardized move ``|r_pre / sigma_pre|`` clears a frozen
  threshold. ``sigma_pre`` is a trailing same-time-of-day std of prior sessions'
  ``r_pre`` (``.shift(1)`` so the current session never sets its own scale).

The module emits boolean ``event_eod_reversal_*`` columns so the family flows
through the SAME candidate / edge-measurement / Hard-Gate-A pipeline as every other
family — a new set of candidates through the same gate, not a new gate. The binding
economic control for F2 (the bounce / half-spread test) lives in
``backtesting.end_of_day_reversal_placebos``.

Research-only feature engineering: no trade signal, order, sizing, or
authorization. Descriptive context columns only.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

EOD_EVENT_PREFIX = "event_eod_reversal_"


def add_end_of_day_reversal_features(
    df: pd.DataFrame,
    *,
    timestamp_col: str = "timestamp",
    close_col: str = "close",
    timezone: str = "America/New_York",
    pre_window_start: str = "14:00",
    pre_window_end: str = "15:00",
    session_close: str = "16:00",
    vol_lookback_days: int = 20,
    conviction_z: float = 1.0,
) -> pd.DataFrame:
    """Add causal end-of-day reversal features and event columns.

    Adds, per local trading date:

    Decision-bar values (NaN/empty off the decision bar; the decision bar is the
    first regular bar at/after ``pre_window_end``):
      - ``eod_decision_bar`` (bool).
      - ``eod_pre_close_return`` — ``r_pre`` = log(close[end] / close[start]) over
        the pre-close window.
      - ``eod_pre_close_vol`` — trailing same-time-of-day std of prior sessions'
        ``r_pre`` (``.shift(1)``); the secondary's scale.
      - ``eod_pre_close_zscore`` — ``r_pre / eod_pre_close_vol`` (NaN until history).
      - ``eod_high_conviction`` (bool) — ``|zscore| >= conviction_z``.

    Event columns (bool, fire only on the decision bar):
      - ``event_eod_reversal_long`` / ``event_eod_reversal_short`` — the primary
        ``-sign(r_pre)`` rule (long when ``r_pre < 0``, short when ``r_pre > 0``).
      - ``event_eod_reversal_long_conviction`` / ``..._short_conviction`` — the
        secondary: same direction, gated to ``|zscore| >= conviction_z``.
    """
    _require_columns(df, [timestamp_col, close_col])
    _validate_positive_int(vol_lookback_days, "vol_lookback_days")
    _validate_non_negative_number(conviction_z, "conviction_z")

    start_min = _minute_of_day_from_clock(pre_window_start, "pre_window_start")
    end_min = _minute_of_day_from_clock(pre_window_end, "pre_window_end")
    close_min = _minute_of_day_from_clock(session_close, "session_close")
    if not start_min < end_min <= close_min:
        raise ValueError(
            "clock boundaries must satisfy pre_window_start < pre_window_end <= session_close"
        )

    result = df.copy()
    local = _local_datetime(result[timestamp_col], timezone)
    trading_date = pd.Series(local.dt.date, index=result.index)
    minute_of_day = pd.Series(local.dt.hour * 60 + local.dt.minute, index=result.index)
    in_session = (minute_of_day >= start_min) & (minute_of_day <= close_min)

    # Pre-window start price: close of the first regular bar at/after the window
    # start, broadcast across the day (known causally from that bar onward).
    at_or_after_start = in_session & (minute_of_day >= start_min)
    start_price_at_bar = result[close_col].where(at_or_after_start)
    pre_start_price = start_price_at_bar.groupby(trading_date).transform("first")

    # Decision bar: first regular bar at/after the pre-window end, per day.
    at_or_after_end = in_session & (minute_of_day >= end_min)
    previously_after_end = (
        at_or_after_end.groupby(trading_date).shift(1).fillna(False).astype(bool)
    )
    decision_bar = at_or_after_end & (~previously_after_end)
    result["eod_decision_bar"] = decision_bar

    # r_pre = log(close[decision] / close[pre-window start]); causal (both <= end).
    end_price = result[close_col].where(decision_bar)
    ratio = end_price.div(pre_start_price.where(decision_bar).replace(0, np.nan))
    r_pre = np.log(ratio.where(ratio > 0))
    result["eod_pre_close_return"] = r_pre

    # Secondary scale: trailing same-time-of-day std of prior sessions' r_pre.
    sigma_pre = _trailing_session_std(
        r_pre,
        decision_bar=decision_bar,
        trading_date=trading_date,
        lookback=vol_lookback_days,
    )
    result["eod_pre_close_vol"] = sigma_pre
    zscore = r_pre.div(sigma_pre.replace(0, np.nan))
    result["eod_pre_close_zscore"] = zscore.where(decision_bar)
    high_conviction = decision_bar & zscore.notna() & (zscore.abs() >= conviction_z)
    result["eod_high_conviction"] = _safe_bool(high_conviction, result.index)

    # Primary -sign(r_pre): long when the pre-close move was DOWN, short when UP.
    long_primary = decision_bar & (r_pre < 0)
    short_primary = decision_bar & (r_pre > 0)
    result["event_eod_reversal_long"] = _safe_bool(long_primary, result.index)
    result["event_eod_reversal_short"] = _safe_bool(short_primary, result.index)
    result["event_eod_reversal_long_conviction"] = _safe_bool(
        long_primary & result["eod_high_conviction"], result.index
    )
    result["event_eod_reversal_short_conviction"] = _safe_bool(
        short_primary & result["eod_high_conviction"], result.index
    )
    return result


def find_end_of_day_reversal_event_columns(df: pd.DataFrame) -> list[str]:
    """Return the F2 event columns present in ``df`` (sorted, deterministic)."""
    return sorted(c for c in df.columns if c.startswith(EOD_EVENT_PREFIX))


def _trailing_session_std(
    r_pre: pd.Series,
    *,
    decision_bar: pd.Series,
    trading_date: pd.Series,
    lookback: int,
) -> pd.Series:
    """Trailing rolling std of prior sessions' ``r_pre`` (shifted, causal).

    Computed over the one-value-per-session series of decision-bar ``r_pre``, then
    ``.shift(1)`` so a session is scaled by history *before* it. Mapped back to the
    decision-bar rows; NaN elsewhere and where history is too short.
    """
    sigma = pd.Series(np.nan, index=r_pre.index, dtype="float64")
    decision_idx = decision_bar[decision_bar].index
    if len(decision_idx) == 0:
        return sigma
    per_session = r_pre.loc[decision_idx]
    rolled = per_session.rolling(lookback, min_periods=lookback).std(ddof=1).shift(1)
    sigma.loc[decision_idx] = rolled
    return sigma


def _local_datetime(timestamps: pd.Series, timezone: str) -> pd.Series:
    parsed = pd.to_datetime(timestamps)
    if parsed.dt.tz is None:
        parsed = parsed.dt.tz_localize(timezone)
    else:
        parsed = parsed.dt.tz_convert(timezone)
    return pd.Series(parsed, index=timestamps.index)


def _minute_of_day_from_clock(clock: str, name: str) -> int:
    try:
        hour_str, minute_str = clock.split(":")
        hour, minute = int(hour_str), int(minute_str)
    except (ValueError, AttributeError) as exc:
        raise ValueError(f"{name} must be a 'HH:MM' clock string") from exc
    if not (0 <= hour < 24 and 0 <= minute < 60):
        raise ValueError(f"{name} must be a valid 'HH:MM' clock time")
    return hour * 60 + minute


def _safe_bool(values: pd.Series, index: pd.Index) -> pd.Series:
    return pd.Series(values, index=index).fillna(False).astype(bool)


def _require_columns(df: pd.DataFrame, columns: list[str]) -> None:
    missing = [column for column in columns if column not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")


def _validate_positive_int(value: int, name: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise ValueError(f"{name} must be an integer greater than or equal to 1")


def _validate_non_negative_number(value: float, name: str) -> None:
    if not isinstance(value, (int, float)) or isinstance(value, bool) or value < 0:
        raise ValueError(f"{name} must be a number greater than or equal to 0")
