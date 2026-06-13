from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from spy_edge_research.support_resistance import add_prior_day_levels


def sample() -> pd.DataFrame:
    index = pd.Index(list("abcdef"), name="row")
    return pd.DataFrame(
        {
            "timestamp": [
                pd.Timestamp("2024-01-02 09:31", tz="America/New_York"),
                pd.Timestamp("2024-01-02 16:00", tz="America/New_York"),
                pd.Timestamp("2024-01-03 09:31", tz="America/New_York"),
                pd.Timestamp("2024-01-03 12:00", tz="America/New_York"),
                pd.Timestamp("2024-01-03 16:00", tz="America/New_York"),
                pd.Timestamp("2024-01-04 09:31", tz="America/New_York"),
            ],
            "high": [101.0, 104.0, 103.0, 110.0, 108.0, 111.0],
            "low": [99.0, 100.0, 101.0, 102.0, 100.0, 109.0],
            "close": [100.0, 103.0, 105.0, 102.0, 107.0, 110.0],
        },
        index=index,
    )


def test_adds_prior_day_levels_and_first_date_is_nan() -> None:
    result = add_prior_day_levels(sample())

    expected_columns = {
        "prior_day_high",
        "prior_day_low",
        "prior_day_close",
        "distance_to_prior_day_high",
        "distance_to_prior_day_low",
        "distance_to_prior_day_close",
        "above_prior_day_high",
        "below_prior_day_low",
    }
    assert expected_columns.issubset(result.columns)
    assert result.loc[["a", "b"], ["prior_day_high", "prior_day_low", "prior_day_close"]].isna().all().all()


def test_second_date_uses_only_completed_prior_date_levels() -> None:
    result = add_prior_day_levels(sample())

    assert result.loc["c":"e", "prior_day_high"].tolist() == [104.0, 104.0, 104.0]
    assert result.loc["c":"e", "prior_day_low"].tolist() == [99.0, 99.0, 99.0]
    assert result.loc["c":"e", "prior_day_close"].tolist() == [103.0, 103.0, 103.0]
    assert result.loc["f", "prior_day_high"] == 110.0


def test_same_day_future_highs_do_not_affect_same_day_prior_levels() -> None:
    df = sample()
    modified = df.copy()
    modified.loc["e", "high"] = 500.0
    modified.loc["e", "low"] = 50.0
    modified.loc["e", "close"] = 400.0

    original = add_prior_day_levels(df)
    changed = add_prior_day_levels(modified)

    pd.testing.assert_frame_equal(
        original.loc[["c", "d"], ["prior_day_high", "prior_day_low", "prior_day_close"]],
        changed.loc[["c", "d"], ["prior_day_high", "prior_day_low", "prior_day_close"]],
    )


def test_session_col_limits_prior_day_calculation_to_regular_rows() -> None:
    df = sample()
    df["session"] = ["premarket", "regular", "regular", "premarket", "regular", "regular"]

    result = add_prior_day_levels(df, session_col="session")

    assert result.loc["c", "prior_day_high"] == 104.0
    assert result.loc["c", "prior_day_low"] == 100.0
    assert result.loc["f", "prior_day_high"] == 108.0
    assert result.loc["f", "prior_day_low"] == 100.0


def test_distance_and_boolean_columns_are_correct() -> None:
    result = add_prior_day_levels(sample())

    assert result.loc["c", "distance_to_prior_day_high"] == 1.0
    assert result.loc["c", "distance_to_prior_day_low"] == 6.0
    assert result.loc["c", "distance_to_prior_day_close"] == 2.0
    assert bool(result.loc["c", "above_prior_day_high"]) is True
    assert bool(result.loc["a", "above_prior_day_high"]) is False
    assert bool(result.loc["b", "below_prior_day_low"]) is False


def test_missing_required_columns_raise_value_error() -> None:
    df = sample()

    with pytest.raises(ValueError, match="Missing required columns"):
        add_prior_day_levels(df.drop(columns=["timestamp"]))
    with pytest.raises(ValueError, match="Missing required columns"):
        add_prior_day_levels(df, session_col="session")


def test_input_is_not_mutated_and_index_row_count_are_preserved() -> None:
    df = sample()
    original = df.copy(deep=True)

    result = add_prior_day_levels(df)

    pd.testing.assert_frame_equal(df, original)
    assert result.index.equals(df.index)
    assert len(result) == len(df)
    assert np.array_equal(result.index.to_numpy(), df.index.to_numpy())
