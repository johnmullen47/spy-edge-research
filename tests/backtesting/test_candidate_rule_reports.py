from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from spy_edge_research.backtesting import (
    build_candidate_rule_catalog,
    build_candidate_rule_report_bundle,
    build_candidate_rule_required_column_inventory,
    create_candidate_edge,
    create_candidate_rule_object,
    export_candidate_rule_report_bundle_to_csv,
    export_candidate_rule_report_bundle_to_json,
    summarize_candidate_rule_caveats,
    summarize_candidate_rule_report_bundle,
    summarize_candidate_rule_research_states,
    validate_candidate_rule_report_bundle,
)


def catalog() -> pd.DataFrame:
    candidate = create_candidate_edge(
        candidate_id="candidate_a",
        candidate_type="event",
        name="event_a",
        direction="long",
        horizon="5m",
        sample_size=20,
        baseline_sample_size=100,
        expectancy=0.001,
        baseline_expectancy=0.0,
        hit_rate=0.55,
        baseline_hit_rate=0.50,
        caveats=["candidate_is_hypothesis"],
    )
    first = create_candidate_rule_object(
        rule_object_id="rule_a",
        candidate=candidate,
        condition_spec={"event_column": "event_a"},
        evaluation_spec={"outcome_column": "fwd_5m_return"},
        required_columns=["event_a", "fwd_5m_return"],
    )
    second = create_candidate_rule_object(
        rule_object_id="rule_b",
        candidate={**candidate, "candidate_id": "candidate_b"},
        condition_spec={"event_column": "event_b"},
        evaluation_spec={"outcome_column": "fwd_5m_return"},
        required_columns=["event_b", "fwd_5m_return"],
        research_state="needs_more_validation",
        caveats=["small_sample_review"],
    )
    return build_candidate_rule_catalog([first, second])


def test_rule_report_tables_summarize_states_columns_and_caveats() -> None:
    cat = catalog()

    states = summarize_candidate_rule_research_states(cat)
    inventory = build_candidate_rule_required_column_inventory(cat)
    caveats = summarize_candidate_rule_caveats(cat)

    assert states["rule_object_count"].sum() == 2
    assert set(inventory["required_column"]) == {"event_a", "event_b", "fwd_5m_return"}
    assert "small_sample_review" in caveats["caveat"].tolist()
    assert set(states["summary_caveat"]) == {"research_state_is_not_deployment_status"}


def test_build_candidate_rule_report_bundle_and_summary() -> None:
    bundle = build_candidate_rule_report_bundle(catalog(), metadata={"milestone": 38})

    assert set(bundle["tables"]) == {
        "rule_catalog",
        "catalog_summary",
        "research_state_breakdown",
        "required_column_inventory",
        "caveat_summary",
    }
    summary = summarize_candidate_rule_report_bundle(bundle)
    assert set(summary["table_name"]) == set(bundle["tables"])
    assert bundle["metadata"]["milestone"] == 38


def test_rule_report_exports_csv_and_json(tmp_path: Path) -> None:
    bundle = build_candidate_rule_report_bundle(catalog(), metadata={"milestone": 38})

    written = export_candidate_rule_report_bundle_to_csv(bundle, tmp_path)
    json_path = export_candidate_rule_report_bundle_to_json(bundle, tmp_path / "report.json")
    payload = json.loads(json_path.read_text())

    assert written["metadata"] == tmp_path / "metadata.json"
    assert (tmp_path / "rule_catalog.csv").exists()
    assert payload["metadata"] == {"milestone": 38}
    assert "required_column_inventory" in payload["tables"]
    with pytest.raises(FileExistsError, match="Refusing to overwrite"):
        export_candidate_rule_report_bundle_to_csv(bundle, tmp_path)
    with pytest.raises(FileExistsError, match="already exists"):
        export_candidate_rule_report_bundle_to_json(bundle, json_path)


def test_rule_report_bundle_validates_inputs() -> None:
    with pytest.raises(TypeError, match="bundle must be a dict"):
        validate_candidate_rule_report_bundle("not-a-bundle")
    with pytest.raises(TypeError, match="must be a pandas DataFrame"):
        validate_candidate_rule_report_bundle({"metadata": {}, "tables": {"bad": []}})
