"""Causal support/resistance zone feature helpers."""

from __future__ import annotations

from numbers import Real

import numpy as np
import pandas as pd

from spy_edge_research.support_resistance.premarket_levels import add_premarket_levels
from spy_edge_research.support_resistance.prior_day_levels import add_prior_day_levels


STANDARD_LEVELS: tuple[tuple[str, str], ...] = (
    ("prior_day_high", "prior_day_high"),
    ("prior_day_low", "prior_day_low"),
    ("prior_day_close", "prior_day_close"),
    ("premarket_high", "premarket_high"),
    ("premarket_low", "premarket_low"),
    ("last_confirmed_pivot_high", "pivot_high"),
    ("last_confirmed_pivot_low", "pivot_low"),
)

STANDARD_ZONE_CENTERS: tuple[tuple[str, str], ...] = (
    ("prior_day_high_zone_center", "prior_day_high"),
    ("prior_day_low_zone_center", "prior_day_low"),
    ("prior_day_close_zone_center", "prior_day_close"),
    ("premarket_high_zone_center", "premarket_high"),
    ("premarket_low_zone_center", "premarket_low"),
    ("pivot_high_zone_center", "pivot_high"),
    ("pivot_low_zone_center", "pivot_low"),
)


def price_to_zone_bounds(
    price: pd.Series | float,
    width_bps: float = 10.0,
) -> tuple[pd.Series | float, pd.Series | float]:
    """Convert a center price to symmetric lower and upper zone bounds."""
    _validate_positive_number(width_bps, "width_bps")
    half_width = price * width_bps / 10_000
    return price - half_width, price + half_width


def add_level_zone(
    df: pd.DataFrame,
    level_col: str,
    zone_name: str,
    width_bps: float = 10.0,
    close_col: str = "close",
) -> pd.DataFrame:
    """Add a simple price zone around one level column."""
    _validate_positive_number(width_bps, "width_bps")
    _require_columns(df, [level_col, close_col])

    result = df.copy()
    center_col = f"{zone_name}_zone_center"
    lower_col = f"{zone_name}_zone_lower"
    upper_col = f"{zone_name}_zone_upper"

    result[center_col] = result[level_col]
    result[lower_col], result[upper_col] = price_to_zone_bounds(
        result[center_col], width_bps=width_bps
    )
    result[f"{zone_name}_in_zone"] = _safe_bool_series(
        result[close_col].between(result[lower_col], result[upper_col], inclusive="both"),
        result.index,
    )
    result[f"{zone_name}_distance_to_center"] = result[close_col] - result[center_col]
    result[f"{zone_name}_distance_to_lower"] = result[close_col] - result[lower_col]
    result[f"{zone_name}_distance_to_upper"] = result[close_col] - result[upper_col]
    return result


def add_standard_level_zones(
    df: pd.DataFrame,
    width_bps: float = 10.0,
    close_col: str = "close",
) -> pd.DataFrame:
    """Add zones for all standard level columns present in ``df``."""
    _validate_positive_number(width_bps, "width_bps")
    _require_columns(df, [close_col])

    result = df.copy()
    for level_col, zone_name in STANDARD_LEVELS:
        if level_col in result.columns:
            result = add_level_zone(
                result,
                level_col=level_col,
                zone_name=zone_name,
                width_bps=width_bps,
                close_col=close_col,
            )
    return result


def add_repeated_touch_counts(
    df: pd.DataFrame,
    zone_center_col: str,
    zone_lower_col: str,
    zone_upper_col: str,
    zone_name: str,
    lookback: int = 50,
    high_col: str = "high",
    low_col: str = "low",
) -> pd.DataFrame:
    """Add causal trailing counts of candle ranges overlapping a zone."""
    _validate_positive_int(lookback, "lookback")
    _require_columns(df, [zone_center_col, zone_lower_col, zone_upper_col, high_col, low_col])

    result = df.copy()
    touch_col = f"{zone_name}_touch"
    count_col = f"{zone_name}_touch_count_{lookback}"
    zone_available = result[zone_center_col].notna() & result[zone_lower_col].notna() & result[
        zone_upper_col
    ].notna()
    result[touch_col] = _safe_bool_series(
        zone_available
        & (result[high_col] >= result[zone_lower_col])
        & (result[low_col] <= result[zone_upper_col]),
        result.index,
    )
    result[count_col] = result[touch_col].astype(int).rolling(lookback, min_periods=1).sum()
    return result


def add_nearest_standard_zones(
    df: pd.DataFrame,
    close_col: str = "close",
) -> pd.DataFrame:
    """Add nearest available standard support and resistance zone centers."""
    _require_columns(df, [close_col])

    result = df.copy()
    candidate_columns = [
        (column, name) for column, name in STANDARD_ZONE_CENTERS if column in result.columns
    ]
    support_names: list[str | float] = []
    support_distances: list[float] = []
    resistance_names: list[str | float] = []
    resistance_distances: list[float] = []

    for _, row in result.iterrows():
        close = row[close_col]
        support_name = np.nan
        support_distance = np.nan
        resistance_name = np.nan
        resistance_distance = np.nan

        for column, name in candidate_columns:
            center = row[column]
            if pd.isna(center):
                continue
            distance = abs(close - center)
            if center <= close and (pd.isna(support_distance) or distance < support_distance):
                support_name = name
                support_distance = distance
            if center >= close and (
                pd.isna(resistance_distance) or distance < resistance_distance
            ):
                resistance_name = name
                resistance_distance = distance

        support_names.append(support_name)
        support_distances.append(support_distance)
        resistance_names.append(resistance_name)
        resistance_distances.append(resistance_distance)

    result["nearest_support_zone"] = pd.Series(support_names, index=result.index, dtype="object")
    result["nearest_support_zone_distance"] = pd.Series(
        support_distances, index=result.index, dtype="float64"
    )
    result["nearest_resistance_zone"] = pd.Series(
        resistance_names, index=result.index, dtype="object"
    )
    result["nearest_resistance_zone_distance"] = pd.Series(
        resistance_distances, index=result.index, dtype="float64"
    )
    return result


def add_support_resistance_features(
    df: pd.DataFrame,
    timezone: str = "America/New_York",
    zone_width_bps: float = 10.0,
    touch_lookback: int = 50,
    timestamp_col: str = "timestamp",
    close_col: str = "close",
) -> pd.DataFrame:
    """Compose causal support/resistance level and zone features only."""
    _validate_positive_number(zone_width_bps, "zone_width_bps")
    _validate_positive_int(touch_lookback, "touch_lookback")
    _require_columns(df, [timestamp_col, close_col])

    result = add_prior_day_levels(
        df,
        timestamp_col=timestamp_col,
        close_col=close_col,
        timezone=timezone,
    )
    result = add_premarket_levels(
        result,
        timestamp_col=timestamp_col,
        close_col=close_col,
        timezone=timezone,
    )
    result = add_standard_level_zones(
        result,
        width_bps=zone_width_bps,
        close_col=close_col,
    )

    for _, zone_name in STANDARD_LEVELS:
        center_col = f"{zone_name}_zone_center"
        lower_col = f"{zone_name}_zone_lower"
        upper_col = f"{zone_name}_zone_upper"
        if _has_columns(result, [center_col, lower_col, upper_col]):
            result = add_repeated_touch_counts(
                result,
                zone_center_col=center_col,
                zone_lower_col=lower_col,
                zone_upper_col=upper_col,
                zone_name=zone_name,
                lookback=touch_lookback,
            )

    return add_nearest_standard_zones(result, close_col=close_col)


def _require_columns(df: pd.DataFrame, columns: list[str]) -> None:
    missing = [column for column in columns if column not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")


def _has_columns(df: pd.DataFrame, columns: list[str]) -> bool:
    return all(column in df.columns for column in columns)


def _validate_positive_int(value: int, name: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise ValueError(f"{name} must be an integer greater than or equal to 1")


def _validate_positive_number(value: float, name: str) -> None:
    if not isinstance(value, Real) or isinstance(value, bool) or value <= 0:
        raise ValueError(f"{name} must be greater than 0")


def _safe_bool_series(values: pd.Series, index: pd.Index) -> pd.Series:
    return pd.Series(values, index=index).fillna(False).astype(bool)
