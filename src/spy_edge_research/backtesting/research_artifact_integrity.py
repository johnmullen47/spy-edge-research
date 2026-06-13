"""Research-only artifact integrity checks for package manifests."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

import pandas as pd

from spy_edge_research.backtesting.research_package_manifest import (
    validate_research_package_manifest,
)

ARTIFACT_PATH_CHECK_COLUMNS: list[str] = [
    "package_id",
    "artifact_name",
    "artifact_path",
    "artifact_type",
    "required",
    "exists",
    "path_status",
    "integrity_caveat",
]


def check_manifest_artifact_paths(
    manifest: Mapping[str, Any],
    *,
    base_dir: str | Path | None = None,
) -> pd.DataFrame:
    """Check whether manifest artifact paths exist without reading artifact contents."""
    validated = validate_research_package_manifest(dict(manifest))
    root = Path(base_dir) if base_dir is not None else None
    rows = []
    for record in validated["artifacts"]:
        artifact_path = Path(record["artifact_path"])
        check_path = artifact_path if artifact_path.is_absolute() or root is None else root / artifact_path
        exists = check_path.exists()
        if exists:
            status = "ok"
            caveat = "artifact_path_exists_but_contents_not_reviewed"
        elif record["required"]:
            status = "missing_required"
            caveat = "required_artifact_path_missing"
        else:
            status = "missing_optional"
            caveat = "optional_artifact_path_missing"
        rows.append(
            {
                "package_id": record["package_id"],
                "artifact_name": record["artifact_name"],
                "artifact_path": record["artifact_path"],
                "artifact_type": record["artifact_type"],
                "required": record["required"],
                "exists": exists,
                "path_status": status,
                "integrity_caveat": caveat,
            }
        )
    return pd.DataFrame(rows, columns=ARTIFACT_PATH_CHECK_COLUMNS).sort_values(
        ["package_id", "artifact_name"], kind="mergesort"
    ).reset_index(drop=True)


def check_manifest_required_metadata(
    manifest: Mapping[str, Any],
    required_metadata_keys: Iterable[str],
) -> pd.DataFrame:
    """Check required manifest metadata keys."""
    validated = validate_research_package_manifest(dict(manifest))
    metadata = validated["metadata"]
    rows = []
    for key in sorted(_validate_key_list(required_metadata_keys, "required_metadata_keys")):
        present = key in metadata and metadata[key] is not None
        rows.append(
            {
                "metadata_key": key,
                "present": present,
                "metadata_status": "ok" if present else "missing",
                "integrity_caveat": (
                    "metadata_key_present_for_research_review"
                    if present
                    else "required_metadata_key_missing"
                ),
            }
        )
    return pd.DataFrame(
        rows,
        columns=["metadata_key", "present", "metadata_status", "integrity_caveat"],
    )


def check_expected_artifacts(
    manifest: Mapping[str, Any],
    expected_artifact_names: Iterable[str],
) -> pd.DataFrame:
    """Check whether expected artifact names are listed in the manifest."""
    validated = validate_research_package_manifest(dict(manifest))
    artifact_names = {record["artifact_name"] for record in validated["artifacts"]}
    rows = []
    for name in sorted(_validate_key_list(expected_artifact_names, "expected_artifact_names")):
        present = name in artifact_names
        rows.append(
            {
                "artifact_name": name,
                "present": present,
                "artifact_status": "ok" if present else "missing",
                "integrity_caveat": (
                    "expected_artifact_listed_for_research_review"
                    if present
                    else "expected_artifact_missing_from_manifest"
                ),
            }
        )
    return pd.DataFrame(
        rows,
        columns=["artifact_name", "present", "artifact_status", "integrity_caveat"],
    )


def build_artifact_integrity_report(
    manifest: Mapping[str, Any],
    *,
    expected_artifact_names: Iterable[str] | None = None,
    required_metadata_keys: Iterable[str] | None = None,
    base_dir: str | Path | None = None,
) -> dict[str, pd.DataFrame]:
    """Build deterministic artifact integrity tables for research review."""
    report = {
        "artifact_path_checks": check_manifest_artifact_paths(manifest, base_dir=base_dir),
    }
    if expected_artifact_names is not None:
        report["expected_artifacts"] = check_expected_artifacts(manifest, expected_artifact_names)
    if required_metadata_keys is not None:
        report["required_metadata"] = check_manifest_required_metadata(
            manifest,
            required_metadata_keys,
        )
    report["artifact_integrity_summary"] = summarize_artifact_integrity(report)
    return report


def summarize_artifact_integrity(
    integrity_report: Mapping[str, pd.DataFrame] | pd.DataFrame,
) -> pd.DataFrame:
    """Summarize artifact integrity check tables."""
    if isinstance(integrity_report, pd.DataFrame):
        tables = {"artifact_path_checks": integrity_report}
    elif isinstance(integrity_report, Mapping):
        tables = {
            name: table
            for name, table in integrity_report.items()
            if name != "artifact_integrity_summary"
        }
    else:
        raise TypeError("integrity_report must be a DataFrame or mapping of DataFrames")

    rows = []
    for table_name, table in tables.items():
        if not isinstance(table, pd.DataFrame):
            raise TypeError(f"{table_name} must be a pandas DataFrame")
        if "present" in table.columns:
            issue_count = int((~table["present"].astype(bool)).sum())
        elif "exists" in table.columns:
            issue_count = int((~table["exists"].astype(bool)).sum())
        elif "path_status" in table.columns:
            issue_count = int((table["path_status"] != "ok").sum())
        else:
            issue_count = 0
        rows.append(
            {
                "table_name": table_name,
                "row_count": len(table),
                "issue_count": issue_count,
                "summary_caveat": "artifact_integrity_is_research_inventory_only",
            }
        )
    return pd.DataFrame(rows).sort_values("table_name", kind="mergesort").reset_index(drop=True)


def _validate_key_list(values: Iterable[str], name: str) -> list[str]:
    normalized = list(values)
    if not all(isinstance(value, str) and value for value in normalized):
        raise ValueError(f"{name} must contain non-empty strings")
    return normalized
