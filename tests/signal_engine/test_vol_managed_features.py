"""Tests for F7 volatility-managed exposure features (M125)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from spy_edge_research.signal_engine.vol_managed_features import (
    add_vol_managed_features,
    find_f7_event_columns,
)

NY = "America/New_York"


def _frame(ndays=80, base=100.0, seed=0, vol=2e-4):
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
            px *= np.exp(rng.randn() * vol)
            rows.append({"timestamp": ts, "open": px, "high": px, "low": px,
                         "close": px, "volume": 1000})
    return pd.DataFrame(rows)


def _vix(frame, level=18.0):
    dates = sorted(pd.to_datetime(frame["timestamp"]).dt.tz_convert(NY).dt.date.unique())
    return pd.DataFrame({"vix": [level] * len(dates)}, index=dates)


def test_column_count_is_six():
    df = add_vol_managed_features(_frame(), vix_frame=_vix(_frame()), garch_burnin_days=20)
    assert len(find_f7_event_columns(df)) == 3 * 2 == 6  # 3 estimators x 2 targets


def test_events_fire_only_on_last_bar():
    df = add_vol_managed_features(_frame(), vix_frame=_vix(_frame()),
                                  target_lookback_days=20, garch_burnin_days=20)
    cols = find_f7_event_columns(df)
    assert (df[cols].any(axis=1) & ~df["f7_last_bar"]).sum() == 0


def test_ten_pct_target_fires_when_realized_vol_below_10pct():
    # Very low intraday vol -> realized annualized vol well under 10% -> the
    # realized/ten variant should be active (long) on warmed-up sessions.
    df = add_vol_managed_features(_frame(vol=1e-5), vix_frame=_vix(_frame(vol=1e-5)),
                                  target_lookback_days=20, garch_burnin_days=20)
    last = df[df["f7_last_bar"]]
    assert last["event_f7_realized_ten_long"].sum() > 0


def test_vix_estimator_inactive_without_vix():
    df = add_vol_managed_features(_frame(), vix_frame=None, target_lookback_days=20, garch_burnin_days=20)
    vix_cols = [c for c in find_f7_event_columns(df) if c.startswith("event_f7_vix_")]
    assert vix_cols and df[vix_cols].to_numpy().sum() == 0


def test_high_vol_above_10pct_target_does_not_fire_realized_ten():
    # Large intraday vol -> realized annualized vol far above 10% -> never full
    # exposure under the 10% target.
    df = add_vol_managed_features(_frame(vol=5e-3), vix_frame=_vix(_frame(vol=5e-3)),
                                  target_lookback_days=20, garch_burnin_days=20)
    assert df["event_f7_realized_ten_long"].sum() == 0


@pytest.mark.parametrize("kwargs", [{"estimators": ("nope",)}, {"targets": ("nope",)},
                                    {"target_lookback_days": 0}])
def test_invalid_arguments_rejected(kwargs):
    with pytest.raises(ValueError):
        add_vol_managed_features(_frame(ndays=10), vix_frame=_vix(_frame(ndays=10)), **kwargs)
