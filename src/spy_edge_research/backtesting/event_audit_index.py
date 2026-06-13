"""Research-only audit export index helpers.

These utilities locate exported registry-audit bundles and track their metadata
and known table file paths. They read metadata JSON only and never inspect audit
table contents or artifact contents.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from copy import deepcopy
from pathlib import Path
from typing import Any

import pandas as pd

from spy_edge_research._internal._common import (
    created_at_utc as _created_at_utc,
    json_safe_mapping as _json_safe_mapping,
    json_safe_value as _json_safe_value,
)

AUDIT_INDEX_TABLE_FILES: dict[str, str] = {
    "run_summary": "run_summary.csv",
    "artifact_summary": "artifact_summary.csv",
    "metadata_consistency": "metadata_consistency.csv",
}

AUDIT_INDEX_SUMMARY_COLUMNS: tuple[str, ...] = (
    "audit_id",
    "audit_dir",
    "metadata_path",
    "table_count",
    "table_names",
    "created_at_utc",
    "metadata_keys",
)

AUDIT_INDEX_TABLE_COLUMNS: tuple[str, ...] = (
    "audit_id",
    "table_name",
    "table_path",
)

REQUIRED_AUDIT_RECORD_FIELDS: tuple[str, ...] = (
    "audit_id",
    "audit_dir",
)


def validate_audit_index(index: Any) -> dict[str, Any]:
    """Validate a research audit index structure."""
    if not isinstance(index, dict):
        raise TypeError("index must be a dict")

    if "metadata" not in index:
        raise KeyError("index is missing metadata")
    if not isinstance(index["metadata"], dict):
        raise TypeError("index metadata must be a dict")

    if "audits" not in index:
        raise KeyError("index is missing audits")
    audits = index["audits"]
    if not isinstance(audits, list):
        raise TypeError("index audits must be a list")

    seen_audit_ids: set[str] = set()
    for audit_index, audit in enumerate(audits):
        _validate_audit_record(audit, record_name=f"audits[{audit_index}]")
        audit_id = audit["audit_id"]
        if audit_id in seen_audit_ids:
            raise ValueError(f"index contains duplicate audit_id: {audit_id}")
        seen_audit_ids.add(audit_id)

    return index


def create_audit_record(
    *,
    audit_id: str,
    audit_dir: str | Path,
    metadata_path: str | Path | None = None,
    table_paths: Mapping[str, str | Path] | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Create one audit export index record."""
    _validate_non_empty_string(audit_id, "audit_id")
    _validate_non_empty_string(str(audit_dir), "audit_dir")
    if metadata_path is not None:
        _validate_non_empty_string(str(metadata_path), "metadata_path")
    if table_paths is not None and not isinstance(table_paths, Mapping):
        raise TypeError("table_paths must be a mapping when provided")
    if metadata is not None and not isinstance(metadata, Mapping):
        raise TypeError("metadata must be a mapping when provided")

    record: dict[str, Any] = {
        "audit_dir": str(audit_dir),
        "audit_id": audit_id,
        "created_at_utc": _created_at_utc(),
    }
    if metadata_path is not None:
        record["metadata_path"] = str(metadata_path)
    if table_paths is not None:
        record["table_paths"] = _validate_and_copy_table_paths(table_paths)
    if metadata is not None:
        record["metadata"] = _json_safe_mapping(metadata)

    _validate_audit_record(record, record_name="audit_record")
    return record


def build_audit_index(
    audit_records: Iterable[Mapping[str, Any]],
    *,
    metadata: Mapping[str, Any] | None = None,
    project_name: str = "SPY Directional Edge Research",
    index_version: str = "1.0",
) -> dict[str, Any]:
    """Build an audit index dictionary from audit records."""
    _validate_non_empty_string(project_name, "project_name")
    _validate_non_empty_string(index_version, "index_version")
    if metadata is not None and not isinstance(metadata, Mapping):
        raise TypeError("metadata must be a mapping when provided")

    audits = [
        _copy_and_validate_audit_record(record, record_name=f"audit_records[{index}]")
        for index, record in enumerate(audit_records)
    ]
    index_metadata = _json_safe_mapping(metadata or {})
    index_metadata["created_at_utc"] = _created_at_utc()
    index_metadata["index_version"] = index_version
    index_metadata["project_name"] = project_name

    audit_index = {
        "metadata": index_metadata,
        "audits": audits,
    }
    validate_audit_index(audit_index)
    return audit_index


def discover_audit_export_dirs(
    root_dir: str | Path,
    *,
    metadata_filename: str = "metadata.json",
) -> list[Path]:
    """Find audit export directories containing a metadata JSON filename."""
    _validate_non_empty_string(metadata_filename, "metadata_filename")
    root_path = Path(root_dir)
    if not root_path.exists():
        raise FileNotFoundError(f"{root_path} does not exist")
    return sorted(
        {path.parent for path in root_path.glob(f"**/{metadata_filename}")},
        key=lambda path: str(path),
    )


def index_audit_export_dir(
    audit_dir: str | Path,
    *,
    audit_id: str | None = None,
    metadata_filename: str = "metadata.json",
) -> dict[str, Any]:
    """Create an audit index record from one exported audit directory."""
    _validate_non_empty_string(metadata_filename, "metadata_filename")
    audit_path = Path(audit_dir)
    record_audit_id = audit_id if audit_id is not None else audit_path.name
    _validate_non_empty_string(record_audit_id, "audit_id")

    metadata_path = audit_path / metadata_filename
    table_paths = {
        table_name: table_path
        for table_name, filename in AUDIT_INDEX_TABLE_FILES.items()
        if (table_path := audit_path / filename).exists()
    }
    return create_audit_record(
        audit_id=record_audit_id,
        audit_dir=audit_path,
        metadata_path=metadata_path if metadata_path.exists() else None,
        table_paths=table_paths,
    )


def load_audit_metadata(metadata_path: str | Path) -> dict[str, Any]:
    """Load one audit export metadata JSON file."""
    path = Path(metadata_path)
    if not path.exists():
        raise FileNotFoundError(f"{path} does not exist")
    try:
        metadata = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"{path} does not contain valid JSON") from exc
    if not isinstance(metadata, dict):
        raise TypeError("audit metadata must be a dict")
    return metadata


def load_audit_index_from_dirs(
    audit_dirs: Iterable[str | Path],
    *,
    load_metadata: bool = True,
) -> dict[str, Any]:
    """Build a deterministic audit index from audit export directories."""
    records = []
    for audit_dir in audit_dirs:
        record = index_audit_export_dir(audit_dir)
        metadata_path = record.get("metadata_path")
        if load_metadata and isinstance(metadata_path, str):
            record["metadata"] = load_audit_metadata(metadata_path)
        records.append(record)

    records = sorted(records, key=lambda record: record["audit_id"])
    return build_audit_index(records)


def summarize_audit_index(index: Mapping[str, Any]) -> pd.DataFrame:
    """Return a deterministic DataFrame summary of audit index records."""
    validated = validate_audit_index(deepcopy(index))
    rows = []
    for audit in validated["audits"]:
        table_paths = audit.get("table_paths", {})
        metadata = audit.get("metadata", {})
        rows.append(
            {
                "audit_id": audit["audit_id"],
                "audit_dir": audit["audit_dir"],
                "metadata_path": audit.get("metadata_path"),
                "table_count": len(table_paths),
                "table_names": sorted(table_paths.keys()),
                "created_at_utc": audit.get("created_at_utc"),
                "metadata_keys": sorted(metadata.keys()) if isinstance(metadata, dict) else [],
            }
        )

    summary = pd.DataFrame(rows, columns=AUDIT_INDEX_SUMMARY_COLUMNS)
    if summary.empty:
        return summary
    return summary.sort_values("audit_id", kind="mergesort").reset_index(drop=True)


def summarize_audit_tables(index: Mapping[str, Any]) -> pd.DataFrame:
    """Return one structural row per indexed audit table path."""
    validated = validate_audit_index(deepcopy(index))
    rows = [
        {
            "audit_id": audit["audit_id"],
            "table_name": table_name,
            "table_path": table_path,
        }
        for audit in validated["audits"]
        for table_name, table_path in audit.get("table_paths", {}).items()
    ]
    summary = pd.DataFrame(rows, columns=AUDIT_INDEX_TABLE_COLUMNS)
    if summary.empty:
        return summary
    return summary.sort_values(["audit_id", "table_name"], kind="mergesort").reset_index(
        drop=True
    )


def write_audit_index(
    index: Mapping[str, Any],
    output_path: str | Path,
    *,
    overwrite: bool = False,
) -> Path:
    """Write a validated audit index to deterministic JSON."""
    validated = validate_audit_index(deepcopy(index))
    target = Path(output_path)
    if target.exists() and not overwrite:
        raise FileExistsError(f"{target} already exists")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(validated, indent=2, sort_keys=True), encoding="utf-8")
    return target


def read_audit_index(path: str | Path) -> dict[str, Any]:
    """Read and validate an audit index JSON file."""
    index = json.loads(Path(path).read_text(encoding="utf-8"))
    validate_audit_index(index)
    return index


def _copy_and_validate_audit_record(
    record: Mapping[str, Any],
    *,
    record_name: str,
) -> dict[str, Any]:
    if not isinstance(record, Mapping):
        raise TypeError(f"{record_name} must be a mapping")
    copied = {str(key): _json_safe_value(value) for key, value in record.items()}
    _validate_audit_record(copied, record_name=record_name)
    return copied


def _validate_audit_record(record: Any, *, record_name: str) -> None:
    if not isinstance(record, dict):
        raise TypeError(f"{record_name} must be a dict")

    missing = [field for field in REQUIRED_AUDIT_RECORD_FIELDS if field not in record]
    if missing:
        raise KeyError(f"{record_name} is missing required fields: {missing}")

    _validate_non_empty_string(record["audit_id"], f"{record_name}.audit_id")
    _validate_non_empty_string(record["audit_dir"], f"{record_name}.audit_dir")
    if "created_at_utc" in record and record["created_at_utc"] is not None:
        if not isinstance(record["created_at_utc"], str):
            raise TypeError(f"{record_name}.created_at_utc must be a string")
    if "metadata_path" in record and record["metadata_path"] is not None:
        _validate_non_empty_string(record["metadata_path"], f"{record_name}.metadata_path")
    if "table_paths" in record and record["table_paths"] is not None:
        if not isinstance(record["table_paths"], dict):
            raise TypeError(f"{record_name}.table_paths must be a dict")
        _validate_and_copy_table_paths(record["table_paths"], name=f"{record_name}.table_paths")
    if "metadata" in record and record["metadata"] is not None:
        if not isinstance(record["metadata"], dict):
            raise TypeError(f"{record_name}.metadata must be a dict")


def _validate_and_copy_table_paths(
    table_paths: Mapping[str, str | Path],
    *,
    name: str = "table_paths",
) -> dict[str, str]:
    copied: dict[str, str] = {}
    for table_name, table_path in table_paths.items():
        _validate_non_empty_string(str(table_name), f"{name} key")
        if not isinstance(table_path, (str, Path)):
            raise TypeError(f"{name}.{table_name} must be a string or Path")
        _validate_non_empty_string(str(table_path), f"{name}.{table_name}")
        copied[str(table_name)] = str(table_path)
    return copied


def _validate_non_empty_string(value: Any, name: str) -> None:
    if not isinstance(value, str):
        raise TypeError(f"{name} must be a string")
    if not value:
        raise ValueError(f"{name} must be non-empty")

