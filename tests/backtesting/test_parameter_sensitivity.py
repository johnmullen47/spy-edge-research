from __future__ import annotations

import pandas as pd
import pytest

from spy_edge_research.backtesting import (
    build_parameter_grid,
    compare_parameter_sensitivity_to_reference,
    evaluate_parameter_grid,
    summarize_parameter_sensitivity,
)


def test_build_parameter_grid_creates_deterministic_cartesian_product() -> None:
    grid = build_parameter_grid(
        {
            "lookback": [5, 10],
            "threshold": [0.5, 1.0],
        },
        parameter_set_prefix="study",
    )

    assert grid["parameter_set_id"].tolist() == [
        "study_001",
        "study_002",
        "study_003",
        "study_004",
    ]
    assert grid["parameters"].tolist() == [
        {"lookback": 5, "threshold": 0.5},
        {"lookback": 5, "threshold": 1.0},
        {"lookback": 10, "threshold": 0.5},
        {"lookback": 10, "threshold": 1.0},
    ]
    assert grid["lookback"].tolist() == [5, 5, 10, 10]
    assert grid["threshold"].tolist() == [0.5, 1.0, 0.5, 1.0]


def test_evaluate_parameter_grid_runs_research_evaluator_for_each_row() -> None:
    grid = build_parameter_grid({"lookback": [5, 10], "threshold": [0.5, 1.0]})

    def evaluator(parameters: dict[str, object]) -> dict[str, float | int]:
        lookback = int(parameters["lookback"])
        threshold = float(parameters["threshold"])
        return {
            "sample_size": lookback * 2,
            "expectancy_difference": (lookback / 10000.0) - (threshold / 1000.0),
        }

    results = evaluate_parameter_grid(
        grid,
        evaluator,
        metric_columns=["sample_size", "expectancy_difference"],
    )

    assert results["sample_size"].tolist() == [10, 10, 20, 20]
    assert results["expectancy_difference"].tolist() == pytest.approx(
        [0.0, -0.0005, 0.0005, 0.0]
    )
    assert results["parameter_set_id"].tolist() == grid["parameter_set_id"].tolist()


def test_summarize_parameter_sensitivity_flags_metric_variation() -> None:
    results = pd.DataFrame(
        {
            "candidate_id": ["a", "a", "a"],
            "expectancy_difference": [0.001, 0.0011, 0.0012],
            "hit_rate_difference": [0.01, 0.05, 0.12],
        }
    )

    summary = summarize_parameter_sensitivity(
        results,
        ["expectancy_difference", "hit_rate_difference"],
        group_columns=["candidate_id"],
        low_sensitivity_relative_range=0.25,
        high_sensitivity_relative_range=1.0,
    )

    expectancy = summary.loc[summary["metric_column"].eq("expectancy_difference")].iloc[0]
    hit_rate = summary.loc[summary["metric_column"].eq("hit_rate_difference")].iloc[0]
    assert expectancy["candidate_id"] == "a"
    assert expectancy["parameter_set_count"] == 3
    assert expectancy["metric_range"] == pytest.approx(0.0002)
    assert expectancy["sensitivity_flag"] == "low_variation"
    assert hit_rate["sensitivity_flag"] == "high_variation"
    assert "parameter_sensitivity_is_descriptive_only" in hit_rate["caveats"]


def test_compare_parameter_sensitivity_to_reference_adds_descriptive_differences() -> None:
    grid = build_parameter_grid({"lookback": [5, 10], "threshold": [0.5]})
    results = grid.assign(expectancy_difference=[0.001, 0.0014], hit_rate_difference=[0.02, 0.03])

    compared = compare_parameter_sensitivity_to_reference(
        results,
        "params_001",
        ["expectancy_difference", "hit_rate_difference"],
    )

    assert compared["reference_parameter_set_id"].tolist() == ["params_001", "params_001"]
    assert compared["expectancy_difference_minus_reference"].tolist() == pytest.approx(
        [0.0, 0.0004]
    )
    assert compared["hit_rate_difference_minus_reference"].tolist() == pytest.approx(
        [0.0, 0.01]
    )
    assert compared["comparison_caveat"].tolist() == [
        "reference_comparison_is_descriptive_only",
        "reference_comparison_is_descriptive_only",
    ]


def test_parameter_sensitivity_helpers_validate_inputs() -> None:
    with pytest.raises(ValueError, match="at least one parameter"):
        build_parameter_grid({})
    with pytest.raises(ValueError, match="must not be empty"):
        build_parameter_grid({"lookback": []})
    with pytest.raises(TypeError, match="evaluator"):
        evaluate_parameter_grid(build_parameter_grid({"lookback": [5]}), "not-callable")
    with pytest.raises(ValueError, match="missing metric"):
        evaluate_parameter_grid(
            build_parameter_grid({"lookback": [5]}),
            lambda parameters: {"sample_size": 10},
            metric_columns=["expectancy_difference"],
        )
    with pytest.raises(ValueError, match="exactly one row"):
        compare_parameter_sensitivity_to_reference(
            build_parameter_grid({"lookback": [5]}).assign(expectancy_difference=[0.001]),
            "missing",
            ["expectancy_difference"],
        )
    with pytest.raises(ValueError, match="greater than or equal"):
        summarize_parameter_sensitivity(
            pd.DataFrame({"metric": [1.0]}),
            ["metric"],
            low_sensitivity_relative_range=1.0,
            high_sensitivity_relative_range=0.5,
        )


def test_parameter_sensitivity_outputs_avoid_optimization_or_trading_columns() -> None:
    grid = build_parameter_grid({"lookback": [5, 10]})
    results = evaluate_parameter_grid(
        grid,
        lambda parameters: {"expectancy_difference": int(parameters["lookback"]) / 10000},
    )
    summary = summarize_parameter_sensitivity(results, ["expectancy_difference"])
    compared = compare_parameter_sensitivity_to_reference(
        results,
        "params_001",
        ["expectancy_difference"],
    )

    forbidden = (
        "best",
        "optimal",
        "buy",
        "sell",
        "entry",
        "exit",
        "approved",
        "live",
        "trade_signal",
    )
    assert not any(word in column for column in results.columns for word in forbidden)
    assert not any(word in column for column in summary.columns for word in forbidden)
    assert not any(word in column for column in compared.columns for word in forbidden)
