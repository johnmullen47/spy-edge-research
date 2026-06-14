"""Score a candidate's research metrics against readiness criteria.

Produces a per-criterion scorecard and a gated verdict with reasons. The verdict
is a research gate: ``eligible_for_paper_consideration`` means only that the
evidence bar is met, never that a trade is authorized. A missing metric is
treated conservatively as insufficient evidence (not ready).
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping
from typing import Any

import pandas as pd

from spy_edge_research.paper.readiness_criteria import ReadinessCriteria


READINESS_VERDICT_ELIGIBLE = "eligible_for_paper_consideration"
READINESS_VERDICT_NOT_READY = "not_ready"
READINESS_SCORE_CAVEAT = "readiness_score_is_research_gate_not_trade_authorization"

SCORECARD_COLUMNS: tuple[str, ...] = (
    "criterion",
    "metric_key",
    "observed",
    "threshold",
    "comparison",
    "passed",
    "status",
    "reason",
    "criterion_caveat",
)


def score_candidate_readiness(
    metrics: Mapping[str, Any],
    criteria: ReadinessCriteria | None = None,
) -> pd.DataFrame:
    """Score candidate metrics against readiness criteria, one row per criterion."""
    if not isinstance(metrics, Mapping):
        raise TypeError("metrics must be a mapping")
    crit = criteria or ReadinessCriteria()
    if not isinstance(crit, ReadinessCriteria):
        raise TypeError("criteria must be a ReadinessCriteria instance")

    rows: list[dict[str, Any]] = []

    def evaluate(criterion: str, metric_key: str, threshold: Any, comparison: str) -> None:
        observed = metrics.get(metric_key)
        if observed is None or (isinstance(observed, float) and math.isnan(observed)):
            rows.append(_row(criterion, metric_key, observed, threshold, comparison,
                             passed=False, status="not_evaluated",
                             reason=f"insufficient_evidence:{metric_key}"))
            return
        if comparison == "ge":
            passed = observed >= threshold
            reason = "" if passed else f"{criterion}_below_min"
        elif comparison == "le":
            passed = observed <= threshold
            reason = "" if passed else f"{criterion}_above_max"
        else:  # is_true
            passed = observed is True
            reason = "" if passed else f"{criterion}_not_passed"
        rows.append(_row(criterion, metric_key, observed, threshold, comparison,
                         passed=passed, status="pass" if passed else "fail", reason=reason))

    if crit.min_oos_positive_splits is not None:
        evaluate("oos_positive_splits", "oos_positive_expectancy_difference_splits",
                 crit.min_oos_positive_splits, "ge")
    if crit.min_oos_mean_sample_size is not None:
        evaluate("oos_mean_sample_size", "oos_mean_sample_size", crit.min_oos_mean_sample_size, "ge")
    if crit.require_negative_control_pass:
        evaluate("negative_control", "negative_control_passed", True, "is_true")
    if crit.require_multiple_testing_pass:
        evaluate("multiple_testing", "multiple_testing_passed", True, "is_true")
    if crit.min_temporal_stable_periods is not None:
        evaluate("temporal_stable_periods", "temporal_stable_period_count",
                 crit.min_temporal_stable_periods, "ge")
    if crit.max_pairwise_jaccard is not None:
        evaluate("exposure_overlap", "max_pairwise_jaccard", crit.max_pairwise_jaccard, "le")
    if crit.min_edge_bps is not None:
        evaluate("economic_edge_bps", "edge_bps", crit.min_edge_bps, "ge")

    return pd.DataFrame(rows, columns=list(SCORECARD_COLUMNS))


def summarize_readiness_verdict(scorecard: pd.DataFrame) -> pd.DataFrame:
    """Reduce a scorecard to one gated verdict row with failing reasons."""
    _require_columns(scorecard, ["passed", "reason"])
    total = int(len(scorecard))
    passed_flags = scorecard["passed"].astype(bool)
    passed_count = int(passed_flags.sum())
    all_passed = total > 0 and passed_count == total
    failing = [reason for reason in scorecard.loc[~passed_flags, "reason"].tolist() if reason]
    verdict = READINESS_VERDICT_ELIGIBLE if all_passed else READINESS_VERDICT_NOT_READY
    return pd.DataFrame(
        [
            {
                "verdict": verdict,
                "criteria_count": total,
                "passed_count": passed_count,
                "failing_reasons": "; ".join(failing),
                "verdict_caveat": READINESS_SCORE_CAVEAT,
            }
        ]
    )


def _row(
    criterion: str,
    metric_key: str,
    observed: Any,
    threshold: Any,
    comparison: str,
    *,
    passed: bool,
    status: str,
    reason: str,
) -> dict[str, Any]:
    return {
        "criterion": criterion,
        "metric_key": metric_key,
        "observed": observed,
        "threshold": threshold,
        "comparison": comparison,
        "passed": bool(passed),
        "status": status,
        "reason": reason,
        "criterion_caveat": READINESS_SCORE_CAVEAT,
    }


def _require_columns(df: pd.DataFrame, columns: Iterable[str]) -> None:
    missing = [column for column in columns if column not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")
