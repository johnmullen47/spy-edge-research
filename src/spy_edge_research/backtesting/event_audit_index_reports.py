"""Research-only audit-index report and comparison helpers.

These utilities export audit-index summaries and compare audit-index structure
reproducibly. They consume audit index structures only and never read audit
table contents, artifact contents, outcome values, or forward-label values.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from copy import deepcopy
from pathlib import Path
from typing import Any

import pandas as pd

from spy_edge_research.backtesting.event_audit_index import (
    summarize_audit_index,
    summarize_audit_tables,
    validate_audit_index,
)

from spy_edge_research._internal._common import (
    created_at_utc as _created_at_utc,
    dataframe_to_records as _dataframe_to_records,
    json_safe_mapping as _json_safe_mapping,
    json_safe_value as _json_safe_value,
    raise_if_exists as _raise_if_exists,
)

AUDIT_INDEX_REPORT_TABLE_FILES: dict[str, str] = {
    "audit_summary": "audit_summary.csv",
    "audit_tables": "audit_tables.csv",
    "comparison_summary": "comparison_summary.csv",
}

FORBIDDEN_AUDIT_INDEX_REPORT_FIELDS: frozenset[str] = frozenset(
    {
        "best_audit",
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


def validate_audit_index_report_bundle(bundle: Any) -> dict[str, Any]:
    """Validate an audit-index report/export bundle structure."""
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


def create_audit_index_report_metadata(
    *,
    project_name: str = "SPY Directional Edge Research",
    milestone: str = "20",
    index_name: str | None = None,
    notes: str | None = None,
) -> dict[str, Any]:
    """Create metadata for audit-index report artifacts."""
    metadata: dict[str, Any] = {
        "created_at_utc": _created_at_utc(),
        "project_name": project_name,
        "milestone": milestone,
    }
    optional = {
        "index_name": index_name,
        "notes": notes,
    }
    for key, value in optional.items():
        if value is not None:
            metadata[key] = _json_safe_value(value)

    forbidden = sorted(FORBIDDEN_AUDIT_INDEX_REPORT_FIELDS.intersection(metadata))
    if forbidden:
        raise KeyError(f"audit-index report metadata contains forbidden fields: {forbidden}")
    return metadata


def build_audit_index_report_bundle(
    audit_index: Mapping[str, Any],
    *,
    metadata: Mapping[str, Any] | None = None,
    include_audit_summary: bool = True,
    include_audit_tables: bool = True,
) -> dict[str, Any]:
    """Build a research-only report bundle from one audit index."""
    audit_index_copy = deepcopy(audit_index)
    validated = validate_audit_index(audit_index_copy)
    if metadata is not None and not isinstance(metadata, Mapping):
        raise TypeError("metadata must be a mapping when provided")

    bundle_metadata = _json_safe_mapping(metadata or {})
    bundle_metadata["created_at_utc"] = _created_at_utc()
    project_name = validated["metadata"].get("project_name")
    if project_name is not None and "project_name" not in bundle_metadata:
        bundle_metadata["project_name"] = _json_safe_value(project_name)

    tables: dict[str, pd.DataFrame] = {}
    if include_audit_summary:
        tables["audit_summary"] = summarize_audit_index(validated).copy(deep=True)
    if include_audit_tables:
        tables["audit_tables"] = summarize_audit_tables(validated).copy(deep=True)

    bundle = {
        "metadata": bundle_metadata,
        "tables": tables,
    }
    validate_audit_index_report_bundle(bundle)
    return bundle


def summarize_audit_index_report_bundle(bundle: Mapping[str, Any]) -> pd.DataFrame:
    """Return a deterministic structural summary of an audit-index report bundle."""
    validated = validate_audit_index_report_bundle(dict(bundle))
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


def compare_audit_indexes_structure(
    left_index: Mapping[str, Any],
    right_index: Mapping[str, Any],
    *,
    left_name: str = "left",
    right_name: str = "right",
) -> pd.DataFrame:
    """Compare two audit indexes structurally without reading table contents."""
    _validate_non_empty_string(left_name, "left_name")
    _validate_non_empty_string(right_name, "right_name")
    left = validate_audit_index(deepcopy(left_index))
    right = validate_audit_index(deepcopy(right_index))

    rows = [
        {
            "comparison_key": "audit_count",
            "left_value": len(left["audits"]),
            "right_value": len(right["audits"]),
        },
        {
            "comparison_key": "audit_ids",
            "left_value": _audit_ids(left),
            "right_value": _audit_ids(right),
        },
        {
            "comparison_key": "table_names",
            "left_value": _table_names(left),
            "right_value": _table_names(right),
        },
        {
            "comparison_key": "table_path_count",
            "left_value": _table_path_count(left),
            "right_value": _table_path_count(right),
        },
    ]
    for row in rows:
        row["matches"] = row["left_value"] == row["right_value"]

    comparison = pd.DataFrame(
        rows,
        columns=["comparison_key", "left_value", "right_value", "matches"],
    )
    comparison.attrs["left_name"] = left_name
    comparison.attrs["right_name"] = right_name
    return comparison.sort_values("comparison_key", kind="mergesort").reset_index(drop=True)


def build_audit_index_comparison_bundle(
    left_index: Mapping[str, Any],
    right_index: Mapping[str, Any],
    *,
    left_name: str = "left",
    right_name: str = "right",
    metadata: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a report bundle containing a structural comparison table."""
    if metadata is not None and not isinstance(metadata, Mapping):
        raise TypeError("metadata must be a mapping when provided")

    bundle_metadata = _json_safe_mapping(metadata or {})
    bundle_metadata["created_at_utc"] = _created_at_utc()
    bundle_metadata["left_name"] = _json_safe_value(left_name)
    bundle_metadata["right_name"] = _json_safe_value(right_name)

    bundle = {
        "metadata": bundle_metadata,
        "tables": {
            "comparison_summary": compare_audit_indexes_structure(
                left_index,
                right_index,
                left_name=left_name,
                right_name=right_name,
            )
        },
    }
    validate_audit_index_report_bundle(bundle)
    return bundle


def export_audit_index_report_bundle_to_csv(
    bundle: Mapping[str, Any],
    output_dir: str | Path,
    *,
    overwrite: bool = False,
) -> dict[str, Path]:
    """Export audit-index report tables to deterministic CSV files."""
    validated = validate_audit_index_report_bundle(dict(bundle))
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    targets: dict[str, Path] = {
        table_name: output_path / AUDIT_INDEX_REPORT_TABLE_FILES.get(
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


def export_audit_index_report_bundle_to_json(
    bundle: Mapping[str, Any],
    output_path: str | Path,
    *,
    overwrite: bool = False,
) -> Path:
    """Export the full audit-index report bundle to one records-oriented JSON file."""
    validated = validate_audit_index_report_bundle(dict(bundle))
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


def build_and_export_audit_index_report(
    audit_index: Mapping[str, Any],
    output_dir: str | Path,
    *,
    metadata: Mapping[str, Any] | None = None,
    overwrite: bool = False,
) -> dict[str, Any]:
    """Build an audit-index report bundle, export it to CSV, and summarize it."""
    report_bundle = build_audit_index_report_bundle(
        audit_index,
        metadata=metadata,
    )
    written_paths = export_audit_index_report_bundle_to_csv(
        report_bundle,
        output_dir,
        overwrite=overwrite,
    )
    report_summary = summarize_audit_index_report_bundle(report_bundle)
    return {
        "report_bundle": report_bundle,
        "written_paths": written_paths,
        "report_summary": report_summary,
    }


def _audit_ids(index: Mapping[str, Any]) -> list[str]:
    return sorted(audit["audit_id"] for audit in index["audits"])


def _table_names(index: Mapping[str, Any]) -> list[str]:
    return sorted(
        {
            table_name
            for audit in index["audits"]
            for table_name in audit.get("table_paths", {})
        }
    )


def _table_path_count(index: Mapping[str, Any]) -> int:
    return sum(len(audit.get("table_paths", {})) for audit in index["audits"])


def _validate_non_empty_string(value: Any, name: str) -> None:
    if not isinstance(value, str):
        raise TypeError(f"{name} must be a string")
    if not value:
        raise ValueError(f"{name} must be non-empty")
