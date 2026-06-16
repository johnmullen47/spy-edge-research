"""F6 — Variance-Risk-Premium (VRP) timing (M125).

Pre-registered in ``docs/PREREG_F6.md`` (immutable). NEW Family 3. The variance risk
premium ``VRP = implied variance - realized variance`` positively predicts
subsequent SPY returns (Bollerslev, Tauchen & Zhou 2009). F6 times SPY exposure on
the standardized VRP.

Causal construction (event fires on each session's **last bar**, outcome resolved by
the ``forward_return_{5,21}sess`` labels):
- ``implied_var_t = (VIX_t/100)^2 * (21/252)`` — 21-session implied variance from the
  VIX close (known at session t's close).
- ``rv_t`` = trailing 21-session sum of intraday realized variance (sum of squared
  1-min log returns per day), through session t's close.
- ``VRP_t = implied_var_t - rv_t``, standardized by a trailing rolling mean/std
  (``.shift(1)``) into ``VRP_z``.
- Position: ``long if VRP_z > +tau ; short if VRP_z < -tau`` at thresholds tau (in
  sigma units). Long columns serve the PREREG long-only and long/short variants; the
  short columns are the long/short addition. 3 tau x {long,short} = 6 columns; the
  registry pairs them with the 5- and 21-session horizons (12 candidates).

Requires a daily VIX frame; without it the columns exist but never fire.
Research-only; no authorization.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from spy_edge_research.signal_engine._daily import (
    build_daily_session_context,
    map_date_value_to_last_bar,
    trailing_zscore,
)
from spy_edge_research.signal_engine._rest_of_day import (
    safe_bool,
    validate_positive_int,
)

F6_EVENT_PREFIX = "event_f6_"
F6_THRESHOLDS_SIGMA: tuple[float, ...] = (0.0, 0.5, 1.0)
F6_HORIZON_SESSIONS: tuple[int, ...] = (5, 21)
_RV_WINDOW = 21


def add_vrp_features(
    df: pd.DataFrame,
    *,
    vix_frame: pd.DataFrame | None = None,
    thresholds_sigma: tuple[float, ...] = F6_THRESHOLDS_SIGMA,
    timestamp_col: str = "timestamp",
    close_col: str = "close",
    timezone: str = "America/New_York",
    session_open: str = "09:30",
    session_close: str = "16:00",
    zscore_lookback_days: int = 60,
) -> pd.DataFrame:
    """Add causal F6 VRP-timing event columns (fired on each session's last bar)."""
    validate_positive_int(zscore_lookback_days, "zscore_lookback_days")
    for tau in thresholds_sigma:
        if not isinstance(tau, (int, float)) or isinstance(tau, bool) or tau < 0:
            raise ValueError("thresholds_sigma must be non-negative numbers")

    ctx = build_daily_session_context(
        df, timestamp_col=timestamp_col, close_col=close_col, timezone=timezone,
        session_open=session_open, session_close=session_close,
    )
    result = df.copy()
    result["f6_last_bar"] = ctx.last_bar

    rv = ctx.daily_realized_var.rolling(_RV_WINDOW, min_periods=_RV_WINDOW).sum()
    if vix_frame is not None:
        vix = pd.to_numeric(vix_frame.reindex(ctx.per_date_dates).get("vix"), errors="coerce")
        implied_var = (vix / 100.0) ** 2 * (_RV_WINDOW / 252.0)
        vrp = implied_var - rv
        vrp_z = trailing_zscore(vrp, lookback=zscore_lookback_days)
    else:
        vrp_z = pd.Series(np.nan, index=ctx.per_date_dates, dtype="float64")

    result["f6_vrp_z"] = map_date_value_to_last_bar(
        vrp_z, last_bar=ctx.last_bar, trading_date=ctx.trading_date, index=result.index
    )
    z = result["f6_vrp_z"]
    for tau in thresholds_sigma:
        tag = _sigma_tag(tau)
        result[f"{F6_EVENT_PREFIX}{tag}_long"] = safe_bool(
            ctx.last_bar & (z > tau), result.index
        )
        result[f"{F6_EVENT_PREFIX}{tag}_short"] = safe_bool(
            ctx.last_bar & (z < -tau), result.index
        )
    return result


def find_f6_event_columns(df: pd.DataFrame) -> list[str]:
    """Return the F6 event columns present in ``df`` (sorted)."""
    return sorted(c for c in df.columns if c.startswith(F6_EVENT_PREFIX))


def _sigma_tag(tau: float) -> str:
    return f"z{int(round(tau * 10))}"
