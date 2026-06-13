from __future__ import annotations

import pandas as pd
import pytest

from spy_edge_research.market_regime import (
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


def _directional_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "above_vwap": [True, False, True, True, True],
            "vwap_slope_positive": [True, False, False, True, True],
            "above_ema": [True, False, True, True, True],
            "ema_slope_positive": [True, False, False, True, True],
            "structure_bullish": [True, False, False, True, True],
            "below_vwap": [False, True, True, False, False],
            "vwap_slope_negative": [False, True, False, False, False],
            "below_ema": [False, True, False, False, False],
            "ema_slope_negative": [False, True, False, False, False],
            "structure_bearish": [False, True, False, False, False],
            "close_position_in_intraday_range": [0.9, 0.1, 0.5, 0.9, 0.9],
            "vwap_cross_count_20": [0.0, 0.0, 0.0, 8.0, 0.0],
            "adx_14": [25.0, 25.0, 25.0, 25.0, 10.0],
        }
    )


def test_directional_regime_classifies_bullish_bearish_mixed_and_crossing() -> None:
    df = _directional_frame()
    original = df.copy(deep=True)

    result = classify_directional_regime(df)

    assert result.tolist() == [
        TRENDING_UP,
        TRENDING_DOWN,
        RANGE_BOUND,
        RANGE_BOUND,
        TRENDING_UP,
    ]
    pd.testing.assert_frame_equal(df, original)


def test_directional_regime_returns_unknown_when_too_few_features() -> None:
    df = pd.DataFrame({"above_vwap": [True], "below_vwap": [False]})

    result = classify_directional_regime(df)

    assert result.iloc[0] == UNKNOWN_DIRECTIONAL_REGIME


def test_volatility_regime_uses_explicit_thresholds() -> None:
    df = pd.DataFrame({"atr_14_pct": [0.02, 0.01, 0.005, None]})
    original = df.copy(deep=True)

    result = classify_volatility_regime(
        df,
        high_atr_pct_threshold=0.015,
        low_atr_pct_threshold=0.007,
    )

    assert result.tolist() == [
        HIGH_VOLATILITY,
        NORMAL_VOLATILITY,
        LOW_VOLATILITY,
        UNKNOWN_VOLATILITY_REGIME,
    ]
    pd.testing.assert_frame_equal(df, original)


def test_volatility_regime_dynamic_thresholds_use_prior_rows_only() -> None:
    df = pd.DataFrame({"atr_14_pct": [1.0, 1.0, 1.0, 2.0, 0.5]})

    result = classify_volatility_regime(df, bb_width_window=3)

    assert result.tolist() == [
        UNKNOWN_VOLATILITY_REGIME,
        UNKNOWN_VOLATILITY_REGIME,
        UNKNOWN_VOLATILITY_REGIME,
        HIGH_VOLATILITY,
        LOW_VOLATILITY,
    ]


def test_volatility_regime_returns_unknown_without_usable_data_and_validates_window() -> None:
    df = pd.DataFrame({"close": [1.0, 2.0]})

    result = classify_volatility_regime(df, bb_width_window=2)

    assert result.tolist() == [UNKNOWN_VOLATILITY_REGIME, UNKNOWN_VOLATILITY_REGIME]
    with pytest.raises(ValueError, match="bb_width_window"):
        classify_volatility_regime(df, bb_width_window=1)


def test_add_market_regime_classification_adds_regime_columns() -> None:
    df = _directional_frame().assign(atr_14_pct=[0.02, 0.01, 0.005, None, 0.02])
    original = df.copy(deep=True)

    result = add_market_regime_classification(
        df,
        high_atr_pct_threshold=0.015,
        low_atr_pct_threshold=0.007,
    )

    assert ["directional_regime", "volatility_regime", "market_regime"] == result.columns[-3:].tolist()
    assert result.loc[0, "market_regime"] == f"{TRENDING_UP} / {HIGH_VOLATILITY}"
    assert result.index.equals(df.index)
    assert len(result) == len(df)
    pd.testing.assert_frame_equal(df, original)


def test_add_market_regime_features_composes_features_and_classification() -> None:
    df = pd.DataFrame(
        {
            "timestamp": pd.date_range("2024-01-02 09:31", periods=3, freq="1min"),
            "high": [11.0, 12.0, 13.0],
            "low": [9.0, 9.0, 9.0],
            "close": [10.5, 11.5, 12.5],
            "vwap": [10.0, 10.5, 11.0],
            "vwap_slope": [0.1, 0.2, 0.3],
            "ema_9": [10.0, 10.5, 11.0],
            "ema_9_slope": [0.1, 0.1, 0.1],
            "adx_14": [25.0, 25.0, 25.0],
            "atr_14_pct": [0.02, 0.02, 0.02],
        },
        index=pd.Index(["a", "b", "c"]),
    )
    original = df.copy(deep=True)

    result = add_market_regime_features(
        df,
        high_atr_pct_threshold=0.015,
        low_atr_pct_threshold=0.007,
    )

    assert "above_vwap" in result.columns
    assert "directional_regime" in result.columns
    assert "market_regime" in result.columns
    for column in original.columns:
        assert column in result.columns
    assert result.index.equals(df.index)
    assert len(result) == len(df)
    pd.testing.assert_frame_equal(df, original)
