"""Research-only reproducibility checklist helpers.

These utilities document whether research packages contain expected metadata,
registry/audit-index structure, and files. They perform structural checklist
bookkeeping only and never read audit table contents, artifact contents,
outcome values, or forward-label values.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from copy import deepcopy
from pathlib import Path
from typing import Any

import pandas as pd

from spy_edge_research.backtesting.event_audit_index import validate_audit_index
from spy_edge_research.backtesting.event_run_registry import validate_run_registry

from spy_edge_research._internal._common import (
    created_at_utc as _created_at_utc,
    json_safe_mapping as _json_safe_mapping,
)

CHECKLIST_SUMMARY_COLUMNS: tuple[str, ...] = (
    "check_name",
    "passed",
    "severity",
    "message",
)

ALLOWED_REPRODUCIBILITY_SEVERITIES: frozenset[str] = frozenset(
    {"info", "warning", "error"}
)

FORBIDDEN_REPRODUCIBILITY_FIELDS: frozenset[str] = frozenset(
    {
        "buy",
        "sell",
        "entry",
        "exit",
        "confidence",
        "score",
        "rank",
        "edge",
        "best_audit",
        "best_run",
        "best_event",
        "selected_event",
        "p_l",
        "pnl",
        "profit",
    }
)


def validate_reproducibility_checklist(checklist: Any) -> dict[str, Any]:
    """Validate a reproducibility checklist structure."""
    if not isinstance(checklist, dict):
        raise TypeError("checklist must be a dict")

    if "metadata" not in checklist:
        raise KeyError("checklist is missing metadata")
    if not isinstance(checklist["metadata"], dict):
        raise TypeError("checklist metadata must be a dict")

    if "checks" not in checklist:
        raise KeyError("checklist is missing checks")
    checks = checklist["checks"]
    if not isinstance(checks, list):
        raise TypeError("checklist checks must be a list")

    for index, check in enumerate(checks):
        _validate_check_record(check, record_name=f"checks[{index}]")

    _raise_forbidden_fields(checklist, name="checklist")
    return checklist


def create_reproducibility_check(
    *,
    check_name: str,
    passed: bool,
    severity: str = "info",
    message: str | None = None,
    details: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Create one reproducibility checklist record."""
    _validate_non_empty_string(check_name, "check_name")
    if not isinstance(passed, bool):
        raise TypeError("passed must be a bool")
    _validate_severity(severity)
    if message is not None and not isinstance(message, str):
        raise TypeError("message must be a string when provided")
    if details is not None and not isinstance(details, Mapping):
        raise TypeError("details must be a mapping when provided")

    check: dict[str, Any] = {
        "check_name": check_name,
        "passed": bool(passed),
        "severity": severity,
    }
    if message is not None:
        check["message"] = message
    if details is not None:
        check["details"] = _json_safe_mapping(details)

    _raise_forbidden_fields(check, name="check")
    return check


def build_reproducibility_checklist(
    checks: Iterable[Mapping[str, Any]],
    *,
    metadata: Mapping[str, Any] | None = None,
    project_name: str = "SPY Directional Edge Research",
    checklist_version: str = "1.0",
) -> dict[str, Any]:
    """Build a reproducibility checklist dictionary from check records."""
    _validate_non_empty_string(project_name, "project_name")
    _validate_non_empty_string(checklist_version, "checklist_version")
    if metadata is not None and not isinstance(metadata, Mapping):
        raise TypeError("metadata must be a mapping when provided")

    checklist_metadata = _json_safe_mapping(metadata or {})
    checklist_metadata["checklist_version"] = checklist_version
    checklist_metadata["created_at_utc"] = _created_at_utc()
    checklist_metadata["project_name"] = project_name

    checklist = {
        "metadata": checklist_metadata,
        "checks": [
            _copy_and_validate_check_record(check, record_name=f"checks[{index}]")
            for index, check in enumerate(checks)
        ],
    }
    validate_reproducibility_checklist(checklist)
    return checklist


def check_required_metadata_keys(
    metadata: Mapping[str, Any],
    required_keys: Iterable[str],
    *,
    check_prefix: str = "metadata",
) -> list[dict[str, Any]]:
    """Create checklist records for required metadata key presence."""
    if not isinstance(metadata, Mapping):
        raise TypeError("metadata must be a mapping")
    _validate_non_empty_string(check_prefix, "check_prefix")
    keys = _normalize_required_keys(required_keys)

    return [
        create_reproducibility_check(
            check_name=f"{check_prefix}.{key}",
            passed=key in metadata,
            severity="info" if key in metadata else "warning",
            message=(
                f"Required metadata key {key!r} is present"
                if key in metadata
                else f"Required metadata key {key!r} is missing"
            ),
            details={"metadata_key": key},
        )
        for key in keys
    ]


def check_required_files(
    paths: Mapping[str, str | Path] | Iterable[str | Path],
    *,
    check_prefix: str = "file",
) -> list[dict[str, Any]]:
    """Create checklist records for required file existence without reading files."""
    _validate_non_empty_string(check_prefix, "check_prefix")
    items = _normalize_path_items(paths)

    checks = []
    for name, raw_path in items:
        path = Path(raw_path)
        exists = path.exists()
        checks.append(
            create_reproducibility_check(
                check_name=f"{check_prefix}.{name}",
                passed=exists,
                severity="info" if exists else "warning",
                message=f"Required file exists at {path}" if exists else f"Required file is missing at {path}",
                details={"path": str(path)},
            )
        )
    return checks


def build_registry_reproducibility_checklist(
    registry: Mapping[str, Any],
    *,
    required_metadata_keys: Iterable[str] | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build reproducibility checks for a run registry structure."""
    validated = validate_run_registry(deepcopy(registry))
    checks = [
        create_reproducibility_check(
            check_name="registry.has_runs",
            passed=len(validated["runs"]) > 0,
            severity="info" if validated["runs"] else "warning",
            message="Registry contains at least one run"
            if validated["runs"]
            else "Registry contains no runs",
            details={"run_count": len(validated["runs"])},
        )
    ]

    if required_metadata_keys is not None:
        checks.extend(
            check_required_metadata_keys(
                validated["metadata"],
                required_metadata_keys,
                check_prefix="registry.metadata",
            )
        )

    for index, run in enumerate(validated["runs"]):
        run_label = run.get("run_id", f"run_{index}")
        checks.extend(
            [
                create_reproducibility_check(
                    check_name=f"registry.run.{run_label}.run_id",
                    passed=bool(run.get("run_id")),
                    severity="info" if run.get("run_id") else "error",
                    message="Run record includes run_id",
                    details={"run_index": index},
                ),
                create_reproducibility_check(
                    check_name=f"registry.run.{run_label}.manifest_path",
                    passed=bool(run.get("manifest_path")),
                    severity="info" if run.get("manifest_path") else "error",
                    message="Run record includes manifest_path",
                    details={"run_index": index, "manifest_path": run.get("manifest_path")},
                ),
            ]
        )

    return build_reproducibility_checklist(
        checks,
        metadata=metadata,
    )


def build_audit_index_reproducibility_checklist(
    audit_index: Mapping[str, Any],
    *,
    required_metadata_keys: Iterable[str] | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build reproducibility checks for an audit index structure."""
    validated = validate_audit_index(deepcopy(audit_index))
    checks = [
        create_reproducibility_check(
            check_name="audit_index.has_audits",
            passed=len(validated["audits"]) > 0,
            severity="info" if validated["audits"] else "warning",
            message="Audit index contains at least one audit"
            if validated["audits"]
            else "Audit index contains no audits",
            details={"audit_count": len(validated["audits"])},
        )
    ]

    if required_metadata_keys is not None:
        checks.extend(
            check_required_metadata_keys(
                validated["metadata"],
                required_metadata_keys,
                check_prefix="audit_index.metadata",
            )
        )

    for index, audit in enumerate(validated["audits"]):
        audit_label = audit.get("audit_id", f"audit_{index}")
        checks.extend(
            [
                create_reproducibility_check(
                    check_name=f"audit_index.audit.{audit_label}.audit_id",
                    passed=bool(audit.get("audit_id")),
                    severity="info" if audit.get("audit_id") else "error",
                    message="Audit record includes audit_id",
                    details={"audit_index": index},
                ),
                create_reproducibility_check(
                    check_name=f"audit_index.audit.{audit_label}.audit_dir",
                    passed=bool(audit.get("audit_dir")),
                    severity="info" if audit.get("audit_dir") else "error",
                    message="Audit record includes audit_dir",
                    details={"audit_index": index, "audit_dir": audit.get("audit_dir")},
                ),
            ]
        )
        if "metadata_path" in audit and audit["metadata_path"] is not None:
            checks.extend(
                check_required_files(
                    {f"audit_index.audit.{audit_label}.metadata_path": audit["metadata_path"]},
                    check_prefix="file",
                )
            )
        if "table_paths" in audit and audit["table_paths"] is not None:
            checks.extend(
                check_required_files(
                    {
                        f"audit_index.audit.{audit_label}.table.{table_name}": table_path
                        for table_name, table_path in audit["table_paths"].items()
                    },
                    check_prefix="file",
                )
            )

    return build_reproducibility_checklist(
        checks,
        metadata=metadata,
    )


def summarize_reproducibility_checklist(checklist: Mapping[str, Any]) -> pd.DataFrame:
    """Return a deterministic DataFrame summary of checklist records."""
    validated = validate_reproducibility_checklist(deepcopy(checklist))
    rows = [
        {column: check.get(column) for column in CHECKLIST_SUMMARY_COLUMNS}
        for check in validated["checks"]
    ]
    summary = pd.DataFrame(rows, columns=CHECKLIST_SUMMARY_COLUMNS)
    if summary.empty:
        return summary
    return summary.sort_values("check_name", kind="mergesort").reset_index(drop=True)


def reproducibility_checklist_status(checklist: Mapping[str, Any]) -> dict[str, Any]:
    """Return pass/fail counts for checklist records."""
    validated = validate_reproducibility_checklist(deepcopy(checklist))
    checks = validated["checks"]
    passed_count = sum(1 for check in checks if check["passed"])
    failed_count = len(checks) - passed_count
    warning_count = sum(1 for check in checks if check.get("severity") == "warning")
    error_count = sum(1 for check in checks if check.get("severity") == "error")
    return {
        "check_count": len(checks),
        "passed_count": passed_count,
        "failed_count": failed_count,
        "warning_count": warning_count,
        "error_count": error_count,
        "all_passed": failed_count == 0,
    }


def write_reproducibility_checklist(
    checklist: Mapping[str, Any],
    output_path: str | Path,
    *,
    overwrite: bool = False,
) -> Path:
    """Write a validated reproducibility checklist to deterministic JSON."""
    validated = validate_reproducibility_checklist(deepcopy(checklist))
    target = Path(output_path)
    if target.exists() and not overwrite:
        raise FileExistsError(f"{target} already exists")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(validated, indent=2, sort_keys=True), encoding="utf-8")
    return target


def read_reproducibility_checklist(path: str | Path) -> dict[str, Any]:
    """Read and validate a reproducibility checklist JSON file."""
    checklist = json.loads(Path(path).read_text(encoding="utf-8"))
    validate_reproducibility_checklist(checklist)
    return checklist


def _copy_and_validate_check_record(
    record: Mapping[str, Any],
    *,
    record_name: str,
) -> dict[str, Any]:
    if not isinstance(record, Mapping):
        raise TypeError(f"{record_name} must be a mapping")
    copied = _json_safe_mapping(record)
    _validate_check_record(copied, record_name=record_name)
    return copied


def _validate_check_record(record: Any, *, record_name: str) -> None:
    if not isinstance(record, dict):
        raise TypeError(f"{record_name} must be a dict")

    missing = [field for field in ("check_name", "passed") if field not in record]
    if missing:
        raise KeyError(f"{record_name} is missing required fields: {missing}")

    _validate_non_empty_string(record["check_name"], f"{record_name}.check_name")
    if not isinstance(record["passed"], bool):
        raise TypeError(f"{record_name}.passed must be a bool")
    if "severity" in record:
        _validate_severity(record["severity"], name=f"{record_name}.severity")
    if "message" in record and record["message"] is not None:
        if not isinstance(record["message"], str):
            raise TypeError(f"{record_name}.message must be a string")
    if "details" in record and record["details"] is not None:
        if not isinstance(record["details"], dict):
            raise TypeError(f"{record_name}.details must be a dict")

    _raise_forbidden_fields(record, name=record_name)


def _normalize_required_keys(required_keys: Iterable[str]) -> list[str]:
    if isinstance(required_keys, str):
        keys = [required_keys]
    else:
        try:
            keys = list(required_keys)
        except TypeError as exc:
            raise TypeError("required_keys must be an iterable") from exc
    if not keys or not all(isinstance(key, str) and key for key in keys):
        raise ValueError("required_keys must contain at least one non-empty string")
    return sorted(keys)


def _normalize_path_items(
    paths: Mapping[str, str | Path] | Iterable[str | Path],
) -> list[tuple[str, str | Path]]:
    if isinstance(paths, Mapping):
        items = [(str(name), path) for name, path in paths.items()]
    elif isinstance(paths, (str, bytes, Path)):
        raise TypeError("paths must be a path iterable or mapping")
    else:
        try:
            items = [(Path(path).name, path) for path in paths]
        except TypeError as exc:
            raise TypeError("paths must be a path iterable or mapping") from exc

    normalized: list[tuple[str, str | Path]] = []
    for name, path in items:
        _validate_non_empty_string(name, "path name")
        if not isinstance(path, (str, Path)):
            raise TypeError(f"{name} path must be a string or Path")
        _validate_non_empty_string(str(path), f"{name} path")
        normalized.append((name, path))
    return sorted(normalized, key=lambda item: item[0])


def _validate_severity(value: Any, *, name: str = "severity") -> None:
    if not isinstance(value, str):
        raise TypeError(f"{name} must be a string")
    if value not in ALLOWED_REPRODUCIBILITY_SEVERITIES:
        raise ValueError(
            f"{name} must be one of {sorted(ALLOWED_REPRODUCIBILITY_SEVERITIES)}"
        )


def _validate_non_empty_string(value: Any, name: str) -> None:
    if not isinstance(value, str):
        raise TypeError(f"{name} must be a string")
    if not value:
        raise ValueError(f"{name} must be non-empty")


def _raise_forbidden_fields(value: Any, *, name: str) -> None:
    keys = _collect_keys(value)
    forbidden = sorted(FORBIDDEN_REPRODUCIBILITY_FIELDS.intersection(keys))
    if forbidden:
        raise KeyError(f"{name} contains forbidden research-only fields: {forbidden}")


def _collect_keys(value: Any) -> set[str]:
    keys: set[str] = set()
    if isinstance(value, Mapping):
        for key, nested in value.items():
            keys.add(str(key))
            keys.update(_collect_keys(nested))
    elif isinstance(value, list):
        for nested in value:
            keys.update(_collect_keys(nested))
    return keys

