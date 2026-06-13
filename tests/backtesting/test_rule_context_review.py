from __future__ import annotations

import pandas as pd
import pytest

from spy_edge_research.backtesting import (
    build_candidate_rule_catalog,
    create_candidate_edge,
    create_candidate_rule_object,
    review_rule_catalog_by_context,
    review_rule_replay_by_context,
    summarize_rule_context_review,
)


def frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "event_a": [True, False, True, True],
            "session_bucket": ["open", "open", "lunch", "open"],
            "volatility_regime": ["normal", "high", "normal", "normal"],
            "fwd_5m_return": [0.01, -0.01, 0.02, 0.0],
        }
    )


def rule(rule_id: str = "rule_a") -> dict[str, object]:
    candidate = create_candidate_edge(
        candidate_id=rule_id.replace("rule", "candidate"),
        candidate_type="event",
        name="event_a",
        direction="long",
        horizon="5m",
        sample_size=3,
        baseline_sample_size=4,
        expectancy=0.01,
        baseline_expectancy=0.0,
        hit_rate=0.66,
        baseline_hit_rate=0.5,
    )
    return create_candidate_rule_object(
        rule_object_id=rule_id,
        candidate=candidate,
        condition_spec={"event_column": "event_a"},
        evaluation_spec={"outcome_column": "fwd_5m_return"},
        required_columns=["event_a", "fwd_5m_return"],
    )


def test_review_rule_replay_by_context_counts_samples_by_bucket() -> None:
    review = review_rule_replay_by_context(frame(), rule(), ["session_bucket"])

    assert set(review["context_key"]) == {"session_bucket=lunch", "session_bucket=open"}
    open_row = review.loc[review["context_key"].eq("session_bucket=open")].iloc[0]
    assert open_row["context_row_count"] == 3
    assert open_row["context_replay_sample_size"] == 2
    assert open_row["context_review_caveat"] == "context_review_is_descriptive_only"


def test_review_rule_catalog_by_context_and_summary() -> None:
    catalog = build_candidate_rule_catalog([rule("rule_a"), rule("rule_b")])

    review = review_rule_catalog_by_context(frame(), catalog, ["session_bucket", "volatility_regime"])
    summary = summarize_rule_context_review(review)

    assert set(review["rule_object_id"]) == {"rule_a", "rule_b"}
    assert summary["total_context_replay_sample_size"].tolist() == [3, 3]
    assert set(summary["summary_caveat"]) == {"context_concentration_is_not_edge_evidence"}


def test_context_review_validates_context_columns() -> None:
    with pytest.raises(ValueError, match="Missing required columns"):
        review_rule_replay_by_context(frame(), rule(), ["missing_context"])
