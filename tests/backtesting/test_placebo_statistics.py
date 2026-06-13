from __future__ import annotations

import pandas as pd
import pytest

from spy_edge_research.backtesting import (
    build_repeated_random_controls,
    build_shifted_control_grid,
    evaluate_placebo_control_suite,
    summarize_placebo_percentile_ranks,
)


def frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "event_a": [True, False, True, False, True, False],
            "fwd_5m_return": [0.02, -0.01, 0.01, -0.02, 0.03, 0.0],
        }
    )


def test_build_shifted_control_grid_adds_multiple_controls() -> None:
    result, columns = build_shifted_control_grid(frame(), "event_a", [1, 2])

    assert columns == ["event_a_shift_control_1", "event_a_shift_control_2"]
    assert columns[0] in result.columns
    assert columns[1] in result.columns


def test_build_repeated_random_controls_is_seed_deterministic() -> None:
    first, first_columns = build_repeated_random_controls(frame(), "event_a", n_controls=3, seed=7)
    second, second_columns = build_repeated_random_controls(frame(), "event_a", n_controls=3, seed=7)

    assert first_columns == second_columns
    for column in first_columns:
        assert first[column].tolist() == second[column].tolist()


def test_evaluate_placebo_control_suite_and_percentile_summary() -> None:
    results = evaluate_placebo_control_suite(
        frame(),
        "event_a",
        "fwd_5m_return",
        shift_periods=[1],
        n_random_controls=2,
        seed=11,
    )
    summary = summarize_placebo_percentile_ranks(results)

    assert results["control_name"].tolist()[0] == "observed_condition"
    assert summary["placebo_control_count"].tolist() == [3]
    assert summary["placebo_caveat"].tolist() == [
        "placebo_statistics_are_research_diagnostics_only"
    ]


def test_placebo_statistics_validate_inputs() -> None:
    with pytest.raises(ValueError, match="n_controls"):
        build_repeated_random_controls(frame(), "event_a", n_controls=0)
    with pytest.raises(ValueError, match="at least one placebo"):
        evaluate_placebo_control_suite(frame(), "event_a", "fwd_5m_return")
    with pytest.raises(ValueError, match="observed_condition"):
        summarize_placebo_percentile_ranks(
            pd.DataFrame(
                {
                    "control_name": ["control"],
                    "expectancy_difference": [0.0],
                    "hit_rate_difference": [0.0],
                }
            )
        )
