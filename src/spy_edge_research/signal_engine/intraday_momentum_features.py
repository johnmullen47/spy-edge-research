"""Regime-conditioned intraday time-series momentum features (Build 4 / M110).

This is the Path 2 signal family adjudicated in
``Auto-Trader Build/RESEARCH_C_DECISION.md``: a single, pre-registered intraday
time-series-momentum (MIM) signal on existing SPY 1-minute bars, gated by one
causal realized-volatility regime threshold. It is a *disjoint* hypothesis family
from the killed 42 chart-pattern candidates — it conditions on the sign of a
realized clock-window return, not on price geometry — and is the
most-replicated short-horizon equity effect in the literature (Gao-Han-Li-Zhou
2018; Bogousslavsky 2016; Heston-Korajczyk-Sadka 2010).

The construction is strictly causal / no-lookahead:

- **Signal.** Over a fixed early-session clock window (default 09:30–10:00 ET),
  measure the open-to-window-end return ``r_open``. The directional hypothesis is
  ``sign(r_open)`` — momentum continuation into the rest of the session. The
  decision is emitted on the *decision bar* (the first bar at/after the window
  end); it uses only bars up to and including that bar.
- **Regime gate.** The realized volatility of 1-minute returns over the same
  window is compared to a trailing high-volatility threshold computed from a
  rolling quantile of *prior* sessions' window realized vol, ``.shift(1)`` so the
  current session never sets its own threshold (the same trailing-quantile
  discipline as ``market_regime``). The signal is "active" only in the
  high-volatility regime — the Gao et al. / Bogousslavsky liquidity channel.
- **Outcome.** Forward returns are added separately as labels
  (``backtesting.labels``) and consumed downstream; nothing here looks forward.

The module emits boolean ``event_mim_*`` columns so the family flows through the
same candidate / edge-measurement / Hard-Gate-A pipeline as every other family —
a new set of candidates through the same gate, not a new gate. Gated and ungated
variants are both emitted so the ungated baseline can be compared to the
regime-conditioned signal.

Research-only feature engineering: no trade signal, order, sizing, or
authorization. Descriptive context columns only.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

MIM_EVENT_PREFIX = "event_mim_"

VOL_REGIME_HIGH = "high"
VOL_REGIME_NORMAL = "normal"
VOL_REGIME_UNKNOWN = "unknown"


def add_intraday_momentum_features(
    df: pd.DataFrame,
    *,
    timestamp_col: str = "timestamp",
    open_col: str = "open",
    close_col: str = "close",
    timezone: str = "America/New_York",
    session_open: str = "09:30",
    momentum_window_end: str = "10:00",
    session_close: str = "16:00",
    realized_vol_lookback_days: int = 20,
    high_vol_quantile: float = 0.66,
) -> pd.DataFrame:
    """Add causal regime-conditioned intraday-momentum features and event columns.

    Adds, per local trading date:

    Running (defined on every regular-session bar; causal):
      - ``intraday_open_return`` — close / session-open price − 1 so far.
      - ``intraday_realized_vol_so_far`` — sqrt of cumulative squared 1-min
        returns since the open.

    Decision-bar values (NaN off the decision bar):
      - ``mim_decision_bar`` (bool) — first bar at/after ``momentum_window_end``.
      - ``mim_open_return`` — ``r_open`` measured at the window end.
      - ``mim_realized_vol`` — open→window-end realized volatility.
      - ``mim_vol_threshold`` — trailing high-vol threshold (prior sessions only).
      - ``mim_high_vol_regime`` (bool) — realized vol at/above the threshold.
      - ``mim_vol_regime`` (str) — ``high`` / ``normal`` / ``unknown``.

    Event columns (bool, fire only on the decision bar):
      - ``event_mim_long`` / ``event_mim_short`` — gated to the high-vol regime.
      - ``event_mim_long_all`` / ``event_mim_short_all`` — ungated baselines.
    """
    _require_columns(df, [timestamp_col, open_col, close_col])
    _validate_positive_int(realized_vol_lookback_days, "realized_vol_lookback_days")
    _validate_quantile(high_vol_quantile, "high_vol_quantile")

    open_min = _minute_of_day_from_clock(session_open, "session_open")
    end_min = _minute_of_day_from_clock(momentum_window_end, "momentum_window_end")
    close_min = _minute_of_day_from_clock(session_close, "session_close")
    if not open_min < end_min <= close_min:
        raise ValueError(
            "clock boundaries must satisfy session_open < momentum_window_end <= session_close"
        )

    result = df.copy()
    local = _local_datetime(result[timestamp_col], timezone)
    trading_date = pd.Series(local.dt.date, index=result.index)
    minute_of_day = pd.Series(local.dt.hour * 60 + local.dt.minute, index=result.index)
    in_session = (minute_of_day >= open_min) & (minute_of_day <= close_min)

    # Session open price: first regular-session open of each day (causal — known
    # from the session's first bar onward).
    open_in_session = result[open_col].where(in_session)
    session_open_price = open_in_session.groupby(trading_date).transform("first")
    result["intraday_open_return"] = result[close_col].div(
        session_open_price.replace(0, np.nan)
    ) - 1.0

    # Cumulative realized volatility of 1-minute returns since the open.
    close_in_session = result[close_col].where(in_session)
    one_min_return = close_in_session.groupby(trading_date).pct_change()
    squared = one_min_return.pow(2)
    realized_var = squared.groupby(trading_date).cumsum()
    result["intraday_realized_vol_so_far"] = np.sqrt(realized_var)

    # Decision bar: first regular-session bar at/after the window end, per day.
    at_or_after_end = in_session & (minute_of_day >= end_min)
    previously_after_end = (
        at_or_after_end.groupby(trading_date).shift(1).fillna(False).astype(bool)
    )
    decision_bar = at_or_after_end & (~previously_after_end)
    result["mim_decision_bar"] = decision_bar

    open_return = result["intraday_open_return"].where(decision_bar)
    realized_vol = result["intraday_realized_vol_so_far"].where(decision_bar)
    result["mim_open_return"] = open_return
    result["mim_realized_vol"] = realized_vol

    threshold = _trailing_high_vol_threshold(
        realized_vol,
        decision_bar=decision_bar,
        trading_date=trading_date,
        lookback=realized_vol_lookback_days,
        quantile=high_vol_quantile,
    )
    result["mim_vol_threshold"] = threshold

    high_vol = decision_bar & realized_vol.notna() & threshold.notna() & (
        realized_vol >= threshold
    )
    result["mim_high_vol_regime"] = _safe_bool(high_vol, result.index)
    result["mim_vol_regime"] = _vol_regime_label(
        decision_bar=decision_bar,
        threshold=threshold,
        high_vol=result["mim_high_vol_regime"],
        index=result.index,
    )

    positive = decision_bar & (open_return > 0)
    negative = decision_bar & (open_return < 0)
    result["event_mim_long_all"] = _safe_bool(positive, result.index)
    result["event_mim_short_all"] = _safe_bool(negative, result.index)
    result["event_mim_long"] = _safe_bool(
        positive & result["mim_high_vol_regime"], result.index
    )
    result["event_mim_short"] = _safe_bool(
        negative & result["mim_high_vol_regime"], result.index
    )
    return result


def find_intraday_momentum_event_columns(df: pd.DataFrame) -> list[str]:
    """Return the MIM event columns present in ``df`` (sorted, deterministic)."""
    return sorted(c for c in df.columns if c.startswith(MIM_EVENT_PREFIX))


def _trailing_high_vol_threshold(
    realized_vol: pd.Series,
    *,
    decision_bar: pd.Series,
    trading_date: pd.Series,
    lookback: int,
    quantile: float,
) -> pd.Series:
    """Trailing rolling-quantile vol threshold from prior sessions only.

    Computed over the one-value-per-session series of decision-bar realized vol,
    then ``.shift(1)`` so a session is judged against history *before* it. Mapped
    back to the decision-bar rows; NaN elsewhere and where history is too short.
    """
    threshold = pd.Series(np.nan, index=realized_vol.index, dtype="float64")
    decision_idx = decision_bar[decision_bar].index
    if len(decision_idx) == 0:
        return threshold
    per_session = realized_vol.loc[decision_idx]
    rolled = (
        per_session.rolling(lookback, min_periods=lookback).quantile(quantile).shift(1)
    )
    threshold.loc[decision_idx] = rolled
    return threshold


def _vol_regime_label(
    *,
    decision_bar: pd.Series,
    threshold: pd.Series,
    high_vol: pd.Series,
    index: pd.Index,
) -> pd.Series:
    labels = pd.Series("", index=index, dtype="object")
    labels.loc[~decision_bar] = ""
    on_decision = decision_bar.astype(bool)
    unknown = on_decision & threshold.isna()
    known = on_decision & threshold.notna()
    labels.loc[unknown] = VOL_REGIME_UNKNOWN
    labels.loc[known & high_vol.astype(bool)] = VOL_REGIME_HIGH
    labels.loc[known & ~high_vol.astype(bool)] = VOL_REGIME_NORMAL
    return labels


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


def _validate_quantile(value: float, name: str) -> None:
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not 0.0 < value < 1.0:
        raise ValueError(f"{name} must be a float in the open interval (0, 1)")
