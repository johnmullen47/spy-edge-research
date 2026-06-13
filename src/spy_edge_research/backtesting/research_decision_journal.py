"""Research-only decision journal helpers for candidate review."""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

DECISION_JOURNAL_COLUMNS: list[str] = [
    "decision_id",
    "subject_id",
    "subject_type",
    "decision",
    "rationale",
    "evidence_refs",
    "reviewer",
    "created_at_utc",
    "caveats",
    "metadata",
]

VALID_DECISIONS: tuple[str, ...] = (
    "continue_study",
    "needs_more_data",
    "merge_with_related_hypothesis",
    "retire_from_review",
)


def create_research_decision_record(
    *,
    decision_id: str,
    subject_id: str,
    subject_type: str,
    decision: str,
    rationale: str,
    evidence_refs: Iterable[str] | None = None,
    reviewer: str = "research",
    created_at_utc: str | None = None,
    caveats: Iterable[str] | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Create one research decision journal record."""
    record = {
        "decision_id": decision_id,
        "subject_id": subject_id,
        "subject_type": subject_type,
        "decision": decision,
        "rationale": rationale,
        "evidence_refs": list(evidence_refs or []),
        "reviewer": reviewer,
        "created_at_utc": created_at_utc
        or datetime.now(UTC).replace(microsecond=0).isoformat(),
        "caveats": _dedupe_strings(
            ["research_decision_is_not_deployment_approval", *(caveats or [])]
        ),
        "metadata": dict(metadata or {}),
    }
    return validate_research_decision_record(record)


def validate_research_decision_record(record: Mapping[str, Any]) -> dict[str, Any]:
    """Validate one decision journal record."""
    if not isinstance(record, Mapping):
        raise TypeError("record must be a mapping")
    missing = [column for column in DECISION_JOURNAL_COLUMNS if column not in record]
    if missing:
        raise KeyError(f"record is missing required fields: {missing}")
    normalized = {column: record[column] for column in DECISION_JOURNAL_COLUMNS}
    for field in ("decision_id", "subject_id", "subject_type", "rationale", "reviewer", "created_at_utc"):
        _validate_non_empty_string(normalized[field], field)
    if normalized["decision"] not in VALID_DECISIONS:
        raise ValueError(f"decision must be one of {VALID_DECISIONS}")
    if not isinstance(normalized["evidence_refs"], list) or not all(
        isinstance(ref, str) for ref in normalized["evidence_refs"]
    ):
        raise TypeError("evidence_refs must be a list of strings")
    if not isinstance(normalized["caveats"], list) or not all(
        isinstance(caveat, str) for caveat in normalized["caveats"]
    ):
        raise TypeError("caveats must be a list of strings")
    if not isinstance(normalized["metadata"], Mapping):
        raise TypeError("metadata must be a mapping")
    normalized["metadata"] = _json_safe_mapping(normalized["metadata"])
    return normalized


def build_research_decision_journal(records: Iterable[Mapping[str, Any]]) -> pd.DataFrame:
    """Build a deterministic decision journal table."""
    normalized = [validate_research_decision_record(record) for record in records]
    journal = pd.DataFrame(normalized, columns=DECISION_JOURNAL_COLUMNS)
    if journal.empty:
        return journal
    if journal["decision_id"].duplicated().any():
        duplicates = sorted(journal.loc[journal["decision_id"].duplicated(), "decision_id"])
        raise ValueError(f"duplicate decision_id values: {duplicates}")
    return journal.sort_values("decision_id", kind="mergesort").reset_index(drop=True)


def summarize_research_decision_journal(journal: pd.DataFrame) -> pd.DataFrame:
    """Summarize journal decisions without approval language."""
    _require_columns(journal, ["subject_type", "decision"])
    if journal.empty:
        return pd.DataFrame(
            columns=["subject_type", "decision", "decision_count", "summary_caveat"]
        )
    return (
        journal.groupby(["subject_type", "decision"], dropna=False, sort=True)
        .size()
        .reset_index(name="decision_count")
        .assign(summary_caveat="journal_decisions_are_research_dispositions")
    )


def write_research_decision_journal(
    journal: pd.DataFrame,
    output_path: str | Path,
    *,
    metadata: Mapping[str, Any] | None = None,
    overwrite: bool = False,
) -> Path:
    """Write decision journal to deterministic JSON."""
    validated = build_research_decision_journal(journal.to_dict("records"))
    target = Path(output_path)
    if target.exists() and not overwrite:
        raise FileExistsError(f"{target} already exists")
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "metadata": _json_safe_mapping(metadata or {}),
        "research_decisions": [
            _json_safe_mapping(record) for record in validated.to_dict("records")
        ],
    }
    target.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return target


def read_research_decision_journal(path: str | Path) -> pd.DataFrame:
    """Read and validate a decision journal JSON artifact."""
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError("decision journal payload must be a dict")
    if "research_decisions" not in payload:
        raise KeyError("decision journal payload is missing research_decisions")
    if not isinstance(payload["research_decisions"], list):
        raise TypeError("research_decisions must be a list")
    return build_research_decision_journal(payload["research_decisions"])


def _require_columns(df: pd.DataFrame, columns: list[str]) -> None:
    missing = [column for column in columns if column not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")


def _validate_non_empty_string(value: Any, name: str) -> None:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{name} must be a non-empty string")


def _dedupe_strings(values: Iterable[str]) -> list[str]:
    result = []
    seen = set()
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result


def _json_safe_mapping(mapping: Mapping[str, Any]) -> dict[str, Any]:
    return {str(key): _json_safe_value(value) for key, value in mapping.items()}


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
