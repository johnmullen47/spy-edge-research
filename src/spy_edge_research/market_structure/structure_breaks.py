"""Causal market-structure break primitives.

These helpers compare current prices with already-confirmed pivot levels. They
are primitive market-structure features, not strategy signals or edge claims.
"""

from __future__ import annotations

import pandas as pd

from spy_edge_research.market_structure.pivots import (
    add_last_confirmed_pivot_levels,
    add_market_structure_pivots,
)


def add_structure_breaks(
    df: pd.DataFrame,
    price_col: str = "close",
    left_bars: int = 2,
    right_bars: int = 2,
) -> pd.DataFrame:
    """Add bullish and bearish structure breaks against confirmed pivots."""
    _require_columns(df, [price_col])

    result = df.copy()
    if not _has_columns(
        result,
        ["last_confirmed_pivot_high", "last_confirmed_pivot_low"],
    ):
        result = add_last_confirmed_pivot_levels(
            result,
            left_bars=left_bars,
            right_bars=right_bars,
        )

    price = result[price_col]
    last_high = result["last_confirmed_pivot_high"]
    last_low = result["last_confirmed_pivot_low"]

    result["bullish_structure_break"] = _safe_bool_series(
        (price > last_high) & (price.shift(1) <= last_high.shift(1)),
        result.index,
    )
    result["bearish_structure_break"] = _safe_bool_series(
        (price < last_low) & (price.shift(1) >= last_low.shift(1)),
        result.index,
    )
    return result


def add_structure_state(
    df: pd.DataFrame,
    price_col: str = "close",
    left_bars: int = 2,
    right_bars: int = 2,
) -> pd.DataFrame:
    """Add a primitive structure state from the most recent one-sided break."""
    result = df.copy()
    if not _has_columns(
        result,
        ["bullish_structure_break", "bearish_structure_break"],
    ):
        result = add_structure_breaks(
            result,
            price_col=price_col,
            left_bars=left_bars,
            right_bars=right_bars,
        )

    state = "neutral"
    states: list[str] = []
    bullish_breaks = result["bullish_structure_break"].fillna(False).astype(bool)
    bearish_breaks = result["bearish_structure_break"].fillna(False).astype(bool)

    for bullish_break, bearish_break in zip(bullish_breaks, bearish_breaks):
        if bullish_break and bearish_break:
            states.append("neutral")
            continue
        if bullish_break:
            state = "bullish"
        elif bearish_break:
            state = "bearish"
        states.append(state)

    result["structure_state"] = pd.Series(states, index=result.index, dtype="object")
    return result


def add_market_structure_features(
    df: pd.DataFrame,
    left_bars: int = 2,
    right_bars: int = 2,
    high_col: str = "high",
    low_col: str = "low",
    price_col: str = "close",
) -> pd.DataFrame:
    """Compose pivot, structure-break, and primitive state features."""
    result = add_market_structure_pivots(
        df,
        left_bars=left_bars,
        right_bars=right_bars,
        high_col=high_col,
        low_col=low_col,
    )
    result = add_structure_breaks(
        result,
        price_col=price_col,
        left_bars=left_bars,
        right_bars=right_bars,
    )
    return add_structure_state(
        result,
        price_col=price_col,
        left_bars=left_bars,
        right_bars=right_bars,
    )


def _require_columns(df: pd.DataFrame, columns: list[str]) -> None:
    missing = [column for column in columns if column not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")


def _has_columns(df: pd.DataFrame, columns: list[str]) -> bool:
    return all(column in df.columns for column in columns)


def _safe_bool_series(values: pd.Series, index: pd.Index) -> pd.Series:
    return pd.Series(values, index=index).fillna(False).astype(bool)
