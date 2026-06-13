from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from spy_edge_research.backtesting import (
    evaluate_event_catalog,
    evaluate_event_column,
    evaluate_named_events,
    event_frequency_summary,
    event_regime_summary,
)
from spy_edge_research.signal_engine import build_named_event_catalog


def sample_event_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "event_vwap_reclaim_bullish": [True, True, False, False, True],
            "event_vwap_loss_bearish": [False, True, True, False, False],
            "event_any_support_retest_touch": [False, False, False, False, False],
            "event_forward_label_leak": [True, True, True, True, True],
            "directional_regime": ["up", "range", "up", "down", "range"],
            "forward_return_5m": [0.02, -0.01, 0.03, -0.02, 0.00],
            "forward_direction_5m": [1, -1, 1, -1, 0],
        },
        index=pd.Index(["a", "b", "c", "d", "e"], name="row"),
    )


def test_evaluate_event_column_computes_counts_rates_and_label_means() -> None:
    df = sample_event_frame()
    original = df.copy(deep=True)

    result = evaluate_event_column(
        df,
        "event_vwap_reclaim_bullish",
        ["forward_return_5m", "forward_direction_5m"],
    )

    assert result["label_column"].tolist() == [
        "forward_return_5m",
        "forward_direction_5m",
    ]
    row = result.loc[result["label_column"] == "forward_return_5m"].iloc[0]
    assert row["event_count"] == 3
    assert row["event_rate"] == pytest.approx(0.6)
    assert row["label_mean_on_event"] == pytest.approx((0.02 - 0.01 + 0.0) / 3)
    assert row["overall_label_mean"] == pytest.approx(0.004)
    assert row["difference_from_overall"] == pytest.approx(
        ((0.02 - 0.01 + 0.0) / 3) - 0.004
    )
    pd.testing.assert_frame_equal(df, original)


def test_evaluate_event_column_handles_empty_no_event_and_min_event_cases() -> None:
    df = sample_event_frame()

    no_events = evaluate_event_column(
        df,
        "event_any_support_retest_touch",
        ["forward_return_5m"],
    ).iloc[0]
    assert no_events["event_count"] == 0
    assert no_events["event_rate"] == 0.0
    assert np.isnan(no_events["label_mean_on_event"])
    assert np.isnan(no_events["difference_from_overall"])

    min_events = evaluate_event_column(
        df,
        "event_vwap_loss_bearish",
        ["forward_return_5m"],
        min_events=3,
    ).iloc[0]
    assert min_events["event_count"] == 2
    assert np.isnan(min_events["label_mean_on_event"])

    empty = evaluate_event_column(
        df.iloc[0:0].copy(),
        "event_vwap_reclaim_bullish",
        ["forward_return_5m"],
    ).iloc[0]
    assert empty["event_count"] == 0
    assert np.isnan(empty["event_rate"])
    assert np.isnan(empty["overall_label_mean"])


def test_evaluate_event_column_validates_inputs() -> None:
    df = sample_event_frame()

    with pytest.raises(ValueError, match="Missing required columns"):
        evaluate_event_column(df, "missing_event", ["forward_return_5m"])
    with pytest.raises(ValueError, match="Missing required columns"):
        evaluate_event_column(df, "event_vwap_reclaim_bullish", ["missing_label"])
    with pytest.raises(ValueError, match="min_events"):
        evaluate_event_column(
            df,
            "event_vwap_reclaim_bullish",
            ["forward_return_5m"],
            min_events=0,
        )


def test_evaluate_event_catalog_returns_expected_rows_with_metadata() -> None:
    df = sample_event_frame()
    catalog = build_named_event_catalog(
        event_columns=[
            "event_vwap_reclaim_bullish",
            "event_vwap_loss_bearish",
            "event_any_support_retest_touch",
        ]
    )

    result = evaluate_event_catalog(
        df,
        catalog,
        ["forward_return_5m", "forward_direction_5m"],
    )

    assert len(result) == 6
    assert result["event_column"].tolist() == [
        "event_vwap_reclaim_bullish",
        "event_vwap_reclaim_bullish",
        "event_vwap_loss_bearish",
        "event_vwap_loss_bearish",
        "event_any_support_retest_touch",
        "event_any_support_retest_touch",
    ]
    assert result["event_family"].tolist()[:2] == ["vwap", "vwap"]
    assert result["event_direction"].tolist()[:4] == ["long", "long", "short", "short"]


def test_evaluate_named_events_builds_or_validates_catalog() -> None:
    df = sample_event_frame()
    original = df.copy(deep=True)

    built = evaluate_named_events(
        df,
        ["forward_return_5m"],
        event_columns=["event_vwap_reclaim_bullish", "event_vwap_loss_bearish"],
    )
    catalog = build_named_event_catalog(event_columns=["event_vwap_reclaim_bullish"])
    provided = evaluate_named_events(df, ["forward_return_5m"], catalog=catalog)

    assert built["event_column"].tolist() == [
        "event_vwap_reclaim_bullish",
        "event_vwap_loss_bearish",
    ]
    assert provided["event_column"].tolist() == ["event_vwap_reclaim_bullish"]
    pd.testing.assert_frame_equal(df, original)


def test_event_frequency_summary_works_without_labels() -> None:
    df = sample_event_frame()[[
        "event_vwap_reclaim_bullish",
        "event_vwap_loss_bearish",
        "directional_regime",
    ]].copy()
    catalog = build_named_event_catalog(df=df)
    original = df.copy(deep=True)

    result = event_frequency_summary(df, catalog)

    assert result["event_column"].tolist() == [
        "event_vwap_reclaim_bullish",
        "event_vwap_loss_bearish",
    ]
    assert result["event_count"].tolist() == [3, 2]
    assert result["event_rate"].tolist() == [0.6, 0.4]
    pd.testing.assert_frame_equal(df, original)


def test_event_regime_summary_groups_by_existing_regime_column() -> None:
    df = sample_event_frame()
    catalog = build_named_event_catalog(event_columns=["event_vwap_reclaim_bullish"])
    original = df.copy(deep=True)

    result = event_regime_summary(df, catalog, "directional_regime")

    assert result["regime"].tolist() == ["up", "range", "down"]
    assert result["regime_count"].tolist() == [2, 2, 1]
    assert result["event_count"].tolist() == [1, 2, 0]
    assert result["event_rate"].tolist() == [0.5, 1.0, 0.0]
    pd.testing.assert_frame_equal(df, original)

    with pytest.raises(ValueError, match="Missing required columns"):
        event_regime_summary(df.drop(columns=["directional_regime"]), catalog, "directional_regime")


def test_label_isolation_boundary_and_catalog_label_exclusion() -> None:
    df = sample_event_frame()
    no_label_df = df.drop(columns=["forward_return_5m", "forward_direction_5m"])

    catalog = build_named_event_catalog(df=df)
    assert "event_forward_label_leak" not in catalog["event_column"].tolist()

    frequency = event_frequency_summary(no_label_df, build_named_event_catalog(df=no_label_df))
    regime = event_regime_summary(
        no_label_df,
        build_named_event_catalog(event_columns=["event_vwap_reclaim_bullish"]),
        "directional_regime",
    )
    assert frequency["event_count"].tolist() == [3, 2, 0]
    assert regime["event_count"].sum() == 3

    with pytest.raises(ValueError, match="Missing required columns"):
        evaluate_event_column(
            no_label_df,
            "event_vwap_reclaim_bullish",
            ["forward_return_5m"],
        )


def test_no_feature_generation_imports_event_study_or_introduces_backward_shift() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    feature_files = [
        *repo_root.glob("src/spy_edge_research/indicators/*.py"),
        *repo_root.glob("src/spy_edge_research/market_data/*.py"),
        *repo_root.glob("src/spy_edge_research/market_regime/*.py"),
        *repo_root.glob("src/spy_edge_research/market_structure/*.py"),
        *repo_root.glob("src/spy_edge_research/signal_engine/*.py"),
        *repo_root.glob("src/spy_edge_research/support_resistance/*.py"),
    ]
    non_evaluation_shift_files = []
    for path in feature_files:
        text = path.read_text()
        if path.name != "__init__.py":
            assert "event_study" not in text
        if path.name not in {"labels.py", "event_study.py"} and "shift(-" in text:
            non_evaluation_shift_files.append(path.name)
    assert non_evaluation_shift_files == []


def test_event_study_outputs_do_not_create_trading_signal_columns() -> None:
    df = sample_event_frame()
    catalog = build_named_event_catalog(
        event_columns=["event_vwap_reclaim_bullish", "event_vwap_loss_bearish"]
    )

    outputs = [
        evaluate_event_catalog(df, catalog, ["forward_return_5m"]),
        evaluate_named_events(df, ["forward_return_5m"], catalog=catalog),
        event_frequency_summary(df, catalog),
        event_regime_summary(df, catalog, "directional_regime"),
    ]

    forbidden = ("buy", "sell", "entry", "exit", "confidence")
    for output in outputs:
        assert not any(word in column for column in output.columns for word in forbidden)
