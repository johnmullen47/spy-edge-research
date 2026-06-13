"""Minimal directional evaluation utilities for benchmark predictions.

This module evaluates prediction columns against forward-looking labels. It
does not create causal features, strategy signals, execution assumptions, or
profit-and-loss simulations.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def directional_profit_factor_equivalent(directional_returns: pd.Series) -> float:
    """Compute a directional return proxy similar to profit factor.

    Gross positive return is divided by gross absolute negative return. NaN and
    exactly-zero return bars are excluded from both sides (the standard
    profit-factor convention). Returns ``inf`` when only gains are present,
    ``0.0`` when only losses are present, and ``NaN`` when neither is present.
    This is a research proxy, not a tradable profit factor (no costs/slippage).
    """
    clean = directional_returns.dropna()
    positive_sum = clean.loc[clean > 0].sum()
    negative_sum = clean.loc[clean < 0].sum()

    has_positive = positive_sum > 0
    has_negative = negative_sum < 0
    if has_positive and not has_negative:
        return np.inf
    if not has_positive and has_negative:
        return 0.0
    if not has_positive and not has_negative:
        return np.nan
    return float(positive_sum / abs(negative_sum))


def evaluate_prediction_column(
    df: pd.DataFrame,
    prediction_col: str,
    horizons_minutes: tuple[int, ...] = (5, 10, 15, 30),
) -> pd.DataFrame:
    """Evaluate one benchmark prediction column against forward labels."""
    _validate_horizons(horizons_minutes)
    _require_columns(df, [prediction_col])
    _validate_prediction_sides(df[prediction_col], prediction_col)

    rows: list[dict[str, float | int | str]] = []
    n_rows = len(df)
    for horizon in horizons_minutes:
        return_col = f"forward_return_{horizon}m"
        bps_col = f"forward_return_bps_{horizon}m"
        direction_col = f"forward_direction_{horizon}m"
        valid_col = f"label_valid_{horizon}m"
        _require_columns(df, [return_col, bps_col, direction_col, valid_col])

        label_valid = df[valid_col] == True
        valid_predictions = df.loc[label_valid, prediction_col]
        non_neutral = valid_predictions != 0
        prediction_rows = valid_predictions.loc[non_neutral]
        n_label_valid = int(label_valid.sum())
        n_predictions = int(non_neutral.sum())
        n_neutral = int((~non_neutral).sum())

        if n_predictions == 0:
            accuracy = np.nan
            average_forward_return = np.nan
            median_forward_return = np.nan
            average_directional_return = np.nan
            median_directional_return = np.nan
            win_rate_directional_return = np.nan
            profit_factor_equivalent = np.nan
        else:
            actual_direction = df.loc[prediction_rows.index, direction_col]
            correct = prediction_rows == actual_direction
            accuracy = float(correct.sum() / n_predictions)

            forward_return = df.loc[prediction_rows.index, return_col]
            directional_return = prediction_rows * forward_return
            average_forward_return = float(forward_return.mean())
            median_forward_return = float(forward_return.median())
            average_directional_return = float(directional_return.mean())
            median_directional_return = float(directional_return.median())
            win_rate_directional_return = float((directional_return > 0).sum() / n_predictions)
            profit_factor_equivalent = directional_profit_factor_equivalent(
                directional_return
            )

        rows.append(
            {
                "prediction_col": prediction_col,
                "horizon_minutes": horizon,
                "n_rows": n_rows,
                "n_label_valid": n_label_valid,
                "n_predictions": n_predictions,
                "n_neutral": n_neutral,
                "coverage": np.nan if n_label_valid == 0 else n_predictions / n_label_valid,
                "accuracy": accuracy,
                "average_forward_return": average_forward_return,
                "median_forward_return": median_forward_return,
                "average_directional_return": average_directional_return,
                "median_directional_return": median_directional_return,
                "win_rate_directional_return": win_rate_directional_return,
                "profit_factor_equivalent": profit_factor_equivalent,
                "bullish_predictions": int((valid_predictions == 1).sum()),
                "bearish_predictions": int((valid_predictions == -1).sum()),
            }
        )

    return pd.DataFrame(rows)


def evaluate_prediction_columns(
    df: pd.DataFrame,
    prediction_cols: tuple[str, ...],
    horizons_minutes: tuple[int, ...] = (5, 10, 15, 30),
) -> pd.DataFrame:
    """Evaluate multiple prediction columns in the requested order."""
    frames = [
        evaluate_prediction_column(df, prediction_col, horizons_minutes=horizons_minutes)
        for prediction_col in prediction_cols
    ]
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


def find_baseline_prediction_columns(
    df: pd.DataFrame,
    prefix: str = "baseline_",
) -> tuple[str, ...]:
    """Return baseline prediction columns in DataFrame column order."""
    return tuple(column for column in df.columns if column.startswith(prefix))


def evaluate_baselines(
    df: pd.DataFrame,
    horizons_minutes: tuple[int, ...] = (5, 10, 15, 30),
    baseline_prefix: str = "baseline_",
) -> pd.DataFrame:
    """Evaluate all baseline prediction columns found in the DataFrame."""
    baseline_columns = find_baseline_prediction_columns(df, prefix=baseline_prefix)
    if not baseline_columns:
        raise ValueError("No baseline prediction columns found")
    return evaluate_prediction_columns(
        df,
        baseline_columns,
        horizons_minutes=horizons_minutes,
    )


def _require_columns(df: pd.DataFrame, columns: list[str]) -> None:
    missing = [column for column in columns if column not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")


def _validate_horizons(horizons_minutes: tuple[int, ...]) -> None:
    if not isinstance(horizons_minutes, tuple) or not horizons_minutes:
        raise ValueError("horizons_minutes must be a non-empty tuple of integers")
    for horizon in horizons_minutes:
        if not isinstance(horizon, int) or isinstance(horizon, bool) or horizon < 1:
            raise ValueError("horizons_minutes must be a non-empty tuple of integers")


def _validate_prediction_sides(predictions: pd.Series, prediction_col: str) -> None:
    if not predictions.isin([-1, 0, 1]).all():
        raise ValueError(f"{prediction_col} values must be one of -1, 0, or 1")
