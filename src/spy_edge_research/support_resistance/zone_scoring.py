"""Simple support/resistance zone scoring primitives.

Scores are reusable feature values only. They are not trading signals or edge
claims.
"""

from __future__ import annotations

from numbers import Real

import numpy as np
import pandas as pd


DEFAULT_WEIGHTS: dict[str, float] = {
    "source_quality": 0.30,
    "recency_score": 0.20,
    "touch_score": 0.20,
    "rejection_score": 0.15,
    "volume_score": 0.10,
    "confluence_score": 0.05,
}


def score_level_recency(
    bars_since_level: pd.Series,
    max_bars: int = 390,
) -> pd.Series:
    """Score level recency from 0 to 1, where newer levels score higher."""
    _validate_positive_int(max_bars, "max_bars")
    values = pd.to_numeric(bars_since_level, errors="coerce")
    return (1 - values.div(max_bars).clip(lower=0, upper=1)).fillna(0)


def score_touch_count(
    touch_count: pd.Series,
    max_touches: int = 5,
) -> pd.Series:
    """Score touch count from 0 to 1, clipped at ``max_touches``."""
    _validate_positive_int(max_touches, "max_touches")
    values = pd.to_numeric(touch_count, errors="coerce")
    return values.div(max_touches).clip(lower=0, upper=1).fillna(0)


def score_rejection_strength(
    rejection_strength: pd.Series,
    max_strength: float,
) -> pd.Series:
    """Score rejection strength from 0 to 1."""
    _validate_positive_number(max_strength, "max_strength")
    values = pd.to_numeric(rejection_strength, errors="coerce")
    return values.div(max_strength).clip(lower=0, upper=1).fillna(0)


def combine_zone_scores(
    source_quality: pd.Series | float,
    recency_score: pd.Series | float,
    touch_score: pd.Series | float,
    rejection_score: pd.Series | float,
    volume_score: pd.Series | float = 0.0,
    confluence_score: pd.Series | float = 0.0,
    violation_penalty: pd.Series | float = 0.0,
    weights: dict[str, float] | None = None,
) -> pd.Series:
    """Combine clipped component scores into a 0-100 zone feature score."""
    score_weights = DEFAULT_WEIGHTS if weights is None else weights
    _validate_weights(score_weights)

    index = _first_series_index(
        source_quality,
        recency_score,
        touch_score,
        rejection_score,
        volume_score,
        confluence_score,
        violation_penalty,
    )
    components = {
        "source_quality": _as_clipped_series(source_quality, index),
        "recency_score": _as_clipped_series(recency_score, index),
        "touch_score": _as_clipped_series(touch_score, index),
        "rejection_score": _as_clipped_series(rejection_score, index),
        "volume_score": _as_clipped_series(volume_score, index),
        "confluence_score": _as_clipped_series(confluence_score, index),
    }
    penalty = _as_clipped_series(violation_penalty, index)

    weighted = sum(
        components[name] * weight for name, weight in score_weights.items()
    ) - penalty
    return (weighted * 100).clip(lower=0, upper=100)


def _first_series_index(*values: pd.Series | float) -> pd.Index:
    for value in values:
        if isinstance(value, pd.Series):
            return value.index
    return pd.RangeIndex(1)


def _as_clipped_series(value: pd.Series | float, index: pd.Index) -> pd.Series:
    if isinstance(value, pd.Series):
        series = pd.to_numeric(value.reindex(index), errors="coerce")
    else:
        series = pd.Series(value, index=index)
    return series.clip(lower=0, upper=1).fillna(0)


def _validate_weights(weights: dict[str, float]) -> None:
    required_keys = set(DEFAULT_WEIGHTS)
    if set(weights) != required_keys:
        raise ValueError(f"weights must contain exactly these keys: {sorted(required_keys)}")
    if any(not isinstance(value, Real) or isinstance(value, bool) for value in weights.values()):
        raise ValueError("weights must be numeric")
    if any(value < 0 for value in weights.values()):
        raise ValueError("weights must be non-negative")
    if not np.isclose(sum(weights.values()), 1.0):
        raise ValueError("weights must sum to approximately 1.0")


def _validate_positive_int(value: int, name: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise ValueError(f"{name} must be an integer greater than or equal to 1")


def _validate_positive_number(value: float, name: str) -> None:
    if not isinstance(value, Real) or isinstance(value, bool) or value <= 0:
        raise ValueError(f"{name} must be greater than 0")
