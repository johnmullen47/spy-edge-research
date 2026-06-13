from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from spy_edge_research.backtesting import (
    build_research_governance_bundle,
    create_research_governance_metadata,
    export_research_governance_bundle_to_csv,
    export_research_governance_bundle_to_json,
    summarize_research_governance_bundle,
    validate_research_governance_bundle,
)


def test_governance_bundle_validates_and_summarizes_tables() -> None:
    metadata = create_research_governance_metadata(notes="review pass")
    bundle = build_research_governance_bundle(
        artifact_integrity_summary=pd.DataFrame(
            {"table_name": ["artifact_path_checks"], "issue_count": [1]}
        ),
        package_comparison_summary=pd.DataFrame(
            {"table_name": ["artifact_coverage"], "row_count": [2]}
        ),
        traceability_summary=pd.DataFrame(
            {"evidence_type": ["oos_results"], "missing_count": [1]}
        ),
        metadata=metadata,
    )
    summary = summarize_research_governance_bundle(bundle)

    assert validate_research_governance_bundle(bundle) == bundle
    assert bundle["metadata"]["governance_caveat"] == "research_governance_bundle_is_review_only"
    assert "governance_caveats" in bundle["tables"]
    assert summary["table_name"].tolist() == [
        "artifact_integrity_summary",
        "governance_caveats",
        "package_comparison_summary",
        "traceability_summary",
    ]


def test_governance_bundle_exports_csv_and_json(tmp_path: Path) -> None:
    bundle = build_research_governance_bundle(
        traceability_summary=pd.DataFrame(
            {"evidence_type": ["risk_report"], "missing_count": [0]}
        ),
        metadata=create_research_governance_metadata(milestone="57"),
    )
    csv_paths = export_research_governance_bundle_to_csv(bundle, tmp_path / "csv")
    json_path = export_research_governance_bundle_to_json(
        bundle,
        tmp_path / "governance.json",
    )

    assert csv_paths["traceability_summary"].exists()
    assert csv_paths["metadata"].exists()
    assert json_path.exists()
    with pytest.raises(FileExistsError, match="already exists|Refusing"):
        export_research_governance_bundle_to_csv(bundle, tmp_path / "csv")


def test_governance_bundle_rejects_duplicate_reserved_table_name() -> None:
    with pytest.raises(ValueError, match="duplicate governance table name"):
        build_research_governance_bundle(
            additional_tables={"governance_caveats": pd.DataFrame()}
        )
