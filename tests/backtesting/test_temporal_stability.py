from __future__ import annotations

import pandas as pd
import pytest

from spy_edge_research.backtesting import (
    assign_temporal_period,
    flag_temporal_concentration,
    summarize_metric_by_period,
    summarize_temporal_stability,
)


def frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "timestamp": pd.to_datetime(
                ["2024-01-02", "2024-01-15", "2024-02-01", "2024-02-10"]
            ),
            "candidate_id": ["a", "a", "a", "b"],
            "expectancy_difference": [0.01, 0.02, -0.01, 0.03],
            "sample_size": [10, 20, 5, 30],
        }
    )


def test_assign_temporal_period_adds_period_column() -> None:
    result = assign_temporal_period(frame(), "timestamp", period="M")

    assert result["temporal_period"].tolist() == ["2024-01", "2024-01", "2024-02", "2024-02"]


def test_summarize_metric_by_period_and_stability() -> None:
    periodized = assign_temporal_period(frame(), "timestamp")
    summary = summarize_metric_by_period(
        periodized,
        "temporal_period",
        ["expectancy_difference"],
        id_column="candidate_id",
    )
    stability = summarize_temporal_stability(summary, ["expectancy_difference_mean"])

    assert summary["row_count"].tolist() == [2, 2]
    assert summary["unique_item_count"].tolist() == [1, 2]
    assert stability["period_count"].tolist() == [2]
    assert stability["stability_caveat"].tolist() == [
        "temporal_stability_is_not_edge_evidence"
    ]


def test_flag_temporal_concentration() -> None:
    concentration = flag_temporal_concentration(frame(), "sample_size", high_share_threshold=0.45)

    assert concentration["temporal_concentration_flag"].tolist() == ["high"]
    assert concentration["largest_period_share"].tolist() == pytest.approx([30 / 65])


def test_temporal_stability_validates_inputs() -> None:
    with pytest.raises(ValueError, match="Missing required columns"):
        assign_temporal_period(frame(), "missing")
    with pytest.raises(ValueError, match="high_share_threshold"):
        flag_temporal_concentration(frame(), "sample_size", high_share_threshold=0)
