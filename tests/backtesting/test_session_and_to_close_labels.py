"""Tests for the M125 session-horizon and to-close forward labels."""

from __future__ import annotations

import numpy as np
import pandas as pd

from spy_edge_research.backtesting.labels import (
    add_session_forward_return_labels,
    add_to_close_forward_return_label,
)

NY = "America/New_York"


def _frame(closes_by_day):
    """One bar per minute, 09:30-15:59; each day ends at the given close level."""
    rows = []
    start = pd.Timestamp("2024-01-02", tz=NY)
    for d, last_close in enumerate(closes_by_day):
        date = start + pd.Timedelta(days=d)
        for m in range(390):
            ts = date + pd.Timedelta(hours=9, minutes=30 + m)
            close = last_close if m == 389 else 100.0
            rows.append({"timestamp": ts, "close": close})
    return pd.DataFrame(rows)


def test_session_label_is_close_to_close_over_k_sessions():
    df = add_session_forward_return_labels(_frame([100.0, 110.0, 121.0]), sessions=(1,))
    last = df[df["timestamp"].dt.minute == 59]
    last = last[pd.to_datetime(last["timestamp"]).dt.hour == 15].reset_index(drop=True)
    # day0 last close 100 -> day1 last close 110: +10%
    np.testing.assert_allclose(last.loc[0, "forward_return_1sess"], 0.10, atol=1e-9)
    np.testing.assert_allclose(last.loc[1, "forward_return_1sess"], 0.10, atol=1e-9)
    assert pd.isna(last.loc[2, "forward_return_1sess"])  # no day3


def test_session_label_only_on_last_bar():
    df = add_session_forward_return_labels(_frame([100.0, 110.0]), sessions=(1,))
    non_last = df[~((pd.to_datetime(df["timestamp"]).dt.hour == 15) &
                    (pd.to_datetime(df["timestamp"]).dt.minute == 59))]
    assert non_last["forward_return_1sess"].isna().all()


def test_to_close_label_is_return_to_day_close():
    # day with close 100 until last bar = 105 -> a 09:30 bar's to-close = +5%.
    df = add_to_close_forward_return_label(_frame([105.0]))
    first = df.iloc[0]
    np.testing.assert_allclose(first["forward_return_to_close"], 0.05, atol=1e-9)
    # last bar's to-close is 0 (it IS the close).
    np.testing.assert_allclose(df.iloc[389]["forward_return_to_close"], 0.0, atol=1e-9)


def test_event_label_scoping_separates_daily_and_intraday():
    from spy_edge_research.cli.pipeline import _event_label_allowed
    # daily families pair only with their session horizons
    assert _event_label_allowed("event_f6_z0_long", "forward_return_5sess") is True
    assert _event_label_allowed("event_f6_z0_long", "forward_return_1sess") is False  # not in F6 grid
    assert _event_label_allowed("event_f7_realized_ten_long", "forward_return_1sess") is True
    assert _event_label_allowed("event_f10_strict_even_long", "forward_return_5sess") is True
    # F8 -> to-close only; F9 -> 30m only
    assert _event_label_allowed("event_f8_n5_none_long", "forward_return_to_close") is True
    assert _event_label_allowed("event_f8_n5_none_long", "forward_return_30m") is False
    assert _event_label_allowed("event_f9_lag1_t0_all_long", "forward_return_30m") is True
    assert _event_label_allowed("event_f9_lag1_t0_all_long", "forward_return_5m") is False
    # intraday minute families never pair with daily / to-close labels
    assert _event_label_allowed("event_mimb_a_uncond_t0_long", "forward_return_29m") is True
    assert _event_label_allowed("event_mimb_a_uncond_t0_long", "forward_return_5sess") is False
    assert _event_label_allowed("event_mim_long", "forward_return_to_close") is False
