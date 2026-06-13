"""Research-only event-study diagnostics and quality controls.

These helpers summarize event-study cleanliness, sample size, and coverage.
They do not create causal features, trade signals, rankings, optimizations,
or edge claims.
"""

from __future__ import annotations

from collections.abc import Iterable
from numbers import Real

import numpy as np
import pandas as pd

EVENT_STUDY_REQUIRED_COLUMNS: list[str] = [
    "event_column",
    "label_column",
    "event_count",
    "event_rate",
    "label_mean_on_event",
    "overall_label_mean",
    "difference_from_overall",
]

SAMPLE_SIZE_FLAG_COLUMNS: list[str] = [
    "has_min_events",
    "sample_size_warning",
]

LABEL_COVERAGE_COLUMNS: list[str] = [
    "label_column",
    "row_count",
    "non_missing_count",
    "missing_count",
    "non_missing_rate",
    "missing_rate",
]

EVENT_COVERAGE_COLUMNS: list[str] = [
    "event_column",
    "row_count",
    "true_count",
    "false_count",
    "missing_count",
    "true_rate",
    "missing_rate",
]

GROUPED_EVENT_STUDY_COLUMNS: list[str] = [
    "row_count",
    "total_event_count",
    "mean_event_rate",
    "mean_label_mean_on_event",
    "mean_overall_label_mean",
    "mean_difference_from_overall",
]


def validate_event_study_results(results: pd.DataFrame) -> pd.DataFrame:
    """Validate descriptive event-study result columns, returning a copy."""
    _require_columns(results, EVENT_STUDY_REQUIRED_COLUMNS)
    validated = results.copy()

    event_count = pd.to_numeric(validated["event_count"], errors="coerce")
    if event_count.isna().any():
        raise ValueError("event_count must contain numeric values")
    if (event_count < 0).any():
        raise ValueError("event_count must be non-negative")

    event_rate = pd.to_numeric(validated["event_rate"], errors="coerce")
    non_missing_rate = event_rate.notna()
    if ((event_rate.loc[non_missing_rate] < 0) | (event_rate.loc[non_missing_rate] > 1)).any():
        raise ValueError("event_rate must be between 0 and 1 when not missing")

    return validated


def add_event_sample_size_flags(
    results: pd.DataFrame,
    *,
    min_events: int = 10,
    min_event_rate: float | None = None,
) -> pd.DataFrame:
    """Add descriptive sample-size and event-frequency quality-control flags."""
    _validate_min_events(min_events)
    if min_event_rate is not None:
        _validate_probability(min_event_rate, "min_event_rate")

    flagged = validate_event_study_results(results)
    flagged["has_min_events"] = flagged["event_count"] >= min_events

    warning = pd.Series("", index=flagged.index, dtype="object")
    warning.loc[~flagged["has_min_events"]] = "event_count_below_minimum"

    if min_event_rate is not None:
        flagged["has_min_event_rate"] = flagged["event_rate"] >= min_event_rate
        below_rate = ~flagged["has_min_event_rate"]
        empty_warning = below_rate & warning.eq("")
        existing_warning = below_rate & warning.ne("")
        warning.loc[empty_warning] = "event_rate_below_minimum"
        warning.loc[existing_warning] = (
            warning.loc[existing_warning] + ";event_rate_below_minimum"
        )

    flagged["sample_size_warning"] = warning
    return flagged


def label_coverage_summary(
    df: pd.DataFrame,
    label_columns: Iterable[str],
) -> pd.DataFrame:
    """Summarize missing and non-missing coverage for evaluation labels."""
    labels = _normalize_columns(label_columns, "label_columns")
    _require_columns(df, labels)

    rows = []
    row_count = len(df)
    for label_column in labels:
        missing_count = int(df[label_column].isna().sum())
        non_missing_count = row_count - missing_count
        rows.append(
            {
                "label_column": label_column,
                "row_count": row_count,
                "non_missing_count": non_missing_count,
                "missing_count": missing_count,
                "non_missing_rate": np.nan if row_count == 0 else non_missing_count / row_count,
                "missing_rate": np.nan if row_count == 0 else missing_count / row_count,
            }
        )
    return pd.DataFrame(rows, columns=LABEL_COVERAGE_COLUMNS)


def event_coverage_summary(
    df: pd.DataFrame,
    event_columns: Iterable[str],
) -> pd.DataFrame:
    """Summarize boolean-like event frequency and missingness."""
    events = _normalize_columns(event_columns, "event_columns")
    _require_columns(df, events)

    rows = []
    row_count = len(df)
    for event_column in events:
        values = df[event_column]
        missing_count = int(values.isna().sum())
        non_missing = values.loc[values.notna()]
        event_occurs = non_missing.astype(bool)
        true_count = int(event_occurs.sum())
        false_count = int((~event_occurs).sum())
        rows.append(
            {
                "event_column": event_column,
                "row_count": row_count,
                "true_count": true_count,
                "false_count": false_count,
                "missing_count": missing_count,
                "true_rate": np.nan if row_count == 0 else true_count / row_count,
                "missing_rate": np.nan if row_count == 0 else missing_count / row_count,
            }
        )
    return pd.DataFrame(rows, columns=EVENT_COVERAGE_COLUMNS)


def grouped_event_study_summary(
    results: pd.DataFrame,
    group_columns: Iterable[str],
) -> pd.DataFrame:
    """Group descriptive event-study results by metadata columns."""
    groups = _normalize_columns(group_columns, "group_columns")
    validated = validate_event_study_results(results)
    _require_columns(validated, groups)

    if validated.empty:
        return pd.DataFrame(columns=[*groups, *GROUPED_EVENT_STUDY_COLUMNS])

    summary = (
        validated.groupby(groups, dropna=False, sort=True)
        .agg(
            row_count=("event_column", "size"),
            total_event_count=("event_count", "sum"),
            mean_event_rate=("event_rate", "mean"),
            mean_label_mean_on_event=("label_mean_on_event", "mean"),
            mean_overall_label_mean=("overall_label_mean", "mean"),
            mean_difference_from_overall=("difference_from_overall", "mean"),
        )
        .reset_index()
    )
    return summary[[*groups, *GROUPED_EVENT_STUDY_COLUMNS]]


def diagnose_event_study(
    df: pd.DataFrame,
    results: pd.DataFrame,
    *,
    label_columns: Iterable[str],
    event_columns: Iterable[str] | None = None,
    min_events: int = 10,
    min_event_rate: float | None = None,
    group_columns: Iterable[str] | None = None,
) -> dict[str, pd.DataFrame]:
    """Return event-study diagnostic tables without mutating inputs."""
    diagnostics = {
        "results_with_sample_flags": add_event_sample_size_flags(
            results,
            min_events=min_events,
            min_event_rate=min_event_rate,
        ),
        "label_coverage": label_coverage_summary(df, label_columns),
    }
    if event_columns is not None:
        diagnostics["event_coverage"] = event_coverage_summary(df, event_columns)
    if group_columns is not None:
        diagnostics["grouped_summary"] = grouped_event_study_summary(results, group_columns)
    return diagnostics


def _normalize_columns(columns: Iterable[str], name: str) -> list[str]:
    if isinstance(columns, str):
        normalized = [columns]
    else:
        normalized = list(columns)
    if not normalized or not all(isinstance(column, str) and column for column in normalized):
        raise ValueError(f"{name} must contain at least one column name")
    return normalized


def _require_columns(df: pd.DataFrame, columns: list[str]) -> None:
    missing = [column for column in columns if column not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")


def _validate_min_events(min_events: int) -> None:
    if not isinstance(min_events, int) or isinstance(min_events, bool) or min_events < 0:
        raise ValueError("min_events must be a non-negative integer")


def _validate_probability(value: float, name: str) -> None:
    if not isinstance(value, Real) or isinstance(value, bool) or not 0 <= value <= 1:
        raise ValueError(f"{name} must satisfy 0 <= {name} <= 1")
