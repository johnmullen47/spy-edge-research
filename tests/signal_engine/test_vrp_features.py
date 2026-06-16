"""Tests for F6 VRP-timing features (M125)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from spy_edge_research.signal_engine.vrp_features import (
    F6_THRESHOLDS_SIGMA,
    add_vrp_features,
    find_f6_event_columns,
)

NY = "America/New_York"


def _frame(ndays=80, base=100.0, seed=0):
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
            px *= np.exp(rng.randn() * 2e-4)
            rows.append({"timestamp": ts, "open": px, "high": px, "low": px,
                         "close": px, "volume": 1000})
    return pd.DataFrame(rows)


def _vix(frame, level=18.0):
    dates = sorted(pd.to_datetime(frame["timestamp"]).dt.tz_convert(NY).dt.date.unique())
    return pd.DataFrame({"vix": [level] * len(dates)}, index=dates)


def test_column_count_is_six():
    df = add_vrp_features(_frame(), vix_frame=_vix(_frame()))
    assert len(find_f6_event_columns(df)) == len(F6_THRESHOLDS_SIGMA) * 2 == 6


def test_inactive_without_vix():
    df = add_vrp_features(_frame(), vix_frame=None)
    cols = find_f6_event_columns(df)
    assert cols and df[cols].to_numpy().sum() == 0


def test_events_fire_only_on_last_bar():
    df = add_vrp_features(_frame(), vix_frame=_vix(_frame()), zscore_lookback_days=20)
    cols = find_f6_event_columns(df)
    assert (df[cols].any(axis=1) & ~df["f6_last_bar"]).sum() == 0


def test_long_short_are_threshold_ordered():
    # higher tau is a subset of lower tau (same direction).
    df = add_vrp_features(_frame(seed=3), vix_frame=_vix(_frame(seed=3), level=25.0),
                          zscore_lookback_days=20)
    assert (df["event_f6_z10_long"] & ~df["event_f6_z0_long"]).sum() == 0
    assert (df["event_f6_z10_short"] & ~df["event_f6_z0_short"]).sum() == 0


def test_no_lookahead_truncation_stable_on_early_last_bar():
    # The VRP z-score on an early session must not change when later sessions are
    # dropped (it uses only trailing data).
    full = add_vrp_features(_frame(ndays=80), vix_frame=_vix(_frame(ndays=80)), zscore_lookback_days=20)
    src = _frame(ndays=80)
    local = pd.to_datetime(src["timestamp"]).dt.tz_convert(NY)
    cut = local.dt.date <= sorted(local.dt.date.unique())[50]
    trunc = add_vrp_features(src[cut].reset_index(drop=True),
                             vix_frame=_vix(src[cut].reset_index(drop=True)), zscore_lookback_days=20)
    f = full[full["f6_last_bar"]].reset_index(drop=True)
    t = trunc[trunc["f6_last_bar"]].reset_index(drop=True)
    np.testing.assert_allclose(f["f6_vrp_z"].to_numpy()[:40], t["f6_vrp_z"].to_numpy()[:40], equal_nan=True)


@pytest.mark.parametrize("kwargs", [{"zscore_lookback_days": 0}, {"thresholds_sigma": (-1.0,)}])
def test_invalid_arguments_rejected(kwargs):
    with pytest.raises(ValueError):
        add_vrp_features(_frame(ndays=10), vix_frame=_vix(_frame(ndays=10)), **kwargs)
