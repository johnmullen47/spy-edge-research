"""Research-only robustness audit bundles for candidate rule objects."""

from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from spy_edge_research._internal._common import (
    dataframe_to_records as _dataframe_to_records,
    json_safe_mapping as _json_safe_mapping,
    raise_if_exists as _raise_if_exists,
)


RULE_AUDIT_TABLE_FILES: dict[str, str] = {
    "rule_catalog": "rule_catalog.csv",
    "catalog_summary": "catalog_summary.csv",
    "replay_results": "replay_results.csv",
    "replay_summary": "replay_summary.csv",
    "oos_comparison": "oos_comparison.csv",
    "oos_comparison_summary": "oos_comparison_summary.csv",
    "robustness_caveats": "robustness_caveats.csv",
}


def create_candidate_rule_audit_metadata(
    *,
    project_name: str = "SPY Directional Edge Research",
    milestone: str = "41",
    notes: str | None = None,
) -> dict[str, Any]:
    """Create metadata for candidate rule robustness audit bundles."""
    metadata: dict[str, Any] = {
        "created_at_utc": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "project_name": project_name,
        "milestone": milestone,
        "audit_caveat": "candidate_rule_audit_is_research_only",
    }
    if notes is not None:
        metadata["notes"] = notes
    return metadata


def build_candidate_rule_audit_bundle(
    *,
    rule_catalog: pd.DataFrame | None = None,
    catalog_summary: pd.DataFrame | None = None,
    replay_results: pd.DataFrame | None = None,
    replay_summary: pd.DataFrame | None = None,
    oos_comparison: pd.DataFrame | None = None,
    oos_comparison_summary: pd.DataFrame | None = None,
    robustness_caveats: pd.DataFrame | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Package candidate rule audit tables into one bundle."""
    tables: dict[str, pd.DataFrame] = {}
    for name, table in {
        "rule_catalog": rule_catalog,
        "catalog_summary": catalog_summary,
        "replay_results": replay_results,
        "replay_summary": replay_summary,
        "oos_comparison": oos_comparison,
        "oos_comparison_summary": oos_comparison_summary,
        "robustness_caveats": robustness_caveats,
    }.items():
        if table is not None:
            if not isinstance(table, pd.DataFrame):
                raise TypeError(f"{name} must be a pandas DataFrame")
            tables[name] = table.copy(deep=True)
    if "robustness_caveats" not in tables:
        tables["robustness_caveats"] = _default_caveat_table()
    bundle = {
        "metadata": _json_safe_mapping(metadata or create_candidate_rule_audit_metadata()),
        "tables": tables,
    }
    return validate_candidate_rule_audit_bundle(bundle)


def validate_candidate_rule_audit_bundle(bundle: Any) -> dict[str, Any]:
    """Validate candidate rule audit bundle structure."""
    if not isinstance(bundle, dict):
        raise TypeError("bundle must be a dict")
    if not isinstance(bundle.get("metadata"), dict):
        raise TypeError("bundle metadata must be a dict")
    if not isinstance(bundle.get("tables"), dict):
        raise TypeError("bundle tables must be a dict")
    for name, table in bundle["tables"].items():
        if not isinstance(name, str) or not name:
            raise ValueError("bundle table names must be non-empty strings")
        if not isinstance(table, pd.DataFrame):
            raise TypeError(f"{name} must be a pandas DataFrame")
    return bundle


def summarize_candidate_rule_audit_bundle(bundle: Mapping[str, Any]) -> pd.DataFrame:
    """Return a structural summary of candidate rule audit tables."""
    validated = validate_candidate_rule_audit_bundle(dict(bundle))
    rows = [
        {
            "table_name": name,
            "row_count": len(table),
            "column_count": len(table.columns),
            "columns": list(table.columns),
        }
        for name, table in validated["tables"].items()
    ]
    return pd.DataFrame(rows).sort_values("table_name", kind="mergesort").reset_index(drop=True)


def export_candidate_rule_audit_bundle_to_csv(
    bundle: Mapping[str, Any],
    output_dir: str | Path,
    *,
    overwrite: bool = False,
) -> dict[str, Path]:
    """Export candidate rule audit tables to CSV."""
    validated = validate_candidate_rule_audit_bundle(dict(bundle))
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    targets = {
        name: output_path / RULE_AUDIT_TABLE_FILES.get(name, f"{name}.csv")
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


def export_candidate_rule_audit_bundle_to_json(
    bundle: Mapping[str, Any],
    output_path: str | Path,
    *,
    overwrite: bool = False,
) -> Path:
    """Export candidate rule audit bundle to records-oriented JSON."""
    validated = validate_candidate_rule_audit_bundle(dict(bundle))
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


def _default_caveat_table() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "audit_section": "overall",
                "caveat": "candidate_rule_audit_is_research_only",
            },
            {
                "audit_section": "overall",
                "caveat": "audit_findings_do_not_approve_deployment",
            },
        ]
    )

