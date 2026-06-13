from __future__ import annotations

import pandas as pd
import pytest

from spy_edge_research.backtesting import (
    add_candidate_family_columns,
    aggregate_candidate_families,
    summarize_candidate_family_concentration,
)


def sample_table() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "rule_object_id": ["rule_a", "rule_b", "rule_c"],
            "candidate_type": ["event", "event", "sequence"],
            "name": ["event_vwap_reclaim", "event_vwap_loss", "a>b"],
            "horizon": ["5m", "5m", "10m"],
            "direction": ["long", "short", "long"],
            "condition_spec": [
                {"event_column": "event_vwap_reclaim", "context_filters": {"session_bucket": "open"}},
                {"event_column": "event_vwap_loss"},
                {"sequence_column": "recent_sequence", "event_sequence": "a>b"},
            ],
        }
    )


def test_add_candidate_family_columns_derives_descriptive_families() -> None:
    enriched = add_candidate_family_columns(sample_table())

    assert enriched["event_family"].tolist() == ["event", "event", "sequence"]
    assert enriched["condition_family"].tolist() == ["event", "event", "sequence"]
    assert enriched["context_family"].tolist() == ["session_bucket", "none", "none"]


def test_aggregate_candidate_families_counts_items_without_ranking() -> None:
    aggregated = aggregate_candidate_families(sample_table())

    assert aggregated["item_count"].sum() == 3
    assert set(aggregated["aggregation_caveat"]) == {
        "family_aggregation_is_descriptive_only"
    }
    assert "research_rank" not in aggregated.columns


def test_summarize_candidate_family_concentration() -> None:
    aggregated = aggregate_candidate_families(sample_table(), group_columns=["event_family"])

    summary = summarize_candidate_family_concentration(aggregated)

    assert summary["family_count"].tolist() == [2]
    assert summary["total_items"].tolist() == [3]
    assert summary["largest_family_item_count"].tolist() == [2]
    assert summary["largest_family_share"].tolist() == pytest.approx([2 / 3])
    assert summary["summary_caveat"].tolist() == [
        "family_concentration_is_not_edge_evidence"
    ]


def test_candidate_family_aggregation_validates_columns() -> None:
    with pytest.raises(ValueError, match="Missing required columns"):
        aggregate_candidate_families(sample_table().drop(columns=["horizon"]))
