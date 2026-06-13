"""Deterministic fixtures for the MOD 14 simulation tests."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest


@pytest.fixture()
def rising_market() -> pd.DataFrame:
    """One trading day, 30 one-minute bars, price rising a steady +0.10/bar.

    Two hand-placed event columns let tests assert exact entry/exit bars and
    P&L. A long held for 5 bars on a +0.10/bar ramp is always a winner; a short
    is always a loser — so signs and win rates are predictable.
    """
    n = 30
    timestamps = [
        pd.Timestamp("2024-01-02 09:30", tz="America/New_York") + pd.Timedelta(minutes=i)
        for i in range(n)
    ]
    price = pd.Series(100.0 + np.arange(n) * 0.10)
    df = pd.DataFrame(
        {
            "timestamp": timestamps,
            "symbol": "SPY",
            "open": price,
            "high": price + 0.05,
            "low": price - 0.05,
            "close": price,
            "volume": 1000,
        }
    )
    df["event_long"] = 0
    df.loc[[2, 5, 8], "event_long"] = 1
    df["event_short"] = 0
    df.loc[[3], "event_short"] = 1
    # An event near end of day whose 5-bar horizon cannot resolve same-day.
    df["event_late"] = 0
    df.loc[[28], "event_late"] = 1
    return df


@pytest.fixture()
def candidates() -> list[dict]:
    return [
        {"candidate_id": "c_long_5m", "name": "event_long", "direction": "long", "horizon": "5m"},
        {"candidate_id": "c_short_5m", "name": "event_short", "direction": "short", "horizon": "5m"},
        {"candidate_id": "c_neutral", "name": "event_long", "direction": "neutral", "horizon": "5m"},
    ]
