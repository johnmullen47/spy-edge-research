"""Research-only evidence traceability matrix helpers."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

import pandas as pd

from spy_edge_research.backtesting.research_package_manifest import (
    validate_research_package_manifest,
)

from spy_edge_research._internal._common import (
    require_columns as _require_columns,
)

TRACEABILITY_COLUMNS: list[str] = [
    "candidate_id",
    "rule_object_id",
    "has_rule_object",
    "has_candidate_record",
    "has_oos_results",
    "has_robustness_report",
    "has_risk_report",
    "has_decision_record",
    "has_lineage_record",
    "has_manifest_artifact",
    "missing_evidence",
    "traceability_caveat",
]


def build_research_traceability_matrix(
    *,
    rule_catalog: pd.DataFrame | None = None,
    candidate_registry: pd.DataFrame | None = None,
    oos_results: pd.DataFrame | None = None,
    robustness_reports: pd.DataFrame | Mapping[str, Any] | None = None,
    risk_reports: pd.DataFrame | Mapping[str, Any] | None = None,
    decision_journal: pd.DataFrame | None = None,
    lineage_table: pd.DataFrame | None = None,
    package_manifest: Mapping[str, Any] | None = None,
    candidate_ids: Iterable[str] | None = None,
) -> pd.DataFrame:
    """Build an evidence-presence matrix for research candidates."""
    rule_ids = _id_map(rule_catalog, "candidate_id", "rule_object_id")
    ids = set(candidate_ids or [])
    ids.update(rule_ids)
    ids.update(_ids_from_table(candidate_registry, "candidate_id"))
    ids.update(_ids_from_table(oos_results, "candidate_id"))
    ids.update(_ids_from_generic_reports(robustness_reports))
    ids.update(_ids_from_generic_reports(risk_reports))
    ids.update(_ids_from_table(decision_journal, "subject_id"))
    ids.update(_ids_from_lineage(lineage_table))
    ids.update(_ids_from_manifest(package_manifest))

    rows = []
    for candidate_id in sorted(_validate_ids(ids)):
        checks = {
            "rule_object": candidate_id in rule_ids,
            "candidate_record": candidate_id in _ids_from_table(candidate_registry, "candidate_id"),
            "oos_results": candidate_id in _ids_from_table(oos_results, "candidate_id"),
            "robustness_report": candidate_id in _ids_from_generic_reports(robustness_reports),
            "risk_report": candidate_id in _ids_from_generic_reports(risk_reports),
            "decision_record": candidate_id in _ids_from_table(decision_journal, "subject_id"),
            "lineage_record": candidate_id in _ids_from_lineage(lineage_table),
            "manifest_artifact": candidate_id in _ids_from_manifest(package_manifest),
        }
        missing = [name for name, present in checks.items() if not present]
        rows.append(
            {
                "candidate_id": candidate_id,
                "rule_object_id": rule_ids.get(candidate_id),
                "has_rule_object": checks["rule_object"],
                "has_candidate_record": checks["candidate_record"],
                "has_oos_results": checks["oos_results"],
                "has_robustness_report": checks["robustness_report"],
                "has_risk_report": checks["risk_report"],
                "has_decision_record": checks["decision_record"],
                "has_lineage_record": checks["lineage_record"],
                "has_manifest_artifact": checks["manifest_artifact"],
                "missing_evidence": missing,
                "traceability_caveat": (
                    "research_evidence_links_present"
                    if not missing
                    else "missing_research_evidence_links"
                ),
            }
        )
    return pd.DataFrame(rows, columns=TRACEABILITY_COLUMNS)


def summarize_research_traceability(traceability_matrix: pd.DataFrame) -> pd.DataFrame:
    """Summarize evidence coverage in a traceability matrix."""
    _require_columns(traceability_matrix, TRACEABILITY_COLUMNS)
    evidence_columns = [column for column in TRACEABILITY_COLUMNS if column.startswith("has_")]
    if traceability_matrix.empty:
        return pd.DataFrame(
            columns=[
                "evidence_type",
                "candidate_count",
                "present_count",
                "missing_count",
                "summary_caveat",
            ]
        )
    rows = []
    candidate_count = len(traceability_matrix)
    for column in evidence_columns:
        present_count = int(traceability_matrix[column].astype(bool).sum())
        rows.append(
            {
                "evidence_type": column.removeprefix("has_"),
                "candidate_count": candidate_count,
                "present_count": present_count,
                "missing_count": candidate_count - present_count,
                "summary_caveat": "traceability_summary_is_research_evidence_inventory",
            }
        )
    return pd.DataFrame(rows).sort_values("evidence_type", kind="mergesort").reset_index(drop=True)


def _id_map(
    table: pd.DataFrame | None,
    candidate_column: str,
    value_column: str,
) -> dict[str, str]:
    if table is None:
        return {}
    _require_dataframe(table, "rule_catalog")
    _require_columns(table, [candidate_column, value_column])
    result = {}
    for _, row in table.iterrows():
        candidate_id = row[candidate_column]
        value = row[value_column]
        if isinstance(candidate_id, str) and candidate_id and isinstance(value, str) and value:
            result[candidate_id] = value
    return result


def _ids_from_table(table: pd.DataFrame | None, column: str) -> set[str]:
    if table is None:
        return set()
    _require_dataframe(table, column)
    if column not in table.columns:
        return set()
    return {value for value in table[column].dropna().astype(str) if value}


def _ids_from_generic_reports(report: pd.DataFrame | Mapping[str, Any] | None) -> set[str]:
    if report is None:
        return set()
    if isinstance(report, pd.DataFrame):
        ids = set()
        for column in ("candidate_id", "subject_id", "rule_object_id"):
            ids.update(_ids_from_table(report, column))
        return ids
    if isinstance(report, Mapping):
        ids = set()
        for value in report.values():
            if isinstance(value, pd.DataFrame):
                ids.update(_ids_from_generic_reports(value))
        return ids
    raise TypeError("report inputs must be DataFrames, mappings of DataFrames, or None")


def _ids_from_lineage(lineage_table: pd.DataFrame | None) -> set[str]:
    if lineage_table is None:
        return set()
    _require_dataframe(lineage_table, "lineage_table")
    ids = set()
    if "source_ids" in lineage_table.columns:
        for sources in lineage_table["source_ids"]:
            if isinstance(sources, list):
                ids.update(str(source) for source in sources if source)
    if "target_id" in lineage_table.columns:
        ids.update(_ids_from_table(lineage_table, "target_id"))
    return {candidate_id for candidate_id in ids if candidate_id != "None"}


def _ids_from_manifest(manifest: Mapping[str, Any] | None) -> set[str]:
    if manifest is None:
        return set()
    validated = validate_research_package_manifest(dict(manifest))
    ids = set()
    for record in validated["artifacts"]:
        metadata = record.get("metadata", {})
        if not isinstance(metadata, Mapping):
            continue
        for key in ("candidate_id", "subject_id", "rule_object_id"):
            value = metadata.get(key)
            if isinstance(value, str) and value:
                ids.add(value)
    return ids


def _validate_ids(values: Iterable[Any]) -> list[str]:
    ids = [value for value in values if isinstance(value, str) and value]
    return sorted(set(ids))


def _require_dataframe(table: Any, name: str) -> None:
    if not isinstance(table, pd.DataFrame):
        raise TypeError(f"{name} must be a pandas DataFrame")

