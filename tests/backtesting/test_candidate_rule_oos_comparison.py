from __future__ import annotations

import pandas as pd
import pytest

from spy_edge_research.backtesting import (
    compare_rule_replay_to_oos_results,
    summarize_rule_oos_comparison,
)


def replay_results() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "rule_object_id": ["rule_a", "rule_b", "rule_missing"],
            "candidate_id": ["candidate_a", "candidate_b", "candidate_missing"],
            "candidate_type": ["event", "event", "event"],
            "direction": ["long", "long", "long"],
            "horizon": ["5m", "5m", "5m"],
            "replay_sample_size": [10, 20, 5],
        }
    )


def oos_results() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "candidate_id": ["candidate_a", "candidate_a", "candidate_b"],
            "oos_sample_size": [4, 6, 5],
        }
    )


def test_compare_rule_replay_to_oos_results_flags_mismatch_and_missing_reference() -> None:
    comparison = compare_rule_replay_to_oos_results(
        replay_results(),
        oos_results(),
        max_relative_sample_difference=0.25,
    )

    assert comparison["comparison_status"].tolist() == [
        "ok",
        "sample_size_mismatch",
        "missing_oos_reference",
    ]
    assert comparison["sample_size_difference"].tolist() == [0, 15, 5]
    assert comparison.loc[0, "sample_size_ratio"] == pytest.approx(1.0)
    assert "comparison_is_research_diagnostic_only" in comparison.loc[0, "comparison_caveats"]
    assert "no_oos_records_for_candidate" in comparison.loc[2, "comparison_caveats"]


def test_summarize_rule_oos_comparison_counts_statuses() -> None:
    comparison = compare_rule_replay_to_oos_results(replay_results(), oos_results())

    summary = summarize_rule_oos_comparison(comparison)

    assert set(summary["comparison_status"]) == {
        "ok",
        "sample_size_mismatch",
        "missing_oos_reference",
    }
    assert summary["rule_object_count"].sum() == 3
    assert set(summary["summary_caveat"]) == {
        "oos_comparison_is_reproducibility_diagnostic_only"
    }


def test_rule_oos_comparison_validates_inputs() -> None:
    with pytest.raises(ValueError, match="non-negative"):
        compare_rule_replay_to_oos_results(
            replay_results(),
            oos_results(),
            max_relative_sample_difference=-1,
        )
    with pytest.raises(ValueError, match="Missing required columns"):
        compare_rule_replay_to_oos_results(
            replay_results().drop(columns=["replay_sample_size"]),
            oos_results(),
        )
    with pytest.raises(ValueError, match="Missing required columns"):
        summarize_rule_oos_comparison(pd.DataFrame({"comparison_status": ["ok"]}))
