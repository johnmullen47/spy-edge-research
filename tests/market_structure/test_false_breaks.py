from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from spy_edge_research.market_structure import (
    add_false_break_count_features,
    add_false_break_events,
    add_false_break_features,
    add_recent_break_context,
)


def _break_context_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "close": [99.0, 101.0, 99.0, 98.0, 97.0, 89.0, 91.0, 92.0, 93.0],
            "trailing_high_3": [np.nan, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0],
            "trailing_low_3": [np.nan, 90.0, 90.0, 90.0, 90.0, 90.0, 90.0, 90.0, 90.0],
            "breaks_above_trailing_high_3": [
                False,
                True,
                False,
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
                False,
                True,
                False,
                False,
                False,
            ],
        },
        index=pd.Index(pd.date_range("2024-01-02 09:31", periods=9, freq="1min"), name="ts"),
    )


def test_add_recent_break_context_tracks_resets_and_expires_causally() -> None:
    df = _break_context_frame()
    df.loc[df.index[7], "breaks_above_trailing_high_3"] = True
    df.loc[df.index[7], "trailing_high_3"] = 105.0
    original = df.copy(deep=True)

    result = add_recent_break_context(df, lookback=3, max_bars_after_break=2)

    pd.testing.assert_series_equal(
        result["recent_breakout_level_3"],
        pd.Series(
            [np.nan, 100.0, 100.0, 100.0, np.nan, np.nan, np.nan, 105.0, 105.0],
            index=df.index,
            name="recent_breakout_level_3",
        ),
    )
    pd.testing.assert_series_equal(
        result["bars_since_recent_breakout_3"],
        pd.Series(
            [np.nan, 0.0, 1.0, 2.0, np.nan, np.nan, np.nan, 0.0, 1.0],
            index=df.index,
            name="bars_since_recent_breakout_3",
        ),
    )
    pd.testing.assert_series_equal(
        result["recent_breakdown_level_3"],
        pd.Series(
            [np.nan, np.nan, np.nan, np.nan, np.nan, 90.0, 90.0, 90.0, np.nan],
            index=df.index,
            name="recent_breakdown_level_3",
        ),
    )
    pd.testing.assert_series_equal(
        result["bars_since_recent_breakdown_3"],
        pd.Series(
            [np.nan, np.nan, np.nan, np.nan, np.nan, 0.0, 1.0, 2.0, np.nan],
            index=df.index,
            name="bars_since_recent_breakdown_3",
        ),
    )
    assert result.index.equals(df.index)
    assert len(result) == len(df)
    pd.testing.assert_frame_equal(df, original)

    with pytest.raises(ValueError, match="Missing required columns"):
        add_recent_break_context(df.drop(columns=["trailing_low_3"]), lookback=3)
    with pytest.raises(ValueError, match="lookback"):
        add_recent_break_context(df, lookback=0)
    with pytest.raises(ValueError, match="max_bars_after_break"):
        add_recent_break_context(df, lookback=3, max_bars_after_break=0)


def test_add_false_break_events_emits_only_after_prior_break_and_before_expiry() -> None:
    df = _break_context_frame()
    original = df.copy(deep=True)

    result = add_false_break_events(df, lookback=3, max_bars_after_break=2)

    assert "recent_breakout_level_3" in result.columns
    assert result["false_breakout_3"].tolist() == [
        False,
        False,
        True,
        True,
        False,
        False,
        False,
        False,
        False,
    ]
    assert result["false_breakdown_3"].tolist() == [
        False,
        False,
        False,
        False,
        False,
        False,
        True,
        True,
        False,
    ]
    assert result.index.equals(df.index)
    pd.testing.assert_frame_equal(df, original)

    context = add_recent_break_context(df, lookback=3, max_bars_after_break=2)
    result_from_context = add_false_break_events(context, lookback=3, max_bars_after_break=2)
    pd.testing.assert_series_equal(
        result["false_breakout_3"],
        result_from_context["false_breakout_3"],
    )

    with pytest.raises(ValueError, match="Missing required columns"):
        add_false_break_events(df.drop(columns=["close"]), lookback=3)


def test_add_false_break_count_features_counts_trailing_events_and_validates_inputs() -> None:
    df = pd.DataFrame(
        {
            "false_breakout_3": [False, True, True, False],
            "false_breakdown_3": [False, False, True, True],
        },
        index=pd.Index(list("abcd")),
    )
    original = df.copy(deep=True)

    result = add_false_break_count_features(df, lookback=3, count_lookback=2)

    assert result["false_breakout_count_3_2"].tolist() == pytest.approx([0.0, 1.0, 2.0, 1.0])
    assert result["false_breakdown_count_3_2"].tolist() == pytest.approx([0.0, 0.0, 1.0, 2.0])
    assert result.index.equals(df.index)
    pd.testing.assert_frame_equal(df, original)

    with pytest.raises(ValueError, match="count_lookback"):
        add_false_break_count_features(df, lookback=3, count_lookback=0)
    with pytest.raises(ValueError, match="Missing required columns"):
        add_false_break_count_features(df.drop(columns=["false_breakout_3"]), lookback=3)


def test_add_false_break_features_composes_context_events_and_counts() -> None:
    df = _break_context_frame()
    original = df.copy(deep=True)

    result = add_false_break_features(
        df,
        lookback=3,
        max_bars_after_break=2,
        count_lookback=3,
    )

    expected_columns = {
        "recent_breakout_level_3",
        "recent_breakdown_level_3",
        "bars_since_recent_breakout_3",
        "bars_since_recent_breakdown_3",
        "false_breakout_3",
        "false_breakdown_3",
        "false_breakout_count_3_3",
        "false_breakdown_count_3_3",
    }
    assert expected_columns.issubset(result.columns)
    for column in original.columns:
        assert column in result.columns
    assert result.index.equals(df.index)
    assert len(result) == len(df)
    pd.testing.assert_frame_equal(df, original)


def test_false_break_flags_are_stable_when_future_close_changes() -> None:
    df = _break_context_frame()
    modified = df.copy()
    modified.loc[modified.index[4:], "close"] = [250.0, 10.0, 250.0, 250.0, 250.0]

    original_result = add_false_break_events(df, lookback=3, max_bars_after_break=2)
    modified_result = add_false_break_events(modified, lookback=3, max_bars_after_break=2)

    pd.testing.assert_frame_equal(
        original_result.loc[original_result.index[:4], ["false_breakout_3", "false_breakdown_3"]],
        modified_result.loc[modified_result.index[:4], ["false_breakout_3", "false_breakdown_3"]],
    )
