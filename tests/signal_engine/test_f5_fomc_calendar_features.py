"""Tests for F5 pre-FOMC calendar placebo features (M122)."""

from __future__ import annotations

import datetime as dt

import numpy as np
import pandas as pd
import pytest

from spy_edge_research.signal_engine.f5_fomc_calendar_features import (
    F5_THRESHOLDS,
    F5_VARIANTS,
    FOMC_ANNOUNCEMENT_DATES,
    add_f5_fomc_calendar_features,
    find_f5_event_columns,
)

NY = "America/New_York"


def _frame(r_rods: list[float], *, base: float = 100.0) -> pd.DataFrame:
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


# Frame dates are 2024-01-02, -03, -04, -05; mark -04 as an FOMC announcement so
# -03 is the FOMC-eve session.
ANN = (dt.date(2024, 1, 4),)


def test_full_grid_column_count():
    df = add_f5_fomc_calendar_features(_frame([0.002, 0.002]), announcement_dates=ANN)
    cols = find_f5_event_columns(df)
    assert len(cols) == len(F5_VARIANTS) * len(F5_THRESHOLDS) * 2 == 16


def test_fomc_eve_is_session_before_announcement():
    df = add_f5_fomc_calendar_features(_frame([0.005, 0.005, 0.005, 0.005]), announcement_dates=ANN)
    dec = df[df["f5_decision_bar"]].reset_index(drop=True)
    # day index 1 (2024-01-03) is the eve of the 01-04 announcement.
    assert bool(dec.loc[1, "f5_is_fomc_eve"]) is True
    assert bool(dec.loc[0, "f5_is_fomc_eve"]) is False
    assert bool(dec.loc[2, "f5_is_fomc_eve"]) is False


def test_c1_restrict_fires_only_on_eve_days():
    df = add_f5_fomc_calendar_features(_frame([0.005, 0.005, 0.005, 0.005]), announcement_dates=ANN)
    dec = df[df["f5_decision_bar"]].reset_index(drop=True)
    assert bool(dec.loc[1, "event_f5_c1_t0_long"]) is True
    assert bool(dec.loc[2, "event_f5_c1_t0_long"]) is False


def test_c2_exclude_fires_only_off_eve_days():
    df = add_f5_fomc_calendar_features(_frame([0.005, 0.005, 0.005, 0.005]), announcement_dates=ANN)
    dec = df[df["f5_decision_bar"]].reset_index(drop=True)
    assert bool(dec.loc[1, "event_f5_c2_t0_long"]) is False  # eve excluded
    assert bool(dec.loc[2, "event_f5_c2_t0_long"]) is True   # non-eve traded


def test_c1_and_c2_are_complementary_on_valid_decision_bars():
    df = add_f5_fomc_calendar_features(_frame([0.0, 0.005, 0.005, 0.005]), announcement_dates=ANN)
    dec = df[df["f5_decision_bar"]].reset_index(drop=True)
    # day index 0 has no prior close (r_rod NaN) -> neither fires; days 1..3 partition.
    for i in range(1, 4):
        c1 = bool(dec.loc[i, "event_f5_c1_t0_long"])
        c2 = bool(dec.loc[i, "event_f5_c2_t0_long"])
        assert c1 != c2  # exactly one of restrict/exclude fires per up-momentum day


def test_events_fire_only_on_decision_bar():
    df = add_f5_fomc_calendar_features(_frame([0.002, -0.002, 0.003]), announcement_dates=ANN)
    cols = find_f5_event_columns(df)
    assert (df[cols].any(axis=1) & ~df["f5_decision_bar"]).sum() == 0


def test_embedded_fomc_calendar_is_well_formed():
    # 8 scheduled meetings per year, 2024-2026, strictly increasing.
    assert len(FOMC_ANNOUNCEMENT_DATES) == 24
    assert list(FOMC_ANNOUNCEMENT_DATES) == sorted(FOMC_ANNOUNCEMENT_DATES)


@pytest.mark.parametrize("kwargs", [{"variants": ("nope",)}, {"thresholds": (-1.0,)}])
def test_invalid_arguments_rejected(kwargs):
    with pytest.raises(ValueError):
        add_f5_fomc_calendar_features(_frame([0.001, 0.001]), announcement_dates=ANN, **kwargs)
