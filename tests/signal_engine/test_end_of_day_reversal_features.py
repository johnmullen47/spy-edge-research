"""Tests for end-of-day reversal features (F2 — M116)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from spy_edge_research.signal_engine.end_of_day_reversal_features import (
    add_end_of_day_reversal_features,
    find_end_of_day_reversal_event_columns,
)

NY = "America/New_York"


def _session_frame(pre_returns: list[float], *, base: float = 100.0) -> pd.DataFrame:
    """Build 1-min bars 14:00->15:05 for each session with a controlled r_pre.

    Within a session the close is ``base`` through 14:59, then ``base*exp(r)`` from
    15:00 on — so r_pre = log(close[15:00]/close[14:00]) = r exactly, and the 15:00
    bar is the decision bar.
    """
    rows = []
    for day, r in enumerate(pre_returns):
        date = pd.Timestamp("2024-01-02", tz=NY) + pd.Timedelta(days=day)
        for minute in range(0, 66):  # 14:00 .. 15:05
            ts = date + pd.Timedelta(hours=14, minutes=minute)
            close = base if minute < 60 else base * np.exp(r)
            rows.append({"timestamp": ts, "open": close, "close": close, "volume": 1000})
    return pd.DataFrame(rows)


def test_decision_bar_is_the_first_bar_at_or_after_pre_window_end():
    df = add_end_of_day_reversal_features(_session_frame([0.001, -0.001]), vol_lookback_days=2)
    decision = df[df["eod_decision_bar"]]
    # one decision bar per session, at 15:00 local
    assert len(decision) == 2
    assert all(pd.to_datetime(decision["timestamp"]).dt.strftime("%H:%M") == "15:00")


def test_primary_direction_is_minus_sign_of_pre_move():
    # up pre-move -> short; down pre-move -> long.
    df = add_end_of_day_reversal_features(_session_frame([0.002, -0.002]), vol_lookback_days=2)
    dec = df[df["eod_decision_bar"]].reset_index(drop=True)
    assert dec.loc[0, "eod_pre_close_return"] > 0
    assert bool(dec.loc[0, "event_eod_reversal_short"]) is True
    assert bool(dec.loc[0, "event_eod_reversal_long"]) is False
    assert dec.loc[1, "eod_pre_close_return"] < 0
    assert bool(dec.loc[1, "event_eod_reversal_long"]) is True
    assert bool(dec.loc[1, "event_eod_reversal_short"]) is False


def test_events_fire_only_on_the_decision_bar():
    df = add_end_of_day_reversal_features(_session_frame([0.002, -0.002, 0.002]), vol_lookback_days=2)
    cols = find_end_of_day_reversal_event_columns(df)
    fired = df[cols].any(axis=1)
    assert (fired & ~df["eod_decision_bar"]).sum() == 0  # never off the decision bar


def test_conviction_requires_trailing_history_and_clears_threshold():
    # First two sessions seed the trailing std; the 3rd is a large move -> conviction.
    df = add_end_of_day_reversal_features(
        _session_frame([0.001, -0.001, 0.05]), vol_lookback_days=2, conviction_z=1.0
    )
    dec = df[df["eod_decision_bar"]].reset_index(drop=True)
    # Session 0,1 have no prior 2-session history (shifted) -> no conviction.
    assert bool(dec.loc[0, "eod_high_conviction"]) is False
    assert bool(dec.loc[1, "eod_high_conviction"]) is False
    # Session 2: large up move, |z| >= 1 -> short conviction fires, long does not.
    assert bool(dec.loc[2, "eod_high_conviction"]) is True
    assert bool(dec.loc[2, "event_eod_reversal_short_conviction"]) is True
    assert bool(dec.loc[2, "event_eod_reversal_long_conviction"]) is False


def test_conviction_is_subset_of_primary():
    df = add_end_of_day_reversal_features(
        _session_frame([0.01, -0.01, 0.02, -0.02, 0.03]), vol_lookback_days=2
    )
    assert (df["event_eod_reversal_long_conviction"] & ~df["event_eod_reversal_long"]).sum() == 0
    assert (df["event_eod_reversal_short_conviction"] & ~df["event_eod_reversal_short"]).sum() == 0


def test_no_lookahead_truncating_after_decision_bar_is_stable():
    # Feature values on/through the decision bar must not depend on later bars.
    full = add_end_of_day_reversal_features(_session_frame([0.002, -0.002]), vol_lookback_days=2)
    # Drop everything strictly after each session's 15:00 decision bar.
    truncated_src = _session_frame([0.002, -0.002])
    local = pd.to_datetime(truncated_src["timestamp"]).dt.tz_convert(NY)
    keep = (local.dt.hour * 60 + local.dt.minute) <= (15 * 60)
    truncated = add_end_of_day_reversal_features(
        truncated_src[keep].reset_index(drop=True), vol_lookback_days=2
    )
    f_dec = full[full["eod_decision_bar"]].reset_index(drop=True)
    t_dec = truncated[truncated["eod_decision_bar"]].reset_index(drop=True)
    np.testing.assert_allclose(
        f_dec["eod_pre_close_return"].to_numpy(), t_dec["eod_pre_close_return"].to_numpy()
    )


def test_zero_pre_move_fires_neither_direction():
    df = add_end_of_day_reversal_features(_session_frame([0.0, 0.0]), vol_lookback_days=2)
    dec = df[df["eod_decision_bar"]]
    assert dec["event_eod_reversal_long"].sum() == 0
    assert dec["event_eod_reversal_short"].sum() == 0


@pytest.mark.parametrize(
    "kwargs",
    [
        {"vol_lookback_days": 0},
        {"vol_lookback_days": True},
        {"conviction_z": -1.0},
        {"pre_window_start": "15:00", "pre_window_end": "14:00"},  # start !< end
        {"pre_window_end": "bad"},
    ],
)
def test_invalid_arguments_rejected(kwargs):
    with pytest.raises(ValueError):
        add_end_of_day_reversal_features(_session_frame([0.001, -0.001]), **kwargs)
