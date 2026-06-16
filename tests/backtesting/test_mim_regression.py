"""Tests for the M127 literature-faithful MIM regression harness.

All fixtures are SYNTHETIC (freeze-compliant: no real-data predictor->target
relationship is computed here). They verify the math and causality of the harness.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from spy_edge_research.backtesting.mim_regression import (
    build_mim_daily_frame,
    high_volatility_mask,
    negative_controls,
    newey_west_t,
    run_mim_regression,
)

NY = "America/New_York"


def _synthetic_bars(day_specs, *, base=400.0):
    """One synthetic RTH day per spec. spec = dict of clock->price multiplier set so
    prev_close, 10:00, 15:30, 16:00 take controlled values; intervening bars flat."""
    rows = []
    start = pd.Timestamp("2024-01-02", tz=NY)
    prev_last = base
    for d, spec in enumerate(day_specs):
        date = start + pd.Timedelta(days=d)
        p1000 = prev_last * spec.get("ha", 1.0)
        p1530 = prev_last * spec.get("hb", 1.0)
        p1600 = p1530 * spec.get("tgt", 1.0)
        for m in range(390):
            ts = date + pd.Timedelta(hours=9, minutes=30 + m)
            mod = ts.hour * 60 + ts.minute
            if mod >= 15 * 60 + 30:
                px = p1600 if mod >= 15 * 60 + 59 else p1530
            elif mod >= 10 * 60:
                px = p1530 if mod >= 15 * 60 else p1000
            else:
                px = prev_last
            rows.append({"timestamp": ts, "close": px})
        prev_last = p1600
    return pd.DataFrame(rows)


def test_daily_frame_predictors_are_causal_and_correct():
    # Day 1: prev_close=400; 10:00 = +1%, 15:30 = +2%, 16:00 = +0.5% vs 15:30.
    bars = _synthetic_bars([{}, {"ha": 1.01, "hb": 1.02, "tgt": 1.005}])
    f = build_mim_daily_frame(bars)
    row = f.iloc[-1]
    np.testing.assert_allclose(row["r_ha"], np.log(1.01), atol=1e-6)
    np.testing.assert_allclose(row["r_hb"], np.log(1.02), atol=1e-6)
    np.testing.assert_allclose(row["target"], np.log(1.005), atol=1e-6)


def test_newey_west_recovers_known_slope():
    rng = np.random.default_rng(0)
    x = rng.normal(0, 1, 500)
    y = 0.4 * x + rng.normal(0, 1, 500)
    r = newey_west_t(y, x)
    assert abs(r["beta"] - 0.4) < 0.1
    assert r["t_stat"] > 3  # strongly significant
    assert r["nw_lags"] >= 1 and r["n"] == 500


def test_newey_west_null_is_insignificant():
    rng = np.random.default_rng(1)
    x = rng.normal(0, 1, 500); y = rng.normal(0, 1, 500)
    r = newey_west_t(y, x)
    assert abs(r["t_stat"]) < 2.5  # no real relationship


def test_run_mim_regression_detects_injected_effect():
    rng = np.random.default_rng(2)
    n = 800
    x = rng.normal(0, 0.01, n)
    y = 0.3 * x + rng.normal(0, 0.01, n)
    frame = pd.DataFrame({"r_hb": x, "target": y})
    res = run_mim_regression(frame, predictor="r_hb", label="H_b")
    assert res.t_stat > 3 and res.corr > 0.1 and res.n == n


def test_negative_controls_kill_a_real_effect():
    rng = np.random.default_rng(3)
    n = 800
    x = rng.normal(0, 0.01, n)
    y = 0.3 * x + rng.normal(0, 0.01, n)
    frame = pd.DataFrame({"r_hb": x, "target": y})
    real = run_mim_regression(frame, predictor="r_hb", label="real")
    ctrls = negative_controls(frame, predictor="r_hb", seed=7)
    assert set(ctrls) == {"date_shuffled", "permuted_target", "randomized_timestamps", "lag_permuted"}
    # every control t-stat must be far below the real one
    for name, c in ctrls.items():
        assert abs(c.t_stat) < 0.5 * real.t_stat, f"{name} t={c.t_stat} vs real {real.t_stat}"


def test_high_volatility_mask_selects_upper_subsample():
    f = pd.DataFrame({"rod_rvol": np.arange(30) / 1000.0,
                      "r_hb": np.zeros(30), "target": np.zeros(30)})
    m = high_volatility_mask(f, quantile=2.0 / 3.0)
    assert m.sum() == 10  # top third of 30
    assert m.iloc[-1] and not m.iloc[0]


def test_negative_controls_reproducible_with_seed():
    rng = np.random.default_rng(4)
    frame = pd.DataFrame({"r_hb": rng.normal(0, 0.01, 300), "target": rng.normal(0, 0.01, 300)})
    a = negative_controls(frame, predictor="r_hb", seed=11)["date_shuffled"].t_stat
    b = negative_controls(frame, predictor="r_hb", seed=11)["date_shuffled"].t_stat
    assert a == b  # seeded reproducibility


@pytest.mark.parametrize("bad", [pd.DataFrame({"close": [1, 2]})])
def test_missing_columns_rejected(bad):
    with pytest.raises(ValueError):
        build_mim_daily_frame(bad)
