from __future__ import annotations

import ast
import json
from pathlib import Path

import pandas as pd
import pytest

from spy_edge_research.backtesting import (
    build_audit_index,
    create_audit_record,
    discover_audit_export_dirs,
    index_audit_export_dir,
    load_audit_index_from_dirs,
    load_audit_metadata,
    read_audit_index,
    summarize_audit_index,
    summarize_audit_tables,
    validate_audit_index,
    write_audit_index,
)


def audit_record(audit_id: str = "audit_a") -> dict[str, object]:
    return create_audit_record(
        audit_id=audit_id,
        audit_dir=f"audits/{audit_id}",
        metadata_path=f"audits/{audit_id}/metadata.json",
        table_paths={"run_summary": f"audits/{audit_id}/run_summary.csv"},
        metadata={"registry_name": audit_id},
    )


def write_audit_dir(
    root: Path,
    name: str,
    *,
    tables: tuple[str, ...] = (
        "run_summary.csv",
        "artifact_summary.csv",
        "metadata_consistency.csv",
    ),
    metadata: dict[str, object] | None = None,
) -> Path:
    audit_dir = root / name
    audit_dir.mkdir(parents=True)
    (audit_dir / "metadata.json").write_text(
        json.dumps(metadata or {"registry_name": name}),
        encoding="utf-8",
    )
    for table in tables:
        (audit_dir / table).write_text("this,is,not,read\n", encoding="utf-8")
    return audit_dir


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


def test_create_audit_record_includes_audit_id_audit_dir_and_created_at_utc() -> None:
    record = create_audit_record(audit_id="audit_a", audit_dir=Path("audits/audit_a"))

    assert record["audit_id"] == "audit_a"
    assert record["audit_dir"] == "audits/audit_a"
    assert record["created_at_utc"].endswith("+00:00")


def test_create_audit_record_accepts_optional_paths_and_metadata() -> None:
    record = create_audit_record(
        audit_id="audit_a",
        audit_dir="audits/audit_a",
        metadata_path=Path("audits/audit_a/metadata.json"),
        table_paths={
            "run_summary": Path("audits/audit_a/run_summary.csv"),
            "artifact_summary": "audits/audit_a/artifact_summary.csv",
        },
        metadata={"registry_name": "sample"},
    )

    assert record["metadata_path"] == "audits/audit_a/metadata.json"
    assert record["table_paths"] == {
        "run_summary": "audits/audit_a/run_summary.csv",
        "artifact_summary": "audits/audit_a/artifact_summary.csv",
    }
    assert record["metadata"] == {"registry_name": "sample"}


def test_create_audit_record_rejects_non_dict_table_paths() -> None:
    with pytest.raises(TypeError, match="table_paths"):
        create_audit_record(
            audit_id="audit_a",
            audit_dir="audits/audit_a",
            table_paths=["run_summary.csv"],  # type: ignore[arg-type]
        )


def test_create_audit_record_rejects_non_string_table_path_values() -> None:
    with pytest.raises(TypeError, match="run_summary"):
        create_audit_record(
            audit_id="audit_a",
            audit_dir="audits/audit_a",
            table_paths={"run_summary": 123},  # type: ignore[dict-item]
        )


def test_build_audit_index_includes_metadata_and_audits() -> None:
    index = build_audit_index(
        [audit_record()],
        metadata={"research_cycle": "smoke"},
        index_version="1.0",
    )

    assert index["metadata"]["project_name"] == "SPY Directional Edge Research"
    assert index["metadata"]["index_version"] == "1.0"
    assert index["metadata"]["created_at_utc"].endswith("+00:00")
    assert index["metadata"]["research_cycle"] == "smoke"
    assert len(index["audits"]) == 1


def test_build_audit_index_does_not_mutate_input_records() -> None:
    records = [audit_record()]
    original = json.loads(json.dumps(records))

    index = build_audit_index(records)
    index["audits"][0]["audit_id"] = "changed"
    index["audits"][0]["table_paths"]["run_summary"] = "changed.csv"

    assert records == original


def test_validate_audit_index_accepts_valid_indexes() -> None:
    index = build_audit_index([audit_record()])

    assert validate_audit_index(index) is index


def test_validate_audit_index_raises_on_non_dict_input() -> None:
    with pytest.raises(TypeError, match="index must be a dict"):
        validate_audit_index(["not", "a", "dict"])


def test_validate_audit_index_raises_when_metadata_is_missing() -> None:
    with pytest.raises(KeyError, match="metadata"):
        validate_audit_index({"audits": []})


def test_validate_audit_index_raises_when_audits_is_missing() -> None:
    with pytest.raises(KeyError, match="audits"):
        validate_audit_index({"metadata": {}})


def test_validate_audit_index_raises_when_audit_entries_are_invalid() -> None:
    with pytest.raises(TypeError, match="audits\\[0\\]"):
        validate_audit_index({"metadata": {}, "audits": ["not a dict"]})

    with pytest.raises(KeyError, match="required fields"):
        validate_audit_index({"metadata": {}, "audits": [{"audit_id": "audit_a"}]})


def test_discover_audit_export_dirs_returns_deterministic_sorted_dirs(tmp_path: Path) -> None:
    b_dir = write_audit_dir(tmp_path, "b_audit")
    a_dir = write_audit_dir(tmp_path, "a_audit")
    nested_dir = write_audit_dir(tmp_path / "nested", "c_audit")
    (tmp_path / "not_metadata.json").write_text("{}", encoding="utf-8")

    dirs = discover_audit_export_dirs(tmp_path)

    assert dirs == [a_dir, b_dir, nested_dir]


def test_discover_audit_export_dirs_raises_when_root_dir_does_not_exist(
    tmp_path: Path,
) -> None:
    with pytest.raises(FileNotFoundError, match="does not exist"):
        discover_audit_export_dirs(tmp_path / "missing")


def test_index_audit_export_dir_identifies_metadata_and_known_csv_tables(
    tmp_path: Path,
) -> None:
    audit_dir = write_audit_dir(tmp_path, "audit_a")

    record = index_audit_export_dir(audit_dir)

    assert record["audit_id"] == "audit_a"
    assert record["metadata_path"] == str(audit_dir / "metadata.json")
    assert record["table_paths"] == {
        "run_summary": str(audit_dir / "run_summary.csv"),
        "artifact_summary": str(audit_dir / "artifact_summary.csv"),
        "metadata_consistency": str(audit_dir / "metadata_consistency.csv"),
    }


def test_index_audit_export_dir_does_not_require_all_known_csv_tables(
    tmp_path: Path,
) -> None:
    audit_dir = write_audit_dir(tmp_path, "audit_a", tables=("run_summary.csv",))

    record = index_audit_export_dir(audit_dir)

    assert record["table_paths"] == {
        "run_summary": str(audit_dir / "run_summary.csv"),
    }


def test_load_audit_metadata_loads_metadata_json(tmp_path: Path) -> None:
    metadata_path = tmp_path / "metadata.json"
    metadata_path.write_text(json.dumps({"registry_name": "sample"}), encoding="utf-8")

    metadata = load_audit_metadata(metadata_path)

    assert metadata == {"registry_name": "sample"}


def test_load_audit_metadata_raises_on_missing_file(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="does not exist"):
        load_audit_metadata(tmp_path / "missing.json")


def test_load_audit_index_from_dirs_builds_deterministic_sorted_index_records(
    tmp_path: Path,
) -> None:
    z_dir = write_audit_dir(tmp_path, "z_audit")
    a_dir = write_audit_dir(tmp_path, "a_audit")

    index = load_audit_index_from_dirs([z_dir, a_dir])

    assert [audit["audit_id"] for audit in index["audits"]] == ["a_audit", "z_audit"]


def test_load_audit_index_from_dirs_attaches_metadata_when_requested(
    tmp_path: Path,
) -> None:
    audit_dir = write_audit_dir(
        tmp_path,
        "audit_a",
        metadata={"registry_name": "sample", "milestone": "18"},
    )

    index = load_audit_index_from_dirs([audit_dir], load_metadata=True)

    assert index["audits"][0]["metadata"] == {
        "registry_name": "sample",
        "milestone": "18",
    }


def test_load_audit_index_from_dirs_does_not_attach_metadata_when_disabled(
    tmp_path: Path,
) -> None:
    audit_dir = write_audit_dir(tmp_path, "audit_a")

    index = load_audit_index_from_dirs([audit_dir], load_metadata=False)

    assert "metadata" not in index["audits"][0]


def test_summarize_audit_index_returns_deterministic_dataframe_sorted_by_audit_id() -> None:
    index = build_audit_index([audit_record("z_audit"), audit_record("a_audit")])

    summary = summarize_audit_index(index)

    assert isinstance(summary, pd.DataFrame)
    assert summary["audit_id"].tolist() == ["a_audit", "z_audit"]
    assert summary.columns.tolist() == [
        "audit_id",
        "audit_dir",
        "metadata_path",
        "table_count",
        "table_names",
        "created_at_utc",
        "metadata_keys",
    ]


def test_summarize_audit_tables_returns_one_row_per_indexed_table_path() -> None:
    index = build_audit_index(
        [
            create_audit_record(
                audit_id="audit_a",
                audit_dir="audits/audit_a",
                table_paths={
                    "run_summary": "audits/audit_a/run_summary.csv",
                    "artifact_summary": "audits/audit_a/artifact_summary.csv",
                },
            ),
            audit_record("audit_b"),
        ]
    )

    summary = summarize_audit_tables(index)

    assert len(summary) == 3
    assert summary["audit_id"].tolist().count("audit_a") == 2
    assert summary["audit_id"].tolist().count("audit_b") == 1


def test_summarize_audit_tables_sorts_by_audit_id_and_table_name() -> None:
    index = build_audit_index(
        [
            create_audit_record(
                audit_id="audit_b",
                audit_dir="audits/audit_b",
                table_paths={
                    "run_summary": "audits/audit_b/run_summary.csv",
                    "artifact_summary": "audits/audit_b/artifact_summary.csv",
                },
            ),
            audit_record("audit_a"),
        ]
    )

    summary = summarize_audit_tables(index)

    assert summary[["audit_id", "table_name"]].values.tolist() == [
        ["audit_a", "run_summary"],
        ["audit_b", "artifact_summary"],
        ["audit_b", "run_summary"],
    ]


def test_write_audit_index_writes_json(tmp_path: Path) -> None:
    index = build_audit_index([audit_record()])
    output_path = tmp_path / "indexes" / "audit_index.json"

    written = write_audit_index(index, output_path)
    payload = json.loads(output_path.read_text())

    assert written == output_path
    assert payload["metadata"]["index_version"] == "1.0"
    assert payload["audits"][0]["audit_id"] == "audit_a"


def test_write_audit_index_respects_overwrite_false(tmp_path: Path) -> None:
    index = build_audit_index([audit_record()])
    output_path = tmp_path / "audit_index.json"
    write_audit_index(index, output_path)

    with pytest.raises(FileExistsError, match="already exists"):
        write_audit_index(index, output_path)


def test_read_audit_index_loads_and_validates_json(tmp_path: Path) -> None:
    index = build_audit_index([audit_record()])
    output_path = tmp_path / "audit_index.json"
    write_audit_index(index, output_path)

    loaded = read_audit_index(output_path)

    assert loaded == index


def test_audit_index_helpers_do_not_create_buy_sell_entry_or_exit_columns() -> None:
    index = build_audit_index([audit_record()])
    outputs = [
        index,
        summarize_audit_index(index),
        summarize_audit_tables(index),
    ]

    forbidden = {"buy", "sell", "entry", "exit"}
    for output in outputs:
        assert forbidden.isdisjoint(collect_keys(output))


def test_audit_index_helpers_do_not_create_selection_or_edge_fields() -> None:
    index = build_audit_index([audit_record()])
    outputs = [
        index,
        summarize_audit_index(index),
        summarize_audit_tables(index),
    ]

    forbidden = {
        "confidence",
        "score",
        "rank",
        "edge",
        "best_run",
        "best_event",
        "selected_event",
    }
    for output in outputs:
        keys = {key.lower() for key in collect_keys(output)}
        assert forbidden.isdisjoint(keys)


def test_audit_index_helpers_do_not_read_audit_csv_table_contents(tmp_path: Path) -> None:
    audit_dir = write_audit_dir(tmp_path, "audit_a")
    (audit_dir / "run_summary.csv").write_text("not,a,valid,research,table", encoding="utf-8")

    index = load_audit_index_from_dirs([audit_dir])
    table_summary = summarize_audit_tables(index)

    assert table_summary["table_path"].str.endswith(".csv").all()
    assert index["audits"][0]["metadata"] == {"registry_name": "audit_a"}


def test_event_audit_index_does_not_import_or_call_disallowed_modules() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    module_path = repo_root / "src/spy_edge_research/backtesting/event_audit_index.py"
    module_text = module_path.read_text()
    parsed = ast.parse(module_text)
    imported_modules = set()
    called_names = set()
    for node in ast.walk(parsed):
        if isinstance(node, ast.Import):
            imported_modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            imported_modules.add(node.module)
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                called_names.add(node.func.id)
            elif isinstance(node.func, ast.Attribute):
                called_names.add(node.func.attr)

    disallowed = {
        "execution",
        "broker",
        "alert",
        "optimizer",
        "signal",
        "strategy",
    }
    checked = {name.lower() for name in imported_modules.union(called_names)}
    assert not any(term in name for term in disallowed for name in checked)
