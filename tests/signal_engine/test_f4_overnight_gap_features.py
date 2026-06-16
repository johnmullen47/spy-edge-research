"""Tests for F4 overnight-gap-conditioned momentum features (M122)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from spy_edge_research.signal_engine.f4_overnight_gap_features import (
    F4_THRESHOLDS,
    F4_VARIANTS,
    add_f4_overnight_gap_features,
    find_f4_event_columns,
)

NY = "America/New_York"


def _frame(specs: list[tuple[float, float]], *, base: float = 100.0) -> pd.DataFrame:
    """Bars 09:30->15:59 per session. specs = list of (r_rod, gap).

    The 09:30 bar's OPEN carries the overnight gap (open = base*exp(gap)); the 15:30
    bar's CLOSE carries r_rod (= base*exp(r_rod)); every session ends at ``base`` so
    the prior session's close is ``base``. Hence (for day >= 1):
    r_rod = log(close[15:30]/prior_close) = r, gap = log(open[09:30]/prior_close) = g.
    """
    rows = []
    start = pd.Timestamp("2024-01-02", tz=NY)
    for day, (r, g) in enumerate(specs):
        date = start + pd.Timedelta(days=day)
        for minute in range(390):  # 09:30 .. 15:59
            ts = date + pd.Timedelta(hours=9, minutes=30 + minute)
            mod = ts.hour * 60 + ts.minute
            o = c = base
            if mod == 9 * 60 + 30:
                o = base * np.exp(g)
            if mod == 15 * 60 + 30:
                o = c = base * np.exp(r)
            rows.append({"timestamp": ts, "open": o, "close": c, "volume": 1000})
    return pd.DataFrame(rows)


def test_full_grid_column_count():
    df = add_f4_overnight_gap_features(_frame([(0.002, 0.001), (0.002, 0.001)]))
    cols = find_f4_event_columns(df)
    # 3 variants x 4 thresholds x 2 directions = 24.
    assert len(cols) == len(F4_VARIANTS) * len(F4_THRESHOLDS) * 2 == 24


def test_g2_sign_agreement_takes_position_only_when_gap_agrees():
    # day1: up momentum + up gap -> long allowed. day2: up momentum + down gap ->
    # long suppressed (disagreement). day3: down momentum + down gap -> short allowed.
    df = add_f4_overnight_gap_features(
        _frame([(0.0, 0.0), (0.005, 0.004), (0.005, -0.004), (-0.005, -0.004)])
    )
    dec = df[df["f4_decision_bar"]].reset_index(drop=True)
    assert bool(dec.loc[1, "event_f4_g2_t0_long"]) is True   # agree up
    assert bool(dec.loc[2, "event_f4_g2_t0_long"]) is False  # disagree
    assert bool(dec.loc[3, "event_f4_g2_t0_short"]) is True  # agree down


def test_g1_magnitude_gate_requires_large_gap_vs_trailing():
    # Day 0 has no gap; with lookback=2 + shift(1) the trailing tercile first warms
    # up on day 3. Seed small gaps, then a large gap on day 3 -> g1 active there.
    df = add_f4_overnight_gap_features(
        _frame([(0.003, 0.0005), (0.003, 0.0005), (0.003, 0.0005), (0.003, 0.02)]),
        gap_lookback_days=2,
    )
    dec = df[df["f4_decision_bar"]].reset_index(drop=True)
    assert bool(dec.loc[3, "f4_large_gap"]) is True
    assert bool(dec.loc[3, "event_f4_g1_t0_long"]) is True
    # the seed days have no trailing tercile yet -> inactive
    assert bool(dec.loc[1, "f4_large_gap"]) is False


def test_g3_is_intersection_of_g1_and_g2():
    df = add_f4_overnight_gap_features(
        _frame([(0.003, 0.0005), (0.003, 0.0005), (0.004, 0.02), (-0.004, -0.02)]),
        gap_lookback_days=2,
    )
    # g3 long must be a subset of both g1 long and g2 long.
    assert (df["event_f4_g3_t0_long"] & ~df["event_f4_g1_t0_long"]).sum() == 0
    assert (df["event_f4_g3_t0_long"] & ~df["event_f4_g2_t0_long"]).sum() == 0


def test_events_fire_only_on_decision_bar():
    df = add_f4_overnight_gap_features(_frame([(0.002, 0.002), (0.002, -0.002), (0.003, 0.003)]))
    cols = find_f4_event_columns(df)
    assert (df[cols].any(axis=1) & ~df["f4_decision_bar"]).sum() == 0


def test_overnight_gap_value_matches_construction():
    df = add_f4_overnight_gap_features(_frame([(0.0, 0.0), (0.001, 0.003)]))
    dec = df[df["f4_decision_bar"]].reset_index(drop=True)
    np.testing.assert_allclose(dec.loc[1, "f4_overnight_gap"], 0.003, atol=1e-9)


def test_no_lookahead_final_session_stable_when_truncated():
    full = add_f4_overnight_gap_features(_frame([(0.002, 0.002), (0.003, -0.001), (0.004, 0.002)]))
    src = _frame([(0.002, 0.002), (0.003, -0.001), (0.004, 0.002)])
    local = pd.to_datetime(src["timestamp"]).dt.tz_convert(NY)
    last = local.dt.date.max()
    drop = (local.dt.date == last) & ((local.dt.hour * 60 + local.dt.minute) > 15 * 60 + 30)
    trunc = add_f4_overnight_gap_features(src[~drop].reset_index(drop=True))
    f = full[full["f4_decision_bar"]].reset_index(drop=True).iloc[-1]
    t = trunc[trunc["f4_decision_bar"]].reset_index(drop=True).iloc[-1]
    np.testing.assert_allclose(f["f4_r_rod"], t["f4_r_rod"])
    np.testing.assert_allclose(f["f4_overnight_gap"], t["f4_overnight_gap"])


@pytest.mark.parametrize("kwargs", [{"gap_lookback_days": 0}, {"variants": ("nope",)}, {"thresholds": (-1.0,)}])
def test_invalid_arguments_rejected(kwargs):
    with pytest.raises(ValueError):
        add_f4_overnight_gap_features(_frame([(0.001, 0.001), (0.001, 0.001)]), **kwargs)
