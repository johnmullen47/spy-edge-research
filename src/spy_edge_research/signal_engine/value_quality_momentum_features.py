"""Causal cross-sectional value / quality / momentum price-factor features (MOD 13).

Phase-8 systematic factor research, built only from OHLCV price data (the platform
ingests no fundamentals). For a timestamp-aligned multi-symbol frame (one
``{SYMBOL}_{suffix}`` column per symbol, as produced by
``market_data.multi_symbol_alignment``), this computes three price-based factor
scores per symbol and ranks them cross-sectionally across the universe at each
timestamp:

- **momentum** — trailing return over a lookback (a symbol that has risen).
- **quality (low-volatility proxy)** — negative trailing realized volatility (a
  symbol whose returns are steadier).
- **value (short-term reversal proxy)** — negative recent return (a symbol that is
  recently cheaper).

All scores use only current and prior rows; cross-sectional ranks use only same-row
values across symbols. These are descriptive research context — not factor
allocations, weights, timing signals, or execution instructions. Distinct from
MOD 07 (which studies factor *ETFs* as instruments): this scores any symbol
universe cross-sectionally from price alone.
"""

from __future__ import annotations

from collections.abc import Sequence

import pandas as pd

from spy_edge_research._internal._common import require_columns, validate_positive_int

VQM_CONTEXT_CAVEAT = (
    "causal_cross_sectional_price_factor_research_only_not_allocation_or_execution"
)

MOMENTUM_SCORE = "momentum_score"
QUALITY_SCORE = "quality_score"
VALUE_SCORE = "value_score"
COMPOSITE_RANK = "vqm_composite_xs_rank"


def add_momentum_score(
    df: pd.DataFrame,
    *,
    symbols: Sequence[str],
    price_suffix: str = "close",
    lookback: int = 20,
) -> pd.DataFrame:
    """Add a trailing-return momentum score per symbol (causal)."""
    validate_positive_int(lookback, "lookback")
    syms = _normalize_symbols(symbols)
    result = df.copy()
    require_columns(result, [_col(s, price_suffix) for s in syms])
    for symbol in syms:
        price = pd.to_numeric(result[_col(symbol, price_suffix)], errors="coerce")
        result[_col(symbol, MOMENTUM_SCORE)] = price.pct_change(lookback)
    return result


def add_quality_score(
    df: pd.DataFrame,
    *,
    symbols: Sequence[str],
    price_suffix: str = "close",
    window: int = 20,
    min_periods: int = 5,
) -> pd.DataFrame:
    """Add a low-volatility 'quality' score per symbol (higher = steadier; causal)."""
    validate_positive_int(window, "window")
    validate_positive_int(min_periods, "min_periods")
    syms = _normalize_symbols(symbols)
    result = df.copy()
    require_columns(result, [_col(s, price_suffix) for s in syms])
    for symbol in syms:
        price = pd.to_numeric(result[_col(symbol, price_suffix)], errors="coerce")
        realized_vol = price.pct_change().rolling(window, min_periods=min_periods).std(ddof=0)
        # Negative volatility so a higher score is steadier (higher "quality").
        result[_col(symbol, QUALITY_SCORE)] = -realized_vol
    return result


def add_value_score(
    df: pd.DataFrame,
    *,
    symbols: Sequence[str],
    price_suffix: str = "close",
    lookback: int = 5,
) -> pd.DataFrame:
    """Add a short-term-reversal 'value' score per symbol (higher = recently cheaper)."""
    validate_positive_int(lookback, "lookback")
    syms = _normalize_symbols(symbols)
    result = df.copy()
    require_columns(result, [_col(s, price_suffix) for s in syms])
    for symbol in syms:
        price = pd.to_numeric(result[_col(symbol, price_suffix)], errors="coerce")
        # Negative recent return: a symbol that has fallen scores as "cheaper".
        result[_col(symbol, VALUE_SCORE)] = -price.pct_change(lookback)
    return result


def add_cross_sectional_factor_ranks(
    df: pd.DataFrame,
    *,
    symbols: Sequence[str],
    score_name: str,
) -> pd.DataFrame:
    """Rank ``{symbol}_{score_name}`` across symbols per row, as a [0, 1] pct rank.

    The rank uses only the same row's values across symbols, so it introduces no
    look-ahead. Rows where every symbol's score is missing yield NaN ranks.
    """
    syms = _normalize_symbols(symbols)
    score_columns = [_col(s, score_name) for s in syms]
    result = df.copy()
    require_columns(result, score_columns)
    numeric = result[score_columns].apply(pd.to_numeric, errors="coerce")
    ranks = numeric.rank(axis=1, method="average", pct=True, na_option="keep")
    for symbol, column in zip(syms, score_columns):
        result[f"{column}_xs_rank"] = ranks[column]
    return result


def add_value_quality_momentum_features(
    df: pd.DataFrame,
    *,
    symbols: Sequence[str],
    price_suffix: str = "close",
    momentum_lookback: int = 20,
    quality_window: int = 20,
    quality_min_periods: int = 5,
    value_lookback: int = 5,
) -> pd.DataFrame:
    """Compose the three causal factor scores, their cross-sectional ranks, and a
    composite VQM rank per symbol (the mean of the three score ranks)."""
    syms = _normalize_symbols(symbols)
    result = add_momentum_score(df, symbols=syms, price_suffix=price_suffix, lookback=momentum_lookback)
    result = add_quality_score(
        result, symbols=syms, price_suffix=price_suffix, window=quality_window, min_periods=quality_min_periods
    )
    result = add_value_score(result, symbols=syms, price_suffix=price_suffix, lookback=value_lookback)
    for score_name in (MOMENTUM_SCORE, QUALITY_SCORE, VALUE_SCORE):
        result = add_cross_sectional_factor_ranks(result, symbols=syms, score_name=score_name)
    for symbol in syms:
        rank_columns = [
            f"{_col(symbol, score_name)}_xs_rank"
            for score_name in (MOMENTUM_SCORE, QUALITY_SCORE, VALUE_SCORE)
        ]
        result[_col(symbol, COMPOSITE_RANK)] = result[rank_columns].mean(axis=1)
    result["vqm_context_caveat"] = VQM_CONTEXT_CAVEAT
    return result


def _col(symbol: str, suffix: str) -> str:
    return f"{_normalize_symbol(symbol)}_{suffix.strip('_')}"


def _normalize_symbol(symbol: str | None) -> str:
    if not isinstance(symbol, str) or not symbol.strip():
        raise ValueError("symbols must be non-empty strings")
    return symbol.strip().upper()


def _normalize_symbols(symbols: Sequence[str]) -> list[str]:
    if isinstance(symbols, str):
        symbols = [symbols]
    normalized = [_normalize_symbol(symbol) for symbol in symbols]
    if not normalized:
        raise ValueError("symbols must contain at least one symbol")
    duplicates = sorted({s for s in normalized if normalized.count(s) > 1})
    if duplicates:
        raise ValueError(f"symbols contains duplicates: {duplicates}")
    return normalized
