"""Versioned, frontend-ready data contracts for research dashboards.

Defines the stable JSON envelope a future dashboard would consume. This is a
descriptive data-contract layer only: payloads carry research tables and
provenance, never trade instructions, signals, allocations, or readiness fields.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

import numpy as np
import pandas as pd


DASHBOARD_SCHEMA_VERSION = "1.0"
DASHBOARD_CONTRACT_CAVEAT = "dashboard_export_is_descriptive_research_data_not_trade_instructions"
DASHBOARD_CONTRACT_KEYS: tuple[str, ...] = (
    "schema_version",
    "payload_type",
    "generated_at_utc",
    "tables",
    "source",
    "dashboard_caveat",
)
FORBIDDEN_DASHBOARD_FIELDS: frozenset[str] = frozenset(
    {
        "buy",
        "sell",
        "entry",
        "exit",
        "approved",
        "live",
        "trade_signal",
        "allocation",
        "portfolio",
        "order",
        "position_size",
        "readiness",
        "optimal",
        "best",
        "p_l",
        "pnl",
    }
)


def build_dashboard_contract(
    *,
    payload_type: str,
    tables: Mapping[str, pd.DataFrame],
    source_metadata: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a versioned dashboard contract envelope from research tables."""
    if not isinstance(payload_type, str) or not payload_type.strip():
        raise ValueError("payload_type must be a non-empty string")
    if not isinstance(tables, Mapping) or not tables:
        raise ValueError("tables must be a non-empty mapping of DataFrames")

    table_records: dict[str, list[dict[str, Any]]] = {}
    for name, table in tables.items():
        if not isinstance(table, pd.DataFrame):
            raise TypeError(f"table {name!r} must be a pandas DataFrame")
        table_records[str(name)] = _dataframe_to_records(table)

    payload = {
        "schema_version": DASHBOARD_SCHEMA_VERSION,
        "payload_type": payload_type.strip(),
        "generated_at_utc": _created_at_utc(),
        "tables": table_records,
        "source": _json_safe_mapping(dict(source_metadata or {})),
        "dashboard_caveat": DASHBOARD_CONTRACT_CAVEAT,
    }
    return validate_dashboard_contract(payload)


def validate_dashboard_contract(payload: Any) -> dict[str, Any]:
    """Validate a dashboard contract envelope's structure and field names."""
    if not isinstance(payload, dict):
        raise TypeError("payload must be a dict")
    missing = [key for key in DASHBOARD_CONTRACT_KEYS if key not in payload]
    if missing:
        raise KeyError(f"payload is missing required keys: {missing}")
    if payload["schema_version"] != DASHBOARD_SCHEMA_VERSION:
        raise ValueError(
            f"unsupported schema_version: {payload['schema_version']!r} "
            f"(expected {DASHBOARD_SCHEMA_VERSION!r})"
        )
    if not isinstance(payload["payload_type"], str) or not payload["payload_type"]:
        raise ValueError("payload_type must be a non-empty string")
    if not isinstance(payload["tables"], Mapping):
        raise TypeError("payload tables must be a mapping")
    if not isinstance(payload["source"], Mapping):
        raise TypeError("payload source must be a mapping")

    _raise_forbidden_fields({"payload_type": payload["payload_type"]}, name="dashboard payload_type")
    for table_name, records in payload["tables"].items():
        _raise_forbidden_fields({"table_name": table_name}, name="dashboard table name")
        if not isinstance(records, list):
            raise TypeError(f"dashboard table {table_name!r} must be a list of records")
        for record in records:
            if not isinstance(record, Mapping):
                raise TypeError(f"dashboard table {table_name!r} rows must be objects")
            _raise_forbidden_fields({key: None for key in record}, name=f"{table_name} columns")
    return payload


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
        if any(token in str(field).lower() for token in FORBIDDEN_DASHBOARD_FIELDS)
    ]
    if forbidden:
        raise ValueError(f"{name} contains forbidden fields: {forbidden}")
