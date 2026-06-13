from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from spy_edge_research.backtesting import (
    filter_event_contexts_by_sample_size,
    group_event_outcomes_by_context,
    rank_conditional_event_edges,
    summarize_conditional_event_edge,
)
from spy_edge_research.signal_engine import build_named_event_catalog


def sample_conditional_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "event_vwap_reclaim_bullish": [True, False, True, False, True, False, False],
            "event_vwap_loss_bearish": [False, True, False, True, False, True, False],
            "vwap_regime": ["above", "above", "below", "below", "above", "below", "above"],
            "volatility_regime": ["low", "high", "low", "high", "low", "high", "low"],
            "directional_forward_return_5m": [0.020, -0.010, -0.030, 0.015, 0.025, 0.010, np.nan],
            "directional_forward_mfe_5m": [0.030, 0.005, 0.004, 0.025, 0.035, 0.020, np.nan],
        },
        index=pd.Index(["a", "b", "c", "d", "e", "f", "g"], name="row"),
    )


def test_group_event_outcomes_by_context_uses_context_local_baseline() -> None:
    df = sample_conditional_frame()
    original = df.copy(deep=True)

    result = group_event_outcomes_by_context(
        df,
        "event_vwap_reclaim_bullish",
        "directional_forward_return_5m",
        ["vwap_regime"],
        event_family="vwap",
        event_direction="long",
    )

    assert result["context_key"].tolist() == ["vwap_regime=above", "vwap_regime=below"]
    assert result["context_sample_count"].tolist() == [4, 3]
    above = result.loc[result["vwap_regime"] == "above"].iloc[0]
    below = result.loc[result["vwap_regime"] == "below"].iloc[0]
    assert above["event_count"] == 2
    assert above["baseline_count"] == 3
    assert above["event_expectancy"] == pytest.approx((0.020 + 0.025) / 2)
    assert above["baseline_expectancy"] == pytest.approx((0.020 - 0.010 + 0.025) / 3)
    assert above["expectancy_difference"] == pytest.approx(
        ((0.020 + 0.025) / 2) - ((0.020 - 0.010 + 0.025) / 3)
    )
    assert above["sample_size_flag"] == "ok"
    assert below["event_count"] == 1
    assert below["baseline_count"] == 3
    pd.testing.assert_frame_equal(df, original)


def test_summarize_conditional_event_edge_uses_catalog_outcomes_and_multiple_contexts() -> None:
    df = sample_conditional_frame()
    catalog = build_named_event_catalog(
        event_columns=["event_vwap_reclaim_bullish", "event_vwap_loss_bearish"]
    )

    result = summarize_conditional_event_edge(
        df,
        catalog,
        ["directional_forward_return_5m", "directional_forward_mfe_5m"],
        ["vwap_regime", "volatility_regime"],
        min_events=1,
    )

    assert {
        "context_key",
        "context_sample_count",
        "vwap_regime",
        "volatility_regime",
        "event_column",
        "outcome_column",
        "event_count",
        "baseline_count",
        "sample_size_flag",
    }.issubset(result.columns)
    assert len(result) == 16
    assert result["event_family"].unique().tolist() == ["vwap"]
    assert set(result["event_direction"]) == {"long", "short"}
    assert "vwap_regime=above|volatility_regime=low" in result["context_key"].tolist()


def test_filter_event_contexts_by_sample_size_keeps_supported_rows() -> None:
    df = sample_conditional_frame()
    table = group_event_outcomes_by_context(
        df,
        "event_vwap_reclaim_bullish",
        "directional_forward_return_5m",
        ["vwap_regime"],
    )

    filtered = filter_event_contexts_by_sample_size(
        table,
        min_events=2,
        min_baseline_count=3,
    )

    assert filtered["vwap_regime"].tolist() == ["above"]
    assert filtered["event_count"].tolist() == [2]


def test_rank_conditional_event_edges_sorts_stably_after_optional_filtering() -> None:
    df = sample_conditional_frame()
    catalog = build_named_event_catalog(
        event_columns=["event_vwap_reclaim_bullish", "event_vwap_loss_bearish"]
    )
    table = summarize_conditional_event_edge(
        df,
        catalog,
        ["directional_forward_return_5m"],
        ["vwap_regime"],
    )

    ranked = rank_conditional_event_edges(
        table,
        sort_by="expectancy_difference",
        min_events=1,
    )

    assert ranked["research_rank"].tolist() == list(range(1, len(ranked) + 1))
    assert ranked["expectancy_difference"].dropna().is_monotonic_decreasing
    assert (ranked["event_count"] >= 1).all()


def test_conditional_event_study_helpers_validate_inputs() -> None:
    df = sample_conditional_frame()
    catalog = build_named_event_catalog(event_columns=["event_vwap_reclaim_bullish"])

    with pytest.raises(ValueError, match="Missing required columns"):
        group_event_outcomes_by_context(
            df,
            "missing_event",
            "directional_forward_return_5m",
            ["vwap_regime"],
        )
    with pytest.raises(ValueError, match="Missing required columns"):
        summarize_conditional_event_edge(
            df,
            catalog,
            ["missing_outcome"],
            ["vwap_regime"],
        )
    with pytest.raises(ValueError, match="context_columns"):
        group_event_outcomes_by_context(
            df,
            "event_vwap_reclaim_bullish",
            "directional_forward_return_5m",
            [],
        )
    with pytest.raises(ValueError, match="min_events"):
        filter_event_contexts_by_sample_size(pd.DataFrame(), min_events=0)
    with pytest.raises(ValueError, match="Missing required columns"):
        rank_conditional_event_edges(pd.DataFrame({"event_count": [1]}), sort_by="missing")


def test_conditional_event_study_outputs_do_not_create_signal_columns() -> None:
    df = sample_conditional_frame()
    catalog = build_named_event_catalog(
        event_columns=["event_vwap_reclaim_bullish", "event_vwap_loss_bearish"]
    )

    result = summarize_conditional_event_edge(
        df,
        catalog,
        ["directional_forward_return_5m"],
        ["vwap_regime"],
    )
    ranked = rank_conditional_event_edges(result)

    forbidden = ("buy", "sell", "entry", "exit", "confidence", "signal")
    assert not any(word in column for column in result.columns for word in forbidden)
    assert not any(word in column for column in ranked.columns for word in forbidden)
