"""Generic, behavior-preserving helpers shared across modules.

These consolidate identical private helpers that were copy-defined in many
modules. Behavior matches the original per-module implementations exactly so
they are drop-in replacements. They contain NO forbidden-field logic — each
report module keeps its own ``_raise_forbidden_fields`` with its own field set.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


def require_columns(df: pd.DataFrame, columns: Iterable[str]) -> None:
    """Raise ValueError listing any required columns missing from ``df``."""
    missing = [column for column in columns if column not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")


def validate_positive_int(value: int, name: str) -> None:
    """Raise ValueError unless ``value`` is an int >= 1 (bools rejected)."""
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise ValueError(f"{name} must be an integer greater than or equal to 1")


def normalize_columns(columns: Iterable[str], name: str) -> list[str]:
    """Normalize a column or columns argument to a non-empty list of names."""
    if isinstance(columns, str):
        normalized = [columns]
    else:
        normalized = list(columns)
    if not normalized or not all(isinstance(column, str) and column for column in normalized):
        raise ValueError(f"{name} must contain at least one column name")
    return normalized


def created_at_utc() -> str:
    """Return a deterministic, second-resolution UTC ISO timestamp."""
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def json_safe_value(value: Any) -> Any:
    """Convert pandas/numpy scalars and containers to JSON-serializable values."""
    if value is None:
        return None
    if isinstance(value, pd.Timestamp):
        return None if pd.isna(value) else value.isoformat()
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, np.generic):
        return json_safe_value(value.item())
    if isinstance(value, float) and np.isnan(value):
        return None
    if isinstance(value, Mapping):
        return json_safe_mapping(value)
    if isinstance(value, (list, tuple)):
        return [json_safe_value(item) for item in value]
    return value


def json_safe_mapping(values: Mapping[str, Any]) -> dict[str, Any]:
    """Return a JSON-safe dict with stringified keys."""
    return {str(key): json_safe_value(value) for key, value in values.items()}


def dataframe_to_records(table: pd.DataFrame) -> list[dict[str, Any]]:
    """Convert a DataFrame to JSON-safe records (NaT/NaN -> None)."""
    records = table.replace({pd.NaT: None}).to_dict(orient="records")
    return [{str(key): json_safe_value(value) for key, value in row.items()} for row in records]


def raise_if_exists(paths: Iterable[Any], *, overwrite: bool) -> None:
    """Raise FileExistsError if any path exists and ``overwrite`` is False."""
    if overwrite:
        return
    existing = [path for path in paths if Path(path).exists()]
    if existing:
        raise FileExistsError(f"Refusing to overwrite existing files: {existing}")
