"""Session classification utilities for SPY bar-close timestamps."""

from __future__ import annotations

from enum import StrEnum

import pandas as pd


class SessionLabel(StrEnum):
    """Supported intraday session labels."""

    PREMARKET = "premarket"
    REGULAR = "regular"
    POSTMARKET = "postmarket"
    CLOSED = "closed"


def classify_session(
    timestamp: pd.Timestamp,
    timezone: str = "America/New_York",
) -> str:
    """Classify a bar-close timestamp into a trading session label."""
    ts = pd.Timestamp(timestamp)
    if ts.tzinfo is None:
        ts = ts.tz_localize(timezone)
    else:
        ts = ts.tz_convert(timezone)

    close_time = ts.time()
    if pd.Timestamp("04:01").time() <= close_time <= pd.Timestamp("09:30").time():
        return SessionLabel.PREMARKET.value
    if pd.Timestamp("09:31").time() <= close_time <= pd.Timestamp("16:00").time():
        return SessionLabel.REGULAR.value
    if pd.Timestamp("16:01").time() <= close_time <= pd.Timestamp("20:00").time():
        return SessionLabel.POSTMARKET.value
    return SessionLabel.CLOSED.value


def add_session_column(
    df: pd.DataFrame,
    timezone: str = "America/New_York",
) -> pd.DataFrame:
    """Return a copy of ``df`` with a session label column."""
    result = df.copy()
    result["session"] = result["timestamp"].map(
        lambda timestamp: classify_session(timestamp, timezone=timezone)
    )
    return result


def filter_regular_session(
    df: pd.DataFrame,
    timezone: str = "America/New_York",
) -> pd.DataFrame:
    """Return only rows classified as regular session."""
    with_sessions = add_session_column(df, timezone=timezone)
    return with_sessions.loc[
        with_sessions["session"] == SessionLabel.REGULAR.value, df.columns
    ].copy()


def filter_premarket(
    df: pd.DataFrame,
    timezone: str = "America/New_York",
) -> pd.DataFrame:
    """Return only rows classified as premarket session."""
    with_sessions = add_session_column(df, timezone=timezone)
    return with_sessions.loc[
        with_sessions["session"] == SessionLabel.PREMARKET.value, df.columns
    ].copy()
