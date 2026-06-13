"""Rule-based causal market-regime classification.

Regimes are descriptive context features only. They are not trading signals,
confidence scores, edge claims, or performance analytics.
"""

from __future__ import annotations

from numbers import Real

import numpy as np
import pandas as pd

from spy_edge_research.market_regime.regime_features import add_regime_features

TRENDING_UP = "Trending Up"
TRENDING_DOWN = "Trending Down"
RANGE_BOUND = "Range Bound"
UNKNOWN_DIRECTIONAL_REGIME = "Unknown"

HIGH_VOLATILITY = "High Volatility"
NORMAL_VOLATILITY = "Normal Volatility"
LOW_VOLATILITY = "Low Volatility"
UNKNOWN_VOLATILITY_REGIME = "Unknown"


def classify_directional_regime(
    df: pd.DataFrame,
    adx_col: str = "adx_14",
    adx_trend_threshold: float = 20.0,
) -> pd.Series:
    """Classify deterministic directional regimes from causal feature columns.

    The rule uses bullish and bearish evidence counts. At least three usable
    evidence fields are required. A directional regime requires a score of at
    least three and a two-point advantage. Low ADX prefers range-bound unless
    directional evidence is stronger: at least four points and a three-point
    advantage. High VWAP cross counts are treated as choppy context and prefer
    range-bound.
    """
    _validate_non_negative_number(adx_trend_threshold, "adx_trend_threshold")

    bullish_score = pd.Series(0, index=df.index, dtype="int64")
    bearish_score = pd.Series(0, index=df.index, dtype="int64")
    available = pd.Series(0, index=df.index, dtype="int64")

    for column in ["above_vwap", "vwap_slope_positive", "above_ema", "ema_slope_positive", "structure_bullish"]:
        _add_boolean_evidence(df, column, bullish_score, available)
    for column in ["below_vwap", "vwap_slope_negative", "below_ema", "ema_slope_negative", "structure_bearish"]:
        _add_boolean_evidence(df, column, bearish_score, available)

    if "close_position_in_intraday_range" in df.columns:
        position = df["close_position_in_intraday_range"]
        usable = position.notna()
        available += usable.astype(int)
        bullish_score += (usable & (position >= 0.65)).astype(int)
        bearish_score += (usable & (position <= 0.35)).astype(int)

    high_cross_count = _high_vwap_cross_count(df)
    adx = df[adx_col] if adx_col in df.columns else pd.Series(np.nan, index=df.index)
    adx_available = adx.notna()
    low_adx = adx_available & (adx < adx_trend_threshold)
    trend_adx = (~adx_available) | (adx >= adx_trend_threshold)

    regimes: list[str] = []
    for index in df.index:
        if available.loc[index] < 3:
            regimes.append(UNKNOWN_DIRECTIONAL_REGIME)
            continue

        bullish = int(bullish_score.loc[index])
        bearish = int(bearish_score.loc[index])
        diff = bullish - bearish
        strong_up = bullish >= 3 and diff >= 2
        strong_down = bearish >= 3 and diff <= -2
        very_strong_up = bullish >= 4 and diff >= 3
        very_strong_down = bearish >= 4 and diff <= -3

        if bool(high_cross_count.loc[index]):
            regimes.append(RANGE_BOUND)
        elif bool(low_adx.loc[index]) and not (very_strong_up or very_strong_down):
            regimes.append(RANGE_BOUND)
        elif strong_up and (bool(trend_adx.loc[index]) or very_strong_up):
            regimes.append(TRENDING_UP)
        elif strong_down and (bool(trend_adx.loc[index]) or very_strong_down):
            regimes.append(TRENDING_DOWN)
        else:
            regimes.append(RANGE_BOUND)

    return pd.Series(regimes, index=df.index, name="directional_regime")


def classify_volatility_regime(
    df: pd.DataFrame,
    atr_pct_col: str = "atr_14_pct",
    bb_width_col: str = "bb_width_20",
    bb_width_window: int = 50,
    high_atr_pct_threshold: float | None = None,
    low_atr_pct_threshold: float | None = None,
) -> pd.Series:
    """Classify volatility regimes from ATR pct and optional Bollinger width.

    Explicit ATR thresholds classify ATR directly. Without explicit thresholds,
    prior trailing rolling quantiles are used: 70th percentile for high and 30th
    percentile for low. Threshold windows are shifted before rolling so the
    current row cannot set its own threshold.
    """
    _validate_minimum_int(bb_width_window, "bb_width_window", 2)
    _validate_thresholds(high_atr_pct_threshold, low_atr_pct_threshold)

    if high_atr_pct_threshold is not None or low_atr_pct_threshold is not None:
        return _classify_with_explicit_atr_thresholds(
            df,
            atr_pct_col,
            high_atr_pct_threshold,
            low_atr_pct_threshold,
        )

    high_evidence = pd.Series(False, index=df.index)
    low_evidence = pd.Series(False, index=df.index)
    available = pd.Series(False, index=df.index)

    if atr_pct_col in df.columns:
        atr = df[atr_pct_col]
        atr_high = atr.shift(1).rolling(bb_width_window).quantile(0.70)
        atr_low = atr.shift(1).rolling(bb_width_window).quantile(0.30)
        usable = atr.notna() & atr_high.notna() & atr_low.notna()
        available |= usable
        high_evidence |= usable & (atr >= atr_high)
        low_evidence |= usable & (atr <= atr_low)

    if bb_width_col in df.columns:
        width = df[bb_width_col]
        width_high = width.shift(1).rolling(bb_width_window).quantile(0.70)
        width_low = width.shift(1).rolling(bb_width_window).quantile(0.30)
        usable = width.notna() & width_high.notna() & width_low.notna()
        available |= usable
        high_evidence |= usable & (width >= width_high)
        low_evidence |= usable & (width <= width_low)

    return _volatility_series_from_evidence(available, high_evidence, low_evidence)


def add_market_regime_classification(
    df: pd.DataFrame,
    adx_col: str = "adx_14",
    adx_trend_threshold: float = 20.0,
    atr_pct_col: str = "atr_14_pct",
    bb_width_col: str = "bb_width_20",
    bb_width_window: int = 50,
    high_atr_pct_threshold: float | None = None,
    low_atr_pct_threshold: float | None = None,
) -> pd.DataFrame:
    """Add directional, volatility, and combined market-regime labels."""
    result = df.copy()
    result["directional_regime"] = classify_directional_regime(
        result,
        adx_col=adx_col,
        adx_trend_threshold=adx_trend_threshold,
    )
    result["volatility_regime"] = classify_volatility_regime(
        result,
        atr_pct_col=atr_pct_col,
        bb_width_col=bb_width_col,
        bb_width_window=bb_width_window,
        high_atr_pct_threshold=high_atr_pct_threshold,
        low_atr_pct_threshold=low_atr_pct_threshold,
    )
    result["market_regime"] = (
        result["directional_regime"] + " / " + result["volatility_regime"]
    )
    return result


def add_market_regime_features(
    df: pd.DataFrame,
    timezone: str = "America/New_York",
    vwap_cross_window: int = 20,
    adx_trend_threshold: float = 20.0,
    bb_width_window: int = 50,
    high_atr_pct_threshold: float | None = None,
    low_atr_pct_threshold: float | None = None,
) -> pd.DataFrame:
    """Compose causal regime features and descriptive classifications."""
    result = add_regime_features(
        df,
        timezone=timezone,
        vwap_cross_window=vwap_cross_window,
    )
    return add_market_regime_classification(
        result,
        adx_trend_threshold=adx_trend_threshold,
        bb_width_window=bb_width_window,
        high_atr_pct_threshold=high_atr_pct_threshold,
        low_atr_pct_threshold=low_atr_pct_threshold,
    )


def _add_boolean_evidence(
    df: pd.DataFrame,
    column: str,
    score: pd.Series,
    available: pd.Series,
) -> None:
    if column not in df.columns:
        return
    values = df[column]
    usable = values.notna()
    available += usable.astype(int)
    score += values.fillna(False).astype(bool).astype(int)


def _high_vwap_cross_count(df: pd.DataFrame) -> pd.Series:
    result = pd.Series(False, index=df.index)
    for column in df.columns:
        if not column.startswith("vwap_cross_count_"):
            continue
        window = _parse_window_suffix(column)
        threshold = max(3, int(np.ceil(window * 0.30)))
        result |= df[column].fillna(0) >= threshold
    return result


def _parse_window_suffix(column: str) -> int:
    suffix = column.rsplit("_", maxsplit=1)[-1]
    if suffix.isdigit():
        return int(suffix)
    return 20


def _classify_with_explicit_atr_thresholds(
    df: pd.DataFrame,
    atr_pct_col: str,
    high_threshold: float | None,
    low_threshold: float | None,
) -> pd.Series:
    if atr_pct_col not in df.columns:
        return pd.Series(UNKNOWN_VOLATILITY_REGIME, index=df.index, name="volatility_regime")

    atr = df[atr_pct_col]
    regimes: list[str] = []
    for value in atr:
        if pd.isna(value):
            regimes.append(UNKNOWN_VOLATILITY_REGIME)
        elif high_threshold is not None and value >= high_threshold:
            regimes.append(HIGH_VOLATILITY)
        elif low_threshold is not None and value <= low_threshold:
            regimes.append(LOW_VOLATILITY)
        else:
            regimes.append(NORMAL_VOLATILITY)
    return pd.Series(regimes, index=df.index, name="volatility_regime")


def _volatility_series_from_evidence(
    available: pd.Series,
    high_evidence: pd.Series,
    low_evidence: pd.Series,
) -> pd.Series:
    regimes: list[str] = []
    for index in available.index:
        if not bool(available.loc[index]):
            regimes.append(UNKNOWN_VOLATILITY_REGIME)
        elif bool(high_evidence.loc[index]) and not bool(low_evidence.loc[index]):
            regimes.append(HIGH_VOLATILITY)
        elif bool(low_evidence.loc[index]) and not bool(high_evidence.loc[index]):
            regimes.append(LOW_VOLATILITY)
        else:
            regimes.append(NORMAL_VOLATILITY)
    return pd.Series(regimes, index=available.index, name="volatility_regime")


def _validate_non_negative_number(value: float, name: str) -> None:
    if not isinstance(value, Real) or isinstance(value, bool) or value < 0:
        raise ValueError(f"{name} must be greater than or equal to 0")


def _validate_minimum_int(value: int, name: str, minimum: int) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value < minimum:
        raise ValueError(f"{name} must be an integer greater than or equal to {minimum}")


def _validate_thresholds(high_threshold: float | None, low_threshold: float | None) -> None:
    for threshold, name in [
        (high_threshold, "high_atr_pct_threshold"),
        (low_threshold, "low_atr_pct_threshold"),
    ]:
        if threshold is not None and (
            not isinstance(threshold, Real) or isinstance(threshold, bool)
        ):
            raise ValueError(f"{name} must be a number or None")
    if high_threshold is not None and low_threshold is not None and high_threshold < low_threshold:
        raise ValueError("high_atr_pct_threshold must be greater than or equal to low_atr_pct_threshold")
