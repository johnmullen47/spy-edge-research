"""Causal cross-instrument context feature helpers."""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import pandas as pd


def add_relative_return_features(
    df: pd.DataFrame,
    *,
    symbols: Sequence[str],
    price_suffix: str = "close",
    periods: int = 1,
) -> pd.DataFrame:
    """Add current-row returns and relative returns for prefixed symbol columns."""
    _validate_periods(periods)
    normalized = _normalize_symbols(symbols)
    result = df.copy()
    for symbol in normalized:
        price_column = _symbol_column(symbol, price_suffix)
        _require_columns(result, [price_column])
        result[f"{symbol}_return_{periods}"] = pd.to_numeric(
            result[price_column],
            errors="coerce",
        ).pct_change(periods=periods)
    primary = normalized[0]
    primary_return = f"{primary}_return_{periods}"
    for symbol in normalized[1:]:
        result[f"{symbol}_relative_return_vs_{primary}_{periods}"] = (
            result[f"{symbol}_return_{periods}"] - result[primary_return]
        )
    return result


def add_cross_symbol_trend_confirmation(
    df: pd.DataFrame,
    *,
    primary_symbol: str,
    confirmation_symbols: Sequence[str],
    return_suffix: str = "return_1",
) -> pd.DataFrame:
    """Add same-direction and divergent return context flags."""
    primary = _normalize_symbol(primary_symbol)
    confirmations = _normalize_symbols(confirmation_symbols)
    result = df.copy()
    columns = [_symbol_column(primary, return_suffix), *[_symbol_column(symbol, return_suffix) for symbol in confirmations]]
    _require_columns(result, columns)
    primary_direction = _direction(result[_symbol_column(primary, return_suffix)])
    result[f"{primary}_trend_direction"] = primary_direction
    confirming_flags = []
    divergent_flags = []
    for symbol in confirmations:
        symbol_direction = _direction(result[_symbol_column(symbol, return_suffix)])
        confirm_column = f"{symbol}_trend_confirms_{primary}"
        divergent_column = f"{symbol}_trend_diverges_from_{primary}"
        result[confirm_column] = (primary_direction.ne(0) & symbol_direction.eq(primary_direction)).astype(int)
        result[divergent_column] = (primary_direction.ne(0) & symbol_direction.eq(-primary_direction)).astype(int)
        confirming_flags.append(confirm_column)
        divergent_flags.append(divergent_column)
    result["cross_trend_confirming_count"] = result[confirming_flags].sum(axis=1) if confirming_flags else 0
    result["cross_trend_divergent_count"] = result[divergent_flags].sum(axis=1) if divergent_flags else 0
    result["cross_trend_context"] = np.select(
        [
            result["cross_trend_confirming_count"].gt(0),
            result["cross_trend_divergent_count"].gt(0),
        ],
        ["confirmed", "divergent"],
        default="neutral",
    )
    return result


def add_cross_symbol_vwap_confirmation(
    df: pd.DataFrame,
    *,
    primary_symbol: str,
    confirmation_symbols: Sequence[str],
    price_suffix: str = "close",
    vwap_suffix: str = "vwap",
) -> pd.DataFrame:
    """Add VWAP-side confirmation and divergence context flags."""
    primary = _normalize_symbol(primary_symbol)
    confirmations = _normalize_symbols(confirmation_symbols)
    result = df.copy()
    required = [
        _symbol_column(symbol, suffix)
        for symbol in [primary, *confirmations]
        for suffix in [price_suffix, vwap_suffix]
    ]
    _require_columns(result, required)
    primary_relation = _direction(result[_symbol_column(primary, price_suffix)] - result[_symbol_column(primary, vwap_suffix)])
    confirm_columns = []
    diverge_columns = []
    for symbol in confirmations:
        relation = _direction(result[_symbol_column(symbol, price_suffix)] - result[_symbol_column(symbol, vwap_suffix)])
        confirm_column = f"{symbol}_vwap_side_confirms_{primary}"
        diverge_column = f"{symbol}_vwap_side_diverges_from_{primary}"
        result[confirm_column] = (primary_relation.ne(0) & relation.eq(primary_relation)).astype(int)
        result[diverge_column] = (primary_relation.ne(0) & relation.eq(-primary_relation)).astype(int)
        confirm_columns.append(confirm_column)
        diverge_columns.append(diverge_column)
    result["cross_vwap_confirming_count"] = result[confirm_columns].sum(axis=1) if confirm_columns else 0
    result["cross_vwap_divergent_count"] = result[diverge_columns].sum(axis=1) if diverge_columns else 0
    return result


def add_cross_symbol_volume_confirmation(
    df: pd.DataFrame,
    *,
    primary_symbol: str,
    confirmation_symbols: Sequence[str],
    volume_suffix: str = "volume",
    baseline_window: int = 3,
) -> pd.DataFrame:
    """Add trailing-volume expansion confirmation features."""
    _validate_periods(baseline_window, name="baseline_window")
    primary = _normalize_symbol(primary_symbol)
    confirmations = _normalize_symbols(confirmation_symbols)
    result = df.copy()
    required = [_symbol_column(symbol, volume_suffix) for symbol in [primary, *confirmations]]
    _require_columns(result, required)
    expansion_columns = []
    for symbol in [primary, *confirmations]:
        volume = pd.to_numeric(result[_symbol_column(symbol, volume_suffix)], errors="coerce")
        baseline = volume.rolling(baseline_window, min_periods=1).mean().shift(1)
        expansion_column = f"{symbol}_volume_expands_vs_trailing"
        result[expansion_column] = volume.gt(baseline).fillna(False).astype(int)
        expansion_columns.append(expansion_column)
    primary_expansion = result[f"{primary}_volume_expands_vs_trailing"].astype(bool)
    confirm_columns = []
    for symbol in confirmations:
        confirm_column = f"{symbol}_volume_expansion_matches_{primary}"
        result[confirm_column] = (
            primary_expansion & result[f"{symbol}_volume_expands_vs_trailing"].astype(bool)
        ).astype(int)
        confirm_columns.append(confirm_column)
    result["cross_volume_confirming_count"] = result[confirm_columns].sum(axis=1) if confirm_columns else 0
    return result


def add_cross_symbol_divergence_flags(
    df: pd.DataFrame,
    *,
    primary_symbol: str,
    confirmation_symbols: Sequence[str],
    return_suffix: str = "return_1",
) -> pd.DataFrame:
    """Add compact cross-symbol divergence flags from current return direction."""
    return add_cross_symbol_trend_confirmation(
        df,
        primary_symbol=primary_symbol,
        confirmation_symbols=confirmation_symbols,
        return_suffix=return_suffix,
    )


def add_cross_instrument_confirmation_features(
    df: pd.DataFrame,
    *,
    primary_symbol: str,
    confirmation_symbols: Sequence[str],
    price_suffix: str = "close",
    vwap_suffix: str = "vwap",
    volume_suffix: str = "volume",
    return_periods: int = 1,
    volume_baseline_window: int = 3,
) -> pd.DataFrame:
    """Compose causal cross-instrument context features."""
    symbols = [_normalize_symbol(primary_symbol), *_normalize_symbols(confirmation_symbols)]
    result = add_relative_return_features(
        df,
        symbols=symbols,
        price_suffix=price_suffix,
        periods=return_periods,
    )
    result = add_cross_symbol_trend_confirmation(
        result,
        primary_symbol=primary_symbol,
        confirmation_symbols=confirmation_symbols,
        return_suffix=f"return_{return_periods}",
    )
    result = add_cross_symbol_vwap_confirmation(
        result,
        primary_symbol=primary_symbol,
        confirmation_symbols=confirmation_symbols,
        price_suffix=price_suffix,
        vwap_suffix=vwap_suffix,
    )
    result = add_cross_symbol_volume_confirmation(
        result,
        primary_symbol=primary_symbol,
        confirmation_symbols=confirmation_symbols,
        volume_suffix=volume_suffix,
        baseline_window=volume_baseline_window,
    )
    result["cross_instrument_context_caveat"] = "causal_current_and_prior_rows_only_research_context"
    return result


def _direction(values: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(values, errors="coerce")
    return pd.Series(np.sign(numeric).fillna(0).astype(int), index=values.index)


def _normalize_symbol(symbol: str) -> str:
    if not isinstance(symbol, str) or not symbol.strip():
        raise ValueError("symbols must be non-empty strings")
    return symbol.strip().upper()


def _normalize_symbols(symbols: Sequence[str]) -> list[str]:
    if isinstance(symbols, str):
        symbols = [symbols]
    normalized = [_normalize_symbol(symbol) for symbol in symbols]
    if not normalized:
        raise ValueError("symbols must contain at least one symbol")
    return normalized


def _symbol_column(symbol: str, suffix: str) -> str:
    suffix = suffix.strip("_")
    return f"{_normalize_symbol(symbol)}_{suffix}"


def _require_columns(df: pd.DataFrame, columns: list[str]) -> None:
    missing = [column for column in columns if column not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")


def _validate_periods(value: int, name: str = "periods") -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise ValueError(f"{name} must be an integer greater than or equal to 1")
