"""Research-only event sequence outcome study helpers."""

from __future__ import annotations

from collections.abc import Iterable

import numpy as np
import pandas as pd

from spy_edge_research.backtesting.event_forward_outcomes import (
    calculate_event_expectancy,
    calculate_event_hit_rate,
    summarize_event_forward_returns,
)

SEQUENCE_OUTCOME_COLUMNS: list[str] = [
    "event_sequence",
    "outcome_column",
    "sequence_count",
    "baseline_count",
    "sequence_rate",
    "sequence_expectancy",
    "baseline_expectancy",
    "expectancy_difference",
    "sequence_hit_rate",
    "baseline_hit_rate",
    "hit_rate_difference",
    "sample_size_flag",
]

SEQUENCE_COMPONENT_COMPARISON_COLUMNS: list[str] = [
    "comparison_type",
    "comparison_name",
    *SEQUENCE_OUTCOME_COLUMNS,
]


def summarize_sequence_forward_returns(
    df: pd.DataFrame,
    sequence_column: str,
    outcome_columns: Iterable[str],
    *,
    sequences: Iterable[str] | None = None,
    hit_rate_threshold: float = 0.0,
    min_occurrences: int = 1,
    include_empty_sequence: bool = False,
) -> pd.DataFrame:
    """Summarize encoded event sequences against forward outcome columns."""
    _validate_positive_int(min_occurrences, "min_occurrences")
    outcomes = _normalize_columns(outcome_columns, "outcome_columns")
    _require_columns(df, [sequence_column, *outcomes])

    sequence_values = _sequence_values(
        df[sequence_column],
        sequences=sequences,
        include_empty_sequence=include_empty_sequence,
    )
    rows = []
    for sequence_value in sequence_values:
        sequence_occurs = df[sequence_column].fillna("").eq(sequence_value)
        for outcome_column in outcomes:
            outcome_values = pd.to_numeric(df[outcome_column], errors="coerce")
            valid_outcome = outcome_values.notna()
            sequence_sample = outcome_values.loc[sequence_occurs & valid_outcome]
            baseline_sample = outcome_values.loc[valid_outcome]
            sequence_count = int(sequence_sample.count())
            baseline_count = int(baseline_sample.count())
            sequence_rate = np.nan if len(df) == 0 else int(sequence_occurs.sum()) / len(df)
            baseline_expectancy = calculate_event_expectancy(baseline_sample)
            baseline_hit_rate = calculate_event_hit_rate(
                baseline_sample,
                threshold=hit_rate_threshold,
            )

            if sequence_count < min_occurrences:
                sequence_expectancy = np.nan
                sequence_hit_rate = np.nan
                expectancy_difference = np.nan
                hit_rate_difference = np.nan
            else:
                sequence_expectancy = calculate_event_expectancy(sequence_sample)
                sequence_hit_rate = calculate_event_hit_rate(
                    sequence_sample,
                    threshold=hit_rate_threshold,
                )
                expectancy_difference = sequence_expectancy - baseline_expectancy
                hit_rate_difference = sequence_hit_rate - baseline_hit_rate

            rows.append(
                {
                    "event_sequence": sequence_value,
                    "outcome_column": outcome_column,
                    "sequence_count": sequence_count,
                    "baseline_count": baseline_count,
                    "sequence_rate": sequence_rate,
                    "sequence_expectancy": sequence_expectancy,
                    "baseline_expectancy": baseline_expectancy,
                    "expectancy_difference": expectancy_difference,
                    "sequence_hit_rate": sequence_hit_rate,
                    "baseline_hit_rate": baseline_hit_rate,
                    "hit_rate_difference": hit_rate_difference,
                    "sample_size_flag": _sample_size_flag(sequence_count, min_occurrences),
                }
            )
    return pd.DataFrame(rows, columns=SEQUENCE_OUTCOME_COLUMNS)


def compare_sequence_vs_component_events(
    df: pd.DataFrame,
    sequence_column: str,
    sequence_value: str,
    outcome_column: str,
    *,
    component_event_columns: Iterable[str] | None = None,
    separator: str = ">",
    hit_rate_threshold: float = 0.0,
    min_occurrences: int = 1,
) -> pd.DataFrame:
    """Compare one encoded sequence to its component event columns."""
    if not isinstance(sequence_value, str) or not sequence_value:
        raise ValueError("sequence_value must be a non-empty string")

    components = (
        _normalize_columns(component_event_columns, "component_event_columns")
        if component_event_columns is not None
        else [component for component in sequence_value.split(separator) if component]
    )
    _require_columns(df, [sequence_column, outcome_column, *components])

    sequence_summary = summarize_sequence_forward_returns(
        df,
        sequence_column,
        [outcome_column],
        sequences=[sequence_value],
        hit_rate_threshold=hit_rate_threshold,
        min_occurrences=min_occurrences,
    ).iloc[0]
    rows = [
        {
            "comparison_type": "sequence",
            "comparison_name": sequence_value,
            **sequence_summary.to_dict(),
        }
    ]

    for component in components:
        component_summary = summarize_event_forward_returns(
            df,
            component,
            [outcome_column],
            hit_rate_threshold=hit_rate_threshold,
            min_events=min_occurrences,
        ).iloc[0]
        rows.append(
            {
                "comparison_type": "component_event",
                "comparison_name": component,
                "event_sequence": sequence_value,
                "outcome_column": outcome_column,
                "sequence_count": component_summary["event_count"],
                "baseline_count": component_summary["baseline_count"],
                "sequence_rate": component_summary["event_rate"],
                "sequence_expectancy": component_summary["event_expectancy"],
                "baseline_expectancy": component_summary["baseline_expectancy"],
                "expectancy_difference": component_summary["expectancy_difference"],
                "sequence_hit_rate": component_summary["event_hit_rate"],
                "baseline_hit_rate": component_summary["baseline_hit_rate"],
                "hit_rate_difference": component_summary["hit_rate_difference"],
                "sample_size_flag": component_summary["sample_size_flag"],
            }
        )
    return pd.DataFrame(rows, columns=SEQUENCE_COMPONENT_COMPARISON_COLUMNS)


def filter_sequences_by_support(
    sequence_table: pd.DataFrame,
    *,
    min_occurrences: int,
    min_baseline_count: int = 1,
) -> pd.DataFrame:
    """Keep sequence rows with enough sequence and baseline observations."""
    _validate_positive_int(min_occurrences, "min_occurrences")
    _validate_positive_int(min_baseline_count, "min_baseline_count")
    _require_columns(sequence_table, ["sequence_count", "baseline_count"])
    mask = (
        sequence_table["sequence_count"].ge(min_occurrences)
        & sequence_table["baseline_count"].ge(min_baseline_count)
    )
    return sequence_table.loc[mask].copy().reset_index(drop=True)


def rank_event_sequences_by_expectancy(
    sequence_table: pd.DataFrame,
    *,
    sort_by: str = "expectancy_difference",
    ascending: bool = False,
    min_occurrences: int | None = None,
    min_baseline_count: int = 1,
) -> pd.DataFrame:
    """Sort sequence outcome rows for research review."""
    _require_columns(sequence_table, [sort_by])
    ranked = sequence_table.copy()
    if min_occurrences is not None:
        ranked = filter_sequences_by_support(
            ranked,
            min_occurrences=min_occurrences,
            min_baseline_count=min_baseline_count,
        )
    ranked = ranked.sort_values(
        by=sort_by,
        ascending=ascending,
        na_position="last",
        kind="mergesort",
    ).reset_index(drop=True)
    ranked.insert(0, "research_rank", range(1, len(ranked) + 1))
    return ranked


def _sequence_values(
    values: pd.Series,
    *,
    sequences: Iterable[str] | None,
    include_empty_sequence: bool,
) -> list[str]:
    if sequences is not None:
        return _normalize_columns(sequences, "sequences")
    result = values.fillna("").drop_duplicates().tolist()
    if not include_empty_sequence:
        result = [value for value in result if value != ""]
    return result


def _sample_size_flag(sequence_count: int, min_occurrences: int) -> str:
    if sequence_count == 0:
        return "no_events"
    if sequence_count < min_occurrences:
        return "small_sample"
    return "ok"


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


def _validate_positive_int(value: int, name: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise ValueError(f"{name} must be an integer greater than or equal to 1")
