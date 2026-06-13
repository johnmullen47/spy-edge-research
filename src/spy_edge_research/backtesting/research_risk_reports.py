"""Research-only risk dashboard report bundles."""

from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

RISK_REPORT_TABLE_FILES: dict[str, str] = {
    "multiple_testing_risk": "multiple_testing_risk.csv",
    "placebo_risk": "placebo_risk.csv",
    "temporal_stability": "temporal_stability.csv",
    "data_quality": "data_quality.csv",
    "decision_summary": "decision_summary.csv",
    "risk_caveats": "risk_caveats.csv",
}


def create_research_risk_report_metadata(
    *,
    project_name: str = "SPY Directional Edge Research",
    milestone: str = "49",
    notes: str | None = None,
) -> dict[str, Any]:
    """Create metadata for risk report artifacts."""
    metadata: dict[str, Any] = {
        "created_at_utc": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "project_name": project_name,
        "milestone": milestone,
        "report_caveat": "research_risk_report_is_diagnostic_only",
    }
    if notes is not None:
        metadata["notes"] = notes
    return metadata


def build_research_risk_report_bundle(
    *,
    multiple_testing_risk: pd.DataFrame | None = None,
    placebo_risk: pd.DataFrame | None = None,
    temporal_stability: pd.DataFrame | None = None,
    data_quality: pd.DataFrame | None = None,
    decision_summary: pd.DataFrame | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a research-risk report bundle from existing diagnostic tables."""
    tables: dict[str, pd.DataFrame] = {}
    for name, table in {
        "multiple_testing_risk": multiple_testing_risk,
        "placebo_risk": placebo_risk,
        "temporal_stability": temporal_stability,
        "data_quality": data_quality,
        "decision_summary": decision_summary,
    }.items():
        if table is not None:
            if not isinstance(table, pd.DataFrame):
                raise TypeError(f"{name} must be a pandas DataFrame")
            tables[name] = table.copy(deep=True)
    tables["risk_caveats"] = _risk_caveat_table()
    bundle = {
        "metadata": _json_safe_mapping(metadata or create_research_risk_report_metadata()),
        "tables": tables,
    }
    return validate_research_risk_report_bundle(bundle)


def validate_research_risk_report_bundle(bundle: Any) -> dict[str, Any]:
    """Validate research-risk report bundle structure."""
    if not isinstance(bundle, dict):
        raise TypeError("bundle must be a dict")
    if not isinstance(bundle.get("metadata"), dict):
        raise TypeError("bundle metadata must be a dict")
    if not isinstance(bundle.get("tables"), dict):
        raise TypeError("bundle tables must be a dict")
    for name, table in bundle["tables"].items():
        if not isinstance(name, str) or not name:
            raise ValueError("table names must be non-empty strings")
        if not isinstance(table, pd.DataFrame):
            raise TypeError(f"{name} must be a pandas DataFrame")
    return bundle


def summarize_research_risk_report_bundle(bundle: Mapping[str, Any]) -> pd.DataFrame:
    """Return structural summary of risk report bundle tables."""
    validated = validate_research_risk_report_bundle(dict(bundle))
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


def export_research_risk_report_bundle_to_csv(
    bundle: Mapping[str, Any],
    output_dir: str | Path,
    *,
    overwrite: bool = False,
) -> dict[str, Path]:
    """Export risk report bundle tables to CSV."""
    validated = validate_research_risk_report_bundle(dict(bundle))
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    targets = {
        name: output_path / RISK_REPORT_TABLE_FILES.get(name, f"{name}.csv")
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


def export_research_risk_report_bundle_to_json(
    bundle: Mapping[str, Any],
    output_path: str | Path,
    *,
    overwrite: bool = False,
) -> Path:
    """Export risk report bundle to records-oriented JSON."""
    validated = validate_research_risk_report_bundle(dict(bundle))
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


def _risk_caveat_table() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "risk_section": "overall",
                "caveat": "risk_report_is_research_only",
            },
            {
                "risk_section": "overall",
                "caveat": "risk_diagnostics_do_not_validate_tradability",
            },
        ]
    )


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
