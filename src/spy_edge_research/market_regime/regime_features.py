"""Causal numeric and context features for market-regime classification."""

from __future__ import annotations

import numpy as np
import pandas as pd


def add_vwap_regime_features(
    df: pd.DataFrame,
    close_col: str = "close",
    vwap_col: str = "vwap",
    vwap_slope_col: str = "vwap_slope",
) -> pd.DataFrame:
    """Add causal VWAP relation features for regime context."""
    _require_columns(df, [close_col, vwap_col, vwap_slope_col])

    result = df.copy()
    close = result[close_col]
    vwap = result[vwap_col]
    slope = result[vwap_slope_col]

    result["above_vwap"] = _safe_bool_series(close > vwap, result.index)
    result["below_vwap"] = _safe_bool_series(close < vwap, result.index)
    result["vwap_slope_positive"] = _safe_bool_series(slope > 0, result.index)
    result["vwap_slope_negative"] = _safe_bool_series(slope < 0, result.index)
    result["vwap_distance_abs"] = (close - vwap).abs()
    return result


def add_ema_regime_features(
    df: pd.DataFrame,
    close_col: str = "close",
    ema_col: str = "ema_9",
    ema_slope_col: str = "ema_9_slope",
) -> pd.DataFrame:
    """Add causal EMA relation features for regime context."""
    _require_columns(df, [close_col, ema_col, ema_slope_col])

    result = df.copy()
    close = result[close_col]
    ema = result[ema_col]
    slope = result[ema_slope_col]

    result["above_ema"] = _safe_bool_series(close > ema, result.index)
    result["below_ema"] = _safe_bool_series(close < ema, result.index)
    result["ema_slope_positive"] = _safe_bool_series(slope > 0, result.index)
    result["ema_slope_negative"] = _safe_bool_series(slope < 0, result.index)
    result["ema_distance_abs"] = (close - ema).abs()
    return result


def add_vwap_cross_count_feature(
    df: pd.DataFrame,
    window: int = 20,
    close_col: str = "close",
    vwap_col: str = "vwap",
) -> pd.DataFrame:
    """Count close/VWAP sign changes over a trailing window including current row."""
    _validate_positive_int(window, "window")
    _require_columns(df, [close_col, vwap_col])

    result = df.copy()
    difference = result[close_col] - result[vwap_col]
    sign = np.sign(difference)
    previous_sign = sign.shift(1)
    valid = difference.notna() & difference.shift(1).notna()
    crossed = valid & (sign != 0) & (previous_sign != 0) & (sign != previous_sign)

    result["vwap_cross"] = _safe_bool_series(crossed, result.index)
    result[f"vwap_cross_count_{window}"] = (
        result["vwap_cross"].astype(int).rolling(window, min_periods=1).sum()
    )
    return result


def add_intraday_range_features(
    df: pd.DataFrame,
    timestamp_col: str = "timestamp",
    high_col: str = "high",
    low_col: str = "low",
    close_col: str = "close",
    timezone: str = "America/New_York",
) -> pd.DataFrame:
    """Add cumulative intraday high/low/range features by local trading date."""
    _require_columns(df, [timestamp_col, high_col, low_col, close_col])

    result = df.copy()
    trading_date = _local_trading_dates(result[timestamp_col], timezone)
    result["intraday_high_so_far"] = result[high_col].groupby(trading_date).cummax()
    result["intraday_low_so_far"] = result[low_col].groupby(trading_date).cummin()
    result["intraday_range_so_far"] = (
        result["intraday_high_so_far"] - result["intraday_low_so_far"]
    )
    result["close_position_in_intraday_range"] = (
        result[close_col] - result["intraday_low_so_far"]
    ).div(result["intraday_range_so_far"].replace(0, np.nan))
    return result


def add_volume_regime_features(
    df: pd.DataFrame,
    relative_volume_col: str = "relative_volume_20",
    volume_zscore_col: str = "volume_zscore_20",
) -> pd.DataFrame:
    """Add simple volume context flags for regime classification."""
    _require_columns(df, [relative_volume_col, volume_zscore_col])

    result = df.copy()
    relative_volume = result[relative_volume_col]
    volume_zscore = result[volume_zscore_col]

    result["relative_volume_available"] = relative_volume.notna()
    result["volume_zscore_available"] = volume_zscore.notna()
    result["high_relative_volume"] = _safe_bool_series(relative_volume >= 1.5, result.index)
    result["low_relative_volume"] = _safe_bool_series(relative_volume <= 0.75, result.index)
    result["positive_volume_zscore"] = _safe_bool_series(volume_zscore >= 1.0, result.index)
    result["negative_volume_zscore"] = _safe_bool_series(volume_zscore <= -1.0, result.index)
    return result


def add_structure_regime_features(
    df: pd.DataFrame,
    structure_state_col: str = "structure_state",
    bullish_break_col: str = "bullish_structure_break",
    bearish_break_col: str = "bearish_structure_break",
) -> pd.DataFrame:
    """Add structure-state flags for regime classification."""
    _require_columns(df, [structure_state_col, bullish_break_col, bearish_break_col])

    result = df.copy()
    state = result[structure_state_col].astype("string").str.lower()
    bullish_values = {"bullish", "up", "uptrend", "trend_up", "trending_up"}
    bearish_values = {"bearish", "down", "downtrend", "trend_down", "trending_down"}

    result["structure_bullish"] = _safe_bool_series(state.isin(bullish_values), result.index)
    result["structure_bearish"] = _safe_bool_series(state.isin(bearish_values), result.index)
    result["structure_range_or_unknown"] = ~(
        result["structure_bullish"] | result["structure_bearish"]
    )
    result["recent_bullish_structure_break"] = _safe_bool_series(
        result[bullish_break_col].fillna(False).astype(bool),
        result.index,
    )
    result["recent_bearish_structure_break"] = _safe_bool_series(
        result[bearish_break_col].fillna(False).astype(bool),
        result.index,
    )
    return result


def add_regime_features(
    df: pd.DataFrame,
    timezone: str = "America/New_York",
    vwap_cross_window: int = 20,
) -> pd.DataFrame:
    """Compose available causal regime feature groups without requiring all inputs."""
    result = df.copy()

    if _has_columns(result, ["close", "vwap", "vwap_slope"]):
        result = add_vwap_regime_features(result)
    if _has_columns(result, ["close", "vwap"]):
        result = add_vwap_cross_count_feature(result, window=vwap_cross_window)
    if _has_columns(result, ["close", "ema_9", "ema_9_slope"]):
        result = add_ema_regime_features(result)
    if _has_columns(result, ["timestamp", "high", "low", "close"]):
        result = add_intraday_range_features(result, timezone=timezone)
    if _has_columns(result, ["relative_volume_20", "volume_zscore_20"]):
        result = add_volume_regime_features(result)
    if _has_columns(
        result,
        ["structure_state", "bullish_structure_break", "bearish_structure_break"],
    ):
        result = add_structure_regime_features(result)
    return result


def _local_trading_dates(timestamps: pd.Series, timezone: str) -> pd.Series:
    parsed = pd.to_datetime(timestamps)
    if parsed.dt.tz is None:
        parsed = parsed.dt.tz_localize(timezone)
    else:
        parsed = parsed.dt.tz_convert(timezone)
    return pd.Series(parsed.dt.date, index=timestamps.index)


def _require_columns(df: pd.DataFrame, columns: list[str]) -> None:
    missing = [column for column in columns if column not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")


def _has_columns(df: pd.DataFrame, columns: list[str]) -> bool:
    return all(column in df.columns for column in columns)


def _safe_bool_series(values: pd.Series, index: pd.Index) -> pd.Series:
    return pd.Series(values, index=index).fillna(False).astype(bool)


def _validate_positive_int(value: int, name: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise ValueError(f"{name} must be an integer greater than or equal to 1")
