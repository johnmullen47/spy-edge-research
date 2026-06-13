"""Research-only package manifest helpers."""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

PACKAGE_MANIFEST_RECORD_COLUMNS: list[str] = [
    "package_id",
    "artifact_name",
    "artifact_path",
    "artifact_type",
    "description",
    "required",
    "metadata",
]


def create_research_package_manifest_record(
    *,
    package_id: str,
    artifact_name: str,
    artifact_path: str | Path,
    artifact_type: str,
    description: str = "",
    required: bool = True,
    metadata: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Create one research package manifest record."""
    for value, name in [
        (package_id, "package_id"),
        (artifact_name, "artifact_name"),
        (str(artifact_path), "artifact_path"),
        (artifact_type, "artifact_type"),
    ]:
        _validate_non_empty_string(value, name)
    if not isinstance(required, bool):
        raise TypeError("required must be a bool")
    return {
        "package_id": package_id,
        "artifact_name": artifact_name,
        "artifact_path": str(artifact_path),
        "artifact_type": artifact_type,
        "description": description,
        "required": required,
        "metadata": dict(metadata or {}),
    }


def build_research_package_manifest(
    records: Iterable[Mapping[str, Any]],
    *,
    metadata: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a research package manifest dictionary."""
    normalized = [_validate_manifest_record(record) for record in records]
    manifest = {
        "metadata": {
            "created_at_utc": datetime.now(UTC).replace(microsecond=0).isoformat(),
            "manifest_caveat": "research_package_manifest_is_not_deployment_bundle",
            **dict(metadata or {}),
        },
        "artifacts": normalized,
    }
    return validate_research_package_manifest(manifest)


def validate_research_package_manifest(manifest: Any) -> dict[str, Any]:
    """Validate research package manifest structure."""
    if not isinstance(manifest, dict):
        raise TypeError("manifest must be a dict")
    if not isinstance(manifest.get("metadata"), dict):
        raise TypeError("manifest metadata must be a dict")
    if not isinstance(manifest.get("artifacts"), list):
        raise TypeError("manifest artifacts must be a list")
    for record in manifest["artifacts"]:
        _validate_manifest_record(record)
    return manifest


def summarize_research_package_manifest(manifest: Mapping[str, Any]) -> pd.DataFrame:
    """Summarize manifest artifacts."""
    validated = validate_research_package_manifest(dict(manifest))
    table = pd.DataFrame(validated["artifacts"], columns=PACKAGE_MANIFEST_RECORD_COLUMNS)
    if table.empty:
        return pd.DataFrame(
            columns=[
                "artifact_type",
                "artifact_count",
                "required_artifact_count",
                "summary_caveat",
            ]
        )
    return (
        table.groupby("artifact_type", dropna=False, sort=True)
        .agg(
            artifact_count=("artifact_name", "count"),
            required_artifact_count=("required", "sum"),
        )
        .reset_index()
        .assign(summary_caveat="manifest_summary_is_research_inventory_only")
    )


def write_research_package_manifest(
    manifest: Mapping[str, Any],
    output_path: str | Path,
    *,
    overwrite: bool = False,
) -> Path:
    """Write manifest JSON."""
    validated = validate_research_package_manifest(dict(manifest))
    target = Path(output_path)
    if target.exists() and not overwrite:
        raise FileExistsError(f"{target} already exists")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(validated, indent=2, sort_keys=True), encoding="utf-8")
    return target


def read_research_package_manifest(path: str | Path) -> dict[str, Any]:
    """Read manifest JSON."""
    return validate_research_package_manifest(json.loads(Path(path).read_text(encoding="utf-8")))


def _validate_manifest_record(record: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(record, Mapping):
        raise TypeError("manifest record must be a mapping")
    missing = [column for column in PACKAGE_MANIFEST_RECORD_COLUMNS if column not in record]
    if missing:
        raise KeyError(f"manifest record is missing required fields: {missing}")
    normalized = {column: record[column] for column in PACKAGE_MANIFEST_RECORD_COLUMNS}
    for field in ("package_id", "artifact_name", "artifact_path", "artifact_type"):
        _validate_non_empty_string(normalized[field], field)
    if not isinstance(normalized["required"], bool):
        raise TypeError("required must be a bool")
    if not isinstance(normalized["metadata"], Mapping):
        raise TypeError("metadata must be a mapping")
    normalized["metadata"] = dict(normalized["metadata"])
    return normalized


def _validate_non_empty_string(value: Any, name: str) -> None:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{name} must be a non-empty string")
