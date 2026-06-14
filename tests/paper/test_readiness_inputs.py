import pandas as pd
import pytest

from spy_edge_research.paper import (
    READINESS_VERDICT_ELIGIBLE,
    build_readiness_metrics,
    score_candidate_readiness,
    summarize_readiness_verdict,
)
from spy_edge_research.risk import (
    ExposureLimits,
    compute_event_mask_overlap,
    evaluate_exposure_limits,
    summarize_signal_overlap,
)


def test_build_metrics_from_summaries_feeds_gate():
    oos = pd.DataFrame(
        [
            {
                "oos_positive_expectancy_difference_splits": 3,
                "oos_mean_sample_size": 50.0,
                "oos_mean_expectancy_difference": 0.0002,  # 2 bps, clears the floor
            }
        ]
    )
    overlap_summary = summarize_signal_overlap(
        compute_event_mask_overlap(
            pd.DataFrame({"a": [True, False, True], "b": [False, True, False]}),
            ["a", "b"],
        )
    )
    metrics = build_readiness_metrics(
        oos_stability_row=oos,
        signal_overlap_summary=overlap_summary,
        negative_control_passed=True,
        multiple_testing_passed=True,
        temporal_stable_period_count=3,
    )
    assert metrics["oos_positive_expectancy_difference_splits"] == 3
    assert metrics["oos_mean_sample_size"] == 50.0
    assert "max_pairwise_jaccard" in metrics

    verdict = summarize_readiness_verdict(score_candidate_readiness(metrics)).iloc[0]
    assert verdict["verdict"] == READINESS_VERDICT_ELIGIBLE


def test_build_metrics_from_exposure_limit_checks():
    df = pd.DataFrame({"a": [True, True, False], "b": [True, True, False]})
    overlap = summarize_signal_overlap(compute_event_mask_overlap(df, ["a", "b"]))
    checks = evaluate_exposure_limits(
        limits=ExposureLimits(max_pairwise_jaccard=0.5),
        overlap_summary=overlap,
    )
    metrics = build_readiness_metrics(exposure_limit_checks=checks)
    assert metrics["max_pairwise_jaccard"] == pytest.approx(1.0)


def test_build_metrics_skips_missing_inputs():
    metrics = build_readiness_metrics(negative_control_passed=True)
    assert metrics == {"negative_control_passed": True}


def test_build_metrics_validates_types():
    with pytest.raises(TypeError):
        build_readiness_metrics(oos_stability_row=123)
