"""Research-only reproducibility report and export helpers.

These utilities package reproducibility checklist summaries with run-registry
and audit-index structural summaries. They never read audit table contents,
manifest contents, artifact contents, outcome values, or forward-label values.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from copy import deepcopy
from pathlib import Path
from typing import Any

import pandas as pd

from spy_edge_research.backtesting.event_audit_index import summarize_audit_index
from spy_edge_research.backtesting.event_reproducibility import (
    reproducibility_checklist_status,
    summarize_reproducibility_checklist,
    validate_reproducibility_checklist,
)
from spy_edge_research.backtesting.event_run_registry import summarize_run_registry

from spy_edge_research._internal._common import (
    created_at_utc as _created_at_utc,
    dataframe_to_records as _dataframe_to_records,
    json_safe_mapping as _json_safe_mapping,
    json_safe_value as _json_safe_value,
    raise_if_exists as _raise_if_exists,
)

REPRODUCIBILITY_REPORT_TABLE_FILES: dict[str, str] = {
    "checklist_summary": "checklist_summary.csv",
    "checklist_status": "checklist_status.csv",
    "registry_audit_summary": "registry_audit_summary.csv",
    "audit_index_summary": "audit_index_summary.csv",
}

FORBIDDEN_REPRODUCIBILITY_REPORT_FIELDS: frozenset[str] = frozenset(
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


def validate_reproducibility_report_bundle(bundle: Any) -> dict[str, Any]:
    """Validate a reproducibility report/export bundle structure."""
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


def create_reproducibility_report_metadata(
    *,
    project_name: str = "SPY Directional Edge Research",
    milestone: str = "22",
    package_name: str | None = None,
    notes: str | None = None,
) -> dict[str, Any]:
    """Create metadata for reproducibility report artifacts."""
    metadata: dict[str, Any] = {
        "created_at_utc": _created_at_utc(),
        "project_name": project_name,
        "milestone": milestone,
    }
    optional = {
        "package_name": package_name,
        "notes": notes,
    }
    for key, value in optional.items():
        if value is not None:
            metadata[key] = _json_safe_value(value)

    _raise_forbidden_fields(metadata, name="reproducibility report metadata")
    return metadata


def build_reproducibility_report_bundle(
    *,
    checklist: Mapping[str, Any] | None = None,
    registry: Mapping[str, Any] | None = None,
    audit_index: Mapping[str, Any] | None = None,
    metadata: Mapping[str, Any] | None = None,
    include_checklist_summary: bool = True,
    include_checklist_status: bool = True,
    include_registry_summary: bool = True,
    include_audit_index_summary: bool = True,
) -> dict[str, Any]:
    """Build a research-only reproducibility report bundle."""
    if metadata is not None and not isinstance(metadata, Mapping):
        raise TypeError("metadata must be a mapping when provided")

    bundle_metadata = _json_safe_mapping(metadata or {})
    _raise_forbidden_fields(bundle_metadata, name="reproducibility report metadata")
    bundle_metadata["created_at_utc"] = _created_at_utc()

    tables: dict[str, pd.DataFrame] = {}

    validated_checklist: dict[str, Any] | None = None
    if checklist is not None:
        validated_checklist = validate_reproducibility_checklist(deepcopy(checklist))
        project_name = validated_checklist["metadata"].get("project_name")
        if project_name is not None and "project_name" not in bundle_metadata:
            bundle_metadata["project_name"] = _json_safe_value(project_name)

    if validated_checklist is not None and include_checklist_summary:
        tables["checklist_summary"] = summarize_reproducibility_checklist(
            validated_checklist
        ).copy(deep=True)
    if validated_checklist is not None and include_checklist_status:
        tables["checklist_status"] = pd.DataFrame(
            [reproducibility_checklist_status(validated_checklist)]
        )

    if registry is not None and include_registry_summary:
        tables["registry_audit_summary"] = summarize_run_registry(
            deepcopy(registry)
        ).copy(deep=True)

    if audit_index is not None and include_audit_index_summary:
        tables["audit_index_summary"] = summarize_audit_index(
            deepcopy(audit_index)
        ).copy(deep=True)

    bundle = {
        "metadata": bundle_metadata,
        "tables": tables,
    }
    validate_reproducibility_report_bundle(bundle)
    return bundle


def summarize_reproducibility_report_bundle(bundle: Mapping[str, Any]) -> pd.DataFrame:
    """Return a deterministic structural summary of a reproducibility report bundle."""
    validated = validate_reproducibility_report_bundle(dict(bundle))
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


def export_reproducibility_report_bundle_to_csv(
    bundle: Mapping[str, Any],
    output_dir: str | Path,
    *,
    overwrite: bool = False,
) -> dict[str, Path]:
    """Export reproducibility report tables to deterministic CSV files."""
    validated = validate_reproducibility_report_bundle(dict(bundle))
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    targets: dict[str, Path] = {
        table_name: output_path / REPRODUCIBILITY_REPORT_TABLE_FILES.get(
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


def export_reproducibility_report_bundle_to_json(
    bundle: Mapping[str, Any],
    output_path: str | Path,
    *,
    overwrite: bool = False,
) -> Path:
    """Export the full reproducibility report bundle to one records-oriented JSON file."""
    validated = validate_reproducibility_report_bundle(dict(bundle))
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


def build_and_export_reproducibility_report(
    *,
    checklist: Mapping[str, Any] | None = None,
    registry: Mapping[str, Any] | None = None,
    audit_index: Mapping[str, Any] | None = None,
    output_dir: str | Path,
    metadata: Mapping[str, Any] | None = None,
    overwrite: bool = False,
) -> dict[str, Any]:
    """Build a reproducibility report bundle, export it to CSV, and summarize it."""
    report_bundle = build_reproducibility_report_bundle(
        checklist=checklist,
        registry=registry,
        audit_index=audit_index,
        metadata=metadata,
    )
    written_paths = export_reproducibility_report_bundle_to_csv(
        report_bundle,
        output_dir,
        overwrite=overwrite,
    )
    report_summary = summarize_reproducibility_report_bundle(report_bundle)
    return {
        "report_bundle": report_bundle,
        "written_paths": written_paths,
        "report_summary": report_summary,
    }


def _raise_forbidden_fields(value: Any, *, name: str) -> None:
    keys = _collect_keys(value)
    forbidden = sorted(FORBIDDEN_REPRODUCIBILITY_REPORT_FIELDS.intersection(keys))
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

