from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from spy_edge_research.market_structure import (
    add_break_retest_events,
    add_retest_count_features,
    add_retest_features,
    add_standard_zone_retest_events,
    add_zone_retest_events,
    price_to_retest_zone_bounds,
)


def test_price_to_retest_zone_bounds_preserves_index_and_validates_tolerance() -> None:
    price = pd.Series([100.0, np.nan], index=pd.Index(["a", "b"], name="row"))

    lower, upper = price_to_retest_zone_bounds(price, tolerance_bps=10.0)

    assert isinstance(lower, pd.Series)
    assert isinstance(upper, pd.Series)
    assert lower.index.equals(price.index)
    assert upper.index.equals(price.index)
    assert lower.iloc[0] == pytest.approx(99.9)
    assert upper.iloc[0] == pytest.approx(100.1)
    assert np.isnan(lower.iloc[1])
    assert np.isnan(upper.iloc[1])

    scalar_lower, scalar_upper = price_to_retest_zone_bounds(200.0, tolerance_bps=5.0)
    assert scalar_lower == pytest.approx(199.9)
    assert scalar_upper == pytest.approx(200.1)

    with pytest.raises(ValueError, match="tolerance_bps"):
        price_to_retest_zone_bounds(price, tolerance_bps=0)


def _zone_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "close": [101.0, 99.0, 100.0, 102.0, 100.0],
            "high": [101.0, 100.0, 100.2, 102.0, 100.2],
            "low": [100.0, 99.0, 99.8, 101.0, 99.8],
            "test_zone_center": [100.0, 100.0, 100.0, 100.0, np.nan],
            "test_zone_lower": [99.5, 99.5, 99.5, 99.5, np.nan],
            "test_zone_upper": [100.5, 100.5, 100.5, 100.5, np.nan],
        },
        index=pd.Index(list("abcde"), name="row"),
    )


def test_add_zone_retest_events_detects_support_and_resistance_cases() -> None:
    df = _zone_frame()
    original = df.copy(deep=True)

    support = add_zone_retest_events(df, "test", "support")
    resistance = add_zone_retest_events(df, "test", "resistance")

    assert support["test_support_retest_touch"].tolist() == [True, True, True, False, False]
    assert support["test_support_retest_hold"].tolist() == [True, False, False, False, False]
    assert support["test_support_retest_failure"].tolist() == [False, True, False, False, False]
    assert resistance["test_resistance_retest_touch"].tolist() == [
        True,
        True,
        True,
        False,
        False,
    ]
    assert resistance["test_resistance_retest_hold"].tolist() == [
        False,
        True,
        False,
        False,
        False,
    ]
    assert resistance["test_resistance_retest_failure"].tolist() == [
        True,
        False,
        False,
        False,
        False,
    ]
    assert support.index.equals(df.index)
    assert len(support) == len(df)
    pd.testing.assert_frame_equal(df, original)

    with pytest.raises(ValueError, match="zone_type"):
        add_zone_retest_events(df, "test", "middle")
    with pytest.raises(ValueError, match="Missing required columns"):
        add_zone_retest_events(df.drop(columns=["test_zone_lower"]), "test", "support")


def test_add_standard_zone_retest_events_adds_available_standard_zones() -> None:
    df = pd.DataFrame(
        {
            "close": [101.0, 99.0],
            "high": [101.0, 100.0],
            "low": [100.0, 99.0],
            "prior_day_high_zone_center": [100.0, 100.0],
            "prior_day_high_zone_lower": [99.5, 99.5],
            "prior_day_high_zone_upper": [100.5, 100.5],
            "prior_day_close_zone_center": [100.0, 100.0],
            "prior_day_close_zone_lower": [99.5, 99.5],
            "prior_day_close_zone_upper": [100.5, 100.5],
        },
        index=pd.Index(["x", "y"]),
    )
    original = df.copy(deep=True)

    result = add_standard_zone_retest_events(df)

    assert "prior_day_high_resistance_retest_touch" in result.columns
    assert "prior_day_close_support_retest_touch" in result.columns
    assert "prior_day_close_resistance_retest_touch" in result.columns
    assert "premarket_high_resistance_retest_touch" not in result.columns
    assert result.index.equals(df.index)
    assert len(result) == len(df)
    pd.testing.assert_frame_equal(df, original)


def test_add_retest_count_features_counts_trailing_events_and_validates_inputs() -> None:
    df = pd.DataFrame(
        {
            "zone_support_retest_touch": [True, True, False, True],
            "zone_support_retest_hold": [False, True, False, True],
            "zone_support_retest_failure": [False, False, True, False],
        },
        index=pd.Index(list("abcd")),
    )
    original = df.copy(deep=True)

    result = add_retest_count_features(df, "zone_support", lookback=2)

    assert result["zone_support_retest_touch_count_2"].tolist() == pytest.approx(
        [1.0, 2.0, 1.0, 1.0]
    )
    assert result["zone_support_retest_hold_count_2"].tolist() == pytest.approx(
        [0.0, 1.0, 1.0, 1.0]
    )
    assert result["zone_support_retest_failure_count_2"].tolist() == pytest.approx(
        [0.0, 0.0, 1.0, 1.0]
    )
    assert result.index.equals(df.index)
    pd.testing.assert_frame_equal(df, original)

    with pytest.raises(ValueError, match="lookback"):
        add_retest_count_features(df, "zone_support", lookback=0)
    with pytest.raises(ValueError, match="Missing required columns"):
        add_retest_count_features(df.drop(columns=["zone_support_retest_hold"]), "zone_support")


def _break_retest_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "close": [99.0, 101.0, 100.2, 99.8, 89.0, 89.8, 90.2, 91.0],
            "high": [99.5, 101.5, 100.05, 100.05, 90.0, 90.05, 90.05, 91.5],
            "low": [98.5, 100.8, 99.95, 99.95, 88.5, 89.95, 89.95, 90.8],
            "trailing_high_3": [np.nan, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0],
            "trailing_low_3": [np.nan, 90.0, 90.0, 90.0, 90.0, 90.0, 90.0, 90.0],
            "breaks_above_trailing_high_3": [
                False,
                True,
                False,
                False,
                False,
                False,
                False,
                False,
            ],
            "breaks_below_trailing_low_3": [
                False,
                False,
                False,
                False,
                True,
                False,
                False,
                False,
            ],
        },
        index=pd.Index(pd.date_range("2024-01-02 09:31", periods=8, freq="1min"), name="ts"),
    )


def test_add_break_retest_events_tracks_levels_expires_and_emits_current_row_events() -> None:
    df = _break_retest_frame()
    original = df.copy(deep=True)

    result = add_break_retest_events(df, lookback=3, max_bars_after_break=2, tolerance_bps=10)

    pd.testing.assert_series_equal(
        result["active_breakout_retest_level_3"].iloc[:5],
        pd.Series([np.nan, 100.0, 100.0, 100.0, np.nan], index=df.index[:5], name="active_breakout_retest_level_3"),
    )
    pd.testing.assert_series_equal(
        result["bars_since_breakout_3"].iloc[:5],
        pd.Series([np.nan, 0.0, 1.0, 2.0, np.nan], index=df.index[:5], name="bars_since_breakout_3"),
    )
    assert result["breakout_retest_touch_3"].tolist()[:5] == [
        False,
        False,
        True,
        True,
        False,
    ]
    assert result["breakout_retest_hold_3"].tolist()[:5] == [
        False,
        False,
        True,
        False,
        False,
    ]
    assert result["breakout_retest_failure_3"].tolist()[:5] == [
        False,
        False,
        False,
        True,
        False,
    ]

    pd.testing.assert_series_equal(
        result["active_breakdown_retest_level_3"].iloc[4:],
        pd.Series([90.0, 90.0, 90.0, np.nan], index=df.index[4:], name="active_breakdown_retest_level_3"),
    )
    pd.testing.assert_series_equal(
        result["bars_since_breakdown_3"].iloc[4:],
        pd.Series([0.0, 1.0, 2.0, np.nan], index=df.index[4:], name="bars_since_breakdown_3"),
    )
    assert result["breakdown_retest_touch_3"].tolist()[4:] == [False, True, True, False]
    assert result["breakdown_retest_hold_3"].tolist()[4:] == [False, True, False, False]
    assert result["breakdown_retest_failure_3"].tolist()[4:] == [False, False, True, False]
    assert result.index.equals(df.index)
    assert len(result) == len(df)
    pd.testing.assert_frame_equal(df, original)

    with pytest.raises(ValueError, match="Missing required columns"):
        add_break_retest_events(df.drop(columns=["trailing_high_3"]), lookback=3)
    with pytest.raises(ValueError, match="lookback"):
        add_break_retest_events(df, lookback=0)
    with pytest.raises(ValueError, match="max_bars_after_break"):
        add_break_retest_events(df, lookback=3, max_bars_after_break=0)
    with pytest.raises(ValueError, match="tolerance_bps"):
        add_break_retest_events(df, lookback=3, tolerance_bps=0)


def test_add_retest_features_composes_available_features_and_skips_missing_optionals() -> None:
    df = _break_retest_frame().assign(
        prior_day_low_zone_center=100.0,
        prior_day_low_zone_lower=99.5,
        prior_day_low_zone_upper=100.5,
    )
    original = df.copy(deep=True)

    result = add_retest_features(
        df,
        trailing_lookback=3,
        max_bars_after_break=2,
        count_lookback=3,
    )

    assert "prior_day_low_support_retest_touch" in result.columns
    assert "prior_day_low_support_retest_touch_count_3" in result.columns
    assert "breakout_retest_touch_3" in result.columns
    assert "premarket_low_support_retest_touch" not in result.columns
    for column in original.columns:
        assert column in result.columns
    assert result.index.equals(df.index)
    assert len(result) == len(df)
    pd.testing.assert_frame_equal(df, original)

    minimal = df[["close", "high", "low"]].copy()
    minimal_result = add_retest_features(minimal)
    assert list(minimal_result.columns) == ["close", "high", "low"]
