"""Descriptive paper-trading readiness scorecard report bundles.

Packages a readiness scorecard and gated verdict into a report bundle with
deterministic CSV/JSON export. The bundle is a research gate artifact only: it
records whether evidence criteria are met, never authorizes a trade, sizes a
position, or implies a live or paper order.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


READINESS_REPORT_CAVEAT = "readiness_report_is_research_gate_not_trade_authorization"
READINESS_TABLE_FILES: dict[str, str] = {
    "readiness_scorecard": "readiness_scorecard.csv",
    "readiness_verdict": "readiness_verdict.csv",
    "readiness_caveats": "readiness_caveats.csv",
}
FORBIDDEN_READINESS_FIELDS: frozenset[str] = frozenset(
    {
        "buy",
        "sell",
        "entry",
        "exit",
        "approved",
        "live",
        "trade_signal",
        "order",
        "position_size",
        "sizing",
        "allocation",
        "portfolio",
        "optimal",
        "best",
        "p_l",
        "pnl",
    }
)


def create_readiness_report_metadata(
    *,
    project_name: str = "SPY Directional Edge Research",
    milestone: str = "92",
    package_name: str | None = None,
    notes: str | None = None,
) -> dict[str, Any]:
    """Create metadata for a readiness scorecard report bundle."""
    metadata: dict[str, Any] = {
        "created_at_utc": _created_at_utc(),
        "project_name": project_name,
        "milestone": milestone,
        "report_caveat": READINESS_REPORT_CAVEAT,
    }
    for key, value in {"package_name": package_name, "notes": notes}.items():
        if value is not None:
            metadata[key] = _json_safe_value(value)
    _raise_forbidden_fields(metadata, name="readiness report metadata")
    return metadata


def build_readiness_report_bundle(
    *,
    scorecard: pd.DataFrame,
    verdict: pd.DataFrame,
    metadata: Mapping[str, Any] | None = None,
    include_caveat_table: bool = True,
) -> dict[str, Any]:
    """Assemble a readiness scorecard report bundle."""
    if metadata is not None and not isinstance(metadata, Mapping):
        raise TypeError("metadata must be a mapping when provided")
    bundle_metadata = _json_safe_mapping(dict(metadata or create_readiness_report_metadata()))
    bundle_metadata.setdefault("report_caveat", READINESS_REPORT_CAVEAT)
    _raise_forbidden_fields(bundle_metadata, name="readiness report metadata")

    tables: dict[str, pd.DataFrame] = {
        "readiness_scorecard": _copy_table(scorecard, "readiness_scorecard"),
        "readiness_verdict": _copy_table(verdict, "readiness_verdict"),
    }
    if include_caveat_table:
        tables["readiness_caveats"] = _build_caveat_table(tables)
    return validate_readiness_report_bundle({"metadata": bundle_metadata, "tables": tables})


def validate_readiness_report_bundle(bundle: Any) -> dict[str, Any]:
    """Validate a readiness report bundle structure."""
    if not isinstance(bundle, dict):
        raise TypeError("bundle must be a dict")
    if "metadata" not in bundle or not isinstance(bundle["metadata"], dict):
        raise KeyError("bundle is missing a metadata dict")
    if "tables" not in bundle or not isinstance(bundle["tables"], dict):
        raise KeyError("bundle is missing a tables dict")
    _raise_forbidden_fields(bundle["metadata"], name="readiness report metadata")
    for table_name, table in bundle["tables"].items():
        if not isinstance(table_name, str) or not table_name:
            raise ValueError("bundle table names must be non-empty strings")
        _raise_forbidden_fields({"table_name": table_name}, name="readiness table name")
        if not isinstance(table, pd.DataFrame):
            raise TypeError(f"{table_name} must be a pandas DataFrame")
        _raise_forbidden_fields({column: None for column in table.columns}, name=f"{table_name} columns")
    return bundle


def summarize_readiness_report_bundle(bundle: Mapping[str, Any]) -> pd.DataFrame:
    """Return a structural summary of readiness report bundle tables."""
    validated = validate_readiness_report_bundle(dict(bundle))
    rows = [
        {"table_name": name, "row_count": len(table), "column_count": len(table.columns)}
        for name, table in validated["tables"].items()
    ]
    summary = pd.DataFrame(rows, columns=["table_name", "row_count", "column_count"])
    if summary.empty:
        return summary
    return summary.sort_values("table_name", kind="mergesort").reset_index(drop=True)


def export_readiness_report_bundle_to_csv(
    bundle: Mapping[str, Any],
    output_dir: str | Path,
    *,
    overwrite: bool = False,
) -> dict[str, Path]:
    """Export readiness report tables to deterministic CSV files."""
    validated = validate_readiness_report_bundle(dict(bundle))
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    targets: dict[str, Path] = {
        name: output_path / READINESS_TABLE_FILES.get(name, f"{name}.csv")
        for name in validated["tables"]
    }
    targets["metadata"] = output_path / "metadata.json"
    _raise_if_exists(targets.values(), overwrite=overwrite)
    written: dict[str, Path] = {}
    for name, table in validated["tables"].items():
        table.to_csv(targets[name], index=False)
        written[name] = targets[name]
    targets["metadata"].write_text(
        json.dumps(_json_safe_mapping(validated["metadata"]), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    written["metadata"] = targets["metadata"]
    return written


def export_readiness_report_bundle_to_json(
    bundle: Mapping[str, Any],
    output_path: str | Path,
    *,
    overwrite: bool = False,
) -> Path:
    """Export a readiness report bundle to one records-oriented JSON file."""
    validated = validate_readiness_report_bundle(dict(bundle))
    target = Path(output_path)
    if target.exists() and not overwrite:
        raise FileExistsError(f"{target} already exists")
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "metadata": _json_safe_mapping(validated["metadata"]),
        "tables": {name: _dataframe_to_records(table) for name, table in validated["tables"].items()},
    }
    target.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return target


def _build_caveat_table(tables: Mapping[str, pd.DataFrame]) -> pd.DataFrame:
    rows = [
        {"report_section": "overall", "caveat": READINESS_REPORT_CAVEAT},
        {"report_section": "overall", "caveat": "eligible_means_evidence_bar_met_not_trade_authorized"},
        {"report_section": "overall", "caveat": "paper_trading_simulation_remains_a_separate_unauthorized_module"},
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


def _raise_if_exists(paths: Any, *, overwrite: bool) -> None:
    if overwrite:
        return
    existing = [path for path in paths if Path(path).exists()]
    if existing:
        raise FileExistsError(f"Refusing to overwrite existing files: {existing}")


def _dataframe_to_records(table: pd.DataFrame) -> list[dict[str, Any]]:
    records = table.replace({pd.NaT: None}).to_dict(orient="records")
    return [{str(key): _json_safe_value(value) for key, value in row.items()} for row in records]


def _json_safe_mapping(values: Mapping[str, Any]) -> dict[str, Any]:
    return {str(key): _json_safe_value(value) for key, value in values.items()}


def _json_safe_value(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, pd.Timestamp):
        return None if pd.isna(value) else value.isoformat()
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, np.generic):
        return _json_safe_value(value.item())
    if isinstance(value, float) and np.isnan(value):
        return None
    if isinstance(value, Mapping):
        return _json_safe_mapping(value)
    if isinstance(value, (list, tuple)):
        return [_json_safe_value(item) for item in value]
    return value


def _created_at_utc() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _raise_forbidden_fields(values: Mapping[str, Any], *, name: str) -> None:
    forbidden = [
        field
        for field in values
        if any(token in str(field).lower() for token in FORBIDDEN_READINESS_FIELDS)
    ]
    if forbidden:
        raise ValueError(f"{name} contains forbidden fields: {forbidden}")
