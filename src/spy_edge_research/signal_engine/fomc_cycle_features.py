"""F10 — FOMC-cycle equity-premium timing (M125).

Pre-registered in ``docs/PREREG_F10.md`` (immutable). NEW Family 7. Since 1994 the
equity premium has accrued in even weeks of FOMC-cycle time (Cieslak, Morse &
Vissing-Jorgensen 2019). F10 is long SPY in even cycle weeks and flat/short in odd.
Distinct from F5 (which gated only the pre-FOMC *eve*).

Causal construction (the scheduled FOMC calendar is known years ahead; the event
fires on each session's last bar, scored by ``forward_return_{1,5}sess``):
- ``sessions_since`` = trading sessions since the most recent scheduled FOMC
  announcement; ``cycle week`` = ``sessions_since // 5``.
- Phase-definition variants (robustness to the exact phase boundary): ``strict``
  (week parity), ``shift`` (+1 session before binning), ``mid`` (first vs second
  half of the inter-meeting interval).
- Per phase: an **even-week long** column and an **odd-week short** column. The
  PREREG odd-week scheme {flat, short} maps to using just the long column (flat) or
  long+short (short); granularity {weekly, daily} is the 5-/1-session horizon. 3
  phases x {even-long, odd-short} = 6 columns -> 12 candidates.

Reuses the embedded 2024-2026 Fed calendar from F5. Research-only; no authorization.
"""

from __future__ import annotations

import bisect
import datetime as _dt

import numpy as np
import pandas as pd

from spy_edge_research.signal_engine._daily import (
    build_daily_session_context,
    map_date_flag_to_last_bar,
)
from spy_edge_research.signal_engine.f5_fomc_calendar_features import (
    FOMC_ANNOUNCEMENT_DATES,
)

F10_EVENT_PREFIX = "event_f10_"
F10_PHASES: tuple[str, ...] = ("strict", "shift", "mid")


def add_fomc_cycle_features(
    df: pd.DataFrame,
    *,
    phases: tuple[str, ...] = F10_PHASES,
    announcement_dates: tuple[_dt.date, ...] = FOMC_ANNOUNCEMENT_DATES,
    timestamp_col: str = "timestamp",
    close_col: str = "close",
    timezone: str = "America/New_York",
    session_open: str = "09:30",
    session_close: str = "16:00",
) -> pd.DataFrame:
    """Add causal F10 FOMC-cycle even/odd-week event columns (per session last bar)."""
    for p in phases:
        if p not in F10_PHASES:
            raise ValueError(f"unknown F10 phase: {p!r}")

    ctx = build_daily_session_context(
        df, timestamp_col=timestamp_col, close_col=close_col, timezone=timezone,
        session_open=session_open, session_close=session_close,
    )
    result = df.copy()
    result["f10_last_bar"] = ctx.last_bar

    dates = list(ctx.per_date_dates)
    ann = sorted(announcement_dates)
    even_by_phase = {p: {} for p in phases}
    defined_by_phase = {p: {} for p in phases}
    for i, d in enumerate(dates):
        k = bisect.bisect_right(ann, d) - 1  # most recent announcement <= d
        for p in phases:
            even_by_phase[p][d] = False
            defined_by_phase[p][d] = False
        if k < 0:
            continue  # before the first scheduled meeting in range -> undefined
        last_ann = ann[k]
        j = bisect.bisect_left(dates, last_ann)  # session index of (or after) the meeting
        sessions_since = i - j
        if sessions_since < 0:
            continue
        for p in phases:
            if p == "strict":
                even = (sessions_since // 5) % 2 == 0
            elif p == "shift":
                even = ((sessions_since + 1) // 5) % 2 == 0
            else:  # mid: first half of the inter-meeting interval = even
                nxt = ann[k + 1] if k + 1 < len(ann) else None
                if nxt is not None and nxt in dates:
                    interval = dates.index(nxt) - j
                    even = interval > 0 and (sessions_since / interval) < 0.5
                else:
                    even = (sessions_since // 5) % 2 == 0  # fallback near series end
            even_by_phase[p][d] = bool(even)
            defined_by_phase[p][d] = True

    for p in phases:
        defined = pd.Series(defined_by_phase[p], dtype=bool)
        even = pd.Series(even_by_phase[p], dtype=bool)
        even_flag = defined & even
        odd_flag = defined & ~even
        result[f"{F10_EVENT_PREFIX}{p}_even_long"] = map_date_flag_to_last_bar(
            even_flag, last_bar=ctx.last_bar, trading_date=ctx.trading_date, index=result.index,
        )
        result[f"{F10_EVENT_PREFIX}{p}_odd_short"] = map_date_flag_to_last_bar(
            odd_flag, last_bar=ctx.last_bar, trading_date=ctx.trading_date, index=result.index,
        )
    return result


def find_f10_event_columns(df: pd.DataFrame) -> list[str]:
    """Return the F10 event columns present in ``df`` (sorted)."""
    return sorted(c for c in df.columns if c.startswith(F10_EVENT_PREFIX))
