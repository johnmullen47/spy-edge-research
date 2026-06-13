"""Research-only replay helpers for candidate rule objects."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

import pandas as pd

from spy_edge_research.backtesting.candidate_rule_objects import (
    build_candidate_rule_catalog,
    validate_candidate_rule_object,
)

from spy_edge_research._internal._common import (
    require_columns as _require_columns,
)

RULE_REPLAY_COLUMNS: list[str] = [
    "rule_object_id",
    "candidate_id",
    "candidate_type",
    "name",
    "direction",
    "horizon",
    "row_count",
    "replay_sample_size",
    "replay_rate",
    "missing_required_columns",
    "condition_spec_status",
    "replay_caveats",
]


def replay_candidate_rule_object(
    df: pd.DataFrame,
    rule_object: Mapping[str, Any],
) -> pd.Series:
    """Replay one rule object's stored condition spec against historical rows."""
    record = validate_candidate_rule_object(rule_object)
    missing_required = [column for column in record["required_columns"] if column not in df.columns]
    if missing_required:
        sample_size = 0
        status = "missing_required_columns"
        caveats = ["replay_not_evaluated_missing_columns"]
    else:
        mask, caveats = _condition_mask(df, record["condition_spec"])
        sample_size = int(mask.sum())
        status = "ok"
    row_count = len(df)
    replay_rate = float(sample_size / row_count) if row_count else 0.0
    return pd.Series(
        {
            "rule_object_id": record["rule_object_id"],
            "candidate_id": record["candidate_id"],
            "candidate_type": record["candidate_type"],
            "name": record["name"],
            "direction": record["direction"],
            "horizon": record["horizon"],
            "row_count": row_count,
            "replay_sample_size": sample_size,
            "replay_rate": replay_rate,
            "missing_required_columns": missing_required,
            "condition_spec_status": status,
            "replay_caveats": _dedupe_strings(
                ["rule_replay_is_research_only", *caveats]
            ),
        },
        index=RULE_REPLAY_COLUMNS,
    )


def replay_candidate_rule_catalog(
    df: pd.DataFrame,
    catalog: pd.DataFrame,
) -> pd.DataFrame:
    """Replay every candidate rule object in a catalog."""
    validated = build_candidate_rule_catalog(catalog.to_dict("records"))
    rows = [
        replay_candidate_rule_object(df, record)
        for record in validated.to_dict("records")
    ]
    if not rows:
        return pd.DataFrame(columns=RULE_REPLAY_COLUMNS)
    return pd.DataFrame(rows, columns=RULE_REPLAY_COLUMNS).reset_index(drop=True)


def summarize_candidate_rule_replay(replay_results: pd.DataFrame) -> pd.DataFrame:
    """Summarize replay status by candidate type, direction, and horizon."""
    _require_columns(
        replay_results,
        [
            "candidate_type",
            "direction",
            "horizon",
            "condition_spec_status",
            "replay_sample_size",
        ],
    )
    if replay_results.empty:
        return pd.DataFrame(
            columns=[
                "candidate_type",
                "direction",
                "horizon",
                "condition_spec_status",
                "rule_object_count",
                "total_replay_sample_size",
                "summary_caveat",
            ]
        )
    return (
        replay_results.groupby(
            ["candidate_type", "direction", "horizon", "condition_spec_status"],
            dropna=False,
            sort=True,
        )
        .agg(
            rule_object_count=("rule_object_id", "nunique"),
            total_replay_sample_size=("replay_sample_size", "sum"),
        )
        .reset_index()
        .assign(summary_caveat="replay_summary_is_not_signal_performance")
    )


def _condition_mask(df: pd.DataFrame, condition_spec: Mapping[str, Any]) -> tuple[pd.Series, list[str]]:
    if not isinstance(condition_spec, Mapping):
        raise TypeError("condition_spec must be a mapping")
    mask = pd.Series(True, index=df.index)
    caveats: list[str] = []

    event_column = condition_spec.get("event_column")
    if event_column is not None:
        _require_columns(df, [event_column])
        mask &= df[event_column].fillna(False).astype(bool)

    sequence_column = condition_spec.get("sequence_column")
    event_sequence = condition_spec.get("event_sequence")
    if sequence_column is not None or event_sequence is not None:
        if not isinstance(sequence_column, str) or not sequence_column:
            raise ValueError("sequence conditions require sequence_column")
        if not isinstance(event_sequence, str) or not event_sequence:
            raise ValueError("sequence conditions require event_sequence")
        _require_columns(df, [sequence_column])
        mask &= df[sequence_column].fillna("").eq(event_sequence)

    context_filters = condition_spec.get("context_filters", {})
    if not isinstance(context_filters, Mapping):
        raise TypeError("context_filters must be a mapping when provided")
    for column, expected in context_filters.items():
        _require_columns(df, [column])
        mask &= df[column].eq(expected)

    if event_column is None and sequence_column is None and not context_filters:
        caveats.append("empty_condition_spec_matches_all_rows")
    return mask, caveats


def _dedupe_strings(values: Iterable[str]) -> list[str]:
    result = []
    seen = set()
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result
