"""Causal retest event features for known zones and broken levels.

Retest events are descriptive feature primitives only. They are not trading
signals, confidence scores, edge claims, or performance analytics.
"""

from __future__ import annotations

from numbers import Real

import numpy as np
import pandas as pd


STANDARD_ZONE_RETESTS: tuple[tuple[str, str], ...] = (
    ("prior_day_high", "resistance"),
    ("prior_day_low", "support"),
    ("premarket_high", "resistance"),
    ("premarket_low", "support"),
    ("pivot_high", "resistance"),
    ("pivot_low", "support"),
)


def add_zone_retest_events(
    df: pd.DataFrame,
    zone_name: str,
    zone_type: str,
    close_col: str = "close",
    high_col: str = "high",
    low_col: str = "low",
) -> pd.DataFrame:
    """Add current-candle retest touch, hold, and failure flags for one zone."""
    _validate_zone_type(zone_type)
    center_col = f"{zone_name}_zone_center"
    lower_col = f"{zone_name}_zone_lower"
    upper_col = f"{zone_name}_zone_upper"
    _require_columns(df, [center_col, lower_col, upper_col, close_col, high_col, low_col])

    result = df.copy()
    event_prefix = f"{zone_name}_{zone_type}"
    zone_available = (
        result[center_col].notna()
        & result[lower_col].notna()
        & result[upper_col].notna()
    )
    touch = (
        zone_available
        & (result[high_col] >= result[lower_col])
        & (result[low_col] <= result[upper_col])
    )

    if zone_type == "support":
        hold = touch & (result[close_col] > result[upper_col])
        failure = touch & (result[close_col] < result[lower_col])
    else:
        hold = touch & (result[close_col] < result[lower_col])
        failure = touch & (result[close_col] > result[upper_col])

    result[f"{event_prefix}_retest_touch"] = _safe_bool_series(touch, result.index)
    result[f"{event_prefix}_retest_hold"] = _safe_bool_series(hold, result.index)
    result[f"{event_prefix}_retest_failure"] = _safe_bool_series(failure, result.index)
    return result


def add_standard_zone_retest_events(
    df: pd.DataFrame,
    close_col: str = "close",
    high_col: str = "high",
    low_col: str = "low",
) -> pd.DataFrame:
    """Add retest events for all available standard support/resistance zones."""
    _require_columns(df, [close_col, high_col, low_col])

    result = df.copy()
    for zone_name, zone_type in STANDARD_ZONE_RETESTS:
        if _has_zone_columns(result, zone_name):
            result = add_zone_retest_events(
                result,
                zone_name=zone_name,
                zone_type=zone_type,
                close_col=close_col,
                high_col=high_col,
                low_col=low_col,
            )

    if _has_zone_columns(result, "prior_day_close"):
        result = add_zone_retest_events(
            result,
            zone_name="prior_day_close",
            zone_type="support",
            close_col=close_col,
            high_col=high_col,
            low_col=low_col,
        )
        result = add_zone_retest_events(
            result,
            zone_name="prior_day_close",
            zone_type="resistance",
            close_col=close_col,
            high_col=high_col,
            low_col=low_col,
        )
    return result


def add_retest_count_features(
    df: pd.DataFrame,
    event_prefix: str,
    lookback: int = 50,
) -> pd.DataFrame:
    """Add trailing counts of retest touch, hold, and failure events."""
    _validate_positive_int(lookback, "lookback")
    event_cols = [
        f"{event_prefix}_retest_touch",
        f"{event_prefix}_retest_hold",
        f"{event_prefix}_retest_failure",
    ]
    _require_columns(df, event_cols)

    result = df.copy()
    for event_name, event_col in [
        ("touch", event_cols[0]),
        ("hold", event_cols[1]),
        ("failure", event_cols[2]),
    ]:
        count_col = f"{event_prefix}_retest_{event_name}_count_{lookback}"
        result[count_col] = (
            result[event_col].fillna(False).astype(bool).astype(int)
            .rolling(lookback, min_periods=1)
            .sum()
        )
    return result


def price_to_retest_zone_bounds(
    price: pd.Series | float,
    tolerance_bps: float = 10.0,
) -> tuple[pd.Series | float, pd.Series | float]:
    """Convert a price level into symmetric lower and upper retest bounds."""
    _validate_positive_number(tolerance_bps, "tolerance_bps")
    half_width = price * tolerance_bps / 10_000
    return price - half_width, price + half_width


def add_break_retest_events(
    df: pd.DataFrame,
    lookback: int = 20,
    max_bars_after_break: int = 5,
    tolerance_bps: float = 10.0,
    close_col: str = "close",
    high_col: str = "high",
    low_col: str = "low",
) -> pd.DataFrame:
    """Add retest features for recently broken trailing high/low levels."""
    _validate_positive_int(lookback, "lookback")
    _validate_positive_int(max_bars_after_break, "max_bars_after_break")
    _validate_positive_number(tolerance_bps, "tolerance_bps")

    breakout_col = f"breaks_above_trailing_high_{lookback}"
    breakdown_col = f"breaks_below_trailing_low_{lookback}"
    trailing_high_col = f"trailing_high_{lookback}"
    trailing_low_col = f"trailing_low_{lookback}"
    _require_columns(
        df,
        [
            breakout_col,
            breakdown_col,
            trailing_high_col,
            trailing_low_col,
            close_col,
            high_col,
            low_col,
        ],
    )

    result = df.copy()
    breakout_levels, bars_since_breakout = _track_recent_levels(
        result[breakout_col],
        result[trailing_high_col],
        max_bars_after_break=max_bars_after_break,
    )
    breakdown_levels, bars_since_breakdown = _track_recent_levels(
        result[breakdown_col],
        result[trailing_low_col],
        max_bars_after_break=max_bars_after_break,
    )

    result[f"active_breakout_retest_level_{lookback}"] = breakout_levels
    result[f"bars_since_breakout_{lookback}"] = bars_since_breakout
    (
        result[f"breakout_retest_zone_lower_{lookback}"],
        result[f"breakout_retest_zone_upper_{lookback}"],
    ) = price_to_retest_zone_bounds(breakout_levels, tolerance_bps=tolerance_bps)
    _add_break_retest_event_columns(
        result,
        prefix=f"breakout_retest",
        lookback=lookback,
        direction="breakout",
        bars_since=bars_since_breakout,
        close_col=close_col,
        high_col=high_col,
        low_col=low_col,
    )

    result[f"active_breakdown_retest_level_{lookback}"] = breakdown_levels
    result[f"bars_since_breakdown_{lookback}"] = bars_since_breakdown
    (
        result[f"breakdown_retest_zone_lower_{lookback}"],
        result[f"breakdown_retest_zone_upper_{lookback}"],
    ) = price_to_retest_zone_bounds(breakdown_levels, tolerance_bps=tolerance_bps)
    _add_break_retest_event_columns(
        result,
        prefix=f"breakdown_retest",
        lookback=lookback,
        direction="breakdown",
        bars_since=bars_since_breakdown,
        close_col=close_col,
        high_col=high_col,
        low_col=low_col,
    )
    return result


def add_retest_features(
    df: pd.DataFrame,
    trailing_lookback: int = 20,
    max_bars_after_break: int = 5,
    tolerance_bps: float = 10.0,
    count_lookback: int = 50,
    close_col: str = "close",
    high_col: str = "high",
    low_col: str = "low",
) -> pd.DataFrame:
    """Compose available causal retest event features and trailing counts."""
    _validate_positive_int(count_lookback, "count_lookback")
    _require_columns(df, [close_col, high_col, low_col])

    result = add_standard_zone_retest_events(
        df,
        close_col=close_col,
        high_col=high_col,
        low_col=low_col,
    )
    if _has_columns(
        result,
        [
            f"breaks_above_trailing_high_{trailing_lookback}",
            f"breaks_below_trailing_low_{trailing_lookback}",
            f"trailing_high_{trailing_lookback}",
            f"trailing_low_{trailing_lookback}",
        ],
    ):
        result = add_break_retest_events(
            result,
            lookback=trailing_lookback,
            max_bars_after_break=max_bars_after_break,
            tolerance_bps=tolerance_bps,
            close_col=close_col,
            high_col=high_col,
            low_col=low_col,
        )

    for prefix in _retest_event_prefixes(result):
        result = add_retest_count_features(result, prefix, lookback=count_lookback)
    return result


def _add_break_retest_event_columns(
    result: pd.DataFrame,
    prefix: str,
    lookback: int,
    direction: str,
    bars_since: pd.Series,
    close_col: str,
    high_col: str,
    low_col: str,
) -> None:
    lower = result[f"{prefix}_zone_lower_{lookback}"]
    upper = result[f"{prefix}_zone_upper_{lookback}"]
    active_after_break = bars_since.notna() & (bars_since > 0)
    touch = active_after_break & lower.notna() & upper.notna()
    touch &= (result[high_col] >= lower) & (result[low_col] <= upper)

    if direction == "breakout":
        hold = touch & (result[close_col] > upper)
        failure = touch & (result[close_col] < lower)
    else:
        hold = touch & (result[close_col] < lower)
        failure = touch & (result[close_col] > upper)

    result[f"{prefix}_touch_{lookback}"] = _safe_bool_series(touch, result.index)
    result[f"{prefix}_hold_{lookback}"] = _safe_bool_series(hold, result.index)
    result[f"{prefix}_failure_{lookback}"] = _safe_bool_series(failure, result.index)


def _track_recent_levels(
    break_events: pd.Series,
    break_levels: pd.Series,
    max_bars_after_break: int,
) -> tuple[pd.Series, pd.Series]:
    active_level = np.nan
    active_bars_since = np.nan
    levels: list[float] = []
    bars_since_values: list[float] = []

    for did_break, level in zip(
        break_events.fillna(False).astype(bool),
        pd.to_numeric(break_levels, errors="coerce"),
    ):
        if did_break and pd.notna(level):
            active_level = float(level)
            active_bars_since = 0.0
        elif pd.notna(active_bars_since):
            active_bars_since += 1.0
            if active_bars_since > max_bars_after_break:
                active_level = np.nan
                active_bars_since = np.nan

        levels.append(active_level)
        bars_since_values.append(active_bars_since)

    return (
        pd.Series(levels, index=break_events.index, dtype="float64"),
        pd.Series(bars_since_values, index=break_events.index, dtype="float64"),
    )


def _retest_event_prefixes(df: pd.DataFrame) -> list[str]:
    suffix = "_retest_touch"
    indexed_suffix = "_retest_touch_"
    prefixes: list[str] = []
    for column in df.columns:
        if column.endswith(suffix):
            prefix = column[: -len(suffix)]
        elif indexed_suffix in column:
            prefix = column.rsplit("_", maxsplit=1)[0]
        else:
            continue
        if _has_columns(
            df,
            [
                f"{prefix}_retest_touch",
                f"{prefix}_retest_hold",
                f"{prefix}_retest_failure",
            ],
        ):
            prefixes.append(prefix)
    return list(dict.fromkeys(prefixes))


def _has_zone_columns(df: pd.DataFrame, zone_name: str) -> bool:
    return _has_columns(
        df,
        [
            f"{zone_name}_zone_center",
            f"{zone_name}_zone_lower",
            f"{zone_name}_zone_upper",
        ],
    )


def _validate_zone_type(zone_type: str) -> None:
    if zone_type not in {"support", "resistance"}:
        raise ValueError("zone_type must be either 'support' or 'resistance'")


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
