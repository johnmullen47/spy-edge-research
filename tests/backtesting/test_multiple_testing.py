from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from spy_edge_research.backtesting import (
    apply_bonferroni_adjustment,
    apply_false_discovery_rate_adjustment,
    count_tested_hypotheses,
    summarize_multiple_testing_risk,
)


def sample_test_results() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "event_family": ["vwap", "vwap", "retest", "retest", "sequence"],
            "horizon": ["5m", "10m", "5m", "10m", "5m"],
            "p_value": [0.001, 0.02, 0.04, 0.20, np.nan],
        }
    )


def test_count_tested_hypotheses_counts_overall_and_by_group() -> None:
    results = sample_test_results()

    assert count_tested_hypotheses(results) == 5
    grouped = count_tested_hypotheses(results, ["event_family"])

    assert grouped["event_family"].tolist() == ["retest", "sequence", "vwap"]
    assert grouped["hypothesis_count"].tolist() == [2, 1, 2]


def test_apply_bonferroni_adjustment_caps_at_one_and_preserves_input() -> None:
    results = sample_test_results()
    original = results.copy(deep=True)

    adjusted = apply_bonferroni_adjustment(results)

    assert adjusted["p_value_bonferroni"].tolist()[:4] == pytest.approx(
        [0.004, 0.08, 0.16, 0.80]
    )
    assert np.isnan(adjusted["p_value_bonferroni"].iloc[4])
    pd.testing.assert_frame_equal(results, original)


def test_apply_false_discovery_rate_adjustment_uses_bh_monotonicity() -> None:
    results = sample_test_results()

    adjusted = apply_false_discovery_rate_adjustment(results)

    assert adjusted["p_value_fdr_bh"].tolist()[:4] == pytest.approx(
        [0.004, 0.04, 0.0533333333, 0.20]
    )
    assert np.isnan(adjusted["p_value_fdr_bh"].iloc[4])


def test_summarize_multiple_testing_risk_counts_adjusted_discoveries() -> None:
    results = sample_test_results()

    summary = summarize_multiple_testing_risk(results, alpha=0.05)

    assert summary["tested_hypotheses"].tolist() == [4]
    assert summary["unadjusted_below_alpha"].tolist() == [3]
    assert summary["bonferroni_below_alpha"].tolist() == [1]
    assert summary["fdr_bh_below_alpha"].tolist() == [2]
    assert summary["multiple_testing_warning"].tolist() == ["low"]


def test_multiple_testing_helpers_validate_inputs() -> None:
    results = sample_test_results()

    with pytest.raises(ValueError, match="Missing required columns"):
        apply_bonferroni_adjustment(results.drop(columns=["p_value"]))
    with pytest.raises(ValueError, match="group_columns"):
        count_tested_hypotheses(results, [])
    with pytest.raises(ValueError, match="alpha"):
        summarize_multiple_testing_risk(results, alpha=1.0)


def test_multiple_testing_outputs_do_not_overclaim_edge() -> None:
    summary = summarize_multiple_testing_risk(sample_test_results())

    forbidden = ("edge_found", "profitable", "approved", "trade", "signal")
    assert not any(word in column for column in summary.columns for word in forbidden)
