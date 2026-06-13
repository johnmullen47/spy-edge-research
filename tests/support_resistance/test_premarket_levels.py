from __future__ import annotations

import pandas as pd
import pytest

from spy_edge_research.support_resistance import add_premarket_levels


def sample() -> pd.DataFrame:
    index = pd.Index(list("abcdefg"), name="row")
    return pd.DataFrame(
        {
            "timestamp": [
                pd.Timestamp("2024-01-02 07:00", tz="America/New_York"),
                pd.Timestamp("2024-01-02 08:00", tz="America/New_York"),
                pd.Timestamp("2024-01-02 09:30", tz="America/New_York"),
                pd.Timestamp("2024-01-02 09:31", tz="America/New_York"),
                pd.Timestamp("2024-01-02 10:00", tz="America/New_York"),
                pd.Timestamp("2024-01-03 09:31", tz="America/New_York"),
                pd.Timestamp("2024-01-03 10:00", tz="America/New_York"),
            ],
            "high": [101.0, 103.0, 102.0, 104.0, 105.0, 106.0, 107.0],
            "low": [99.0, 98.0, 100.0, 101.0, 102.0, 104.0, 105.0],
            "close": [100.0, 102.0, 101.0, 104.0, 99.0, 106.0, 104.0],
        },
        index=index,
    )


def test_premarket_high_low_so_far_are_cumulative_only_through_current_row() -> None:
    result = add_premarket_levels(sample())

    assert result.loc[["a", "b", "c"], "premarket_high_so_far"].tolist() == [
        101.0,
        103.0,
        103.0,
    ]
    assert result.loc[["a", "b", "c"], "premarket_low_so_far"].tolist() == [
        99.0,
        98.0,
        98.0,
    ]
    assert result.loc["a", "premarket_high_so_far"] != result.loc["c", "premarket_high_so_far"]


def test_early_premarket_rows_do_not_know_later_premarket_highs() -> None:
    df = sample()
    modified = df.copy()
    modified.loc["c", "high"] = 200.0
    modified.loc["c", "low"] = 50.0

    original = add_premarket_levels(df)
    changed = add_premarket_levels(modified)

    pd.testing.assert_series_equal(
        original.loc[["a", "b"], "premarket_high_so_far"],
        changed.loc[["a", "b"], "premarket_high_so_far"],
    )
    pd.testing.assert_series_equal(
        original.loc[["a", "b"], "premarket_low_so_far"],
        changed.loc[["a", "b"], "premarket_low_so_far"],
    )


def test_regular_rows_receive_completed_same_day_premarket_levels() -> None:
    result = add_premarket_levels(sample())

    assert result.loc[["d", "e"], "premarket_high"].tolist() == [103.0, 103.0]
    assert result.loc[["d", "e"], "premarket_low"].tolist() == [98.0, 98.0]


def test_dates_with_no_premarket_rows_receive_nan_levels() -> None:
    result = add_premarket_levels(sample())

    assert result.loc[["f", "g"], "premarket_high"].isna().all()
    assert result.loc[["f", "g"], "premarket_low"].isna().all()


def test_distance_and_boolean_columns_are_correct() -> None:
    result = add_premarket_levels(sample())

    assert result.loc["d", "distance_to_premarket_high"] == 1.0
    assert result.loc["d", "distance_to_premarket_low"] == 6.0
    assert bool(result.loc["d", "above_premarket_high"]) is True
    assert bool(result.loc["e", "below_premarket_low"]) is False
    assert bool(result.loc["f", "above_premarket_high"]) is False


def test_missing_required_columns_raise_value_error() -> None:
    df = sample()

    with pytest.raises(ValueError, match="Missing required columns"):
        add_premarket_levels(df.drop(columns=["high"]))
    with pytest.raises(ValueError, match="Missing required columns"):
        add_premarket_levels(df, session_col="session")


def test_input_is_not_mutated_and_index_row_count_are_preserved() -> None:
    df = sample()
    original = df.copy(deep=True)

    result = add_premarket_levels(df)

    pd.testing.assert_frame_equal(df, original)
    assert result.index.equals(df.index)
    assert len(result) == len(df)
