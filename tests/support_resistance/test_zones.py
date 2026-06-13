from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from spy_edge_research.support_resistance import (
    add_level_zone,
    add_nearest_standard_zones,
    add_repeated_touch_counts,
    add_standard_level_zones,
    add_support_resistance_features,
    price_to_zone_bounds,
)


def zone_sample() -> pd.DataFrame:
    index = pd.Index(list("abcde"), name="row")
    return pd.DataFrame(
        {
            "close": [100.0, 100.5, 101.5, 99.5, 98.0],
            "high": [100.2, 101.0, 102.0, 100.1, 98.5],
            "low": [99.8, 100.0, 101.0, 99.0, 97.5],
            "level": [100.0, 100.0, np.nan, 100.0, 100.0],
        },
        index=index,
    )


def feature_sample() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "timestamp": [
                pd.Timestamp("2024-01-02 08:00", tz="America/New_York"),
                pd.Timestamp("2024-01-02 09:30", tz="America/New_York"),
                pd.Timestamp("2024-01-02 09:31", tz="America/New_York"),
                pd.Timestamp("2024-01-02 16:00", tz="America/New_York"),
                pd.Timestamp("2024-01-03 08:00", tz="America/New_York"),
                pd.Timestamp("2024-01-03 09:31", tz="America/New_York"),
            ],
            "high": [101.0, 102.0, 103.0, 104.0, 106.0, 107.0],
            "low": [99.0, 98.0, 100.0, 101.0, 104.0, 105.0],
            "close": [100.0, 101.0, 102.0, 103.0, 105.0, 106.0],
        },
        index=pd.Index(list("abcdef"), name="row"),
    )


def test_price_to_zone_bounds_computes_expected_values() -> None:
    lower, upper = price_to_zone_bounds(100.0, width_bps=10.0)
    series_lower, series_upper = price_to_zone_bounds(
        pd.Series([100.0, np.nan], index=["a", "b"]), width_bps=10.0
    )

    assert lower == 99.9
    assert upper == 100.1
    assert series_lower.index.tolist() == ["a", "b"]
    assert series_lower.iloc[0] == 99.9
    assert pd.isna(series_upper.iloc[1])


def test_add_level_zone_creates_zone_and_distance_columns() -> None:
    result = add_level_zone(zone_sample(), "level", "test", width_bps=100)

    expected_columns = {
        "test_zone_center",
        "test_zone_lower",
        "test_zone_upper",
        "test_in_zone",
        "test_distance_to_center",
        "test_distance_to_lower",
        "test_distance_to_upper",
    }
    assert expected_columns.issubset(result.columns)
    assert bool(result.loc["a", "test_in_zone"]) is True
    assert result.loc["b", "test_distance_to_center"] == 0.5


def test_add_level_zone_marks_unavailable_levels_as_not_in_zone() -> None:
    result = add_level_zone(zone_sample(), "level", "test", width_bps=100)

    assert bool(result.loc["c", "test_in_zone"]) is False


def test_add_standard_level_zones_skips_missing_optional_levels() -> None:
    df = zone_sample().rename(columns={"level": "prior_day_high"})

    result = add_standard_level_zones(df, width_bps=100)

    assert "prior_day_high_zone_center" in result.columns
    assert "premarket_high_zone_center" not in result.columns


def test_add_repeated_touch_counts_detects_overlap_and_uses_trailing_count() -> None:
    df = add_level_zone(zone_sample(), "level", "test", width_bps=100)

    result = add_repeated_touch_counts(
        df,
        "test_zone_center",
        "test_zone_lower",
        "test_zone_upper",
        "test",
        lookback=2,
    )

    assert result["test_touch"].tolist() == [True, True, False, True, False]
    assert result["test_touch_count_2"].tolist() == [1.0, 2.0, 1.0, 1.0, 1.0]


def test_add_nearest_standard_zones_finds_support_and_resistance() -> None:
    df = pd.DataFrame(
        {
            "close": [100.0, 100.0],
            "prior_day_low_zone_center": [99.0, np.nan],
            "prior_day_high_zone_center": [103.0, np.nan],
            "premarket_low_zone_center": [98.0, np.nan],
            "premarket_high_zone_center": [101.0, np.nan],
        },
        index=["a", "b"],
    )

    result = add_nearest_standard_zones(df)

    assert result.loc["a", "nearest_support_zone"] == "prior_day_low"
    assert result.loc["a", "nearest_support_zone_distance"] == 1.0
    assert result.loc["a", "nearest_resistance_zone"] == "premarket_high"
    assert result.loc["a", "nearest_resistance_zone_distance"] == 1.0
    assert pd.isna(result.loc["b", "nearest_support_zone"])
    assert pd.isna(result.loc["b", "nearest_resistance_zone"])


def test_add_support_resistance_features_composes_core_features() -> None:
    result = add_support_resistance_features(
        feature_sample(),
        zone_width_bps=10,
        touch_lookback=2,
    )

    expected_columns = {
        "prior_day_high",
        "premarket_high",
        "prior_day_high_zone_center",
        "premarket_high_zone_center",
        "prior_day_high_touch_count_2",
        "nearest_support_zone",
        "nearest_resistance_zone",
    }
    assert expected_columns.issubset(result.columns)
    assert result.index.equals(feature_sample().index)
    assert len(result) == len(feature_sample())


def test_input_dataframes_are_not_mutated_and_index_row_count_are_preserved() -> None:
    df = zone_sample()
    original = df.copy(deep=True)

    result = add_level_zone(df, "level", "test")

    pd.testing.assert_frame_equal(df, original)
    assert result.index.equals(df.index)
    assert len(result) == len(df)


def test_invalid_parameters_raise_value_error() -> None:
    df = zone_sample()

    with pytest.raises(ValueError, match="width_bps"):
        price_to_zone_bounds(100.0, width_bps=0)
    with pytest.raises(ValueError, match="Missing required columns"):
        add_level_zone(df, "missing", "test")
    with pytest.raises(ValueError, match="lookback"):
        add_repeated_touch_counts(
            add_level_zone(df, "level", "test"),
            "test_zone_center",
            "test_zone_lower",
            "test_zone_upper",
            "test",
            lookback=0,
        )
    with pytest.raises(ValueError, match="zone_width_bps"):
        add_support_resistance_features(feature_sample(), zone_width_bps=0)
