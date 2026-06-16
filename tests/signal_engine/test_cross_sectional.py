"""Tests for the M128 cross-sectional Fama-MacBeth harness.

All synthetic (freeze-compliant): no real predictor->target relationship is touched.
Validates: bucket-return construction, market neutralization, NW-mean inference,
planted-slope recovery, and that the seeded negative controls nullify a real effect.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from spy_edge_research.signal_engine.cross_sectional import (
    N_BUCKETS,
    bucket_index,
    build_bucket_returns,
    cross_sectional_continuation_test,
    market_neutralize,
    negative_controls,
    newey_west_mean,
)


def _planted_panel(n_days=400, n_stocks=120, rho=0.10, lag=5, seed=0):
    """Build bucket_returns with same-bucket lag-L cross-sectional autocorrelation rho."""
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2018-01-01", periods=n_days, freq="B", tz="America/New_York")
    syms = [f"S{i:03d}" for i in range(n_stocks)]
    frames = {}
    for b in range(N_BUCKETS):
        arr = np.zeros((n_days, n_stocks))
        eps = rng.normal(0, 1.0, size=(n_days, n_stocks))
        for d in range(n_days):
            if d - lag >= 0:
                arr[d] = rho * arr[d - lag] + np.sqrt(1 - rho**2) * eps[d]
            else:
                arr[d] = eps[d]
        frames[b] = pd.DataFrame(arr, index=dates, columns=syms)
    mask = pd.DataFrame(True, index=dates, columns=syms)
    return frames, mask


def test_bucket_index_grid():
    ts = pd.Timestamp("2020-03-02 09:30", tz="America/New_York")
    assert bucket_index(ts) == 0
    assert bucket_index(pd.Timestamp("2020-03-02 15:30", tz="America/New_York")) == 12
    assert bucket_index(pd.Timestamp("2020-03-02 09:45", tz="America/New_York")) is None


def test_build_bucket_returns_math():
    # One symbol, one day, 3 buckets with known prices.
    rows = [
        {"timestamp": "2020-03-02 09:30:00", "open": 100.0, "close": 101.0},
        {"timestamp": "2020-03-02 10:00:00", "open": 101.0, "close": 102.0},
        {"timestamp": "2020-03-02 10:30:00", "open": 102.0, "close": 100.0},
    ]
    bars = {"AAA": pd.DataFrame(rows)}
    frames = build_bucket_returns(bars)
    # bucket 0: log(101/100) (close/open of first bar)
    np.testing.assert_allclose(frames[0].iloc[0]["AAA"], np.log(101 / 100), atol=1e-9)
    # bucket 1: log(102/101) (close/prev close)
    np.testing.assert_allclose(frames[1].iloc[0]["AAA"], np.log(102 / 101), atol=1e-9)
    # bucket 2: log(100/102)
    np.testing.assert_allclose(frames[2].iloc[0]["AAA"], np.log(100 / 102), atol=1e-9)


def test_market_neutralize_demeans_rows():
    df = pd.DataFrame({"A": [1.0, 2.0], "B": [3.0, 4.0], "C": [5.0, 9.0]})
    out = market_neutralize(df)
    np.testing.assert_allclose(out.sum(axis=1).to_numpy(), [0.0, 0.0], atol=1e-12)


def test_market_neutralize_respects_mask():
    df = pd.DataFrame({"A": [1.0], "B": [3.0], "C": [100.0]})
    mask = pd.DataFrame({"A": [True], "B": [True], "C": [False]})
    out = market_neutralize(df, mask)
    assert np.isnan(out.iloc[0]["C"])
    # demean only over A,B -> mean 2.0
    np.testing.assert_allclose(out.iloc[0]["A"], -1.0, atol=1e-9)


def test_newey_west_mean_zero_for_centered_noise():
    rng = np.random.default_rng(1)
    x = rng.normal(0, 1, 1000)
    res = newey_west_mean(x, lags=12)
    assert abs(res["t_stat"]) < 3.0


def test_fama_macbeth_recovers_planted_slope():
    frames, mask = _planted_panel(rho=0.12, lag=5, seed=2)
    res = cross_sectional_continuation_test(frames, mask, lag=5, label="planted")
    assert res.mean_slope > 0.07           # recovers ~0.12
    assert res.t_stat > 5.0                 # strongly significant with planted effect
    assert res.n_days > 300


def test_negative_controls_kill_planted_effect():
    frames, mask = _planted_panel(rho=0.12, lag=5, seed=3)
    real = cross_sectional_continuation_test(frames, mask, lag=5)
    ctrl = negative_controls(frames, mask, lag=5, seed=42)
    for name, r in ctrl.items():
        assert abs(r.t_stat) < abs(real.t_stat) / 2, f"{name} not nullified: t={r.t_stat}"
        assert abs(r.mean_slope) < 0.03, f"{name} slope not ~0: {r.mean_slope}"


def test_wrong_lag_shows_no_effect():
    # Effect planted at lag 5; testing lag 7 should be ~null.
    frames, mask = _planted_panel(rho=0.12, lag=5, seed=4)
    res = cross_sectional_continuation_test(frames, mask, lag=7)
    assert abs(res.t_stat) < 3.0
