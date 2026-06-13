"""Causal factor-context feature helpers.

Inputs are expected to be already-loaded and timestamp-aligned dataframes.
Features use only current and prior rows and are descriptive research context,
not factor allocation, trade, or execution instructions.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

import numpy as np
import pandas as pd


FACTOR_CONTEXT_CAVEAT = "causal_factor_context_research_only_not_allocation_or_execution"


def add_factor_relative_return_features(
    df: pd.DataFrame,
    *,
    primary_symbol: str = "SPY",
    factor_symbols: Sequence[str],
    price_suffix: str = "close",
    periods: int = 1,
) -> pd.DataFrame:
    """Add current-row factor returns and returns relative to the primary symbol."""
    _validate_positive_int(periods, "periods")
    primary = _normalize_symbol(primary_symbol)
    factors = _normalize_symbols(factor_symbols, "factor_symbols")
    result = df.copy()
    symbols = [primary, *factors]
    _require_columns(result, [_symbol_column(symbol, price_suffix) for symbol in symbols])
    for symbol in symbols:
        result[f"{symbol}_return_{periods}"] = pd.to_numeric(
            result[_symbol_column(symbol, price_suffix)],
            errors="coerce",
        ).pct_change(periods=periods)
    primary_return = result[f"{primary}_return_{periods}"]
    for factor in factors:
        result[f"{factor}_relative_return_vs_{primary}_{periods}"] = (
            result[f"{factor}_return_{periods}"] - primary_return
        )
    return result


def add_factor_leadership_flags(
    df: pd.DataFrame,
    *,
    factor_symbols: Sequence[str],
    return_suffix: str = "return_1",
    factor_styles: Mapping[str, str] | None = None,
) -> pd.DataFrame:
    """Add descriptive top/bottom factor and factor-style leadership context."""
    factors = _normalize_symbols(factor_symbols, "factor_symbols")
    styles = {_normalize_symbol(symbol): style for symbol, style in dict(factor_styles or {}).items()}
    result = df.copy()
    return_columns = [_symbol_column(symbol, return_suffix) for symbol in factors]
    _require_columns(result, return_columns)
    factor_returns = result[return_columns].apply(pd.to_numeric, errors="coerce")
    top_labels: list[str | None] = []
    bottom_labels: list[str | None] = []
    for _, row in factor_returns.iterrows():
        if row.notna().sum() == 0:
            top_labels.append(None)
            bottom_labels.append(None)
        else:
            top_labels.append(_symbol_from_return_column(row.idxmax(), return_suffix))
            bottom_labels.append(_symbol_from_return_column(row.idxmin(), return_suffix))
    result["factor_leadership_symbol"] = top_labels
    result["factor_laggard_symbol"] = bottom_labels
    result["factor_leadership_style"] = [styles.get(symbol, "unknown") if symbol else None for symbol in top_labels]
    result["factor_laggard_style"] = [styles.get(symbol, "unknown") if symbol else None for symbol in bottom_labels]
    for style in sorted(set(styles.values())):
        style_symbols = [symbol for symbol in factors if styles.get(symbol) == style]
        if not style_symbols:
            continue
        style_columns = [_symbol_column(symbol, return_suffix) for symbol in style_symbols]
        result[f"factor_style_{style}_mean_return"] = factor_returns[style_columns].mean(axis=1)
        result[f"factor_style_{style}_positive_count"] = factor_returns[style_columns].gt(0).sum(axis=1).astype(int)
    return result


def add_factor_dispersion_features(
    df: pd.DataFrame,
    *,
    factor_symbols: Sequence[str],
    return_suffix: str = "return_1",
    high_dispersion_quantile_window: int = 20,
    high_dispersion_min_periods: int = 3,
) -> pd.DataFrame:
    """Add current-row factor return dispersion features."""
    _validate_positive_int(high_dispersion_quantile_window, "high_dispersion_quantile_window")
    _validate_positive_int(high_dispersion_min_periods, "high_dispersion_min_periods")
    factors = _normalize_symbols(factor_symbols, "factor_symbols")
    result = df.copy()
    return_columns = [_symbol_column(symbol, return_suffix) for symbol in factors]
    _require_columns(result, return_columns)
    factor_returns = result[return_columns].apply(pd.to_numeric, errors="coerce")
    result["factor_dispersion_return_std"] = factor_returns.std(axis=1, ddof=0)
    result["factor_dispersion_return_range"] = factor_returns.max(axis=1) - factor_returns.min(axis=1)
    trailing_threshold = result["factor_dispersion_return_std"].rolling(
        high_dispersion_quantile_window,
        min_periods=high_dispersion_min_periods,
    ).quantile(0.75)
    result["factor_high_dispersion_context"] = (
        result["factor_dispersion_return_std"].ge(trailing_threshold).fillna(False).astype(int)
    )
    return result


def add_factor_context_features(
    df: pd.DataFrame,
    *,
    primary_symbol: str = "SPY",
    factor_symbols: Sequence[str],
    factor_styles: Mapping[str, str] | None = None,
    price_suffix: str = "close",
    return_periods: int = 1,
    dispersion_window: int = 20,
    dispersion_min_periods: int = 3,
) -> pd.DataFrame:
    """Compose causal factor context features for descriptive research."""
    result = add_factor_relative_return_features(
        df,
        primary_symbol=primary_symbol,
        factor_symbols=factor_symbols,
        price_suffix=price_suffix,
        periods=return_periods,
    )
    return_suffix = f"return_{return_periods}"
    result = add_factor_leadership_flags(
        result,
        factor_symbols=factor_symbols,
        return_suffix=return_suffix,
        factor_styles=factor_styles,
    )
    result = add_factor_dispersion_features(
        result,
        factor_symbols=factor_symbols,
        return_suffix=return_suffix,
        high_dispersion_quantile_window=dispersion_window,
        high_dispersion_min_periods=dispersion_min_periods,
    )
    result["factor_context_caveat"] = FACTOR_CONTEXT_CAVEAT
    return result


def _symbol_from_return_column(column: str, return_suffix: str) -> str:
    suffix = f"_{return_suffix.strip('_')}"
    return column[: -len(suffix)] if column.endswith(suffix) else column


def _symbol_column(symbol: str, suffix: str) -> str:
    return f"{_normalize_symbol(symbol)}_{suffix.strip('_')}"


def _normalize_symbol(symbol: str | None) -> str:
    if not isinstance(symbol, str) or not symbol.strip():
        raise ValueError("symbols must be non-empty strings")
    return symbol.strip().upper()


def _normalize_symbols(symbols: Sequence[str], name: str) -> list[str]:
    if isinstance(symbols, str):
        symbols = [symbols]
    normalized = [_normalize_symbol(symbol) for symbol in symbols]
    if not normalized:
        raise ValueError(f"{name} must contain at least one symbol")
    duplicates = sorted({symbol for symbol in normalized if normalized.count(symbol) > 1})
    if duplicates:
        raise ValueError(f"{name} contains duplicate symbols: {duplicates}")
    return normalized


def _require_columns(df: pd.DataFrame, columns: list[str]) -> None:
    missing = [column for column in columns if column not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")


def _validate_positive_int(value: int, name: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise ValueError(f"{name} must be an integer greater than or equal to 1")
