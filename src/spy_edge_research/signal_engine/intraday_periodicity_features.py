"""F9 — intraday periodicity / same-half-hour-bucket continuation (M125).

Pre-registered in ``docs/PREREG_F9.md`` (immutable). NEW Family 6. The half-hour
return in a given RTH bucket is hypothesized to continue from the same bucket on
prior days (Heston, Korajczyk & Sadka 2010). The native effect is cross-sectional;
on single-asset SPY it reduces to own same-bucket autocorrelation, weaker and
bounce-contaminated — hence the bounce-only synthetic placebo is the binding control.

Causal construction (no lookahead):
- 13 half-hour buckets per session (09:30-10:00, ..., 15:30-16:00). The realized
  bucket return is ``close[last bar]/close[first bar] - 1`` per (date, bucket).
- Predictor at the **start bar** of bucket b on day t: an aggregate of the SAME
  bucket's realized return on **prior** days (``.shift(1)`` over the date axis):
  ``lag1`` (yesterday), ``mean5``, ``mean40``.
- Position (continuation): ``long if agg > +tau ; short if agg < -tau``; held one
  bucket (30 min), scored by ``forward_return_30m``.
- tau: ``0`` or ``sig`` (trailing rolling std of the bucket return, shifted).
- scope: ``all`` 13 buckets or ``ends`` (first + last bucket only).

3 lags x 2 tau x 2 scope = 12 cells -> 24 directional ``event_f9_*`` columns.
SPY 1-min only. Research-only; no authorization.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from spy_edge_research.signal_engine._rest_of_day import (
    local_datetime,
    require_columns,
    safe_bool,
)

F9_EVENT_PREFIX = "event_f9_"
F9_LAGS: tuple[str, ...] = ("lag1", "mean5", "mean40")
F9_THRESHOLDS: tuple[str, ...] = ("t0", "sig")
F9_SCOPES: tuple[str, ...] = ("all", "ends")
_N_BUCKETS = 13
_SIG_WINDOW = 20


def add_intraday_periodicity_features(
    df: pd.DataFrame,
    *,
    lags: tuple[str, ...] = F9_LAGS,
    thresholds: tuple[str, ...] = F9_THRESHOLDS,
    scopes: tuple[str, ...] = F9_SCOPES,
    timestamp_col: str = "timestamp",
    close_col: str = "close",
    timezone: str = "America/New_York",
    session_open: str = "09:30",
    session_close: str = "16:00",
) -> pd.DataFrame:
    """Add causal F9 same-bucket-continuation event columns."""
    require_columns(df, [timestamp_col, close_col])
    for lg in lags:
        if lg not in F9_LAGS:
            raise ValueError(f"unknown F9 lag: {lg!r}")
    for th in thresholds:
        if th not in F9_THRESHOLDS:
            raise ValueError(f"unknown F9 threshold: {th!r}")
    for sc in scopes:
        if sc not in F9_SCOPES:
            raise ValueError(f"unknown F9 scope: {sc!r}")

    result = df.copy()
    local = local_datetime(result[timestamp_col], timezone)
    trading_date = pd.Series(local.dt.date, index=result.index)
    minute_of_day = pd.Series(local.dt.hour * 60 + local.dt.minute, index=result.index)
    open_min = _minute(session_open)
    close_min = _minute(session_close)
    in_session = (minute_of_day >= open_min) & (minute_of_day < close_min)
    bucket = ((minute_of_day - open_min) // 30).where(in_session)

    grp = result.assign(_d=trading_date, _b=bucket).groupby(["_d", "_b"])
    first_close = grp[close_col].transform("first")
    last_close = grp[close_col].transform("last")
    bucket_ret = (last_close.div(first_close.replace(0, np.nan)) - 1.0).where(in_session)
    bucket_start = in_session & (grp.cumcount() == 0)
    result["f9_bucket"] = bucket
    result["f9_bucket_start"] = safe_bool(bucket_start, result.index)

    # (date x bucket) table of realized bucket returns.
    per_db = bucket_ret.where(bucket_start).groupby([trading_date, bucket]).first()
    table = per_db.unstack(level=1).sort_index()  # rows = date, cols = bucket id

    agg_tables = {
        "lag1": table.shift(1),
        "mean5": table.rolling(5, min_periods=5).mean().shift(1),
        "mean40": table.rolling(40, min_periods=40).mean().shift(1),
    }
    sigma_table = table.rolling(_SIG_WINDOW, min_periods=_SIG_WINDOW).std(ddof=1).shift(1)

    end_buckets = {0, _N_BUCKETS - 1}
    for lg in lags:
        agg = _map_table_to_start_bars(
            agg_tables[lg], trading_date=trading_date, bucket=bucket,
            bucket_start=bucket_start, index=result.index,
        )
        for th in thresholds:
            if th == "t0":
                tau = pd.Series(0.0, index=result.index)
            else:
                tau = _map_table_to_start_bars(
                    sigma_table, trading_date=trading_date, bucket=bucket,
                    bucket_start=bucket_start, index=result.index,
                ).abs()
            long_sig = bucket_start & (agg > tau)
            short_sig = bucket_start & (agg < -tau)
            for sc in scopes:
                if sc == "ends":
                    scope_mask = bucket.isin(end_buckets).fillna(False)
                else:
                    scope_mask = pd.Series(True, index=result.index)
                base = f"{F9_EVENT_PREFIX}{lg}_{th}_{sc}"
                result[f"{base}_long"] = safe_bool(long_sig & scope_mask, result.index)
                result[f"{base}_short"] = safe_bool(short_sig & scope_mask, result.index)
    return result


def find_f9_event_columns(df: pd.DataFrame) -> list[str]:
    """Return the F9 event columns present in ``df`` (sorted)."""
    return sorted(c for c in df.columns if c.startswith(F9_EVENT_PREFIX))


def _map_table_to_start_bars(
    table: pd.DataFrame, *, trading_date: pd.Series, bucket: pd.Series,
    bucket_start: pd.Series, index: pd.Index,
) -> pd.Series:
    """Look up a (date x bucket) table value at each bucket-start bar."""
    out = pd.Series(np.nan, index=index, dtype="float64")
    start_idx = bucket_start[bucket_start].index
    if len(start_idx) == 0 or table.empty:
        return out
    stacked = table.stack()  # MultiIndex (date, bucket) -> value; missing keys -> get default
    keys = list(zip(trading_date.loc[start_idx], bucket.loc[start_idx]))
    out.loc[start_idx] = [stacked.get(k, np.nan) for k in keys]
    return out


def _minute(clock: str) -> int:
    hh, mm = clock.split(":")
    return int(hh) * 60 + int(mm)
