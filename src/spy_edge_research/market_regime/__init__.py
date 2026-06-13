"""Causal market-regime feature and classification helpers."""

from spy_edge_research.market_regime.regime_classifier import (
    HIGH_VOLATILITY,
    LOW_VOLATILITY,
    NORMAL_VOLATILITY,
    RANGE_BOUND,
    TRENDING_DOWN,
    TRENDING_UP,
    UNKNOWN_DIRECTIONAL_REGIME,
    UNKNOWN_VOLATILITY_REGIME,
    add_market_regime_classification,
    add_market_regime_features,
    classify_directional_regime,
    classify_volatility_regime,
)
from spy_edge_research.market_regime.regime_diagnostics import (
    regime_duration_summary,
    regime_transition_counts,
    regime_value_counts,
)
from spy_edge_research.market_regime.regime_features import (
    add_ema_regime_features,
    add_intraday_range_features,
    add_regime_features,
    add_structure_regime_features,
    add_volume_regime_features,
    add_vwap_cross_count_feature,
    add_vwap_regime_features,
)

__all__ = [
    "HIGH_VOLATILITY",
    "LOW_VOLATILITY",
    "NORMAL_VOLATILITY",
    "RANGE_BOUND",
    "TRENDING_DOWN",
    "TRENDING_UP",
    "UNKNOWN_DIRECTIONAL_REGIME",
    "UNKNOWN_VOLATILITY_REGIME",
    "add_ema_regime_features",
    "add_intraday_range_features",
    "add_market_regime_classification",
    "add_market_regime_features",
    "add_regime_features",
    "add_structure_regime_features",
    "add_volume_regime_features",
    "add_vwap_cross_count_feature",
    "add_vwap_regime_features",
    "classify_directional_regime",
    "classify_volatility_regime",
    "regime_duration_summary",
    "regime_transition_counts",
    "regime_value_counts",
]
