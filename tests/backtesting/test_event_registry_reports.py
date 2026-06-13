from __future__ import annotations

import ast
import json
from pathlib import Path

import pandas as pd
import pytest

from spy_edge_research.backtesting import (
    build_and_export_registry_audit,
    build_artifact_manifest,
    build_registry_audit_bundle,
    build_run_registry,
    create_artifact_record,
    create_registry_audit_metadata,
    create_run_record,
    export_registry_audit_bundle_to_csv,
    export_registry_audit_bundle_to_json,
    summarize_registry_audit_bundle,
    validate_registry_audit_bundle,
)


def artifact_record(name: str = "event_study_results") -> dict[str, object]:
    return create_artifact_record(
        name=name,
        path=f"exports/{name}.csv",
        artifact_type="csv_table",
        description=f"{name} table",
        row_count=3,
        column_count=4,
    )


def artifact_manifest(
    *,
    run_id: str = "run_a",
    artifact_names: list[str] | None = None,
    metadata: dict[str, object] | None = None,
) -> dict[str, object]:
    manifest_metadata: dict[str, object] = {
        "run_id": run_id,
        "workflow_name": "event_research_workflow",
    }
    if metadata is not None:
        manifest_metadata.update(metadata)
    return build_artifact_manifest(
        [artifact_record(name) for name in (artifact_names or ["event_study_results"])],
        metadata=manifest_metadata,
    )


def run_record(
    run_id: str = "run_a",
    *,
    artifact_names: list[str] | None = None,
    metadata: dict[str, object] | None = None,
) -> dict[str, object]:
    manifest = artifact_manifest(
        run_id=run_id,
        artifact_names=artifact_names,
        metadata=metadata,
    )
    return create_run_record(
        run_id=run_id,
        manifest_path=f"runs/{run_id}/manifest.json",
        manifest=manifest,
        metadata=manifest["metadata"],
    )


def sample_registry() -> dict[str, object]:
    return build_run_registry(
        [
            run_record(
                "run_b",
                artifact_names=["z_table", "a_table"],
                metadata={"dataset": "feb"},
            ),
            run_record("run_a", metadata={"dataset": "jan"}),
        ]
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


def test_create_registry_audit_metadata_includes_created_at_project_name_and_milestone() -> None:
    metadata = create_registry_audit_metadata()

    assert metadata["created_at_utc"].endswith("+00:00")
    assert metadata["project_name"] == "SPY Directional Edge Research"
    assert metadata["milestone"] == "18"


def test_create_registry_audit_metadata_includes_optional_registry_name_and_notes() -> None:
    metadata = create_registry_audit_metadata(
        registry_name="january_registry",
        notes="monthly audit",
    )

    assert metadata["registry_name"] == "january_registry"
    assert metadata["notes"] == "monthly audit"


def test_create_registry_audit_metadata_excludes_forbidden_selection_fields() -> None:
    metadata = create_registry_audit_metadata()

    forbidden = {
        "best_run",
        "best_event",
        "selected_event",
        "rank",
        "score",
        "confidence",
        "edge",
    }
    assert forbidden.isdisjoint(metadata)


def test_build_registry_audit_bundle_validates_registry_input() -> None:
    with pytest.raises(TypeError, match="registry must be a dict"):
        build_registry_audit_bundle(["not", "a", "registry"])  # type: ignore[arg-type]


def test_build_registry_audit_bundle_includes_requested_run_summary_table() -> None:
    bundle = build_registry_audit_bundle(
        sample_registry(),
        include_artifact_summary=False,
        include_metadata_consistency=False,
    )

    assert list(bundle["tables"]) == ["run_summary"]
    assert bundle["tables"]["run_summary"]["run_id"].tolist() == ["run_a", "run_b"]


def test_build_registry_audit_bundle_includes_requested_artifact_summary_table() -> None:
    bundle = build_registry_audit_bundle(
        sample_registry(),
        include_run_summary=False,
        include_metadata_consistency=False,
    )

    assert list(bundle["tables"]) == ["artifact_summary"]
    assert bundle["tables"]["artifact_summary"][["run_id", "artifact_name"]].values.tolist() == [
        ["run_a", "event_study_results"],
        ["run_b", "a_table"],
        ["run_b", "z_table"],
    ]


def test_build_registry_audit_bundle_includes_requested_metadata_consistency_table() -> None:
    bundle = build_registry_audit_bundle(
        sample_registry(),
        required_metadata_keys=["dataset", "workflow_name"],
        include_run_summary=False,
        include_artifact_summary=False,
    )

    assert list(bundle["tables"]) == ["metadata_consistency"]
    assert bundle["tables"]["metadata_consistency"]["metadata_key"].tolist() == [
        "dataset",
        "workflow_name",
        "dataset",
        "workflow_name",
    ]


def test_build_registry_audit_bundle_can_omit_optional_tables() -> None:
    bundle = build_registry_audit_bundle(
        sample_registry(),
        include_run_summary=False,
        include_artifact_summary=False,
        include_metadata_consistency=False,
    )

    assert bundle["tables"] == {}
    assert bundle["metadata"]["project_name"] == "SPY Directional Edge Research"


def test_build_registry_audit_bundle_does_not_mutate_input_registry() -> None:
    registry = sample_registry()
    original = json.loads(json.dumps(registry))

    bundle = build_registry_audit_bundle(registry)
    bundle["tables"]["run_summary"].loc[0, "run_id"] = "changed"

    assert registry == original


def test_validate_registry_audit_bundle_accepts_valid_bundles() -> None:
    bundle = build_registry_audit_bundle(sample_registry())

    assert validate_registry_audit_bundle(bundle) is bundle


def test_validate_registry_audit_bundle_raises_on_non_dict_input() -> None:
    with pytest.raises(TypeError, match="bundle must be a dict"):
        validate_registry_audit_bundle(["not", "a", "dict"])


def test_validate_registry_audit_bundle_raises_when_metadata_is_missing() -> None:
    with pytest.raises(KeyError, match="metadata"):
        validate_registry_audit_bundle({"tables": {}})


def test_validate_registry_audit_bundle_raises_when_tables_is_missing() -> None:
    with pytest.raises(KeyError, match="tables"):
        validate_registry_audit_bundle({"metadata": {}})


def test_validate_registry_audit_bundle_raises_when_table_is_not_dataframe() -> None:
    with pytest.raises(TypeError, match="must be a pandas DataFrame"):
        validate_registry_audit_bundle({"metadata": {}, "tables": {"run_summary": []}})


def test_summarize_registry_audit_bundle_returns_table_level_structure() -> None:
    bundle = build_registry_audit_bundle(sample_registry())

    summary = summarize_registry_audit_bundle(bundle)

    assert summary.columns.tolist() == [
        "table_name",
        "row_count",
        "column_count",
        "columns",
    ]
    assert set(summary["table_name"]) == {
        "run_summary",
        "artifact_summary",
        "metadata_consistency",
    }
    assert summary.loc[summary["table_name"] == "run_summary", "row_count"].item() == 2


def test_summarize_registry_audit_bundle_sorts_by_table_name() -> None:
    bundle = {
        "metadata": {},
        "tables": {
            "z_table": pd.DataFrame({"z": [1]}),
            "a_table": pd.DataFrame({"a": [1]}),
        },
    }

    summary = summarize_registry_audit_bundle(bundle)

    assert summary["table_name"].tolist() == ["a_table", "z_table"]


def test_export_registry_audit_bundle_to_csv_writes_expected_files_and_metadata(
    tmp_path: Path,
) -> None:
    bundle = build_registry_audit_bundle(
        sample_registry(),
        metadata=create_registry_audit_metadata(registry_name="sample"),
    )

    written = export_registry_audit_bundle_to_csv(bundle, tmp_path)
    metadata = json.loads((tmp_path / "metadata.json").read_text())

    assert set(written) == {
        "run_summary",
        "artifact_summary",
        "metadata_consistency",
        "metadata",
    }
    assert (tmp_path / "run_summary.csv").exists()
    assert (tmp_path / "artifact_summary.csv").exists()
    assert (tmp_path / "metadata_consistency.csv").exists()
    assert metadata["registry_name"] == "sample"


def test_export_registry_audit_bundle_to_csv_respects_overwrite_false(
    tmp_path: Path,
) -> None:
    bundle = build_registry_audit_bundle(sample_registry())
    export_registry_audit_bundle_to_csv(bundle, tmp_path)

    with pytest.raises(FileExistsError, match="Refusing to overwrite"):
        export_registry_audit_bundle_to_csv(bundle, tmp_path)


def test_export_registry_audit_bundle_to_json_writes_metadata_and_records(
    tmp_path: Path,
) -> None:
    bundle = build_registry_audit_bundle(
        sample_registry(),
        metadata={"milestone": "18"},
    )
    output_path = tmp_path / "registry_audit.json"

    written = export_registry_audit_bundle_to_json(bundle, output_path)
    payload = json.loads(output_path.read_text())

    assert written == output_path
    assert payload["metadata"]["milestone"] == "18"
    assert set(payload["tables"]) == {
        "run_summary",
        "artifact_summary",
        "metadata_consistency",
    }
    assert payload["tables"]["run_summary"][0]["run_id"] == "run_a"


def test_export_registry_audit_bundle_to_json_respects_overwrite_false(
    tmp_path: Path,
) -> None:
    bundle = build_registry_audit_bundle(sample_registry())
    output_path = tmp_path / "registry_audit.json"
    export_registry_audit_bundle_to_json(bundle, output_path)

    with pytest.raises(FileExistsError, match="already exists"):
        export_registry_audit_bundle_to_json(bundle, output_path)


def test_build_and_export_registry_audit_returns_bundle_paths_and_summary(
    tmp_path: Path,
) -> None:
    result = build_and_export_registry_audit(
        sample_registry(),
        tmp_path,
        metadata=create_registry_audit_metadata(),
    )

    assert set(result) == {"audit_bundle", "written_paths", "audit_summary"}
    assert validate_registry_audit_bundle(result["audit_bundle"]) is result["audit_bundle"]
    assert (tmp_path / "run_summary.csv").exists()
    assert result["audit_summary"]["table_name"].tolist() == [
        "artifact_summary",
        "metadata_consistency",
        "run_summary",
    ]


def test_build_and_export_registry_audit_respects_overwrite_false(tmp_path: Path) -> None:
    registry = sample_registry()
    build_and_export_registry_audit(registry, tmp_path)

    with pytest.raises(FileExistsError, match="Refusing to overwrite"):
        build_and_export_registry_audit(registry, tmp_path)


def test_registry_audit_helpers_do_not_create_buy_sell_entry_or_exit_columns() -> None:
    bundle = build_registry_audit_bundle(sample_registry())
    summary = summarize_registry_audit_bundle(bundle)

    forbidden = ("buy", "sell", "entry", "exit")
    for table in [summary, *bundle["tables"].values()]:
        assert not any(word in column for column in table.columns for word in forbidden)


def test_registry_audit_helpers_do_not_create_selection_or_scoring_fields() -> None:
    bundle = build_registry_audit_bundle(
        sample_registry(),
        metadata=create_registry_audit_metadata(),
    )
    summary = summarize_registry_audit_bundle(bundle)
    keys = collect_keys(bundle)
    keys.update(summary.columns)

    forbidden = {
        "confidence",
        "score",
        "rank",
        "edge",
        "best_run",
        "best_event",
        "selected_event",
    }
    assert forbidden.isdisjoint(keys)


def test_registry_audit_helpers_do_not_inspect_artifact_contents(
    tmp_path: Path,
) -> None:
    artifact_path = tmp_path / "exports" / "event_study_results.csv"
    manifest = build_artifact_manifest(
        [
            create_artifact_record(
                name="event_study_results",
                path=artifact_path,
                artifact_type="csv_table",
                row_count=1,
                column_count=1,
            )
        ],
        metadata={"run_id": "run_a"},
    )
    registry = build_run_registry(
        [
            create_run_record(
                run_id="run_a",
                manifest_path="runs/run_a/manifest.json",
                manifest=manifest,
                metadata=manifest["metadata"],
            )
        ]
    )

    bundle = build_registry_audit_bundle(registry)

    assert not artifact_path.exists()
    assert bundle["tables"]["artifact_summary"]["artifact_path"].tolist() == [
        str(artifact_path)
    ]


def test_registry_audit_helpers_do_not_import_forbidden_trading_modules() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    module_path = (
        repo_root
        / "src/spy_edge_research/backtesting/event_registry_reports.py"
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
