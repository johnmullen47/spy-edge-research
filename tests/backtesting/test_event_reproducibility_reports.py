from __future__ import annotations

import ast
import json
from pathlib import Path

import pandas as pd
import pytest

from spy_edge_research.backtesting import (
    build_and_export_reproducibility_report,
    build_artifact_manifest,
    build_audit_index,
    build_reproducibility_checklist,
    build_reproducibility_report_bundle,
    build_run_registry,
    create_artifact_record,
    create_audit_record,
    create_reproducibility_check,
    create_reproducibility_report_metadata,
    create_run_record,
    export_reproducibility_report_bundle_to_csv,
    export_reproducibility_report_bundle_to_json,
    summarize_reproducibility_report_bundle,
    validate_reproducibility_report_bundle,
)


def sample_checklist() -> dict[str, object]:
    return build_reproducibility_checklist(
        [
            create_reproducibility_check(
                check_name="metadata.dataset",
                passed=True,
                message="dataset present",
            ),
            create_reproducibility_check(
                check_name="file.audit_summary",
                passed=False,
                severity="warning",
                message="audit summary missing",
            ),
        ],
        metadata={"package_name": "sample_package"},
    )


def artifact_record(name: str = "event_study_results") -> dict[str, object]:
    return create_artifact_record(
        name=name,
        path=f"exports/{name}.csv",
        artifact_type="csv_table",
        row_count=3,
        column_count=4,
    )


def sample_registry() -> dict[str, object]:
    manifest = build_artifact_manifest(
        [artifact_record("z_table"), artifact_record("a_table")],
        metadata={"run_id": "run_a", "workflow_name": "event_research_workflow"},
    )
    return build_run_registry(
        [
            create_run_record(
                run_id="run_b",
                manifest_path="runs/run_b/manifest.json",
                metadata={"dataset": "feb"},
            ),
            create_run_record(
                run_id="run_a",
                manifest_path="runs/run_a/manifest.json",
                manifest=manifest,
                metadata=manifest["metadata"],
            ),
        ],
        metadata={"registry_name": "sample"},
    )


def sample_audit_index() -> dict[str, object]:
    return build_audit_index(
        [
            create_audit_record(
                audit_id="audit_b",
                audit_dir="audits/audit_b",
                metadata_path="audits/audit_b/metadata.json",
                table_paths={
                    "run_summary": "audits/audit_b/run_summary.csv",
                    "artifact_summary": "audits/audit_b/artifact_summary.csv",
                },
            ),
            create_audit_record(
                audit_id="audit_a",
                audit_dir="audits/audit_a",
                metadata_path="audits/audit_a/metadata.json",
                table_paths={"run_summary": "audits/audit_a/run_summary.csv"},
            ),
        ],
        metadata={"index_name": "sample"},
    )


def collect_keys(value: object) -> set[str]:
    keys: set[str] = set()
    if isinstance(value, dict):
        for key, nested in value.items():
            keys.add(str(key))
            keys.update(collect_keys(nested))
    elif isinstance(value, list):
        for nested in value:
            keys.update(collect_keys(nested))
    elif isinstance(value, pd.DataFrame):
        keys.update(str(column) for column in value.columns)
    return keys


def test_create_reproducibility_report_metadata_includes_created_at_project_and_milestone() -> None:
    metadata = create_reproducibility_report_metadata()

    assert metadata["created_at_utc"].endswith("+00:00")
    assert metadata["project_name"] == "SPY Directional Edge Research"
    assert metadata["milestone"] == "22"


def test_create_reproducibility_report_metadata_includes_optional_package_name_and_notes() -> None:
    metadata = create_reproducibility_report_metadata(
        package_name="january_research_package",
        notes="monthly reproducibility package",
    )

    assert metadata["package_name"] == "january_research_package"
    assert metadata["notes"] == "monthly reproducibility package"


def test_create_reproducibility_report_metadata_excludes_forbidden_fields() -> None:
    metadata = create_reproducibility_report_metadata()

    forbidden = {
        "best_audit",
        "best_run",
        "best_event",
        "selected_event",
        "rank",
        "score",
        "confidence",
        "edge",
    }
    assert forbidden.isdisjoint(metadata)


def test_build_reproducibility_report_bundle_validates_checklist_input() -> None:
    with pytest.raises(TypeError, match="checklist must be a dict"):
        build_reproducibility_report_bundle(checklist=["not", "a", "checklist"])  # type: ignore[arg-type]


def test_build_reproducibility_report_bundle_includes_requested_checklist_summary() -> None:
    bundle = build_reproducibility_report_bundle(
        checklist=sample_checklist(),
        include_checklist_status=False,
        include_registry_summary=False,
        include_audit_index_summary=False,
    )

    assert list(bundle["tables"]) == ["checklist_summary"]
    assert bundle["tables"]["checklist_summary"]["check_name"].tolist() == [
        "file.audit_summary",
        "metadata.dataset",
    ]


def test_build_reproducibility_report_bundle_includes_requested_checklist_status() -> None:
    bundle = build_reproducibility_report_bundle(
        checklist=sample_checklist(),
        include_checklist_summary=False,
        include_registry_summary=False,
        include_audit_index_summary=False,
    )

    assert list(bundle["tables"]) == ["checklist_status"]
    assert bundle["tables"]["checklist_status"].iloc[0].to_dict() == {
        "check_count": 2,
        "passed_count": 1,
        "failed_count": 1,
        "warning_count": 1,
        "error_count": 0,
        "all_passed": False,
    }


def test_build_reproducibility_report_bundle_includes_requested_registry_summary() -> None:
    bundle = build_reproducibility_report_bundle(
        registry=sample_registry(),
        include_checklist_summary=False,
        include_checklist_status=False,
        include_audit_index_summary=False,
    )

    assert list(bundle["tables"]) == ["registry_audit_summary"]
    assert bundle["tables"]["registry_audit_summary"]["run_id"].tolist() == [
        "run_a",
        "run_b",
    ]


def test_build_reproducibility_report_bundle_includes_requested_audit_index_summary() -> None:
    bundle = build_reproducibility_report_bundle(
        audit_index=sample_audit_index(),
        include_checklist_summary=False,
        include_checklist_status=False,
        include_registry_summary=False,
    )

    assert list(bundle["tables"]) == ["audit_index_summary"]
    assert bundle["tables"]["audit_index_summary"]["audit_id"].tolist() == [
        "audit_a",
        "audit_b",
    ]


def test_build_reproducibility_report_bundle_can_omit_optional_tables() -> None:
    bundle = build_reproducibility_report_bundle(
        checklist=sample_checklist(),
        registry=sample_registry(),
        audit_index=sample_audit_index(),
        include_checklist_summary=False,
        include_checklist_status=False,
        include_registry_summary=False,
        include_audit_index_summary=False,
    )

    assert bundle["tables"] == {}
    assert bundle["metadata"]["project_name"] == "SPY Directional Edge Research"


def test_build_reproducibility_report_bundle_does_not_mutate_inputs() -> None:
    checklist = sample_checklist()
    registry = sample_registry()
    audit_index = sample_audit_index()
    original_checklist = json.loads(json.dumps(checklist))
    original_registry = json.loads(json.dumps(registry))
    original_audit_index = json.loads(json.dumps(audit_index))

    bundle = build_reproducibility_report_bundle(
        checklist=checklist,
        registry=registry,
        audit_index=audit_index,
    )
    bundle["tables"]["checklist_summary"].loc[0, "check_name"] = "changed"
    bundle["tables"]["registry_audit_summary"].loc[0, "run_id"] = "changed"
    bundle["tables"]["audit_index_summary"].loc[0, "audit_id"] = "changed"

    assert checklist == original_checklist
    assert registry == original_registry
    assert audit_index == original_audit_index


def test_validate_reproducibility_report_bundle_accepts_valid_bundles() -> None:
    bundle = build_reproducibility_report_bundle(checklist=sample_checklist())

    assert validate_reproducibility_report_bundle(bundle) is bundle


def test_validate_reproducibility_report_bundle_raises_on_non_dict_input() -> None:
    with pytest.raises(TypeError, match="bundle must be a dict"):
        validate_reproducibility_report_bundle(["not", "a", "dict"])


def test_validate_reproducibility_report_bundle_raises_when_metadata_is_missing() -> None:
    with pytest.raises(KeyError, match="metadata"):
        validate_reproducibility_report_bundle({"tables": {}})


def test_validate_reproducibility_report_bundle_raises_when_tables_is_missing() -> None:
    with pytest.raises(KeyError, match="tables"):
        validate_reproducibility_report_bundle({"metadata": {}})


def test_validate_reproducibility_report_bundle_raises_when_table_is_not_dataframe() -> None:
    with pytest.raises(TypeError, match="must be a pandas DataFrame"):
        validate_reproducibility_report_bundle({"metadata": {}, "tables": {"summary": []}})


def test_summarize_reproducibility_report_bundle_returns_table_level_structure() -> None:
    bundle = build_reproducibility_report_bundle(
        checklist=sample_checklist(),
        registry=sample_registry(),
    )

    summary = summarize_reproducibility_report_bundle(bundle)

    assert summary.columns.tolist() == [
        "table_name",
        "row_count",
        "column_count",
        "columns",
    ]
    assert set(summary["table_name"]) == {
        "checklist_summary",
        "checklist_status",
        "registry_audit_summary",
    }


def test_summarize_reproducibility_report_bundle_sorts_by_table_name() -> None:
    bundle = {
        "metadata": {},
        "tables": {
            "z_table": pd.DataFrame({"z": [1]}),
            "a_table": pd.DataFrame({"a": [1]}),
        },
    }

    summary = summarize_reproducibility_report_bundle(bundle)

    assert summary["table_name"].tolist() == ["a_table", "z_table"]


def test_export_reproducibility_report_bundle_to_csv_writes_expected_files_and_metadata(
    tmp_path: Path,
) -> None:
    bundle = build_reproducibility_report_bundle(
        checklist=sample_checklist(),
        registry=sample_registry(),
        audit_index=sample_audit_index(),
        metadata=create_reproducibility_report_metadata(package_name="sample"),
    )

    written = export_reproducibility_report_bundle_to_csv(bundle, tmp_path)
    metadata = json.loads((tmp_path / "metadata.json").read_text())

    assert set(written) == {
        "checklist_summary",
        "checklist_status",
        "registry_audit_summary",
        "audit_index_summary",
        "metadata",
    }
    assert (tmp_path / "checklist_summary.csv").exists()
    assert (tmp_path / "checklist_status.csv").exists()
    assert (tmp_path / "registry_audit_summary.csv").exists()
    assert (tmp_path / "audit_index_summary.csv").exists()
    assert metadata["package_name"] == "sample"


def test_export_reproducibility_report_bundle_to_csv_respects_overwrite_false(
    tmp_path: Path,
) -> None:
    bundle = build_reproducibility_report_bundle(checklist=sample_checklist())
    export_reproducibility_report_bundle_to_csv(bundle, tmp_path)

    with pytest.raises(FileExistsError, match="Refusing to overwrite"):
        export_reproducibility_report_bundle_to_csv(bundle, tmp_path)


def test_export_reproducibility_report_bundle_to_json_writes_metadata_and_records(
    tmp_path: Path,
) -> None:
    bundle = build_reproducibility_report_bundle(
        checklist=sample_checklist(),
        metadata={"milestone": "22"},
    )
    output_path = tmp_path / "reproducibility_report.json"

    written = export_reproducibility_report_bundle_to_json(bundle, output_path)
    payload = json.loads(output_path.read_text())

    assert written == output_path
    assert payload["metadata"]["milestone"] == "22"
    assert set(payload["tables"]) == {"checklist_summary", "checklist_status"}
    assert payload["tables"]["checklist_status"][0]["check_count"] == 2


def test_export_reproducibility_report_bundle_to_json_respects_overwrite_false(
    tmp_path: Path,
) -> None:
    bundle = build_reproducibility_report_bundle(checklist=sample_checklist())
    output_path = tmp_path / "reproducibility_report.json"
    export_reproducibility_report_bundle_to_json(bundle, output_path)

    with pytest.raises(FileExistsError, match="already exists"):
        export_reproducibility_report_bundle_to_json(bundle, output_path)


def test_build_and_export_reproducibility_report_returns_bundle_paths_and_summary(
    tmp_path: Path,
) -> None:
    result = build_and_export_reproducibility_report(
        checklist=sample_checklist(),
        registry=sample_registry(),
        audit_index=sample_audit_index(),
        output_dir=tmp_path,
        metadata=create_reproducibility_report_metadata(),
    )

    assert set(result) == {"report_bundle", "written_paths", "report_summary"}
    assert (
        validate_reproducibility_report_bundle(result["report_bundle"])
        is result["report_bundle"]
    )
    assert (tmp_path / "checklist_summary.csv").exists()
    assert result["report_summary"]["table_name"].tolist() == [
        "audit_index_summary",
        "checklist_status",
        "checklist_summary",
        "registry_audit_summary",
    ]


def test_build_and_export_reproducibility_report_respects_overwrite_false(
    tmp_path: Path,
) -> None:
    checklist = sample_checklist()
    build_and_export_reproducibility_report(checklist=checklist, output_dir=tmp_path)

    with pytest.raises(FileExistsError, match="Refusing to overwrite"):
        build_and_export_reproducibility_report(checklist=checklist, output_dir=tmp_path)


def test_reproducibility_report_helpers_do_not_create_buy_sell_entry_or_exit_columns() -> None:
    bundle = build_reproducibility_report_bundle(
        checklist=sample_checklist(),
        registry=sample_registry(),
        audit_index=sample_audit_index(),
    )
    summary = summarize_reproducibility_report_bundle(bundle)

    forbidden = ("buy", "sell", "entry", "exit")
    for table in [summary, *bundle["tables"].values()]:
        assert not any(word in column for column in table.columns for word in forbidden)


def test_reproducibility_report_helpers_do_not_create_selection_or_scoring_fields() -> None:
    bundle = build_reproducibility_report_bundle(
        checklist=sample_checklist(),
        registry=sample_registry(),
        audit_index=sample_audit_index(),
        metadata=create_reproducibility_report_metadata(),
    )
    summary = summarize_reproducibility_report_bundle(bundle)
    keys = collect_keys(bundle)
    keys.update(summary.columns)

    forbidden = {
        "confidence",
        "score",
        "rank",
        "edge",
        "best_audit",
        "best_run",
        "best_event",
        "selected_event",
    }
    assert forbidden.isdisjoint(keys)


def test_reproducibility_report_helpers_do_not_read_audit_csv_artifacts_or_manifests(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    artifact_path = tmp_path / "exports" / "event_study_results.csv"
    manifest_path = tmp_path / "runs" / "run_a" / "manifest.json"
    audit_table_path = tmp_path / "audits" / "audit_a" / "run_summary.csv"
    manifest = build_artifact_manifest(
        [
            create_artifact_record(
                name="event_study_results",
                path=artifact_path,
                artifact_type="csv_table",
                metadata={
                    "outcome": "not read",
                    "forward_return_5m": 123,
                },
            )
        ],
        metadata={"run_id": "run_a"},
    )
    registry = build_run_registry(
        [
            create_run_record(
                run_id="run_a",
                manifest_path=manifest_path,
                manifest=manifest,
                metadata=manifest["metadata"],
            )
        ]
    )
    audit_index = build_audit_index(
        [
            create_audit_record(
                audit_id="audit_a",
                audit_dir=tmp_path / "audits" / "audit_a",
                metadata_path=tmp_path / "audits" / "audit_a" / "metadata.json",
                table_paths={"run_summary": audit_table_path},
                metadata={"outcome": "not read"},
            )
        ]
    )

    def fail_read_text(self: Path, *args: object, **kwargs: object) -> str:
        raise AssertionError(f"read_text should not be called for {self}")

    def fail_read_csv(*args: object, **kwargs: object) -> pd.DataFrame:
        raise AssertionError("read_csv should not be called")

    monkeypatch.setattr(Path, "read_text", fail_read_text)
    monkeypatch.setattr(pd, "read_csv", fail_read_csv)

    bundle = build_reproducibility_report_bundle(
        checklist=sample_checklist(),
        registry=registry,
        audit_index=audit_index,
    )

    assert not artifact_path.exists()
    assert not manifest_path.exists()
    assert not audit_table_path.exists()
    assert bundle["tables"]["registry_audit_summary"]["manifest_path"].tolist() == [
        str(manifest_path)
    ]


def test_reproducibility_report_helpers_do_not_import_or_call_forbidden_trading_modules() -> None:
    module_path = (
        Path(__file__).parents[2]
        / "src"
        / "spy_edge_research"
        / "backtesting"
        / "event_reproducibility_reports.py"
    )
    tree = ast.parse(module_path.read_text(encoding="utf-8"))
    imported_modules: set[str] = set()
    called_names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            imported_modules.add(node.module)
        elif isinstance(node, ast.Call):
            function = node.func
            if isinstance(function, ast.Name):
                called_names.add(function.id.lower())
            elif isinstance(function, ast.Attribute):
                called_names.add(function.attr.lower())

    forbidden_terms = ("execution", "broker", "alert", "optimizer", "signal", "strategy")
    assert not any(
        term in module_name.lower()
        for module_name in imported_modules
        for term in forbidden_terms
    )
    assert not any(
        term in call_name
        for call_name in called_names
        for term in forbidden_terms
    )
