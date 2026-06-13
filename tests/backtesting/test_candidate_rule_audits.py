from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from spy_edge_research.backtesting import (
    build_candidate_rule_audit_bundle,
    create_candidate_rule_audit_metadata,
    export_candidate_rule_audit_bundle_to_csv,
    export_candidate_rule_audit_bundle_to_json,
    summarize_candidate_rule_audit_bundle,
    validate_candidate_rule_audit_bundle,
)


def replay_results() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "rule_object_id": ["rule_a"],
            "candidate_id": ["candidate_a"],
            "replay_sample_size": [10],
            "condition_spec_status": ["ok"],
        }
    )


def comparison() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "rule_object_id": ["rule_a"],
            "candidate_id": ["candidate_a"],
            "comparison_status": ["ok"],
            "sample_size_difference": [0],
        }
    )


def test_create_candidate_rule_audit_metadata() -> None:
    metadata = create_candidate_rule_audit_metadata(notes="unit")

    assert metadata["created_at_utc"].endswith("+00:00")
    assert metadata["milestone"] == "41"
    assert metadata["audit_caveat"] == "candidate_rule_audit_is_research_only"
    assert metadata["notes"] == "unit"


def test_build_candidate_rule_audit_bundle_copies_tables_and_adds_caveats() -> None:
    replay = replay_results()
    bundle = build_candidate_rule_audit_bundle(
        replay_results=replay,
        oos_comparison=comparison(),
        metadata={"milestone": 41},
    )

    assert set(bundle["tables"]) == {
        "replay_results",
        "oos_comparison",
        "robustness_caveats",
    }
    assert bundle["metadata"] == {"milestone": 41}
    assert "candidate_rule_audit_is_research_only" in bundle["tables"]["robustness_caveats"][
        "caveat"
    ].tolist()
    bundle["tables"]["replay_results"].loc[0, "candidate_id"] = "changed"
    assert replay.loc[0, "candidate_id"] == "candidate_a"


def test_summarize_candidate_rule_audit_bundle_reports_structure() -> None:
    bundle = build_candidate_rule_audit_bundle(
        replay_results=replay_results(),
        oos_comparison=comparison(),
    )

    summary = summarize_candidate_rule_audit_bundle(bundle)

    assert set(summary["table_name"]) == {
        "replay_results",
        "oos_comparison",
        "robustness_caveats",
    }
    assert summary["row_count"].sum() == 4


def test_candidate_rule_audit_exports_csv_and_json(tmp_path: Path) -> None:
    bundle = build_candidate_rule_audit_bundle(
        replay_results=replay_results(),
        oos_comparison=comparison(),
        metadata={"milestone": 41},
    )

    written = export_candidate_rule_audit_bundle_to_csv(bundle, tmp_path)
    json_path = export_candidate_rule_audit_bundle_to_json(bundle, tmp_path / "audit.json")
    payload = json.loads(json_path.read_text())

    assert written["metadata"] == tmp_path / "metadata.json"
    assert (tmp_path / "replay_results.csv").exists()
    assert payload["metadata"] == {"milestone": 41}
    assert "oos_comparison" in payload["tables"]
    with pytest.raises(FileExistsError, match="Refusing to overwrite"):
        export_candidate_rule_audit_bundle_to_csv(bundle, tmp_path)
    with pytest.raises(FileExistsError, match="already exists"):
        export_candidate_rule_audit_bundle_to_json(bundle, json_path)


def test_candidate_rule_audit_bundle_validates_inputs() -> None:
    with pytest.raises(TypeError, match="bundle must be a dict"):
        validate_candidate_rule_audit_bundle("not-a-bundle")
    with pytest.raises(TypeError, match="must be a pandas DataFrame"):
        build_candidate_rule_audit_bundle(replay_results={"bad": "table"})  # type: ignore[arg-type]
