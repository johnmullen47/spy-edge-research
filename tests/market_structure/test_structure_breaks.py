from __future__ import annotations

import pandas as pd
import pytest

from spy_edge_research.market_structure import (
    add_market_structure_features,
    add_structure_breaks,
    add_structure_state,
)


def break_sample() -> pd.DataFrame:
    index = pd.Index(pd.date_range("2024-01-02 09:31", periods=10, freq="1min"), name="ts")
    return pd.DataFrame(
        {
            "high": [10.0, 12.0, 11.0, 11.0, 13.0, 12.0, 11.0, 10.0, 9.0, 8.0],
            "low": [9.0, 8.0, 9.0, 10.0, 9.0, 8.0, 7.0, 6.0, 5.0, 4.0],
            "close": [9.5, 11.5, 11.0, 12.5, 12.8, 12.0, 7.5, 5.5, 4.5, 3.5],
        },
        index=index,
    )


def test_add_structure_breaks_uses_only_confirmed_pivot_levels() -> None:
    df = break_sample()
    original = df.copy(deep=True)

    result = add_structure_breaks(df, left_bars=1, right_bars=1)

    assert "bullish_structure_break" in result.columns
    assert "bearish_structure_break" in result.columns
    assert result.index.equals(df.index)
    assert bool(result["bullish_structure_break"].iloc[0]) is False
    assert bool(result["bearish_structure_break"].iloc[0]) is False
    pd.testing.assert_frame_equal(df, original)

    assert result["last_confirmed_pivot_high"].iloc[:2].isna().all()
    assert result["bullish_structure_break"].iloc[:3].tolist() == [False, False, False]
    assert result["last_confirmed_pivot_high"].iloc[2] == 12.0
    assert bool(result["bullish_structure_break"].iloc[3]) is True
    assert result["bullish_structure_break"].iloc[4:6].tolist() == [False, False]

    assert result["last_confirmed_pivot_low"].iloc[:2].isna().all()
    assert result["bearish_structure_break"].iloc[:6].tolist() == [False] * 6
    assert result["last_confirmed_pivot_low"].iloc[2] == 8.0
    assert bool(result["bearish_structure_break"].iloc[6]) is True
    assert result["bearish_structure_break"].iloc[7:].tolist() == [False, False, False]


def test_add_structure_breaks_validates_price_column() -> None:
    with pytest.raises(ValueError, match="Missing required columns"):
        add_structure_breaks(break_sample().drop(columns=["close"]))


def test_add_structure_state_tracks_latest_one_sided_break() -> None:
    df = break_sample()

    result = add_structure_state(df, left_bars=1, right_bars=1)

    assert result["structure_state"].iloc[0] == "neutral"
    assert result["structure_state"].iloc[2] == "neutral"
    assert result["structure_state"].iloc[3] == "bullish"
    assert result["structure_state"].iloc[5] == "bullish"
    assert result["structure_state"].iloc[6] == "bearish"
    assert result["structure_state"].iloc[-1] == "bearish"


def test_add_structure_state_handles_no_break_data_as_neutral() -> None:
    df = pd.DataFrame({"close": [10.0, 10.0, 10.0]})

    result = add_structure_state(
        df.assign(
            bullish_structure_break=[False, False, False],
            bearish_structure_break=[False, False, False],
        )
    )

    assert result["structure_state"].tolist() == ["neutral", "neutral", "neutral"]


def test_add_structure_state_handles_same_row_bullish_and_bearish_break_as_neutral() -> None:
    df = pd.DataFrame(
        {
            "close": [10.0, 11.0, 10.5, 10.8],
            "bullish_structure_break": [False, True, True, False],
            "bearish_structure_break": [False, False, True, False],
        }
    )

    result = add_structure_state(df)

    assert result["structure_state"].tolist() == ["neutral", "bullish", "neutral", "bullish"]


def test_add_market_structure_features_composes_all_market_structure_columns() -> None:
    df = break_sample()
    original = df.copy(deep=True)

    result = add_market_structure_features(df, left_bars=1, right_bars=1)

    expected_columns = {
        "pivot_high_candidate",
        "pivot_low_candidate",
        "confirmed_pivot_high",
        "confirmed_pivot_low",
        "pivot_high_price",
        "pivot_low_price",
        "last_confirmed_pivot_high",
        "last_confirmed_pivot_low",
        "higher_high",
        "lower_high",
        "higher_low",
        "lower_low",
        "bullish_structure_break",
        "bearish_structure_break",
        "structure_state",
    }
    assert expected_columns.issubset(result.columns)
    assert len(result) == len(df)
    assert result.index.equals(df.index)
    pd.testing.assert_frame_equal(df, original)


def test_structure_values_are_stable_when_rows_after_confirmation_change() -> None:
    df = break_sample()
    modified = df.copy()
    modified.iloc[4:, modified.columns.get_loc("high")] = [100.0, 101.0, 102.0, 103.0, 104.0, 105.0]
    modified.iloc[4:, modified.columns.get_loc("low")] = [1.0, 0.5, 0.25, 0.2, 0.1, 0.05]
    modified.iloc[4:, modified.columns.get_loc("close")] = [50.0, 51.0, 52.0, 53.0, 54.0, 55.0]

    original_result = add_market_structure_features(df, left_bars=1, right_bars=1)
    modified_result = add_market_structure_features(modified, left_bars=1, right_bars=1)
    causal_columns = [
        "confirmed_pivot_high",
        "confirmed_pivot_low",
        "pivot_high_price",
        "pivot_low_price",
        "last_confirmed_pivot_high",
        "last_confirmed_pivot_low",
        "bullish_structure_break",
        "bearish_structure_break",
        "structure_state",
    ]

    pd.testing.assert_frame_equal(
        original_result.loc[original_result.index[:4], causal_columns],
        modified_result.loc[modified_result.index[:4], causal_columns],
    )
