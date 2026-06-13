from __future__ import annotations

import pandas as pd
import pytest

from spy_edge_research.market_structure import (
    add_confirmed_pivots,
    add_last_confirmed_pivot_levels,
    add_market_structure_pivots,
    add_pivot_classification,
)


def pivot_sample() -> pd.DataFrame:
    index = pd.Index(pd.date_range("2024-01-02 09:31", periods=8, freq="1min"), name="ts")
    return pd.DataFrame(
        {
            "high": [10.0, 11.0, 15.0, 12.0, 11.0, 13.0, 12.0, 11.0],
            "low": [9.0, 8.0, 7.0, 8.0, 9.0, 6.0, 7.0, 8.0],
            "close": [9.5, 10.5, 14.0, 11.5, 10.5, 12.0, 11.0, 10.0],
        },
        index=index,
    )


def test_add_confirmed_pivots_delays_pivot_features_until_confirmation() -> None:
    df = pivot_sample()
    original = df.copy(deep=True)

    result = add_confirmed_pivots(df, left_bars=2, right_bars=2)

    expected_columns = {
        "pivot_high_candidate",
        "pivot_low_candidate",
        "confirmed_pivot_high",
        "confirmed_pivot_low",
        "pivot_high_price",
        "pivot_low_price",
    }
    assert expected_columns.issubset(result.columns)
    assert result.index.equals(df.index)
    assert len(result) == len(df)
    pd.testing.assert_frame_equal(df, original)

    assert bool(result["pivot_high_candidate"].iloc[2]) is True
    assert result["confirmed_pivot_high"].iloc[:4].tolist() == [False] * 4
    assert bool(result["confirmed_pivot_high"].iloc[4]) is True
    assert result["pivot_high_price"].iloc[:4].isna().all()
    assert result["pivot_high_price"].iloc[4] == 15.0

    assert bool(result["pivot_low_candidate"].iloc[2]) is True
    assert result["confirmed_pivot_low"].iloc[:4].tolist() == [False] * 4
    assert bool(result["confirmed_pivot_low"].iloc[4]) is True
    assert result["pivot_low_price"].iloc[:4].isna().all()
    assert result["pivot_low_price"].iloc[4] == 7.0

    assert result["pivot_high_candidate"].iloc[-2:].tolist() == [False, False]
    assert result["pivot_low_candidate"].iloc[-2:].tolist() == [False, False]


def test_add_confirmed_pivots_validates_columns_and_parameters() -> None:
    df = pivot_sample()

    with pytest.raises(ValueError, match="Missing required columns"):
        add_confirmed_pivots(df.drop(columns=["high"]))
    with pytest.raises(ValueError, match="Missing required columns"):
        add_confirmed_pivots(df.drop(columns=["low"]))
    with pytest.raises(ValueError, match="left_bars"):
        add_confirmed_pivots(df, left_bars=0)
    with pytest.raises(ValueError, match="right_bars"):
        add_confirmed_pivots(df, right_bars=0)


def test_add_last_confirmed_pivot_levels_forward_fills_after_confirmation_only() -> None:
    df = pivot_sample()

    result = add_last_confirmed_pivot_levels(df, left_bars=2, right_bars=2)

    assert result["last_confirmed_pivot_high"].iloc[:4].isna().all()
    assert result["last_confirmed_pivot_low"].iloc[:4].isna().all()
    assert result["last_confirmed_pivot_high"].iloc[4] == 15.0
    assert result["last_confirmed_pivot_high"].iloc[5] == 15.0
    assert result["last_confirmed_pivot_low"].iloc[4] == 7.0
    assert result["last_confirmed_pivot_low"].iloc[5] == 7.0
    assert result.index.equals(df.index)


def test_add_pivot_classification_compares_only_new_confirmed_pivots() -> None:
    df = pd.DataFrame(
        {
            "high": [1.0] * 8,
            "low": [1.0] * 8,
            "confirmed_pivot_high": [False, True, False, True, False, True, False, True],
            "confirmed_pivot_low": [False, True, False, True, False, True, False, True],
            "pivot_high_price": [None, 10.0, None, 12.0, None, 12.0, None, 11.0],
            "pivot_low_price": [None, 8.0, None, 9.0, None, 9.0, None, 7.0],
        },
        index=pd.Index(list("abcdefgh"), name="row"),
    )

    result = add_pivot_classification(df)

    assert result["higher_high"].tolist() == [False, False, False, True, False, False, False, False]
    assert result["lower_high"].tolist() == [False, False, False, False, False, False, False, True]
    assert result["higher_low"].tolist() == [False, False, False, True, False, False, False, False]
    assert result["lower_low"].tolist() == [False, False, False, False, False, False, False, True]
    assert result["higher_high"].dtype == bool
    assert result["lower_low"].dtype == bool
    assert result.index.equals(df.index)


def test_add_market_structure_pivots_composes_columns_without_mutation() -> None:
    df = pivot_sample()
    original = df.copy(deep=True)

    result = add_market_structure_pivots(df, left_bars=2, right_bars=2)

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
    }
    assert expected_columns.issubset(result.columns)
    pd.testing.assert_frame_equal(df, original)


def test_confirmed_pivot_features_are_stable_when_later_rows_change() -> None:
    df = pivot_sample()
    modified = df.copy()
    modified.iloc[5:, modified.columns.get_loc("high")] = [100.0, 101.0, 102.0]
    modified.iloc[5:, modified.columns.get_loc("low")] = [1.0, 0.5, 0.25]

    original_result = add_market_structure_pivots(df, left_bars=2, right_bars=2)
    modified_result = add_market_structure_pivots(modified, left_bars=2, right_bars=2)
    causal_columns = [
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
    ]

    pd.testing.assert_frame_equal(
        original_result.loc[original_result.index[:5], causal_columns],
        modified_result.loc[modified_result.index[:5], causal_columns],
    )
