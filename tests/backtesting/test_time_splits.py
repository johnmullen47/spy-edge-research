from __future__ import annotations

import pandas as pd
import pytest

from spy_edge_research.backtesting import (
    create_time_series_splits,
    create_walk_forward_splits,
    summarize_walk_forward_splits,
    validate_time_series_split,
)


def sample_split_frame(rows: int = 12) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "timestamp": pd.date_range("2024-01-02 09:31", periods=rows, freq="1min"),
            "close": range(rows),
        }
    )


def test_create_time_series_splits_uses_fixed_chronological_windows() -> None:
    df = sample_split_frame(12)

    splits = create_time_series_splits(
        df,
        train_size=4,
        test_size=2,
        n_splits=3,
        step_size=2,
    )

    assert [split["train_indices"] for split in splits] == [
        [0, 1, 2, 3],
        [2, 3, 4, 5],
        [4, 5, 6, 7],
    ]
    assert [split["test_indices"] for split in splits] == [
        [4, 5],
        [6, 7],
        [8, 9],
    ]


def test_create_walk_forward_splits_supports_expanding_and_rolling_windows() -> None:
    df = sample_split_frame(10)

    expanding = create_walk_forward_splits(
        df,
        initial_train_size=4,
        test_size=2,
        step_size=2,
        expanding=True,
    )
    rolling = create_walk_forward_splits(
        df,
        initial_train_size=4,
        test_size=2,
        step_size=2,
        expanding=False,
    )

    assert [split["train_indices"] for split in expanding] == [
        [0, 1, 2, 3],
        [0, 1, 2, 3, 4, 5],
        [0, 1, 2, 3, 4, 5, 6, 7],
    ]
    assert [split["train_indices"] for split in rolling] == [
        [0, 1, 2, 3],
        [2, 3, 4, 5],
        [4, 5, 6, 7],
    ]


def test_create_walk_forward_splits_can_limit_max_train_size() -> None:
    df = sample_split_frame(12)

    splits = create_walk_forward_splits(
        df,
        initial_train_size=4,
        test_size=2,
        step_size=2,
        expanding=True,
        max_train_size=5,
    )

    assert splits[-1]["train_indices"] == [5, 6, 7, 8, 9]
    assert splits[-1]["test_indices"] == [10, 11]


def test_validate_time_series_split_rejects_overlap_or_non_chronological_splits() -> None:
    valid = {
        "split_number": 0,
        "train_indices": [0, 1, 2],
        "test_indices": [3, 4],
    }

    assert validate_time_series_split(valid) == valid

    with pytest.raises(ValueError, match="overlap"):
        validate_time_series_split(
            {"split_number": 0, "train_indices": [0, 1], "test_indices": [1, 2]}
        )
    with pytest.raises(ValueError, match="before"):
        validate_time_series_split(
            {"split_number": 0, "train_indices": [2, 3], "test_indices": [0, 1]}
        )
    with pytest.raises(KeyError, match="required fields"):
        validate_time_series_split({"train_indices": [0], "test_indices": [1]})


def test_summarize_walk_forward_splits_returns_sizes_and_bounds() -> None:
    splits = create_walk_forward_splits(
        sample_split_frame(8),
        initial_train_size=3,
        test_size=2,
        step_size=2,
    )

    summary = summarize_walk_forward_splits(splits)

    assert summary.to_dict("records") == [
        {
            "split_number": 0,
            "train_start": 0,
            "train_end": 2,
            "test_start": 3,
            "test_end": 4,
            "train_size": 3,
            "test_size": 2,
        },
        {
            "split_number": 1,
            "train_start": 0,
            "train_end": 4,
            "test_start": 5,
            "test_end": 6,
            "train_size": 5,
            "test_size": 2,
        },
    ]


def test_time_split_helpers_validate_parameters() -> None:
    df = sample_split_frame(5)

    with pytest.raises(ValueError, match="train_size"):
        create_time_series_splits(df, train_size=0, test_size=1, n_splits=1)
    with pytest.raises(ValueError, match="initial_train_size"):
        create_walk_forward_splits(df, initial_train_size=0, test_size=1)
