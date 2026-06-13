from __future__ import annotations

import ast
import json
from pathlib import Path

import pandas as pd
import pytest

from spy_edge_research.backtesting import (
    build_artifact_manifest,
    create_artifact_record,
    build_run_registry,
    create_run_record,
    discover_manifest_paths,
    load_run_registry_from_manifests,
    read_run_registry,
    summarize_registry_artifacts,
    summarize_run_registry,
    validate_run_metadata_consistency,
    validate_run_registry,
    write_artifact_manifest,
    write_run_registry,
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
    run_id: str | None = "run_a",
    artifact_names: list[str] | None = None,
    metadata: dict[str, object] | None = None,
) -> dict[str, object]:
    manifest_metadata: dict[str, object] = {"workflow_name": "event_research_workflow"}
    if run_id is not None:
        manifest_metadata["run_id"] = run_id
    if metadata is not None:
        manifest_metadata.update(metadata)
    return build_artifact_manifest(
        [artifact_record(name) for name in (artifact_names or ["event_study_results"])],
        metadata=manifest_metadata,
    )


def run_record(run_id: str = "run_a") -> dict[str, object]:
    manifest = artifact_manifest(run_id=run_id)
    return create_run_record(
        run_id=run_id,
        manifest_path=f"runs/{run_id}/manifest.json",
        manifest=manifest,
        metadata=manifest["metadata"],
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


def test_create_run_record_includes_run_id_manifest_path_and_created_at_utc() -> None:
    record = create_run_record(run_id="run_a", manifest_path=Path("runs/a/manifest.json"))

    assert record["run_id"] == "run_a"
    assert record["manifest_path"] == "runs/a/manifest.json"
    assert record["created_at_utc"].endswith("+00:00")


def test_create_run_record_accepts_and_validates_optional_manifest() -> None:
    manifest = artifact_manifest(run_id="run_a")

    record = create_run_record(
        run_id="run_a",
        manifest_path="runs/a/manifest.json",
        manifest=manifest,
    )

    assert record["manifest"] == manifest


def test_create_run_record_rejects_invalid_manifest_input() -> None:
    with pytest.raises(KeyError, match="metadata"):
        create_run_record(
            run_id="run_a",
            manifest_path="runs/a/manifest.json",
            manifest={"artifacts": []},
        )


def test_build_run_registry_includes_metadata_and_runs() -> None:
    registry = build_run_registry(
        [run_record()],
        metadata={"research_cycle": "smoke"},
        registry_version="1.0",
    )

    assert registry["metadata"]["project_name"] == "SPY Directional Edge Research"
    assert registry["metadata"]["registry_version"] == "1.0"
    assert registry["metadata"]["created_at_utc"].endswith("+00:00")
    assert registry["metadata"]["research_cycle"] == "smoke"
    assert len(registry["runs"]) == 1


def test_build_run_registry_does_not_mutate_input_records() -> None:
    records = [run_record()]
    original = json.loads(json.dumps(records))

    registry = build_run_registry(records)
    registry["runs"][0]["run_id"] = "changed"

    assert records == original


def test_validate_run_registry_accepts_valid_registries() -> None:
    registry = build_run_registry([run_record()])

    assert validate_run_registry(registry) is registry


def test_validate_run_registry_raises_on_non_dict_input() -> None:
    with pytest.raises(TypeError, match="registry must be a dict"):
        validate_run_registry(["not", "a", "dict"])


def test_validate_run_registry_raises_when_metadata_is_missing() -> None:
    with pytest.raises(KeyError, match="metadata"):
        validate_run_registry({"runs": []})


def test_validate_run_registry_raises_when_runs_is_missing() -> None:
    with pytest.raises(KeyError, match="runs"):
        validate_run_registry({"metadata": {}})


def test_validate_run_registry_raises_when_run_entries_are_invalid() -> None:
    with pytest.raises(TypeError, match="runs\\[0\\]"):
        validate_run_registry({"metadata": {}, "runs": ["not a dict"]})

    with pytest.raises(KeyError, match="required fields"):
        validate_run_registry({"metadata": {}, "runs": [{"run_id": "run_a"}]})


def test_discover_manifest_paths_returns_deterministic_sorted_manifest_paths(
    tmp_path: Path,
) -> None:
    write_artifact_manifest(artifact_manifest(run_id="b"), tmp_path / "b" / "manifest.json")
    write_artifact_manifest(artifact_manifest(run_id="a"), tmp_path / "a" / "manifest.json")
    (tmp_path / "a" / "not_manifest.json").write_text("{}", encoding="utf-8")

    paths = discover_manifest_paths(tmp_path)

    assert paths == [
        tmp_path / "a" / "manifest.json",
        tmp_path / "b" / "manifest.json",
    ]


def test_discover_manifest_paths_raises_when_root_dir_does_not_exist(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="does not exist"):
        discover_manifest_paths(tmp_path / "missing")


def test_load_run_registry_from_manifests_loads_multiple_manifest_json_files(
    tmp_path: Path,
) -> None:
    first = tmp_path / "first" / "manifest.json"
    second = tmp_path / "second" / "manifest.json"
    write_artifact_manifest(artifact_manifest(run_id="run_b"), first)
    write_artifact_manifest(artifact_manifest(run_id="run_a"), second)

    registry = load_run_registry_from_manifests([first, second], base_dir=tmp_path)

    assert [run["run_id"] for run in registry["runs"]] == ["run_a", "run_b"]
    assert [run["manifest_path"] for run in registry["runs"]] == [
        "second/manifest.json",
        "first/manifest.json",
    ]
    assert all("manifest" in run for run in registry["runs"])


def test_load_run_registry_from_manifests_creates_deterministic_run_id_values(
    tmp_path: Path,
) -> None:
    manifest_path = tmp_path / "research runs" / "no id" / "manifest.json"
    write_artifact_manifest(artifact_manifest(run_id=None), manifest_path)

    registry = load_run_registry_from_manifests([manifest_path], base_dir=tmp_path)

    assert registry["runs"][0]["run_id"] == "research_runs_no_id_manifest"


def test_load_run_registry_from_manifests_sorts_runs_by_run_id(tmp_path: Path) -> None:
    first = tmp_path / "z" / "manifest.json"
    second = tmp_path / "a" / "manifest.json"
    write_artifact_manifest(artifact_manifest(run_id="z_run"), first)
    write_artifact_manifest(artifact_manifest(run_id="a_run"), second)

    registry = load_run_registry_from_manifests([first, second])

    assert [run["run_id"] for run in registry["runs"]] == ["a_run", "z_run"]


def test_summarize_run_registry_returns_deterministic_dataframe_sorted_by_run_id() -> None:
    registry = build_run_registry([run_record("z_run"), run_record("a_run")])

    summary = summarize_run_registry(registry)

    assert isinstance(summary, pd.DataFrame)
    assert summary["run_id"].tolist() == ["a_run", "z_run"]
    assert summary.columns.tolist() == [
        "run_id",
        "manifest_path",
        "artifact_count",
        "artifact_types",
        "project_name",
        "created_at_utc",
        "metadata_keys",
    ]


def test_summarize_registry_artifacts_returns_one_row_per_artifact_across_runs() -> None:
    registry = build_run_registry(
        [
            create_run_record(
                run_id="run_a",
                manifest_path="a/manifest.json",
                manifest=artifact_manifest(
                    run_id="run_a",
                    artifact_names=["event_study_results", "metadata"],
                ),
            ),
            run_record("run_b"),
        ]
    )

    summary = summarize_registry_artifacts(registry)

    assert len(summary) == 3
    assert summary["run_id"].tolist().count("run_a") == 2
    assert summary["run_id"].tolist().count("run_b") == 1


def test_summarize_registry_artifacts_sorts_by_run_id_and_artifact_name() -> None:
    registry = build_run_registry(
        [
            create_run_record(
                run_id="run_b",
                manifest_path="b/manifest.json",
                manifest=artifact_manifest(
                    run_id="run_b",
                    artifact_names=["z_table", "a_table"],
                ),
            ),
            create_run_record(
                run_id="run_a",
                manifest_path="a/manifest.json",
                manifest=artifact_manifest(run_id="run_a", artifact_names=["m_table"]),
            ),
        ]
    )

    summary = summarize_registry_artifacts(registry)

    assert summary[["run_id", "artifact_name"]].values.tolist() == [
        ["run_a", "m_table"],
        ["run_b", "a_table"],
        ["run_b", "z_table"],
    ]


def test_validate_run_metadata_consistency_returns_metadata_key_presence_rows() -> None:
    registry = build_run_registry(
        [
            create_run_record(
                run_id="run_a",
                manifest_path="a/manifest.json",
                metadata={"dataset": "jan", "workflow_name": "event_research_workflow"},
            ),
            create_run_record(
                run_id="run_b",
                manifest_path="b/manifest.json",
                metadata={"workflow_name": "event_research_workflow"},
            ),
        ]
    )

    summary = validate_run_metadata_consistency(registry)

    assert summary.values.tolist() == [
        ["run_a", "dataset", True],
        ["run_a", "workflow_name", True],
        ["run_b", "dataset", False],
        ["run_b", "workflow_name", True],
    ]


def test_validate_run_metadata_consistency_respects_required_metadata_keys() -> None:
    registry = build_run_registry(
        [
            create_run_record(
                run_id="run_a",
                manifest_path="a/manifest.json",
                metadata={"workflow_name": "event_research_workflow"},
            )
        ]
    )

    summary = validate_run_metadata_consistency(
        registry,
        required_metadata_keys=["dataset", "workflow_name"],
    )

    assert summary.values.tolist() == [
        ["run_a", "dataset", False],
        ["run_a", "workflow_name", True],
    ]


def test_write_run_registry_writes_json(tmp_path: Path) -> None:
    registry = build_run_registry([run_record()])
    output_path = tmp_path / "registries" / "run_registry.json"

    written = write_run_registry(registry, output_path)
    payload = json.loads(output_path.read_text())

    assert written == output_path
    assert payload["metadata"]["registry_version"] == "1.0"
    assert payload["runs"][0]["run_id"] == "run_a"


def test_write_run_registry_respects_overwrite_false(tmp_path: Path) -> None:
    registry = build_run_registry([run_record()])
    output_path = tmp_path / "run_registry.json"
    write_run_registry(registry, output_path)

    with pytest.raises(FileExistsError, match="already exists"):
        write_run_registry(registry, output_path)


def test_read_run_registry_loads_and_validates_json(tmp_path: Path) -> None:
    registry = build_run_registry([run_record()])
    output_path = tmp_path / "run_registry.json"
    write_run_registry(registry, output_path)

    loaded = read_run_registry(output_path)

    assert loaded == registry


def test_run_registry_helpers_do_not_create_buy_sell_entry_exit_columns() -> None:
    registry = build_run_registry([run_record()])
    outputs = [
        registry,
        summarize_run_registry(registry),
        summarize_registry_artifacts(registry),
        validate_run_metadata_consistency(registry),
    ]

    forbidden = {"buy", "sell", "entry", "exit"}
    for output in outputs:
        assert forbidden.isdisjoint(collect_keys(output))


def test_run_registry_helpers_do_not_create_confidence_score_rank_edge_or_selection_fields() -> None:
    registry = build_run_registry([run_record()])
    outputs = [
        registry,
        summarize_run_registry(registry),
        summarize_registry_artifacts(registry),
        validate_run_metadata_consistency(registry),
    ]

    forbidden = {"confidence", "score", "rank", "edge", "best_event", "selected_event"}
    for output in outputs:
        assert forbidden.isdisjoint(collect_keys(output))


def test_run_registry_helpers_do_not_inspect_artifact_contents(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest_path = tmp_path / "run_a" / "manifest.json"
    artifact_path = tmp_path / "run_a" / "exports" / "event_study_results.csv"
    write_artifact_manifest(
        artifact_manifest(
            run_id="run_a",
            metadata={"artifact_absolute_path": artifact_path},
        ),
        manifest_path,
    )
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.write_text("this,file,must,not,be,read\n", encoding="utf-8")
    original_read_text = Path.read_text
    read_paths: list[Path] = []

    def guarded_read_text(path: Path, *args: object, **kwargs: object) -> str:
        read_paths.append(path)
        if path == artifact_path:
            raise AssertionError("artifact contents were read")
        return original_read_text(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", guarded_read_text)

    registry = load_run_registry_from_manifests([manifest_path], base_dir=tmp_path)

    assert registry["runs"][0]["run_id"] == "run_a"
    assert read_paths == [manifest_path]


def test_run_registry_helpers_do_not_import_execution_or_strategy_modules() -> None:
    source_path = (
        Path(__file__).parents[2]
        / "src"
        / "spy_edge_research"
        / "backtesting"
        / "event_run_registry.py"
    )
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
    imported_modules: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_modules.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            imported_modules.append(node.module)

    forbidden = ("execution", "broker", "alert", "optimizer", "signal", "strategy")
    assert not any(
        forbidden_word in module
        for module in imported_modules
        for forbidden_word in forbidden
    )
