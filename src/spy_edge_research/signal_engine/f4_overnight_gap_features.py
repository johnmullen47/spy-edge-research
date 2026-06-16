"""F4 — overnight-gap-conditioned intraday momentum (M122).

Pre-registered in ``docs/PREREG_F4.md`` (immutable). F4 conditions the same
Config-A Baltussen predictor (``r_rod`` prev close→15:30, trade 15:30→16:00) on the
**overnight gap** ``gap = log(open_t / close_{t-1})``, known at 09:30 (causal,
pre-trade). The Baltussen predictor already embeds the gap, so the binding test
(recorded, evaluated downstream) is **incremental information beyond the
undecomposed base predictor** out-of-sample.

Conditioner variants (pre-declared, §3):
  - ``g1`` magnitude gate — trade only when ``|gap|`` is in the **top trailing
    tercile** (threshold from a shifted trailing distribution → no current-day
    leakage; the gap value itself is current-day but pre-window, so causal).
  - ``g2`` sign-agreement — take the momentum position only when
    ``sign(gap) == sign(r_rod)`` (long requires gap > 0, short requires gap < 0).
  - ``g3`` combined — ``g1 ∧ g2``.

Grid: 4 thresholds × 3 variants = 12 cells, encoded as 24 directional
``event_f4_*`` columns. SPY 1-min only — no external data. Research-only.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from spy_edge_research.signal_engine._rest_of_day import (
    build_rest_of_day_context,
    safe_bool,
    threshold_tag,
    validate_positive_int,
    validate_thresholds,
)

F4_EVENT_PREFIX = "event_f4_"
F4_VARIANTS: tuple[str, ...] = ("g1", "g2", "g3")
F4_THRESHOLDS: tuple[float, ...] = (0.0, 0.0010, 0.0025, 0.0050)
TOP_TERCILE_QUANTILE = 2.0 / 3.0


def add_f4_overnight_gap_features(
    df: pd.DataFrame,
    *,
    variants: tuple[str, ...] = F4_VARIANTS,
    thresholds: tuple[float, ...] = F4_THRESHOLDS,
    timestamp_col: str = "timestamp",
    open_col: str = "open",
    close_col: str = "close",
    timezone: str = "America/New_York",
    session_open: str = "09:30",
    session_close: str = "16:00",
    cutoff_time: str = "15:30",
    gap_lookback_days: int = 60,
) -> pd.DataFrame:
    """Add causal F4 overnight-gap-conditioned momentum event columns."""
    validate_thresholds(thresholds)
    validate_positive_int(gap_lookback_days, "gap_lookback_days")
    for v in variants:
        if v not in F4_VARIANTS:
            raise ValueError(f"unknown F4 variant: {v!r}")

    ctx = build_rest_of_day_context(
        df,
        cutoff_time=cutoff_time,
        timestamp_col=timestamp_col,
        open_col=open_col,
        close_col=close_col,
        timezone=timezone,
        session_open=session_open,
        session_close=session_close,
    )
    result = df.copy()
    result["f4_decision_bar"] = ctx.decision_bar
    result["f4_r_rod"] = ctx.r_rod
    result["f4_overnight_gap"] = ctx.overnight_gap

    gap = ctx.overnight_gap  # NaN off the decision bar; the gate masks below are
    # only ever ANDed with ctx.decision_bar, so off-bar NaNs cannot fire.

    # Per-date |gap| top-tercile gate, threshold from a shifted trailing window.
    dec_idx = ctx.decision_bar[ctx.decision_bar].index
    gap_by_date = pd.Series(
        gap.loc[dec_idx].to_numpy(), index=ctx.trading_date.loc[dec_idx]
    )
    abs_gap = gap_by_date.abs()
    tercile = abs_gap.rolling(gap_lookback_days, min_periods=gap_lookback_days).quantile(
        TOP_TERCILE_QUANTILE
    ).shift(1)
    large_gap_by_date = (abs_gap > tercile).fillna(False).astype(bool)
    magnitude_gate = safe_bool(
        ctx.decision_bar & ctx.trading_date.map(large_gap_by_date).fillna(False).astype(bool),
        result.index,
    )
    result["f4_large_gap"] = magnitude_gate

    gap_up = ctx.decision_bar & (gap > 0)
    gap_down = ctx.decision_bar & (gap < 0)

    for variant in variants:
        if variant == "g1":
            long_gate = short_gate = magnitude_gate
        elif variant == "g2":
            long_gate = safe_bool(gap_up, result.index)
            short_gate = safe_bool(gap_down, result.index)
        else:  # g3 = g1 ∧ g2
            long_gate = safe_bool(magnitude_gate & gap_up, result.index)
            short_gate = safe_bool(magnitude_gate & gap_down, result.index)
        result[f"f4_gate_{variant}_long"] = long_gate
        result[f"f4_gate_{variant}_short"] = short_gate
        for tau in thresholds:
            base = f"{F4_EVENT_PREFIX}{variant}_{threshold_tag(tau)}"
            result[f"{base}_long"] = safe_bool(
                ctx.decision_bar & long_gate & (ctx.r_rod > tau), result.index
            )
            result[f"{base}_short"] = safe_bool(
                ctx.decision_bar & short_gate & (ctx.r_rod < -tau), result.index
            )
    return result


def find_f4_event_columns(df: pd.DataFrame) -> list[str]:
    """Return the F4 event columns present in ``df`` (sorted)."""
    return sorted(c for c in df.columns if c.startswith(F4_EVENT_PREFIX))
