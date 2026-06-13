from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from spy_edge_research.backtesting import (
    build_event_forward_return_table,
    calculate_event_expectancy,
    calculate_event_hit_rate,
    calculate_event_sample_size,
    compare_event_vs_baseline_forward_returns,
    summarize_event_forward_returns,
)
from spy_edge_research.signal_engine import build_named_event_catalog


def sample_outcome_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "event_vwap_reclaim_bullish": [True, True, False, False, True, False],
            "event_vwap_loss_bearish": [False, False, True, True, False, False],
            "event_any_support_retest_touch": [False, False, False, False, False, False],
            "forward_return_5m": [0.020, -0.010, -0.030, 0.010, 0.015, np.nan],
            "directional_forward_return_5m": [0.020, -0.010, 0.030, -0.010, 0.015, np.nan],
            "directional_forward_mfe_5m": [0.030, 0.005, 0.040, 0.008, 0.025, np.nan],
            "directional_forward_mae_5m": [-0.004, -0.020, -0.006, -0.015, -0.002, np.nan],
        },
        index=pd.Index(["a", "b", "c", "d", "e", "f"], name="row"),
    )


def test_calculate_event_sample_size_counts_valid_event_outcomes() -> None:
    df = sample_outcome_frame()

    assert calculate_event_sample_size(df, "event_vwap_reclaim_bullish") == 3
    assert (
        calculate_event_sample_size(
            df,
            "event_vwap_reclaim_bullish",
            "directional_forward_return_5m",
        )
        == 3
    )
    assert calculate_event_sample_size(df, "event_any_support_retest_touch") == 0


def test_calculate_event_expectancy_and_hit_rate_handle_empty_samples() -> None:
    outcomes = pd.Series([0.02, -0.01, np.nan, 0.03])

    assert calculate_event_expectancy(outcomes) == pytest.approx((0.02 - 0.01 + 0.03) / 3)
    assert calculate_event_hit_rate(outcomes) == pytest.approx(2 / 3)
    assert calculate_event_hit_rate(outcomes, threshold=0.01) == pytest.approx(2 / 3)
    assert np.isnan(calculate_event_expectancy(pd.Series([np.nan])))
    assert np.isnan(calculate_event_hit_rate(pd.Series([np.nan])))


def test_summarize_event_forward_returns_compares_event_to_baseline_without_mutation() -> None:
    df = sample_outcome_frame()
    original = df.copy(deep=True)

    result = summarize_event_forward_returns(
        df,
        "event_vwap_reclaim_bullish",
        ["directional_forward_return_5m", "directional_forward_mfe_5m"],
        event_family="vwap",
        event_direction="long",
    )

    assert result["outcome_column"].tolist() == [
        "directional_forward_return_5m",
        "directional_forward_mfe_5m",
    ]
    row = result.loc[result["outcome_column"] == "directional_forward_return_5m"].iloc[0]
    assert row["event_column"] == "event_vwap_reclaim_bullish"
    assert row["event_family"] == "vwap"
    assert row["event_direction"] == "long"
    assert row["event_count"] == 3
    assert row["baseline_count"] == 5
    assert row["event_rate"] == pytest.approx(3 / 6)
    assert row["event_expectancy"] == pytest.approx((0.020 - 0.010 + 0.015) / 3)
    assert row["baseline_expectancy"] == pytest.approx((0.020 - 0.010 + 0.030 - 0.010 + 0.015) / 5)
    assert row["expectancy_difference"] == pytest.approx(
        ((0.020 - 0.010 + 0.015) / 3)
        - ((0.020 - 0.010 + 0.030 - 0.010 + 0.015) / 5)
    )
    assert row["event_hit_rate"] == pytest.approx(2 / 3)
    assert row["baseline_hit_rate"] == pytest.approx(3 / 5)
    assert row["hit_rate_difference"] == pytest.approx((2 / 3) - (3 / 5))
    assert row["sample_size_flag"] == "ok"
    pd.testing.assert_frame_equal(df, original)


def test_summarize_event_forward_returns_makes_small_samples_obvious() -> None:
    df = sample_outcome_frame()

    no_events = summarize_event_forward_returns(
        df,
        "event_any_support_retest_touch",
        ["directional_forward_return_5m"],
        min_events=2,
    ).iloc[0]
    assert no_events["event_count"] == 0
    assert no_events["sample_size_flag"] == "no_events"
    assert np.isnan(no_events["event_expectancy"])
    assert np.isnan(no_events["expectancy_difference"])

    small_sample = summarize_event_forward_returns(
        df,
        "event_vwap_loss_bearish",
        ["directional_forward_return_5m"],
        min_events=3,
    ).iloc[0]
    assert small_sample["event_count"] == 2
    assert small_sample["sample_size_flag"] == "small_sample"
    assert np.isnan(small_sample["event_hit_rate"])
    assert small_sample["baseline_count"] == 5
    assert not np.isnan(small_sample["baseline_expectancy"])


def test_build_event_forward_return_table_uses_catalog_metadata() -> None:
    df = sample_outcome_frame()
    catalog = build_named_event_catalog(
        event_columns=[
            "event_vwap_reclaim_bullish",
            "event_vwap_loss_bearish",
            "event_any_support_retest_touch",
        ]
    )

    result = build_event_forward_return_table(
        df,
        catalog,
        ["directional_forward_return_5m"],
        min_events=2,
    )

    assert result["event_column"].tolist() == [
        "event_vwap_reclaim_bullish",
        "event_vwap_loss_bearish",
        "event_any_support_retest_touch",
    ]
    assert result["event_family"].tolist() == ["vwap", "vwap", "retest"]
    assert result["event_direction"].tolist() == ["long", "short", "neutral"]
    assert result["sample_size_flag"].tolist() == ["ok", "ok", "no_events"]


def test_compare_event_vs_baseline_forward_returns_returns_one_series() -> None:
    df = sample_outcome_frame()

    result = compare_event_vs_baseline_forward_returns(
        df,
        "event_vwap_loss_bearish",
        "directional_forward_return_5m",
    )

    assert result["event_column"] == "event_vwap_loss_bearish"
    assert result["outcome_column"] == "directional_forward_return_5m"
    assert result["event_count"] == 2
    assert result["event_expectancy"] == pytest.approx((0.030 - 0.010) / 2)


def test_event_forward_outcome_helpers_validate_inputs() -> None:
    df = sample_outcome_frame()

    with pytest.raises(ValueError, match="Missing required columns"):
        summarize_event_forward_returns(df, "missing_event", ["directional_forward_return_5m"])
    with pytest.raises(ValueError, match="Missing required columns"):
        summarize_event_forward_returns(df, "event_vwap_reclaim_bullish", ["missing_outcome"])
    with pytest.raises(ValueError, match="min_events"):
        summarize_event_forward_returns(
            df,
            "event_vwap_reclaim_bullish",
            ["directional_forward_return_5m"],
            min_events=0,
        )
    with pytest.raises(ValueError, match="hit_rate_threshold"):
        summarize_event_forward_returns(
            df,
            "event_vwap_reclaim_bullish",
            ["directional_forward_return_5m"],
            hit_rate_threshold=True,
        )


def test_event_forward_outcome_helpers_do_not_create_signal_columns() -> None:
    df = sample_outcome_frame()
    catalog = build_named_event_catalog(
        event_columns=["event_vwap_reclaim_bullish", "event_vwap_loss_bearish"]
    )

    result = build_event_forward_return_table(
        df,
        catalog,
        ["directional_forward_return_5m", "directional_forward_mfe_5m"],
    )

    forbidden = ("buy", "sell", "entry", "exit", "confidence", "signal")
    assert not any(word in column for column in result.columns for word in forbidden)
