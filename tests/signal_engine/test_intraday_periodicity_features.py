"""Tests for F9 intraday-periodicity features (M125)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from spy_edge_research.signal_engine.intraday_periodicity_features import (
    add_intraday_periodicity_features,
    find_f9_event_columns,
)

NY = "America/New_York"


def _frame(ndays=60, base=100.0, seed=0):
    rng = np.random.RandomState(seed)
    rows = []
    start = pd.Timestamp("2024-06-03", tz=NY)
    px = base
    for d in range(ndays):
        date = start + pd.Timedelta(days=d)
        if date.weekday() >= 5:
            continue
        for m in range(390):
            ts = date + pd.Timedelta(hours=9, minutes=30 + m)
            px *= np.exp(rng.randn() * 3e-4)
            rows.append({"timestamp": ts, "open": px, "high": px, "low": px,
                         "close": px, "volume": 1000})
    return pd.DataFrame(rows)


def test_column_count_is_twentyfour():
    df = add_intraday_periodicity_features(_frame())
    # 3 lags x 2 thresholds x 2 scopes = 12 cells, each long + short = 24 columns.
    assert len(find_f9_event_columns(df)) == 3 * 2 * 2 * 2 == 24


def test_events_fire_only_on_bucket_start():
    df = add_intraday_periodicity_features(_frame())
    cols = find_f9_event_columns(df)
    assert (df[cols].any(axis=1) & ~df["f9_bucket_start"]).sum() == 0


def test_ends_scope_only_fires_in_first_or_last_bucket():
    df = add_intraday_periodicity_features(_frame())
    ends_cols = [c for c in find_f9_event_columns(df) if "_ends_" in c]
    fired = df[ends_cols].any(axis=1)
    buckets_fired = set(df.loc[fired, "f9_bucket"].dropna().unique())
    assert buckets_fired <= {0.0, 12.0}


def test_long_short_mutually_exclusive_at_t0():
    df = add_intraday_periodicity_features(_frame(seed=2))
    # at threshold 0, agg>0 and agg<0 cannot both hold
    assert (df["event_f9_lag1_t0_all_long"] & df["event_f9_lag1_t0_all_short"]).sum() == 0


def test_no_lookahead_truncation_stable():
    full = add_intraday_periodicity_features(_frame(ndays=60))
    src = _frame(ndays=60)
    local = pd.to_datetime(src["timestamp"]).dt.tz_convert(NY)
    cut = local.dt.date <= sorted(local.dt.date.unique())[40]
    trunc = add_intraday_periodicity_features(src[cut].reset_index(drop=True))
    fcols = find_f9_event_columns(full)
    # the union of fires on the first 40 days must match between full and truncated
    f_fire = full.loc[full["timestamp"].isin(trunc["timestamp"]), fcols].reset_index(drop=True)
    t_fire = trunc[fcols].reset_index(drop=True)
    assert int((f_fire.to_numpy() != t_fire.to_numpy()).sum()) == 0


@pytest.mark.parametrize("kwargs", [{"lags": ("nope",)}, {"thresholds": ("nope",)}, {"scopes": ("nope",)}])
def test_invalid_arguments_rejected(kwargs):
    with pytest.raises(ValueError):
        add_intraday_periodicity_features(_frame(ndays=10), **kwargs)
