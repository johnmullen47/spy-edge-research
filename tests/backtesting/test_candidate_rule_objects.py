from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from spy_edge_research.backtesting import (
    build_candidate_rule_catalog,
    create_candidate_edge,
    create_candidate_rule_object,
    read_candidate_rule_catalog,
    summarize_candidate_rule_catalog,
    validate_candidate_rule_object,
    write_candidate_rule_catalog,
)


def candidate_record(candidate_id: str = "event_vwap_reclaim_5m") -> dict[str, object]:
    return create_candidate_edge(
        candidate_id=candidate_id,
        candidate_type="event",
        name="event_vwap_reclaim",
        direction="long",
        horizon="5m",
        context={"event_column": "event_vwap_reclaim", "outcome_column": "fwd_5m_return"},
        sample_size=42,
        baseline_sample_size=390,
        expectancy=0.0015,
        baseline_expectancy=0.0004,
        hit_rate=0.57,
        baseline_hit_rate=0.51,
        caveats=["candidate_is_hypothesis"],
        data_start="2024-01-02",
        data_end="2024-03-29",
        reproducibility_metadata={"run_id": "run_001"},
    )


def rule_object(rule_object_id: str = "rule_event_vwap_reclaim_5m") -> dict[str, object]:
    return create_candidate_rule_object(
        rule_object_id=rule_object_id,
        candidate=candidate_record(),
        condition_spec={
            "event_column": "event_vwap_reclaim",
            "context_filters": {"session_bucket": "open"},
        },
        evaluation_spec={
            "outcome_column": "fwd_5m_return",
            "min_oos_splits": 3,
            "min_oos_sample_size": 30,
        },
        validation_summary={
            "oos_split_count": 4,
            "oos_mean_expectancy_difference": 0.0008,
        },
        robustness_summary={
            "parameter_sensitivity_flag": "moderate_variation",
        },
        required_columns=[
            "event_vwap_reclaim",
            "session_bucket",
            "fwd_5m_return",
        ],
        caveats=["requires_additional_review"],
        reproducibility_metadata={"robustness_report_id": "robustness_001"},
    )


def test_create_candidate_rule_object_preserves_candidate_identity_and_caveats() -> None:
    record = rule_object()

    assert record["rule_object_id"] == "rule_event_vwap_reclaim_5m"
    assert record["candidate_id"] == "event_vwap_reclaim_5m"
    assert record["candidate_type"] == "event"
    assert record["direction"] == "long"
    assert record["research_state"] == "research_only"
    assert record["condition_spec"]["event_column"] == "event_vwap_reclaim"
    assert record["evaluation_spec"]["outcome_column"] == "fwd_5m_return"
    assert record["required_columns"] == [
        "event_vwap_reclaim",
        "session_bucket",
        "fwd_5m_return",
    ]
    assert record["caveats"][:3] == [
        "research_only_rule_object",
        "not_a_trading_signal",
        "not_deployment_approval",
    ]
    assert "candidate_is_hypothesis" in record["caveats"]
    assert "requires_additional_review" in record["caveats"]


def test_validate_candidate_rule_object_rejects_incomplete_invalid_or_forbidden_records() -> None:
    record = rule_object()

    with pytest.raises(KeyError, match="required fields"):
        validate_candidate_rule_object(
            {key: value for key, value in record.items() if key != "evaluation_spec"}
        )

    invalid_state = record.copy()
    invalid_state["research_state"] = "ready_for_use"
    with pytest.raises(ValueError, match="research_state"):
        validate_candidate_rule_object(invalid_state)

    invalid_spec = record.copy()
    invalid_spec["condition_spec"] = ["not", "a", "mapping"]
    with pytest.raises(TypeError, match="condition_spec"):
        validate_candidate_rule_object(invalid_spec)

    invalid_columns = record.copy()
    invalid_columns["required_columns"] = ["event_vwap_reclaim", ""]
    with pytest.raises(ValueError, match="columns"):
        validate_candidate_rule_object(invalid_columns)

    forbidden = record.copy()
    forbidden["evaluation_spec"] = {"execution_rule": "never allowed"}
    with pytest.raises(ValueError, match="forbidden"):
        validate_candidate_rule_object(forbidden)


def test_build_candidate_rule_catalog_sorts_and_rejects_duplicate_ids() -> None:
    catalog = build_candidate_rule_catalog(
        [
            rule_object("z_rule"),
            rule_object("a_rule"),
        ]
    )

    assert catalog["rule_object_id"].tolist() == ["a_rule", "z_rule"]
    assert catalog.columns.tolist() == [
        "rule_object_id",
        "candidate_id",
        "candidate_type",
        "name",
        "direction",
        "horizon",
        "research_state",
        "condition_spec",
        "evaluation_spec",
        "validation_summary",
        "robustness_summary",
        "required_columns",
        "caveats",
        "reproducibility_metadata",
    ]

    with pytest.raises(ValueError, match="duplicate"):
        build_candidate_rule_catalog([rule_object("duplicate"), rule_object("duplicate")])


def test_summarize_candidate_rule_catalog_reports_inventory_not_rankings() -> None:
    first = rule_object("first")
    second = rule_object("second")
    second["research_state"] = "needs_more_validation"
    catalog = build_candidate_rule_catalog([first, second])

    summary = summarize_candidate_rule_catalog(catalog)

    assert summary["rule_object_count"].tolist() == [1, 1]
    assert summary["unique_required_column_count"].tolist() == [3, 3]
    assert set(summary["summary_caveat"]) == {"candidate_rule_catalog_is_research_only"}
    assert "research_rank" not in summary.columns


def test_write_and_read_candidate_rule_catalog_round_trips_json(tmp_path: Path) -> None:
    catalog = build_candidate_rule_catalog([rule_object()])
    output_path = tmp_path / "candidate_rule_objects.json"

    written = write_candidate_rule_catalog(
        catalog,
        output_path,
        metadata={"milestone": 37},
    )
    payload = json.loads(output_path.read_text())
    loaded = read_candidate_rule_catalog(output_path)

    assert written == output_path
    assert payload["metadata"] == {"milestone": 37}
    assert payload["candidate_rule_objects"][0]["rule_object_id"] == (
        "rule_event_vwap_reclaim_5m"
    )
    pd.testing.assert_frame_equal(loaded, catalog)

    with pytest.raises(FileExistsError, match="already exists"):
        write_candidate_rule_catalog(catalog, output_path)


def test_read_candidate_rule_catalog_validates_payload(tmp_path: Path) -> None:
    missing = tmp_path / "missing_candidate_rule_objects.json"
    missing.write_text(json.dumps({"metadata": {}}), encoding="utf-8")

    with pytest.raises(KeyError, match="candidate_rule_objects"):
        read_candidate_rule_catalog(missing)


def test_candidate_rule_objects_avoid_execution_or_deployment_columns() -> None:
    catalog = build_candidate_rule_catalog([rule_object()])
    summary = summarize_candidate_rule_catalog(catalog)

    forbidden = (
        "buy",
        "sell",
        "entry",
        "exit",
        "approved",
        "live",
        "trade_signal",
        "order",
        "broker",
        "route",
        "execution",
    )
    assert not any(word in column for column in catalog.columns for word in forbidden)
    assert not any(word in column for column in summary.columns for word in forbidden)
