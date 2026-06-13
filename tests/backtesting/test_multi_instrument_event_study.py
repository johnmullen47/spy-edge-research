import pandas as pd
import pytest

from spy_edge_research.backtesting import (
    build_multi_instrument_event_outcome_table,
    build_multi_instrument_research_report,
    compare_confirmed_vs_divergent_event_outcomes,
    summarize_event_by_instrument_context,
    summarize_multi_instrument_context_coverage,
)


def _df():
    return pd.DataFrame(
        {
            "event_vwap_reclaim": [1, 0, 1, 1, 0, 1],
            "forward_return_5m": [0.3, -0.1, 0.2, -0.4, 0.1, 0.5],
            "cross_trend_context": [
                "confirmed",
                "confirmed",
                "divergent",
                "divergent",
                "neutral",
                "confirmed",
            ],
        }
    )


def _catalog():
    return pd.DataFrame(
        {
            "event_column": ["event_vwap_reclaim"],
            "event_name": ["event_vwap_reclaim"],
            "event_family": ["vwap"],
            "event_direction": ["long"],
            "is_directional": [True],
        }
    )


def test_summarize_event_by_instrument_context_includes_caveats_and_samples():
    summary = summarize_event_by_instrument_context(
        _df(),
        "event_vwap_reclaim",
        "forward_return_5m",
        ["cross_trend_context"],
        min_events=2,
    )

    confirmed = summary.set_index("cross_trend_context").loc["confirmed"]
    neutral = summary.set_index("cross_trend_context").loc["neutral"]

    assert confirmed["event_count"] == 2
    assert confirmed["event_expectancy"] == pytest.approx(0.4)
    assert neutral["sample_size_flag"] == "no_events"
    assert summary["study_caveat"].eq("multi_instrument_event_study_is_descriptive_research_only").all()


def test_compare_confirmed_vs_divergent_event_outcomes_is_descriptive():
    summary = summarize_event_by_instrument_context(
        _df(),
        "event_vwap_reclaim",
        "forward_return_5m",
        ["cross_trend_context"],
    )

    comparison = compare_confirmed_vs_divergent_event_outcomes(summary)

    assert comparison.loc[0, "confirmed_event_count"] == 2
    assert comparison.loc[0, "divergent_event_count"] == 2
    assert comparison.loc[0, "comparison_caveat"] == "descriptive_context_comparison_not_edge_claim"


def test_build_multi_instrument_event_outcome_table_uses_catalog_metadata():
    table = build_multi_instrument_event_outcome_table(
        _df(),
        _catalog(),
        ["forward_return_5m"],
        ["cross_trend_context"],
    )

    assert set(table["event_family"]) == {"vwap"}
    assert set(table["event_direction"]) == {"long"}
    assert set(table["cross_trend_context"]) == {"confirmed", "divergent", "neutral"}


def test_context_coverage_flags_low_sample_contexts():
    coverage = summarize_multi_instrument_context_coverage(
        _df(),
        ["cross_trend_context"],
        min_context_rows=2,
    )

    neutral = coverage.set_index("context_key").loc["cross_trend_context=neutral"]
    assert neutral["context_sample_flag"] == "small_context_sample"
    assert "__missing_context_rows__" in set(coverage["context_key"])


def test_research_report_packages_tables_without_trade_language():
    report = build_multi_instrument_research_report(
        _df(),
        _catalog(),
        ["forward_return_5m"],
        ["cross_trend_context"],
    )

    assert set(report) == {
        "metadata",
        "context_coverage",
        "event_outcomes",
        "confirmed_vs_divergent",
    }
    assert report["metadata"]["forward_outcomes_are_evaluation_only"] is True
    columns = list(report["event_outcomes"].columns)
    assert not any(term in column.lower() for column in columns for term in ["buy", "sell", "entry", "exit"])


def test_missing_required_columns_raise_clear_errors():
    with pytest.raises(ValueError, match="Missing required columns"):
        summarize_event_by_instrument_context(
            _df().drop(columns=["cross_trend_context"]),
            "event_vwap_reclaim",
            "forward_return_5m",
            ["cross_trend_context"],
        )
