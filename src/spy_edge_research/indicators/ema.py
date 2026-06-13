"""Exponential moving average calculations."""

from __future__ import annotations

import pandas as pd


def calculate_ema(
    df: pd.DataFrame,
    span: int = 9,
    price_col: str = "close",
) -> pd.DataFrame:
    """Add a causal EMA and derived distance fields."""
    _validate_positive_int(span, "span")
    _require_columns(df, [price_col])

    result = df.copy()
    ema_col = f"ema_{span}"
    result[ema_col] = result[price_col].ewm(span=span, adjust=False).mean()
    result[f"{ema_col}_slope"] = result[ema_col].diff()
    result[f"{ema_col}_distance"] = result[price_col] - result[ema_col]
    result[f"{ema_col}_distance_pct"] = result[f"{ema_col}_distance"].div(result[ema_col])
    return result


def _require_columns(df: pd.DataFrame, columns: list[str]) -> None:
    missing = [column for column in columns if column not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")


def _validate_positive_int(value: int, name: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise ValueError(f"{name} must be an integer greater than or equal to 1")
