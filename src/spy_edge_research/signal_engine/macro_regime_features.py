"""Causal macro regime context feature helpers.

Inputs are expected to be already-loaded and timestamp-aligned dataframes.
Features use only current and prior rows and are descriptive research context,
not macro allocation, trade, or execution instructions.
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import pandas as pd


MACRO_REGIME_CONTEXT_CAVEAT = "causal_macro_regime_context_research_only_not_allocation_or_execution"


def add_macro_relative_return_features(
    df: pd.DataFrame,
    *,
    primary_symbol: str = "SPY",
    macro_symbols: Sequence[str],
    price_suffix: str = "close",
    periods: int = 1,
) -> pd.DataFrame:
    """Add current-row macro proxy returns and returns relative to primary."""
    _validate_positive_int(periods, "periods")
    primary = _normalize_symbol(primary_symbol)
    macros = _normalize_symbols(macro_symbols, "macro_symbols")
    result = df.copy()
    symbols = [primary, *macros]
    _require_columns(result, [_symbol_column(symbol, price_suffix) for symbol in symbols])
    for symbol in symbols:
        result[f"{symbol}_return_{periods}"] = pd.to_numeric(
            result[_symbol_column(symbol, price_suffix)],
            errors="coerce",
        ).pct_change(periods=periods)
    primary_return = result[f"{primary}_return_{periods}"]
    for symbol in macros:
        result[f"{symbol}_relative_return_vs_{primary}_{periods}"] = result[f"{symbol}_return_{periods}"] - primary_return
    return result


def add_rates_regime_features(
    df: pd.DataFrame,
    *,
    duration_symbols: Sequence[str] = ("TLT", "IEF"),
    return_suffix: str = "return_1",
    threshold: float = 0.0,
) -> pd.DataFrame:
    """Add descriptive rates-up/down context from duration proxy returns."""
    symbols = _normalize_symbols(duration_symbols, "duration_symbols")
    result = df.copy()
    columns = [_symbol_column(symbol, return_suffix) for symbol in symbols]
    _require_columns(result, columns)
    proxy_returns = result[columns].apply(pd.to_numeric, errors="coerce")
    mean_return = proxy_returns.mean(axis=1)
    result["macro_rates_proxy_mean_return"] = mean_return
    result["macro_rates_context"] = np.select(
        [mean_return.lt(-threshold), mean_return.gt(threshold)],
        ["rates_up", "rates_down"],
        default="rates_mixed",
    )
    return result


def add_credit_regime_features(
    df: pd.DataFrame,
    *,
    credit_risk_symbol: str = "HYG",
    credit_quality_symbol: str = "LQD",
    return_suffix: str = "return_1",
    threshold: float = 0.0,
) -> pd.DataFrame:
    """Add descriptive credit-risk-on/off context from credit proxy spread returns."""
    risk_symbol = _normalize_symbol(credit_risk_symbol)
    quality_symbol = _normalize_symbol(credit_quality_symbol)
    result = df.copy()
    risk_column = _symbol_column(risk_symbol, return_suffix)
    quality_column = _symbol_column(quality_symbol, return_suffix)
    _require_columns(result, [risk_column, quality_column])
    spread = pd.to_numeric(result[risk_column], errors="coerce") - pd.to_numeric(result[quality_column], errors="coerce")
    result["macro_credit_risk_spread_return"] = spread
    result["macro_credit_context"] = np.select(
        [spread.gt(threshold), spread.lt(-threshold)],
        ["credit_risk_on", "credit_risk_off"],
        default="credit_mixed",
    )
    return result


def add_commodity_regime_features(
    df: pd.DataFrame,
    *,
    commodity_symbols: Sequence[str] = ("GLD", "USO"),
    return_suffix: str = "return_1",
    threshold: float = 0.0,
) -> pd.DataFrame:
    """Add descriptive commodity-up/down context from commodity proxy returns."""
    symbols = _normalize_symbols(commodity_symbols, "commodity_symbols")
    result = df.copy()
    columns = [_symbol_column(symbol, return_suffix) for symbol in symbols]
    _require_columns(result, columns)
    proxy_returns = result[columns].apply(pd.to_numeric, errors="coerce")
    mean_return = proxy_returns.mean(axis=1)
    result["macro_commodity_proxy_mean_return"] = mean_return
    result["macro_commodity_context"] = np.select(
        [mean_return.gt(threshold), mean_return.lt(-threshold)],
        ["commodity_up", "commodity_down"],
        default="commodity_mixed",
    )
    return result


def add_volatility_proxy_regime_features(
    df: pd.DataFrame,
    *,
    volatility_symbols: Sequence[str] = ("VIXY", "VXX"),
    return_suffix: str = "return_1",
    threshold: float = 0.0,
) -> pd.DataFrame:
    """Add descriptive volatility-proxy-up/down context."""
    symbols = _normalize_symbols(volatility_symbols, "volatility_symbols")
    result = df.copy()
    columns = [_symbol_column(symbol, return_suffix) for symbol in symbols]
    _require_columns(result, columns)
    proxy_returns = result[columns].apply(pd.to_numeric, errors="coerce")
    mean_return = proxy_returns.mean(axis=1)
    result["macro_volatility_proxy_mean_return"] = mean_return
    result["macro_volatility_proxy_context"] = np.select(
        [mean_return.gt(threshold), mean_return.lt(-threshold)],
        ["volatility_proxy_up", "volatility_proxy_down"],
        default="volatility_proxy_mixed",
    )
    return result


def add_risk_on_risk_off_features(
    df: pd.DataFrame,
    *,
    primary_symbol: str = "SPY",
    return_suffix: str = "return_1",
    credit_context_column: str = "macro_credit_context",
    volatility_context_column: str = "macro_volatility_proxy_context",
) -> pd.DataFrame:
    """Add descriptive risk-on/risk-off/mixed context from existing macro regimes."""
    primary = _normalize_symbol(primary_symbol)
    result = df.copy()
    primary_return_column = _symbol_column(primary, return_suffix)
    _require_columns(result, [primary_return_column, credit_context_column, volatility_context_column])
    primary_return = pd.to_numeric(result[primary_return_column], errors="coerce")
    credit = result[credit_context_column].astype("string")
    volatility = result[volatility_context_column].astype("string")
    risk_on = primary_return.gt(0) & credit.eq("credit_risk_on") & volatility.eq("volatility_proxy_down")
    risk_off = primary_return.lt(0) & (credit.eq("credit_risk_off") | volatility.eq("volatility_proxy_up"))
    result["macro_risk_context"] = np.select(
        [risk_on, risk_off],
        ["risk_on", "risk_off"],
        default="risk_mixed",
    )
    return result


def add_macro_regime_features(
    df: pd.DataFrame,
    *,
    primary_symbol: str = "SPY",
    macro_symbols: Sequence[str] = ("TLT", "IEF", "HYG", "LQD", "GLD", "USO", "UUP", "VIXY", "VXX"),
    price_suffix: str = "close",
    return_periods: int = 1,
    duration_symbols: Sequence[str] = ("TLT", "IEF"),
    credit_risk_symbol: str = "HYG",
    credit_quality_symbol: str = "LQD",
    commodity_symbols: Sequence[str] = ("GLD", "USO"),
    volatility_symbols: Sequence[str] = ("VIXY", "VXX"),
    threshold: float = 0.0,
) -> pd.DataFrame:
    """Compose causal macro regime context features for descriptive research."""
    result = add_macro_relative_return_features(
        df,
        primary_symbol=primary_symbol,
        macro_symbols=macro_symbols,
        price_suffix=price_suffix,
        periods=return_periods,
    )
    return_suffix = f"return_{return_periods}"
    result = add_rates_regime_features(
        result,
        duration_symbols=duration_symbols,
        return_suffix=return_suffix,
        threshold=threshold,
    )
    result = add_credit_regime_features(
        result,
        credit_risk_symbol=credit_risk_symbol,
        credit_quality_symbol=credit_quality_symbol,
        return_suffix=return_suffix,
        threshold=threshold,
    )
    result = add_commodity_regime_features(
        result,
        commodity_symbols=commodity_symbols,
        return_suffix=return_suffix,
        threshold=threshold,
    )
    result = add_volatility_proxy_regime_features(
        result,
        volatility_symbols=volatility_symbols,
        return_suffix=return_suffix,
        threshold=threshold,
    )
    result = add_risk_on_risk_off_features(
        result,
        primary_symbol=primary_symbol,
        return_suffix=return_suffix,
    )
    result["macro_regime_context_caveat"] = MACRO_REGIME_CONTEXT_CAVEAT
    return result


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
