from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from spy_edge_research.market_regime import (
    add_ema_regime_features,
    add_intraday_range_features,
    add_regime_features,
    add_structure_regime_features,
    add_volume_regime_features,
    add_vwap_cross_count_feature,
    add_vwap_regime_features,
)


def test_vwap_regime_features_identify_relation_slope_and_nan_values() -> None:
    df = pd.DataFrame(
        {
            "close": [11.0, 9.0, np.nan, 10.0],
            "vwap": [10.0, 10.0, 10.0, np.nan],
            "vwap_slope": [0.2, -0.1, np.nan, 0.0],
        }
    )
    original = df.copy(deep=True)

    result = add_vwap_regime_features(df)

    assert result["above_vwap"].tolist() == [True, False, False, False]
    assert result["below_vwap"].tolist() == [False, True, False, False]
    assert result["vwap_slope_positive"].tolist() == [True, False, False, False]
    assert result["vwap_slope_negative"].tolist() == [False, True, False, False]
    assert result["vwap_distance_abs"].iloc[:2].tolist() == pytest.approx([1.0, 1.0])
    pd.testing.assert_frame_equal(df, original)


def test_ema_regime_features_identify_relation_slope_and_nan_values() -> None:
    df = pd.DataFrame(
        {
            "close": [11.0, 9.0, np.nan, 10.0],
            "ema_9": [10.0, 10.0, 10.0, np.nan],
            "ema_9_slope": [0.2, -0.1, np.nan, 0.0],
        }
    )
    original = df.copy(deep=True)

    result = add_ema_regime_features(df)

    assert result["above_ema"].tolist() == [True, False, False, False]
    assert result["below_ema"].tolist() == [False, True, False, False]
    assert result["ema_slope_positive"].tolist() == [True, False, False, False]
    assert result["ema_slope_negative"].tolist() == [False, True, False, False]
    assert result["ema_distance_abs"].iloc[:2].tolist() == pytest.approx([1.0, 1.0])
    pd.testing.assert_frame_equal(df, original)


def test_vwap_cross_count_is_trailing_and_validates_window() -> None:
    df = pd.DataFrame({"close": [9.0, 11.0, 12.0, 8.0, 7.0], "vwap": [10.0] * 5})
    original = df.copy(deep=True)

    result = add_vwap_cross_count_feature(df, window=3)

    assert result["vwap_cross"].tolist() == [False, True, False, True, False]
    assert result["vwap_cross_count_3"].tolist() == pytest.approx([0.0, 1.0, 1.0, 2.0, 1.0])
    truncated = add_vwap_cross_count_feature(df.iloc[:4], window=3)
    pd.testing.assert_series_equal(result["vwap_cross_count_3"].iloc[:4], truncated["vwap_cross_count_3"])
    pd.testing.assert_frame_equal(df, original)

    with pytest.raises(ValueError, match="window"):
        add_vwap_cross_count_feature(df, window=0)


def test_intraday_range_features_are_cumulative_by_local_date() -> None:
    df = pd.DataFrame(
        {
            "timestamp": pd.to_datetime(
                [
                    "2024-01-02 09:31",
                    "2024-01-02 09:32",
                    "2024-01-02 09:33",
                    "2024-01-03 09:31",
                    "2024-01-03 09:32",
                ]
            ).tz_localize("America/New_York"),
            "high": [10.0, 12.0, 15.0, 20.0, 19.0],
            "low": [10.0, 9.0, 8.0, 18.0, 17.0],
            "close": [10.0, 10.5, 11.5, 19.0, 18.0],
        },
        index=pd.Index(["a", "b", "c", "d", "e"], name="row"),
    )
    original = df.copy(deep=True)

    result = add_intraday_range_features(df)

    assert result["intraday_high_so_far"].tolist() == pytest.approx([10.0, 12.0, 15.0, 20.0, 20.0])
    assert result["intraday_low_so_far"].tolist() == pytest.approx([10.0, 9.0, 8.0, 18.0, 17.0])
    assert result["intraday_range_so_far"].tolist() == pytest.approx([0.0, 3.0, 7.0, 2.0, 3.0])
    assert np.isnan(result.loc["a", "close_position_in_intraday_range"])
    assert result.loc["b", "close_position_in_intraday_range"] == pytest.approx(0.5)
    truncated = add_intraday_range_features(df.iloc[:2])
    pd.testing.assert_series_equal(result["intraday_high_so_far"].iloc[:2], truncated["intraday_high_so_far"])
    pd.testing.assert_frame_equal(df, original)


def test_volume_regime_features_identify_thresholds_and_nan_values() -> None:
    df = pd.DataFrame(
        {
            "relative_volume_20": [1.6, 0.7, np.nan, 1.0],
            "volume_zscore_20": [1.2, -1.2, np.nan, 0.0],
        }
    )

    result = add_volume_regime_features(df)

    assert result["relative_volume_available"].tolist() == [True, True, False, True]
    assert result["volume_zscore_available"].tolist() == [True, True, False, True]
    assert result["high_relative_volume"].tolist() == [True, False, False, False]
    assert result["low_relative_volume"].tolist() == [False, True, False, False]
    assert result["positive_volume_zscore"].tolist() == [True, False, False, False]
    assert result["negative_volume_zscore"].tolist() == [False, True, False, False]


def test_structure_regime_features_map_state_and_breaks() -> None:
    df = pd.DataFrame(
        {
            "structure_state": ["bullish", "down", "neutral", None],
            "bullish_structure_break": [1, 0, np.nan, True],
            "bearish_structure_break": [0, 1, np.nan, False],
        }
    )

    result = add_structure_regime_features(df)

    assert result["structure_bullish"].tolist() == [True, False, False, False]
    assert result["structure_bearish"].tolist() == [False, True, False, False]
    assert result["structure_range_or_unknown"].tolist() == [False, False, True, True]
    assert result["recent_bullish_structure_break"].tolist() == [True, False, False, True]
    assert result["recent_bearish_structure_break"].tolist() == [False, True, False, False]


def test_add_regime_features_composes_available_groups_and_preserves_shape() -> None:
    df = pd.DataFrame(
        {
            "timestamp": pd.date_range("2024-01-02 09:31", periods=3, freq="1min"),
            "high": [11.0, 12.0, 13.0],
            "low": [9.0, 9.5, 10.0],
            "close": [10.0, 11.0, 12.0],
            "vwap": [10.0, 10.5, 11.5],
        },
        index=pd.Index(["x", "y", "z"]),
    )
    original = df.copy(deep=True)

    result = add_regime_features(df, vwap_cross_window=2)

    assert "intraday_high_so_far" in result.columns
    assert "vwap_cross_count_2" in result.columns
    assert "above_vwap" not in result.columns
    for column in original.columns:
        assert column in result.columns
    assert result.index.equals(df.index)
    assert len(result) == len(df)
    pd.testing.assert_frame_equal(df, original)
