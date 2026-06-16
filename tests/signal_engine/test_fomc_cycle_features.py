"""Tests for F10 FOMC-cycle features (M125)."""

from __future__ import annotations

import datetime as dt

import numpy as np
import pandas as pd
import pytest

from spy_edge_research.signal_engine.fomc_cycle_features import (
    F10_PHASES,
    add_fomc_cycle_features,
    find_f10_event_columns,
)

NY = "America/New_York"


def _frame(ndays=80, base=100.0, seed=0, start="2024-06-03"):
    rng = np.random.RandomState(seed)
    rows = []
    s = pd.Timestamp(start, tz=NY)
    px = base
    for d in range(ndays):
        date = s + pd.Timedelta(days=d)
        if date.weekday() >= 5:
            continue
        for m in range(390):
            ts = date + pd.Timedelta(hours=9, minutes=30 + m)
            px *= np.exp(rng.randn() * 2e-4)
            rows.append({"timestamp": ts, "open": px, "high": px, "low": px,
                         "close": px, "volume": 1000})
    return pd.DataFrame(rows)


# A small custom calendar inside the frame's span (2024-06-03 .. ~2024-09).
ANN = (dt.date(2024, 6, 12), dt.date(2024, 7, 31))


def test_column_count_is_six():
    df = add_fomc_cycle_features(_frame(), announcement_dates=ANN)
    assert len(find_f10_event_columns(df)) == len(F10_PHASES) * 2 == 6


def test_events_fire_only_on_last_bar():
    df = add_fomc_cycle_features(_frame(), announcement_dates=ANN)
    cols = find_f10_event_columns(df)
    assert (df[cols].any(axis=1) & ~df["f10_last_bar"]).sum() == 0


def test_even_and_odd_are_complementary_when_defined():
    df = add_fomc_cycle_features(_frame(), announcement_dates=ANN)
    last = df[df["f10_last_bar"]]
    even = last["event_f10_strict_even_long"].astype(bool)
    odd = last["event_f10_strict_odd_short"].astype(bool)
    # never both; and where defined (one of them set) it is exactly one.
    assert (even & odd).sum() == 0
    defined = even | odd
    assert defined.sum() > 0


def test_week_zero_after_meeting_is_even_long():
    # The session right after a meeting (cycle week 0) must be an even-week long.
    df = add_fomc_cycle_features(_frame(), announcement_dates=ANN)
    last = df[df["f10_last_bar"]].copy()
    last["date"] = pd.to_datetime(last["timestamp"]).dt.tz_convert(NY).dt.date
    # 2024-07-31 is a meeting; 2024-08-01 is week-0 day 1.
    row = last[last["date"] == dt.date(2024, 8, 1)]
    if not row.empty:
        assert bool(row["event_f10_strict_even_long"].iloc[0]) is True


def test_undefined_before_first_meeting():
    # Sessions before the first announcement in range have no cycle phase.
    df = add_fomc_cycle_features(_frame(start="2024-06-03"), announcement_dates=(dt.date(2024, 7, 31),))
    last = df[df["f10_last_bar"]].copy()
    last["date"] = pd.to_datetime(last["timestamp"]).dt.tz_convert(NY).dt.date
    early = last[last["date"] < dt.date(2024, 7, 31)]
    cols = find_f10_event_columns(df)
    assert early[cols].to_numpy().sum() == 0


def test_invalid_phase_rejected():
    with pytest.raises(ValueError):
        add_fomc_cycle_features(_frame(ndays=10), phases=("nope",), announcement_dates=ANN)
