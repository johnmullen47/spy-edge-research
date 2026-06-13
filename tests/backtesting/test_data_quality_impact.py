from __future__ import annotations

import pandas as pd
import pytest

from spy_edge_research.backtesting import (
    evaluate_quality_filter_impact,
    summarize_column_coverage,
    summarize_required_context_coverage,
    summarize_session_coverage,
)


def frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "session": ["open", "open", "lunch", "close"],
            "date": ["2024-01-02", "2024-01-02", "2024-01-03", "2024-01-03"],
            "outcome": [0.01, None, -0.02, 0.03],
            "context": ["normal", "high", None, "normal"],
            "quality_ok": [True, False, True, True],
            "metric": [1.0, 5.0, 2.0, 3.0],
        }
    )


def test_summarize_column_and_context_coverage() -> None:
    coverage = summarize_column_coverage(frame(), ["outcome", "context"])
    context = summarize_required_context_coverage(frame(), ["outcome", "context"])

    assert coverage["missing_count"].tolist() == [1, 1]
    assert context["complete_context_count"].tolist() == [2]
    assert context["coverage_caveat"].tolist() == [
        "context_coverage_is_research_diagnostic_only"
    ]


def test_summarize_session_coverage() -> None:
    summary = summarize_session_coverage(frame(), "session", date_column="date")

    assert set(summary["session_value"]) == {"open", "lunch", "close"}
    assert summary.loc[summary["session_value"].eq("open"), "row_count"].iloc[0] == 2


def test_evaluate_quality_filter_impact() -> None:
    impact = evaluate_quality_filter_impact(frame(), "quality_ok", ["metric"])

    assert impact["included_count"].tolist() == [3]
    assert impact["excluded_count"].tolist() == [1]
    assert impact["impact_caveat"].tolist() == [
        "quality_filter_impact_is_descriptive_only"
    ]


def test_data_quality_helpers_validate_columns() -> None:
    with pytest.raises(ValueError, match="Missing required columns"):
        summarize_column_coverage(frame(), ["missing"])
    with pytest.raises(ValueError, match="Missing required columns"):
        evaluate_quality_filter_impact(frame(), "missing", ["metric"])
