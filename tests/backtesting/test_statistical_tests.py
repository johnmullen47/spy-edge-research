from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from spy_edge_research.backtesting import (
    bootstrap_hit_rate_difference,
    bootstrap_mean_difference,
    calculate_confidence_interval,
    permutation_test_event_vs_baseline,
    summarize_statistical_test_result,
)


def test_calculate_confidence_interval_uses_percentiles_and_handles_empty() -> None:
    assert calculate_confidence_interval([1, 2, 3, 4], confidence_level=0.5) == pytest.approx(
        (1.75, 3.25)
    )
    lower, upper = calculate_confidence_interval([np.nan])
    assert np.isnan(lower)
    assert np.isnan(upper)


def test_bootstrap_mean_difference_is_seed_deterministic() -> None:
    event = [0.02, 0.01, 0.03, np.nan]
    baseline = [0.00, -0.01, 0.01, 0.02]

    first = bootstrap_mean_difference(event, baseline, n_bootstrap=200, seed=7)
    second = bootstrap_mean_difference(event, baseline, n_bootstrap=200, seed=7)

    assert first == second
    assert first["test_name"] == "bootstrap_mean_difference"
    assert first["observed_difference"] == pytest.approx(np.mean([0.02, 0.01, 0.03]) - 0.005)
    assert first["ci_lower"] <= first["ci_upper"]
    assert first["n_event"] == 3
    assert first["n_baseline"] == 4
    assert np.isnan(first["p_value"])


def test_bootstrap_hit_rate_difference_is_seed_deterministic() -> None:
    event = [0.02, -0.01, 0.03, 0.04]
    baseline = [0.00, -0.01, 0.01, -0.02]

    result = bootstrap_hit_rate_difference(
        event,
        baseline,
        threshold=0.0,
        n_bootstrap=200,
        seed=11,
    )
    repeated = bootstrap_hit_rate_difference(
        event,
        baseline,
        threshold=0.0,
        n_bootstrap=200,
        seed=11,
    )

    assert result == repeated
    assert result["observed_difference"] == pytest.approx(0.75 - 0.25)
    assert result["threshold"] == 0.0


def test_permutation_test_event_vs_baseline_supports_mean_and_hit_rate() -> None:
    event = [0.02, 0.03, 0.04, 0.01]
    baseline = [-0.01, 0.00, 0.01, -0.02]

    mean_result = permutation_test_event_vs_baseline(
        event,
        baseline,
        statistic="mean",
        n_permutations=200,
        seed=13,
    )
    hit_rate_result = permutation_test_event_vs_baseline(
        event,
        baseline,
        statistic="hit_rate",
        threshold=0.0,
        n_permutations=200,
        seed=13,
    )

    assert mean_result["test_name"] == "permutation_test_event_vs_baseline"
    assert 0.0 <= mean_result["p_value"] <= 1.0
    assert mean_result["observed_difference"] == pytest.approx(0.025 - (-0.005))
    assert hit_rate_result["observed_difference"] == pytest.approx(1.0 - 0.25)
    assert 0.0 <= hit_rate_result["p_value"] <= 1.0


def test_summarize_statistical_test_result_adds_small_sample_warnings() -> None:
    result = bootstrap_mean_difference([0.01, 0.02], [0.00, 0.01], n_bootstrap=20, seed=1)

    summary = summarize_statistical_test_result(result, small_sample_threshold=5)

    assert summary["test_name"].tolist() == ["bootstrap_mean_difference"]
    assert summary["n_event"].tolist() == [2]
    assert summary["n_baseline"].tolist() == [2]
    assert summary["sample_warning"].tolist() == [
        "small_event_sample,small_baseline_sample,no_p_value"
    ]


def test_statistical_test_helpers_validate_inputs() -> None:
    with pytest.raises(ValueError, match="confidence_level"):
        calculate_confidence_interval([1, 2, 3], confidence_level=1.0)
    with pytest.raises(ValueError, match="event_values"):
        bootstrap_mean_difference([np.nan], [1.0], n_bootstrap=10)
    with pytest.raises(ValueError, match="n_resamples"):
        bootstrap_hit_rate_difference([1.0], [0.0], n_bootstrap=0)
    with pytest.raises(ValueError, match="statistic"):
        permutation_test_event_vs_baseline([1.0], [0.0], statistic="median")
    with pytest.raises(KeyError, match="required fields"):
        summarize_statistical_test_result({"test_name": "incomplete"})


def test_statistical_test_summaries_do_not_overclaim_edge() -> None:
    result = permutation_test_event_vs_baseline(
        [0.02, 0.03, 0.04],
        [0.00, -0.01, 0.01],
        n_permutations=100,
        seed=3,
    )
    summary = summarize_statistical_test_result(result)

    forbidden = ("edge_found", "profitable", "approved", "trade", "signal")
    assert not any(word in column for column in summary.columns for word in forbidden)
