"""Research-only out-of-sample validation helpers for candidate edges.

Candidate records are hypotheses. These helpers compare candidate outcomes
inside chronological train/test splits without creating strategy rules,
signals, execution instructions, or tradability claims.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

import numpy as np
import pandas as pd

from spy_edge_research.backtesting.candidate_edges import (
    build_candidate_edge_registry,
    validate_candidate_edge,
)
from spy_edge_research.backtesting.event_forward_outcomes import (
    calculate_event_expectancy,
    calculate_event_hit_rate,
)
from spy_edge_research.backtesting.time_splits import validate_time_series_split


OOS_EDGE_VALIDATION_COLUMNS: list[str] = [
    "candidate_id",
    "candidate_type",
    "name",
    "direction",
    "horizon",
    "split_number",
    "train_start",
    "train_end",
    "test_start",
    "test_end",
    "train_window_size",
    "test_window_size",
    "evaluation_target",
    "hypothesis_definition",
    "train_sample_size",
    "train_baseline_sample_size",
    "train_expectancy",
    "train_baseline_expectancy",
    "train_expectancy_difference",
    "train_hit_rate",
    "train_baseline_hit_rate",
    "train_hit_rate_difference",
    "train_sample_size_flag",
    "oos_sample_size",
    "oos_baseline_sample_size",
    "oos_expectancy",
    "oos_baseline_expectancy",
    "oos_expectancy_difference",
    "oos_hit_rate",
    "oos_baseline_hit_rate",
    "oos_hit_rate_difference",
    "oos_sample_size_flag",
    "caveats",
]

OOS_STABILITY_COLUMNS: list[str] = [
    "candidate_id",
    "candidate_type",
    "name",
    "direction",
    "horizon",
    "split_count",
    "oos_positive_expectancy_difference_splits",
    "oos_positive_hit_rate_difference_splits",
    "oos_mean_expectancy_difference",
    "oos_std_expectancy_difference",
    "oos_min_expectancy_difference",
    "oos_max_expectancy_difference",
    "oos_mean_hit_rate_difference",
    "oos_mean_sample_size",
    "small_sample_split_count",
    "caveats",
]


def evaluate_candidate_edge_in_split(
    df: pd.DataFrame,
    candidate: Mapping[str, Any],
    split: Mapping[str, Any],
    *,
    outcome_columns_by_horizon: Mapping[str, str] | None = None,
    hit_rate_threshold: float = 0.0,
    min_events: int = 1,
    align_outcomes_to_candidate_direction: bool = False,
) -> pd.Series:
    """Evaluate one candidate hypothesis in one chronological train/test split."""
    record = validate_candidate_edge(candidate)
    validated_split = validate_time_series_split(split)
    _validate_positive_int(min_events, "min_events")
    _validate_number(hit_rate_threshold, "hit_rate_threshold")

    train_indices = list(validated_split["train_indices"])
    test_indices = list(validated_split["test_indices"])
    _validate_indices_within_frame(df, train_indices + test_indices)

    definition = _resolve_candidate_definition(
        record,
        outcome_columns_by_horizon=outcome_columns_by_horizon,
    )
    _require_columns(df, definition["required_columns"])

    train_metrics = _evaluate_candidate_metrics(
        df.iloc[train_indices],
        definition=definition,
        direction=record["direction"],
        hit_rate_threshold=hit_rate_threshold,
        min_events=min_events,
        align_outcomes_to_candidate_direction=align_outcomes_to_candidate_direction,
    )
    oos_metrics = _evaluate_candidate_metrics(
        df.iloc[test_indices],
        definition=definition,
        direction=record["direction"],
        hit_rate_threshold=hit_rate_threshold,
        min_events=min_events,
        align_outcomes_to_candidate_direction=align_outcomes_to_candidate_direction,
    )
    caveats = _dedupe_strings(
        [
            *record["caveats"],
            "chronological_train_test_split",
            "out_of_sample_result_is_not_edge_proof",
            *train_metrics.pop("caveats"),
            *oos_metrics.pop("caveats"),
        ]
    )

    return pd.Series(
        {
            "candidate_id": record["candidate_id"],
            "candidate_type": record["candidate_type"],
            "name": record["name"],
            "direction": record["direction"],
            "horizon": record["horizon"],
            "split_number": validated_split["split_number"],
            "train_start": min(train_indices),
            "train_end": max(train_indices),
            "test_start": min(test_indices),
            "test_end": max(test_indices),
            "train_window_size": len(train_indices),
            "test_window_size": len(test_indices),
            "evaluation_target": definition["outcome_column"],
            "hypothesis_definition": definition["hypothesis_definition"],
            **{f"train_{key}": value for key, value in train_metrics.items()},
            **{f"oos_{key}": value for key, value in oos_metrics.items()},
            "caveats": caveats,
        },
        index=OOS_EDGE_VALIDATION_COLUMNS,
    )


def evaluate_candidate_registry_oos(
    df: pd.DataFrame,
    registry: pd.DataFrame,
    splits: Iterable[Mapping[str, Any]],
    *,
    outcome_columns_by_horizon: Mapping[str, str] | None = None,
    hit_rate_threshold: float = 0.0,
    min_events: int = 1,
    align_outcomes_to_candidate_direction: bool = False,
) -> pd.DataFrame:
    """Evaluate every candidate record across chronological OOS splits."""
    validated_registry = build_candidate_edge_registry(_candidate_records_from_frame(registry))
    split_records = [validate_time_series_split(split) for split in splits]
    if validated_registry.empty or not split_records:
        return pd.DataFrame(columns=OOS_EDGE_VALIDATION_COLUMNS)

    rows = []
    for candidate in _candidate_records_from_frame(validated_registry):
        for split in split_records:
            rows.append(
                evaluate_candidate_edge_in_split(
                    df,
                    candidate,
                    split,
                    outcome_columns_by_horizon=outcome_columns_by_horizon,
                    hit_rate_threshold=hit_rate_threshold,
                    min_events=min_events,
                    align_outcomes_to_candidate_direction=align_outcomes_to_candidate_direction,
                )
            )
    return pd.DataFrame(rows, columns=OOS_EDGE_VALIDATION_COLUMNS).reset_index(drop=True)


def compare_in_sample_vs_oos_results(oos_results: pd.DataFrame) -> pd.DataFrame:
    """Add train-vs-OOS diagnostic differences to validation rows."""
    required = [
        "train_expectancy_difference",
        "oos_expectancy_difference",
        "train_hit_rate_difference",
        "oos_hit_rate_difference",
    ]
    _require_columns(oos_results, required)
    compared = oos_results.copy()
    compared["oos_minus_train_expectancy_difference"] = (
        compared["oos_expectancy_difference"] - compared["train_expectancy_difference"]
    )
    compared["oos_minus_train_hit_rate_difference"] = (
        compared["oos_hit_rate_difference"] - compared["train_hit_rate_difference"]
    )
    compared["same_expectancy_difference_sign"] = _same_nonzero_sign(
        compared["train_expectancy_difference"],
        compared["oos_expectancy_difference"],
    )
    compared["same_hit_rate_difference_sign"] = _same_nonzero_sign(
        compared["train_hit_rate_difference"],
        compared["oos_hit_rate_difference"],
    )
    return compared


def summarize_oos_edge_stability(oos_results: pd.DataFrame) -> pd.DataFrame:
    """Summarize candidate OOS stability across chronological splits."""
    if oos_results.empty:
        return pd.DataFrame(columns=OOS_STABILITY_COLUMNS)
    _require_columns(
        oos_results,
        [
            "candidate_id",
            "candidate_type",
            "name",
            "direction",
            "horizon",
            "oos_expectancy_difference",
            "oos_hit_rate_difference",
            "oos_sample_size",
            "oos_sample_size_flag",
            "caveats",
        ],
    )

    rows = []
    group_columns = ["candidate_id", "candidate_type", "name", "direction", "horizon"]
    for keys, group in oos_results.groupby(group_columns, sort=True, dropna=False):
        expectancy = pd.to_numeric(group["oos_expectancy_difference"], errors="coerce")
        hit_rate = pd.to_numeric(group["oos_hit_rate_difference"], errors="coerce")
        sample_size = pd.to_numeric(group["oos_sample_size"], errors="coerce")
        rows.append(
            {
                **dict(zip(group_columns, keys)),
                "split_count": int(len(group)),
                "oos_positive_expectancy_difference_splits": int(expectancy.gt(0).sum()),
                "oos_positive_hit_rate_difference_splits": int(hit_rate.gt(0).sum()),
                "oos_mean_expectancy_difference": _nan_safe_mean(expectancy),
                "oos_std_expectancy_difference": _nan_safe_std(expectancy),
                "oos_min_expectancy_difference": _nan_safe_min(expectancy),
                "oos_max_expectancy_difference": _nan_safe_max(expectancy),
                "oos_mean_hit_rate_difference": _nan_safe_mean(hit_rate),
                "oos_mean_sample_size": _nan_safe_mean(sample_size),
                "small_sample_split_count": int(
                    group["oos_sample_size_flag"].isin(["no_events", "small_sample"]).sum()
                ),
                "caveats": _dedupe_strings(
                    [
                        "stability_summary_is_descriptive_only",
                        *[
                            caveat
                            for caveats in group["caveats"]
                            for caveat in _coerce_caveats(caveats)
                        ],
                    ]
                ),
            }
        )
    return pd.DataFrame(rows, columns=OOS_STABILITY_COLUMNS)


def _evaluate_candidate_metrics(
    df: pd.DataFrame,
    *,
    definition: Mapping[str, Any],
    direction: str,
    hit_rate_threshold: float,
    min_events: int,
    align_outcomes_to_candidate_direction: bool,
) -> dict[str, Any]:
    event_mask = _candidate_mask(df, definition)
    outcome_values = pd.to_numeric(df[definition["outcome_column"]], errors="coerce")
    if align_outcomes_to_candidate_direction and direction == "short":
        outcome_values = -outcome_values
    valid_outcome = outcome_values.notna()
    candidate_sample = outcome_values.loc[event_mask & valid_outcome]
    baseline_sample = outcome_values.loc[valid_outcome]
    sample_size = int(candidate_sample.count())
    baseline_sample_size = int(baseline_sample.count())
    baseline_expectancy = calculate_event_expectancy(baseline_sample)
    baseline_hit_rate = calculate_event_hit_rate(
        baseline_sample,
        threshold=hit_rate_threshold,
    )
    sample_size_flag = _sample_size_flag(sample_size, min_events)
    caveats = []
    if sample_size_flag != "ok":
        caveats.append(f"{sample_size_flag}_in_split")

    if sample_size < min_events:
        expectancy = np.nan
        hit_rate = np.nan
        expectancy_difference = np.nan
        hit_rate_difference = np.nan
    else:
        expectancy = calculate_event_expectancy(candidate_sample)
        hit_rate = calculate_event_hit_rate(
            candidate_sample,
            threshold=hit_rate_threshold,
        )
        expectancy_difference = expectancy - baseline_expectancy
        hit_rate_difference = hit_rate - baseline_hit_rate

    return {
        "sample_size": sample_size,
        "baseline_sample_size": baseline_sample_size,
        "expectancy": expectancy,
        "baseline_expectancy": baseline_expectancy,
        "expectancy_difference": expectancy_difference,
        "hit_rate": hit_rate,
        "baseline_hit_rate": baseline_hit_rate,
        "hit_rate_difference": hit_rate_difference,
        "sample_size_flag": sample_size_flag,
        "caveats": caveats,
    }


def _resolve_candidate_definition(
    candidate: Mapping[str, Any],
    *,
    outcome_columns_by_horizon: Mapping[str, str] | None,
) -> dict[str, Any]:
    context = dict(candidate["context"])
    outcome_column = context.get("outcome_column")
    if outcome_column is None and outcome_columns_by_horizon is not None:
        outcome_column = outcome_columns_by_horizon.get(candidate["horizon"])
    if not isinstance(outcome_column, str) or not outcome_column:
        raise ValueError(
            "candidate context must include outcome_column or outcome_columns_by_horizon "
            "must map the candidate horizon"
        )

    candidate_type = candidate["candidate_type"]
    if candidate_type == "event":
        event_column = context.get("event_column", candidate["name"])
        if not isinstance(event_column, str) or not event_column:
            raise ValueError("event candidates require a non-empty event_column or name")
        return {
            "outcome_column": outcome_column,
            "required_columns": [event_column, outcome_column],
            "candidate_type": candidate_type,
            "event_column": event_column,
            "hypothesis_definition": f"event:{event_column}",
        }
    if candidate_type == "sequence":
        sequence_column = context.get("sequence_column")
        sequence_value = context.get("event_sequence", candidate["name"])
        if not isinstance(sequence_column, str) or not sequence_column:
            raise ValueError("sequence candidates require context.sequence_column")
        if not isinstance(sequence_value, str) or not sequence_value:
            raise ValueError("sequence candidates require a non-empty event_sequence or name")
        return {
            "outcome_column": outcome_column,
            "required_columns": [sequence_column, outcome_column],
            "candidate_type": candidate_type,
            "sequence_column": sequence_column,
            "sequence_value": sequence_value,
            "hypothesis_definition": f"sequence:{sequence_column}={sequence_value}",
        }
    if candidate_type == "conditional_event":
        event_column = context.get("event_column", candidate["name"])
        context_filters = context.get("context_filters", {})
        if not isinstance(event_column, str) or not event_column:
            raise ValueError(
                "conditional_event candidates require a non-empty event_column or name"
            )
        if not isinstance(context_filters, Mapping):
            raise TypeError("context.context_filters must be a mapping when provided")
        filter_columns = [str(column) for column in context_filters.keys()]
        return {
            "outcome_column": outcome_column,
            "required_columns": [event_column, outcome_column, *filter_columns],
            "candidate_type": candidate_type,
            "event_column": event_column,
            "context_filters": dict(context_filters),
            "hypothesis_definition": (
                f"conditional_event:{event_column}|"
                + "|".join(f"{key}={value}" for key, value in context_filters.items())
            ),
        }
    raise ValueError(f"unsupported candidate_type: {candidate_type}")


def _candidate_mask(df: pd.DataFrame, definition: Mapping[str, Any]) -> pd.Series:
    if definition["candidate_type"] == "sequence":
        return df[definition["sequence_column"]].fillna("").eq(definition["sequence_value"])

    mask = df[definition["event_column"]].fillna(False).astype(bool)
    if definition["candidate_type"] == "conditional_event":
        for column, value in definition.get("context_filters", {}).items():
            mask &= df[column].eq(value)
    return mask


def _sample_size_flag(sample_size: int, min_events: int) -> str:
    if sample_size == 0:
        return "no_events"
    if sample_size < min_events:
        return "small_sample"
    return "ok"


def _same_nonzero_sign(left: pd.Series, right: pd.Series) -> pd.Series:
    left_values = pd.to_numeric(left, errors="coerce")
    right_values = pd.to_numeric(right, errors="coerce")
    return (
        left_values.notna()
        & right_values.notna()
        & (np.sign(left_values) == np.sign(right_values))
        & left_values.ne(0)
        & right_values.ne(0)
    )


def _candidate_records_from_frame(registry: pd.DataFrame) -> list[dict[str, Any]]:
    records = []
    for record in registry.to_dict("records"):
        normalized = dict(record)
        for field in ("data_start", "data_end"):
            if pd.isna(normalized.get(field)):
                normalized[field] = None
        records.append(normalized)
    return records


def _nan_safe_mean(values: pd.Series) -> float:
    values = values.dropna()
    return np.nan if values.empty else float(values.mean())


def _nan_safe_std(values: pd.Series) -> float:
    values = values.dropna()
    return np.nan if len(values) < 2 else float(values.std(ddof=1))


def _nan_safe_min(values: pd.Series) -> float:
    values = values.dropna()
    return np.nan if values.empty else float(values.min())


def _nan_safe_max(values: pd.Series) -> float:
    values = values.dropna()
    return np.nan if values.empty else float(values.max())


def _dedupe_strings(values: Iterable[str]) -> list[str]:
    result = []
    seen = set()
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result


def _coerce_caveats(value: Any) -> list[str]:
    if isinstance(value, list):
        return [item for item in value if isinstance(item, str)]
    return []


def _validate_indices_within_frame(df: pd.DataFrame, indices: list[int]) -> None:
    invalid = [index for index in indices if index < 0 or index >= len(df)]
    if invalid:
        raise IndexError(f"split indices outside DataFrame bounds: {invalid}")


def _require_columns(df: pd.DataFrame, columns: Iterable[str]) -> None:
    missing = [column for column in columns if column not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")


def _validate_positive_int(value: int, name: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise ValueError(f"{name} must be an integer greater than or equal to 1")


def _validate_number(value: float, name: str) -> None:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError(f"{name} must be numeric")
