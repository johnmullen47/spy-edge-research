from __future__ import annotations

import pandas as pd
import pytest

from spy_edge_research.backtesting import (
    build_random_condition_control,
    build_shifted_condition_control,
    evaluate_negative_control_outcomes,
    summarize_negative_control_risk,
)


def frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "event_a": [True, False, True, False, True],
            "fwd_5m_return": [0.02, -0.01, 0.01, -0.02, 0.03],
        }
    )


def test_build_shifted_condition_control_adds_shifted_boolean_column() -> None:
    shifted = build_shifted_condition_control(frame(), "event_a", shift_periods=1)

    assert shifted["event_a_shift_control_1"].tolist() == [
        False,
        True,
        False,
        True,
        False,
    ]


def test_build_random_condition_control_is_seed_deterministic() -> None:
    first = build_random_condition_control(frame(), "event_a", seed=7)
    second = build_random_condition_control(frame(), "event_a", seed=7)

    assert first["event_a_random_control"].tolist() == second["event_a_random_control"].tolist()
    assert sorted(first["event_a_random_control"].tolist()) == sorted(frame()["event_a"].tolist())


def test_evaluate_negative_control_outcomes_and_risk_summary() -> None:
    controls = build_shifted_condition_control(frame(), "event_a", shift_periods=1)
    controls = build_random_condition_control(controls, "event_a", seed=1)

    results = evaluate_negative_control_outcomes(
        controls,
        "event_a",
        ["event_a_shift_control_1", "event_a_random_control"],
        "fwd_5m_return",
    )
    summary = summarize_negative_control_risk(results)

    assert results["control_name"].tolist()[0] == "observed_condition"
    assert results["sample_size"].tolist()[0] == 3
    assert summary["control_count"].tolist() == [2]
    assert summary["risk_caveat"].tolist() == [
        "negative_controls_are_data_mining_diagnostics_only"
    ]


def test_negative_control_helpers_validate_inputs() -> None:
    with pytest.raises(ValueError, match="non-zero integer"):
        build_shifted_condition_control(frame(), "event_a", shift_periods=0)
    with pytest.raises(ValueError, match="Missing required columns"):
        build_random_condition_control(frame(), "missing")
    with pytest.raises(ValueError, match="observed_condition"):
        summarize_negative_control_risk(
            pd.DataFrame(
                {
                    "control_name": ["control"],
                    "expectancy_difference": [0.0],
                    "hit_rate_difference": [0.0],
                }
            )
        )
