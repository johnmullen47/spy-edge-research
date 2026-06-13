import pandas as pd
import pytest

from spy_edge_research.paper import (
    READINESS_VERDICT_ELIGIBLE,
    READINESS_VERDICT_NOT_READY,
    ReadinessCriteria,
    default_readiness_criteria,
    score_candidate_readiness,
    summarize_readiness_verdict,
)


def _eligible_metrics():
    return {
        "oos_positive_expectancy_difference_splits": 3,
        "oos_mean_sample_size": 50.0,
        "negative_control_passed": True,
        "multiple_testing_passed": True,
        "temporal_stable_period_count": 3,
        "max_pairwise_jaccard": 0.5,
    }


def test_default_criteria_values():
    criteria = default_readiness_criteria()
    assert isinstance(criteria, ReadinessCriteria)
    assert criteria.min_oos_positive_splits == 2
    assert criteria.max_pairwise_jaccard == 0.8


def test_eligible_candidate_passes_all_criteria():
    scorecard = score_candidate_readiness(_eligible_metrics())
    assert len(scorecard) == 6
    assert scorecard["passed"].all()
    verdict = summarize_readiness_verdict(scorecard).iloc[0]
    assert verdict["verdict"] == READINESS_VERDICT_ELIGIBLE
    assert verdict["passed_count"] == 6
    assert verdict["failing_reasons"] == ""


def test_failing_metrics_produce_not_ready_with_reasons():
    metrics = _eligible_metrics()
    metrics["max_pairwise_jaccard"] = 0.95
    metrics["multiple_testing_passed"] = False
    scorecard = score_candidate_readiness(metrics)
    verdict = summarize_readiness_verdict(scorecard).iloc[0]
    assert verdict["verdict"] == READINESS_VERDICT_NOT_READY
    assert "exposure_overlap_above_max" in verdict["failing_reasons"]
    assert "multiple_testing_not_passed" in verdict["failing_reasons"]


def test_missing_metric_is_insufficient_evidence_and_not_ready():
    metrics = _eligible_metrics()
    del metrics["negative_control_passed"]
    scorecard = score_candidate_readiness(metrics)
    negative_control = scorecard.set_index("criterion").loc["negative_control"]
    assert negative_control["status"] == "not_evaluated"
    assert negative_control["reason"] == "insufficient_evidence:negative_control_passed"
    verdict = summarize_readiness_verdict(scorecard).iloc[0]
    assert verdict["verdict"] == READINESS_VERDICT_NOT_READY


def test_disabled_criteria_are_skipped():
    criteria = ReadinessCriteria(
        min_oos_positive_splits=None,
        min_oos_mean_sample_size=None,
        require_negative_control_pass=False,
        require_multiple_testing_pass=False,
        min_temporal_stable_periods=None,
        max_pairwise_jaccard=0.8,
    )
    scorecard = score_candidate_readiness({"max_pairwise_jaccard": 0.5}, criteria)
    assert len(scorecard) == 1
    assert scorecard.iloc[0]["criterion"] == "exposure_overlap"


def test_score_requires_mapping_and_criteria_type():
    with pytest.raises(TypeError, match="metrics must be a mapping"):
        score_candidate_readiness([1, 2, 3])
    with pytest.raises(TypeError, match="ReadinessCriteria"):
        score_candidate_readiness({}, criteria={"min_oos_positive_splits": 1})
