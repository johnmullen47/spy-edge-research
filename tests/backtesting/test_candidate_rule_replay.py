from __future__ import annotations

import pandas as pd
import pytest

from spy_edge_research.backtesting import (
    build_candidate_rule_catalog,
    create_candidate_edge,
    create_candidate_rule_object,
    replay_candidate_rule_catalog,
    replay_candidate_rule_object,
    summarize_candidate_rule_replay,
)


def candidate(candidate_id: str = "candidate_a") -> dict[str, object]:
    return create_candidate_edge(
        candidate_id=candidate_id,
        candidate_type="event",
        name="event_a",
        direction="long",
        horizon="5m",
        sample_size=2,
        baseline_sample_size=5,
        expectancy=0.001,
        baseline_expectancy=0.0,
        hit_rate=0.6,
        baseline_hit_rate=0.5,
    )


def frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "event_a": [True, False, True, True],
            "sequence": ["a>b", "b>c", "a>b", ""],
            "session_bucket": ["open", "open", "lunch", "open"],
            "fwd_5m_return": [0.01, -0.01, 0.02, 0.0],
        }
    )


def test_replay_candidate_rule_object_applies_event_and_context_filters() -> None:
    rule = create_candidate_rule_object(
        rule_object_id="rule_a",
        candidate=candidate(),
        condition_spec={"event_column": "event_a", "context_filters": {"session_bucket": "open"}},
        evaluation_spec={"outcome_column": "fwd_5m_return"},
        required_columns=["event_a", "session_bucket", "fwd_5m_return"],
    )

    result = replay_candidate_rule_object(frame(), rule)

    assert result["replay_sample_size"] == 2
    assert result["replay_rate"] == pytest.approx(0.5)
    assert result["condition_spec_status"] == "ok"
    assert result["missing_required_columns"] == []
    assert "rule_replay_is_research_only" in result["replay_caveats"]


def test_replay_candidate_rule_object_applies_sequence_conditions() -> None:
    rule = create_candidate_rule_object(
        rule_object_id="rule_sequence",
        candidate={**candidate("candidate_sequence"), "candidate_type": "sequence"},
        condition_spec={"sequence_column": "sequence", "event_sequence": "a>b"},
        evaluation_spec={"outcome_column": "fwd_5m_return"},
        required_columns=["sequence", "fwd_5m_return"],
    )

    result = replay_candidate_rule_object(frame(), rule)

    assert result["replay_sample_size"] == 2
    assert result["condition_spec_status"] == "ok"


def test_replay_candidate_rule_catalog_and_summary() -> None:
    rule = create_candidate_rule_object(
        rule_object_id="rule_a",
        candidate=candidate(),
        condition_spec={"event_column": "event_a"},
        evaluation_spec={"outcome_column": "fwd_5m_return"},
        required_columns=["event_a", "fwd_5m_return"],
    )
    catalog = build_candidate_rule_catalog([rule])

    replay = replay_candidate_rule_catalog(frame(), catalog)
    summary = summarize_candidate_rule_replay(replay)

    assert replay["replay_sample_size"].tolist() == [3]
    assert summary["total_replay_sample_size"].tolist() == [3]
    assert summary["summary_caveat"].tolist() == ["replay_summary_is_not_signal_performance"]


def test_replay_reports_missing_required_columns_without_evaluating() -> None:
    rule = create_candidate_rule_object(
        rule_object_id="rule_missing",
        candidate=candidate(),
        condition_spec={"event_column": "missing_event"},
        evaluation_spec={"outcome_column": "fwd_5m_return"},
        required_columns=["missing_event", "fwd_5m_return"],
    )

    result = replay_candidate_rule_object(frame(), rule)

    assert result["condition_spec_status"] == "missing_required_columns"
    assert result["replay_sample_size"] == 0
    assert result["missing_required_columns"] == ["missing_event"]
    assert "replay_not_evaluated_missing_columns" in result["replay_caveats"]


def test_replay_rejects_invalid_sequence_spec() -> None:
    rule = create_candidate_rule_object(
        rule_object_id="rule_bad_sequence",
        candidate=candidate(),
        condition_spec={"sequence_column": "sequence"},
        evaluation_spec={"outcome_column": "fwd_5m_return"},
        required_columns=["sequence", "fwd_5m_return"],
    )

    with pytest.raises(ValueError, match="event_sequence"):
        replay_candidate_rule_object(frame(), rule)
