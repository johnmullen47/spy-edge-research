"""Simple benchmark directional prediction baselines.

These helpers create benchmark prediction columns from causal columns already
present in the input data. They are not trading signals or edge claims.
"""

from __future__ import annotations

from numbers import Real

import numpy as np
import pandas as pd

from spy_edge_research._internal._common import (
    require_columns as _require_columns,
    validate_positive_int as _validate_positive_int,
)


def add_always_long_baseline(
    df: pd.DataFrame,
    column_name: str = "baseline_always_long",
) -> pd.DataFrame:
    """Add a benchmark column that always predicts bullish direction."""
    result = df.copy()
    result[column_name] = 1
    return result


def add_always_short_baseline(
    df: pd.DataFrame,
    column_name: str = "baseline_always_short",
) -> pd.DataFrame:
    """Add a benchmark column that always predicts bearish direction."""
    result = df.copy()
    result[column_name] = -1
    return result


def add_random_direction_baseline(
    df: pd.DataFrame,
    column_name: str = "baseline_random_direction",
    seed: int = 42,
    neutral_probability: float = 0.0,
) -> pd.DataFrame:
    """Add a deterministic random benchmark direction column."""
    _validate_probability(neutral_probability, "neutral_probability")

    result = df.copy()
    rng = np.random.default_rng(seed)
    if neutral_probability == 0.0:
        result[column_name] = rng.choice([-1, 1], size=len(result))
    else:
        side_probability = (1.0 - neutral_probability) / 2.0
        result[column_name] = rng.choice(
            [-1, 0, 1],
            size=len(result),
            p=[side_probability, neutral_probability, side_probability],
        )
    return result


def add_vwap_relation_baseline(
    df: pd.DataFrame,
    price_col: str = "close",
    vwap_col: str = "vwap",
    column_name: str = "baseline_vwap_relation",
) -> pd.DataFrame:
    """Add a simple price-versus-VWAP benchmark prediction column."""
    _require_columns(df, [price_col, vwap_col])

    result = df.copy()
    result[column_name] = _side_from_relation(result[price_col], result[vwap_col])
    return result


def add_ema_relation_baseline(
    df: pd.DataFrame,
    price_col: str = "close",
    ema_col: str = "ema_9",
    column_name: str = "baseline_ema_relation",
) -> pd.DataFrame:
    """Add a simple price-versus-EMA benchmark prediction column."""
    _require_columns(df, [price_col, ema_col])

    result = df.copy()
    result[column_name] = _side_from_relation(result[price_col], result[ema_col])
    return result


def add_trailing_break_baseline(
    df: pd.DataFrame,
    lookback: int = 20,
    column_name: str = "baseline_trailing_break",
) -> pd.DataFrame:
    """Add a benchmark prediction from trailing high/low break primitives."""
    _validate_positive_int(lookback, "lookback")
    break_above_col = f"breaks_above_trailing_high_{lookback}"
    break_below_col = f"breaks_below_trailing_low_{lookback}"
    _require_columns(df, [break_above_col, break_below_col])

    result = df.copy()
    break_above = result[break_above_col].fillna(False).astype(bool)
    break_below = result[break_below_col].fillna(False).astype(bool)
    result[column_name] = np.select(
        [break_above & ~break_below, break_below & ~break_above],
        [1, -1],
        default=0,
    )
    return result


def add_basic_baselines(
    df: pd.DataFrame,
    include_random: bool = True,
    random_seed: int = 42,
    neutral_probability: float = 0.0,
    include_vwap: bool = True,
    include_ema: bool = True,
    include_trailing_break: bool = True,
    trailing_lookback: int = 20,
) -> pd.DataFrame:
    """Compose the basic benchmark prediction columns that can be supported."""
    result = add_always_long_baseline(df)
    result = add_always_short_baseline(result)

    if include_random:
        result = add_random_direction_baseline(
            result,
            seed=random_seed,
            neutral_probability=neutral_probability,
        )
    if include_vwap and _has_columns(result, ["close", "vwap"]):
        result = add_vwap_relation_baseline(result)
    if include_ema and _has_columns(result, ["close", "ema_9"]):
        result = add_ema_relation_baseline(result)
    if include_trailing_break:
        break_columns = [
            f"breaks_above_trailing_high_{trailing_lookback}",
            f"breaks_below_trailing_low_{trailing_lookback}",
        ]
        if _has_columns(result, break_columns):
            result = add_trailing_break_baseline(result, lookback=trailing_lookback)
    return result


def _has_columns(df: pd.DataFrame, columns: list[str]) -> bool:
    return all(column in df.columns for column in columns)


def _validate_probability(value: float, name: str) -> None:
    if not isinstance(value, Real) or isinstance(value, bool) or not 0 <= value < 1:
        raise ValueError(f"{name} must satisfy 0 <= {name} < 1")


def _side_from_relation(left: pd.Series, right: pd.Series) -> pd.Series:
    values = np.select([left > right, left < right], [1, -1], default=0)
    return pd.Series(values, index=left.index, dtype="int64")
