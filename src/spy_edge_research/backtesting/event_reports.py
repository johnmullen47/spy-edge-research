"""Research-only reporting and export helpers for event-study outputs.

These utilities package existing event-study and diagnostic tables into stable
research artifacts. They do not create causal features, trade signals,
rankings, optimizations, or edge claims.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from spy_edge_research._internal._common import (
    dataframe_to_records as _dataframe_to_records,
    json_safe_mapping as _json_safe_mapping,
    json_safe_value as _json_safe_value,
    normalize_columns as _normalize_columns,
    raise_if_exists as _raise_if_exists,
)


def _require_columns(table: pd.DataFrame, columns: list[str], table_name: str) -> None:
    missing = [column for column in columns if column not in table.columns]
    if missing:
        raise KeyError(f"{table_name} is missing required columns: {missing}")

REPORT_TABLE_NAMES: tuple[str, ...] = (
    "event_study_results",
    "diagnostics",
    "label_coverage",
    "event_coverage",
    "grouped_summary",
)


def validate_report_table(
    table: pd.DataFrame,
    *,
    required_columns: Iterable[str] | None = None,
    table_name: str = "table",
) -> pd.DataFrame:
    """Validate that a DataFrame can be used as a report/export table."""
    if not isinstance(table_name, str) or not table_name:
        raise ValueError("table_name must be a non-empty string")
    if not isinstance(table, pd.DataFrame):
        raise TypeError(f"{table_name} must be a pandas DataFrame")

    if required_columns is not None:
        columns = _normalize_columns(required_columns, "required_columns")
        missing = [column for column in columns if column not in table.columns]
        if missing:
            raise KeyError(f"{table_name} is missing required columns: {missing}")

    return table


def normalize_report_table(
    table: pd.DataFrame,
    *,
    sort_columns: Iterable[str] | None = None,
    column_order: Iterable[str] | None = None,
    round_decimals: int | None = None,
) -> pd.DataFrame:
    """Return a deterministic copy of a report table without mutating input."""
    validate_report_table(table)
    normalized = table.copy()

    if sort_columns is not None:
        sort_by = _normalize_columns(sort_columns, "sort_columns")
        _require_columns(normalized, sort_by, "table")
        normalized = normalized.sort_values(sort_by, kind="mergesort").reset_index(drop=True)

    if column_order is not None:
        ordered = _normalize_columns(column_order, "column_order")
        leading = [column for column in ordered if column in normalized.columns]
        trailing = [column for column in normalized.columns if column not in leading]
        normalized = normalized.loc[:, [*leading, *trailing]]

    if round_decimals is not None:
        if not isinstance(round_decimals, int) or isinstance(round_decimals, bool):
            raise ValueError("round_decimals must be an integer when provided")
        float_columns = normalized.select_dtypes(include=["float"]).columns
        normalized.loc[:, float_columns] = normalized.loc[:, float_columns].round(
            round_decimals
        )

    return normalized


def build_event_study_report_bundle(
    event_study_results: pd.DataFrame,
    diagnostics: pd.DataFrame | None = None,
    label_coverage: pd.DataFrame | None = None,
    event_coverage: pd.DataFrame | None = None,
    grouped_summary: pd.DataFrame | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a report bundle containing provided tables and optional metadata."""
    tables = {
        "event_study_results": event_study_results,
        "diagnostics": diagnostics,
        "label_coverage": label_coverage,
        "event_coverage": event_coverage,
        "grouped_summary": grouped_summary,
    }
    provided_tables = {
        name: validate_report_table(table, table_name=name).copy()
        for name, table in tables.items()
        if table is not None
    }

    return {
        "metadata": _json_safe_mapping(metadata or {}),
        "tables": provided_tables,
    }


def summarize_report_bundle(bundle: Mapping[str, Any]) -> pd.DataFrame:
    """Return a structural summary of report-bundle table contents."""
    tables = _get_bundle_tables(bundle)
    rows = [
        {
            "table_name": table_name,
            "row_count": len(table),
            "column_count": len(table.columns),
            "columns": list(table.columns),
        }
        for table_name, table in tables.items()
    ]
    return pd.DataFrame(
        rows,
        columns=["table_name", "row_count", "column_count", "columns"],
    )


def export_report_bundle_to_csv(
    bundle: Mapping[str, Any],
    output_dir: str | Path,
    *,
    overwrite: bool = False,
) -> dict[str, Path]:
    """Export report-bundle tables to deterministic CSV files."""
    tables = _get_bundle_tables(bundle)
    metadata = _get_bundle_metadata(bundle)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    targets: dict[str, Path] = {
        table_name: output_path / f"{table_name}.csv" for table_name in tables
    }
    if metadata:
        targets["metadata"] = output_path / "metadata.json"
    _raise_if_exists(targets.values(), overwrite=overwrite)

    written: dict[str, Path] = {}
    for table_name, table in tables.items():
        target = targets[table_name]
        table.to_csv(target, index=False)
        written[table_name] = target

    if metadata:
        target = targets["metadata"]
        target.write_text(json.dumps(metadata, indent=2, sort_keys=True), encoding="utf-8")
        written["metadata"] = target

    return written


def export_report_bundle_to_json(
    bundle: Mapping[str, Any],
    output_path: str | Path,
    *,
    overwrite: bool = False,
) -> Path:
    """Export the full report bundle to one records-oriented JSON file."""
    tables = _get_bundle_tables(bundle)
    metadata = _get_bundle_metadata(bundle)
    target = Path(output_path)
    if target.exists() and not overwrite:
        raise FileExistsError(f"{target} already exists")
    target.parent.mkdir(parents=True, exist_ok=True)

    payload = {
        "metadata": metadata,
        "tables": {
            table_name: _dataframe_to_records(table)
            for table_name, table in tables.items()
        },
    }
    target.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return target


def create_research_run_metadata(
    *,
    project_name: str = "SPY Directional Edge Research",
    milestone: str | int | None = None,
    data_start: Any | None = None,
    data_end: Any | None = None,
    label_columns: Iterable[str] | None = None,
    event_count: int | None = None,
    notes: str | None = None,
) -> dict[str, Any]:
    """Create stable metadata for exported research artifacts."""
    metadata: dict[str, Any] = {
        "created_at_utc": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "project_name": project_name,
    }
    optional = {
        "milestone": milestone,
        "data_start": data_start,
        "data_end": data_end,
        "label_columns": list(label_columns) if label_columns is not None else None,
        "event_count": event_count,
        "notes": notes,
    }
    for key, value in optional.items():
        if value is not None:
            metadata[key] = _json_safe_value(value)
    return metadata


def _get_bundle_tables(bundle: Mapping[str, Any]) -> dict[str, pd.DataFrame]:
    if not isinstance(bundle, Mapping):
        raise TypeError("bundle must be a mapping")
    tables = bundle.get("tables")
    if not isinstance(tables, Mapping):
        raise KeyError("bundle must contain a tables mapping")
    return {
        table_name: validate_report_table(table, table_name=table_name)
        for table_name, table in tables.items()
    }


def _get_bundle_metadata(bundle: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(bundle, Mapping):
        raise TypeError("bundle must be a mapping")
    metadata = bundle.get("metadata", {})
    if metadata is None:
        return {}
    if not isinstance(metadata, Mapping):
        raise TypeError("bundle metadata must be a mapping")
    return _json_safe_mapping(metadata)

