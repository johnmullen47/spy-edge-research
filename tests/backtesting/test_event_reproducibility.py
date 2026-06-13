from __future__ import annotations

import ast
import json
from pathlib import Path

import pandas as pd
import pytest

from spy_edge_research.backtesting import (
    build_audit_index,
    build_audit_index_reproducibility_checklist,
    build_registry_reproducibility_checklist,
    build_run_registry,
    build_reproducibility_checklist,
    check_required_files,
    check_required_metadata_keys,
    create_audit_record,
    create_run_record,
    create_reproducibility_check,
    read_reproducibility_checklist,
    reproducibility_checklist_status,
    summarize_reproducibility_checklist,
    validate_reproducibility_checklist,
    write_reproducibility_checklist,
)


def sample_check(name: str = "metadata.run_id", passed: bool = True) -> dict[str, object]:
    return create_reproducibility_check(
        check_name=name,
        passed=passed,
        severity="info" if passed else "warning",
        message="sample check",
        details={"source": "unit_test"},
    )


def sample_registry() -> dict[str, object]:
    return build_run_registry(
        [
            create_run_record(
                run_id="run_a",
                manifest_path="runs/run_a/manifest.json",
                metadata={"run_id": "run_a", "dataset": "jan"},
            )
        ],
        metadata={"registry_name": "sample"},
    )


def sample_audit_index(tmp_path: Path) -> dict[str, object]:
    audit_dir = tmp_path / "audit_a"
    audit_dir.mkdir()
    metadata_path = audit_dir / "metadata.json"
    table_path = audit_dir / "run_summary.csv"
    metadata_path.write_text('{"outcome": "not read"}', encoding="utf-8")
    table_path.write_text("outcome,value\nignored,1\n", encoding="utf-8")
    return build_audit_index(
        [
            create_audit_record(
                audit_id="audit_a",
                audit_dir=audit_dir,
                metadata_path=metadata_path,
                table_paths={"run_summary": table_path},
            )
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


def test_create_reproducibility_check_includes_check_name_passed_and_severity() -> None:
    check = create_reproducibility_check(check_name="metadata.run_id", passed=True)

    assert check["check_name"] == "metadata.run_id"
    assert check["passed"] is True
    assert check["severity"] == "info"


def test_create_reproducibility_check_accepts_optional_message_and_details() -> None:
    check = create_reproducibility_check(
        check_name="metadata.run_id",
        passed=True,
        message="run_id is present",
        details={"metadata_key": "run_id"},
    )

    assert check["message"] == "run_id is present"
    assert check["details"] == {"metadata_key": "run_id"}


def test_create_reproducibility_check_rejects_invalid_severity() -> None:
    with pytest.raises(ValueError, match="severity"):
        create_reproducibility_check(
            check_name="metadata.run_id",
            passed=True,
            severity="critical",
        )


def test_create_reproducibility_check_rejects_non_dict_details() -> None:
    with pytest.raises(TypeError, match="details"):
        create_reproducibility_check(
            check_name="metadata.run_id",
            passed=True,
            details=["not", "a", "dict"],  # type: ignore[arg-type]
        )


def test_build_reproducibility_checklist_includes_metadata_and_checks() -> None:
    checklist = build_reproducibility_checklist(
        [sample_check()],
        metadata={"research_cycle": "smoke"},
        checklist_version="1.0",
    )

    assert checklist["metadata"]["project_name"] == "SPY Directional Edge Research"
    assert checklist["metadata"]["checklist_version"] == "1.0"
    assert checklist["metadata"]["created_at_utc"].endswith("+00:00")
    assert checklist["metadata"]["research_cycle"] == "smoke"
    assert len(checklist["checks"]) == 1


def test_build_reproducibility_checklist_does_not_mutate_input_checks() -> None:
    checks = [sample_check()]
    original = json.loads(json.dumps(checks))

    checklist = build_reproducibility_checklist(checks)
    checklist["checks"][0]["check_name"] = "changed"
    checklist["checks"][0]["details"]["source"] = "changed"

    assert checks == original


def test_validate_reproducibility_checklist_accepts_valid_checklists() -> None:
    checklist = build_reproducibility_checklist([sample_check()])

    assert validate_reproducibility_checklist(checklist) is checklist


def test_validate_reproducibility_checklist_raises_on_non_dict_input() -> None:
    with pytest.raises(TypeError, match="checklist must be a dict"):
        validate_reproducibility_checklist(["not", "a", "dict"])


def test_validate_reproducibility_checklist_raises_when_metadata_is_missing() -> None:
    with pytest.raises(KeyError, match="metadata"):
        validate_reproducibility_checklist({"checks": []})


def test_validate_reproducibility_checklist_raises_when_checks_is_missing() -> None:
    with pytest.raises(KeyError, match="checks"):
        validate_reproducibility_checklist({"metadata": {}})


def test_validate_reproducibility_checklist_raises_when_check_entries_are_invalid() -> None:
    with pytest.raises(TypeError, match="checks\\[0\\]"):
        validate_reproducibility_checklist({"metadata": {}, "checks": ["not a dict"]})

    with pytest.raises(KeyError, match="required fields"):
        validate_reproducibility_checklist({"metadata": {}, "checks": [{"passed": True}]})


def test_check_required_metadata_keys_returns_one_check_per_required_key() -> None:
    checks = check_required_metadata_keys(
        {"run_id": "run_a", "dataset": "jan"},
        ["run_id", "dataset"],
    )

    assert [check["check_name"] for check in checks] == [
        "metadata.dataset",
        "metadata.run_id",
    ]


def test_check_required_metadata_keys_marks_missing_keys_as_failed() -> None:
    checks = check_required_metadata_keys({"run_id": "run_a"}, ["run_id", "dataset"])

    by_name = {check["check_name"]: check for check in checks}
    assert by_name["metadata.run_id"]["passed"] is True
    assert by_name["metadata.dataset"]["passed"] is False
    assert by_name["metadata.dataset"]["severity"] == "warning"


def test_check_required_files_works_with_dict_of_name_to_path(tmp_path: Path) -> None:
    existing = tmp_path / "manifest.json"
    missing = tmp_path / "missing.json"
    existing.write_text("not read", encoding="utf-8")

    checks = check_required_files({"manifest": existing, "missing": missing})

    by_name = {check["check_name"]: check for check in checks}
    assert by_name["file.manifest"]["passed"] is True
    assert by_name["file.missing"]["passed"] is False


def test_check_required_files_works_with_iterable_of_paths(tmp_path: Path) -> None:
    existing = tmp_path / "manifest.json"
    existing.write_text("not read", encoding="utf-8")

    checks = check_required_files([existing])

    assert checks[0]["check_name"] == "file.manifest.json"
    assert checks[0]["passed"] is True


def test_check_required_files_does_not_read_file_contents(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    existing = tmp_path / "manifest.json"
    existing.write_text("do not read", encoding="utf-8")

    def fail_read_text(self: Path, *args: object, **kwargs: object) -> str:
        raise AssertionError(f"read_text should not be called for {self}")

    monkeypatch.setattr(Path, "read_text", fail_read_text)

    checks = check_required_files({"manifest": existing})

    assert checks[0]["passed"] is True


def test_build_registry_reproducibility_checklist_validates_registry_input() -> None:
    with pytest.raises(TypeError, match="registry must be a dict"):
        build_registry_reproducibility_checklist(["not", "a", "registry"])  # type: ignore[arg-type]


def test_build_registry_reproducibility_checklist_creates_run_id_and_manifest_checks() -> None:
    checklist = build_registry_reproducibility_checklist(
        sample_registry(),
        required_metadata_keys=["registry_name"],
    )
    check_names = [check["check_name"] for check in checklist["checks"]]

    assert "registry.has_runs" in check_names
    assert "registry.metadata.registry_name" in check_names
    assert "registry.run.run_a.run_id" in check_names
    assert "registry.run.run_a.manifest_path" in check_names


def test_build_registry_reproducibility_checklist_does_not_read_manifest_files(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text('{"outcome": "not read"}', encoding="utf-8")
    registry = build_run_registry(
        [create_run_record(run_id="run_a", manifest_path=manifest_path)]
    )

    def fail_read_text(self: Path, *args: object, **kwargs: object) -> str:
        raise AssertionError(f"read_text should not be called for {self}")

    monkeypatch.setattr(Path, "read_text", fail_read_text)

    checklist = build_registry_reproducibility_checklist(registry)

    assert "registry.run.run_a.manifest_path" in [
        check["check_name"] for check in checklist["checks"]
    ]


def test_build_audit_index_reproducibility_checklist_validates_audit_index_input() -> None:
    with pytest.raises(TypeError, match="index must be a dict"):
        build_audit_index_reproducibility_checklist(["not", "an", "index"])  # type: ignore[arg-type]


def test_build_audit_index_reproducibility_checklist_creates_audit_id_and_dir_checks(
    tmp_path: Path,
) -> None:
    checklist = build_audit_index_reproducibility_checklist(
        sample_audit_index(tmp_path),
        required_metadata_keys=["index_name"],
    )
    check_names = [check["check_name"] for check in checklist["checks"]]

    assert "audit_index.has_audits" in check_names
    assert "audit_index.metadata.index_name" in check_names
    assert "audit_index.audit.audit_a.audit_id" in check_names
    assert "audit_index.audit.audit_a.audit_dir" in check_names


def test_build_audit_index_reproducibility_checklist_does_not_read_metadata_or_csv_tables(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    audit_index = sample_audit_index(tmp_path)

    def fail_read_text(self: Path, *args: object, **kwargs: object) -> str:
        raise AssertionError(f"read_text should not be called for {self}")

    def fail_read_csv(*args: object, **kwargs: object) -> pd.DataFrame:
        raise AssertionError("read_csv should not be called")

    monkeypatch.setattr(Path, "read_text", fail_read_text)
    monkeypatch.setattr(pd, "read_csv", fail_read_csv)

    checklist = build_audit_index_reproducibility_checklist(audit_index)

    assert any(
        check["check_name"] == "file.audit_index.audit.audit_a.table.run_summary"
        for check in checklist["checks"]
    )


def test_summarize_reproducibility_checklist_returns_sorted_dataframe() -> None:
    checklist = build_reproducibility_checklist(
        [sample_check("z_check"), sample_check("a_check")]
    )

    summary = summarize_reproducibility_checklist(checklist)

    assert summary.columns.tolist() == ["check_name", "passed", "severity", "message"]
    assert summary["check_name"].tolist() == ["a_check", "z_check"]


def test_reproducibility_checklist_status_returns_correct_counts() -> None:
    checklist = build_reproducibility_checklist(
        [
            sample_check("a_check", passed=True),
            create_reproducibility_check(
                check_name="b_check",
                passed=False,
                severity="warning",
            ),
            create_reproducibility_check(
                check_name="c_check",
                passed=False,
                severity="error",
            ),
        ]
    )

    assert reproducibility_checklist_status(checklist) == {
        "check_count": 3,
        "passed_count": 1,
        "failed_count": 2,
        "warning_count": 1,
        "error_count": 1,
        "all_passed": False,
    }


def test_write_reproducibility_checklist_writes_json(tmp_path: Path) -> None:
    checklist = build_reproducibility_checklist([sample_check()])
    output_path = tmp_path / "checklists" / "reproducibility.json"

    written = write_reproducibility_checklist(checklist, output_path)
    payload = json.loads(output_path.read_text())

    assert written == output_path
    assert payload["metadata"]["checklist_version"] == "1.0"
    assert payload["checks"][0]["check_name"] == "metadata.run_id"


def test_write_reproducibility_checklist_respects_overwrite_false(tmp_path: Path) -> None:
    checklist = build_reproducibility_checklist([sample_check()])
    output_path = tmp_path / "reproducibility.json"
    write_reproducibility_checklist(checklist, output_path)

    with pytest.raises(FileExistsError, match="already exists"):
        write_reproducibility_checklist(checklist, output_path)


def test_read_reproducibility_checklist_loads_and_validates_json(tmp_path: Path) -> None:
    checklist = build_reproducibility_checklist([sample_check()])
    output_path = tmp_path / "reproducibility.json"
    write_reproducibility_checklist(checklist, output_path)

    loaded = read_reproducibility_checklist(output_path)

    assert loaded == checklist


def test_reproducibility_helpers_do_not_create_buy_sell_entry_or_exit_columns(
    tmp_path: Path,
) -> None:
    checklist = build_audit_index_reproducibility_checklist(sample_audit_index(tmp_path))
    summary = summarize_reproducibility_checklist(checklist)

    forbidden = {"buy", "sell", "entry", "exit"}
    assert forbidden.isdisjoint(collect_keys(checklist))
    assert forbidden.isdisjoint(collect_keys(summary))


def test_reproducibility_helpers_do_not_create_selection_or_edge_fields(
    tmp_path: Path,
) -> None:
    checklist = build_audit_index_reproducibility_checklist(sample_audit_index(tmp_path))
    status = reproducibility_checklist_status(checklist)
    summary = summarize_reproducibility_checklist(checklist)

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
    assert forbidden.isdisjoint(collect_keys(checklist))
    assert forbidden.isdisjoint(collect_keys(status))
    assert forbidden.isdisjoint(collect_keys(summary))


def test_reproducibility_helpers_do_not_read_artifact_audit_csv_or_outcome_values(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text('{"outcome": "not read"}', encoding="utf-8")
    registry = build_run_registry(
        [create_run_record(run_id="run_a", manifest_path=manifest_path)]
    )
    audit_index = sample_audit_index(tmp_path)

    def fail_read_text(self: Path, *args: object, **kwargs: object) -> str:
        raise AssertionError(f"read_text should not be called for {self}")

    def fail_read_csv(*args: object, **kwargs: object) -> pd.DataFrame:
        raise AssertionError("read_csv should not be called")

    monkeypatch.setattr(Path, "read_text", fail_read_text)
    monkeypatch.setattr(pd, "read_csv", fail_read_csv)

    registry_checklist = build_registry_reproducibility_checklist(registry)
    audit_checklist = build_audit_index_reproducibility_checklist(audit_index)

    assert reproducibility_checklist_status(registry_checklist)["check_count"] > 0
    assert reproducibility_checklist_status(audit_checklist)["check_count"] > 0


def test_reproducibility_helpers_do_not_import_execution_or_strategy_modules() -> None:
    module_path = (
        Path(__file__).parents[2]
        / "src"
        / "spy_edge_research"
        / "backtesting"
        / "event_reproducibility.py"
    )
    tree = ast.parse(module_path.read_text(encoding="utf-8"))
    imported_names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            imported_names.add(node.module)

    forbidden_fragments = (
        "execution",
        "broker",
        "alert",
        "optimizer",
        "signal",
        "strategy",
    )
    assert not any(
        fragment in imported_name
        for imported_name in imported_names
        for fragment in forbidden_fragments
    )
