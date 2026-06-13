"""Research-only candidate edge registry helpers.

Candidate records describe hypotheses worth further validation. They are not
strategy rules, trading signals, recommendations, or profitability claims.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

import pandas as pd

CANDIDATE_EDGE_COLUMNS: list[str] = [
    "candidate_id",
    "candidate_type",
    "name",
    "direction",
    "horizon",
    "context",
    "sample_size",
    "baseline_sample_size",
    "expectancy",
    "baseline_expectancy",
    "expectancy_difference",
    "hit_rate",
    "baseline_hit_rate",
    "hit_rate_difference",
    "caveats",
    "data_start",
    "data_end",
    "reproducibility_metadata",
]

VALID_CANDIDATE_TYPES: tuple[str, ...] = ("event", "sequence", "conditional_event")
VALID_DIRECTIONS: tuple[str, ...] = ("long", "short", "neutral", "unknown")


def create_candidate_edge(
    *,
    candidate_id: str,
    candidate_type: str,
    name: str,
    direction: str,
    horizon: str,
    sample_size: int,
    baseline_sample_size: int,
    expectancy: float,
    baseline_expectancy: float,
    hit_rate: float,
    baseline_hit_rate: float,
    context: Mapping[str, Any] | None = None,
    caveats: Iterable[str] | None = None,
    data_start: str | None = None,
    data_end: str | None = None,
    reproducibility_metadata: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Create and validate one candidate edge record."""
    record = {
        "candidate_id": candidate_id,
        "candidate_type": candidate_type,
        "name": name,
        "direction": direction,
        "horizon": horizon,
        "context": dict(context or {}),
        "sample_size": sample_size,
        "baseline_sample_size": baseline_sample_size,
        "expectancy": float(expectancy),
        "baseline_expectancy": float(baseline_expectancy),
        "expectancy_difference": float(expectancy) - float(baseline_expectancy),
        "hit_rate": float(hit_rate),
        "baseline_hit_rate": float(baseline_hit_rate),
        "hit_rate_difference": float(hit_rate) - float(baseline_hit_rate),
        "caveats": list(caveats or []),
        "data_start": data_start,
        "data_end": data_end,
        "reproducibility_metadata": dict(reproducibility_metadata or {}),
    }
    return validate_candidate_edge(record)


def validate_candidate_edge(candidate: Mapping[str, Any]) -> dict[str, Any]:
    """Validate one candidate edge record and return a normalized copy."""
    if not isinstance(candidate, Mapping):
        raise TypeError("candidate must be a mapping")
    missing = [column for column in CANDIDATE_EDGE_COLUMNS if column not in candidate]
    if missing:
        raise KeyError(f"candidate is missing required fields: {missing}")

    record = {column: candidate[column] for column in CANDIDATE_EDGE_COLUMNS}
    _validate_non_empty_string(record["candidate_id"], "candidate_id")
    _validate_choice(record["candidate_type"], VALID_CANDIDATE_TYPES, "candidate_type")
    _validate_non_empty_string(record["name"], "name")
    _validate_choice(record["direction"], VALID_DIRECTIONS, "direction")
    _validate_non_empty_string(record["horizon"], "horizon")
    _validate_non_negative_int(record["sample_size"], "sample_size")
    _validate_non_negative_int(record["baseline_sample_size"], "baseline_sample_size")

    for field in (
        "expectancy",
        "baseline_expectancy",
        "expectancy_difference",
        "hit_rate",
        "baseline_hit_rate",
        "hit_rate_difference",
    ):
        record[field] = _validate_number(record[field], field)

    if not isinstance(record["context"], Mapping):
        raise TypeError("context must be a mapping")
    if not isinstance(record["reproducibility_metadata"], Mapping):
        raise TypeError("reproducibility_metadata must be a mapping")
    if not isinstance(record["caveats"], list) or not all(
        isinstance(caveat, str) for caveat in record["caveats"]
    ):
        raise TypeError("caveats must be a list of strings")
    if record["data_start"] is not None and not isinstance(record["data_start"], str):
        raise TypeError("data_start must be a string when provided")
    if record["data_end"] is not None and not isinstance(record["data_end"], str):
        raise TypeError("data_end must be a string when provided")

    record["context"] = _json_safe_mapping(record["context"])
    record["reproducibility_metadata"] = _json_safe_mapping(
        record["reproducibility_metadata"]
    )
    return record


def build_candidate_edge_registry(
    candidates: Iterable[Mapping[str, Any]],
) -> pd.DataFrame:
    """Build a deterministic candidate edge registry table."""
    records = [
        validate_candidate_edge(candidate)
        for candidate in candidates
    ]
    registry = pd.DataFrame(records, columns=CANDIDATE_EDGE_COLUMNS)
    if registry.empty:
        return registry
    if registry["candidate_id"].duplicated().any():
        duplicates = sorted(registry.loc[registry["candidate_id"].duplicated(), "candidate_id"])
        raise ValueError(f"duplicate candidate_id values: {duplicates}")
    return registry.sort_values("candidate_id", kind="mergesort").reset_index(drop=True)


def rank_candidate_edges(
    registry: pd.DataFrame,
    *,
    sort_by: str = "expectancy_difference",
    ascending: bool = False,
    min_sample_size: int | None = None,
) -> pd.DataFrame:
    """Sort candidate records for research review without validation claims."""
    _require_columns(registry, [sort_by, "sample_size"])
    ranked = registry.copy()
    if min_sample_size is not None:
        _validate_non_negative_int(min_sample_size, "min_sample_size")
        ranked = ranked.loc[ranked["sample_size"].ge(min_sample_size)].copy()
    ranked = ranked.sort_values(
        by=sort_by,
        ascending=ascending,
        na_position="last",
        kind="mergesort",
    ).reset_index(drop=True)
    ranked.insert(0, "research_rank", range(1, len(ranked) + 1))
    return ranked


def write_candidate_edge_registry(
    registry: pd.DataFrame,
    output_path: str | Path,
    *,
    metadata: Mapping[str, Any] | None = None,
    overwrite: bool = False,
) -> Path:
    """Write a candidate edge registry to deterministic JSON."""
    validated = build_candidate_edge_registry(registry.to_dict("records"))
    target = Path(output_path)
    if target.exists() and not overwrite:
        raise FileExistsError(f"{target} already exists")
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "metadata": _json_safe_mapping(metadata or {}),
        "candidate_edges": [_json_safe_mapping(record) for record in validated.to_dict("records")],
    }
    target.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return target


def read_candidate_edge_registry(path: str | Path) -> pd.DataFrame:
    """Read and validate a candidate edge registry JSON file."""
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError("candidate edge registry payload must be a dict")
    if "candidate_edges" not in payload:
        raise KeyError("candidate edge registry payload is missing candidate_edges")
    if not isinstance(payload["candidate_edges"], list):
        raise TypeError("candidate_edges must be a list")
    return build_candidate_edge_registry(payload["candidate_edges"])


def _require_columns(df: pd.DataFrame, columns: list[str]) -> None:
    missing = [column for column in columns if column not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")


def _validate_non_empty_string(value: Any, name: str) -> None:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{name} must be a non-empty string")


def _validate_choice(value: Any, choices: tuple[str, ...], name: str) -> None:
    if value not in choices:
        raise ValueError(f"{name} must be one of {choices}")


def _validate_non_negative_int(value: Any, name: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"{name} must be an integer greater than or equal to 0")


def _validate_number(value: Any, name: str) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise TypeError(f"{name} must be numeric")
    return float(value)


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
    return value
