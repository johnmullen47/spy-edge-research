from __future__ import annotations

from pathlib import Path

from spy_edge_research.backtesting import (
    build_artifact_integrity_report,
    build_research_package_manifest,
    check_expected_artifacts,
    check_manifest_artifact_paths,
    check_manifest_required_metadata,
    create_research_package_manifest_record,
    summarize_artifact_integrity,
)


def test_artifact_integrity_checks_paths_metadata_and_expected_artifacts(
    tmp_path: Path,
) -> None:
    present = tmp_path / "risk.csv"
    present.write_text("x\n1\n", encoding="utf-8")
    manifest = build_research_package_manifest(
        [
            create_research_package_manifest_record(
                package_id="pkg_a",
                artifact_name="risk",
                artifact_path="risk.csv",
                artifact_type="csv",
            ),
            create_research_package_manifest_record(
                package_id="pkg_a",
                artifact_name="traceability",
                artifact_path="traceability.csv",
                artifact_type="csv",
            ),
        ],
        metadata={"package_id": "pkg_a"},
    )

    paths = check_manifest_artifact_paths(manifest, base_dir=tmp_path)
    metadata = check_manifest_required_metadata(manifest, ["package_id", "reviewer"])
    expected = check_expected_artifacts(manifest, ["risk", "governance"])

    assert paths["path_status"].tolist() == ["ok", "missing_required"]
    assert metadata.set_index("metadata_key").loc["reviewer", "metadata_status"] == "missing"
    assert expected.set_index("artifact_name").loc["governance", "artifact_status"] == "missing"
    assert "deployment" not in " ".join(paths["integrity_caveat"].tolist())


def test_build_artifact_integrity_report_is_deterministic(tmp_path: Path) -> None:
    (tmp_path / "manifest.json").write_text("{}", encoding="utf-8")
    manifest = build_research_package_manifest(
        [
            create_research_package_manifest_record(
                package_id="pkg_a",
                artifact_name="manifest",
                artifact_path="manifest.json",
                artifact_type="json",
            )
        ],
        metadata={"package_id": "pkg_a", "milestone": "54"},
    )

    report = build_artifact_integrity_report(
        manifest,
        expected_artifact_names=["manifest"],
        required_metadata_keys=["milestone"],
        base_dir=tmp_path,
    )
    summary = summarize_artifact_integrity(report)

    assert list(report) == [
        "artifact_path_checks",
        "expected_artifacts",
        "required_metadata",
        "artifact_integrity_summary",
    ]
    assert summary["issue_count"].sum() == 0
    assert report["artifact_integrity_summary"].equals(summary)
