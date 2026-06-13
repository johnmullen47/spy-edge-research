"""Research-only report helpers for candidate rule catalogs."""

from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from spy_edge_research.backtesting.candidate_rule_objects import (
    build_candidate_rule_catalog,
    summarize_candidate_rule_catalog,
)

RULE_CATALOG_REPORT_TABLE_FILES: dict[str, str] = {
    "rule_catalog": "rule_catalog.csv",
    "catalog_summary": "catalog_summary.csv",
    "research_state_breakdown": "research_state_breakdown.csv",
    "required_column_inventory": "required_column_inventory.csv",
    "caveat_summary": "caveat_summary.csv",
}


def create_candidate_rule_report_metadata(
    *,
    project_name: str = "SPY Directional Edge Research",
    milestone: str = "38",
    notes: str | None = None,
) -> dict[str, Any]:
    """Create metadata for candidate rule catalog reports."""
    metadata: dict[str, Any] = {
        "created_at_utc": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "project_name": project_name,
        "milestone": milestone,
        "report_caveat": "candidate_rule_report_is_research_only",
    }
    if notes is not None:
        metadata["notes"] = notes
    return metadata


def summarize_candidate_rule_research_states(catalog: pd.DataFrame) -> pd.DataFrame:
    """Count rule objects by research state without approval language."""
    validated = build_candidate_rule_catalog(_records_from_frame(catalog))
    if validated.empty:
        return pd.DataFrame(columns=["research_state", "rule_object_count", "summary_caveat"])
    return (
        validated.groupby("research_state", dropna=False)
        .size()
        .reset_index(name="rule_object_count")
        .assign(summary_caveat="research_state_is_not_deployment_status")
        .sort_values("research_state", kind="mergesort")
        .reset_index(drop=True)
    )


def build_candidate_rule_required_column_inventory(catalog: pd.DataFrame) -> pd.DataFrame:
    """Build a required-column inventory for catalog audit."""
    validated = build_candidate_rule_catalog(_records_from_frame(catalog))
    rows = []
    for row in validated.to_dict("records"):
        for column in row["required_columns"]:
            rows.append(
                {
                    "required_column": column,
                    "rule_object_id": row["rule_object_id"],
                    "candidate_id": row["candidate_id"],
                    "research_state": row["research_state"],
                }
            )
    if not rows:
        return pd.DataFrame(
            columns=[
                "required_column",
                "rule_object_count",
                "rule_object_ids",
                "candidate_ids",
                "research_states",
                "inventory_caveat",
            ]
        )
    inventory = pd.DataFrame(rows)
    grouped = inventory.groupby("required_column", dropna=False, sort=True)
    return grouped.agg(
        rule_object_count=("rule_object_id", "nunique"),
        rule_object_ids=("rule_object_id", lambda values: sorted(set(values))),
        candidate_ids=("candidate_id", lambda values: sorted(set(values))),
        research_states=("research_state", lambda values: sorted(set(values))),
    ).reset_index().assign(
        inventory_caveat="required_columns_are_for_replay_audit_only"
    )


def summarize_candidate_rule_caveats(catalog: pd.DataFrame) -> pd.DataFrame:
    """Summarize caveats attached to rule objects."""
    validated = build_candidate_rule_catalog(_records_from_frame(catalog))
    rows = []
    for row in validated.to_dict("records"):
        for caveat in row["caveats"]:
            rows.append(
                {
                    "caveat": caveat,
                    "rule_object_id": row["rule_object_id"],
                    "candidate_id": row["candidate_id"],
                }
            )
    if not rows:
        return pd.DataFrame(
            columns=["caveat", "rule_object_count", "candidate_count", "summary_caveat"]
        )
    caveats = pd.DataFrame(rows)
    return caveats.groupby("caveat", dropna=False, sort=True).agg(
        rule_object_count=("rule_object_id", "nunique"),
        candidate_count=("candidate_id", "nunique"),
    ).reset_index().assign(summary_caveat="caveats_are_research_warnings")


def build_candidate_rule_report_bundle(
    catalog: pd.DataFrame,
    *,
    metadata: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Package candidate rule catalog reports into a deterministic bundle."""
    validated = build_candidate_rule_catalog(_records_from_frame(catalog))
    bundle = {
        "metadata": _json_safe_mapping(metadata or create_candidate_rule_report_metadata()),
        "tables": {
            "rule_catalog": validated.copy(deep=True),
            "catalog_summary": summarize_candidate_rule_catalog(validated),
            "research_state_breakdown": summarize_candidate_rule_research_states(validated),
            "required_column_inventory": build_candidate_rule_required_column_inventory(validated),
            "caveat_summary": summarize_candidate_rule_caveats(validated),
        },
    }
    return validate_candidate_rule_report_bundle(bundle)


def validate_candidate_rule_report_bundle(bundle: Any) -> dict[str, Any]:
    """Validate candidate rule report bundle structure."""
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


def summarize_candidate_rule_report_bundle(bundle: Mapping[str, Any]) -> pd.DataFrame:
    """Return structural summary for a candidate rule report bundle."""
    validated = validate_candidate_rule_report_bundle(dict(bundle))
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


def export_candidate_rule_report_bundle_to_csv(
    bundle: Mapping[str, Any],
    output_dir: str | Path,
    *,
    overwrite: bool = False,
) -> dict[str, Path]:
    """Export candidate rule report bundle tables to CSV."""
    validated = validate_candidate_rule_report_bundle(dict(bundle))
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    targets = {
        name: output_path / RULE_CATALOG_REPORT_TABLE_FILES.get(name, f"{name}.csv")
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


def export_candidate_rule_report_bundle_to_json(
    bundle: Mapping[str, Any],
    output_path: str | Path,
    *,
    overwrite: bool = False,
) -> Path:
    """Export candidate rule report bundle to records-oriented JSON."""
    validated = validate_candidate_rule_report_bundle(dict(bundle))
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


def _records_from_frame(catalog: pd.DataFrame) -> list[dict[str, Any]]:
    return catalog.to_dict("records")


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
