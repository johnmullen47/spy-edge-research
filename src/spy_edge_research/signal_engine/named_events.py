"""Named causal event feature definitions.

Named events compose existing causal primitives into recognizable research
feature columns. They are not trading signals, scores, confidence estimates,
backtests, execution instructions, or edge claims.
"""

from __future__ import annotations

import pandas as pd

from spy_edge_research.signal_engine.events import crosses_above, crosses_below

STANDARD_ZONE_NAMES: tuple[str, ...] = (
    "prior_day_high",
    "prior_day_low",
    "prior_day_close",
    "premarket_high",
    "premarket_low",
    "pivot_high",
    "pivot_low",
)

SUPPORT_RETEST_SUFFIXES: tuple[tuple[str, str], ...] = (
    ("touch", "_support_retest_touch"),
    ("hold", "_support_retest_hold"),
    ("failure", "_support_retest_failure"),
)

RESISTANCE_RETEST_SUFFIXES: tuple[tuple[str, str], ...] = (
    ("touch", "_resistance_retest_touch"),
    ("hold", "_resistance_retest_hold"),
    ("failure", "_resistance_retest_failure"),
)

BULLISH_CONTEXT_COLUMNS: tuple[str, ...] = (
    "above_vwap",
    "above_ema",
    "vwap_slope_positive",
    "ema_slope_positive",
)

BEARISH_CONTEXT_COLUMNS: tuple[str, ...] = (
    "below_vwap",
    "below_ema",
    "vwap_slope_negative",
    "ema_slope_negative",
)


def add_vwap_named_events(
    df: pd.DataFrame,
    close_col: str = "close",
    high_col: str = "high",
    low_col: str = "low",
    vwap_col: str = "vwap",
) -> pd.DataFrame:
    """Add named VWAP reclaim, loss, rejection, and bounce event columns."""
    _require_columns(df, [close_col, high_col, low_col, vwap_col])

    result = df.copy()
    close = result[close_col]
    high = result[high_col]
    low = result[low_col]
    vwap = result[vwap_col]
    prior_close = close.shift(1)
    prior_vwap = vwap.shift(1)

    result["event_vwap_reclaim_bullish"] = crosses_above(close, vwap)
    result["event_vwap_loss_bearish"] = crosses_below(close, vwap)
    result["event_vwap_rejection_bearish"] = _bool_series(
        (high >= vwap) & (close < vwap) & (prior_close < prior_vwap),
        result.index,
    )
    result["event_vwap_bounce_bullish"] = _bool_series(
        (low <= vwap) & (close > vwap) & (prior_close > prior_vwap),
        result.index,
    )
    return result


def add_trailing_break_named_events(
    df: pd.DataFrame,
    lookback: int = 20,
) -> pd.DataFrame:
    """Copy causal trailing break primitives into named event columns."""
    _validate_positive_int(lookback, "lookback")
    above_col = f"breaks_above_trailing_high_{lookback}"
    below_col = f"breaks_below_trailing_low_{lookback}"
    _require_columns(df, [above_col, below_col])

    result = df.copy()
    result[f"event_trailing_breakout_{lookback}"] = _bool_series(
        result[above_col], result.index
    )
    result[f"event_trailing_breakdown_{lookback}"] = _bool_series(
        result[below_col], result.index
    )
    return result


def add_standard_zone_break_named_events(
    df: pd.DataFrame,
    close_col: str = "close",
) -> pd.DataFrame:
    """Add named crossing events for available standard support/resistance zones."""
    _require_columns(df, [close_col])

    result = df.copy()
    close = result[close_col]
    for zone_name in STANDARD_ZONE_NAMES:
        lower_col = f"{zone_name}_zone_lower"
        upper_col = f"{zone_name}_zone_upper"
        if not _has_columns(result, [lower_col, upper_col]):
            continue
        result[f"event_{zone_name}_break_above"] = crosses_above(
            close, result[upper_col]
        )
        result[f"event_{zone_name}_break_below"] = crosses_below(
            close, result[lower_col]
        )
    return result


def add_structure_named_events(
    df: pd.DataFrame,
    bullish_break_col: str = "bullish_structure_break",
    bearish_break_col: str = "bearish_structure_break",
    structure_state_col: str = "structure_state",
) -> pd.DataFrame:
    """Add named structure break and structure-context event columns."""
    result = df.copy()

    if bullish_break_col in result.columns:
        result["event_bullish_structure_break"] = _bool_series(
            result[bullish_break_col], result.index
        )
    if bearish_break_col in result.columns:
        result["event_bearish_structure_break"] = _bool_series(
            result[bearish_break_col], result.index
        )
    if structure_state_col in result.columns:
        normalized = result[structure_state_col].astype("string").str.strip().str.lower()
        bullish = normalized.isin({"bullish", "up", "trending up"})
        bearish = normalized.isin({"bearish", "down", "trending down"})
        result["event_structure_context_bullish"] = _bool_series(bullish, result.index)
        result["event_structure_context_bearish"] = _bool_series(bearish, result.index)
        result["event_structure_context_range_or_unknown"] = _bool_series(
            ~(bullish | bearish), result.index
        )
    return result


def add_retest_named_events(
    df: pd.DataFrame,
    trailing_lookback: int = 20,
) -> pd.DataFrame:
    """Add named retest event columns from available causal retest outputs."""
    _validate_positive_int(trailing_lookback, "trailing_lookback")
    result = df.copy()

    for direction in ("breakout", "breakdown"):
        for event_name in ("touch", "hold", "failure"):
            source_col = f"{direction}_retest_{event_name}_{trailing_lookback}"
            if source_col in result.columns:
                result[f"event_{direction}_retest_{event_name}_{trailing_lookback}"] = (
                    _bool_series(result[source_col], result.index)
                )

    for event_name, suffix in SUPPORT_RETEST_SUFFIXES:
        columns = _find_existing_columns(result, suffix)
        if columns:
            result[f"event_any_support_retest_{event_name}"] = _safe_or(
                result, columns
            )

    for event_name, suffix in RESISTANCE_RETEST_SUFFIXES:
        columns = _find_existing_columns(result, suffix)
        if columns:
            result[f"event_any_resistance_retest_{event_name}"] = _safe_or(
                result, columns
            )
    return result


def add_false_break_named_events(
    df: pd.DataFrame,
    lookback: int = 20,
) -> pd.DataFrame:
    """Copy already-emitted false-break primitives into named event columns."""
    _validate_positive_int(lookback, "lookback")
    result = df.copy()

    breakout_col = f"false_breakout_{lookback}"
    breakdown_col = f"false_breakdown_{lookback}"
    if breakout_col in result.columns:
        result[f"event_failed_breakout_{lookback}"] = _bool_series(
            result[breakout_col], result.index
        )
    if breakdown_col in result.columns:
        result[f"event_failed_breakdown_{lookback}"] = _bool_series(
            result[breakdown_col], result.index
        )
    return result


def add_momentum_volume_named_events(
    df: pd.DataFrame,
    consecutive_count: int = 3,
    expansion_window: int = 20,
) -> pd.DataFrame:
    """Add named momentum, range, volume, and combined expansion events."""
    _validate_minimum_int(consecutive_count, "consecutive_count", minimum=2)
    _validate_positive_int(expansion_window, "expansion_window")

    result = df.copy()
    up_col = f"consecutive_higher_closes_{consecutive_count}"
    down_col = f"consecutive_lower_closes_{consecutive_count}"
    range_col = f"range_expansion_{expansion_window}"
    volume_col = f"volume_expansion_{expansion_window}"

    if up_col in result.columns:
        result[f"event_momentum_up_{consecutive_count}"] = _bool_series(
            result[up_col], result.index
        )
    if down_col in result.columns:
        result[f"event_momentum_down_{consecutive_count}"] = _bool_series(
            result[down_col], result.index
        )
    if range_col in result.columns:
        result[f"event_range_expansion_{expansion_window}"] = _bool_series(
            result[range_col], result.index
        )
    if volume_col in result.columns:
        result[f"event_volume_expansion_{expansion_window}"] = _bool_series(
            result[volume_col], result.index
        )

    if _has_columns(result, [up_col, range_col]):
        result[f"event_momentum_expansion_up_{consecutive_count}_{expansion_window}"] = (
            _safe_and(result, [up_col, range_col])
        )
    if _has_columns(result, [down_col, range_col]):
        result[f"event_momentum_expansion_down_{consecutive_count}_{expansion_window}"] = (
            _safe_and(result, [down_col, range_col])
        )
    if _has_columns(result, [up_col, volume_col]):
        result[
            f"event_volume_confirmed_momentum_up_{consecutive_count}_{expansion_window}"
        ] = _safe_and(result, [up_col, volume_col])
    if _has_columns(result, [down_col, volume_col]):
        result[
            f"event_volume_confirmed_momentum_down_{consecutive_count}_{expansion_window}"
        ] = _safe_and(result, [down_col, volume_col])
    return result


def add_trend_continuation_named_events(
    df: pd.DataFrame,
    consecutive_count: int = 3,
) -> pd.DataFrame:
    """Add named trend-continuation context events when source columns exist."""
    _validate_minimum_int(consecutive_count, "consecutive_count", minimum=2)
    result = df.copy()

    if "directional_regime" not in result.columns:
        return result

    up_momentum_col = _first_existing_column(
        result,
        [
            f"event_momentum_up_{consecutive_count}",
            f"consecutive_higher_closes_{consecutive_count}",
        ],
    )
    down_momentum_col = _first_existing_column(
        result,
        [
            f"event_momentum_down_{consecutive_count}",
            f"consecutive_lower_closes_{consecutive_count}",
        ],
    )

    if up_momentum_col is not None:
        bullish_confirmations = _existing_columns(result, BULLISH_CONTEXT_COLUMNS)
        up_context = (
            result["directional_regime"].eq("Trending Up")
            & _bool_series(result[up_momentum_col], result.index)
        )
        if bullish_confirmations:
            up_context &= _safe_or(result, bullish_confirmations)
        result["event_trend_continuation_up_context"] = _bool_series(
            up_context, result.index
        )

    if down_momentum_col is not None:
        bearish_confirmations = _existing_columns(result, BEARISH_CONTEXT_COLUMNS)
        down_context = (
            result["directional_regime"].eq("Trending Down")
            & _bool_series(result[down_momentum_col], result.index)
        )
        if bearish_confirmations:
            down_context &= _safe_or(result, bearish_confirmations)
        result["event_trend_continuation_down_context"] = _bool_series(
            down_context, result.index
        )
    return result


def add_named_event_features(
    df: pd.DataFrame,
    trailing_lookback: int = 20,
    consecutive_count: int = 3,
    expansion_window: int = 20,
) -> pd.DataFrame:
    """Compose all available named causal event feature groups."""
    result = df.copy()

    if _has_columns(result, ["close", "high", "low", "vwap"]):
        result = add_vwap_named_events(result)
    if _has_columns(
        result,
        [
            f"breaks_above_trailing_high_{trailing_lookback}",
            f"breaks_below_trailing_low_{trailing_lookback}",
        ],
    ):
        result = add_trailing_break_named_events(result, lookback=trailing_lookback)
    if "close" in result.columns:
        result = add_standard_zone_break_named_events(result)
    result = add_structure_named_events(result)
    result = add_retest_named_events(result, trailing_lookback=trailing_lookback)
    result = add_false_break_named_events(result, lookback=trailing_lookback)
    result = add_momentum_volume_named_events(
        result,
        consecutive_count=consecutive_count,
        expansion_window=expansion_window,
    )
    return add_trend_continuation_named_events(
        result,
        consecutive_count=consecutive_count,
    )


def find_named_event_columns(
    df: pd.DataFrame,
    prefix: str = "event_",
) -> tuple[str, ...]:
    """Return event feature columns in DataFrame column order."""
    return tuple(column for column in df.columns if column.startswith(prefix))


def _require_columns(df: pd.DataFrame, columns: list[str]) -> None:
    missing = [column for column in columns if column not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")


def _has_columns(df: pd.DataFrame, columns: list[str]) -> bool:
    return all(column in df.columns for column in columns)


def _bool_series(values: pd.Series, index: pd.Index) -> pd.Series:
    return pd.Series(values, index=index).astype("boolean").fillna(False).astype(bool)


def _safe_or(df: pd.DataFrame, columns: list[str]) -> pd.Series:
    result = pd.Series(False, index=df.index)
    for column in columns:
        result |= _bool_series(df[column], df.index)
    return result.astype(bool)


def _safe_and(df: pd.DataFrame, columns: list[str]) -> pd.Series:
    result = pd.Series(True, index=df.index)
    for column in columns:
        result &= _bool_series(df[column], df.index)
    return result.astype(bool)


def _find_existing_columns(df: pd.DataFrame, suffix: str) -> list[str]:
    return [column for column in df.columns if column.endswith(suffix)]


def _existing_columns(df: pd.DataFrame, columns: tuple[str, ...]) -> list[str]:
    return [column for column in columns if column in df.columns]


def _first_existing_column(df: pd.DataFrame, columns: list[str]) -> str | None:
    for column in columns:
        if column in df.columns:
            return column
    return None


def _validate_positive_int(value: int, name: str) -> None:
    _validate_minimum_int(value, name, minimum=1)


def _validate_minimum_int(value: int, name: str, minimum: int) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value < minimum:
        raise ValueError(f"{name} must be an integer greater than or equal to {minimum}")
