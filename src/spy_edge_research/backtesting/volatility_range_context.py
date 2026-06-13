"""Research-only volatility and range context study helpers."""

from __future__ import annotations

from collections.abc import Iterable

import numpy as np
import pandas as pd

from spy_edge_research.backtesting.conditional_event_study import (
    summarize_conditional_event_edge,
)


def calculate_intraday_realized_volatility(
    df: pd.DataFrame,
    *,
    window: int = 20,
    price_col: str = "close",
    high_ratio_threshold: float = 1.25,
    low_ratio_threshold: float = 0.75,
) -> pd.DataFrame:
    """Add causal rolling realized-volatility context features."""
    _validate_positive_int(window, "window")
    _validate_positive_number(high_ratio_threshold, "high_ratio_threshold")
    _validate_positive_number(low_ratio_threshold, "low_ratio_threshold")
    _require_columns(df, [price_col])

    result = df.copy()
    return_col = "return_1b"
    vol_col = f"realized_volatility_{window}"
    baseline_col = f"realized_volatility_baseline_{window}"
    ratio_col = f"realized_volatility_ratio_{window}"
    context_col = f"volatility_context_{window}"

    result[return_col] = result[price_col].pct_change()
    result[vol_col] = result[return_col].rolling(window, min_periods=window).std()
    result[baseline_col] = result[vol_col].shift(1).rolling(window, min_periods=1).median()
    result[ratio_col] = result[vol_col].div(result[baseline_col].replace(0, np.nan))
    result[context_col] = _classify_ratio_context(
        result[ratio_col],
        high_threshold=high_ratio_threshold,
        low_threshold=low_ratio_threshold,
        high_label="high_volatility",
        low_label="low_volatility",
    )
    return result


def calculate_range_expansion_features(
    df: pd.DataFrame,
    *,
    window: int = 20,
    high_col: str = "high",
    low_col: str = "low",
    expansion_threshold: float = 1.25,
    contraction_threshold: float = 0.75,
) -> pd.DataFrame:
    """Add causal range expansion/contraction context features."""
    _validate_positive_int(window, "window")
    _validate_positive_number(expansion_threshold, "expansion_threshold")
    _validate_positive_number(contraction_threshold, "contraction_threshold")
    _require_columns(df, [high_col, low_col])

    result = df.copy()
    range_col = "bar_range"
    baseline_col = f"prior_range_mean_{window}"
    ratio_col = f"range_expansion_ratio_{window}"
    context_col = f"range_context_{window}"

    result[range_col] = result[high_col] - result[low_col]
    result[baseline_col] = result[range_col].shift(1).rolling(window, min_periods=1).mean()
    result[ratio_col] = result[range_col].div(result[baseline_col].replace(0, np.nan))
    result[context_col] = _classify_ratio_context(
        result[ratio_col],
        high_threshold=expansion_threshold,
        low_threshold=contraction_threshold,
        high_label="range_expansion",
        low_label="range_contraction",
    )
    return result


def summarize_event_by_volatility_context(
    df: pd.DataFrame,
    catalog: pd.DataFrame,
    outcome_columns: Iterable[str],
    *,
    window: int = 20,
    context_col: str | None = None,
    hit_rate_threshold: float = 0.0,
    min_events: int = 1,
) -> pd.DataFrame:
    """Summarize event outcomes by realized-volatility context."""
    resolved_context_col = context_col or f"volatility_context_{window}"
    working = (
        df.copy()
        if resolved_context_col in df.columns
        else calculate_intraday_realized_volatility(df, window=window)
    )
    return summarize_conditional_event_edge(
        working,
        catalog,
        outcome_columns,
        [resolved_context_col],
        hit_rate_threshold=hit_rate_threshold,
        min_events=min_events,
    )


def summarize_event_by_range_context(
    df: pd.DataFrame,
    catalog: pd.DataFrame,
    outcome_columns: Iterable[str],
    *,
    window: int = 20,
    context_col: str | None = None,
    hit_rate_threshold: float = 0.0,
    min_events: int = 1,
) -> pd.DataFrame:
    """Summarize event outcomes by range expansion/contraction context."""
    resolved_context_col = context_col or f"range_context_{window}"
    working = (
        df.copy()
        if resolved_context_col in df.columns
        else calculate_range_expansion_features(df, window=window)
    )
    return summarize_conditional_event_edge(
        working,
        catalog,
        outcome_columns,
        [resolved_context_col],
        hit_rate_threshold=hit_rate_threshold,
        min_events=min_events,
    )


def _classify_ratio_context(
    ratio: pd.Series,
    *,
    high_threshold: float,
    low_threshold: float,
    high_label: str,
    low_label: str,
) -> pd.Series:
    context = pd.Series("normal", index=ratio.index, dtype="object")
    context.loc[ratio >= high_threshold] = high_label
    context.loc[ratio <= low_threshold] = low_label
    context.loc[ratio.isna()] = "unknown"
    return context


def _require_columns(df: pd.DataFrame, columns: list[str]) -> None:
    missing = [column for column in columns if column not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")


def _validate_positive_int(value: int, name: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise ValueError(f"{name} must be an integer greater than or equal to 1")


def _validate_positive_number(value: float, name: str) -> None:
    if not isinstance(value, (int, float)) or isinstance(value, bool) or value <= 0:
        raise ValueError(f"{name} must be greater than 0")
