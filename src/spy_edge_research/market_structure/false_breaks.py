"""Causal false-break event features.

False-break events are emitted only when the failure is known at the current
row. They are descriptive feature primitives, not trading signals or edge
claims.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def add_recent_break_context(
    df: pd.DataFrame,
    lookback: int = 20,
    max_bars_after_break: int = 5,
) -> pd.DataFrame:
    """Track recently broken trailing high/low levels causally row by row."""
    _validate_positive_int(lookback, "lookback")
    _validate_positive_int(max_bars_after_break, "max_bars_after_break")

    breakout_col = f"breaks_above_trailing_high_{lookback}"
    breakdown_col = f"breaks_below_trailing_low_{lookback}"
    trailing_high_col = f"trailing_high_{lookback}"
    trailing_low_col = f"trailing_low_{lookback}"
    _require_columns(df, [breakout_col, breakdown_col, trailing_high_col, trailing_low_col])

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

    result[f"recent_breakout_level_{lookback}"] = breakout_levels
    result[f"recent_breakdown_level_{lookback}"] = breakdown_levels
    result[f"bars_since_recent_breakout_{lookback}"] = bars_since_breakout
    result[f"bars_since_recent_breakdown_{lookback}"] = bars_since_breakdown
    return result


def add_false_break_events(
    df: pd.DataFrame,
    lookback: int = 20,
    max_bars_after_break: int = 5,
    close_col: str = "close",
) -> pd.DataFrame:
    """Add false breakout and false breakdown event flags."""
    _validate_positive_int(lookback, "lookback")
    _validate_positive_int(max_bars_after_break, "max_bars_after_break")
    _require_columns(df, [close_col])

    result = df.copy()
    context_cols = [
        f"recent_breakout_level_{lookback}",
        f"recent_breakdown_level_{lookback}",
        f"bars_since_recent_breakout_{lookback}",
        f"bars_since_recent_breakdown_{lookback}",
    ]
    if not _has_columns(result, context_cols):
        result = add_recent_break_context(
            result,
            lookback=lookback,
            max_bars_after_break=max_bars_after_break,
        )

    breakout_level = result[f"recent_breakout_level_{lookback}"]
    breakdown_level = result[f"recent_breakdown_level_{lookback}"]
    bars_since_breakout = result[f"bars_since_recent_breakout_{lookback}"]
    bars_since_breakdown = result[f"bars_since_recent_breakdown_{lookback}"]

    result[f"false_breakout_{lookback}"] = _safe_bool_series(
        breakout_level.notna()
        & bars_since_breakout.notna()
        & (bars_since_breakout > 0)
        & (bars_since_breakout <= max_bars_after_break)
        & (result[close_col] < breakout_level),
        result.index,
    )
    result[f"false_breakdown_{lookback}"] = _safe_bool_series(
        breakdown_level.notna()
        & bars_since_breakdown.notna()
        & (bars_since_breakdown > 0)
        & (bars_since_breakdown <= max_bars_after_break)
        & (result[close_col] > breakdown_level),
        result.index,
    )
    return result


def add_false_break_count_features(
    df: pd.DataFrame,
    lookback: int = 20,
    count_lookback: int = 50,
) -> pd.DataFrame:
    """Add trailing rolling counts of false breakout and breakdown events."""
    _validate_positive_int(lookback, "lookback")
    _validate_positive_int(count_lookback, "count_lookback")
    breakout_col = f"false_breakout_{lookback}"
    breakdown_col = f"false_breakdown_{lookback}"
    _require_columns(df, [breakout_col, breakdown_col])

    result = df.copy()
    result[f"false_breakout_count_{lookback}_{count_lookback}"] = (
        result[breakout_col].fillna(False).astype(bool).astype(int)
        .rolling(count_lookback, min_periods=1)
        .sum()
    )
    result[f"false_breakdown_count_{lookback}_{count_lookback}"] = (
        result[breakdown_col].fillna(False).astype(bool).astype(int)
        .rolling(count_lookback, min_periods=1)
        .sum()
    )
    return result


def add_false_break_features(
    df: pd.DataFrame,
    lookback: int = 20,
    max_bars_after_break: int = 5,
    count_lookback: int = 50,
    close_col: str = "close",
) -> pd.DataFrame:
    """Compose recent-break context, false-break events, and event counts."""
    result = add_recent_break_context(
        df,
        lookback=lookback,
        max_bars_after_break=max_bars_after_break,
    )
    result = add_false_break_events(
        result,
        lookback=lookback,
        max_bars_after_break=max_bars_after_break,
        close_col=close_col,
    )
    return add_false_break_count_features(
        result,
        lookback=lookback,
        count_lookback=count_lookback,
    )


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


def _require_columns(df: pd.DataFrame, columns: list[str]) -> None:
    missing = [column for column in columns if column not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")


def _has_columns(df: pd.DataFrame, columns: list[str]) -> bool:
    return all(column in df.columns for column in columns)


def _validate_positive_int(value: int, name: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise ValueError(f"{name} must be an integer greater than or equal to 1")


def _safe_bool_series(values: pd.Series, index: pd.Index) -> pd.Series:
    return pd.Series(values, index=index).fillna(False).astype(bool)
