"""Forward-looking label utilities for later statistical evaluation.

These helpers intentionally look forward to create evaluation targets. Label
columns must not be used as causal features, event primitives, strategy signals,
or inputs to indicator calculations.
"""

from __future__ import annotations

from numbers import Real

import numpy as np
import pandas as pd

from spy_edge_research._internal._common import (
    require_columns as _require_columns,
    validate_positive_int as _validate_positive_int,
)


def horizon_to_bars(horizon_minutes: int, bar_interval_minutes: int = 1) -> int:
    """Convert a forward horizon in minutes to a whole number of bars."""
    _validate_positive_int(horizon_minutes, "horizon_minutes")
    _validate_positive_int(bar_interval_minutes, "bar_interval_minutes")
    if horizon_minutes % bar_interval_minutes != 0:
        raise ValueError("horizon_minutes must be evenly divisible by bar_interval_minutes")
    return horizon_minutes // bar_interval_minutes


def add_forward_return_labels(
    df: pd.DataFrame,
    horizons_minutes: tuple[int, ...] = (5, 10, 15, 30),
    price_col: str = "close",
    timestamp_col: str = "timestamp",
    bar_interval_minutes: int = 1,
    timezone: str = "America/New_York",
    prevent_cross_day: bool = True,
) -> pd.DataFrame:
    """Add forward close and return label columns.

    These labels are forward-looking evaluation targets only. When
    ``prevent_cross_day`` is True, future prices are shifted within local
    trading-date groups in ``timezone`` so labels do not cross day boundaries.
    """
    _require_columns(df, [price_col])
    if prevent_cross_day:
        _require_columns(df, [timestamp_col])
    _validate_horizons(horizons_minutes, bar_interval_minutes)

    result = df.copy()
    trading_dates = (
        _local_trading_dates(result[timestamp_col], timezone) if prevent_cross_day else None
    )

    for horizon in horizons_minutes:
        bars = horizon_to_bars(horizon, bar_interval_minutes)
        future_col = f"future_close_{horizon}m"
        return_col = f"forward_return_{horizon}m"
        bps_col = f"forward_return_bps_{horizon}m"
        valid_col = f"label_valid_{horizon}m"

        if prevent_cross_day:
            result[future_col] = result[price_col].groupby(trading_dates).shift(-bars)
        else:
            result[future_col] = result[price_col].shift(-bars)

        result[return_col] = _safe_forward_return(result[future_col], result[price_col])
        result[bps_col] = result[return_col] * 10_000
        result[valid_col] = result[future_col].notna()

    return result


def add_forward_direction_labels(
    df: pd.DataFrame,
    horizons_minutes: tuple[int, ...] = (5, 10, 15, 30),
    threshold_bps: float = 0.0,
) -> pd.DataFrame:
    """Add forward direction target labels from existing forward-return labels.

    Direction labels are target labels, not trading signals, and do not imply
    bullish or bearish trade decisions.
    """
    _validate_horizons(horizons_minutes)
    _validate_non_negative_number(threshold_bps, "threshold_bps")

    required_columns: list[str] = []
    for horizon in horizons_minutes:
        required_columns.extend(
            [f"forward_return_bps_{horizon}m", f"label_valid_{horizon}m"]
        )
    _require_columns(df, required_columns)

    result = df.copy()
    for horizon in horizons_minutes:
        bps_col = f"forward_return_bps_{horizon}m"
        valid_col = f"label_valid_{horizon}m"
        direction_col = f"forward_direction_{horizon}m"

        direction = pd.Series(np.nan, index=result.index, dtype="float64")
        valid = result[valid_col].astype(bool)
        direction.loc[valid & (result[bps_col] > threshold_bps)] = 1.0
        direction.loc[valid & (result[bps_col] < -threshold_bps)] = -1.0
        direction.loc[valid & (result[bps_col].abs() <= threshold_bps)] = 0.0
        result[direction_col] = direction

    return result


def add_forward_labels(
    df: pd.DataFrame,
    horizons_minutes: tuple[int, ...] = (5, 10, 15, 30),
    price_col: str = "close",
    timestamp_col: str = "timestamp",
    bar_interval_minutes: int = 1,
    timezone: str = "America/New_York",
    prevent_cross_day: bool = True,
    threshold_bps: float = 0.0,
) -> pd.DataFrame:
    """Add forward return and direction evaluation labels."""
    result = add_forward_return_labels(
        df,
        horizons_minutes=horizons_minutes,
        price_col=price_col,
        timestamp_col=timestamp_col,
        bar_interval_minutes=bar_interval_minutes,
        timezone=timezone,
        prevent_cross_day=prevent_cross_day,
    )
    return add_forward_direction_labels(
        result,
        horizons_minutes=horizons_minutes,
        threshold_bps=threshold_bps,
    )


def add_forward_path_outcome_labels(
    df: pd.DataFrame,
    horizons_minutes: tuple[int, ...] = (5, 10, 15, 30),
    price_col: str = "close",
    high_col: str = "high",
    low_col: str = "low",
    timestamp_col: str = "timestamp",
    bar_interval_minutes: int = 1,
    timezone: str = "America/New_York",
    prevent_cross_day: bool = True,
) -> pd.DataFrame:
    """Add forward path outcome labels for MFE/MAE evaluation.

    Path outcomes intentionally inspect future bars and are evaluation targets
    only. The current bar is excluded from the forward high/low windows.
    """
    _require_columns(df, [price_col, high_col, low_col])
    if prevent_cross_day:
        _require_columns(df, [timestamp_col])
    _validate_horizons(horizons_minutes, bar_interval_minutes)

    result = df.copy()
    trading_dates = (
        _local_trading_dates(result[timestamp_col], timezone) if prevent_cross_day else None
    )

    for horizon in horizons_minutes:
        bars = horizon_to_bars(horizon, bar_interval_minutes)
        future_high_col = f"future_high_{horizon}m"
        future_low_col = f"future_low_{horizon}m"
        mfe_col = f"forward_mfe_{horizon}m"
        mae_col = f"forward_mae_{horizon}m"
        mfe_bps_col = f"forward_mfe_bps_{horizon}m"
        mae_bps_col = f"forward_mae_bps_{horizon}m"
        valid_col = f"path_label_valid_{horizon}m"

        if prevent_cross_day:
            result[future_high_col] = result[high_col].groupby(trading_dates).transform(
                lambda values: _forward_window_extreme(values, bars, "max")
            )
            result[future_low_col] = result[low_col].groupby(trading_dates).transform(
                lambda values: _forward_window_extreme(values, bars, "min")
            )
        else:
            result[future_high_col] = _forward_window_extreme(result[high_col], bars, "max")
            result[future_low_col] = _forward_window_extreme(result[low_col], bars, "min")

        result[mfe_col] = _safe_forward_return(result[future_high_col], result[price_col])
        result[mae_col] = _safe_forward_return(result[future_low_col], result[price_col])
        result[mfe_bps_col] = result[mfe_col] * 10_000
        result[mae_bps_col] = result[mae_col] * 10_000
        result[valid_col] = result[future_high_col].notna() & result[future_low_col].notna()

    return result


def add_directional_forward_outcome_labels(
    df: pd.DataFrame,
    horizons_minutes: tuple[int, ...] = (5, 10, 15, 30),
    direction_col: str = "event_direction",
    price_col: str = "close",
) -> pd.DataFrame:
    """Normalize existing forward return/path labels for long or short hypotheses.

    Direction-normalized outputs are still outcome labels. They are useful for
    event studies where the catalog records whether an event hypothesis is long
    or short, but they must not be fed back into causal event generation.
    """
    _validate_horizons(horizons_minutes)
    _require_columns(df, [direction_col, price_col])

    required_columns: list[str] = []
    for horizon in horizons_minutes:
        required_columns.extend(
            [
                f"forward_return_{horizon}m",
                f"future_high_{horizon}m",
                f"future_low_{horizon}m",
            ]
        )
    _require_columns(df, required_columns)

    result = df.copy()
    signs = result[direction_col].map(_direction_to_sign)
    if signs.isna().any():
        bad_values = sorted(result.loc[signs.isna(), direction_col].dropna().astype(str).unique())
        raise ValueError(f"Unsupported direction values: {bad_values}")

    for horizon in horizons_minutes:
        return_col = f"forward_return_{horizon}m"
        future_high_col = f"future_high_{horizon}m"
        future_low_col = f"future_low_{horizon}m"
        directional_return_col = f"directional_forward_return_{horizon}m"
        directional_mfe_col = f"directional_forward_mfe_{horizon}m"
        directional_mae_col = f"directional_forward_mae_{horizon}m"
        directional_return_bps_col = f"directional_forward_return_bps_{horizon}m"
        directional_mfe_bps_col = f"directional_forward_mfe_bps_{horizon}m"
        directional_mae_bps_col = f"directional_forward_mae_bps_{horizon}m"

        long_mfe = _safe_forward_return(result[future_high_col], result[price_col])
        long_mae = _safe_forward_return(result[future_low_col], result[price_col])
        short_mfe = result[price_col].div(result[future_low_col].replace(0, np.nan)) - 1
        short_mae = result[price_col].div(result[future_high_col].replace(0, np.nan)) - 1

        result[directional_return_col] = result[return_col] * signs
        result[directional_mfe_col] = long_mfe.where(signs.ge(0), short_mfe)
        result[directional_mae_col] = long_mae.where(signs.ge(0), short_mae)
        result[directional_return_bps_col] = result[directional_return_col] * 10_000
        result[directional_mfe_bps_col] = result[directional_mfe_col] * 10_000
        result[directional_mae_bps_col] = result[directional_mae_col] * 10_000

    return result


def _safe_forward_return(future_price: pd.Series, current_price: pd.Series) -> pd.Series:
    denominator = current_price.replace(0, np.nan)
    return future_price.div(denominator) - 1


def _forward_window_extreme(
    values: pd.Series,
    bars: int,
    method: str,
) -> pd.Series:
    shifted = pd.concat([values.shift(-offset) for offset in range(1, bars + 1)], axis=1)
    if method == "max":
        return shifted.max(axis=1, skipna=False)
    if method == "min":
        return shifted.min(axis=1, skipna=False)
    raise ValueError("method must be 'max' or 'min'")


def _direction_to_sign(value: object) -> float | None:
    if value in ("long", "bullish", "buy", 1, 1.0):
        return 1.0
    if value in ("short", "bearish", "sell", -1, -1.0):
        return -1.0
    if pd.isna(value):
        return None
    return None


def add_session_forward_return_labels(
    df: pd.DataFrame,
    sessions: tuple[int, ...] = (1, 5, 21),
    price_col: str = "close",
    timestamp_col: str = "timestamp",
    timezone: str = "America/New_York",
) -> pd.DataFrame:
    """Add ``forward_return_{k}sess`` close-to-close labels over k trading sessions.

    For the daily/weekly-horizon families (F6 VRP, F7 vol-managed, F10 FOMC cycle),
    whose events fire on each session's **last bar**, the outcome is the return from
    that session's close to the close k sessions later. Defined only on the last bar
    of each date (NaN elsewhere) so it aligns with those families' decision bars.
    Forward-looking evaluation label only — never an event input.
    """
    _require_columns(df, [price_col, timestamp_col])
    result = df.copy()
    dates = _local_trading_dates(result[timestamp_col], timezone)
    per_date_last = result[price_col].groupby(dates).last()  # date-indexed
    is_last_bar = dates.ne(dates.shift(-1))  # rows are timestamp-sorted
    for k in sessions:
        if not isinstance(k, int) or isinstance(k, bool) or k < 1:
            raise ValueError("sessions must be positive integers")
        fwd = per_date_last.shift(-k).div(per_date_last) - 1.0  # date-indexed
        series = pd.Series(np.nan, index=result.index, dtype="float64")
        series.loc[is_last_bar] = dates.loc[is_last_bar].map(fwd).to_numpy()
        result[f"forward_return_{k}sess"] = series
    return result


def add_to_close_forward_return_label(
    df: pd.DataFrame,
    price_col: str = "close",
    timestamp_col: str = "timestamp",
    timezone: str = "America/New_York",
    column: str = "forward_return_to_close",
) -> pd.DataFrame:
    """Add a per-bar forward return to that session's close (for ORB hold-to-close).

    F8 (ORB) enters on a variable breakout bar and holds to 16:00; a fixed
    minute-horizon label cannot express that, but the return from any bar to its own
    session's last close can. On the session's last bar this is 0. Forward-looking
    evaluation label only.
    """
    _require_columns(df, [price_col, timestamp_col])
    result = df.copy()
    dates = _local_trading_dates(result[timestamp_col], timezone)
    day_last_close = result[price_col].groupby(dates).transform("last")
    result[column] = day_last_close.div(result[price_col].replace(0, np.nan)) - 1.0
    return result


def _local_trading_dates(timestamps: pd.Series, timezone: str) -> pd.Series:
    parsed = pd.to_datetime(timestamps)
    if parsed.dt.tz is None:
        parsed = parsed.dt.tz_localize(timezone)
    else:
        parsed = parsed.dt.tz_convert(timezone)
    return pd.Series(parsed.dt.date, index=timestamps.index)


def _validate_horizons(
    horizons_minutes: tuple[int, ...],
    bar_interval_minutes: int = 1,
) -> None:
    if not isinstance(horizons_minutes, tuple) or not horizons_minutes:
        raise ValueError("horizons_minutes must be a non-empty tuple of integers")
    for horizon in horizons_minutes:
        horizon_to_bars(horizon, bar_interval_minutes)


def _validate_non_negative_number(value: float, name: str) -> None:
    if not isinstance(value, Real) or isinstance(value, bool) or value < 0:
        raise ValueError(f"{name} must be greater than or equal to 0")
