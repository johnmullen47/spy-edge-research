"""Descriptive portfolio/risk exposure research report bundles.

These helpers package exposure, concentration, signal-overlap, and advisory
limit-check tables into a research report bundle with deterministic CSV/JSON
export. They do not produce allocations, position sizes, portfolio construction,
order instructions, or trade-readiness claims.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pandas as pd

from spy_edge_research._internal._common import (
    created_at_utc as _created_at_utc,
    dataframe_to_records as _dataframe_to_records,
    json_safe_mapping as _json_safe_mapping,
    json_safe_value as _json_safe_value,
    raise_if_exists as _raise_if_exists,
)


RISK_EXPOSURE_REPORT_CAVEAT = "risk_exposure_report_is_descriptive_research_only"
RISK_EXPOSURE_TABLE_FILES: dict[str, str] = {
    "exposure_summary": "exposure_summary.csv",
    "exposure_concentration": "exposure_concentration.csv",
    "signal_overlap": "signal_overlap.csv",
    "exposure_limit_checks": "exposure_limit_checks.csv",
    "risk_exposure_caveats": "risk_exposure_caveats.csv",
}
FORBIDDEN_RISK_EXPOSURE_FIELDS: frozenset[str] = frozenset(
    {
        "buy",
        "sell",
        "entry",
        "exit",
        "approved",
        "live",
        "trade_signal",
        "allocation",
        "portfolio",
        "position_size",
        "sizing",
        "order",
        "readiness",
        "optimal",
        "best",
        "p_l",
        "pnl",
    }
)


def create_risk_exposure_report_metadata(
    *,
    project_name: str = "SPY Directional Edge Research",
    milestone: str = "74",
    package_name: str | None = None,
    notes: str | None = None,
) -> dict[str, Any]:
    """Create metadata for descriptive risk exposure report artifacts."""
    metadata: dict[str, Any] = {
        "created_at_utc": _created_at_utc(),
        "project_name": project_name,
        "milestone": milestone,
        "report_caveat": RISK_EXPOSURE_REPORT_CAVEAT,
    }
    for key, value in {"package_name": package_name, "notes": notes}.items():
        if value is not None:
            metadata[key] = _json_safe_value(value)
    _raise_forbidden_fields(metadata, name="risk exposure report metadata")
    return metadata


def build_risk_exposure_report_bundle(
    *,
    exposure_summary: pd.DataFrame,
    exposure_concentration: pd.DataFrame | None = None,
    signal_overlap: pd.DataFrame | None = None,
    exposure_limit_checks: pd.DataFrame | None = None,
    metadata: Mapping[str, Any] | None = None,
    include_caveat_table: bool = True,
) -> dict[str, Any]:
    """Assemble a descriptive risk exposure research report bundle."""
    if metadata is not None and not isinstance(metadata, Mapping):
        raise TypeError("metadata must be a mapping when provided")
    bundle_metadata = _json_safe_mapping(dict(metadata or create_risk_exposure_report_metadata()))
    bundle_metadata.setdefault("report_caveat", RISK_EXPOSURE_REPORT_CAVEAT)
    _raise_forbidden_fields(bundle_metadata, name="risk exposure report metadata")

    tables: dict[str, pd.DataFrame] = {"exposure_summary": _copy_table(exposure_summary, "exposure_summary")}
    if exposure_concentration is not None:
        tables["exposure_concentration"] = _copy_table(exposure_concentration, "exposure_concentration")
    if signal_overlap is not None:
        tables["signal_overlap"] = _copy_table(signal_overlap, "signal_overlap")
    if exposure_limit_checks is not None:
        tables["exposure_limit_checks"] = _copy_table(exposure_limit_checks, "exposure_limit_checks")
    if include_caveat_table:
        tables["risk_exposure_caveats"] = _build_caveat_table(tables)

    return validate_risk_exposure_report_bundle({"metadata": bundle_metadata, "tables": tables})


def validate_risk_exposure_report_bundle(bundle: Any) -> dict[str, Any]:
    """Validate a risk exposure report bundle structure."""
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
    _raise_forbidden_fields(bundle["metadata"], name="risk exposure report metadata")
    for table_name, table in bundle["tables"].items():
        if not isinstance(table_name, str) or not table_name:
            raise ValueError("bundle table names must be non-empty strings")
        _raise_forbidden_fields({"table_name": table_name}, name="risk exposure table name")
        if not isinstance(table, pd.DataFrame):
            raise TypeError(f"{table_name} must be a pandas DataFrame")
        _raise_forbidden_fields({column: None for column in table.columns}, name=f"{table_name} columns")
    return bundle


def summarize_risk_exposure_report_bundle(bundle: Mapping[str, Any]) -> pd.DataFrame:
    """Return a structural summary of risk exposure report bundle tables."""
    validated = validate_risk_exposure_report_bundle(dict(bundle))
    rows = [
        {
            "table_name": table_name,
            "row_count": len(table),
            "column_count": len(table.columns),
            "columns": list(table.columns),
        }
        for table_name, table in validated["tables"].items()
    ]
    summary = pd.DataFrame(rows, columns=["table_name", "row_count", "column_count", "columns"])
    if summary.empty:
        return summary
    return summary.sort_values("table_name", kind="mergesort").reset_index(drop=True)


def export_risk_exposure_report_bundle_to_csv(
    bundle: Mapping[str, Any],
    output_dir: str | Path,
    *,
    overwrite: bool = False,
) -> dict[str, Path]:
    """Export risk exposure report tables to deterministic CSV files."""
    validated = validate_risk_exposure_report_bundle(dict(bundle))
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    targets: dict[str, Path] = {
        table_name: output_path / RISK_EXPOSURE_TABLE_FILES.get(table_name, f"{table_name}.csv")
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


def export_risk_exposure_report_bundle_to_json(
    bundle: Mapping[str, Any],
    output_path: str | Path,
    *,
    overwrite: bool = False,
) -> Path:
    """Export a risk exposure report bundle to one records-oriented JSON file."""
    validated = validate_risk_exposure_report_bundle(dict(bundle))
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


def _build_caveat_table(tables: Mapping[str, pd.DataFrame]) -> pd.DataFrame:
    rows = [
        {"report_section": "overall", "caveat": RISK_EXPOSURE_REPORT_CAVEAT},
        {"report_section": "overall", "caveat": "exposure_is_not_position_sizing_or_allocation_guidance"},
        {"report_section": "overall", "caveat": "limit_flags_are_advisory_for_human_review_only"},
        {"report_section": "overall", "caveat": "sample_size_and_coverage_require_research_review"},
    ]
    for table_name, table in tables.items():
        for column in table.columns:
            if "caveat" not in column:
                continue
            for caveat in table[column].dropna().unique().tolist():
                rows.append({"report_section": table_name, "caveat": caveat})
    return pd.DataFrame(rows, columns=["report_section", "caveat"]).drop_duplicates().reset_index(drop=True)


def _copy_table(table: Any, table_name: str) -> pd.DataFrame:
    if not isinstance(table, pd.DataFrame):
        raise TypeError(f"{table_name} must be a pandas DataFrame")
    return table.copy(deep=True)


def _raise_forbidden_fields(values: Mapping[str, Any], *, name: str) -> None:
    forbidden = [
        field
        for field in values
        if any(token in str(field).lower() for token in FORBIDDEN_RISK_EXPOSURE_FIELDS)
    ]
    if forbidden:
        raise ValueError(f"{name} contains forbidden fields: {forbidden}")
