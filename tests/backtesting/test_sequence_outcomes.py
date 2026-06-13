from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from spy_edge_research.backtesting import (
    compare_sequence_vs_component_events,
    filter_sequences_by_support,
    rank_event_sequences_by_expectancy,
    summarize_sequence_forward_returns,
)


def sample_sequence_outcome_frame() -> pd.DataFrame:
    sequence_a = "event_vwap_reclaim_bullish>event_trailing_breakout_20"
    sequence_b = "event_vwap_loss_bearish"
    return pd.DataFrame(
        {
            "recent_event_sequence_3": [
                sequence_a,
                sequence_b,
                sequence_a,
                "",
                sequence_b,
                sequence_a,
                "event_other",
            ],
            "event_vwap_reclaim_bullish": [True, False, True, False, False, True, False],
            "event_trailing_breakout_20": [True, False, True, False, False, True, False],
            "event_vwap_loss_bearish": [False, True, False, False, True, False, False],
            "directional_forward_return_5m": [0.020, -0.010, 0.030, 0.000, 0.015, np.nan, -0.020],
            "directional_forward_mfe_5m": [0.030, 0.005, 0.040, 0.001, 0.025, np.nan, 0.004],
        },
        index=pd.Index(["a", "b", "c", "d", "e", "f", "g"], name="row"),
    )


def test_summarize_sequence_forward_returns_compares_sequences_to_baseline() -> None:
    df = sample_sequence_outcome_frame()
    original = df.copy(deep=True)
    sequence = "event_vwap_reclaim_bullish>event_trailing_breakout_20"

    result = summarize_sequence_forward_returns(
        df,
        "recent_event_sequence_3",
        ["directional_forward_return_5m", "directional_forward_mfe_5m"],
        sequences=[sequence],
    )

    assert result["outcome_column"].tolist() == [
        "directional_forward_return_5m",
        "directional_forward_mfe_5m",
    ]
    row = result.loc[result["outcome_column"] == "directional_forward_return_5m"].iloc[0]
    assert row["event_sequence"] == sequence
    assert row["sequence_count"] == 2
    assert row["baseline_count"] == 6
    assert row["sequence_rate"] == pytest.approx(3 / 7)
    assert row["sequence_expectancy"] == pytest.approx((0.020 + 0.030) / 2)
    assert row["baseline_expectancy"] == pytest.approx(
        (0.020 - 0.010 + 0.030 + 0.000 + 0.015 - 0.020) / 6
    )
    assert row["sequence_hit_rate"] == pytest.approx(1.0)
    assert row["baseline_hit_rate"] == pytest.approx(3 / 6)
    assert row["sample_size_flag"] == "ok"
    pd.testing.assert_frame_equal(df, original)


def test_summarize_sequence_forward_returns_flags_small_and_empty_samples() -> None:
    df = sample_sequence_outcome_frame()

    small = summarize_sequence_forward_returns(
        df,
        "recent_event_sequence_3",
        ["directional_forward_return_5m"],
        sequences=["event_vwap_loss_bearish"],
        min_occurrences=3,
    ).iloc[0]
    assert small["sequence_count"] == 2
    assert small["sample_size_flag"] == "small_sample"
    assert np.isnan(small["sequence_expectancy"])
    assert not np.isnan(small["baseline_expectancy"])

    empty = summarize_sequence_forward_returns(
        df,
        "recent_event_sequence_3",
        ["directional_forward_return_5m"],
        sequences=["event_missing_sequence"],
        min_occurrences=2,
    ).iloc[0]
    assert empty["sequence_count"] == 0
    assert empty["sample_size_flag"] == "no_events"


def test_compare_sequence_vs_component_events_returns_sequence_and_components() -> None:
    df = sample_sequence_outcome_frame()
    sequence = "event_vwap_reclaim_bullish>event_trailing_breakout_20"

    result = compare_sequence_vs_component_events(
        df,
        "recent_event_sequence_3",
        sequence,
        "directional_forward_return_5m",
    )

    assert result["comparison_type"].tolist() == [
        "sequence",
        "component_event",
        "component_event",
    ]
    assert result["comparison_name"].tolist() == [
        sequence,
        "event_vwap_reclaim_bullish",
        "event_trailing_breakout_20",
    ]
    assert result["sequence_count"].tolist() == [2, 2, 2]
    assert result["sequence_expectancy"].tolist() == pytest.approx([0.025, 0.025, 0.025])


def test_filter_and_rank_event_sequences_by_support() -> None:
    df = sample_sequence_outcome_frame()
    table = summarize_sequence_forward_returns(
        df,
        "recent_event_sequence_3",
        ["directional_forward_return_5m"],
        include_empty_sequence=True,
    )

    filtered = filter_sequences_by_support(table, min_occurrences=2, min_baseline_count=6)
    assert set(filtered["event_sequence"]) == {
        "event_vwap_reclaim_bullish>event_trailing_breakout_20",
        "event_vwap_loss_bearish",
    }

    ranked = rank_event_sequences_by_expectancy(
        table,
        sort_by="expectancy_difference",
        min_occurrences=1,
    )
    assert ranked["research_rank"].tolist() == list(range(1, len(ranked) + 1))
    assert ranked["expectancy_difference"].dropna().is_monotonic_decreasing


def test_sequence_outcome_helpers_validate_inputs() -> None:
    df = sample_sequence_outcome_frame()

    with pytest.raises(ValueError, match="Missing required columns"):
        summarize_sequence_forward_returns(df, "missing_sequence", ["directional_forward_return_5m"])
    with pytest.raises(ValueError, match="Missing required columns"):
        summarize_sequence_forward_returns(df, "recent_event_sequence_3", ["missing_outcome"])
    with pytest.raises(ValueError, match="min_occurrences"):
        summarize_sequence_forward_returns(
            df,
            "recent_event_sequence_3",
            ["directional_forward_return_5m"],
            min_occurrences=0,
        )
    with pytest.raises(ValueError, match="sequence_value"):
        compare_sequence_vs_component_events(
            df,
            "recent_event_sequence_3",
            "",
            "directional_forward_return_5m",
        )
    with pytest.raises(ValueError, match="Missing required columns"):
        rank_event_sequences_by_expectancy(pd.DataFrame({"sequence_count": [1]}))


def test_sequence_outcome_helpers_do_not_create_signal_columns() -> None:
    df = sample_sequence_outcome_frame()

    result = summarize_sequence_forward_returns(
        df,
        "recent_event_sequence_3",
        ["directional_forward_return_5m"],
    )
    comparison = compare_sequence_vs_component_events(
        df,
        "recent_event_sequence_3",
        "event_vwap_reclaim_bullish>event_trailing_breakout_20",
        "directional_forward_return_5m",
    )

    forbidden = ("buy", "sell", "entry", "exit", "confidence", "signal")
    assert not any(word in column for column in result.columns for word in forbidden)
    assert not any(word in column for column in comparison.columns for word in forbidden)
