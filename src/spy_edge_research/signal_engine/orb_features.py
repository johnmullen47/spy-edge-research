"""F8 — Opening Range Breakout (ORB) on un-leveraged SPY (M125).

Pre-registered in ``docs/PREREG_F8.md`` (immutable). NEW Family 5. If SPY breaks out
of its opening range (first N minutes' high/low), intraday momentum is hypothesized
to continue into the close (Zarattini & Aziz 2023 — but on leveraged ETFs /
stocks-in-play; here strictly un-leveraged SPY, with the half-spread cost test as the
binding control).

Causal construction (no lookahead):
- Opening range over the first N minutes: ``OR_high`` / ``OR_low`` = high/low of bars
  with minute-of-day <= 09:30 + N.
- Entry: the **first** 1-min close beyond OR high (long) or OR low (short) after the
  OR window; one entry per direction per day. The event fires on that breakout bar
  (it uses only bars up to and including it).
- Trend filter (causal, evaluated at the breakout bar): ``none``; ``pclose`` (price
  vs prior-day close); ``vwap`` (price vs session VWAP so far).
- Outcome: held to the 16:00 close, scored by the ``forward_return_to_close`` label.

3 OR windows x 3 filters x {long,short} = 18 directional ``event_f8_*`` columns
(PREREG's 9 cells in the harness's directional encoding). SPY 1-min only.
Research-only; no authorization.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from spy_edge_research.signal_engine._rest_of_day import (
    local_datetime,
    require_columns,
    safe_bool,
)

F8_EVENT_PREFIX = "event_f8_"
F8_OR_WINDOWS: tuple[int, ...] = (5, 15, 30)
F8_FILTERS: tuple[str, ...] = ("none", "pclose", "vwap")


def add_orb_features(
    df: pd.DataFrame,
    *,
    or_windows: tuple[int, ...] = F8_OR_WINDOWS,
    filters: tuple[str, ...] = F8_FILTERS,
    timestamp_col: str = "timestamp",
    open_col: str = "open",
    high_col: str = "high",
    low_col: str = "low",
    close_col: str = "close",
    volume_col: str = "volume",
    timezone: str = "America/New_York",
    session_open: str = "09:30",
    session_close: str = "16:00",
) -> pd.DataFrame:
    """Add causal F8 opening-range-breakout event columns."""
    require_columns(df, [timestamp_col, high_col, low_col, close_col])
    for n in or_windows:
        if not isinstance(n, int) or isinstance(n, bool) or n < 1:
            raise ValueError("or_windows must be positive integers")
    for f in filters:
        if f not in F8_FILTERS:
            raise ValueError(f"unknown F8 filter: {f!r}")

    result = df.copy()
    local = local_datetime(result[timestamp_col], timezone)
    trading_date = pd.Series(local.dt.date, index=result.index)
    minute_of_day = pd.Series(local.dt.hour * 60 + local.dt.minute, index=result.index)
    open_min = _minute(session_open)
    close_min = _minute(session_close)
    in_session = (minute_of_day >= open_min) & (minute_of_day <= close_min)

    # Prior-day close (broadcast), for the pclose filter.
    close_in_session = result[close_col].where(in_session)
    per_date_last = close_in_session.groupby(trading_date).last()
    prior_close = trading_date.map(per_date_last.shift(1))

    # Session VWAP so far (causal cumulative), for the vwap filter.
    typical = (result[high_col] + result[low_col] + result[close_col]) / 3.0
    vol = pd.to_numeric(result.get(volume_col, pd.Series(1.0, index=result.index)), errors="coerce").fillna(0.0)
    tp_vol = (typical * vol).where(in_session)
    cum_tpv = tp_vol.groupby(trading_date).cumsum()
    cum_v = vol.where(in_session).groupby(trading_date).cumsum()
    vwap = cum_tpv.div(cum_v.replace(0, np.nan))

    price = result[close_col]
    for n in or_windows:
        in_or = in_session & (minute_of_day <= open_min + n)
        after_or = in_session & (minute_of_day > open_min + n)
        # Opening range over the first N minutes (complete once after_or begins, so
        # using it on after-OR breakout bars is causal — no lookahead).
        or_high_day = result[high_col].where(in_or).groupby(trading_date).max()
        or_low_day = result[low_col].where(in_or).groupby(trading_date).min()
        orh = trading_date.map(or_high_day)
        orl = trading_date.map(or_low_day)

        first_long = _first_true_per_day(after_or & (price > orh), trading_date)
        first_short = _first_true_per_day(after_or & (price < orl), trading_date)

        for f in filters:
            if f == "none":
                long_ok = pd.Series(True, index=result.index)
                short_ok = pd.Series(True, index=result.index)
            elif f == "pclose":
                long_ok = price > prior_close
                short_ok = price < prior_close
            else:  # vwap
                long_ok = price > vwap
                short_ok = price < vwap
            base = f"{F8_EVENT_PREFIX}n{n}_{f}"
            result[f"{base}_long"] = safe_bool(first_long & long_ok, result.index)
            result[f"{base}_short"] = safe_bool(first_short & short_ok, result.index)
    return result


def find_f8_event_columns(df: pd.DataFrame) -> list[str]:
    """Return the F8 event columns present in ``df`` (sorted)."""
    return sorted(c for c in df.columns if c.startswith(F8_EVENT_PREFIX))


def _first_true_per_day(mask: pd.Series, trading_date: pd.Series) -> pd.Series:
    """Mark only the first True bar of each day (the day's first breakout)."""
    mask = mask.fillna(False).astype(bool)
    cum = mask.groupby(trading_date).cumsum()
    return mask & (cum == 1)


def _minute(clock: str) -> int:
    hh, mm = clock.split(":")
    return int(hh) * 60 + int(mm)
