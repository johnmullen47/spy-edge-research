"""Research-only family aggregation helpers for candidates and rule objects."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

import pandas as pd


def add_candidate_family_columns(
    table: pd.DataFrame,
    *,
    context_column: str = "context",
    condition_spec_column: str = "condition_spec",
) -> pd.DataFrame:
    """Add descriptive family columns for candidate or rule-object review."""
    result = table.copy()
    result["event_family"] = [
        _family_from_row(row, context_column=context_column, condition_spec_column=condition_spec_column)
        for row in result.to_dict("records")
    ]
    result["condition_family"] = [
        _condition_family(row, context_column=context_column, condition_spec_column=condition_spec_column)
        for row in result.to_dict("records")
    ]
    result["context_family"] = [
        _context_family(row, context_column=context_column, condition_spec_column=condition_spec_column)
        for row in result.to_dict("records")
    ]
    return result


def aggregate_candidate_families(
    table: pd.DataFrame,
    *,
    group_columns: Iterable[str] | None = None,
) -> pd.DataFrame:
    """Aggregate candidates/rule objects by descriptive family columns."""
    enriched = add_candidate_family_columns(table)
    groups = list(group_columns or [
        "event_family",
        "condition_family",
        "context_family",
        "horizon",
        "direction",
    ])
    _require_columns(enriched, groups)
    id_column = "rule_object_id" if "rule_object_id" in enriched.columns else "candidate_id"
    _require_columns(enriched, [id_column])
    return (
        enriched.groupby(groups, dropna=False, sort=True)
        .agg(
            item_count=(id_column, "nunique"),
            item_ids=(id_column, lambda values: sorted(set(values))),
        )
        .reset_index()
        .assign(aggregation_caveat="family_aggregation_is_descriptive_only")
    )


def summarize_candidate_family_concentration(
    family_table: pd.DataFrame,
    *,
    count_column: str = "item_count",
) -> pd.DataFrame:
    """Summarize whether reviewed artifacts cluster in a few families."""
    _require_columns(family_table, [count_column])
    counts = pd.to_numeric(family_table[count_column], errors="coerce").dropna()
    total = int(counts.sum()) if not counts.empty else 0
    max_count = int(counts.max()) if not counts.empty else 0
    return pd.DataFrame(
        [
            {
                "family_count": int(len(family_table)),
                "total_items": total,
                "largest_family_item_count": max_count,
                "largest_family_share": 0.0 if total == 0 else max_count / total,
                "summary_caveat": "family_concentration_is_not_edge_evidence",
            }
        ]
    )


def _family_from_row(
    row: Mapping[str, Any],
    *,
    context_column: str,
    condition_spec_column: str,
) -> str:
    if isinstance(row.get("candidate_type"), str):
        return row["candidate_type"]
    spec = _mapping_value(row, condition_spec_column)
    context = _mapping_value(row, context_column)
    event_column = spec.get("event_column") or context.get("event_column") or row.get("name")
    if isinstance(event_column, str) and event_column:
        return event_column.split("_")[1] if "_" in event_column else event_column
    return "unknown"


def _condition_family(
    row: Mapping[str, Any],
    *,
    context_column: str,
    condition_spec_column: str,
) -> str:
    spec = _mapping_value(row, condition_spec_column)
    context = _mapping_value(row, context_column)
    if spec.get("sequence_column") or context.get("sequence_column"):
        return "sequence"
    if spec.get("event_column") or context.get("event_column"):
        return "event"
    if spec.get("context_filters") or context.get("context_filters"):
        return "context_only"
    return "unknown"


def _context_family(
    row: Mapping[str, Any],
    *,
    context_column: str,
    condition_spec_column: str,
) -> str:
    spec = _mapping_value(row, condition_spec_column)
    context = _mapping_value(row, context_column)
    filters = spec.get("context_filters") or context.get("context_filters") or {}
    if isinstance(filters, Mapping) and filters:
        return "|".join(sorted(str(key) for key in filters))
    return "none"


def _mapping_value(row: Mapping[str, Any], column: str) -> dict[str, Any]:
    value = row.get(column, {})
    return dict(value) if isinstance(value, Mapping) else {}


def _require_columns(df: pd.DataFrame, columns: Iterable[str]) -> None:
    missing = [column for column in columns if column not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")
