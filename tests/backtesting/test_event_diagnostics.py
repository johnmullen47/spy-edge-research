from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from spy_edge_research.backtesting.event_diagnostics import (
    add_event_sample_size_flags,
    diagnose_event_study,
    event_coverage_summary,
    grouped_event_study_summary,
    label_coverage_summary,
    validate_event_study_results,
)


def sample_event_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "event_vwap_reclaim_bullish": [True, False, True, None, False],
            "event_vwap_loss_bearish": [False, True, False, False, None],
            "forward_return_5m": [0.01, None, -0.02, 0.03, None],
            "forward_direction_5m": [1, None, -1, 1, None],
        },
        index=pd.Index(["a", "b", "c", "d", "e"], name="row"),
    )


def sample_event_study_results() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "event_column": [
                "event_vwap_reclaim_bullish",
                "event_vwap_loss_bearish",
                "event_prior_day_high_break_above",
            ],
            "event_family": ["vwap", "vwap", "zone"],
            "event_direction": ["long", "short", "long"],
            "label_column": [
                "forward_return_5m",
                "forward_return_5m",
                "forward_direction_5m",
            ],
            "event_count": [12, 3, 8],
            "event_rate": [0.30, 0.08, 0.20],
            "label_mean_on_event": [0.004, -0.002, 0.100],
            "overall_label_mean": [0.001, 0.001, 0.020],
            "difference_from_overall": [0.003, -0.003, 0.080],
        }
    )


def test_validate_event_study_results_accepts_valid_milestone_11_results() -> None:
    results = sample_event_study_results()

    validated = validate_event_study_results(results)

    pd.testing.assert_frame_equal(validated, results)
    assert validated is not results


def test_validate_event_study_results_raises_when_required_columns_are_missing() -> None:
    results = sample_event_study_results().drop(columns=["event_count"])

    with pytest.raises(ValueError, match="Missing required columns"):
        validate_event_study_results(results)


def test_validate_event_study_results_raises_on_invalid_event_rate_values() -> None:
    results = sample_event_study_results()
    results.loc[0, "event_rate"] = 1.2

    with pytest.raises(ValueError, match="event_rate"):
        validate_event_study_results(results)


def test_add_event_sample_size_flags_adds_has_min_events_correctly() -> None:
    result = add_event_sample_size_flags(sample_event_study_results(), min_events=8)

    assert result["has_min_events"].tolist() == [True, False, True]
    assert result["sample_size_warning"].tolist() == [
        "",
        "event_count_below_minimum",
        "",
    ]


def test_add_event_sample_size_flags_adds_min_event_rate_when_requested() -> None:
    result = add_event_sample_size_flags(
        sample_event_study_results(),
        min_events=1,
        min_event_rate=0.10,
    )

    assert result["has_min_event_rate"].tolist() == [True, False, True]
    assert result["sample_size_warning"].tolist() == [
        "",
        "event_rate_below_minimum",
        "",
    ]


def test_add_event_sample_size_flags_does_not_filter_rank_or_sort_rows_by_outcome() -> None:
    results = sample_event_study_results()

    flagged = add_event_sample_size_flags(results, min_events=1)

    assert flagged["event_column"].tolist() == results["event_column"].tolist()
    assert flagged["difference_from_overall"].tolist() == results[
        "difference_from_overall"
    ].tolist()
    assert len(flagged) == len(results)


def test_label_coverage_summary_computes_missing_and_non_missing_counts() -> None:
    summary = label_coverage_summary(
        sample_event_frame(),
        ["forward_return_5m", "forward_direction_5m"],
    )

    assert summary["label_column"].tolist() == [
        "forward_return_5m",
        "forward_direction_5m",
    ]
    assert summary["row_count"].tolist() == [5, 5]
    assert summary["non_missing_count"].tolist() == [3, 3]
    assert summary["missing_count"].tolist() == [2, 2]
    assert summary["non_missing_rate"].tolist() == [0.6, 0.6]
    assert summary["missing_rate"].tolist() == [0.4, 0.4]


def test_event_coverage_summary_computes_true_false_and_missing_counts() -> None:
    summary = event_coverage_summary(
        sample_event_frame(),
        ["event_vwap_reclaim_bullish", "event_vwap_loss_bearish"],
    )

    assert summary["event_column"].tolist() == [
        "event_vwap_reclaim_bullish",
        "event_vwap_loss_bearish",
    ]
    assert summary["row_count"].tolist() == [5, 5]
    assert summary["true_count"].tolist() == [2, 1]
    assert summary["false_count"].tolist() == [2, 3]
    assert summary["missing_count"].tolist() == [1, 1]
    assert summary["true_rate"].tolist() == [0.4, 0.2]
    assert summary["missing_rate"].tolist() == [0.2, 0.2]


def test_event_coverage_summary_raises_on_missing_event_columns() -> None:
    with pytest.raises(ValueError, match="Missing required columns"):
        event_coverage_summary(sample_event_frame(), ["missing_event"])


def test_grouped_event_study_summary_groups_by_event_family_correctly() -> None:
    summary = grouped_event_study_summary(sample_event_study_results(), ["event_family"])

    assert summary["event_family"].tolist() == ["vwap", "zone"]
    assert summary["row_count"].tolist() == [2, 1]
    assert summary["total_event_count"].tolist() == [15, 8]
    assert summary["mean_event_rate"].tolist() == [pytest.approx(0.19), 0.20]


def test_grouped_event_study_summary_groups_by_direction_and_label_column() -> None:
    summary = grouped_event_study_summary(
        sample_event_study_results(),
        ["event_direction", "label_column"],
    )

    assert summary["event_direction"].tolist() == ["long", "long", "short"]
    assert summary["label_column"].tolist() == [
        "forward_direction_5m",
        "forward_return_5m",
        "forward_return_5m",
    ]
    assert summary["total_event_count"].tolist() == [8, 12, 3]


def test_grouped_event_study_summary_sorts_only_by_group_keys_not_performance() -> None:
    results = sample_event_study_results().iloc[[2, 1, 0]].reset_index(drop=True)

    summary = grouped_event_study_summary(results, ["event_family"])

    assert summary["event_family"].tolist() == ["vwap", "zone"]
    assert summary["mean_difference_from_overall"].tolist() == [
        pytest.approx(0.0),
        0.080,
    ]


def test_diagnose_event_study_returns_expected_dictionary_keys() -> None:
    diagnostics = diagnose_event_study(
        sample_event_frame(),
        sample_event_study_results(),
        label_columns=["forward_return_5m"],
        event_columns=["event_vwap_reclaim_bullish"],
        group_columns=["event_family"],
    )

    assert list(diagnostics) == [
        "results_with_sample_flags",
        "label_coverage",
        "event_coverage",
        "grouped_summary",
    ]


def test_diagnose_event_study_does_not_mutate_input_feature_dataframe() -> None:
    df = sample_event_frame()
    original = df.copy(deep=True)

    diagnose_event_study(df, sample_event_study_results(), label_columns=["forward_return_5m"])

    pd.testing.assert_frame_equal(df, original)


def test_diagnose_event_study_does_not_mutate_input_results_dataframe() -> None:
    results = sample_event_study_results()
    original = results.copy(deep=True)

    diagnose_event_study(sample_event_frame(), results, label_columns=["forward_return_5m"])

    pd.testing.assert_frame_equal(results, original)


def test_diagnostics_do_not_create_buy_sell_entry_or_exit_columns() -> None:
    diagnostics = diagnose_event_study(
        sample_event_frame(),
        sample_event_study_results(),
        label_columns=["forward_return_5m"],
        event_columns=["event_vwap_reclaim_bullish"],
        group_columns=["event_family"],
    )

    forbidden = ("buy", "sell", "entry", "exit")
    for output in diagnostics.values():
        assert not any(word in column for column in output.columns for word in forbidden)


def test_diagnostics_do_not_create_confidence_score_rank_or_edge_columns() -> None:
    diagnostics = diagnose_event_study(
        sample_event_frame(),
        sample_event_study_results(),
        label_columns=["forward_return_5m"],
        event_columns=["event_vwap_reclaim_bullish"],
        group_columns=["event_family"],
    )

    forbidden = ("confidence", "score", "rank", "edge")
    for output in diagnostics.values():
        assert not any(word in column for column in output.columns for word in forbidden)


def test_diagnostics_do_not_import_or_call_feature_generation_modules() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    diagnostics_text = (
        repo_root / "src/spy_edge_research/backtesting/event_diagnostics.py"
    ).read_text()
    forbidden_imports = (
        "spy_edge_research.signal_engine",
        "spy_edge_research.indicators",
        "spy_edge_research.market_structure",
        "spy_edge_research.market_regime",
        "spy_edge_research.support_resistance",
    )

    assert not any(forbidden in diagnostics_text for forbidden in forbidden_imports)
