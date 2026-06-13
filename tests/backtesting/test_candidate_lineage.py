from __future__ import annotations

import json
from pathlib import Path

import pytest

from spy_edge_research.backtesting import (
    build_candidate_lineage_table,
    create_candidate_lineage_record,
    read_candidate_lineage_table,
    summarize_candidate_lineage,
    validate_candidate_lineage_record,
    write_candidate_lineage_table,
)


def lineage_record(lineage_id: str = "lineage_001") -> dict[str, object]:
    return create_candidate_lineage_record(
        lineage_id=lineage_id,
        action="merge_hypotheses",
        source_ids=["candidate_a", "candidate_b"],
        target_id="candidate_ab",
        rationale="Related condition family.",
        created_at_utc="2026-06-13T12:00:00+00:00",
        caveats=["manual_review"],
    )


def test_create_candidate_lineage_record_preserves_research_history() -> None:
    record = lineage_record()

    assert record["action"] == "merge_hypotheses"
    assert record["source_ids"] == ["candidate_a", "candidate_b"]
    assert "lineage_record_preserves_research_history" in record["caveats"]


def test_candidate_lineage_validation_and_summary() -> None:
    retire = create_candidate_lineage_record(
        lineage_id="lineage_002",
        action="retire_from_review",
        source_ids=["candidate_c"],
        rationale="Insufficient support.",
        created_at_utc="2026-06-13T12:00:00+00:00",
    )
    table = build_candidate_lineage_table([lineage_record(), retire])
    summary = summarize_candidate_lineage(table)

    assert table["lineage_id"].tolist() == ["lineage_001", "lineage_002"]
    assert summary["record_count"].sum() == 2
    assert set(summary["summary_caveat"]) == {"lineage_summary_is_research_history_only"}

    invalid = lineage_record()
    invalid["action"] = "approve"
    with pytest.raises(ValueError, match="action"):
        validate_candidate_lineage_record(invalid)


def test_candidate_lineage_json_round_trip(tmp_path: Path) -> None:
    table = build_candidate_lineage_table([lineage_record()])
    output_path = tmp_path / "lineage.json"

    written = write_candidate_lineage_table(table, output_path, metadata={"milestone": 51})
    payload = json.loads(output_path.read_text())
    loaded = read_candidate_lineage_table(output_path)

    assert written == output_path
    assert payload["metadata"] == {"milestone": 51}
    assert loaded["lineage_id"].tolist() == ["lineage_001"]
    with pytest.raises(FileExistsError, match="already exists"):
        write_candidate_lineage_table(table, output_path)
