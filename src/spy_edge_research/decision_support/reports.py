"""Decision support report bundles with deterministic CSV/JSON export.

Packages the human-review records and summary into the project's standard
``{metadata, tables}`` bundle, validated against the decision_support
forbidden-field guard. The bundle is a review artifact only — it authorizes
nothing and recommends no size or order.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pandas as pd

from spy_edge_research._internal._common import (
    dataframe_to_records,
    json_safe_mapping,
    raise_if_exists,
)
from spy_edge_research.decision_support.contracts import (
    DECISION_SUPPORT_REPORT_CAVEAT,
    DECISION_SUPPORT_TABLE_FILES,
    create_decision_support_metadata,
    raise_forbidden_decision_support_fields,
    validate_decision_support_report_bundle,
)


def build_decision_support_report_bundle(
    *,
    records: pd.DataFrame,
    summary: pd.DataFrame | None = None,
    metadata: Mapping[str, Any] | None = None,
    include_caveat_table: bool = True,
) -> dict[str, Any]:
    """Assemble a decision support report bundle."""
    if metadata is not None and not isinstance(metadata, Mapping):
        raise TypeError("metadata must be a mapping when provided")
    if not isinstance(records, pd.DataFrame):
        raise TypeError("records must be a pandas DataFrame")

    bundle_metadata = json_safe_mapping(
        dict(metadata or create_decision_support_metadata())
    )
    bundle_metadata.setdefault("report_caveat", DECISION_SUPPORT_REPORT_CAVEAT)
    raise_forbidden_decision_support_fields(
        bundle_metadata, name="decision support metadata"
    )

    tables: dict[str, pd.DataFrame] = {
        "decision_support_review": records.copy(deep=True)
    }
    if summary is not None:
        if not isinstance(summary, pd.DataFrame):
            raise TypeError("summary must be a pandas DataFrame when provided")
        tables["decision_support_summary"] = summary.copy(deep=True)
    if include_caveat_table:
        tables["decision_support_caveats"] = _build_caveat_table(tables)

    return validate_decision_support_report_bundle(
        {"metadata": bundle_metadata, "tables": tables}
    )


def summarize_decision_support_report_bundle(bundle: Mapping[str, Any]) -> pd.DataFrame:
    """Return a structural summary of decision support bundle tables."""
    validated = validate_decision_support_report_bundle(dict(bundle))
    rows = [
        {"table_name": name, "row_count": len(table), "column_count": len(table.columns)}
        for name, table in validated["tables"].items()
    ]
    summary = pd.DataFrame(rows, columns=["table_name", "row_count", "column_count"])
    if summary.empty:
        return summary
    return summary.sort_values("table_name", kind="mergesort").reset_index(drop=True)


def export_decision_support_report_bundle_to_csv(
    bundle: Mapping[str, Any],
    output_dir: str | Path,
    *,
    overwrite: bool = False,
) -> dict[str, Path]:
    """Export decision support tables to deterministic CSV files."""
    validated = validate_decision_support_report_bundle(dict(bundle))
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    targets: dict[str, Path] = {
        name: output_path / DECISION_SUPPORT_TABLE_FILES.get(name, f"{name}.csv")
        for name in validated["tables"]
    }
    targets["metadata"] = output_path / "metadata.json"
    raise_if_exists(list(targets.values()), overwrite=overwrite)
    written: dict[str, Path] = {}
    for name, table in validated["tables"].items():
        table.to_csv(targets[name], index=False)
        written[name] = targets[name]
    targets["metadata"].write_text(
        json.dumps(json_safe_mapping(validated["metadata"]), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    written["metadata"] = targets["metadata"]
    return written


def export_decision_support_report_bundle_to_json(
    bundle: Mapping[str, Any],
    output_path: str | Path,
    *,
    overwrite: bool = False,
) -> Path:
    """Export a decision support bundle to one records-oriented JSON file."""
    validated = validate_decision_support_report_bundle(dict(bundle))
    target = Path(output_path)
    if target.exists() and not overwrite:
        raise FileExistsError(f"{target} already exists")
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "metadata": json_safe_mapping(validated["metadata"]),
        "tables": {
            name: dataframe_to_records(table)
            for name, table in validated["tables"].items()
        },
    }
    target.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return target


def _build_caveat_table(tables: Mapping[str, pd.DataFrame]) -> pd.DataFrame:
    rows = [
        {"report_section": "overall", "caveat": DECISION_SUPPORT_REPORT_CAVEAT},
        {
            "report_section": "overall",
            "caveat": "recommendation_requires_explicit_human_approval_not_an_instruction",
        },
        {
            "report_section": "overall",
            "caveat": "broker_and_live_execution_remain_separate_gated_modules",
        },
    ]
    for table_name, table in tables.items():
        for column in table.columns:
            if "caveat" not in column:
                continue
            for caveat in table[column].dropna().unique().tolist():
                rows.append({"report_section": table_name, "caveat": caveat})
    return (
        pd.DataFrame(rows, columns=["report_section", "caveat"])
        .drop_duplicates()
        .reset_index(drop=True)
    )
