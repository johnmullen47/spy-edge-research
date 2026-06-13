"""Named event catalog and research-direction metadata utilities.

The catalog describes already-created named event columns. It does not inspect
forward labels, outcomes, returns, or performance, and it does not create
trading signals or edge claims.
"""

from __future__ import annotations

from collections.abc import Iterable

import pandas as pd

CATALOG_COLUMNS: list[str] = [
    "event_column",
    "event_name",
    "event_family",
    "event_direction",
    "is_directional",
]

VALID_DIRECTIONS: tuple[str, ...] = ("long", "short", "neutral", "unknown")
DIRECTIONAL_DIRECTIONS: tuple[str, ...] = ("long", "short")
EXCLUDED_COLUMN_KEYWORDS: tuple[str, ...] = (
    "forward",
    "future",
    "label",
    "target",
    "outcome",
    "return",
    "profit",
)
PRICE_VOLUME_COLUMNS: tuple[str, ...] = (
    "timestamp",
    "symbol",
    "open",
    "high",
    "low",
    "close",
    "volume",
)


def infer_named_event_direction(event_name: str) -> str:
    """Infer a deterministic research hypothesis direction from an event name."""
    _validate_event_name(event_name)
    name = event_name.lower()

    neutral_patterns = (
        "neutral",
        "regime",
        "chop",
        "range_bound",
        "range_or_unknown",
        "high_volatility",
        "low_volatility",
        "normal_volatility",
    )
    long_patterns = (
        "failed_breakdown",
        "false_break_down",
        "breakdown_retest_failure",
        "resistance_retest_failure",
        "support_retest_hold",
        "bullish",
        "reclaim",
        "bounce",
        "break_above",
        "breakout",
        "higher_low",
        "momentum_up",
        "trend_continuation_up",
    )
    short_patterns = (
        "failed_breakout",
        "false_break_up",
        "breakout_retest_failure",
        "support_retest_failure",
        "resistance_retest_hold",
        "bearish",
        "loss",
        "rejection",
        "break_below",
        "breakdown",
        "lower_high",
        "momentum_down",
        "trend_continuation_down",
    )

    if any(pattern in name for pattern in neutral_patterns):
        return "neutral"
    if "touch" in name and "hold" not in name and "failure" not in name:
        return "neutral"
    if any(pattern in name for pattern in long_patterns):
        return "long"
    if any(pattern in name for pattern in short_patterns):
        return "short"
    return "unknown"


def infer_named_event_family(event_name: str) -> str:
    """Classify a named event into a broad deterministic family."""
    _validate_event_name(event_name)
    name = event_name.lower()

    if "vwap" in name:
        return "vwap"
    if "ema" in name:
        return "ema"
    if "trend_continuation" in name:
        return "trend_continuation"
    if "momentum" in name or "volume" in name or "range_expansion" in name:
        return "momentum_volume"
    if "failed_break" in name or "false_break" in name:
        return "false_break"
    if "retest" in name:
        return "retest"
    if "regime" in name or "context" in name:
        return "regime"
    if "structure" in name or "higher_low" in name or "lower_high" in name:
        return "structure"
    if "zone" in name or "support" in name or "resistance" in name:
        return "zone"
    if "prior_day" in name or "premarket" in name or "pivot" in name:
        return "zone"
    if "break_above" in name or "break_below" in name:
        return "zone"
    return "unknown"


def build_named_event_catalog(
    df: pd.DataFrame | None = None,
    event_columns: Iterable[str] | None = None,
) -> pd.DataFrame:
    """Build a normalized catalog of named event columns.

    If ``event_columns`` is supplied, those names are used in order. Otherwise,
    candidate event columns are inferred from ``df``.
    """
    if df is None and event_columns is None:
        raise ValueError("Either df or event_columns must be provided")

    columns = list(event_columns) if event_columns is not None else _find_event_columns(df)
    rows = []
    for column in columns:
        if not _is_named_event_column(column):
            continue
        direction = infer_named_event_direction(column)
        rows.append(
            {
                "event_column": column,
                "event_name": column,
                "event_family": infer_named_event_family(column),
                "event_direction": direction,
                "is_directional": direction in DIRECTIONAL_DIRECTIONS,
            }
        )
    return pd.DataFrame(rows, columns=CATALOG_COLUMNS)


def filter_directional_event_catalog(
    catalog: pd.DataFrame,
    directions: tuple[str, ...] = DIRECTIONAL_DIRECTIONS,
) -> pd.DataFrame:
    """Return directional catalog rows matching the requested directions."""
    validated = validate_event_catalog(catalog)
    if not isinstance(directions, tuple) or not directions:
        raise ValueError("directions must be a non-empty tuple")
    invalid = [direction for direction in directions if direction not in DIRECTIONAL_DIRECTIONS]
    if invalid:
        raise ValueError(f"directions must contain only {DIRECTIONAL_DIRECTIONS}")
    return validated.loc[
        validated["is_directional"] & validated["event_direction"].isin(directions)
    ].copy()


def validate_event_catalog(
    catalog: pd.DataFrame,
    *,
    require_directional: bool = False,
) -> pd.DataFrame:
    """Validate event catalog schema and metadata values, returning a copy."""
    _require_columns(catalog, CATALOG_COLUMNS)
    result = catalog.copy()

    if not result["event_direction"].isin(VALID_DIRECTIONS).all():
        raise ValueError(f"event_direction values must be one of {VALID_DIRECTIONS}")

    expected_directional = result["event_direction"].isin(DIRECTIONAL_DIRECTIONS)
    if not result["is_directional"].eq(expected_directional).all():
        raise ValueError("is_directional must be True only for long or short events")

    if result["event_column"].isna().any() or result["event_name"].isna().any():
        raise ValueError("event_column and event_name must not contain missing values")

    if require_directional and not bool(expected_directional.any()):
        raise ValueError("Catalog must contain at least one directional event")
    return result


def add_event_hypothesis_columns(
    df: pd.DataFrame,
    catalog: pd.DataFrame,
    output_prefix: str = "event_hypothesis_",
) -> pd.DataFrame:
    """Add non-causal research metadata helper columns for directional events."""
    if not isinstance(output_prefix, str) or not output_prefix:
        raise ValueError("output_prefix must be a non-empty string")

    result = df.copy()
    directional_catalog = filter_directional_event_catalog(catalog)
    for row in directional_catalog.itertuples(index=False):
        event_column = row.event_column
        _require_columns(result, [event_column])
        suffix = event_column.removeprefix("event_")
        output_column = f"{output_prefix}{suffix}"
        event_occurs = result[event_column].fillna(False).astype(bool)
        result[output_column] = pd.Series("neutral", index=result.index, dtype="object")
        result.loc[event_occurs, output_column] = row.event_direction
    return result


def _find_event_columns(df: pd.DataFrame | None) -> list[str]:
    if df is None:
        return []
    return [column for column in df.columns if _is_named_event_column(column)]


def _is_named_event_column(column: str) -> bool:
    if not isinstance(column, str) or not column.startswith("event_"):
        return False
    lowered = column.lower()
    if lowered in PRICE_VOLUME_COLUMNS:
        return False
    return not any(keyword in lowered for keyword in EXCLUDED_COLUMN_KEYWORDS)


def _validate_event_name(event_name: str) -> None:
    if not isinstance(event_name, str) or not event_name:
        raise ValueError("event_name must be a non-empty string")


def _require_columns(df: pd.DataFrame, columns: list[str]) -> None:
    missing = [column for column in columns if column not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")
