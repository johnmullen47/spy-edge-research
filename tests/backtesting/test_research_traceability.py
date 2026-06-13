from __future__ import annotations

import pandas as pd

from spy_edge_research.backtesting import (
    build_research_package_manifest,
    build_research_traceability_matrix,
    create_research_package_manifest_record,
    summarize_research_traceability,
)


def test_traceability_matrix_links_evidence_and_surfaces_missing_items() -> None:
    manifest = build_research_package_manifest(
        [
            create_research_package_manifest_record(
                package_id="pkg_a",
                artifact_name="risk",
                artifact_path="risk.csv",
                artifact_type="csv",
                metadata={"candidate_id": "cand_a"},
            )
        ],
        metadata={"package_id": "pkg_a"},
    )
    matrix = build_research_traceability_matrix(
        rule_catalog=pd.DataFrame(
            {"candidate_id": ["cand_a", "cand_b"], "rule_object_id": ["rule_a", "rule_b"]}
        ),
        candidate_registry=pd.DataFrame({"candidate_id": ["cand_a"]}),
        oos_results=pd.DataFrame({"candidate_id": ["cand_a"]}),
        robustness_reports=pd.DataFrame({"candidate_id": ["cand_a"]}),
        risk_reports=pd.DataFrame({"candidate_id": ["cand_a"]}),
        decision_journal=pd.DataFrame({"subject_id": ["cand_a"]}),
        lineage_table=pd.DataFrame({"source_ids": [["cand_a"]], "target_id": [None]}),
        package_manifest=manifest,
    )

    cand_a = matrix.set_index("candidate_id").loc["cand_a"]
    cand_b = matrix.set_index("candidate_id").loc["cand_b"]

    assert cand_a["missing_evidence"] == []
    assert cand_a["traceability_caveat"] == "research_evidence_links_present"
    assert "candidate_record" in cand_b["missing_evidence"]
    assert cand_b["traceability_caveat"] == "missing_research_evidence_links"


def test_traceability_summary_counts_present_and_missing_evidence() -> None:
    matrix = build_research_traceability_matrix(
        candidate_ids=["cand_a", "cand_b"],
        decision_journal=pd.DataFrame({"subject_id": ["cand_a"]}),
    )
    summary = summarize_research_traceability(matrix)
    decision = summary.set_index("evidence_type").loc["decision_record"]
    rule_object = summary.set_index("evidence_type").loc["rule_object"]

    assert decision["present_count"] == 1
    assert decision["missing_count"] == 1
    assert rule_object["present_count"] == 0
    assert "approval" not in " ".join(summary["summary_caveat"].tolist())
