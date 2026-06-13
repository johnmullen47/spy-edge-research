"""Causal sector context feature helpers.

Inputs are expected to be already-loaded and timestamp-aligned dataframes.
Features use only current and prior rows and are descriptive research context,
not sector allocation, trade, or execution instructions.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

import numpy as np
import pandas as pd


SECTOR_CONTEXT_CAVEAT = "causal_sector_context_research_only_not_allocation_or_execution"


def add_sector_relative_return_features(
    df: pd.DataFrame,
    *,
    primary_symbol: str = "SPY",
    sector_symbols: Sequence[str],
    price_suffix: str = "close",
    periods: int = 1,
) -> pd.DataFrame:
    """Add current-row sector returns and returns relative to the primary symbol."""
    _validate_positive_int(periods, "periods")
    primary = _normalize_symbol(primary_symbol)
    sectors = _normalize_symbols(sector_symbols, "sector_symbols")
    result = df.copy()
    symbols = [primary, *sectors]
    _require_columns(result, [_symbol_column(symbol, price_suffix) for symbol in symbols])
    for symbol in symbols:
        result[f"{symbol}_return_{periods}"] = pd.to_numeric(
            result[_symbol_column(symbol, price_suffix)],
            errors="coerce",
        ).pct_change(periods=periods)
    primary_return = result[f"{primary}_return_{periods}"]
    for sector in sectors:
        result[f"{sector}_relative_return_vs_{primary}_{periods}"] = result[f"{sector}_return_{periods}"] - primary_return
    return result


def add_sector_breadth_features(
    df: pd.DataFrame,
    *,
    sector_symbols: Sequence[str],
    return_suffix: str = "return_1",
    benchmark_symbol: str | None = None,
) -> pd.DataFrame:
    """Add descriptive sector breadth counts and fractions."""
    sectors = _normalize_symbols(sector_symbols, "sector_symbols")
    benchmark = _normalize_symbol(benchmark_symbol) if benchmark_symbol is not None else None
    result = df.copy()
    sector_return_columns = [_symbol_column(symbol, return_suffix) for symbol in sectors]
    _require_columns(result, sector_return_columns)
    sector_returns = result[sector_return_columns].apply(pd.to_numeric, errors="coerce")
    valid_counts = sector_returns.notna().sum(axis=1)
    positive_counts = sector_returns.gt(0).sum(axis=1)
    result["sector_breadth_positive_count"] = positive_counts.astype(int)
    result["sector_breadth_valid_count"] = valid_counts.astype(int)
    result["sector_breadth_fraction_positive"] = _safe_fraction(positive_counts, valid_counts)
    if benchmark is not None:
        benchmark_column = _symbol_column(benchmark, return_suffix)
        _require_columns(result, [benchmark_column])
        benchmark_return = pd.to_numeric(result[benchmark_column], errors="coerce")
        above_benchmark = sector_returns.gt(benchmark_return, axis=0)
        result[f"sector_breadth_above_{benchmark}_count"] = above_benchmark.sum(axis=1).astype(int)
        result[f"sector_breadth_fraction_above_{benchmark}"] = _safe_fraction(
            above_benchmark.sum(axis=1),
            valid_counts,
        )
    return result


def add_sector_leadership_flags(
    df: pd.DataFrame,
    *,
    sector_symbols: Sequence[str],
    return_suffix: str = "return_1",
    sector_groups: Mapping[str, str] | None = None,
) -> pd.DataFrame:
    """Add descriptive top/bottom sector and sector-group leadership context."""
    sectors = _normalize_symbols(sector_symbols, "sector_symbols")
    groups = {_normalize_symbol(symbol): group for symbol, group in dict(sector_groups or {}).items()}
    result = df.copy()
    return_columns = [_symbol_column(symbol, return_suffix) for symbol in sectors]
    _require_columns(result, return_columns)
    sector_returns = result[return_columns].apply(pd.to_numeric, errors="coerce")
    top_labels: list[str | None] = []
    bottom_labels: list[str | None] = []
    for _, row in sector_returns.iterrows():
        if row.notna().sum() == 0:
            top_labels.append(None)
            bottom_labels.append(None)
        else:
            top_labels.append(_symbol_from_return_column(row.idxmax(), return_suffix))
            bottom_labels.append(_symbol_from_return_column(row.idxmin(), return_suffix))
    result["sector_leadership_symbol"] = top_labels
    result["sector_laggard_symbol"] = bottom_labels
    result["sector_leadership_group"] = [groups.get(symbol, "unknown") if symbol else None for symbol in top_labels]
    result["sector_laggard_group"] = [groups.get(symbol, "unknown") if symbol else None for symbol in bottom_labels]
    for group in sorted(set(groups.values())):
        group_symbols = [symbol for symbol in sectors if groups.get(symbol) == group]
        if not group_symbols:
            continue
        group_columns = [_symbol_column(symbol, return_suffix) for symbol in group_symbols]
        result[f"sector_group_{group}_mean_return"] = sector_returns[group_columns].mean(axis=1)
        result[f"sector_group_{group}_positive_count"] = sector_returns[group_columns].gt(0).sum(axis=1).astype(int)
    return result


def add_sector_dispersion_features(
    df: pd.DataFrame,
    *,
    sector_symbols: Sequence[str],
    return_suffix: str = "return_1",
    high_dispersion_quantile_window: int = 20,
    high_dispersion_min_periods: int = 3,
) -> pd.DataFrame:
    """Add current-row sector return dispersion features."""
    _validate_positive_int(high_dispersion_quantile_window, "high_dispersion_quantile_window")
    _validate_positive_int(high_dispersion_min_periods, "high_dispersion_min_periods")
    sectors = _normalize_symbols(sector_symbols, "sector_symbols")
    result = df.copy()
    return_columns = [_symbol_column(symbol, return_suffix) for symbol in sectors]
    _require_columns(result, return_columns)
    sector_returns = result[return_columns].apply(pd.to_numeric, errors="coerce")
    result["sector_dispersion_return_std"] = sector_returns.std(axis=1, ddof=0)
    result["sector_dispersion_return_range"] = sector_returns.max(axis=1) - sector_returns.min(axis=1)
    trailing_threshold = result["sector_dispersion_return_std"].rolling(
        high_dispersion_quantile_window,
        min_periods=high_dispersion_min_periods,
    ).quantile(0.75)
    result["sector_high_dispersion_context"] = (
        result["sector_dispersion_return_std"].ge(trailing_threshold).fillna(False).astype(int)
    )
    return result


def add_primary_sector_confirmation_features(
    df: pd.DataFrame,
    *,
    primary_symbol: str = "SPY",
    sector_symbols: Sequence[str],
    return_suffix: str = "return_1",
) -> pd.DataFrame:
    """Add descriptive primary direction confirmation/divergence context."""
    primary = _normalize_symbol(primary_symbol)
    sectors = _normalize_symbols(sector_symbols, "sector_symbols")
    result = df.copy()
    columns = [_symbol_column(primary, return_suffix), *[_symbol_column(symbol, return_suffix) for symbol in sectors]]
    _require_columns(result, columns)
    primary_direction = _direction(result[_symbol_column(primary, return_suffix)])
    result[f"{primary}_sector_context_direction"] = primary_direction
    confirm_columns = []
    divergent_columns = []
    for sector in sectors:
        sector_direction = _direction(result[_symbol_column(sector, return_suffix)])
        confirm_column = f"{sector}_sector_confirms_{primary}"
        divergent_column = f"{sector}_sector_diverges_from_{primary}"
        result[confirm_column] = (primary_direction.ne(0) & sector_direction.eq(primary_direction)).astype(int)
        result[divergent_column] = (primary_direction.ne(0) & sector_direction.eq(-primary_direction)).astype(int)
        confirm_columns.append(confirm_column)
        divergent_columns.append(divergent_column)
    result["sector_confirming_count"] = result[confirm_columns].sum(axis=1).astype(int)
    result["sector_divergent_count"] = result[divergent_columns].sum(axis=1).astype(int)
    result["sector_confirmation_fraction"] = _safe_fraction(result["sector_confirming_count"], len(sectors))
    result["sector_divergence_fraction"] = _safe_fraction(result["sector_divergent_count"], len(sectors))
    result["primary_sector_context"] = np.select(
        [
            result["sector_confirming_count"].gt(result["sector_divergent_count"]),
            result["sector_divergent_count"].gt(result["sector_confirming_count"]),
        ],
        ["sector_confirmed", "sector_divergent"],
        default="sector_neutral",
    )
    return result


def add_sector_context_features(
    df: pd.DataFrame,
    *,
    primary_symbol: str = "SPY",
    sector_symbols: Sequence[str],
    sector_groups: Mapping[str, str] | None = None,
    price_suffix: str = "close",
    return_periods: int = 1,
    dispersion_window: int = 20,
    dispersion_min_periods: int = 3,
) -> pd.DataFrame:
    """Compose causal sector context features for descriptive research."""
    result = add_sector_relative_return_features(
        df,
        primary_symbol=primary_symbol,
        sector_symbols=sector_symbols,
        price_suffix=price_suffix,
        periods=return_periods,
    )
    return_suffix = f"return_{return_periods}"
    result = add_sector_breadth_features(
        result,
        sector_symbols=sector_symbols,
        return_suffix=return_suffix,
        benchmark_symbol=primary_symbol,
    )
    result = add_sector_leadership_flags(
        result,
        sector_symbols=sector_symbols,
        return_suffix=return_suffix,
        sector_groups=sector_groups,
    )
    result = add_sector_dispersion_features(
        result,
        sector_symbols=sector_symbols,
        return_suffix=return_suffix,
        high_dispersion_quantile_window=dispersion_window,
        high_dispersion_min_periods=dispersion_min_periods,
    )
    result = add_primary_sector_confirmation_features(
        result,
        primary_symbol=primary_symbol,
        sector_symbols=sector_symbols,
        return_suffix=return_suffix,
    )
    result["sector_context_caveat"] = SECTOR_CONTEXT_CAVEAT
    return result


def _direction(values: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(values, errors="coerce")
    return pd.Series(np.sign(numeric).fillna(0).astype(int), index=values.index)


def _safe_fraction(numerator, denominator):
    if isinstance(denominator, int):
        if denominator == 0:
            return np.nan
        return numerator / denominator
    return numerator.divide(denominator.replace(0, np.nan))


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
