from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from spy_edge_research.signal_engine.events import (
    add_basic_event_primitives,
    add_candle_body_features,
    add_crossover_events,
    add_momentum_events,
    add_range_expansion_events,
    add_single_bar_pattern_events,
    add_trailing_break_events,
    add_volume_expansion_events,
    crosses_above,
    crosses_below,
)


def sample_ohlcv() -> pd.DataFrame:
    index = pd.Index(pd.date_range("2024-01-02 09:31", periods=6, freq="1min"), name="ts")
    return pd.DataFrame(
        {
            "timestamp": pd.date_range(
                "2024-01-02 09:31", periods=6, freq="1min", tz="America/New_York"
            ),
            "symbol": ["SPY"] * 6,
            "open": [10.0, 10.5, 10.2, 10.4, 11.8, 10.0],
            "high": [11.0, 11.5, 10.8, 11.0, 12.6, 10.5],
            "low": [9.5, 10.0, 9.8, 10.1, 11.7, 8.5],
            "close": [10.5, 10.2, 10.4, 10.8, 12.2, 9.0],
            "volume": [100, 120, 110, 130, 400, 90],
        },
        index=index,
    )


def test_crosses_above_detects_only_causal_crossings() -> None:
    left = pd.Series([1.0, 2.0, 4.0, 5.0, np.nan, 7.0])
    right = pd.Series([2.0, 2.0, 3.0, 4.0, 4.0, np.nan])

    result = crosses_above(left, right)

    assert result.tolist() == [False, False, True, False, False, False]
    assert result.dtype == bool
    assert result.index.equals(left.index)


def test_crosses_below_detects_only_causal_crossings() -> None:
    left = pd.Series([5.0, 4.0, 2.0, 1.0, np.nan, 0.0])
    right = pd.Series([4.0, 4.0, 3.0, 2.0, 2.0, np.nan])

    result = crosses_below(left, right)

    assert result.tolist() == [False, False, True, False, False, False]
    assert result.dtype == bool
    assert result.index.equals(left.index)


def test_add_crossover_events_adds_columns_without_mutation() -> None:
    df = pd.DataFrame({"close": [1.0, 2.0, 4.0], "vwap": [2.0, 2.0, 3.0]})
    original = df.copy(deep=True)

    result = add_crossover_events(df, "close", "vwap")

    assert "close_cross_vwap_crosses_above" in result.columns
    assert "close_cross_vwap_crosses_below" in result.columns
    assert "close_cross_vwap_crosses_above" not in df.columns
    pd.testing.assert_frame_equal(df, original)


def test_add_crossover_events_requires_columns() -> None:
    with pytest.raises(ValueError, match="Missing required columns"):
        add_crossover_events(pd.DataFrame({"close": [1.0]}), "close", "vwap")


def test_add_trailing_break_events_uses_prior_bars_only() -> None:
    df = sample_ohlcv()
    original = df.copy(deep=True)

    result = add_trailing_break_events(df, lookback=3)

    assert result["trailing_high_3"].iloc[:3].isna().all()
    assert result["trailing_low_3"].iloc[:3].isna().all()
    assert result["breaks_above_trailing_high_3"].iloc[:3].tolist() == [False] * 3
    assert result["breaks_below_trailing_low_3"].iloc[:3].tolist() == [False] * 3
    assert result["trailing_high_3"].iloc[3] == 11.5
    assert result["trailing_low_3"].iloc[3] == 9.5
    assert result["trailing_high_3"].iloc[4] == 11.5
    assert result["trailing_low_3"].iloc[5] == 9.8
    assert bool(result["breaks_above_trailing_high_3"].iloc[4]) is True
    assert bool(result["breaks_below_trailing_low_3"].iloc[5]) is True
    pd.testing.assert_frame_equal(df, original)


def test_add_trailing_break_events_validates_lookback_and_columns() -> None:
    with pytest.raises(ValueError, match="lookback"):
        add_trailing_break_events(sample_ohlcv(), lookback=0)
    with pytest.raises(ValueError, match="Missing required columns"):
        add_trailing_break_events(pd.DataFrame({"close": [1.0]}))


def test_add_candle_body_features_calculates_candle_fields_without_mutation() -> None:
    df = pd.DataFrame(
        {
            "open": [10.0, 10.0, 10.0],
            "high": [12.0, 11.0, 10.5],
            "low": [9.0, 9.0, 9.5],
            "close": [11.0, 9.0, 10.0],
        }
    )
    original = df.copy(deep=True)

    result = add_candle_body_features(df)

    assert result["candle_range"].tolist() == [3.0, 2.0, 1.0]
    assert result["candle_body"].tolist() == [1.0, -1.0, 0.0]
    assert result["candle_body_abs"].tolist() == [1.0, 1.0, 0.0]
    assert result["candle_body_pct_of_range"].tolist() == pytest.approx([1 / 3, 0.5, 0.0])
    assert result["upper_wick"].tolist() == [1.0, 1.0, 0.5]
    assert result["lower_wick"].tolist() == [1.0, 0.0, 0.5]
    assert result["bullish_candle"].tolist() == [True, False, False]
    assert result["bearish_candle"].tolist() == [False, True, False]
    assert result["doji_like_candle"].tolist() == [False, False, True]
    pd.testing.assert_frame_equal(df, original)


def test_add_candle_body_features_handles_zero_range_and_requires_columns() -> None:
    result = add_candle_body_features(
        pd.DataFrame({"open": [10.0], "high": [10.0], "low": [10.0], "close": [10.0]})
    )

    assert pd.isna(result.loc[0, "candle_body_pct_of_range"])
    assert bool(result.loc[0, "doji_like_candle"]) is False
    with pytest.raises(ValueError, match="Missing required columns"):
        add_candle_body_features(pd.DataFrame({"open": [1.0]}))


def test_add_single_bar_pattern_events_uses_only_previous_and_current_bars() -> None:
    df = pd.DataFrame(
        {
            "high": [10.0, 9.0, 11.0, 10.5],
            "low": [5.0, 6.0, 4.0, 4.5],
        }
    )
    original = df.copy(deep=True)

    result = add_single_bar_pattern_events(df)

    assert result["inside_bar"].tolist() == [False, True, False, True]
    assert result["outside_bar"].tolist() == [False, False, True, False]
    pd.testing.assert_frame_equal(df, original)


def test_add_momentum_events_identifies_consecutive_closes_without_mutation() -> None:
    df = pd.DataFrame({"close": [10.0, 11.0, 12.0, 11.0, 10.0, 9.0]})
    original = df.copy(deep=True)

    result = add_momentum_events(df, consecutive_count=3)

    assert result["higher_close"].tolist() == [False, True, True, False, False, False]
    assert result["lower_close"].tolist() == [False, False, False, True, True, True]
    assert result["consecutive_higher_closes_3"].tolist() == [
        False,
        False,
        True,
        False,
        False,
        False,
    ]
    assert result["consecutive_lower_closes_3"].tolist() == [
        False,
        False,
        False,
        False,
        True,
        True,
    ]
    pd.testing.assert_frame_equal(df, original)


def test_add_momentum_events_validates_inputs() -> None:
    with pytest.raises(ValueError, match="consecutive_count"):
        add_momentum_events(pd.DataFrame({"close": [1.0]}), consecutive_count=1)
    with pytest.raises(ValueError, match="Missing required columns"):
        add_momentum_events(pd.DataFrame({"open": [1.0]}))


def test_add_range_expansion_events_uses_prior_ranges_only() -> None:
    df = pd.DataFrame(
        {
            "high": [11.0, 12.0, 13.0, 20.0],
            "low": [10.0, 10.0, 10.0, 10.0],
        }
    )

    result = add_range_expansion_events(df, window=3, multiplier=2.0)

    assert result["candle_range"].tolist() == [1.0, 2.0, 3.0, 10.0]
    assert result["prior_range_sma_3"].iloc[:3].isna().all()
    assert result["prior_range_sma_3"].iloc[3] == 2.0
    assert result["range_expansion_3"].tolist() == [False, False, False, True]


def test_add_range_expansion_events_validates_inputs() -> None:
    with pytest.raises(ValueError, match="window"):
        add_range_expansion_events(sample_ohlcv(), window=0)
    with pytest.raises(ValueError, match="multiplier"):
        add_range_expansion_events(sample_ohlcv(), multiplier=0)
    with pytest.raises(ValueError, match="Missing required columns"):
        add_range_expansion_events(pd.DataFrame({"high": [1.0]}))


def test_add_volume_expansion_events_uses_prior_volume_only() -> None:
    df = pd.DataFrame({"volume": [100, 200, 300, 1000]})

    result = add_volume_expansion_events(df, window=3, multiplier=2.0)

    assert result["prior_volume_sma_3"].iloc[:3].isna().all()
    assert result["prior_volume_sma_3"].iloc[3] == 200.0
    assert result["volume_expansion_3"].tolist() == [False, False, False, True]


def test_add_volume_expansion_events_validates_inputs() -> None:
    with pytest.raises(ValueError, match="window"):
        add_volume_expansion_events(sample_ohlcv(), window=0)
    with pytest.raises(ValueError, match="multiplier"):
        add_volume_expansion_events(sample_ohlcv(), multiplier=0)
    with pytest.raises(ValueError, match="Missing required columns"):
        add_volume_expansion_events(pd.DataFrame({"close": [1.0]}))


def test_add_basic_event_primitives_composes_expected_columns_without_mutation() -> None:
    df = sample_ohlcv()
    original = df.copy(deep=True)

    result = add_basic_event_primitives(
        df,
        trailing_lookback=3,
        consecutive_count=3,
        expansion_window=3,
        expansion_multiplier=2.0,
    )

    expected_columns = {
        "timestamp",
        "symbol",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "trailing_high_3",
        "trailing_low_3",
        "breaks_above_trailing_high_3",
        "breaks_below_trailing_low_3",
        "candle_range",
        "candle_body",
        "candle_body_abs",
        "candle_body_pct_of_range",
        "upper_wick",
        "lower_wick",
        "bullish_candle",
        "bearish_candle",
        "doji_like_candle",
        "inside_bar",
        "outside_bar",
        "higher_close",
        "lower_close",
        "consecutive_higher_closes_3",
        "consecutive_lower_closes_3",
        "prior_range_sma_3",
        "range_expansion_3",
        "prior_volume_sma_3",
        "volume_expansion_3",
    }
    assert expected_columns.issubset(result.columns)
    assert len(result) == len(df)
    assert result.index.equals(df.index)
    for column in ["timestamp", "symbol", "open", "high", "low", "close", "volume"]:
        assert column in result.columns
    pd.testing.assert_frame_equal(df, original)
