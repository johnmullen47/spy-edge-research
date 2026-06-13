"""Research-only comparison reports for research package inventories."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from spy_edge_research.backtesting.research_package_manifest import (
    validate_research_package_manifest,
)

from spy_edge_research._internal._common import (
    dataframe_to_records as _dataframe_to_records,
    json_safe_mapping as _json_safe_mapping,
    raise_if_exists as _raise_if_exists,
    require_columns as _require_columns,
)

PACKAGE_COMPARISON_TABLE_FILES: dict[str, str] = {
    "artifact_coverage": "artifact_coverage.csv",
    "maturity_comparison": "maturity_comparison.csv",
    "risk_summary": "risk_summary.csv",
    "decision_distribution": "decision_distribution.csv",
    "lineage_counts": "lineage_counts.csv",
    "caveat_inventory": "caveat_inventory.csv",
}


def compare_research_package_artifacts(
    manifests: Mapping[str, Mapping[str, Any]],
) -> pd.DataFrame:
    """Compare manifest artifact coverage across packages."""
    rows = []
    for label, manifest in sorted(manifests.items()):
        validated = validate_research_package_manifest(dict(manifest))
        artifact_names = sorted({record["artifact_name"] for record in validated["artifacts"]})
        artifact_types = sorted({record["artifact_type"] for record in validated["artifacts"]})
        rows.append(
            {
                "package_id": str(validated["metadata"].get("package_id", label)),
                "package_label": str(label),
                "artifact_count": len(validated["artifacts"]),
                "required_artifact_count": sum(
                    bool(record["required"]) for record in validated["artifacts"]
                ),
                "artifact_names": artifact_names,
                "artifact_types": artifact_types,
                "comparison_caveat": "artifact_coverage_is_inventory_only",
            }
        )
    return pd.DataFrame(rows).sort_values("package_id", kind="mergesort").reset_index(drop=True)


def compare_research_package_maturity(
    maturity_tables: Mapping[str, pd.DataFrame],
) -> pd.DataFrame:
    """Compare maturity table structure and distributions without ranking packages."""
    rows = []
    for label, table in sorted(maturity_tables.items()):
        _require_dataframe(table, label)
        _require_columns(table, ["research_maturity_score", "maturity_band"])
        rows.append(
            {
                "package_label": str(label),
                "row_count": len(table),
                "mean_research_maturity_score": (
                    float(table["research_maturity_score"].mean()) if not table.empty else np.nan
                ),
                "maturity_bands": _value_counts(table, "maturity_band"),
                "comparison_caveat": "maturity_comparison_is_not_trade_readiness",
            }
        )
    return pd.DataFrame(rows).sort_values("package_label", kind="mergesort").reset_index(drop=True)


def compare_research_package_risks(
    risk_summaries: Mapping[str, pd.DataFrame],
) -> pd.DataFrame:
    """Compare risk report summaries by table shape only."""
    rows = []
    for label, table in sorted(risk_summaries.items()):
        _require_dataframe(table, label)
        if table.empty:
            rows.append(
                {
                    "package_label": str(label),
                    "risk_table_count": 0,
                    "risk_row_count": 0,
                    "risk_sections": [],
                    "comparison_caveat": "risk_comparison_is_diagnostic_only",
                }
            )
            continue
        risk_sections = (
            sorted(table["table_name"].dropna().astype(str).unique().tolist())
            if "table_name" in table.columns
            else list(table.columns)
        )
        rows.append(
            {
                "package_label": str(label),
                "risk_table_count": len(risk_sections),
                "risk_row_count": len(table),
                "risk_sections": risk_sections,
                "comparison_caveat": "risk_comparison_is_diagnostic_only",
            }
        )
    return pd.DataFrame(rows).sort_values("package_label", kind="mergesort").reset_index(drop=True)


def compare_research_package_decisions(
    decision_summaries: Mapping[str, pd.DataFrame],
) -> pd.DataFrame:
    """Compare decision distributions across packages."""
    rows = []
    for label, table in sorted(decision_summaries.items()):
        _require_dataframe(table, label)
        _require_columns(table, ["decision"])
        count_column = "decision_count" if "decision_count" in table.columns else None
        for decision in sorted(table["decision"].dropna().astype(str).unique()):
            mask = table["decision"].astype(str) == decision
            decision_count = (
                int(table.loc[mask, count_column].sum()) if count_column else int(mask.sum())
            )
            rows.append(
                {
                    "package_label": str(label),
                    "decision": decision,
                    "decision_count": decision_count,
                    "comparison_caveat": "decision_distribution_is_research_disposition_only",
                }
            )
    return pd.DataFrame(
        rows,
        columns=["package_label", "decision", "decision_count", "comparison_caveat"],
    ).sort_values(["package_label", "decision"], kind="mergesort").reset_index(drop=True)


def compare_research_package_lineage(
    lineage_summaries: Mapping[str, pd.DataFrame],
) -> pd.DataFrame:
    """Compare lineage action counts across packages."""
    rows = []
    for label, table in sorted(lineage_summaries.items()):
        _require_dataframe(table, label)
        _require_columns(table, ["action"])
        count_column = "record_count" if "record_count" in table.columns else None
        for action in sorted(table["action"].dropna().astype(str).unique()):
            mask = table["action"].astype(str) == action
            record_count = int(table.loc[mask, count_column].sum()) if count_column else int(mask.sum())
            rows.append(
                {
                    "package_label": str(label),
                    "lineage_action": action,
                    "record_count": record_count,
                    "comparison_caveat": "lineage_comparison_preserves_research_history_only",
                }
            )
    return pd.DataFrame(
        rows,
        columns=["package_label", "lineage_action", "record_count", "comparison_caveat"],
    ).sort_values(["package_label", "lineage_action"], kind="mergesort").reset_index(drop=True)


def build_research_package_comparison_bundle(
    *,
    manifests: Mapping[str, Mapping[str, Any]],
    maturity_tables: Mapping[str, pd.DataFrame] | None = None,
    risk_summaries: Mapping[str, pd.DataFrame] | None = None,
    decision_summaries: Mapping[str, pd.DataFrame] | None = None,
    lineage_summaries: Mapping[str, pd.DataFrame] | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build deterministic package comparison tables."""
    tables: dict[str, pd.DataFrame] = {
        "artifact_coverage": compare_research_package_artifacts(manifests),
        "caveat_inventory": _comparison_caveat_table(),
    }
    if maturity_tables is not None:
        tables["maturity_comparison"] = compare_research_package_maturity(maturity_tables)
    if risk_summaries is not None:
        tables["risk_summary"] = compare_research_package_risks(risk_summaries)
    if decision_summaries is not None:
        tables["decision_distribution"] = compare_research_package_decisions(decision_summaries)
    if lineage_summaries is not None:
        tables["lineage_counts"] = compare_research_package_lineage(lineage_summaries)
    return validate_research_package_comparison_bundle(
        {
            "metadata": {
                "comparison_caveat": "package_comparison_has_no_best_package_claim",
                **dict(metadata or {}),
            },
            "tables": tables,
        }
    )


def validate_research_package_comparison_bundle(bundle: Any) -> dict[str, Any]:
    """Validate research package comparison bundle structure."""
    if not isinstance(bundle, dict):
        raise TypeError("bundle must be a dict")
    if not isinstance(bundle.get("metadata"), dict):
        raise TypeError("bundle metadata must be a dict")
    if not isinstance(bundle.get("tables"), dict):
        raise TypeError("bundle tables must be a dict")
    for name, table in bundle["tables"].items():
        if not isinstance(name, str) or not name:
            raise ValueError("table names must be non-empty strings")
        _require_dataframe(table, name)
    return bundle


def summarize_research_package_comparison_bundle(bundle: Mapping[str, Any]) -> pd.DataFrame:
    """Summarize package comparison bundle tables."""
    validated = validate_research_package_comparison_bundle(dict(bundle))
    return pd.DataFrame(
        [
            {
                "table_name": name,
                "row_count": len(table),
                "column_count": len(table.columns),
                "summary_caveat": "package_comparison_summary_is_research_only",
            }
            for name, table in validated["tables"].items()
        ]
    ).sort_values("table_name", kind="mergesort").reset_index(drop=True)


def export_research_package_comparison_bundle_to_csv(
    bundle: Mapping[str, Any],
    output_dir: str | Path,
    *,
    overwrite: bool = False,
) -> dict[str, Path]:
    """Export package comparison tables to CSV."""
    validated = validate_research_package_comparison_bundle(dict(bundle))
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    targets = {
        name: output_path / PACKAGE_COMPARISON_TABLE_FILES.get(name, f"{name}.csv")
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


def export_research_package_comparison_bundle_to_json(
    bundle: Mapping[str, Any],
    output_path: str | Path,
    *,
    overwrite: bool = False,
) -> Path:
    """Export package comparison bundle to records-oriented JSON."""
    validated = validate_research_package_comparison_bundle(dict(bundle))
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


def _comparison_caveat_table() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"comparison_section": "overall", "caveat": "comparison_is_descriptive_only"},
            {"comparison_section": "overall", "caveat": "comparison_does_not_rank_packages"},
        ]
    )


def _value_counts(table: pd.DataFrame, column: str) -> dict[str, int]:
    return {
        str(key): int(value)
        for key, value in table[column].astype(str).value_counts(sort=True).sort_index().items()
    }


def _require_dataframe(table: Any, name: str) -> None:
    if not isinstance(table, pd.DataFrame):
        raise TypeError(f"{name} must be a pandas DataFrame")

