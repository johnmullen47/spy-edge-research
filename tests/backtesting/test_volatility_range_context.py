from __future__ import annotations

import pandas as pd
import pytest

from spy_edge_research.backtesting import (
    calculate_intraday_realized_volatility,
    calculate_range_expansion_features,
    summarize_event_by_range_context,
    summarize_event_by_volatility_context,
)
from spy_edge_research.signal_engine import build_named_event_catalog


def sample_context_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "timestamp": pd.date_range("2024-01-02 09:31", periods=6, freq="1min"),
            "high": [101.0, 102.0, 104.0, 101.0, 103.0, 106.0],
            "low": [100.0, 100.0, 100.0, 100.0, 100.0, 101.0],
            "close": [100.0, 101.0, 99.0, 104.0, 103.0, 110.0],
            "event_vwap_reclaim_bullish": [False, True, True, False, True, False],
            "event_vwap_loss_bearish": [False, False, False, True, False, True],
            "directional_forward_return_5m": [0.010, 0.020, -0.010, 0.030, 0.000, -0.020],
            "volatility_context_2": [
                "unknown",
                "unknown",
                "normal",
                "high_volatility",
                "low_volatility",
                "normal",
            ],
        },
        index=pd.Index(["a", "b", "c", "d", "e", "f"], name="row"),
    )


def test_calculate_intraday_realized_volatility_is_causal_and_non_mutating() -> None:
    df = sample_context_frame()
    original = df.copy(deep=True)

    result = calculate_intraday_realized_volatility(df, window=2)
    changed_future = df.copy(deep=True)
    changed_future.loc["f", "close"] = 150.0
    revised = calculate_intraday_realized_volatility(changed_future, window=2)

    assert "return_1b" in result.columns
    assert "realized_volatility_2" in result.columns
    assert "realized_volatility_baseline_2" in result.columns
    assert "realized_volatility_ratio_2" in result.columns
    assert "volatility_context_2" in result.columns
    pd.testing.assert_series_equal(
        result.loc["a":"e", "realized_volatility_2"],
        revised.loc["a":"e", "realized_volatility_2"],
    )
    pd.testing.assert_frame_equal(df, original)


def test_calculate_range_expansion_features_uses_prior_range_baseline() -> None:
    df = sample_context_frame()

    result = calculate_range_expansion_features(
        df,
        window=2,
        expansion_threshold=1.25,
        contraction_threshold=0.75,
    )

    assert result["bar_range"].tolist() == pytest.approx([1.0, 2.0, 4.0, 1.0, 3.0, 5.0])
    assert result["prior_range_mean_2"].tolist()[0] != result["prior_range_mean_2"].tolist()[0]
    assert result["prior_range_mean_2"].iloc[1:].tolist() == pytest.approx(
        [1.0, 1.5, 3.0, 2.5, 2.0]
    )
    assert result["range_expansion_ratio_2"].iloc[1:].tolist() == pytest.approx(
        [2.0, 4.0 / 1.5, 1.0 / 3.0, 3.0 / 2.5, 5.0 / 2.0]
    )
    assert result["range_context_2"].tolist() == [
        "unknown",
        "range_expansion",
        "range_expansion",
        "range_contraction",
        "normal",
        "range_expansion",
    ]


def test_summarize_event_by_volatility_context_uses_existing_or_generated_context() -> None:
    df = sample_context_frame()
    catalog = build_named_event_catalog(event_columns=["event_vwap_reclaim_bullish"])

    existing = summarize_event_by_volatility_context(
        df,
        catalog,
        ["directional_forward_return_5m"],
        window=2,
    )
    generated = summarize_event_by_volatility_context(
        df.drop(columns=["volatility_context_2"]),
        catalog,
        ["directional_forward_return_5m"],
        window=2,
    )

    assert "volatility_context_2" in existing.columns
    assert set(existing["volatility_context_2"]) == {
        "unknown",
        "normal",
        "high_volatility",
        "low_volatility",
    }
    assert "volatility_context_2" in generated.columns


def test_summarize_event_by_range_context_generates_context_and_summarizes_events() -> None:
    df = sample_context_frame()
    catalog = build_named_event_catalog(
        event_columns=["event_vwap_reclaim_bullish", "event_vwap_loss_bearish"]
    )

    result = summarize_event_by_range_context(
        df,
        catalog,
        ["directional_forward_return_5m"],
        window=2,
    )

    assert "range_context_2" in result.columns
    assert {"range_expansion", "range_contraction", "normal", "unknown"}.issubset(
        set(result["range_context_2"])
    )
    expansion = result.loc[
        (result["event_column"] == "event_vwap_reclaim_bullish")
        & (result["range_context_2"] == "range_expansion")
    ].iloc[0]
    assert expansion["event_count"] == 2
    assert expansion["baseline_count"] == 3


def test_volatility_range_context_helpers_validate_inputs() -> None:
    df = sample_context_frame()
    catalog = build_named_event_catalog(event_columns=["event_vwap_reclaim_bullish"])

    with pytest.raises(ValueError, match="Missing required columns"):
        calculate_intraday_realized_volatility(df.drop(columns=["close"]), window=2)
    with pytest.raises(ValueError, match="window"):
        calculate_range_expansion_features(df, window=0)
    with pytest.raises(ValueError, match="Missing required columns"):
        summarize_event_by_volatility_context(
            df.drop(columns=["close", "volatility_context_2"]),
            catalog,
            ["directional_forward_return_5m"],
            window=2,
        )
    with pytest.raises(ValueError, match="Missing required columns"):
        summarize_event_by_range_context(
            df.drop(columns=["high"]),
            catalog,
            ["directional_forward_return_5m"],
            window=2,
        )


def test_volatility_range_context_outputs_do_not_create_signal_columns() -> None:
    df = sample_context_frame()
    catalog = build_named_event_catalog(event_columns=["event_vwap_reclaim_bullish"])

    volatility = summarize_event_by_volatility_context(
        df,
        catalog,
        ["directional_forward_return_5m"],
        window=2,
    )
    range_context = summarize_event_by_range_context(
        df,
        catalog,
        ["directional_forward_return_5m"],
        window=2,
    )

    forbidden = ("buy", "sell", "entry", "exit", "confidence", "signal")
    assert not any(word in column for column in volatility.columns for word in forbidden)
    assert not any(word in column for column in range_context.columns for word in forbidden)
