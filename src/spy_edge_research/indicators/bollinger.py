"""Bollinger Band calculations."""

from __future__ import annotations

from numbers import Real

import numpy as np
import pandas as pd


def calculate_bollinger_bands(
    df: pd.DataFrame,
    window: int = 20,
    num_std: float = 2.0,
    price_col: str = "close",
) -> pd.DataFrame:
    """Add trailing Bollinger Bands using pandas' default sample std ``ddof=1``."""
    _validate_positive_int(window, "window")
    _validate_positive_number(num_std, "num_std")
    _require_columns(df, [price_col])

    result = df.copy()
    mid_col = f"bb_mid_{window}"
    upper_col = f"bb_upper_{window}"
    lower_col = f"bb_lower_{window}"
    width_col = f"bb_width_{window}"
    percent_b_col = f"bb_percent_b_{window}"

    rolling = result[price_col].rolling(window)
    result[mid_col] = rolling.mean()
    rolling_std = rolling.std()
    result[upper_col] = result[mid_col] + num_std * rolling_std
    result[lower_col] = result[mid_col] - num_std * rolling_std
    result[width_col] = result[upper_col] - result[lower_col]
    result[percent_b_col] = (result[price_col] - result[lower_col]).div(
        result[width_col].replace(0, np.nan)
    )
    return result


def _require_columns(df: pd.DataFrame, columns: list[str]) -> None:
    missing = [column for column in columns if column not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")


def _validate_positive_int(value: int, name: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise ValueError(f"{name} must be an integer greater than or equal to 1")


def _validate_positive_number(value: float, name: str) -> None:
    if not isinstance(value, Real) or isinstance(value, bool) or value <= 0:
        raise ValueError(f"{name} must be greater than 0")
