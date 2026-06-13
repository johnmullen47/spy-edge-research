"""Causal market-structure pivot primitives.

Pivot candidates require right-side bars to confirm, so candidate columns mark
the pivot candle for diagnostics while confirmed pivot feature columns are
emitted only on the later confirmation row.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def add_confirmed_pivots(
    df: pd.DataFrame,
    left_bars: int = 2,
    right_bars: int = 2,
    high_col: str = "high",
    low_col: str = "low",
) -> pd.DataFrame:
    """Add pivot candidates and delayed confirmed pivot events.

    A pivot at row ``i`` is visible as a confirmed feature only at row
    ``i + right_bars``. The candidate columns are diagnostics and are not
    causal features at the candidate timestamp.
    """
    _validate_positive_int(left_bars, "left_bars")
    _validate_positive_int(right_bars, "right_bars")
    _require_columns(df, [high_col, low_col])

    result = df.copy()
    n_rows = len(result)
    highs = result[high_col].to_numpy(dtype="float64")
    lows = result[low_col].to_numpy(dtype="float64")

    pivot_high_candidate = np.zeros(n_rows, dtype=bool)
    pivot_low_candidate = np.zeros(n_rows, dtype=bool)
    confirmed_pivot_high = np.zeros(n_rows, dtype=bool)
    confirmed_pivot_low = np.zeros(n_rows, dtype=bool)
    pivot_high_price = np.full(n_rows, np.nan, dtype="float64")
    pivot_low_price = np.full(n_rows, np.nan, dtype="float64")

    for pivot_idx in range(left_bars, n_rows - right_bars):
        high = highs[pivot_idx]
        low = lows[pivot_idx]
        previous_highs = highs[pivot_idx - left_bars : pivot_idx]
        next_highs = highs[pivot_idx + 1 : pivot_idx + right_bars + 1]
        previous_lows = lows[pivot_idx - left_bars : pivot_idx]
        next_lows = lows[pivot_idx + 1 : pivot_idx + right_bars + 1]
        confirmation_idx = pivot_idx + right_bars

        if high > np.max(previous_highs) and high >= np.max(next_highs):
            pivot_high_candidate[pivot_idx] = True
            confirmed_pivot_high[confirmation_idx] = True
            pivot_high_price[confirmation_idx] = high

        if low < np.min(previous_lows) and low <= np.min(next_lows):
            pivot_low_candidate[pivot_idx] = True
            confirmed_pivot_low[confirmation_idx] = True
            pivot_low_price[confirmation_idx] = low

    result["pivot_high_candidate"] = pivot_high_candidate
    result["pivot_low_candidate"] = pivot_low_candidate
    result["confirmed_pivot_high"] = confirmed_pivot_high
    result["confirmed_pivot_low"] = confirmed_pivot_low
    result["pivot_high_price"] = pivot_high_price
    result["pivot_low_price"] = pivot_low_price
    return result


def add_last_confirmed_pivot_levels(
    df: pd.DataFrame,
    left_bars: int = 2,
    right_bars: int = 2,
    high_col: str = "high",
    low_col: str = "low",
) -> pd.DataFrame:
    """Add forward-filled last confirmed pivot high and low levels."""
    result = df.copy()
    if not _has_columns(
        result,
        [
            "confirmed_pivot_high",
            "confirmed_pivot_low",
            "pivot_high_price",
            "pivot_low_price",
        ],
    ):
        result = add_confirmed_pivots(
            result,
            left_bars=left_bars,
            right_bars=right_bars,
            high_col=high_col,
            low_col=low_col,
        )

    result["last_confirmed_pivot_high"] = result["pivot_high_price"].ffill()
    result["last_confirmed_pivot_low"] = result["pivot_low_price"].ffill()
    return result


def add_pivot_classification(
    df: pd.DataFrame,
    left_bars: int = 2,
    right_bars: int = 2,
    high_col: str = "high",
    low_col: str = "low",
) -> pd.DataFrame:
    """Classify newly confirmed pivots against prior confirmed pivots."""
    result = df.copy()
    if not _has_columns(
        result,
        [
            "confirmed_pivot_high",
            "confirmed_pivot_low",
            "pivot_high_price",
            "pivot_low_price",
        ],
    ):
        result = add_confirmed_pivots(
            result,
            left_bars=left_bars,
            right_bars=right_bars,
            high_col=high_col,
            low_col=low_col,
        )

    previous_pivot_high = result["pivot_high_price"].ffill().shift(1)
    previous_pivot_low = result["pivot_low_price"].ffill().shift(1)
    confirmed_high = result["confirmed_pivot_high"].fillna(False).astype(bool)
    confirmed_low = result["confirmed_pivot_low"].fillna(False).astype(bool)

    result["higher_high"] = _safe_bool_series(
        confirmed_high & (result["pivot_high_price"] > previous_pivot_high),
        result.index,
    )
    result["lower_high"] = _safe_bool_series(
        confirmed_high & (result["pivot_high_price"] < previous_pivot_high),
        result.index,
    )
    result["higher_low"] = _safe_bool_series(
        confirmed_low & (result["pivot_low_price"] > previous_pivot_low),
        result.index,
    )
    result["lower_low"] = _safe_bool_series(
        confirmed_low & (result["pivot_low_price"] < previous_pivot_low),
        result.index,
    )
    return result


def add_market_structure_pivots(
    df: pd.DataFrame,
    left_bars: int = 2,
    right_bars: int = 2,
    high_col: str = "high",
    low_col: str = "low",
) -> pd.DataFrame:
    """Compose confirmed pivots, last pivot levels, and pivot classifications."""
    result = add_confirmed_pivots(
        df,
        left_bars=left_bars,
        right_bars=right_bars,
        high_col=high_col,
        low_col=low_col,
    )
    result = add_last_confirmed_pivot_levels(
        result,
        left_bars=left_bars,
        right_bars=right_bars,
        high_col=high_col,
        low_col=low_col,
    )
    return add_pivot_classification(
        result,
        left_bars=left_bars,
        right_bars=right_bars,
        high_col=high_col,
        low_col=low_col,
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
