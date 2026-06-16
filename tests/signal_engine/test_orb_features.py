"""Tests for F8 opening-range-breakout features (M125)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from spy_edge_research.signal_engine.orb_features import (
    add_orb_features,
    find_f8_event_columns,
)

NY = "America/New_York"


def _trend_day(date, base, drift):
    """One session that ranges in the first 30 min then trends by `drift`/bar."""
    rows = []
    px = base
    for m in range(390):
        ts = date + pd.Timedelta(hours=9, minutes=30 + m)
        if m < 30:
            px = base * (1 + 0.0005 * np.sin(m))  # oscillate to set an opening range
        else:
            px = px * (1 + drift)  # trend out of the range
        rows.append({"timestamp": ts, "open": px, "high": px * 1.0002,
                     "low": px * 0.9998, "close": px, "volume": 1000})
    return rows


def _frame(drifts):
    rows = []
    start = pd.Timestamp("2024-06-03", tz=NY)
    base = 100.0
    day = 0
    for drift in drifts:
        date = start + pd.Timedelta(days=day)
        while date.weekday() >= 5:
            day += 1
            date = start + pd.Timedelta(days=day)
        rows += _trend_day(date, base, drift)
        day += 1
    return pd.DataFrame(rows)


def test_column_count_is_eighteen():
    df = add_orb_features(_frame([0.0001, -0.0001]))
    assert len(find_f8_event_columns(df)) == 3 * 3 * 2 == 18  # 3 windows x 3 filters x 2 dir


def test_upward_breakout_fires_long_not_short():
    df = add_orb_features(_frame([0.0005]))  # strong up-trend out of the range
    assert df["event_f8_n30_none_long"].sum() >= 1
    assert df["event_f8_n30_none_short"].sum() == 0


def test_downward_breakout_fires_short_not_long():
    df = add_orb_features(_frame([-0.0005]))
    assert df["event_f8_n30_none_short"].sum() >= 1
    assert df["event_f8_n30_none_long"].sum() == 0


def test_at_most_one_long_entry_per_day():
    df = add_orb_features(_frame([0.0005, 0.0005, 0.0005]))
    local = pd.to_datetime(df["timestamp"]).dt.tz_convert(NY).dt.date
    per_day = df.groupby(local)["event_f8_n5_none_long"].sum()
    assert (per_day <= 1).all()


def test_events_are_after_the_opening_range_window():
    df = add_orb_features(_frame([0.0005]))
    local = pd.to_datetime(df["timestamp"]).dt.tz_convert(NY)
    minute = local.dt.hour * 60 + local.dt.minute
    fired = df[find_f8_event_columns(df)].any(axis=1)
    # n=5 window ends 09:35; the earliest any breakout can fire is 09:36.
    assert (minute[fired] > (9 * 60 + 35)).all()


@pytest.mark.parametrize("kwargs", [{"or_windows": (0,)}, {"filters": ("nope",)}])
def test_invalid_arguments_rejected(kwargs):
    with pytest.raises(ValueError):
        add_orb_features(_frame([0.0001]), **kwargs)
