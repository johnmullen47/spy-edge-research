"""Research-only artifact manifest and index helpers.

These utilities track files produced by research workflows. They perform
bookkeeping only: path indexing, manifest validation, JSON persistence, and
deterministic structural summaries.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

import pandas as pd

from spy_edge_research._internal._common import (
    created_at_utc as _created_at_utc,
    json_safe_mapping as _json_safe_mapping,
    json_safe_value as _json_safe_value,
)

ARTIFACT_SUMMARY_COLUMNS: tuple[str, ...] = (
    "name",
    "path",
    "artifact_type",
    "description",
    "row_count",
    "column_count",
    "created_at_utc",
)

ARTIFACT_TYPE_BY_SUFFIX: dict[str, str] = {
    ".csv": "csv_table",
    ".json": "json",
    ".png": "image",
    ".svg": "image",
    ".txt": "text",
}

REQUIRED_ARTIFACT_RECORD_FIELDS: tuple[str, ...] = (
    "name",
    "path",
    "artifact_type",
)


def validate_artifact_manifest(manifest: Any) -> dict[str, Any]:
    """Validate a research artifact manifest structure."""
    if not isinstance(manifest, dict):
        raise TypeError("manifest must be a dict")

    if "metadata" not in manifest:
        raise KeyError("manifest is missing metadata")
    if not isinstance(manifest["metadata"], dict):
        raise TypeError("manifest metadata must be a dict")

    if "artifacts" not in manifest:
        raise KeyError("manifest is missing artifacts")
    artifacts = manifest["artifacts"]
    if not isinstance(artifacts, list):
        raise TypeError("manifest artifacts must be a list")

    for index, artifact in enumerate(artifacts):
        _validate_artifact_record(artifact, record_name=f"artifacts[{index}]")

    return manifest


def create_artifact_record(
    *,
    name: str,
    path: str | Path,
    artifact_type: str,
    description: str | None = None,
    row_count: int | None = None,
    column_count: int | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Create one deterministic artifact record."""
    _validate_non_empty_string(name, "name")
    _validate_non_empty_string(str(path), "path")
    _validate_non_empty_string(artifact_type, "artifact_type")
    if description is not None and not isinstance(description, str):
        raise TypeError("description must be a string when provided")
    _validate_optional_count(row_count, "row_count")
    _validate_optional_count(column_count, "column_count")
    if metadata is not None and not isinstance(metadata, Mapping):
        raise TypeError("metadata must be a mapping when provided")

    record: dict[str, Any] = {
        "artifact_type": artifact_type,
        "created_at_utc": _created_at_utc(),
        "name": name,
        "path": str(path),
    }
    if description is not None:
        record["description"] = description
    if row_count is not None:
        record["row_count"] = row_count
    if column_count is not None:
        record["column_count"] = column_count
    if metadata is not None:
        record["metadata"] = _json_safe_mapping(metadata)

    return record


def build_artifact_manifest(
    artifact_records: Iterable[Mapping[str, Any]],
    *,
    metadata: Mapping[str, Any] | None = None,
    project_name: str = "SPY Directional Edge Research",
    manifest_version: str = "1.0",
) -> dict[str, Any]:
    """Build a manifest dictionary from artifact records."""
    _validate_non_empty_string(project_name, "project_name")
    _validate_non_empty_string(manifest_version, "manifest_version")
    if metadata is not None and not isinstance(metadata, Mapping):
        raise TypeError("metadata must be a mapping when provided")

    artifacts = [
        _copy_and_validate_artifact_record(record, record_name=f"artifact_records[{index}]")
        for index, record in enumerate(artifact_records)
    ]
    manifest_metadata = _json_safe_mapping(metadata or {})
    manifest_metadata["created_at_utc"] = _created_at_utc()
    manifest_metadata["manifest_version"] = manifest_version
    manifest_metadata["project_name"] = project_name

    manifest = {
        "metadata": manifest_metadata,
        "artifacts": artifacts,
    }
    validate_artifact_manifest(manifest)
    return manifest


def infer_artifact_type(path: str | Path) -> str:
    """Infer a simple artifact type from a path suffix."""
    suffix = Path(path).suffix.lower()
    return ARTIFACT_TYPE_BY_SUFFIX.get(suffix, "unknown")


def index_artifact_paths(
    paths: Iterable[str | Path] | Mapping[str, str | Path],
    *,
    base_dir: str | Path | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Create artifact records from path lists or name-to-path mappings."""
    if metadata is not None and not isinstance(metadata, Mapping):
        raise TypeError("metadata must be a mapping when provided")

    if isinstance(paths, Mapping):
        items = paths.items()
    elif isinstance(paths, (str, bytes, Path)):
        raise TypeError("paths must be a path iterable or mapping")
    else:
        items = ((Path(path).stem, path) for path in paths)

    return [
        create_artifact_record(
            name=str(name),
            path=_format_artifact_path(path, base_dir=base_dir),
            artifact_type=infer_artifact_type(path),
            metadata=metadata,
        )
        for name, path in items
    ]


def write_artifact_manifest(
    manifest: Mapping[str, Any],
    output_path: str | Path,
    *,
    overwrite: bool = False,
) -> Path:
    """Write a validated manifest to deterministic JSON."""
    validated = validate_artifact_manifest(dict(manifest))
    target = Path(output_path)
    if target.exists() and not overwrite:
        raise FileExistsError(f"{target} already exists")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(validated, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return target


def read_artifact_manifest(path: str | Path) -> dict[str, Any]:
    """Read and validate a manifest JSON file."""
    manifest = json.loads(Path(path).read_text(encoding="utf-8"))
    validate_artifact_manifest(manifest)
    return manifest


def summarize_artifact_manifest(manifest: Mapping[str, Any]) -> pd.DataFrame:
    """Return a deterministic DataFrame summary of artifact records."""
    validated = validate_artifact_manifest(dict(manifest))
    rows = [
        {column: artifact.get(column) for column in ARTIFACT_SUMMARY_COLUMNS}
        for artifact in validated["artifacts"]
    ]
    summary = pd.DataFrame(rows, columns=ARTIFACT_SUMMARY_COLUMNS)
    if summary.empty:
        return summary
    return summary.sort_values("name", kind="mergesort").reset_index(drop=True)


def build_manifest_from_written_paths(
    written_paths: Mapping[str, Any],
    *,
    metadata: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a manifest from output-path dictionaries returned by exporters."""
    if not isinstance(written_paths, Mapping):
        raise TypeError("written_paths must be a mapping")
    records = index_artifact_paths(
        _flatten_path_mapping(written_paths),
        metadata={"source": "written_paths"},
    )
    return build_artifact_manifest(records, metadata=metadata)


def _copy_and_validate_artifact_record(
    record: Mapping[str, Any],
    *,
    record_name: str,
) -> dict[str, Any]:
    if not isinstance(record, Mapping):
        raise TypeError(f"{record_name} must be a mapping")
    copied = {str(key): _json_safe_value(value) for key, value in record.items()}
    _validate_artifact_record(copied, record_name=record_name)
    return copied


def _validate_artifact_record(record: Any, *, record_name: str) -> None:
    if not isinstance(record, dict):
        raise TypeError(f"{record_name} must be a dict")

    missing = [field for field in REQUIRED_ARTIFACT_RECORD_FIELDS if field not in record]
    if missing:
        raise KeyError(f"{record_name} is missing required fields: {missing}")

    _validate_non_empty_string(record["name"], f"{record_name}.name")
    _validate_non_empty_string(record["path"], f"{record_name}.path")
    _validate_non_empty_string(record["artifact_type"], f"{record_name}.artifact_type")
    _validate_optional_count(record.get("row_count"), f"{record_name}.row_count")
    _validate_optional_count(record.get("column_count"), f"{record_name}.column_count")

    if "description" in record and record["description"] is not None:
        if not isinstance(record["description"], str):
            raise TypeError(f"{record_name}.description must be a string")
    if "metadata" in record and record["metadata"] is not None:
        if not isinstance(record["metadata"], dict):
            raise TypeError(f"{record_name}.metadata must be a dict")
    if "created_at_utc" in record and record["created_at_utc"] is not None:
        if not isinstance(record["created_at_utc"], str):
            raise TypeError(f"{record_name}.created_at_utc must be a string")


def _validate_optional_count(value: Any, name: str) -> None:
    if value is None:
        return
    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError(f"{name} must be an integer when provided")
    if value < 0:
        raise ValueError(f"{name} must be non-negative")


def _validate_non_empty_string(value: Any, name: str) -> None:
    if not isinstance(value, str):
        raise TypeError(f"{name} must be a string")
    if not value:
        raise ValueError(f"{name} must be non-empty")


def _format_artifact_path(path: str | Path, *, base_dir: str | Path | None) -> str:
    path_obj = Path(path)
    if base_dir is None:
        return str(path_obj)

    try:
        return str(path_obj.relative_to(Path(base_dir)))
    except ValueError:
        return str(path_obj)


def _flatten_path_mapping(paths: Mapping[str, Any], *, prefix: str = "") -> dict[str, str | Path]:
    flattened: dict[str, str | Path] = {}
    for name, value in paths.items():
        key = f"{prefix}.{name}" if prefix else str(name)
        if isinstance(value, Mapping):
            flattened.update(_flatten_path_mapping(value, prefix=key))
        elif isinstance(value, (str, Path)):
            flattened[key] = value
        else:
            raise TypeError(f"written path for {key} must be a string, Path, or mapping")
    return flattened

