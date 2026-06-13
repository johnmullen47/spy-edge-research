"""Chronological train/test split helpers for out-of-sample research."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pandas as pd


def create_time_series_splits(
    df: pd.DataFrame,
    *,
    train_size: int,
    test_size: int,
    n_splits: int,
    step_size: int | None = None,
) -> list[dict[str, Any]]:
    """Create fixed-width chronological train/test splits."""
    _validate_positive_int(train_size, "train_size")
    _validate_positive_int(test_size, "test_size")
    _validate_positive_int(n_splits, "n_splits")
    if step_size is None:
        step_size = test_size
    _validate_positive_int(step_size, "step_size")

    splits = []
    for split_number in range(n_splits):
        train_start = split_number * step_size
        train_end = train_start + train_size
        test_start = train_end
        test_end = test_start + test_size
        if test_end > len(df):
            break
        splits.append(
            _make_split_record(
                split_number=split_number,
                train_start=train_start,
                train_end=train_end,
                test_start=test_start,
                test_end=test_end,
            )
        )
    return splits


def create_walk_forward_splits(
    df: pd.DataFrame,
    *,
    initial_train_size: int,
    test_size: int,
    step_size: int | None = None,
    expanding: bool = True,
    max_train_size: int | None = None,
) -> list[dict[str, Any]]:
    """Create chronological walk-forward splits."""
    _validate_positive_int(initial_train_size, "initial_train_size")
    _validate_positive_int(test_size, "test_size")
    if step_size is None:
        step_size = test_size
    _validate_positive_int(step_size, "step_size")
    if max_train_size is not None:
        _validate_positive_int(max_train_size, "max_train_size")

    splits = []
    split_number = 0
    test_start = initial_train_size
    while test_start + test_size <= len(df):
        if expanding:
            train_start = 0
        else:
            train_start = test_start - initial_train_size
        if max_train_size is not None:
            train_start = max(train_start, test_start - max_train_size)
        train_end = test_start
        splits.append(
            _make_split_record(
                split_number=split_number,
                train_start=train_start,
                train_end=train_end,
                test_start=test_start,
                test_end=test_start + test_size,
            )
        )
        split_number += 1
        test_start += step_size
    return splits


def validate_time_series_split(split: Mapping[str, Any]) -> dict[str, Any]:
    """Validate one chronological split record."""
    required = ["split_number", "train_indices", "test_indices"]
    missing = [field for field in required if field not in split]
    if missing:
        raise KeyError(f"split is missing required fields: {missing}")
    train_indices = list(split["train_indices"])
    test_indices = list(split["test_indices"])
    if not train_indices:
        raise ValueError("train_indices must not be empty")
    if not test_indices:
        raise ValueError("test_indices must not be empty")
    if set(train_indices).intersection(test_indices):
        raise ValueError("train_indices and test_indices must not overlap")
    if max(train_indices) >= min(test_indices):
        raise ValueError("train_indices must occur before test_indices")
    return dict(split)


def summarize_walk_forward_splits(splits: list[Mapping[str, Any]]) -> pd.DataFrame:
    """Summarize chronological split records."""
    rows = []
    for split in splits:
        validated = validate_time_series_split(split)
        train_indices = list(validated["train_indices"])
        test_indices = list(validated["test_indices"])
        rows.append(
            {
                "split_number": validated["split_number"],
                "train_start": min(train_indices),
                "train_end": max(train_indices),
                "test_start": min(test_indices),
                "test_end": max(test_indices),
                "train_size": len(train_indices),
                "test_size": len(test_indices),
            }
        )
    return pd.DataFrame(
        rows,
        columns=[
            "split_number",
            "train_start",
            "train_end",
            "test_start",
            "test_end",
            "train_size",
            "test_size",
        ],
    )


def _make_split_record(
    *,
    split_number: int,
    train_start: int,
    train_end: int,
    test_start: int,
    test_end: int,
) -> dict[str, Any]:
    split = {
        "split_number": split_number,
        "train_indices": list(range(train_start, train_end)),
        "test_indices": list(range(test_start, test_end)),
    }
    validate_time_series_split(split)
    return split


def _validate_positive_int(value: int, name: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise ValueError(f"{name} must be an integer greater than or equal to 1")
