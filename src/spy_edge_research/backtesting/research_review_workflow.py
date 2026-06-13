"""Research-only end-to-end review workflow helpers."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from spy_edge_research.backtesting.research_package_manifest import (
    create_research_package_manifest_record,
    build_research_package_manifest,
    write_research_package_manifest,
)


def create_research_review_metadata(
    *,
    project_name: str = "SPY Directional Edge Research",
    milestone: str = "53",
    notes: str | None = None,
) -> dict[str, Any]:
    """Create metadata for research review workflow outputs."""
    metadata = {
        "created_at_utc": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "project_name": project_name,
        "milestone": milestone,
        "workflow_caveat": "research_review_workflow_is_not_strategy_execution",
    }
    if notes is not None:
        metadata["notes"] = notes
    return metadata


def build_research_review_workflow_outputs(
    *,
    package_id: str,
    tables: Mapping[str, pd.DataFrame],
    metadata: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a research review workflow output dictionary."""
    if not isinstance(package_id, str) or not package_id:
        raise ValueError("package_id must be a non-empty string")
    if not isinstance(tables, Mapping):
        raise TypeError("tables must be a mapping")
    copied_tables = {}
    for name, table in tables.items():
        if not isinstance(name, str) or not name:
            raise ValueError("table names must be non-empty strings")
        if not isinstance(table, pd.DataFrame):
            raise TypeError(f"{name} must be a pandas DataFrame")
        copied_tables[name] = table.copy(deep=True)
    workflow_metadata = dict(metadata or create_research_review_metadata())
    manifest_records = [
        create_research_package_manifest_record(
            package_id=package_id,
            artifact_name=name,
            artifact_path=f"{name}.csv",
            artifact_type="csv_table",
            description=f"Research review table: {name}",
        )
        for name in sorted(copied_tables)
    ]
    return {
        "metadata": workflow_metadata,
        "tables": copied_tables,
        "manifest": build_research_package_manifest(
            manifest_records,
            metadata={"package_id": package_id, "source": "research_review_workflow"},
        ),
    }


def summarize_research_review_workflow_outputs(outputs: Mapping[str, Any]) -> pd.DataFrame:
    """Summarize workflow output tables."""
    if not isinstance(outputs, Mapping):
        raise TypeError("outputs must be a mapping")
    tables = outputs.get("tables")
    if not isinstance(tables, Mapping):
        raise KeyError("outputs must contain a tables mapping")
    rows = []
    for name, table in tables.items():
        if not isinstance(table, pd.DataFrame):
            raise TypeError(f"{name} must be a pandas DataFrame")
        rows.append(
            {
                "table_name": name,
                "row_count": len(table),
                "column_count": len(table.columns),
                "columns": list(table.columns),
            }
        )
    return pd.DataFrame(rows).sort_values("table_name", kind="mergesort").reset_index(drop=True)


def export_research_review_workflow_outputs(
    outputs: Mapping[str, Any],
    output_dir: str | Path,
    *,
    overwrite: bool = False,
) -> dict[str, Path]:
    """Export workflow tables and manifest to a directory."""
    if not isinstance(outputs, Mapping):
        raise TypeError("outputs must be a mapping")
    tables = outputs.get("tables")
    manifest = outputs.get("manifest")
    if not isinstance(tables, Mapping):
        raise KeyError("outputs must contain a tables mapping")
    if not isinstance(manifest, Mapping):
        raise KeyError("outputs must contain a manifest")
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    targets = {name: output_path / f"{name}.csv" for name in tables}
    targets["manifest"] = output_path / "research_package_manifest.json"
    if not overwrite:
        existing = [path for path in targets.values() if path.exists()]
        if existing:
            raise FileExistsError(f"Refusing to overwrite existing files: {existing}")
    written = {}
    for name, table in tables.items():
        if not isinstance(table, pd.DataFrame):
            raise TypeError(f"{name} must be a pandas DataFrame")
        table.to_csv(targets[name], index=False)
        written[name] = targets[name]
    written["manifest"] = write_research_package_manifest(
        manifest,
        targets["manifest"],
        overwrite=overwrite,
    )
    return written
