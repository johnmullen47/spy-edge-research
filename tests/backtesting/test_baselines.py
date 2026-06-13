from __future__ import annotations

import pandas as pd
import pytest

from spy_edge_research.backtesting import (
    add_always_long_baseline,
    add_always_short_baseline,
    add_basic_baselines,
    add_ema_relation_baseline,
    add_random_direction_baseline,
    add_trailing_break_baseline,
    add_vwap_relation_baseline,
)


def sample_feature_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "close": [101.0, 99.0, 100.0, 100.0, 102.0],
            "vwap": [100.0, 100.0, 100.0, None, 101.0],
            "ema_9": [100.0, 100.0, 100.0, None, 103.0],
            "breaks_above_trailing_high_20": [True, False, False, True, False],
            "breaks_below_trailing_low_20": [False, True, False, True, False],
        },
        index=pd.Index(["a", "b", "c", "d", "e"], name="row"),
    )


def test_always_long_baseline_adds_ones_without_mutation_and_preserves_index() -> None:
    df = sample_feature_frame()
    original = df.copy(deep=True)

    result = add_always_long_baseline(df)

    assert result["baseline_always_long"].tolist() == [1, 1, 1, 1, 1]
    assert result.index.equals(df.index)
    pd.testing.assert_frame_equal(df, original)


def test_always_short_baseline_adds_negative_ones_without_mutation_and_preserves_index() -> None:
    df = sample_feature_frame()
    original = df.copy(deep=True)

    result = add_always_short_baseline(df)

    assert result["baseline_always_short"].tolist() == [-1, -1, -1, -1, -1]
    assert result.index.equals(df.index)
    pd.testing.assert_frame_equal(df, original)


def test_random_direction_baseline_is_seeded_and_validates_probability() -> None:
    df = pd.DataFrame({"close": range(100)}, index=pd.Index(range(100), name="row"))
    original = df.copy(deep=True)

    first = add_random_direction_baseline(df, seed=7)
    second = add_random_direction_baseline(df, seed=7)
    different = add_random_direction_baseline(df, seed=8)
    neutral = add_random_direction_baseline(df, seed=7, neutral_probability=0.25)

    assert first["baseline_random_direction"].equals(second["baseline_random_direction"])
    assert not first["baseline_random_direction"].equals(
        different["baseline_random_direction"]
    )
    assert set(first["baseline_random_direction"].unique()).issubset({-1, 1})
    assert set(neutral["baseline_random_direction"].unique()).issubset({-1, 0, 1})
    assert 0 in set(neutral["baseline_random_direction"].unique())
    with pytest.raises(ValueError, match="neutral_probability"):
        add_random_direction_baseline(df, neutral_probability=-0.1)
    with pytest.raises(ValueError, match="neutral_probability"):
        add_random_direction_baseline(df, neutral_probability=1.0)
    pd.testing.assert_frame_equal(df, original)


def test_vwap_relation_baseline_maps_relation_and_validates_columns() -> None:
    df = sample_feature_frame()
    original = df.copy(deep=True)

    result = add_vwap_relation_baseline(df)

    assert result["baseline_vwap_relation"].tolist() == [1, -1, 0, 0, 1]
    with pytest.raises(ValueError, match="Missing required columns"):
        add_vwap_relation_baseline(df.drop(columns=["vwap"]))
    pd.testing.assert_frame_equal(df, original)


def test_ema_relation_baseline_maps_relation_and_validates_columns() -> None:
    df = sample_feature_frame()
    original = df.copy(deep=True)

    result = add_ema_relation_baseline(df)

    assert result["baseline_ema_relation"].tolist() == [1, -1, 0, 0, -1]
    with pytest.raises(ValueError, match="Missing required columns"):
        add_ema_relation_baseline(df.drop(columns=["ema_9"]))
    pd.testing.assert_frame_equal(df, original)


def test_trailing_break_baseline_maps_events_and_validates_columns() -> None:
    df = sample_feature_frame()
    original = df.copy(deep=True)

    result = add_trailing_break_baseline(df)

    assert result["baseline_trailing_break"].tolist() == [1, -1, 0, 0, 0]
    with pytest.raises(ValueError, match="Missing required columns"):
        add_trailing_break_baseline(df.drop(columns=["breaks_above_trailing_high_20"]))
    pd.testing.assert_frame_equal(df, original)


def test_add_basic_baselines_adds_available_optional_baselines_without_mutation() -> None:
    df = sample_feature_frame()
    original = df.copy(deep=True)

    result = add_basic_baselines(df, random_seed=7, neutral_probability=0.1)

    assert "baseline_always_long" in result.columns
    assert "baseline_always_short" in result.columns
    assert "baseline_random_direction" in result.columns
    assert "baseline_vwap_relation" in result.columns
    assert "baseline_ema_relation" in result.columns
    assert "baseline_trailing_break" in result.columns
    pd.testing.assert_frame_equal(df, original)


def test_add_basic_baselines_skips_missing_optional_baselines() -> None:
    df = pd.DataFrame({"close": [100.0, 101.0]}, index=pd.Index(["a", "b"], name="row"))

    result = add_basic_baselines(df, include_random=False)

    assert "baseline_always_long" in result.columns
    assert "baseline_always_short" in result.columns
    assert "baseline_random_direction" not in result.columns
    assert "baseline_vwap_relation" not in result.columns
    assert "baseline_ema_relation" not in result.columns
    assert "baseline_trailing_break" not in result.columns
