"""Research-only event forward-outcome study helpers.

These helpers evaluate already-created causal event columns against existing
forward-looking outcome columns. They do not create causal features, trading
signals, rankings, optimization results, or statistical significance claims.
"""

from __future__ import annotations

from collections.abc import Iterable
from numbers import Real

import numpy as np
import pandas as pd

from spy_edge_research.signal_engine.event_catalog import validate_event_catalog

from spy_edge_research._internal._common import (
    normalize_columns as _normalize_columns,
    require_columns as _require_columns,
)

EVENT_FORWARD_OUTCOME_COLUMNS: list[str] = [
    "event_column",
    "event_family",
    "event_direction",
    "outcome_column",
    "event_count",
    "baseline_count",
    "event_rate",
    "event_expectancy",
    "baseline_expectancy",
    "expectancy_difference",
    "event_hit_rate",
    "baseline_hit_rate",
    "hit_rate_difference",
    "sample_size_flag",
]


def calculate_event_sample_size(
    df: pd.DataFrame,
    event_column: str,
    outcome_column: str | None = None,
) -> int:
    """Count event rows, optionally requiring a non-missing outcome value."""
    _require_columns(df, [event_column])
    event_occurs = df[event_column].fillna(False).astype(bool)
    if outcome_column is not None:
        _require_columns(df, [outcome_column])
        event_occurs &= pd.to_numeric(df[outcome_column], errors="coerce").notna()
    return int(event_occurs.sum())


def calculate_event_expectancy(outcomes: pd.Series) -> float:
    """Return the mean outcome for a sample, or NaN for an empty sample."""
    values = pd.to_numeric(outcomes, errors="coerce").dropna()
    if values.empty:
        return np.nan
    return float(values.mean())


def calculate_event_hit_rate(
    outcomes: pd.Series,
    *,
    threshold: float = 0.0,
) -> float:
    """Return the share of outcomes above ``threshold``, or NaN if empty."""
    _validate_number(threshold, "threshold")
    values = pd.to_numeric(outcomes, errors="coerce").dropna()
    if values.empty:
        return np.nan
    return float(values.gt(threshold).mean())


def summarize_event_forward_returns(
    df: pd.DataFrame,
    event_column: str,
    outcome_columns: Iterable[str],
    *,
    event_family: str = "unknown",
    event_direction: str = "unknown",
    hit_rate_threshold: float = 0.0,
    min_events: int = 1,
) -> pd.DataFrame:
    """Summarize one event column against forward outcome columns."""
    _validate_min_events(min_events)
    _validate_number(hit_rate_threshold, "hit_rate_threshold")
    outcomes = _normalize_columns(outcome_columns, "outcome_columns")
    _require_columns(df, [event_column, *outcomes])

    event_occurs = df[event_column].fillna(False).astype(bool)
    rows = []
    for outcome_column in outcomes:
        outcome_values = pd.to_numeric(df[outcome_column], errors="coerce")
        valid_outcome = outcome_values.notna()
        event_sample = outcome_values.loc[event_occurs & valid_outcome]
        baseline_sample = outcome_values.loc[valid_outcome]
        event_count = int(event_sample.count())
        baseline_count = int(baseline_sample.count())
        event_rate = np.nan if len(df) == 0 else int(event_occurs.sum()) / len(df)

        if event_count < min_events:
            event_expectancy = np.nan
            expectancy_difference = np.nan
            event_hit_rate = np.nan
            hit_rate_difference = np.nan
        else:
            event_expectancy = calculate_event_expectancy(event_sample)
            event_hit_rate = calculate_event_hit_rate(
                event_sample,
                threshold=hit_rate_threshold,
            )
            baseline_expectancy_for_difference = calculate_event_expectancy(baseline_sample)
            baseline_hit_rate_for_difference = calculate_event_hit_rate(
                baseline_sample,
                threshold=hit_rate_threshold,
            )
            expectancy_difference = event_expectancy - baseline_expectancy_for_difference
            hit_rate_difference = event_hit_rate - baseline_hit_rate_for_difference

        baseline_expectancy = calculate_event_expectancy(baseline_sample)
        baseline_hit_rate = calculate_event_hit_rate(
            baseline_sample,
            threshold=hit_rate_threshold,
        )
        rows.append(
            {
                "event_column": event_column,
                "event_family": event_family,
                "event_direction": event_direction,
                "outcome_column": outcome_column,
                "event_count": event_count,
                "baseline_count": baseline_count,
                "event_rate": event_rate,
                "event_expectancy": event_expectancy,
                "baseline_expectancy": baseline_expectancy,
                "expectancy_difference": expectancy_difference,
                "event_hit_rate": event_hit_rate,
                "baseline_hit_rate": baseline_hit_rate,
                "hit_rate_difference": hit_rate_difference,
                "sample_size_flag": _sample_size_flag(event_count, min_events),
            }
        )
    return pd.DataFrame(rows, columns=EVENT_FORWARD_OUTCOME_COLUMNS)


def build_event_forward_return_table(
    df: pd.DataFrame,
    catalog: pd.DataFrame,
    outcome_columns: Iterable[str],
    *,
    hit_rate_threshold: float = 0.0,
    min_events: int = 1,
) -> pd.DataFrame:
    """Build a forward-outcome table for every event in a validated catalog."""
    validated = validate_event_catalog(catalog)
    outcomes = _normalize_columns(outcome_columns, "outcome_columns")
    _require_columns(df, outcomes)
    if validated.empty:
        return pd.DataFrame(columns=EVENT_FORWARD_OUTCOME_COLUMNS)

    tables = []
    for event in validated.itertuples(index=False):
        tables.append(
            summarize_event_forward_returns(
                df,
                event.event_column,
                outcomes,
                event_family=event.event_family,
                event_direction=event.event_direction,
                hit_rate_threshold=hit_rate_threshold,
                min_events=min_events,
            )
        )
    if not tables:
        return pd.DataFrame(columns=EVENT_FORWARD_OUTCOME_COLUMNS)
    return pd.concat(tables, ignore_index=True)


def compare_event_vs_baseline_forward_returns(
    df: pd.DataFrame,
    event_column: str,
    outcome_column: str,
    *,
    hit_rate_threshold: float = 0.0,
    min_events: int = 1,
) -> pd.Series:
    """Compare one event/outcome pair against the full valid-outcome baseline."""
    table = summarize_event_forward_returns(
        df,
        event_column,
        [outcome_column],
        hit_rate_threshold=hit_rate_threshold,
        min_events=min_events,
    )
    return table.iloc[0].copy()


def _sample_size_flag(event_count: int, min_events: int) -> str:
    if event_count == 0:
        return "no_events"
    if event_count < min_events:
        return "small_sample"
    return "ok"


def _validate_min_events(min_events: int) -> None:
    if not isinstance(min_events, int) or isinstance(min_events, bool) or min_events < 1:
        raise ValueError("min_events must be an integer greater than or equal to 1")


def _validate_number(value: float, name: str) -> None:
    if not isinstance(value, Real) or isinstance(value, bool):
        raise ValueError(f"{name} must be numeric")
