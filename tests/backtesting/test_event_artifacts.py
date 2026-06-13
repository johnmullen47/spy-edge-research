from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from spy_edge_research.backtesting.event_artifacts import (
    build_artifact_manifest,
    build_manifest_from_written_paths,
    create_artifact_record,
    index_artifact_paths,
    infer_artifact_type,
    read_artifact_manifest,
    summarize_artifact_manifest,
    validate_artifact_manifest,
    write_artifact_manifest,
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


def collect_manifest_keys(value: object) -> set[str]:
    keys: set[str] = set()
    if isinstance(value, dict):
        for key, nested in value.items():
            keys.add(str(key))
            keys.update(collect_manifest_keys(nested))
    elif isinstance(value, list):
        for nested in value:
            keys.update(collect_manifest_keys(nested))
    return keys


def test_create_artifact_record_includes_required_fields_and_created_at_utc() -> None:
    record = create_artifact_record(
        name="event_study_results",
        path="exports/event_study_results.csv",
        artifact_type="csv_table",
    )

    assert record["name"] == "event_study_results"
    assert record["path"] == "exports/event_study_results.csv"
    assert record["artifact_type"] == "csv_table"
    assert record["created_at_utc"].endswith("+00:00")


def test_create_artifact_record_includes_optional_counts_and_metadata() -> None:
    record = create_artifact_record(
        name="metadata",
        path=Path("exports/metadata.json"),
        artifact_type="json",
        description="workflow metadata",
        row_count=0,
        column_count=2,
        metadata={"workflow_name": "event_research_workflow"},
    )

    assert record["description"] == "workflow metadata"
    assert record["row_count"] == 0
    assert record["column_count"] == 2
    assert record["metadata"] == {"workflow_name": "event_research_workflow"}


def test_create_artifact_record_rejects_negative_row_or_column_count() -> None:
    with pytest.raises(ValueError, match="row_count"):
        create_artifact_record(
            name="table",
            path="table.csv",
            artifact_type="csv_table",
            row_count=-1,
        )

    with pytest.raises(ValueError, match="column_count"):
        create_artifact_record(
            name="table",
            path="table.csv",
            artifact_type="csv_table",
            column_count=-1,
        )


def test_infer_artifact_type_maps_suffixes_deterministically() -> None:
    assert infer_artifact_type("table.csv") == "csv_table"
    assert infer_artifact_type("manifest.json") == "json"
    assert infer_artifact_type("chart.png") == "image"
    assert infer_artifact_type("chart.svg") == "image"
    assert infer_artifact_type("notes.txt") == "text"
    assert infer_artifact_type("artifact.parquet") == "unknown"


def test_index_artifact_paths_accepts_list_of_paths() -> None:
    records = index_artifact_paths(
        [
            Path("exports/event_study_results.csv"),
            Path("exports/metadata.json"),
        ]
    )

    assert [record["name"] for record in records] == ["event_study_results", "metadata"]
    assert [record["artifact_type"] for record in records] == ["csv_table", "json"]
    assert [record["path"] for record in records] == [
        "exports/event_study_results.csv",
        "exports/metadata.json",
    ]


def test_index_artifact_paths_accepts_name_to_path_mapping() -> None:
    records = index_artifact_paths(
        {
            "results": Path("exports/event_study_results.csv"),
            "metadata": Path("exports/metadata.json"),
        }
    )

    assert [record["name"] for record in records] == ["results", "metadata"]
    assert [record["artifact_type"] for record in records] == ["csv_table", "json"]


def test_index_artifact_paths_can_make_paths_relative_to_base_dir(tmp_path: Path) -> None:
    output_dir = tmp_path / "exports"
    paths = [output_dir / "event_study_results.csv"]

    records = index_artifact_paths(paths, base_dir=tmp_path)

    assert records[0]["path"] == "exports/event_study_results.csv"


def test_build_artifact_manifest_includes_metadata_and_artifacts() -> None:
    manifest = build_artifact_manifest(
        [artifact_record()],
        metadata={"workflow_name": "event_research_workflow"},
        manifest_version="1.0",
    )

    assert manifest["metadata"]["project_name"] == "SPY Directional Edge Research"
    assert manifest["metadata"]["manifest_version"] == "1.0"
    assert manifest["metadata"]["created_at_utc"].endswith("+00:00")
    assert manifest["metadata"]["workflow_name"] == "event_research_workflow"
    assert len(manifest["artifacts"]) == 1


def test_build_artifact_manifest_does_not_mutate_input_records() -> None:
    records = [artifact_record()]
    original = [record.copy() for record in records]

    manifest = build_artifact_manifest(records)
    manifest["artifacts"][0]["name"] = "changed"

    assert records == original


def test_validate_artifact_manifest_accepts_valid_manifest() -> None:
    manifest = build_artifact_manifest([artifact_record()])

    assert validate_artifact_manifest(manifest) is manifest


def test_validate_artifact_manifest_raises_on_non_dict_input() -> None:
    with pytest.raises(TypeError, match="manifest must be a dict"):
        validate_artifact_manifest(["not", "a", "dict"])


def test_validate_artifact_manifest_raises_when_metadata_is_missing() -> None:
    with pytest.raises(KeyError, match="metadata"):
        validate_artifact_manifest({"artifacts": []})


def test_validate_artifact_manifest_raises_when_artifacts_is_missing() -> None:
    with pytest.raises(KeyError, match="artifacts"):
        validate_artifact_manifest({"metadata": {}})


def test_validate_artifact_manifest_raises_when_artifact_entries_are_invalid() -> None:
    with pytest.raises(TypeError, match="artifacts\\[0\\]"):
        validate_artifact_manifest({"metadata": {}, "artifacts": ["not a dict"]})

    with pytest.raises(KeyError, match="required fields"):
        validate_artifact_manifest({"metadata": {}, "artifacts": [{"name": "table"}]})


def test_write_artifact_manifest_writes_json(tmp_path: Path) -> None:
    manifest = build_artifact_manifest([artifact_record()])
    output_path = tmp_path / "manifests" / "artifact_manifest.json"

    written = write_artifact_manifest(manifest, output_path)
    payload = json.loads(output_path.read_text())

    assert written == output_path
    assert payload["metadata"]["manifest_version"] == "1.0"
    assert payload["artifacts"][0]["name"] == "event_study_results"


def test_write_artifact_manifest_respects_overwrite_false(tmp_path: Path) -> None:
    manifest = build_artifact_manifest([artifact_record()])
    output_path = tmp_path / "artifact_manifest.json"
    write_artifact_manifest(manifest, output_path)

    with pytest.raises(FileExistsError, match="already exists"):
        write_artifact_manifest(manifest, output_path)


def test_read_artifact_manifest_loads_and_validates_json(tmp_path: Path) -> None:
    manifest = build_artifact_manifest([artifact_record()])
    output_path = tmp_path / "artifact_manifest.json"
    write_artifact_manifest(manifest, output_path)

    loaded = read_artifact_manifest(output_path)

    assert loaded == manifest


def test_summarize_artifact_manifest_returns_sorted_dataframe() -> None:
    manifest = build_artifact_manifest(
        [
            artifact_record("z_table"),
            artifact_record("a_table"),
        ]
    )

    summary = summarize_artifact_manifest(manifest)

    assert isinstance(summary, pd.DataFrame)
    assert summary["name"].tolist() == ["a_table", "z_table"]
    assert summary.columns.tolist() == [
        "name",
        "path",
        "artifact_type",
        "description",
        "row_count",
        "column_count",
        "created_at_utc",
    ]


def test_build_manifest_from_written_paths_accepts_export_style_path_dictionaries() -> None:
    manifest = build_manifest_from_written_paths(
        {
            "event_study_results": Path("exports/event_study_results.csv"),
            "diagnostics": Path("exports/diagnostics.csv"),
            "nested": {"metadata": Path("exports/metadata.json")},
        },
        metadata={"workflow_name": "event_research_workflow"},
    )

    assert [record["name"] for record in manifest["artifacts"]] == [
        "event_study_results",
        "diagnostics",
        "nested.metadata",
    ]
    assert manifest["metadata"]["workflow_name"] == "event_research_workflow"
    assert validate_artifact_manifest(manifest) is manifest


def test_artifact_helpers_do_not_create_buy_sell_entry_or_exit_columns_or_fields() -> None:
    manifest = build_manifest_from_written_paths(
        {"event_study_results": Path("exports/event_study_results.csv")}
    )
    summary = summarize_artifact_manifest(manifest)

    forbidden = ("buy", "sell", "entry", "exit")
    assert not any(word in key for key in collect_manifest_keys(manifest) for word in forbidden)
    assert not any(word in column for column in summary.columns for word in forbidden)


def test_artifact_helpers_do_not_create_confidence_score_rank_or_edge_fields() -> None:
    manifest = build_manifest_from_written_paths(
        {"event_study_results": Path("exports/event_study_results.csv")}
    )
    summary = summarize_artifact_manifest(manifest)

    forbidden = ("confidence", "score", "rank", "edge")
    keys = {key.lower() for key in collect_manifest_keys(manifest)}
    columns = {column.lower() for column in summary.columns}
    assert not any(word in key for key in keys for word in forbidden)
    assert not any(word in column for column in columns for word in forbidden)


def test_event_artifacts_do_not_import_or_call_execution_broker_alert_optimizer_signal_or_strategy_modules() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    module_text = (
        repo_root / "src/spy_edge_research/backtesting/event_artifacts.py"
    ).read_text()
    forbidden_terms = (
        "execution",
        "broker",
        "alert",
        "optimizer",
        "signal",
        "strategy",
    )

    assert not any(term in module_text.lower() for term in forbidden_terms)
