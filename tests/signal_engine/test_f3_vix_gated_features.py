"""Tests for F3 VIX-regime-gated momentum features (M122)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from spy_edge_research.signal_engine.f3_vix_gated_features import (
    F3_THRESHOLDS,
    F3_VARIANTS,
    add_f3_vix_gated_features,
    find_f3_event_columns,
)

NY = "America/New_York"


def _frame(r_rods: list[float], *, base: float = 100.0) -> pd.DataFrame:
    """Bars 09:30->15:59 per session; only the 15:30 close carries r_rod (= r)."""
    rows = []
    start = pd.Timestamp("2024-01-02", tz=NY)
    for day, r in enumerate(r_rods):
        date = start + pd.Timedelta(days=day)
        for minute in range(390):
            ts = date + pd.Timedelta(hours=9, minutes=30 + minute)
            mod = ts.hour * 60 + ts.minute
            close = base * np.exp(r) if mod == 15 * 60 + 30 else base
            rows.append({"timestamp": ts, "open": close, "close": close, "volume": 1000})
    return pd.DataFrame(rows)


def _dates(frame: pd.DataFrame) -> list:
    return sorted(pd.to_datetime(frame["timestamp"]).dt.tz_convert(NY).dt.date.unique())


def _vix(frame, vix=None, vix9d=None, vix3m=None) -> pd.DataFrame:
    d = _dates(frame)
    return pd.DataFrame(
        {
            "vix": vix if vix is not None else [15.0] * len(d),
            "vix9d": vix9d if vix9d is not None else [np.nan] * len(d),
            "vix3m": vix3m if vix3m is not None else [np.nan] * len(d),
        },
        index=d,
    )


def test_full_grid_column_count():
    df = add_f3_vix_gated_features(_frame([0.002, 0.002]), vix_frame=_vix(_frame([0.002, 0.002])))
    cols = find_f3_event_columns(df)
    assert len(cols) == len(F3_VARIANTS) * len(F3_THRESHOLDS) * 2 == 24


def test_inactive_without_vix_frame():
    df = add_f3_vix_gated_features(_frame([0.005, 0.005, 0.005]), vix_frame=None)
    cols = find_f3_event_columns(df)
    assert cols and df[cols].to_numpy().sum() == 0


def test_vix20_gate_uses_prior_session_close():
    fr = _frame([0.005, 0.005, 0.005])
    # VIX: day0=30 (>20), day1=10, day2=10. Day1 uses day0 prior -> active; day2 not.
    df = add_f3_vix_gated_features(fr, vix_frame=_vix(fr, vix=[30.0, 10.0, 10.0]))
    dec = df[df["f3_decision_bar"]].reset_index(drop=True)
    assert bool(dec.loc[1, "event_f3_vix20_t0_long"]) is True
    assert bool(dec.loc[2, "event_f3_vix20_t0_long"]) is False


def test_vixmed_gate_fires_above_trailing_median():
    fr = _frame([0.004, 0.004, 0.004, 0.004])
    # rising VIX: each day's prior exceeds the trailing median -> later days active.
    df = add_f3_vix_gated_features(
        fr, vix_frame=_vix(fr, vix=[10.0, 12.0, 25.0, 30.0]), regime_lookback_days=2
    )
    dec = df[df["f3_decision_bar"]].reset_index(drop=True)
    # day3: prior VIX=25 vs trailing median(of days1,2)=~ -> active
    assert bool(dec.loc[3, "event_f3_vixmed_t0_long"]) is True


def test_tslope_stress_gate_on_inverted_term_structure():
    fr = _frame([0.004, 0.004, 0.004, 0.004, 0.004])
    # slope = vix3m - vix9d. Contango (positive) for seed days, deep inversion on day3
    # (prior) -> stress active on day4.
    vix9d = [15.0, 15.0, 15.0, 40.0, 15.0]
    vix3m = [20.0, 20.0, 20.0, 18.0, 20.0]
    df = add_f3_vix_gated_features(
        fr, vix_frame=_vix(fr, vix9d=vix9d, vix3m=vix3m), regime_lookback_days=2
    )
    dec = df[df["f3_decision_bar"]].reset_index(drop=True)
    assert bool(dec.loc[4, "event_f3_tslope_t0_long"]) is True


def test_events_fire_only_on_decision_bar():
    fr = _frame([0.002, -0.002, 0.003])
    df = add_f3_vix_gated_features(fr, vix_frame=_vix(fr, vix=[30.0, 30.0, 30.0]))
    cols = find_f3_event_columns(df)
    assert (df[cols].any(axis=1) & ~df["f3_decision_bar"]).sum() == 0


@pytest.mark.parametrize("kwargs", [{"regime_lookback_days": 0}, {"variants": ("nope",)}, {"thresholds": (-1.0,)}])
def test_invalid_arguments_rejected(kwargs):
    with pytest.raises(ValueError):
        add_f3_vix_gated_features(_frame([0.001, 0.001]), **kwargs)
