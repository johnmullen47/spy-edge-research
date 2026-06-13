"""Research-only governance summary bundle helpers."""

from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

GOVERNANCE_TABLE_FILES: dict[str, str] = {
    "artifact_integrity_summary": "artifact_integrity_summary.csv",
    "package_comparison_summary": "package_comparison_summary.csv",
    "traceability_summary": "traceability_summary.csv",
    "governance_caveats": "governance_caveats.csv",
}


def create_research_governance_metadata(
    *,
    project_name: str = "SPY Directional Edge Research",
    milestone: str = "57",
    notes: str | None = None,
) -> dict[str, Any]:
    """Create metadata for governance summary bundle artifacts."""
    metadata: dict[str, Any] = {
        "created_at_utc": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "project_name": project_name,
        "milestone": milestone,
        "governance_caveat": "research_governance_bundle_is_review_only",
    }
    if notes is not None:
        metadata["notes"] = notes
    return metadata


def build_research_governance_bundle(
    *,
    artifact_integrity_summary: pd.DataFrame | None = None,
    package_comparison_summary: pd.DataFrame | None = None,
    traceability_summary: pd.DataFrame | None = None,
    additional_tables: Mapping[str, pd.DataFrame] | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a deterministic governance summary bundle."""
    tables: dict[str, pd.DataFrame] = {}
    for name, table in {
        "artifact_integrity_summary": artifact_integrity_summary,
        "package_comparison_summary": package_comparison_summary,
        "traceability_summary": traceability_summary,
    }.items():
        if table is not None:
            _require_dataframe(table, name)
            tables[name] = table.copy(deep=True)
    for name, table in dict(additional_tables or {}).items():
        if name in tables or name == "governance_caveats":
            raise ValueError(f"duplicate governance table name: {name}")
        _require_dataframe(table, name)
        tables[str(name)] = table.copy(deep=True)
    tables["governance_caveats"] = _governance_caveat_table()
    return validate_research_governance_bundle(
        {
            "metadata": _json_safe_mapping(metadata or create_research_governance_metadata()),
            "tables": tables,
        }
    )


def validate_research_governance_bundle(bundle: Any) -> dict[str, Any]:
    """Validate research governance bundle structure."""
    if not isinstance(bundle, dict):
        raise TypeError("bundle must be a dict")
    if not isinstance(bundle.get("metadata"), dict):
        raise TypeError("bundle metadata must be a dict")
    if not isinstance(bundle.get("tables"), dict):
        raise TypeError("bundle tables must be a dict")
    if "governance_caveats" not in bundle["tables"]:
        raise KeyError("bundle tables must include governance_caveats")
    for name, table in bundle["tables"].items():
        if not isinstance(name, str) or not name:
            raise ValueError("table names must be non-empty strings")
        _require_dataframe(table, name)
    return bundle


def summarize_research_governance_bundle(bundle: Mapping[str, Any]) -> pd.DataFrame:
    """Summarize governance bundle tables structurally."""
    validated = validate_research_governance_bundle(dict(bundle))
    rows = []
    for name, table in validated["tables"].items():
        rows.append(
            {
                "table_name": name,
                "row_count": len(table),
                "column_count": len(table.columns),
                "columns": list(table.columns),
                "summary_caveat": "governance_summary_is_research_review_only",
            }
        )
    return pd.DataFrame(rows).sort_values("table_name", kind="mergesort").reset_index(drop=True)


def export_research_governance_bundle_to_csv(
    bundle: Mapping[str, Any],
    output_dir: str | Path,
    *,
    overwrite: bool = False,
) -> dict[str, Path]:
    """Export governance bundle tables to CSV."""
    validated = validate_research_governance_bundle(dict(bundle))
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    targets = {
        name: output_path / GOVERNANCE_TABLE_FILES.get(name, f"{name}.csv")
        for name in validated["tables"]
    }
    targets["metadata"] = output_path / "metadata.json"
    _raise_if_exists(targets.values(), overwrite=overwrite)
    written = {}
    for name, table in validated["tables"].items():
        table.to_csv(targets[name], index=False)
        written[name] = targets[name]
    targets["metadata"].write_text(
        json.dumps(_json_safe_mapping(validated["metadata"]), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    written["metadata"] = targets["metadata"]
    return written


def export_research_governance_bundle_to_json(
    bundle: Mapping[str, Any],
    output_path: str | Path,
    *,
    overwrite: bool = False,
) -> Path:
    """Export governance bundle to records-oriented JSON."""
    validated = validate_research_governance_bundle(dict(bundle))
    target = Path(output_path)
    if target.exists() and not overwrite:
        raise FileExistsError(f"{target} already exists")
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "metadata": _json_safe_mapping(validated["metadata"]),
        "tables": {
            name: _dataframe_to_records(table)
            for name, table in validated["tables"].items()
        },
    }
    target.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return target


def _governance_caveat_table() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"governance_section": "overall", "caveat": "governance_bundle_is_research_only"},
            {"governance_section": "overall", "caveat": "governance_bundle_does_not_authorize_trading"},
            {"governance_section": "overall", "caveat": "missing_evidence_is_a_review_caveat"},
        ]
    )


def _require_dataframe(table: Any, name: str) -> None:
    if not isinstance(table, pd.DataFrame):
        raise TypeError(f"{name} must be a pandas DataFrame")


def _raise_if_exists(paths: Any, *, overwrite: bool) -> None:
    if overwrite:
        return
    existing = [path for path in paths if Path(path).exists()]
    if existing:
        raise FileExistsError(f"Refusing to overwrite existing files: {existing}")


def _dataframe_to_records(table: pd.DataFrame) -> list[dict[str, Any]]:
    return [
        {str(key): _json_safe_value(value) for key, value in row.items()}
        for row in table.replace({pd.NaT: None}).to_dict("records")
    ]


def _json_safe_mapping(values: Mapping[str, Any]) -> dict[str, Any]:
    return {str(key): _json_safe_value(value) for key, value in values.items()}


def _json_safe_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return _json_safe_mapping(value)
    if isinstance(value, list):
        return [_json_safe_value(item) for item in value]
    if isinstance(value, tuple):
        return [_json_safe_value(item) for item in value]
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if isinstance(value, np.generic):
        return _json_safe_value(value.item())
    if isinstance(value, float) and np.isnan(value):
        return None
    return value
