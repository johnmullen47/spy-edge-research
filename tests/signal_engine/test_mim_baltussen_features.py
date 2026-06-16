"""Tests for MIM-Baltussen rest-of-day momentum features (M121)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from spy_edge_research.signal_engine.mim_baltussen_features import (
    GATE_GARCH_GT_MEDIAN,
    GATE_UNCONDITIONAL,
    GATE_VIX_GT_20,
    MIMB_CONFIGS,
    MIMB_THRESHOLDS,
    add_mim_baltussen_features,
    find_mim_baltussen_event_columns,
    mim_baltussen_to_close_horizons,
)

NY = "America/New_York"


def _session_frame(rod_returns: list[float], *, base: float = 100.0) -> pd.DataFrame:
    """Build 1-min bars 09:30->15:59 for each session with a controlled r_rod.

    Every close is ``base`` except the single 15:30 bar, which is ``base*exp(r)``.
    So each session ends at ``base`` -> the prior session's last close is ``base``,
    and for Config A (cutoff 15:30):
    r_rod = log(close[15:30] / prior_close) = log(base*exp(r) / base) = r exactly.
    (The 15:30 spike reverts immediately, which is irrelevant: the predictor reads
    only the cutoff-bar close.)
    """
    rows = []
    start = pd.Timestamp("2024-01-02", tz=NY)
    for day, r in enumerate(rod_returns):
        date = start + pd.Timedelta(days=day)
        for minute in range(0, 390):  # 09:30 .. 15:59 (390 bars)
            ts = date + pd.Timedelta(hours=9, minutes=30 + minute)
            mod = ts.hour * 60 + ts.minute
            close = base * np.exp(r) if mod == 15 * 60 + 30 else base
            rows.append({"timestamp": ts, "open": close, "close": close, "volume": 1000})
    return pd.DataFrame(rows)


def test_decision_bar_is_first_bar_at_or_after_cutoff():
    df = add_mim_baltussen_features(_session_frame([0.001, -0.001, 0.001]))
    dec = df[df["mimb_a_decision_bar"]]
    assert len(dec) == 3
    assert all(pd.to_datetime(dec["timestamp"]).dt.strftime("%H:%M") == "15:30")
    decb = df[df["mimb_b_decision_bar"]]
    assert all(pd.to_datetime(decb["timestamp"]).dt.strftime("%H:%M") == "15:00")


def test_r_rod_is_prev_close_to_cutoff_return():
    # Day 0 has no prior session -> r_rod NaN. Day 1 onward: r_rod == that day's r.
    df = add_mim_baltussen_features(_session_frame([0.002, 0.003, -0.004]))
    dec = df[df["mimb_a_decision_bar"]].reset_index(drop=True)
    assert pd.isna(dec.loc[0, "mimb_a_r_rod"])  # no prior close
    np.testing.assert_allclose(dec.loc[1, "mimb_a_r_rod"], 0.003, atol=1e-9)
    np.testing.assert_allclose(dec.loc[2, "mimb_a_r_rod"], -0.004, atol=1e-9)


def test_momentum_direction_long_on_up_short_on_down_unconditional_tau0():
    df = add_mim_baltussen_features(_session_frame([0.001, 0.005, -0.005]))
    dec = df[df["mimb_a_decision_bar"]].reset_index(drop=True)
    long_col = f"event_mimb_a_{GATE_UNCONDITIONAL}_t0_long"
    short_col = f"event_mimb_a_{GATE_UNCONDITIONAL}_t0_short"
    # Day 1: up move -> long fires, short does not.
    assert bool(dec.loc[1, long_col]) is True
    assert bool(dec.loc[1, short_col]) is False
    # Day 2: down move -> short fires, long does not.
    assert bool(dec.loc[2, short_col]) is True
    assert bool(dec.loc[2, long_col]) is False


def test_threshold_gates_out_small_moves():
    # r_rod = 0.0015 clears tau=0.0010 but not tau=0.0025.
    df = add_mim_baltussen_features(_session_frame([0.001, 0.0015]))
    dec = df[df["mimb_a_decision_bar"]].reset_index(drop=True)
    assert bool(dec.loc[1, f"event_mimb_a_{GATE_UNCONDITIONAL}_t10_long"]) is True
    assert bool(dec.loc[1, f"event_mimb_a_{GATE_UNCONDITIONAL}_t25_long"]) is False


def test_events_fire_only_on_decision_bar():
    df = add_mim_baltussen_features(_session_frame([0.002, -0.002, 0.003]))
    cols = find_mim_baltussen_event_columns(df)
    fired = df[cols].any(axis=1)
    off_a = fired & ~df["mimb_a_decision_bar"] & ~df["mimb_b_decision_bar"]
    assert off_a.sum() == 0


def test_vix_gates_inactive_without_vix_series():
    df = add_mim_baltussen_features(_session_frame([0.005, 0.005, 0.005, 0.005]))
    vix_cols = [c for c in find_mim_baltussen_event_columns(df) if GATE_VIX_GT_20 in c]
    assert vix_cols  # the columns still exist (family is fully represented)
    assert df[vix_cols].to_numpy().sum() == 0  # but never fire without VIX data


def test_vix_gate_fires_when_prior_close_vix_exceeds_threshold():
    frame = _session_frame([0.005, 0.005, 0.005])
    dates = sorted(pd.to_datetime(frame["timestamp"]).dt.tz_convert(NY).dt.date.unique())
    # VIX at prior close > 20 only before day 2 -> day 2 gate active.
    vix = pd.Series([10.0, 30.0, 12.0], index=dates)
    df = add_mim_baltussen_features(frame, vix_daily=vix)
    dec = df[df["mimb_a_decision_bar"]].reset_index(drop=True)
    long_col = f"event_mimb_a_{GATE_VIX_GT_20}_t0_long"
    # Day 1 uses day 0's VIX (10, not > 20) -> inactive; day 2 uses day 1's VIX (30) -> active.
    assert bool(dec.loc[1, long_col]) is False
    assert bool(dec.loc[2, long_col]) is True


def test_full_grid_column_count():
    df = add_mim_baltussen_features(_session_frame([0.001, 0.002]))
    cols = find_mim_baltussen_event_columns(df)
    # 2 configs x 4 gates x 4 thresholds x 2 directions = 64 directional columns.
    assert len(cols) == len(MIMB_CONFIGS) * 4 * len(MIMB_THRESHOLDS) * 2 == 64


def test_no_lookahead_truncating_after_decision_bar_is_stable():
    # r_rod at a session's decision bar must not change when that session's own
    # post-cutoff bars are removed (prior sessions are left whole — r_rod
    # legitimately reads the prior session's close).
    full = add_mim_baltussen_features(_session_frame([0.002, -0.002, 0.003]))
    src = _session_frame([0.002, -0.002, 0.003])
    local = pd.to_datetime(src["timestamp"]).dt.tz_convert(NY)
    last_date = local.dt.date.max()
    after_final_cutoff = (local.dt.date == last_date) & (
        (local.dt.hour * 60 + local.dt.minute) > (15 * 60 + 30)
    )
    truncated = add_mim_baltussen_features(src[~after_final_cutoff].reset_index(drop=True))
    f_last = full[full["mimb_a_decision_bar"]].reset_index(drop=True).iloc[-1]
    t_last = truncated[truncated["mimb_a_decision_bar"]].reset_index(drop=True).iloc[-1]
    np.testing.assert_allclose(f_last["mimb_a_r_rod"], t_last["mimb_a_r_rod"])


def test_zero_rod_fires_neither_direction_at_tau0():
    df = add_mim_baltussen_features(_session_frame([0.0, 0.0, 0.0]))
    dec = df[df["mimb_a_decision_bar"]]
    assert dec[f"event_mimb_a_{GATE_UNCONDITIONAL}_t0_long"].sum() == 0
    assert dec[f"event_mimb_a_{GATE_UNCONDITIONAL}_t0_short"].sum() == 0


def test_to_close_horizons():
    assert mim_baltussen_to_close_horizons() == (29, 59)


def test_garch_gate_present_and_boolean():
    df = add_mim_baltussen_features(_session_frame([0.01, -0.01, 0.02, -0.02, 0.03]))
    garch_cols = [c for c in find_mim_baltussen_event_columns(df) if GATE_GARCH_GT_MEDIAN in c]
    assert garch_cols
    # With a tiny sample the GARCH gate cannot warm up -> no fires, but columns exist.
    assert df[garch_cols].to_numpy().dtype == bool


@pytest.mark.parametrize(
    "kwargs",
    [
        {"regime_lookback_days": 0},
        {"regime_lookback_days": True},
        {"garch_burnin_days": 0},
        {"gates": ("not_a_gate",)},
        {"thresholds": (-0.1,)},
    ],
)
def test_invalid_arguments_rejected(kwargs):
    with pytest.raises(ValueError):
        add_mim_baltussen_features(_session_frame([0.001, -0.001]), **kwargs)
