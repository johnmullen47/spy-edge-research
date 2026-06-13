"""Research-only candidate retirement and merge lineage helpers."""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from spy_edge_research._internal._common import (
    require_columns as _require_columns,
)

LINEAGE_COLUMNS: list[str] = [
    "lineage_id",
    "action",
    "source_ids",
    "target_id",
    "rationale",
    "created_at_utc",
    "caveats",
    "metadata",
]

VALID_LINEAGE_ACTIONS: tuple[str, ...] = ("retire_from_review", "merge_hypotheses")


def create_candidate_lineage_record(
    *,
    lineage_id: str,
    action: str,
    source_ids: Iterable[str],
    rationale: str,
    target_id: str | None = None,
    created_at_utc: str | None = None,
    caveats: Iterable[str] | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Create one candidate lineage record."""
    record = {
        "lineage_id": lineage_id,
        "action": action,
        "source_ids": list(source_ids),
        "target_id": target_id,
        "rationale": rationale,
        "created_at_utc": created_at_utc
        or datetime.now(UTC).replace(microsecond=0).isoformat(),
        "caveats": _dedupe_strings(["lineage_record_preserves_research_history", *(caveats or [])]),
        "metadata": dict(metadata or {}),
    }
    return validate_candidate_lineage_record(record)


def validate_candidate_lineage_record(record: Mapping[str, Any]) -> dict[str, Any]:
    """Validate one lineage record."""
    if not isinstance(record, Mapping):
        raise TypeError("record must be a mapping")
    missing = [column for column in LINEAGE_COLUMNS if column not in record]
    if missing:
        raise KeyError(f"record is missing required fields: {missing}")
    normalized = {column: record[column] for column in LINEAGE_COLUMNS}
    _validate_non_empty_string(normalized["lineage_id"], "lineage_id")
    if normalized["action"] not in VALID_LINEAGE_ACTIONS:
        raise ValueError(f"action must be one of {VALID_LINEAGE_ACTIONS}")
    if not isinstance(normalized["source_ids"], list) or not normalized["source_ids"]:
        raise ValueError("source_ids must be a non-empty list")
    if not all(isinstance(source_id, str) and source_id for source_id in normalized["source_ids"]):
        raise ValueError("source_ids must contain non-empty strings")
    if normalized["action"] == "merge_hypotheses":
        _validate_non_empty_string(normalized["target_id"], "target_id")
    if normalized["target_id"] is not None and not isinstance(normalized["target_id"], str):
        raise TypeError("target_id must be a string when provided")
    _validate_non_empty_string(normalized["rationale"], "rationale")
    _validate_non_empty_string(normalized["created_at_utc"], "created_at_utc")
    if not isinstance(normalized["caveats"], list) or not all(isinstance(c, str) for c in normalized["caveats"]):
        raise TypeError("caveats must be a list of strings")
    if not isinstance(normalized["metadata"], Mapping):
        raise TypeError("metadata must be a mapping")
    normalized["metadata"] = dict(normalized["metadata"])
    return normalized


def build_candidate_lineage_table(records: Iterable[Mapping[str, Any]]) -> pd.DataFrame:
    """Build a deterministic lineage table."""
    table = pd.DataFrame([validate_candidate_lineage_record(record) for record in records], columns=LINEAGE_COLUMNS)
    if table.empty:
        return table
    if table["lineage_id"].duplicated().any():
        duplicates = sorted(table.loc[table["lineage_id"].duplicated(), "lineage_id"])
        raise ValueError(f"duplicate lineage_id values: {duplicates}")
    return table.sort_values("lineage_id", kind="mergesort").reset_index(drop=True)


def summarize_candidate_lineage(lineage_table: pd.DataFrame) -> pd.DataFrame:
    """Summarize lineage actions."""
    _require_columns(lineage_table, ["action", "source_ids"])
    if lineage_table.empty:
        return pd.DataFrame(columns=["action", "record_count", "source_id_count", "summary_caveat"])
    rows = []
    for action, group in lineage_table.groupby("action", sort=True, dropna=False):
        source_ids = {source for sources in group["source_ids"] for source in sources}
        rows.append(
            {
                "action": action,
                "record_count": len(group),
                "source_id_count": len(source_ids),
                "summary_caveat": "lineage_summary_is_research_history_only",
            }
        )
    return pd.DataFrame(rows)


def write_candidate_lineage_table(
    lineage_table: pd.DataFrame,
    output_path: str | Path,
    *,
    metadata: Mapping[str, Any] | None = None,
    overwrite: bool = False,
) -> Path:
    """Write lineage table to deterministic JSON."""
    validated = build_candidate_lineage_table(lineage_table.to_dict("records"))
    target = Path(output_path)
    if target.exists() and not overwrite:
        raise FileExistsError(f"{target} already exists")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(
            {
                "metadata": dict(metadata or {}),
                "candidate_lineage": validated.to_dict("records"),
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    return target


def read_candidate_lineage_table(path: str | Path) -> pd.DataFrame:
    """Read and validate lineage JSON."""
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError("lineage payload must be a dict")
    if "candidate_lineage" not in payload:
        raise KeyError("lineage payload is missing candidate_lineage")
    if not isinstance(payload["candidate_lineage"], list):
        raise TypeError("candidate_lineage must be a list")
    return build_candidate_lineage_table(payload["candidate_lineage"])


def _dedupe_strings(values: Iterable[str]) -> list[str]:
    result = []
    seen = set()
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result


def _validate_non_empty_string(value: Any, name: str) -> None:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{name} must be a non-empty string")

