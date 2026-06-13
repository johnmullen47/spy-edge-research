"""Research-only candidate rule object helpers.

Candidate rule objects describe validated research hypotheses in a structured
form for audit and later analysis. They are not trading signals, strategy
instructions, recommendations, execution rules, or deployment approvals.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

import pandas as pd

from spy_edge_research.backtesting.candidate_edges import validate_candidate_edge

from spy_edge_research._internal._common import (
    json_safe_mapping as _json_safe_mapping,
    require_columns as _require_columns,
)


CANDIDATE_RULE_OBJECT_COLUMNS: list[str] = [
    "rule_object_id",
    "candidate_id",
    "candidate_type",
    "name",
    "direction",
    "horizon",
    "research_state",
    "condition_spec",
    "evaluation_spec",
    "validation_summary",
    "robustness_summary",
    "required_columns",
    "caveats",
    "reproducibility_metadata",
]

VALID_RESEARCH_STATES: tuple[str, ...] = (
    "research_only",
    "needs_more_validation",
    "insufficient_evidence",
    "retired_from_review",
)

FORBIDDEN_RULE_OBJECT_FIELDS: frozenset[str] = frozenset(
    {
        "buy",
        "sell",
        "entry",
        "exit",
        "approved",
        "live",
        "trade_signal",
        "order",
        "broker",
        "route",
        "execution",
        "profit",
        "pnl",
        "p_l",
    }
)


def create_candidate_rule_object(
    *,
    rule_object_id: str,
    candidate: Mapping[str, Any],
    condition_spec: Mapping[str, Any],
    evaluation_spec: Mapping[str, Any],
    validation_summary: Mapping[str, Any] | None = None,
    robustness_summary: Mapping[str, Any] | None = None,
    required_columns: Iterable[str] | None = None,
    research_state: str = "research_only",
    caveats: Iterable[str] | None = None,
    reproducibility_metadata: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Create and validate one research-only candidate rule object."""
    candidate_record = validate_candidate_edge(candidate)
    record = {
        "rule_object_id": rule_object_id,
        "candidate_id": candidate_record["candidate_id"],
        "candidate_type": candidate_record["candidate_type"],
        "name": candidate_record["name"],
        "direction": candidate_record["direction"],
        "horizon": candidate_record["horizon"],
        "research_state": research_state,
        "condition_spec": dict(condition_spec),
        "evaluation_spec": dict(evaluation_spec),
        "validation_summary": dict(validation_summary or {}),
        "robustness_summary": dict(robustness_summary or {}),
        "required_columns": _normalize_columns(required_columns or []),
        "caveats": _dedupe_strings(
            [
                "research_only_rule_object",
                "not_a_trading_signal",
                "not_deployment_approval",
                *candidate_record["caveats"],
                *(caveats or []),
            ]
        ),
        "reproducibility_metadata": dict(reproducibility_metadata or {}),
    }
    return validate_candidate_rule_object(record)


def validate_candidate_rule_object(rule_object: Mapping[str, Any]) -> dict[str, Any]:
    """Validate one candidate rule object and return a normalized copy."""
    if not isinstance(rule_object, Mapping):
        raise TypeError("rule_object must be a mapping")
    missing = [
        column
        for column in CANDIDATE_RULE_OBJECT_COLUMNS
        if column not in rule_object
    ]
    if missing:
        raise KeyError(f"rule_object is missing required fields: {missing}")

    record = {column: rule_object[column] for column in CANDIDATE_RULE_OBJECT_COLUMNS}
    for field in ("rule_object_id", "candidate_id", "candidate_type", "name", "direction", "horizon"):
        _validate_non_empty_string(record[field], field)
    if record["research_state"] not in VALID_RESEARCH_STATES:
        raise ValueError(f"research_state must be one of {VALID_RESEARCH_STATES}")
    for field in (
        "condition_spec",
        "evaluation_spec",
        "validation_summary",
        "robustness_summary",
        "reproducibility_metadata",
    ):
        if not isinstance(record[field], Mapping):
            raise TypeError(f"{field} must be a mapping")
        _raise_forbidden_fields(record[field], name=field)
        record[field] = _json_safe_mapping(record[field])

    record["required_columns"] = _normalize_columns(record["required_columns"])
    if not isinstance(record["caveats"], list) or not all(
        isinstance(caveat, str) for caveat in record["caveats"]
    ):
        raise TypeError("caveats must be a list of strings")
    _raise_forbidden_fields({column: None for column in record}, name="rule object fields")
    return record


def build_candidate_rule_catalog(
    rule_objects: Iterable[Mapping[str, Any]],
) -> pd.DataFrame:
    """Build a deterministic catalog of research-only candidate rule objects."""
    records = [validate_candidate_rule_object(rule_object) for rule_object in rule_objects]
    catalog = pd.DataFrame(records, columns=CANDIDATE_RULE_OBJECT_COLUMNS)
    if catalog.empty:
        return catalog
    if catalog["rule_object_id"].duplicated().any():
        duplicates = sorted(
            catalog.loc[catalog["rule_object_id"].duplicated(), "rule_object_id"]
        )
        raise ValueError(f"duplicate rule_object_id values: {duplicates}")
    return catalog.sort_values("rule_object_id", kind="mergesort").reset_index(drop=True)


def summarize_candidate_rule_catalog(catalog: pd.DataFrame) -> pd.DataFrame:
    """Summarize candidate rule object inventory without ranking or approval."""
    _require_columns(
        catalog,
        [
            "candidate_type",
            "direction",
            "horizon",
            "research_state",
            "required_columns",
        ],
    )
    if catalog.empty:
        return pd.DataFrame(
            columns=[
                "candidate_type",
                "direction",
                "horizon",
                "research_state",
                "rule_object_count",
                "unique_required_column_count",
                "summary_caveat",
            ]
        )

    rows = []
    group_columns = ["candidate_type", "direction", "horizon", "research_state"]
    for keys, group in catalog.groupby(group_columns, dropna=False, sort=True):
        required_columns = sorted(
            {
                column
                for columns in group["required_columns"]
                for column in _normalize_columns(columns)
            }
        )
        rows.append(
            {
                **dict(zip(group_columns, keys)),
                "rule_object_count": int(len(group)),
                "unique_required_column_count": len(required_columns),
                "summary_caveat": "candidate_rule_catalog_is_research_only",
            }
        )
    return pd.DataFrame(rows).reset_index(drop=True)


def write_candidate_rule_catalog(
    catalog: pd.DataFrame,
    output_path: str | Path,
    *,
    metadata: Mapping[str, Any] | None = None,
    overwrite: bool = False,
) -> Path:
    """Write a candidate rule object catalog to deterministic JSON."""
    validated = build_candidate_rule_catalog(_records_from_frame(catalog))
    target = Path(output_path)
    if target.exists() and not overwrite:
        raise FileExistsError(f"{target} already exists")
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "metadata": _json_safe_mapping(metadata or {}),
        "candidate_rule_objects": [
            _json_safe_mapping(record) for record in validated.to_dict("records")
        ],
    }
    target.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return target


def read_candidate_rule_catalog(path: str | Path) -> pd.DataFrame:
    """Read and validate a candidate rule object catalog JSON file."""
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError("candidate rule catalog payload must be a dict")
    if "candidate_rule_objects" not in payload:
        raise KeyError("candidate rule catalog payload is missing candidate_rule_objects")
    if not isinstance(payload["candidate_rule_objects"], list):
        raise TypeError("candidate_rule_objects must be a list")
    return build_candidate_rule_catalog(payload["candidate_rule_objects"])


def _records_from_frame(catalog: pd.DataFrame) -> list[dict[str, Any]]:
    return [
        {key: _none_if_missing(value) for key, value in record.items()}
        for record in catalog.to_dict("records")
    ]


def _none_if_missing(value: Any) -> Any:
    if isinstance(value, (list, dict)):
        return value
    if pd.isna(value):
        return None
    return value


def _normalize_columns(columns: Iterable[str]) -> list[str]:
    if isinstance(columns, str):
        normalized = [columns]
    else:
        normalized = list(columns)
    if not all(isinstance(column, str) and column for column in normalized):
        raise ValueError("columns must contain only non-empty column names")
    return normalized


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


def _raise_forbidden_fields(values: Mapping[str, Any], *, name: str) -> None:
    forbidden = [
        field
        for field in values
        if any(token in str(field).lower() for token in FORBIDDEN_RULE_OBJECT_FIELDS)
    ]
    if forbidden:
        raise ValueError(f"{name} contains forbidden fields: {forbidden}")
