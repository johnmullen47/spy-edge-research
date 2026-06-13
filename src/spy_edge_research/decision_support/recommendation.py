"""Assemble human-review records from readiness-eligible candidates.

For each candidate whose readiness verdict is ``eligible_for_paper_consideration``
this builds one descriptive review record — direction, horizon, sample size, the
candidate's expectancy difference, and any portfolio risk flags — and marks it
``requires_human_review``. It is a reshaping of already-computed research numbers
into a review surface; it makes no trade decision, recommends no size, and is
never an instruction. Not-yet-eligible candidates are excluded.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

import pandas as pd

from spy_edge_research.simulation.eligibility import select_eligible_candidates
from spy_edge_research.decision_support.contracts import (
    DECISION_SUPPORT_REPORT_CAVEAT,
    raise_forbidden_decision_support_fields,
)

REVIEW_RECORD_COLUMNS: tuple[str, ...] = (
    "candidate_id",
    "direction",
    "horizon",
    "sample_size",
    "expectancy_difference",
    "verdict",
    "risk_flags",
    "requires_human_review",
    "review_caveat",
)


def build_decision_support_records(
    candidates: Iterable[Mapping[str, Any]],
    verdicts: pd.DataFrame,
    *,
    exposure_limit_checks: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Build one human-review record per readiness-eligible candidate.

    ``candidates`` is the candidate edge registry as records (e.g. loaded from a
    run's ``candidate_edges.json``); ``verdicts`` is the per-candidate readiness
    verdict table. ``exposure_limit_checks`` (optional) supplies portfolio risk
    flags, attached as descriptive context to every record.
    """
    eligible = select_eligible_candidates(candidates, verdicts)
    risk_flags = "; ".join(_collect_risk_flags(exposure_limit_checks))

    rows: list[dict[str, Any]] = []
    for candidate in eligible:
        rows.append(
            {
                "candidate_id": str(candidate.get("candidate_id")),
                "direction": str(candidate.get("direction", "unknown")),
                "horizon": str(candidate.get("horizon", "")),
                "sample_size": _as_number(candidate.get("sample_size")),
                "expectancy_difference": _as_number(
                    candidate.get("expectancy_difference")
                ),
                "verdict": "eligible_for_paper_consideration",
                "risk_flags": risk_flags,
                "requires_human_review": True,
                "review_caveat": DECISION_SUPPORT_REPORT_CAVEAT,
            }
        )

    records = pd.DataFrame(rows, columns=list(REVIEW_RECORD_COLUMNS))
    raise_forbidden_decision_support_fields(
        {column: None for column in records.columns},
        name="decision support review columns",
    )
    return records


def summarize_decision_support(records: pd.DataFrame) -> pd.DataFrame:
    """Summarize the review set: counts by direction and risk-flag presence."""
    if not isinstance(records, pd.DataFrame):
        raise TypeError("records must be a pandas DataFrame")
    total = int(len(records))
    if total:
        long_count = int((records["direction"] == "long").sum())
        short_count = int((records["direction"] == "short").sum())
        flagged = int((records["risk_flags"].astype(str).str.len() > 0).sum())
    else:
        long_count = short_count = flagged = 0
    return pd.DataFrame(
        [
            {
                "review_candidate_count": total,
                "long_count": long_count,
                "short_count": short_count,
                "risk_flagged_count": flagged,
                "summary_caveat": DECISION_SUPPORT_REPORT_CAVEAT,
            }
        ]
    )


def _collect_risk_flags(exposure_limit_checks: pd.DataFrame | None) -> list[str]:
    if (
        exposure_limit_checks is None
        or not isinstance(exposure_limit_checks, pd.DataFrame)
        or exposure_limit_checks.empty
        or "flag" not in exposure_limit_checks.columns
    ):
        return []
    return [
        str(flag)
        for flag in exposure_limit_checks["flag"].dropna().tolist()
        if str(flag).strip()
    ]


def _as_number(value: Any) -> float | None:
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return None if pd.isna(number) else number
