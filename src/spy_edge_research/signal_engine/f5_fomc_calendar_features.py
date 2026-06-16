"""F5 — pre-FOMC calendar gate (placebo / decay monitor) (M122).

Pre-registered in ``docs/PREREG_F5.md`` (immutable). **This is a pre-registered
placebo, not an edge candidate** — its designed-for outcome is a null. F5
conditions the same Config-A Baltussen predictor (``r_rod`` prev close→15:30, trade
15:30→16:00) on a scheduled-FOMC-eve flag. The calendar is known years in advance,
so the gate is strictly causal.

``is_fomc_eve_t`` = 1 if the next regular trading session after date ``t`` is a
scheduled FOMC **decision/announcement** day (the 2nd day of a two-day meeting).
Variants:
  - ``c1`` restrict — trade only on FOMC-eve days.
  - ``c2`` exclude  — trade only on non-FOMC-eve days (the guard complement).

Grid: 4 thresholds × 2 variants = 8 cells, encoded as 16 directional ``event_f5_*``
columns. Scheduled FOMC announcement dates 2024–2026 are embedded below from
federalreserve.gov/monetarypolicy/fomccalendars.htm. Research-only.
"""

from __future__ import annotations

import datetime as _dt

import pandas as pd

from spy_edge_research.signal_engine._rest_of_day import (
    build_rest_of_day_context,
    map_date_flag_to_decision_bar,
    safe_bool,
    threshold_tag,
    validate_thresholds,
)

F5_EVENT_PREFIX = "event_f5_"
F5_VARIANTS: tuple[str, ...] = ("c1", "c2")
F5_THRESHOLDS: tuple[float, ...] = (0.0, 0.0010, 0.0025, 0.0050)

# Scheduled FOMC decision (2nd-day / announcement) dates, 2024–2026.
# Source: Federal Reserve FOMC meeting calendars (known years in advance → causal).
FOMC_ANNOUNCEMENT_DATES: tuple[_dt.date, ...] = (
    _dt.date(2024, 1, 31), _dt.date(2024, 3, 20), _dt.date(2024, 5, 1),
    _dt.date(2024, 6, 12), _dt.date(2024, 7, 31), _dt.date(2024, 9, 18),
    _dt.date(2024, 11, 7), _dt.date(2024, 12, 18),
    _dt.date(2025, 1, 29), _dt.date(2025, 3, 19), _dt.date(2025, 5, 7),
    _dt.date(2025, 6, 18), _dt.date(2025, 7, 30), _dt.date(2025, 9, 17),
    _dt.date(2025, 10, 29), _dt.date(2025, 12, 10),
    _dt.date(2026, 1, 28), _dt.date(2026, 3, 18), _dt.date(2026, 4, 29),
    _dt.date(2026, 6, 17), _dt.date(2026, 7, 29), _dt.date(2026, 9, 16),
    _dt.date(2026, 10, 28), _dt.date(2026, 12, 9),
)


def add_f5_fomc_calendar_features(
    df: pd.DataFrame,
    *,
    variants: tuple[str, ...] = F5_VARIANTS,
    thresholds: tuple[float, ...] = F5_THRESHOLDS,
    announcement_dates: tuple[_dt.date, ...] = FOMC_ANNOUNCEMENT_DATES,
    timestamp_col: str = "timestamp",
    open_col: str = "open",
    close_col: str = "close",
    timezone: str = "America/New_York",
    session_open: str = "09:30",
    session_close: str = "16:00",
    cutoff_time: str = "15:30",
) -> pd.DataFrame:
    """Add causal F5 FOMC-eve-gated momentum event columns (placebo)."""
    validate_thresholds(thresholds)
    for v in variants:
        if v not in F5_VARIANTS:
            raise ValueError(f"unknown F5 variant: {v!r}")

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
    result["f5_decision_bar"] = ctx.decision_bar
    result["f5_r_rod"] = ctx.r_rod

    spy_dates = list(ctx.per_date_last_close.index)
    ann = set(announcement_dates)
    # FOMC-eve[t] = the next trading session is an announcement day. Causal.
    eve_flags = {
        d: (i + 1 < len(spy_dates) and spy_dates[i + 1] in ann)
        for i, d in enumerate(spy_dates)
    }
    eve_by_date = pd.Series(eve_flags, dtype=bool)
    result["f5_is_fomc_eve"] = map_date_flag_to_decision_bar(
        eve_by_date, decision_bar=ctx.decision_bar, trading_date=ctx.trading_date, index=result.index
    )

    for variant in variants:
        if variant == "c1":  # restrict: trade only on FOMC-eve days
            gate_by_date = eve_by_date
        else:  # c2 exclude: trade only on non-FOMC-eve days
            gate_by_date = ~eve_by_date
        active = map_date_flag_to_decision_bar(
            gate_by_date, decision_bar=ctx.decision_bar, trading_date=ctx.trading_date, index=result.index
        )
        result[f"f5_gate_{variant}"] = active
        for tau in thresholds:
            base = f"{F5_EVENT_PREFIX}{variant}_{threshold_tag(tau)}"
            result[f"{base}_long"] = safe_bool(
                ctx.decision_bar & active & (ctx.r_rod > tau), result.index
            )
            result[f"{base}_short"] = safe_bool(
                ctx.decision_bar & active & (ctx.r_rod < -tau), result.index
            )
    return result


def find_f5_event_columns(df: pd.DataFrame) -> list[str]:
    """Return the F5 event columns present in ``df`` (sorted)."""
    return sorted(c for c in df.columns if c.startswith(F5_EVENT_PREFIX))
