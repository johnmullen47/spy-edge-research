"""Research-only registry audit and export helpers.

These utilities package run-registry inventory and metadata-consistency tables
for reproducible review. They consume registry structures only and do not read
artifact file contents, rank runs, optimize thresholds, create trade signals,
simulate P/L, or claim edge.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from copy import deepcopy
from pathlib import Path
from typing import Any

import pandas as pd

from spy_edge_research.backtesting.event_run_registry import (
    summarize_registry_artifacts,
    summarize_run_registry,
    validate_run_metadata_consistency,
    validate_run_registry,
)

from spy_edge_research._internal._common import (
    created_at_utc as _created_at_utc,
    dataframe_to_records as _dataframe_to_records,
    json_safe_mapping as _json_safe_mapping,
    json_safe_value as _json_safe_value,
    raise_if_exists as _raise_if_exists,
)

REGISTRY_AUDIT_TABLE_FILES: dict[str, str] = {
    "run_summary": "run_summary.csv",
    "artifact_summary": "artifact_summary.csv",
    "metadata_consistency": "metadata_consistency.csv",
}

FORBIDDEN_AUDIT_METADATA_FIELDS: frozenset[str] = frozenset(
    {
        "best_run",
        "best_event",
        "selected_event",
        "rank",
        "score",
        "confidence",
        "edge",
        "p_l",
        "pnl",
        "profit",
    }
)


def validate_registry_audit_bundle(bundle: Any) -> dict[str, Any]:
    """Validate a registry audit/export bundle structure."""
    if not isinstance(bundle, dict):
        raise TypeError("bundle must be a dict")

    if "metadata" not in bundle:
        raise KeyError("bundle is missing metadata")
    if not isinstance(bundle["metadata"], dict):
        raise TypeError("bundle metadata must be a dict")

    if "tables" not in bundle:
        raise KeyError("bundle is missing tables")
    if not isinstance(bundle["tables"], dict):
        raise TypeError("bundle tables must be a dict")

    for table_name, table in bundle["tables"].items():
        if not isinstance(table_name, str) or not table_name:
            raise ValueError("bundle table names must be non-empty strings")
        if not isinstance(table, pd.DataFrame):
            raise TypeError(f"{table_name} must be a pandas DataFrame")

    return bundle


def build_registry_audit_bundle(
    registry: Mapping[str, Any],
    *,
    required_metadata_keys: Iterable[str] | None = None,
    metadata: Mapping[str, Any] | None = None,
    include_run_summary: bool = True,
    include_artifact_summary: bool = True,
    include_metadata_consistency: bool = True,
) -> dict[str, Any]:
    """Build a research-only audit bundle from a run registry."""
    registry_copy = deepcopy(registry)
    validated = validate_run_registry(registry_copy)
    if metadata is not None and not isinstance(metadata, Mapping):
        raise TypeError("metadata must be a mapping when provided")

    bundle_metadata = _json_safe_mapping(metadata or {})
    bundle_metadata["created_at_utc"] = _created_at_utc()
    project_name = validated["metadata"].get("project_name")
    if project_name is not None and "project_name" not in bundle_metadata:
        bundle_metadata["project_name"] = _json_safe_value(project_name)

    tables: dict[str, pd.DataFrame] = {}
    if include_run_summary:
        tables["run_summary"] = summarize_run_registry(validated).copy(deep=True)
    if include_artifact_summary:
        tables["artifact_summary"] = summarize_registry_artifacts(validated).copy(deep=True)
    if include_metadata_consistency:
        tables["metadata_consistency"] = validate_run_metadata_consistency(
            validated,
            required_metadata_keys=required_metadata_keys,
        ).copy(deep=True)

    bundle = {
        "metadata": bundle_metadata,
        "tables": tables,
    }
    validate_registry_audit_bundle(bundle)
    return bundle


def summarize_registry_audit_bundle(bundle: Mapping[str, Any]) -> pd.DataFrame:
    """Return a deterministic structural summary of an audit bundle."""
    validated = validate_registry_audit_bundle(dict(bundle))
    rows = [
        {
            "table_name": table_name,
            "row_count": len(table),
            "column_count": len(table.columns),
            "columns": list(table.columns),
        }
        for table_name, table in validated["tables"].items()
    ]
    summary = pd.DataFrame(
        rows,
        columns=["table_name", "row_count", "column_count", "columns"],
    )
    if summary.empty:
        return summary
    return summary.sort_values("table_name", kind="mergesort").reset_index(drop=True)


def export_registry_audit_bundle_to_csv(
    bundle: Mapping[str, Any],
    output_dir: str | Path,
    *,
    overwrite: bool = False,
) -> dict[str, Path]:
    """Export registry-audit tables to deterministic CSV files."""
    validated = validate_registry_audit_bundle(dict(bundle))
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    targets: dict[str, Path] = {
        table_name: output_path / REGISTRY_AUDIT_TABLE_FILES.get(
            table_name,
            f"{table_name}.csv",
        )
        for table_name in validated["tables"]
    }
    targets["metadata"] = output_path / "metadata.json"
    _raise_if_exists(targets.values(), overwrite=overwrite)

    written: dict[str, Path] = {}
    for table_name, table in validated["tables"].items():
        target = targets[table_name]
        table.to_csv(target, index=False)
        written[table_name] = target

    metadata_target = targets["metadata"]
    metadata_target.write_text(
        json.dumps(_json_safe_mapping(validated["metadata"]), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    written["metadata"] = metadata_target
    return written


def export_registry_audit_bundle_to_json(
    bundle: Mapping[str, Any],
    output_path: str | Path,
    *,
    overwrite: bool = False,
) -> Path:
    """Export the full registry audit bundle to one records-oriented JSON file."""
    validated = validate_registry_audit_bundle(dict(bundle))
    target = Path(output_path)
    if target.exists() and not overwrite:
        raise FileExistsError(f"{target} already exists")
    target.parent.mkdir(parents=True, exist_ok=True)

    payload = {
        "metadata": _json_safe_mapping(validated["metadata"]),
        "tables": {
            table_name: _dataframe_to_records(table)
            for table_name, table in validated["tables"].items()
        },
    }
    target.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return target


def create_registry_audit_metadata(
    *,
    project_name: str = "SPY Directional Edge Research",
    milestone: str = "18",
    registry_name: str | None = None,
    notes: str | None = None,
) -> dict[str, Any]:
    """Create metadata for registry audit artifacts."""
    metadata: dict[str, Any] = {
        "created_at_utc": _created_at_utc(),
        "project_name": project_name,
        "milestone": milestone,
    }
    optional = {
        "registry_name": registry_name,
        "notes": notes,
    }
    for key, value in optional.items():
        if value is not None:
            metadata[key] = _json_safe_value(value)

    forbidden = sorted(FORBIDDEN_AUDIT_METADATA_FIELDS.intersection(metadata))
    if forbidden:
        raise KeyError(f"registry audit metadata contains forbidden fields: {forbidden}")
    return metadata


def build_and_export_registry_audit(
    registry: Mapping[str, Any],
    output_dir: str | Path,
    *,
    required_metadata_keys: Iterable[str] | None = None,
    metadata: Mapping[str, Any] | None = None,
    overwrite: bool = False,
) -> dict[str, Any]:
    """Build a registry audit bundle, export it to CSV, and summarize it."""
    audit_bundle = build_registry_audit_bundle(
        registry,
        required_metadata_keys=required_metadata_keys,
        metadata=metadata,
    )
    written_paths = export_registry_audit_bundle_to_csv(
        audit_bundle,
        output_dir,
        overwrite=overwrite,
    )
    audit_summary = summarize_registry_audit_bundle(audit_bundle)
    return {
        "audit_bundle": audit_bundle,
        "written_paths": written_paths,
        "audit_summary": audit_summary,
    }

