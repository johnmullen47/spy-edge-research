"""Research-only robustness report builders.

These helpers package out-of-sample and parameter-sensitivity diagnostics into
deterministic report bundles. They do not create signals, optimize parameters,
select strategy rules, simulate P/L, or claim tradability.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from spy_edge_research.backtesting.oos_validation import summarize_oos_edge_stability


ROBUSTNESS_REPORT_TABLE_FILES: dict[str, str] = {
    "oos_validation_results": "oos_validation_results.csv",
    "oos_stability_summary": "oos_stability_summary.csv",
    "parameter_sensitivity_summary": "parameter_sensitivity_summary.csv",
    "parameter_reference_comparison": "parameter_reference_comparison.csv",
    "robustness_caveats": "robustness_caveats.csv",
}

FORBIDDEN_ROBUSTNESS_REPORT_FIELDS: frozenset[str] = frozenset(
    {
        "buy",
        "sell",
        "entry",
        "exit",
        "approved",
        "live",
        "trade_signal",
        "optimal",
        "best",
        "p_l",
        "pnl",
        "profit",
    }
)


def validate_robustness_report_bundle(bundle: Any) -> dict[str, Any]:
    """Validate a robustness report bundle structure."""
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

    _raise_forbidden_fields(bundle["metadata"], name="robustness report metadata")
    for table_name, table in bundle["tables"].items():
        if not isinstance(table_name, str) or not table_name:
            raise ValueError("bundle table names must be non-empty strings")
        _raise_forbidden_fields({"table_name": table_name}, name="robustness table name")
        if not isinstance(table, pd.DataFrame):
            raise TypeError(f"{table_name} must be a pandas DataFrame")
        _raise_forbidden_fields(
            {column: None for column in table.columns},
            name=f"{table_name} columns",
        )
    return bundle


def create_robustness_report_metadata(
    *,
    project_name: str = "SPY Directional Edge Research",
    milestone: str = "36",
    package_name: str | None = None,
    notes: str | None = None,
) -> dict[str, Any]:
    """Create metadata for robustness report artifacts."""
    metadata: dict[str, Any] = {
        "created_at_utc": _created_at_utc(),
        "project_name": project_name,
        "milestone": milestone,
        "report_caveat": "robustness_report_is_descriptive_only",
    }
    optional = {
        "package_name": package_name,
        "notes": notes,
    }
    for key, value in optional.items():
        if value is not None:
            metadata[key] = _json_safe_value(value)
    _raise_forbidden_fields(metadata, name="robustness report metadata")
    return metadata


def build_robustness_report_bundle(
    *,
    oos_validation_results: pd.DataFrame | None = None,
    oos_stability_summary: pd.DataFrame | None = None,
    parameter_sensitivity_summary: pd.DataFrame | None = None,
    parameter_reference_comparison: pd.DataFrame | None = None,
    metadata: Mapping[str, Any] | None = None,
    include_caveat_table: bool = True,
) -> dict[str, Any]:
    """Build a robustness report bundle from existing diagnostic tables."""
    if metadata is not None and not isinstance(metadata, Mapping):
        raise TypeError("metadata must be a mapping when provided")

    bundle_metadata = _json_safe_mapping(metadata or create_robustness_report_metadata())
    if "report_caveat" not in bundle_metadata:
        bundle_metadata["report_caveat"] = "robustness_report_is_descriptive_only"
    _raise_forbidden_fields(bundle_metadata, name="robustness report metadata")

    tables: dict[str, pd.DataFrame] = {}
    if oos_validation_results is not None:
        tables["oos_validation_results"] = _copy_table(
            oos_validation_results,
            "oos_validation_results",
        )
    if oos_stability_summary is not None:
        tables["oos_stability_summary"] = _copy_table(
            oos_stability_summary,
            "oos_stability_summary",
        )
    elif oos_validation_results is not None:
        tables["oos_stability_summary"] = summarize_oos_edge_stability(
            oos_validation_results
        )
    if parameter_sensitivity_summary is not None:
        tables["parameter_sensitivity_summary"] = _copy_table(
            parameter_sensitivity_summary,
            "parameter_sensitivity_summary",
        )
    if parameter_reference_comparison is not None:
        tables["parameter_reference_comparison"] = _copy_table(
            parameter_reference_comparison,
            "parameter_reference_comparison",
        )
    if include_caveat_table:
        tables["robustness_caveats"] = _build_caveat_table(tables)

    bundle = {
        "metadata": bundle_metadata,
        "tables": tables,
    }
    return validate_robustness_report_bundle(bundle)


def summarize_robustness_report_bundle(bundle: Mapping[str, Any]) -> pd.DataFrame:
    """Return a structural summary of robustness report bundle tables."""
    validated = validate_robustness_report_bundle(dict(bundle))
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


def export_robustness_report_bundle_to_csv(
    bundle: Mapping[str, Any],
    output_dir: str | Path,
    *,
    overwrite: bool = False,
) -> dict[str, Path]:
    """Export robustness report tables to deterministic CSV files."""
    validated = validate_robustness_report_bundle(dict(bundle))
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    targets: dict[str, Path] = {
        table_name: output_path / ROBUSTNESS_REPORT_TABLE_FILES.get(
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


def export_robustness_report_bundle_to_json(
    bundle: Mapping[str, Any],
    output_path: str | Path,
    *,
    overwrite: bool = False,
) -> Path:
    """Export a robustness report bundle to one records-oriented JSON file."""
    validated = validate_robustness_report_bundle(dict(bundle))
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


def build_and_export_robustness_report(
    *,
    output_dir: str | Path,
    oos_validation_results: pd.DataFrame | None = None,
    oos_stability_summary: pd.DataFrame | None = None,
    parameter_sensitivity_summary: pd.DataFrame | None = None,
    parameter_reference_comparison: pd.DataFrame | None = None,
    metadata: Mapping[str, Any] | None = None,
    overwrite: bool = False,
) -> dict[str, Any]:
    """Build, export, and summarize a robustness report bundle."""
    report_bundle = build_robustness_report_bundle(
        oos_validation_results=oos_validation_results,
        oos_stability_summary=oos_stability_summary,
        parameter_sensitivity_summary=parameter_sensitivity_summary,
        parameter_reference_comparison=parameter_reference_comparison,
        metadata=metadata,
    )
    written_paths = export_robustness_report_bundle_to_csv(
        report_bundle,
        output_dir,
        overwrite=overwrite,
    )
    return {
        "bundle": report_bundle,
        "written_paths": written_paths,
        "summary": summarize_robustness_report_bundle(report_bundle),
    }


def _copy_table(table: pd.DataFrame, table_name: str) -> pd.DataFrame:
    if not isinstance(table, pd.DataFrame):
        raise TypeError(f"{table_name} must be a pandas DataFrame")
    return table.copy(deep=True)


def _build_caveat_table(tables: Mapping[str, pd.DataFrame]) -> pd.DataFrame:
    rows = [
        {
            "report_section": "overall",
            "caveat": "robustness_report_is_descriptive_only",
        },
        {
            "report_section": "overall",
            "caveat": "positive_diagnostics_do_not_prove_repeatable_edge",
        },
        {
            "report_section": "overall",
            "caveat": "no_strategy_rule_or_execution_instruction_created",
        },
    ]
    for table_name, table in tables.items():
        if "caveats" in table.columns:
            for caveats in table["caveats"]:
                for caveat in _coerce_caveats(caveats):
                    rows.append({"report_section": table_name, "caveat": caveat})
    return (
        pd.DataFrame(rows, columns=["report_section", "caveat"])
        .drop_duplicates()
        .reset_index(drop=True)
    )


def _coerce_caveats(value: Any) -> list[str]:
    if isinstance(value, list):
        return [item for item in value if isinstance(item, str)]
    if isinstance(value, str) and value:
        return [value]
    return []


def _raise_if_exists(paths: Any, *, overwrite: bool) -> None:
    if overwrite:
        return
    existing = [path for path in paths if Path(path).exists()]
    if existing:
        raise FileExistsError(f"Refusing to overwrite existing files: {existing}")


def _dataframe_to_records(table: pd.DataFrame) -> list[dict[str, Any]]:
    records = table.replace({pd.NaT: None}).to_dict(orient="records")
    return [
        {str(key): _json_safe_value(value) for key, value in row.items()}
        for row in records
    ]


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
    if isinstance(value, list):
        return [_json_safe_value(item) for item in value]
    if isinstance(value, tuple):
        return [_json_safe_value(item) for item in value]
    return value


def _created_at_utc() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _raise_forbidden_fields(values: Mapping[str, Any], *, name: str) -> None:
    forbidden = [
        field
        for field in values
        if any(token in str(field).lower() for token in FORBIDDEN_ROBUSTNESS_REPORT_FIELDS)
    ]
    if forbidden:
        raise ValueError(f"{name} contains forbidden fields: {forbidden}")
