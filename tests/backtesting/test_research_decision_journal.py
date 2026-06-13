from __future__ import annotations

import json
from pathlib import Path

import pytest

from spy_edge_research.backtesting import (
    build_research_decision_journal,
    create_research_decision_record,
    read_research_decision_journal,
    summarize_research_decision_journal,
    validate_research_decision_record,
    write_research_decision_journal,
)


def decision_record(decision_id: str = "decision_001") -> dict[str, object]:
    return create_research_decision_record(
        decision_id=decision_id,
        subject_id="rule_a",
        subject_type="candidate_rule_object",
        decision="continue_study",
        rationale="OOS diagnostics remain mixed and need more review.",
        evidence_refs=["robustness_report_001"],
        reviewer="unit",
        created_at_utc="2026-06-13T12:00:00+00:00",
        caveats=["small_sample"],
        metadata={"milestone": 42},
    )


def test_create_research_decision_record_adds_required_caveat() -> None:
    record = decision_record()

    assert record["decision"] == "continue_study"
    assert record["subject_id"] == "rule_a"
    assert "research_decision_is_not_deployment_approval" in record["caveats"]
    assert "small_sample" in record["caveats"]


def test_decision_journal_validates_records_and_decisions() -> None:
    record = decision_record()

    with pytest.raises(KeyError, match="required fields"):
        validate_research_decision_record(
            {key: value for key, value in record.items() if key != "rationale"}
        )

    bad_decision = record.copy()
    bad_decision["decision"] = "approved"
    with pytest.raises(ValueError, match="decision"):
        validate_research_decision_record(bad_decision)

    bad_refs = record.copy()
    bad_refs["evidence_refs"] = "report"
    with pytest.raises(TypeError, match="evidence_refs"):
        validate_research_decision_record(bad_refs)


def test_build_and_summarize_research_decision_journal() -> None:
    first = decision_record("decision_b")
    second = decision_record("decision_a")
    second["decision"] = "needs_more_data"
    journal = build_research_decision_journal([first, second])

    summary = summarize_research_decision_journal(journal)

    assert journal["decision_id"].tolist() == ["decision_a", "decision_b"]
    assert summary["decision_count"].sum() == 2
    assert set(summary["summary_caveat"]) == {"journal_decisions_are_research_dispositions"}

    with pytest.raises(ValueError, match="duplicate"):
        build_research_decision_journal([decision_record("same"), decision_record("same")])


def test_research_decision_journal_json_round_trip(tmp_path: Path) -> None:
    journal = build_research_decision_journal([decision_record()])
    output_path = tmp_path / "decision_journal.json"

    written = write_research_decision_journal(journal, output_path, metadata={"milestone": 42})
    payload = json.loads(output_path.read_text())
    loaded = read_research_decision_journal(output_path)

    assert written == output_path
    assert payload["metadata"] == {"milestone": 42}
    assert loaded["decision_id"].tolist() == ["decision_001"]
    with pytest.raises(FileExistsError, match="already exists"):
        write_research_decision_journal(journal, output_path)
