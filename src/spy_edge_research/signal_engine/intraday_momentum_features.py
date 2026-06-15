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

from dataclasses import dataclass

import numpy as np
import pandas as pd

MIM_EVENT_PREFIX = "event_mim_"

VOL_REGIME_HIGH = "high"
VOL_REGIME_NORMAL = "normal"
VOL_REGIME_UNKNOWN = "unknown"


@dataclass(frozen=True)
class IntradayMomentumVariantSpec:
    """Frozen MIM parameter-iteration cell.

    Each spec contributes exactly two gated event columns (long/short). Across
    the standard 5/15/30 minute labels that is six candidate hypotheses, so the
    default M117 iteration set below adds 12 candidates total.
    """

    suffix: str
    momentum_window_end: str
    entry_time: str
    high_vol_quantile: float


MIM_PARAMETER_ITERATION_SPECS: tuple[IntradayMomentumVariantSpec, ...] = (
    IntradayMomentumVariantSpec(
        suffix="q75_w15_e30",
        momentum_window_end="09:45",
        entry_time="10:00",
        high_vol_quantile=0.75,
    ),
    IntradayMomentumVariantSpec(
        suffix="q70_w45_e45",
        momentum_window_end="10:15",
        entry_time="10:15",
        high_vol_quantile=0.70,
    ),
)


def add_intraday_momentum_features(
    df: pd.DataFrame,
    *,
    timestamp_col: str = "timestamp",
    open_col: str = "open",
    close_col: str = "close",
    timezone: str = "America/New_York",
    session_open: str = "09:30",
    momentum_window_end: str = "10:00",
    entry_time: str | None = None,
    session_close: str = "16:00",
    realized_vol_lookback_days: int = 20,
    high_vol_quantile: float = 0.66,
    event_suffix: str = "",
    include_ungated_events: bool = True,
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
    _validate_event_suffix(event_suffix)

    open_min = _minute_of_day_from_clock(session_open, "session_open")
    end_min = _minute_of_day_from_clock(momentum_window_end, "momentum_window_end")
    entry_clock = entry_time or momentum_window_end
    entry_min = _minute_of_day_from_clock(entry_clock, "entry_time")
    close_min = _minute_of_day_from_clock(session_close, "session_close")
    if not open_min < end_min <= entry_min <= close_min:
        raise ValueError(
            "clock boundaries must satisfy session_open < "
            "momentum_window_end <= entry_time <= session_close"
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

    # Prediction-window bar: first regular-session bar at/after the window end.
    window_end_bar = _first_bar_at_or_after(
        in_session=in_session,
        minute_of_day=minute_of_day,
        trading_date=trading_date,
        minute=end_min,
    )

    # Decision/entry bar: first regular-session bar at/after the entry time.
    # Delayed-entry variants use only the window-end features, then wait until a
    # later decision bar to emit the event.
    decision_bar = _first_bar_at_or_after(
        in_session=in_session,
        minute_of_day=minute_of_day,
        trading_date=trading_date,
        minute=entry_min,
    )
    result[_suffixed("mim_decision_bar", event_suffix)] = decision_bar

    window_open_return = result["intraday_open_return"].where(window_end_bar)
    window_realized_vol = result["intraday_realized_vol_so_far"].where(window_end_bar)

    window_threshold = _trailing_high_vol_threshold(
        window_realized_vol,
        decision_bar=window_end_bar,
        trading_date=trading_date,
        lookback=realized_vol_lookback_days,
        quantile=high_vol_quantile,
    )

    open_return = _map_window_value_to_decision_bar(
        window_open_return, window_end_bar=window_end_bar, decision_bar=decision_bar, trading_date=trading_date
    )
    realized_vol = _map_window_value_to_decision_bar(
        window_realized_vol, window_end_bar=window_end_bar, decision_bar=decision_bar, trading_date=trading_date
    )
    threshold = _map_window_value_to_decision_bar(
        window_threshold, window_end_bar=window_end_bar, decision_bar=decision_bar, trading_date=trading_date
    )

    result[_suffixed("mim_open_return", event_suffix)] = open_return
    result[_suffixed("mim_realized_vol", event_suffix)] = realized_vol
    result[_suffixed("mim_vol_threshold", event_suffix)] = threshold

    high_vol = decision_bar & realized_vol.notna() & threshold.notna() & (
        realized_vol >= threshold
    )
    high_vol_col = _suffixed("mim_high_vol_regime", event_suffix)
    result[high_vol_col] = _safe_bool(high_vol, result.index)
    result[_suffixed("mim_vol_regime", event_suffix)] = _vol_regime_label(
        decision_bar=decision_bar,
        threshold=threshold,
        high_vol=result[high_vol_col],
        index=result.index,
    )

    positive = decision_bar & (open_return > 0)
    negative = decision_bar & (open_return < 0)
    if include_ungated_events:
        result[_suffixed("event_mim_long_all", event_suffix)] = _safe_bool(
            positive, result.index
        )
        result[_suffixed("event_mim_short_all", event_suffix)] = _safe_bool(
            negative, result.index
        )
    result[_suffixed("event_mim_long", event_suffix)] = _safe_bool(
        positive & result[high_vol_col], result.index
    )
    result[_suffixed("event_mim_short", event_suffix)] = _safe_bool(
        negative & result[high_vol_col], result.index
    )
    return result


def add_intraday_momentum_parameter_iteration_features(
    df: pd.DataFrame,
    *,
    specs: tuple[IntradayMomentumVariantSpec, ...] = MIM_PARAMETER_ITERATION_SPECS,
    timestamp_col: str = "timestamp",
    open_col: str = "open",
    close_col: str = "close",
    timezone: str = "America/New_York",
    session_open: str = "09:30",
    session_close: str = "16:00",
    realized_vol_lookback_days: int = 20,
) -> pd.DataFrame:
    """Append the frozen M117 MIM parameter-iteration event columns.

    The default iteration deliberately adds only two specs, each long/short only,
    so the 5/15/30 minute pipeline adds 12 candidate hypotheses rather than an
    open-ended grid. Ungated baselines are not emitted for these variants; every
    emitted event column flows into the candidate registry and DSR trial count.
    """
    result = df.copy()
    for spec in specs:
        result = add_intraday_momentum_features(
            result,
            timestamp_col=timestamp_col,
            open_col=open_col,
            close_col=close_col,
            timezone=timezone,
            session_open=session_open,
            momentum_window_end=spec.momentum_window_end,
            entry_time=spec.entry_time,
            session_close=session_close,
            realized_vol_lookback_days=realized_vol_lookback_days,
            high_vol_quantile=spec.high_vol_quantile,
            event_suffix=spec.suffix,
            include_ungated_events=False,
        )
    return result


def find_intraday_momentum_event_columns(df: pd.DataFrame) -> list[str]:
    """Return the MIM event columns present in ``df`` (sorted, deterministic)."""
    return sorted(c for c in df.columns if c.startswith(MIM_EVENT_PREFIX))


def _first_bar_at_or_after(
    *,
    in_session: pd.Series,
    minute_of_day: pd.Series,
    trading_date: pd.Series,
    minute: int,
) -> pd.Series:
    at_or_after = in_session & (minute_of_day >= minute)
    previously_after = at_or_after.groupby(trading_date).shift(1).fillna(False).astype(bool)
    return at_or_after & (~previously_after)


def _map_window_value_to_decision_bar(
    values: pd.Series,
    *,
    window_end_bar: pd.Series,
    decision_bar: pd.Series,
    trading_date: pd.Series,
) -> pd.Series:
    result = pd.Series(np.nan, index=values.index, dtype="float64")
    window_idx = window_end_bar[window_end_bar].index
    if len(window_idx) == 0:
        return result
    by_date = pd.Series(values.loc[window_idx].to_numpy(), index=trading_date.loc[window_idx])
    decision_idx = decision_bar[decision_bar].index
    if len(decision_idx) == 0:
        return result
    result.loc[decision_idx] = trading_date.loc[decision_idx].map(by_date).to_numpy()
    return result


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


def _validate_event_suffix(value: str) -> None:
    if not isinstance(value, str):
        raise ValueError("event_suffix must be a string")
    if value and not value.replace("_", "").isalnum():
        raise ValueError("event_suffix may contain only letters, numbers, and underscores")


def _suffixed(name: str, suffix: str) -> str:
    return name if not suffix else f"{name}_{suffix}"
