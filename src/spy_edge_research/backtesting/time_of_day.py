"""Research-only time-of-day event outcome helpers."""

from __future__ import annotations

from collections.abc import Iterable

import numpy as np
import pandas as pd

from spy_edge_research.backtesting.conditional_event_study import (
    summarize_conditional_event_edge,
)
from spy_edge_research.backtesting.event_forward_outcomes import (
    calculate_event_expectancy,
    calculate_event_hit_rate,
)

from spy_edge_research._internal._common import (
    normalize_columns as _normalize_columns,
    require_columns as _require_columns,
    validate_positive_int as _validate_positive_int,
)

SESSION_BUCKET_COLUMN = "session_bucket"

SESSION_BUCKETS: tuple[str, ...] = (
    "open",
    "post_open",
    "mid_morning",
    "lunch",
    "afternoon",
    "power_hour",
    "outside_regular",
)

SESSION_BUCKET_OUTCOME_COLUMNS: list[str] = [
    "session_bucket",
    "outcome_column",
    "bucket_count",
    "baseline_count",
    "bucket_expectancy",
    "baseline_expectancy",
    "expectancy_difference",
    "bucket_hit_rate",
    "baseline_hit_rate",
    "hit_rate_difference",
]


def assign_intraday_session_bucket(
    timestamp: pd.Timestamp,
    *,
    timezone: str = "America/New_York",
) -> str:
    """Assign a bar-close timestamp to a deterministic intraday bucket."""
    ts = pd.Timestamp(timestamp)
    if ts.tzinfo is None:
        ts = ts.tz_localize(timezone)
    else:
        ts = ts.tz_convert(timezone)

    time_value = ts.time()
    if pd.Timestamp("09:31").time() <= time_value <= pd.Timestamp("10:00").time():
        return "open"
    if pd.Timestamp("10:01").time() <= time_value <= pd.Timestamp("11:00").time():
        return "post_open"
    if pd.Timestamp("11:01").time() <= time_value <= pd.Timestamp("12:00").time():
        return "mid_morning"
    if pd.Timestamp("12:01").time() <= time_value <= pd.Timestamp("13:30").time():
        return "lunch"
    if pd.Timestamp("13:31").time() <= time_value <= pd.Timestamp("15:00").time():
        return "afternoon"
    if pd.Timestamp("15:01").time() <= time_value <= pd.Timestamp("16:00").time():
        return "power_hour"
    return "outside_regular"


def summarize_event_by_session_bucket(
    df: pd.DataFrame,
    catalog: pd.DataFrame,
    outcome_columns: Iterable[str],
    *,
    timestamp_col: str = "timestamp",
    bucket_col: str = SESSION_BUCKET_COLUMN,
    timezone: str = "America/New_York",
    hit_rate_threshold: float = 0.0,
    min_events: int = 1,
) -> pd.DataFrame:
    """Summarize event outcomes by intraday session bucket."""
    working = _with_session_bucket(
        df,
        timestamp_col=timestamp_col,
        bucket_col=bucket_col,
        timezone=timezone,
    )
    return summarize_conditional_event_edge(
        working,
        catalog,
        outcome_columns,
        [bucket_col],
        hit_rate_threshold=hit_rate_threshold,
        min_events=min_events,
    )


def compare_session_bucket_outcomes(
    df: pd.DataFrame,
    outcome_columns: Iterable[str],
    *,
    timestamp_col: str = "timestamp",
    bucket_col: str = SESSION_BUCKET_COLUMN,
    timezone: str = "America/New_York",
    hit_rate_threshold: float = 0.0,
) -> pd.DataFrame:
    """Compare outcome distributions by session bucket against all rows."""
    outcomes = _normalize_columns(outcome_columns, "outcome_columns")
    working = _with_session_bucket(
        df,
        timestamp_col=timestamp_col,
        bucket_col=bucket_col,
        timezone=timezone,
    )
    _require_columns(working, outcomes)

    rows = []
    for bucket, bucket_df in working.groupby(bucket_col, dropna=False, sort=False):
        for outcome_column in outcomes:
            outcome_values = pd.to_numeric(working[outcome_column], errors="coerce")
            bucket_values = pd.to_numeric(bucket_df[outcome_column], errors="coerce").dropna()
            baseline_values = outcome_values.dropna()
            bucket_expectancy = calculate_event_expectancy(bucket_values)
            baseline_expectancy = calculate_event_expectancy(baseline_values)
            bucket_hit_rate = calculate_event_hit_rate(
                bucket_values,
                threshold=hit_rate_threshold,
            )
            baseline_hit_rate = calculate_event_hit_rate(
                baseline_values,
                threshold=hit_rate_threshold,
            )
            rows.append(
                {
                    "session_bucket": bucket,
                    "outcome_column": outcome_column,
                    "bucket_count": int(bucket_values.count()),
                    "baseline_count": int(baseline_values.count()),
                    "bucket_expectancy": bucket_expectancy,
                    "baseline_expectancy": baseline_expectancy,
                    "expectancy_difference": bucket_expectancy - baseline_expectancy,
                    "bucket_hit_rate": bucket_hit_rate,
                    "baseline_hit_rate": baseline_hit_rate,
                    "hit_rate_difference": bucket_hit_rate - baseline_hit_rate,
                }
            )
    return pd.DataFrame(rows, columns=SESSION_BUCKET_OUTCOME_COLUMNS)


def detect_time_of_day_edge_concentration(
    session_event_table: pd.DataFrame,
    *,
    min_events: int,
    concentration_threshold: float = 0.5,
    sort_by: str = "expectancy_difference",
) -> pd.DataFrame:
    """Flag event/outcome rows concentrated in specific time-of-day buckets."""
    _validate_positive_int(min_events, "min_events")
    if not isinstance(concentration_threshold, (int, float)) or isinstance(
        concentration_threshold, bool
    ):
        raise ValueError("concentration_threshold must be numeric")
    if concentration_threshold <= 0 or concentration_threshold > 1:
        raise ValueError("concentration_threshold must be in the interval (0, 1]")
    _require_columns(
        session_event_table,
        ["event_column", "outcome_column", "event_count", sort_by],
    )

    result = session_event_table.copy()
    totals = result.groupby(["event_column", "outcome_column"])["event_count"].transform("sum")
    result["event_count_share"] = result["event_count"].div(totals.replace(0, np.nan))
    result["abs_expectancy_difference"] = result["expectancy_difference"].abs()
    result["is_time_of_day_concentrated"] = (
        result["event_count"].ge(min_events)
        & result["event_count_share"].ge(concentration_threshold)
    )
    return result.sort_values(
        by=["is_time_of_day_concentrated", sort_by],
        ascending=[False, False],
        na_position="last",
        kind="mergesort",
    ).reset_index(drop=True)


def _with_session_bucket(
    df: pd.DataFrame,
    *,
    timestamp_col: str,
    bucket_col: str,
    timezone: str,
) -> pd.DataFrame:
    if bucket_col in df.columns:
        return df.copy()
    _require_columns(df, [timestamp_col])
    result = df.copy()
    result[bucket_col] = result[timestamp_col].map(
        lambda timestamp: assign_intraday_session_bucket(timestamp, timezone=timezone)
    )
    return result

