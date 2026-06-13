"""Research-only context review helpers for candidate rule replay."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

import pandas as pd

from spy_edge_research.backtesting.candidate_rule_objects import (
    build_candidate_rule_catalog,
)
from spy_edge_research.backtesting.candidate_rule_replay import replay_candidate_rule_object

from spy_edge_research._internal._common import (
    normalize_columns as _normalize_columns,
    require_columns as _require_columns,
)


def review_rule_replay_by_context(
    df: pd.DataFrame,
    rule_object: Mapping[str, Any],
    context_columns: Iterable[str],
) -> pd.DataFrame:
    """Review one rule object's replay sample distribution across context buckets."""
    contexts = _normalize_columns(context_columns, "context_columns")
    _require_columns(df, contexts)
    replay = replay_candidate_rule_object(df, rule_object)
    if replay["condition_spec_status"] != "ok":
        return pd.DataFrame(
            [
                {
                    "rule_object_id": replay["rule_object_id"],
                    "candidate_id": replay["candidate_id"],
                    "context_key": "not_evaluated",
                    "context_row_count": len(df),
                    "context_replay_sample_size": 0,
                    "context_replay_rate": 0.0,
                    "context_review_caveat": "rule_replay_not_evaluated",
                }
            ]
        )
    mask = _replay_mask(df, rule_object)
    rows = []
    group_key = contexts[0] if len(contexts) == 1 else contexts
    for values, group in df.assign(_rule_replay_mask=mask).groupby(group_key, dropna=False, sort=True):
        values_tuple = (values,) if len(contexts) == 1 else tuple(values)
        context_key = "|".join(f"{column}={value}" for column, value in zip(contexts, values_tuple))
        sample_size = int(group["_rule_replay_mask"].sum())
        rows.append(
            {
                "rule_object_id": replay["rule_object_id"],
                "candidate_id": replay["candidate_id"],
                "context_key": context_key,
                "context_row_count": len(group),
                "context_replay_sample_size": sample_size,
                "context_replay_rate": 0.0 if len(group) == 0 else sample_size / len(group),
                "context_review_caveat": "context_review_is_descriptive_only",
            }
        )
    return pd.DataFrame(rows)


def review_rule_catalog_by_context(
    df: pd.DataFrame,
    catalog: pd.DataFrame,
    context_columns: Iterable[str],
) -> pd.DataFrame:
    """Review all rule objects in a catalog across context buckets."""
    validated = build_candidate_rule_catalog(catalog.to_dict("records"))
    tables = [
        review_rule_replay_by_context(df, record, context_columns)
        for record in validated.to_dict("records")
    ]
    if not tables:
        return pd.DataFrame(
            columns=[
                "rule_object_id",
                "candidate_id",
                "context_key",
                "context_row_count",
                "context_replay_sample_size",
                "context_replay_rate",
                "context_review_caveat",
            ]
        )
    return pd.concat(tables, ignore_index=True)


def summarize_rule_context_review(context_review: pd.DataFrame) -> pd.DataFrame:
    """Summarize context review concentration by rule object."""
    _require_columns(
        context_review,
        ["rule_object_id", "context_replay_sample_size", "context_key"],
    )
    if context_review.empty:
        return pd.DataFrame(
            columns=[
                "rule_object_id",
                "context_bucket_count",
                "total_context_replay_sample_size",
                "largest_context_sample_size",
                "largest_context_share",
                "summary_caveat",
            ]
        )
    rows = []
    for rule_object_id, group in context_review.groupby("rule_object_id", sort=True, dropna=False):
        counts = pd.to_numeric(group["context_replay_sample_size"], errors="coerce").fillna(0)
        total = int(counts.sum())
        largest = int(counts.max()) if len(counts) else 0
        rows.append(
            {
                "rule_object_id": rule_object_id,
                "context_bucket_count": int(group["context_key"].nunique()),
                "total_context_replay_sample_size": total,
                "largest_context_sample_size": largest,
                "largest_context_share": 0.0 if total == 0 else largest / total,
                "summary_caveat": "context_concentration_is_not_edge_evidence",
            }
        )
    return pd.DataFrame(rows)


def _replay_mask(df: pd.DataFrame, rule_object: Mapping[str, Any]) -> pd.Series:
    spec = dict(rule_object["condition_spec"])
    mask = pd.Series(True, index=df.index)
    if spec.get("event_column") is not None:
        mask &= df[spec["event_column"]].fillna(False).astype(bool)
    if spec.get("sequence_column") is not None:
        mask &= df[spec["sequence_column"]].fillna("").eq(spec["event_sequence"])
    for column, expected in dict(spec.get("context_filters", {})).items():
        mask &= df[column].eq(expected)
    return mask

