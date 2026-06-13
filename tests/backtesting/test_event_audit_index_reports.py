from __future__ import annotations

import ast
import json
from pathlib import Path

import pandas as pd
import pytest

from spy_edge_research.backtesting import (
    build_and_export_audit_index_report,
    build_audit_index,
    build_audit_index_comparison_bundle,
    build_audit_index_report_bundle,
    compare_audit_indexes_structure,
    create_audit_index_report_metadata,
    create_audit_record,
    export_audit_index_report_bundle_to_csv,
    export_audit_index_report_bundle_to_json,
    summarize_audit_index_report_bundle,
    validate_audit_index_report_bundle,
)


def audit_record(
    audit_id: str = "audit_a",
    *,
    table_paths: dict[str, str] | None = None,
) -> dict[str, object]:
    return create_audit_record(
        audit_id=audit_id,
        audit_dir=f"audits/{audit_id}",
        metadata_path=f"audits/{audit_id}/metadata.json",
        table_paths=table_paths or {"run_summary": f"audits/{audit_id}/run_summary.csv"},
        metadata={"registry_name": audit_id},
    )


def sample_audit_index() -> dict[str, object]:
    return build_audit_index(
        [
            audit_record(
                "audit_b",
                table_paths={
                    "run_summary": "audits/audit_b/run_summary.csv",
                    "artifact_summary": "audits/audit_b/artifact_summary.csv",
                },
            ),
            audit_record("audit_a"),
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


def test_create_audit_index_report_metadata_includes_created_at_project_and_milestone() -> None:
    metadata = create_audit_index_report_metadata()

    assert metadata["created_at_utc"].endswith("+00:00")
    assert metadata["project_name"] == "SPY Directional Edge Research"
    assert metadata["milestone"] == "20"


def test_create_audit_index_report_metadata_includes_optional_index_name_and_notes() -> None:
    metadata = create_audit_index_report_metadata(
        index_name="january_audit_index",
        notes="monthly comparison",
    )

    assert metadata["index_name"] == "january_audit_index"
    assert metadata["notes"] == "monthly comparison"


def test_create_audit_index_report_metadata_excludes_forbidden_selection_fields() -> None:
    metadata = create_audit_index_report_metadata()

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


def test_build_audit_index_report_bundle_validates_audit_index_input() -> None:
    with pytest.raises(TypeError, match="index must be a dict"):
        build_audit_index_report_bundle(["not", "an", "index"])  # type: ignore[arg-type]


def test_build_audit_index_report_bundle_includes_requested_audit_summary_table() -> None:
    bundle = build_audit_index_report_bundle(
        sample_audit_index(),
        include_audit_tables=False,
    )

    assert list(bundle["tables"]) == ["audit_summary"]
    assert bundle["tables"]["audit_summary"]["audit_id"].tolist() == [
        "audit_a",
        "audit_b",
    ]


def test_build_audit_index_report_bundle_includes_requested_audit_tables_table() -> None:
    bundle = build_audit_index_report_bundle(
        sample_audit_index(),
        include_audit_summary=False,
    )

    assert list(bundle["tables"]) == ["audit_tables"]
    assert bundle["tables"]["audit_tables"][["audit_id", "table_name"]].values.tolist() == [
        ["audit_a", "run_summary"],
        ["audit_b", "artifact_summary"],
        ["audit_b", "run_summary"],
    ]


def test_build_audit_index_report_bundle_can_omit_optional_tables() -> None:
    bundle = build_audit_index_report_bundle(
        sample_audit_index(),
        include_audit_summary=False,
        include_audit_tables=False,
    )

    assert bundle["tables"] == {}
    assert bundle["metadata"]["project_name"] == "SPY Directional Edge Research"


def test_build_audit_index_report_bundle_does_not_mutate_input_audit_index() -> None:
    audit_index = sample_audit_index()
    original = json.loads(json.dumps(audit_index))

    bundle = build_audit_index_report_bundle(audit_index)
    bundle["tables"]["audit_summary"].loc[0, "audit_id"] = "changed"

    assert audit_index == original


def test_validate_audit_index_report_bundle_accepts_valid_bundles() -> None:
    bundle = build_audit_index_report_bundle(sample_audit_index())

    assert validate_audit_index_report_bundle(bundle) is bundle


def test_validate_audit_index_report_bundle_raises_on_non_dict_input() -> None:
    with pytest.raises(TypeError, match="bundle must be a dict"):
        validate_audit_index_report_bundle(["not", "a", "dict"])


def test_validate_audit_index_report_bundle_raises_when_metadata_is_missing() -> None:
    with pytest.raises(KeyError, match="metadata"):
        validate_audit_index_report_bundle({"tables": {}})


def test_validate_audit_index_report_bundle_raises_when_tables_is_missing() -> None:
    with pytest.raises(KeyError, match="tables"):
        validate_audit_index_report_bundle({"metadata": {}})


def test_validate_audit_index_report_bundle_raises_when_table_is_not_dataframe() -> None:
    with pytest.raises(TypeError, match="must be a pandas DataFrame"):
        validate_audit_index_report_bundle({"metadata": {}, "tables": {"audit_summary": []}})


def test_summarize_audit_index_report_bundle_returns_table_level_structure() -> None:
    bundle = build_audit_index_report_bundle(sample_audit_index())

    summary = summarize_audit_index_report_bundle(bundle)

    assert summary.columns.tolist() == [
        "table_name",
        "row_count",
        "column_count",
        "columns",
    ]
    assert summary["table_name"].tolist() == ["audit_summary", "audit_tables"]
    assert summary.loc[summary["table_name"] == "audit_summary", "row_count"].item() == 2


def test_summarize_audit_index_report_bundle_sorts_by_table_name() -> None:
    bundle = {
        "metadata": {},
        "tables": {
            "z_table": pd.DataFrame({"z": [1]}),
            "a_table": pd.DataFrame({"a": [1]}),
        },
    }

    summary = summarize_audit_index_report_bundle(bundle)

    assert summary["table_name"].tolist() == ["a_table", "z_table"]


def test_compare_audit_indexes_structure_returns_deterministic_rows() -> None:
    left = sample_audit_index()
    right = build_audit_index(
        [
            audit_record(
                "audit_a",
                table_paths={
                    "run_summary": "audits/audit_a/run_summary.csv",
                    "metadata_consistency": "audits/audit_a/metadata_consistency.csv",
                },
            )
        ]
    )

    comparison = compare_audit_indexes_structure(left, right)

    assert comparison["comparison_key"].tolist() == [
        "audit_count",
        "audit_ids",
        "table_names",
        "table_path_count",
    ]
    assert comparison["matches"].tolist() == [False, False, False, False]


def test_compare_audit_indexes_structure_does_not_read_audit_table_contents(
    tmp_path: Path,
) -> None:
    missing_table = tmp_path / "missing_run_summary.csv"
    left = build_audit_index(
        [
            audit_record(
                "audit_a",
                table_paths={"run_summary": str(missing_table)},
            )
        ]
    )
    right = build_audit_index([audit_record("audit_a")])

    comparison = compare_audit_indexes_structure(left, right)

    assert not missing_table.exists()
    assert "table_path_count" in comparison["comparison_key"].tolist()


def test_compare_audit_indexes_structure_does_not_mutate_inputs() -> None:
    left = sample_audit_index()
    right = build_audit_index([audit_record("audit_a")])
    original_left = json.loads(json.dumps(left))
    original_right = json.loads(json.dumps(right))

    compare_audit_indexes_structure(left, right)

    assert left == original_left
    assert right == original_right


def test_build_audit_index_comparison_bundle_returns_comparison_summary() -> None:
    bundle = build_audit_index_comparison_bundle(
        sample_audit_index(),
        build_audit_index([audit_record("audit_a")]),
        left_name="baseline",
        right_name="candidate",
        metadata={"milestone": "20"},
    )

    assert list(bundle["tables"]) == ["comparison_summary"]
    assert bundle["metadata"]["left_name"] == "baseline"
    assert bundle["metadata"]["right_name"] == "candidate"
    assert bundle["tables"]["comparison_summary"]["comparison_key"].tolist() == [
        "audit_count",
        "audit_ids",
        "table_names",
        "table_path_count",
    ]


def test_export_audit_index_report_bundle_to_csv_writes_expected_files_and_metadata(
    tmp_path: Path,
) -> None:
    bundle = build_audit_index_report_bundle(
        sample_audit_index(),
        metadata=create_audit_index_report_metadata(index_name="sample"),
    )

    written = export_audit_index_report_bundle_to_csv(bundle, tmp_path)
    metadata = json.loads((tmp_path / "metadata.json").read_text())

    assert set(written) == {"audit_summary", "audit_tables", "metadata"}
    assert (tmp_path / "audit_summary.csv").exists()
    assert (tmp_path / "audit_tables.csv").exists()
    assert metadata["index_name"] == "sample"


def test_export_audit_index_report_bundle_to_csv_respects_overwrite_false(
    tmp_path: Path,
) -> None:
    bundle = build_audit_index_report_bundle(sample_audit_index())
    export_audit_index_report_bundle_to_csv(bundle, tmp_path)

    with pytest.raises(FileExistsError, match="Refusing to overwrite"):
        export_audit_index_report_bundle_to_csv(bundle, tmp_path)


def test_export_audit_index_report_bundle_to_json_writes_metadata_and_records(
    tmp_path: Path,
) -> None:
    bundle = build_audit_index_report_bundle(
        sample_audit_index(),
        metadata={"milestone": "20"},
    )
    output_path = tmp_path / "audit_index_report.json"

    written = export_audit_index_report_bundle_to_json(bundle, output_path)
    payload = json.loads(output_path.read_text())

    assert written == output_path
    assert payload["metadata"]["milestone"] == "20"
    assert set(payload["tables"]) == {"audit_summary", "audit_tables"}
    assert payload["tables"]["audit_summary"][0]["audit_id"] == "audit_a"


def test_export_audit_index_report_bundle_to_json_respects_overwrite_false(
    tmp_path: Path,
) -> None:
    bundle = build_audit_index_report_bundle(sample_audit_index())
    output_path = tmp_path / "audit_index_report.json"
    export_audit_index_report_bundle_to_json(bundle, output_path)

    with pytest.raises(FileExistsError, match="already exists"):
        export_audit_index_report_bundle_to_json(bundle, output_path)


def test_build_and_export_audit_index_report_returns_bundle_paths_and_summary(
    tmp_path: Path,
) -> None:
    result = build_and_export_audit_index_report(
        sample_audit_index(),
        tmp_path,
        metadata=create_audit_index_report_metadata(),
    )

    assert set(result) == {"report_bundle", "written_paths", "report_summary"}
    assert validate_audit_index_report_bundle(result["report_bundle"]) is result["report_bundle"]
    assert (tmp_path / "audit_summary.csv").exists()
    assert result["report_summary"]["table_name"].tolist() == [
        "audit_summary",
        "audit_tables",
    ]


def test_build_and_export_audit_index_report_respects_overwrite_false(
    tmp_path: Path,
) -> None:
    audit_index = sample_audit_index()
    build_and_export_audit_index_report(audit_index, tmp_path)

    with pytest.raises(FileExistsError, match="Refusing to overwrite"):
        build_and_export_audit_index_report(audit_index, tmp_path)


def test_audit_index_report_helpers_do_not_create_buy_sell_entry_or_exit_columns() -> None:
    bundle = build_audit_index_report_bundle(sample_audit_index())
    comparison_bundle = build_audit_index_comparison_bundle(
        sample_audit_index(),
        build_audit_index([audit_record("audit_a")]),
    )
    summary = summarize_audit_index_report_bundle(bundle)

    forbidden = ("buy", "sell", "entry", "exit")
    for table in [summary, *bundle["tables"].values(), *comparison_bundle["tables"].values()]:
        assert not any(word in column for column in table.columns for word in forbidden)


def test_audit_index_report_helpers_do_not_create_selection_scoring_or_edge_fields() -> None:
    bundle = build_audit_index_report_bundle(
        sample_audit_index(),
        metadata=create_audit_index_report_metadata(),
    )
    comparison_bundle = build_audit_index_comparison_bundle(
        sample_audit_index(),
        build_audit_index([audit_record("audit_a")]),
    )
    summary = summarize_audit_index_report_bundle(bundle)
    keys = collect_keys(bundle)
    keys.update(collect_keys(comparison_bundle))
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


def test_audit_index_report_helpers_do_not_read_audit_csv_table_contents(
    tmp_path: Path,
) -> None:
    table_path = tmp_path / "run_summary.csv"
    table_path.write_text("not,a,valid,research,table", encoding="utf-8")
    audit_index = build_audit_index(
        [
            audit_record(
                "audit_a",
                table_paths={"run_summary": str(table_path)},
            )
        ]
    )

    bundle = build_audit_index_report_bundle(audit_index)

    assert bundle["tables"]["audit_tables"]["table_path"].tolist() == [str(table_path)]


def test_event_audit_index_reports_does_not_import_or_call_disallowed_modules() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    module_path = repo_root / "src/spy_edge_research/backtesting/event_audit_index_reports.py"
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
