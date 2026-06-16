"""F3 — VIX-regime-gated intraday momentum (M122).

Pre-registered in ``docs/PREREG_F3.md`` (immutable). F3 swaps the MIM-Baltussen
realized-vol regime gate for a **VIX-level / term-structure** gate on the *same*
Config-A predictor (``r_rod`` prev close→15:30, trade 15:30→16:00). It is a
RESEARCH_H Family-1 variant: same predictor/horizon/direction, distinct regime
*variable*. The binding test (recorded, evaluated downstream) is **incremental
value over the realized-vol gate** — F3 is interesting only if it beats the base
MIM out-of-sample.

Gate variants (all causal; measured at the **prior session's close**, so known
pre-trade — the per-date flags are ``.shift(1)`` over the trading-date ordering):
  - ``vix20``  — VIX level > 20.
  - ``vixmed`` — VIX level > trailing rolling median.
  - ``tslope`` — term-structure stress: slope (VIX3M − VIX9D) in the bottom
    trailing quartile (unusually flat/inverted = stress; pre-declared bucket).

Grid: 4 thresholds × 3 variants = 12 cells, encoded as 24 directional
``event_f3_*`` columns. Requires a daily VIX frame (vix / vix9d / vix3m); without
it the columns exist but never fire. Research-only; no authorization.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from spy_edge_research.signal_engine._rest_of_day import (
    build_rest_of_day_context,
    map_date_flag_to_decision_bar,
    safe_bool,
    threshold_tag,
    validate_positive_int,
    validate_thresholds,
)

F3_EVENT_PREFIX = "event_f3_"
F3_VARIANTS: tuple[str, ...] = ("vix20", "vixmed", "tslope")
F3_THRESHOLDS: tuple[float, ...] = (0.0, 0.0010, 0.0025, 0.0050)


def add_f3_vix_gated_features(
    df: pd.DataFrame,
    *,
    vix_frame: pd.DataFrame | None = None,
    variants: tuple[str, ...] = F3_VARIANTS,
    thresholds: tuple[float, ...] = F3_THRESHOLDS,
    timestamp_col: str = "timestamp",
    open_col: str = "open",
    close_col: str = "close",
    timezone: str = "America/New_York",
    session_open: str = "09:30",
    session_close: str = "16:00",
    cutoff_time: str = "15:30",
    vix_threshold: float = 20.0,
    regime_lookback_days: int = 60,
) -> pd.DataFrame:
    """Add causal F3 VIX-gated momentum event columns (Config-A predictor)."""
    validate_thresholds(thresholds)
    validate_positive_int(regime_lookback_days, "regime_lookback_days")
    for v in variants:
        if v not in F3_VARIANTS:
            raise ValueError(f"unknown F3 variant: {v!r}")

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
    result["f3_decision_bar"] = ctx.decision_bar
    result["f3_r_rod"] = ctx.r_rod

    spy_dates = ctx.per_date_last_close.index
    gate_by_date = _vix_gate_flags(
        vix_frame,
        spy_dates=spy_dates,
        variants=variants,
        vix_threshold=vix_threshold,
        lookback=regime_lookback_days,
    )

    for variant in variants:
        active = map_date_flag_to_decision_bar(
            gate_by_date[variant],
            decision_bar=ctx.decision_bar,
            trading_date=ctx.trading_date,
            index=result.index,
        )
        result[f"f3_gate_{variant}"] = active
        for tau in thresholds:
            base = f"{F3_EVENT_PREFIX}{variant}_{threshold_tag(tau)}"
            result[f"{base}_long"] = safe_bool(
                ctx.decision_bar & active & (ctx.r_rod > tau), result.index
            )
            result[f"{base}_short"] = safe_bool(
                ctx.decision_bar & active & (ctx.r_rod < -tau), result.index
            )
    return result


def find_f3_event_columns(df: pd.DataFrame) -> list[str]:
    """Return the F3 event columns present in ``df`` (sorted)."""
    return sorted(c for c in df.columns if c.startswith(F3_EVENT_PREFIX))


def _vix_gate_flags(
    vix_frame: pd.DataFrame | None,
    *,
    spy_dates: pd.Index,
    variants: tuple[str, ...],
    vix_threshold: float,
    lookback: int,
) -> dict[str, pd.Series]:
    """Per-(SPY)-date boolean gate flags, pre-trade-known (shifted to prior close)."""
    inactive = pd.Series(False, index=spy_dates, dtype=bool)
    if vix_frame is None:
        return {v: inactive.copy() for v in variants}

    # Align VIX onto the SPY trading-date ordering; shift(1) -> prior session close.
    aligned = vix_frame.reindex(spy_dates)
    vix = pd.to_numeric(aligned.get("vix"), errors="coerce")
    flags: dict[str, pd.Series] = {}
    if "vix20" in variants:
        flags["vix20"] = (vix > vix_threshold).shift(1).fillna(False).astype(bool)
    if "vixmed" in variants:
        med = vix.rolling(lookback, min_periods=lookback).median()
        flags["vixmed"] = (vix > med).shift(1).fillna(False).astype(bool)
    if "tslope" in variants:
        vix9d = pd.to_numeric(aligned.get("vix9d"), errors="coerce")
        vix3m = pd.to_numeric(aligned.get("vix3m"), errors="coerce")
        slope = vix3m - vix9d  # contango (positive) vs flat/inverted (low/negative)
        q25 = slope.rolling(lookback, min_periods=lookback).quantile(0.25)
        stress = (slope < q25) & np.isfinite(slope)
        flags["tslope"] = stress.shift(1).fillna(False).astype(bool)
    return flags
