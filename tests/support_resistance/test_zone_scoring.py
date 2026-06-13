from __future__ import annotations

import pandas as pd
import pytest

from spy_edge_research.support_resistance import (
    combine_zone_scores,
    score_level_recency,
    score_rejection_strength,
    score_touch_count,
)


def test_recency_score_is_between_zero_and_one_and_recent_scores_higher() -> None:
    result = score_level_recency(pd.Series([0, 50, 100, 200]), max_bars=100)

    assert result.between(0, 1).all()
    assert result.iloc[0] > result.iloc[1] > result.iloc[2]
    assert result.iloc[3] == 0


def test_touch_count_score_clips_at_one() -> None:
    result = score_touch_count(pd.Series([0, 2, 5, 10]), max_touches=5)

    assert result.tolist() == [0.0, 0.4, 1.0, 1.0]


def test_rejection_strength_score_clips_at_one() -> None:
    result = score_rejection_strength(pd.Series([0.0, 1.0, 3.0]), max_strength=2.0)

    assert result.tolist() == [0.0, 0.5, 1.0]


def test_nans_become_zero_in_component_scores() -> None:
    values = pd.Series([None, 1.0])

    assert score_level_recency(values, max_bars=10).iloc[0] == 0
    assert score_touch_count(values, max_touches=5).iloc[0] == 0
    assert score_rejection_strength(values, max_strength=2).iloc[0] == 0


def test_combined_zone_score_is_between_zero_and_one_hundred() -> None:
    index = pd.Index(["a", "b"], name="row")
    result = combine_zone_scores(
        source_quality=pd.Series([1.0, 0.5], index=index),
        recency_score=1.0,
        touch_score=0.5,
        rejection_score=0.5,
    )

    assert result.index.equals(index)
    assert result.between(0, 100).all()


def test_violation_penalty_reduces_score() -> None:
    base = combine_zone_scores(1, 1, 1, 1, volume_score=1, confluence_score=1)
    penalized = combine_zone_scores(
        1,
        1,
        1,
        1,
        volume_score=1,
        confluence_score=1,
        violation_penalty=0.25,
    )

    assert penalized.iloc[0] < base.iloc[0]


def test_invalid_weights_raise_value_error() -> None:
    with pytest.raises(ValueError, match="weights"):
        combine_zone_scores(1, 1, 1, 1, weights={"source_quality": 1.0})
    with pytest.raises(ValueError, match="non-negative"):
        combine_zone_scores(
            1,
            1,
            1,
            1,
            weights={
                "source_quality": -0.3,
                "recency_score": 0.2,
                "touch_score": 0.2,
                "rejection_score": 0.15,
                "volume_score": 0.1,
                "confluence_score": 0.65,
            },
        )
    with pytest.raises(ValueError, match="sum"):
        combine_zone_scores(
            1,
            1,
            1,
            1,
            weights={
                "source_quality": 0.3,
                "recency_score": 0.2,
                "touch_score": 0.2,
                "rejection_score": 0.15,
                "volume_score": 0.1,
                "confluence_score": 0.1,
            },
        )


def test_invalid_component_parameters_raise_value_error() -> None:
    with pytest.raises(ValueError, match="max_bars"):
        score_level_recency(pd.Series([1]), max_bars=0)
    with pytest.raises(ValueError, match="max_touches"):
        score_touch_count(pd.Series([1]), max_touches=0)
    with pytest.raises(ValueError, match="max_strength"):
        score_rejection_strength(pd.Series([1]), max_strength=0)


def test_scalar_and_series_inputs_both_work() -> None:
    scalar = combine_zone_scores(0.5, 0.5, 0.5, 0.5)
    series = combine_zone_scores(pd.Series([0.5, 1.0]), 0.5, 0.5, 0.5)

    assert scalar.tolist() == [42.5]
    assert series.tolist() == pytest.approx([42.5, 57.5])
