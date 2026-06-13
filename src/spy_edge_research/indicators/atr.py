"""Average True Range calculations."""

from __future__ import annotations

import pandas as pd


def calculate_atr(
    df: pd.DataFrame,
    window: int = 14,
) -> pd.DataFrame:
    """Add true range and ATR using a simple trailing mean, not Wilder smoothing."""
    _validate_positive_int(window, "window")
    _require_columns(df, ["high", "low", "close"])

    result = df.copy()
    result["true_range"] = _true_range(result)
    result[f"atr_{window}"] = result["true_range"].rolling(window).mean()
    result[f"atr_{window}_pct"] = result[f"atr_{window}"].div(result["close"])
    return result


def _true_range(df: pd.DataFrame) -> pd.Series:
    previous_close = df["close"].shift(1)
    ranges = pd.concat(
        [
            df["high"] - df["low"],
            (df["high"] - previous_close).abs(),
            (df["low"] - previous_close).abs(),
        ],
        axis=1,
    )
    return ranges.max(axis=1)


def _require_columns(df: pd.DataFrame, columns: list[str]) -> None:
    missing = [column for column in columns if column not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")


def _validate_positive_int(value: int, name: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise ValueError(f"{name} must be an integer greater than or equal to 1")
