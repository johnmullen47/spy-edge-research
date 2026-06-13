from __future__ import annotations

from pathlib import Path

import pytest

from spy_edge_research.backtesting import (
    build_research_package_manifest,
    create_research_package_manifest_record,
    read_research_package_manifest,
    summarize_research_package_manifest,
    validate_research_package_manifest,
    write_research_package_manifest,
)


def manifest_record(name: str = "risk_report") -> dict[str, object]:
    return create_research_package_manifest_record(
        package_id="pkg_a",
        artifact_name=name,
        artifact_path=f"{name}.json",
        artifact_type="json",
        description="Research artifact",
        required=True,
        metadata={"milestone": 52},
    )


def test_build_and_summarize_research_package_manifest() -> None:
    manifest = build_research_package_manifest(
        [manifest_record("risk"), manifest_record("journal")],
        metadata={"package_id": "pkg_a"},
    )
    summary = summarize_research_package_manifest(manifest)

    assert manifest["metadata"]["package_id"] == "pkg_a"
    assert manifest["metadata"]["manifest_caveat"] == (
        "research_package_manifest_is_not_deployment_bundle"
    )
    assert summary["artifact_count"].tolist() == [2]
    assert summary["summary_caveat"].tolist() == [
        "manifest_summary_is_research_inventory_only"
    ]


def test_research_package_manifest_json_round_trip(tmp_path: Path) -> None:
    manifest = build_research_package_manifest([manifest_record()])
    output_path = tmp_path / "manifest.json"

    written = write_research_package_manifest(manifest, output_path)
    loaded = read_research_package_manifest(output_path)

    assert written == output_path
    assert loaded["artifacts"][0]["artifact_name"] == "risk_report"
    with pytest.raises(FileExistsError, match="already exists"):
        write_research_package_manifest(manifest, output_path)


def test_research_package_manifest_validates_records() -> None:
    with pytest.raises(KeyError, match="required fields"):
        validate_research_package_manifest({"metadata": {}, "artifacts": [{}]})
    with pytest.raises(TypeError, match="required"):
        create_research_package_manifest_record(
            package_id="pkg",
            artifact_name="artifact",
            artifact_path="artifact.csv",
            artifact_type="csv",
            required="yes",  # type: ignore[arg-type]
        )
