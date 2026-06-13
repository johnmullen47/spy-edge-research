from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from spy_edge_research.signal_engine import (
    add_false_break_named_events,
    add_momentum_volume_named_events,
    add_named_event_features,
    add_retest_named_events,
    add_standard_zone_break_named_events,
    add_structure_named_events,
    add_trailing_break_named_events,
    add_trend_continuation_named_events,
    add_vwap_named_events,
    find_named_event_columns,
)


def _index(length: int = 5) -> pd.Index:
    return pd.Index(pd.date_range("2024-01-02 09:31", periods=length, freq="1min"), name="ts")


def test_add_vwap_named_events_detects_events_and_preserves_input() -> None:
    df = pd.DataFrame(
        {
            "close": [99.0, 101.0, 99.0, 99.0, 101.0, 101.0, np.nan],
            "high": [99.5, 101.5, 100.5, 100.0, 101.2, 101.3, 102.0],
            "low": [98.5, 99.5, 98.8, 98.9, 99.5, 99.5, 100.0],
            "vwap": [100.0] * 7,
        },
        index=_index(7),
    )
    original = df.copy(deep=True)

    result = add_vwap_named_events(df)

    assert result["event_vwap_reclaim_bullish"].tolist() == [
        False,
        True,
        False,
        False,
        True,
        False,
        False,
    ]
    assert result["event_vwap_loss_bearish"].tolist() == [
        False,
        False,
        True,
        False,
        False,
        False,
        False,
    ]
    assert result["event_vwap_rejection_bearish"].tolist() == [
        False,
        False,
        False,
        True,
        False,
        False,
        False,
    ]
    assert result["event_vwap_bounce_bullish"].tolist() == [
        False,
        False,
        False,
        False,
        False,
        True,
        False,
    ]
    assert result["event_vwap_reclaim_bullish"].dtype == bool
    assert result.index.equals(df.index)
    assert len(result) == len(df)
    pd.testing.assert_frame_equal(df, original)

    with pytest.raises(ValueError, match="Missing required columns"):
        add_vwap_named_events(df.drop(columns=["vwap"]))


def test_add_trailing_break_named_events_copies_primitives() -> None:
    df = pd.DataFrame(
        {
            "breaks_above_trailing_high_3": [False, True, np.nan],
            "breaks_below_trailing_low_3": [True, False, False],
        },
        index=_index(3),
    )
    original = df.copy(deep=True)

    result = add_trailing_break_named_events(df, lookback=3)

    assert result["event_trailing_breakout_3"].tolist() == [False, True, False]
    assert result["event_trailing_breakdown_3"].tolist() == [True, False, False]
    pd.testing.assert_frame_equal(df, original)

    with pytest.raises(ValueError, match="Missing required columns"):
        add_trailing_break_named_events(
            df.drop(columns=["breaks_below_trailing_low_3"]),
            lookback=3,
        )


def test_add_standard_zone_break_named_events_crosses_available_zones_only() -> None:
    df = pd.DataFrame(
        {
            "close": [99.0, 100.5, 101.5, 99.5, 98.5, 100.0],
            "prior_day_high_zone_lower": [99.0] * 6,
            "prior_day_high_zone_upper": [101.0, 101.0, 101.0, 101.0, 101.0, np.nan],
            "prior_day_low_zone_lower": [99.0, 99.0, 99.0, 99.0, 99.0, np.nan],
            "prior_day_low_zone_upper": [100.0] * 6,
        },
        index=_index(6),
    )
    original = df.copy(deep=True)

    result = add_standard_zone_break_named_events(df)

    assert result["event_prior_day_high_break_above"].tolist() == [
        False,
        False,
        True,
        False,
        False,
        False,
    ]
    assert result["event_prior_day_low_break_below"].tolist() == [
        False,
        False,
        False,
        False,
        True,
        False,
    ]
    assert "event_premarket_high_break_above" not in result.columns
    pd.testing.assert_frame_equal(df, original)

    with pytest.raises(ValueError, match="Missing required columns"):
        add_standard_zone_break_named_events(df.drop(columns=["close"]))


def test_add_structure_named_events_maps_breaks_and_contexts() -> None:
    df = pd.DataFrame(
        {
            "bullish_structure_break": [False, True, False, np.nan],
            "bearish_structure_break": [False, False, True, False],
            "structure_state": ["bullish", "down", "Range Bound", None],
        },
        index=_index(4),
    )
    original = df.copy(deep=True)

    result = add_structure_named_events(df)

    assert result["event_bullish_structure_break"].tolist() == [False, True, False, False]
    assert result["event_bearish_structure_break"].tolist() == [False, False, True, False]
    assert result["event_structure_context_bullish"].tolist() == [True, False, False, False]
    assert result["event_structure_context_bearish"].tolist() == [False, True, False, False]
    assert result["event_structure_context_range_or_unknown"].tolist() == [
        False,
        False,
        True,
        True,
    ]
    pd.testing.assert_frame_equal(df, original)

    skipped = add_structure_named_events(pd.DataFrame({"close": [1.0]}, index=_index(1)))
    assert find_named_event_columns(skipped) == ()


def test_add_retest_named_events_copies_and_aggregates_available_sources() -> None:
    df = pd.DataFrame(
        {
            "breakout_retest_touch_3": [False, True, False],
            "breakout_retest_hold_3": [False, False, True],
            "breakout_retest_failure_3": [False, False, False],
            "breakdown_retest_touch_3": [True, False, False],
            "breakdown_retest_hold_3": [False, True, False],
            "breakdown_retest_failure_3": [False, False, True],
            "prior_day_low_support_retest_touch": [False, True, False],
            "pivot_low_support_retest_touch": [True, False, False],
            "prior_day_low_support_retest_hold": [False, False, True],
            "pivot_low_support_retest_failure": [False, True, False],
            "prior_day_high_resistance_retest_touch": [False, False, True],
            "pivot_high_resistance_retest_hold": [True, False, False],
            "prior_day_high_resistance_retest_failure": [False, True, False],
        },
        index=_index(3),
    )
    original = df.copy(deep=True)

    result = add_retest_named_events(df, trailing_lookback=3)

    assert result["event_breakout_retest_touch_3"].tolist() == [False, True, False]
    assert result["event_breakdown_retest_failure_3"].tolist() == [False, False, True]
    assert result["event_any_support_retest_touch"].tolist() == [True, True, False]
    assert result["event_any_support_retest_hold"].tolist() == [False, False, True]
    assert result["event_any_support_retest_failure"].tolist() == [False, True, False]
    assert result["event_any_resistance_retest_touch"].tolist() == [False, False, True]
    assert result["event_any_resistance_retest_hold"].tolist() == [True, False, False]
    assert result["event_any_resistance_retest_failure"].tolist() == [False, True, False]
    pd.testing.assert_frame_equal(df, original)

    skipped = add_retest_named_events(pd.DataFrame({"close": [1.0]}, index=_index(1)), trailing_lookback=3)
    assert find_named_event_columns(skipped) == ()


def test_add_false_break_named_events_copies_without_inferring() -> None:
    df = pd.DataFrame(
        {
            "false_breakout_3": [False, True, False],
            "false_breakdown_3": [False, False, True],
            "recent_breakout_level_3": [np.nan, 100.0, 100.0],
        },
        index=_index(3),
    )
    original = df.copy(deep=True)

    result = add_false_break_named_events(df, lookback=3)

    assert result["event_failed_breakout_3"].tolist() == [False, True, False]
    assert result["event_failed_breakdown_3"].tolist() == [False, False, True]
    assert "event_failed_breakout_4" not in result.columns
    pd.testing.assert_frame_equal(df, original)

    skipped = add_false_break_named_events(pd.DataFrame({"close": [99.0]}, index=_index(1)), lookback=3)
    assert find_named_event_columns(skipped) == ()


def test_add_momentum_volume_named_events_adds_combinations() -> None:
    df = pd.DataFrame(
        {
            "consecutive_higher_closes_3": [True, False, True],
            "consecutive_lower_closes_3": [False, True, True],
            "range_expansion_5": [True, True, False],
            "volume_expansion_5": [False, True, True],
        },
        index=_index(3),
    )
    original = df.copy(deep=True)

    result = add_momentum_volume_named_events(df, consecutive_count=3, expansion_window=5)

    assert result["event_momentum_up_3"].tolist() == [True, False, True]
    assert result["event_momentum_down_3"].tolist() == [False, True, True]
    assert result["event_range_expansion_5"].tolist() == [True, True, False]
    assert result["event_volume_expansion_5"].tolist() == [False, True, True]
    assert result["event_momentum_expansion_up_3_5"].tolist() == [True, False, False]
    assert result["event_momentum_expansion_down_3_5"].tolist() == [False, True, False]
    assert result["event_volume_confirmed_momentum_up_3_5"].tolist() == [False, False, True]
    assert result["event_volume_confirmed_momentum_down_3_5"].tolist() == [False, True, True]
    pd.testing.assert_frame_equal(df, original)

    skipped = add_momentum_volume_named_events(
        pd.DataFrame({"close": [1.0]}, index=_index(1)),
        consecutive_count=3,
        expansion_window=5,
    )
    assert find_named_event_columns(skipped) == ()


def test_add_trend_continuation_named_events_respects_optional_confirmations() -> None:
    df = pd.DataFrame(
        {
            "directional_regime": [
                "Trending Up",
                "Trending Up",
                "Trending Down",
                "Trending Down",
                "Range Bound",
            ],
            "event_momentum_up_3": [True, True, False, False, True],
            "event_momentum_down_3": [False, False, True, True, False],
            "above_vwap": [True, False, False, False, True],
            "below_vwap": [False, False, True, False, False],
        },
        index=_index(5),
    )
    original = df.copy(deep=True)

    result = add_trend_continuation_named_events(df, consecutive_count=3)

    assert result["event_trend_continuation_up_context"].tolist() == [
        True,
        False,
        False,
        False,
        False,
    ]
    assert result["event_trend_continuation_down_context"].tolist() == [
        False,
        False,
        True,
        False,
        False,
    ]
    pd.testing.assert_frame_equal(df, original)

    no_confirmations = df.drop(columns=["above_vwap", "below_vwap"])
    result_no_confirmations = add_trend_continuation_named_events(
        no_confirmations,
        consecutive_count=3,
    )
    assert result_no_confirmations["event_trend_continuation_up_context"].tolist() == [
        True,
        True,
        False,
        False,
        False,
    ]

    skipped = add_trend_continuation_named_events(
        pd.DataFrame({"directional_regime": ["Trending Up"]}, index=_index(1)),
        consecutive_count=3,
    )
    assert find_named_event_columns(skipped) == ()


def test_add_named_event_features_composes_available_groups() -> None:
    df = pd.DataFrame(
        {
            "close": [99.0, 101.0, 102.0],
            "high": [99.5, 101.5, 102.5],
            "low": [98.5, 99.5, 101.5],
            "vwap": [100.0, 100.0, 100.0],
            "breaks_above_trailing_high_3": [False, True, False],
            "breaks_below_trailing_low_3": [False, False, True],
            "false_breakout_3": [False, False, True],
            "consecutive_higher_closes_3": [False, True, True],
            "range_expansion_5": [False, True, False],
            "directional_regime": ["Unknown", "Trending Up", "Trending Up"],
        },
        index=_index(3),
    )
    original = df.copy(deep=True)

    result = add_named_event_features(
        df,
        trailing_lookback=3,
        consecutive_count=3,
        expansion_window=5,
    )

    assert result.index.equals(df.index)
    assert len(result) == len(df)
    for column in df.columns:
        assert column in result.columns
    assert "event_vwap_reclaim_bullish" in result.columns
    assert "event_trailing_breakout_3" in result.columns
    assert "event_failed_breakout_3" in result.columns
    assert "event_momentum_expansion_up_3_5" in result.columns
    assert "event_trend_continuation_up_context" in result.columns
    pd.testing.assert_frame_equal(df, original)


def test_find_named_event_columns_preserves_order_and_prefix() -> None:
    df = pd.DataFrame(
        {
            "close": [1.0],
            "event_a": [True],
            "not_event": [False],
            "event_b": [False],
            "flag_c": [True],
        }
    )

    assert find_named_event_columns(df) == ("event_a", "event_b")
    assert find_named_event_columns(df, prefix="flag_") == ("flag_c",)


def test_named_events_are_stable_when_future_rows_change() -> None:
    df = pd.DataFrame(
        {
            "close": [99.0, 101.0, 100.5, 99.5, 98.5],
            "high": [99.5, 101.5, 101.0, 100.0, 99.0],
            "low": [98.5, 99.5, 100.0, 99.0, 98.0],
            "vwap": [100.0, 100.0, 100.0, 100.0, 100.0],
            "prior_day_high_zone_lower": [99.0] * 5,
            "prior_day_high_zone_upper": [101.0] * 5,
        },
        index=_index(5),
    )
    modified = df.copy()
    modified.loc[modified.index[3:], ["close", "vwap", "prior_day_high_zone_upper"]] = [
        [250.0, 300.0, 400.0],
        [10.0, 5.0, 1.0],
    ]

    original_result = add_named_event_features(df)
    modified_result = add_named_event_features(modified)
    event_cols = [
        "event_vwap_reclaim_bullish",
        "event_vwap_loss_bearish",
        "event_prior_day_high_break_above",
    ]

    pd.testing.assert_frame_equal(
        original_result.loc[original_result.index[:3], event_cols],
        modified_result.loc[modified_result.index[:3], event_cols],
    )
