"""Research-only comparisons between rule replay and OOS validation."""

from __future__ import annotations

import numpy as np
import pandas as pd

from spy_edge_research._internal._common import (
    require_columns as _require_columns,
)


RULE_OOS_COMPARISON_COLUMNS: list[str] = [
    "rule_object_id",
    "candidate_id",
    "candidate_type",
    "direction",
    "horizon",
    "replay_sample_size",
    "oos_total_sample_size",
    "oos_split_count",
    "sample_size_difference",
    "sample_size_ratio",
    "comparison_status",
    "comparison_caveats",
]


def compare_rule_replay_to_oos_results(
    replay_results: pd.DataFrame,
    oos_results: pd.DataFrame,
    *,
    max_relative_sample_difference: float = 0.25,
) -> pd.DataFrame:
    """Compare rule-object replay sample sizes against OOS validation records."""
    _validate_non_negative_number(
        max_relative_sample_difference,
        "max_relative_sample_difference",
    )
    _require_columns(
        replay_results,
        [
            "rule_object_id",
            "candidate_id",
            "candidate_type",
            "direction",
            "horizon",
            "replay_sample_size",
        ],
    )
    _require_columns(
        oos_results,
        ["candidate_id", "oos_sample_size"],
    )
    oos_summary = (
        oos_results.groupby("candidate_id", dropna=False, sort=True)
        .agg(
            oos_total_sample_size=("oos_sample_size", "sum"),
            oos_split_count=("oos_sample_size", "count"),
        )
        .reset_index()
    )
    merged = replay_results.merge(oos_summary, on="candidate_id", how="left")
    rows = []
    for row in merged.to_dict("records"):
        replay_sample_size = int(row["replay_sample_size"])
        oos_total = row.get("oos_total_sample_size")
        if pd.isna(oos_total):
            oos_total = 0
            oos_split_count = 0
            status = "missing_oos_reference"
            caveats = ["no_oos_records_for_candidate"]
        else:
            oos_total = int(oos_total)
            oos_split_count = int(row["oos_split_count"])
            difference = replay_sample_size - oos_total
            denominator = max(oos_total, 1)
            relative_difference = abs(difference) / denominator
            status = (
                "sample_size_mismatch"
                if relative_difference > max_relative_sample_difference
                else "ok"
            )
            caveats = ["comparison_is_research_diagnostic_only"]
        difference = replay_sample_size - oos_total
        ratio = np.nan if oos_total == 0 else replay_sample_size / oos_total
        rows.append(
            {
                "rule_object_id": row["rule_object_id"],
                "candidate_id": row["candidate_id"],
                "candidate_type": row["candidate_type"],
                "direction": row["direction"],
                "horizon": row["horizon"],
                "replay_sample_size": replay_sample_size,
                "oos_total_sample_size": oos_total,
                "oos_split_count": oos_split_count,
                "sample_size_difference": difference,
                "sample_size_ratio": ratio,
                "comparison_status": status,
                "comparison_caveats": caveats,
            }
        )
    return pd.DataFrame(rows, columns=RULE_OOS_COMPARISON_COLUMNS)


def summarize_rule_oos_comparison(comparison: pd.DataFrame) -> pd.DataFrame:
    """Summarize replay-vs-OOS comparison statuses."""
    _require_columns(comparison, ["comparison_status", "sample_size_difference"])
    if comparison.empty:
        return pd.DataFrame(
            columns=[
                "comparison_status",
                "rule_object_count",
                "mean_sample_size_difference",
                "summary_caveat",
            ]
        )
    return (
        comparison.groupby("comparison_status", dropna=False, sort=True)
        .agg(
            rule_object_count=("rule_object_id", "nunique"),
            mean_sample_size_difference=("sample_size_difference", "mean"),
        )
        .reset_index()
        .assign(summary_caveat="oos_comparison_is_reproducibility_diagnostic_only")
    )


def _validate_non_negative_number(value: float, name: str) -> None:
    if not isinstance(value, (int, float)) or isinstance(value, bool) or value < 0:
        raise ValueError(f"{name} must be a non-negative number")
