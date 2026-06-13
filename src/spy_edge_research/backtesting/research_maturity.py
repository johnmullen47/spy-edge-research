"""Research-only maturity scoring helpers."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pandas as pd

MATURITY_COMPONENTS: tuple[str, ...] = (
    "evidence_completeness",
    "oos_coverage",
    "placebo_risk_control",
    "temporal_stability",
    "data_quality",
    "caveat_control",
    "decision_status",
)


def create_research_maturity_record(
    *,
    package_id: str,
    subject_id: str,
    component_scores: Mapping[str, float],
    notes: str | None = None,
) -> dict[str, Any]:
    """Create one research maturity record without readiness claims."""
    _validate_non_empty_string(package_id, "package_id")
    _validate_non_empty_string(subject_id, "subject_id")
    scores = {
        component: _score(component_scores.get(component, 0.0), component)
        for component in MATURITY_COMPONENTS
    }
    maturity_score = sum(scores.values()) / len(MATURITY_COMPONENTS)
    return {
        "package_id": package_id,
        "subject_id": subject_id,
        **scores,
        "research_maturity_score": maturity_score,
        "maturity_band": _maturity_band(maturity_score),
        "notes": notes,
        "maturity_caveat": "maturity_score_is_not_trade_readiness",
    }


def build_research_maturity_table(records: list[Mapping[str, Any]]) -> pd.DataFrame:
    """Build a deterministic research maturity table."""
    table = pd.DataFrame([dict(record) for record in records])
    if table.empty:
        return pd.DataFrame(
            columns=[
                "package_id",
                "subject_id",
                *MATURITY_COMPONENTS,
                "research_maturity_score",
                "maturity_band",
                "notes",
                "maturity_caveat",
            ]
        )
    _require_columns(table, ["package_id", "subject_id", *MATURITY_COMPONENTS])
    if table["package_id"].duplicated().any():
        duplicates = sorted(table.loc[table["package_id"].duplicated(), "package_id"])
        raise ValueError(f"duplicate package_id values: {duplicates}")
    return table.sort_values("package_id", kind="mergesort").reset_index(drop=True)


def summarize_research_maturity(maturity_table: pd.DataFrame) -> pd.DataFrame:
    """Summarize maturity bands across research packages."""
    _require_columns(maturity_table, ["maturity_band", "research_maturity_score"])
    if maturity_table.empty:
        return pd.DataFrame(
            columns=[
                "maturity_band",
                "package_count",
                "mean_research_maturity_score",
                "summary_caveat",
            ]
        )
    return (
        maturity_table.groupby("maturity_band", dropna=False, sort=True)
        .agg(
            package_count=("package_id", "nunique"),
            mean_research_maturity_score=("research_maturity_score", "mean"),
        )
        .reset_index()
        .assign(summary_caveat="maturity_summary_is_research_only")
    )


def score_research_package_from_diagnostics(
    *,
    package_id: str,
    subject_id: str,
    has_oos: bool,
    has_placebo: bool,
    has_temporal: bool,
    has_data_quality: bool,
    caveat_count: int = 0,
    decision: str | None = None,
) -> dict[str, Any]:
    """Create a coarse maturity score from available diagnostic coverage."""
    if caveat_count < 0:
        raise ValueError("caveat_count must be non-negative")
    decision_score = {
        "continue_study": 0.75,
        "needs_more_data": 0.45,
        "merge_with_related_hypothesis": 0.5,
        "retire_from_review": 0.2,
    }.get(decision or "", 0.25)
    return create_research_maturity_record(
        package_id=package_id,
        subject_id=subject_id,
        component_scores={
            "evidence_completeness": sum([has_oos, has_placebo, has_temporal, has_data_quality]) / 4,
            "oos_coverage": 1.0 if has_oos else 0.0,
            "placebo_risk_control": 1.0 if has_placebo else 0.0,
            "temporal_stability": 1.0 if has_temporal else 0.0,
            "data_quality": 1.0 if has_data_quality else 0.0,
            "caveat_control": max(0.0, 1.0 - caveat_count / 10.0),
            "decision_status": decision_score,
        },
    )


def _maturity_band(score: float) -> str:
    if score >= 0.75:
        return "well_documented"
    if score >= 0.5:
        return "partial_review"
    return "early_review"


def _score(value: Any, name: str) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool) or value < 0 or value > 1:
        raise ValueError(f"{name} score must be in [0, 1]")
    return float(value)


def _validate_non_empty_string(value: Any, name: str) -> None:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{name} must be a non-empty string")


def _require_columns(df: pd.DataFrame, columns: list[str]) -> None:
    missing = [column for column in columns if column not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")
