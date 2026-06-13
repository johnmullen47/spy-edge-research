"""Causal price-action event primitives.

The helpers in this module emit primitive boolean event columns and trailing
reference levels without using future bars. They are building blocks for later
research, not complete trading signals.
"""

from __future__ import annotations

from numbers import Real
import re

import numpy as np
import pandas as pd


def crosses_above(left: pd.Series, right: pd.Series) -> pd.Series:
    """Return True when left crosses from at-or-below to above right."""
    previous_condition = left.shift(1) <= right.shift(1)
    current_condition = left > right
    return _safe_bool_series(previous_condition & current_condition, left.index)


def crosses_below(left: pd.Series, right: pd.Series) -> pd.Series:
    """Return True when left crosses from at-or-above to below right."""
    previous_condition = left.shift(1) >= right.shift(1)
    current_condition = left < right
    return _safe_bool_series(previous_condition & current_condition, left.index)


def add_crossover_events(
    df: pd.DataFrame,
    left_col: str,
    right_col: str,
    prefix: str | None = None,
) -> pd.DataFrame:
    """Add causal cross-above and cross-below event columns."""
    _require_columns(df, [left_col, right_col])

    result = df.copy()
    column_prefix = prefix or f"{_safe_name(left_col)}_cross_{_safe_name(right_col)}"
    result[f"{column_prefix}_crosses_above"] = crosses_above(
        result[left_col], result[right_col]
    )
    result[f"{column_prefix}_crosses_below"] = crosses_below(
        result[left_col], result[right_col]
    )
    return result


def add_trailing_break_events(
    df: pd.DataFrame,
    lookback: int = 20,
    price_col: str = "close",
    high_col: str = "high",
    low_col: str = "low",
) -> pd.DataFrame:
    """Add prior trailing high/low levels and current-price break events."""
    _validate_positive_int(lookback, "lookback")
    _require_columns(df, [price_col, high_col, low_col])

    result = df.copy()
    trailing_high_col = f"trailing_high_{lookback}"
    trailing_low_col = f"trailing_low_{lookback}"
    breaks_above_col = f"breaks_above_trailing_high_{lookback}"
    breaks_below_col = f"breaks_below_trailing_low_{lookback}"

    result[trailing_high_col] = result[high_col].shift(1).rolling(lookback).max()
    result[trailing_low_col] = result[low_col].shift(1).rolling(lookback).min()
    result[breaks_above_col] = _safe_bool_series(
        result[price_col] > result[trailing_high_col], result.index
    )
    result[breaks_below_col] = _safe_bool_series(
        result[price_col] < result[trailing_low_col], result.index
    )
    return result


def add_candle_body_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add candle body, wick, and simple candle-direction features."""
    _require_columns(df, ["open", "high", "low", "close"])

    result = df.copy()
    result["candle_range"] = result["high"] - result["low"]
    result["candle_body"] = result["close"] - result["open"]
    result["candle_body_abs"] = result["candle_body"].abs()
    result["candle_body_pct_of_range"] = result["candle_body_abs"].div(
        result["candle_range"].replace(0, np.nan)
    )
    result["upper_wick"] = result["high"] - result[["open", "close"]].max(axis=1)
    result["lower_wick"] = result[["open", "close"]].min(axis=1) - result["low"]
    result["bullish_candle"] = _safe_bool_series(result["close"] > result["open"], result.index)
    result["bearish_candle"] = _safe_bool_series(result["close"] < result["open"], result.index)
    result["doji_like_candle"] = _safe_bool_series(
        result["candle_body_pct_of_range"] <= 0.1, result.index
    )
    return result


def add_single_bar_pattern_events(df: pd.DataFrame) -> pd.DataFrame:
    """Add inside-bar and outside-bar events using only current and prior bars."""
    _require_columns(df, ["high", "low"])

    result = df.copy()
    result["inside_bar"] = _safe_bool_series(
        (result["high"] < result["high"].shift(1))
        & (result["low"] > result["low"].shift(1)),
        result.index,
    )
    result["outside_bar"] = _safe_bool_series(
        (result["high"] > result["high"].shift(1))
        & (result["low"] < result["low"].shift(1)),
        result.index,
    )
    return result


def add_momentum_events(
    df: pd.DataFrame,
    consecutive_count: int = 3,
    price_col: str = "close",
) -> pd.DataFrame:
    """Add one-bar and consecutive close-to-close momentum events."""
    _validate_minimum_int(consecutive_count, "consecutive_count", minimum=2)
    _require_columns(df, [price_col])

    result = df.copy()
    higher_close = result[price_col] > result[price_col].shift(1)
    lower_close = result[price_col] < result[price_col].shift(1)
    result["higher_close"] = _safe_bool_series(higher_close, result.index)
    result["lower_close"] = _safe_bool_series(lower_close, result.index)

    required_moves = consecutive_count - 1
    higher_col = f"consecutive_higher_closes_{consecutive_count}"
    lower_col = f"consecutive_lower_closes_{consecutive_count}"
    result[higher_col] = _safe_bool_series(
        result["higher_close"].rolling(required_moves).sum() == required_moves,
        result.index,
    )
    result[lower_col] = _safe_bool_series(
        result["lower_close"].rolling(required_moves).sum() == required_moves,
        result.index,
    )
    return result


def add_range_expansion_events(
    df: pd.DataFrame,
    window: int = 20,
    multiplier: float = 1.5,
) -> pd.DataFrame:
    """Add range expansion events against a prior-bar range average."""
    _validate_positive_int(window, "window")
    _validate_positive_number(multiplier, "multiplier")
    _require_columns(df, ["high", "low"])

    result = df.copy()
    prior_sma_col = f"prior_range_sma_{window}"
    expansion_col = f"range_expansion_{window}"

    result["candle_range"] = result["high"] - result["low"]
    result[prior_sma_col] = result["candle_range"].shift(1).rolling(window).mean()
    result[expansion_col] = _safe_bool_series(
        result["candle_range"] > result[prior_sma_col] * multiplier,
        result.index,
    )
    return result


def add_volume_expansion_events(
    df: pd.DataFrame,
    window: int = 20,
    multiplier: float = 1.5,
    volume_col: str = "volume",
) -> pd.DataFrame:
    """Add volume expansion events against a prior-bar volume average."""
    _validate_positive_int(window, "window")
    _validate_positive_number(multiplier, "multiplier")
    _require_columns(df, [volume_col])

    result = df.copy()
    prior_sma_col = f"prior_volume_sma_{window}"
    expansion_col = f"volume_expansion_{window}"

    result[prior_sma_col] = result[volume_col].shift(1).rolling(window).mean()
    result[expansion_col] = _safe_bool_series(
        result[volume_col] > result[prior_sma_col] * multiplier,
        result.index,
    )
    return result


def add_basic_event_primitives(
    df: pd.DataFrame,
    trailing_lookback: int = 20,
    consecutive_count: int = 3,
    expansion_window: int = 20,
    expansion_multiplier: float = 1.5,
) -> pd.DataFrame:
    """Compose the basic causal event primitive feature set."""
    result = df.copy()
    result = add_trailing_break_events(result, lookback=trailing_lookback)
    result = add_candle_body_features(result)
    result = add_single_bar_pattern_events(result)
    result = add_momentum_events(result, consecutive_count=consecutive_count)
    result = add_range_expansion_events(
        result, window=expansion_window, multiplier=expansion_multiplier
    )
    result = add_volume_expansion_events(
        result, window=expansion_window, multiplier=expansion_multiplier
    )
    return result


def _require_columns(df: pd.DataFrame, columns: list[str]) -> None:
    missing = [column for column in columns if column not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")


def _validate_positive_int(value: int, name: str) -> None:
    _validate_minimum_int(value, name, minimum=1)


def _validate_minimum_int(value: int, name: str, minimum: int) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value < minimum:
        raise ValueError(f"{name} must be an integer greater than or equal to {minimum}")


def _validate_positive_number(value: float, name: str) -> None:
    if not isinstance(value, Real) or isinstance(value, bool) or value <= 0:
        raise ValueError(f"{name} must be greater than 0")


def _safe_bool_series(values: pd.Series, index: pd.Index) -> pd.Series:
    return pd.Series(values, index=index).fillna(False).astype(bool)


def _safe_name(name: str) -> str:
    normalized = re.sub(r"[^0-9a-zA-Z]+", "_", name.strip().lower()).strip("_")
    return normalized or "series"
