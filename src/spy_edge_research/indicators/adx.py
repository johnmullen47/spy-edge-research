"""Average Directional Index calculations."""

from __future__ import annotations

import numpy as np
import pandas as pd


def calculate_adx(
    df: pd.DataFrame,
    window: int = 14,
) -> pd.DataFrame:
    """Add causal ADX fields using simple rolling sums/means, not Wilder smoothing."""
    _validate_positive_int(window, "window")
    _require_columns(df, ["high", "low", "close"])

    result = df.copy()
    up_move = result["high"].diff()
    down_move = -result["low"].diff()
    result["plus_dm"] = pd.Series(
        np.where((up_move > down_move) & (up_move > 0), up_move, 0.0),
        index=result.index,
    )
    result["minus_dm"] = pd.Series(
        np.where((down_move > up_move) & (down_move > 0), down_move, 0.0),
        index=result.index,
    )

    true_range = _true_range(result)
    rolling_tr = true_range.rolling(window).sum()
    plus_di_col = f"plus_di_{window}"
    minus_di_col = f"minus_di_{window}"
    dx_col = f"dx_{window}"
    adx_col = f"adx_{window}"

    result[plus_di_col] = 100 * result["plus_dm"].rolling(window).sum().div(
        rolling_tr.replace(0, np.nan)
    )
    result[minus_di_col] = 100 * result["minus_dm"].rolling(window).sum().div(
        rolling_tr.replace(0, np.nan)
    )
    di_sum = result[plus_di_col] + result[minus_di_col]
    result[dx_col] = 100 * (result[plus_di_col] - result[minus_di_col]).abs().div(
        di_sum.replace(0, np.nan)
    )
    result[adx_col] = result[dx_col].rolling(window).mean()
    return result


def _true_range(df: pd.DataFrame) -> pd.Series:
    previous_close = df["close"].shift(1)
    ranges = pd.concat(
        [
            df["high"] - df["low"],
            (df["high"] - previous_close).abs(),
            (df["low"] - previous_close).abs(),
        ],
        axis=1,
    )
    return ranges.max(axis=1)


def _require_columns(df: pd.DataFrame, columns: list[str]) -> None:
    missing = [column for column in columns if column not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")


def _validate_positive_int(value: int, name: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise ValueError(f"{name} must be an integer greater than or equal to 1")
