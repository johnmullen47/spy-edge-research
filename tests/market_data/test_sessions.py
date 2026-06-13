from __future__ import annotations

import pandas as pd

from spy_edge_research.market_data.sessions import (
    SessionLabel,
    add_session_column,
    classify_session,
    filter_premarket,
    filter_regular_session,
)


def test_classifies_premarket_regular_postmarket_and_closed_timestamps() -> None:
    tz = "America/New_York"

    assert classify_session(pd.Timestamp("2024-01-02 04:01", tz=tz)) == SessionLabel.PREMARKET
    assert classify_session(pd.Timestamp("2024-01-02 09:31", tz=tz)) == SessionLabel.REGULAR
    assert classify_session(pd.Timestamp("2024-01-02 16:01", tz=tz)) == SessionLabel.POSTMARKET
    assert classify_session(pd.Timestamp("2024-01-02 20:01", tz=tz)) == SessionLabel.CLOSED


def test_adds_session_column() -> None:
    df = pd.DataFrame(
        {
            "timestamp": [pd.Timestamp("2024-01-02 09:31", tz="America/New_York")],
            "symbol": ["SPY"],
        }
    )

    result = add_session_column(df)

    assert result.loc[0, "session"] == SessionLabel.REGULAR


def test_filters_regular_session_correctly() -> None:
    df = pd.DataFrame(
        {
            "timestamp": [
                pd.Timestamp("2024-01-02 09:30", tz="America/New_York"),
                pd.Timestamp("2024-01-02 09:31", tz="America/New_York"),
                pd.Timestamp("2024-01-02 16:00", tz="America/New_York"),
                pd.Timestamp("2024-01-02 16:01", tz="America/New_York"),
            ],
            "symbol": ["SPY"] * 4,
        }
    )

    result = filter_regular_session(df)

    assert list(result["timestamp"].dt.strftime("%H:%M")) == ["09:31", "16:00"]


def test_filters_premarket_correctly() -> None:
    df = pd.DataFrame(
        {
            "timestamp": [
                pd.Timestamp("2024-01-02 04:00", tz="America/New_York"),
                pd.Timestamp("2024-01-02 04:01", tz="America/New_York"),
                pd.Timestamp("2024-01-02 09:30", tz="America/New_York"),
                pd.Timestamp("2024-01-02 09:31", tz="America/New_York"),
            ],
            "symbol": ["SPY"] * 4,
        }
    )

    result = filter_premarket(df)

    assert list(result["timestamp"].dt.strftime("%H:%M")) == ["04:01", "09:30"]
