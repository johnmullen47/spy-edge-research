import pandas as pd
import pytest

from spy_edge_research.backtesting import (
    build_factor_event_outcome_table,
    build_factor_event_research_report,
    compare_factor_context_event_outcomes,
    summarize_event_by_factor_context,
    summarize_factor_context_coverage,
)


def _df():
    return pd.DataFrame(
        {
            "event_vwap_reclaim": [1, 0, 1, 1, 0, 1, 1],
            "forward_return_5m": [0.3, -0.1, 0.2, -0.4, 0.1, 0.5, 0.0],
            "factor_leadership_style": [
                "momentum",
                "momentum",
                "value",
                "value",
                "low_volatility",
                "momentum",
                "low_volatility",
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


def test_summarize_event_by_factor_context_includes_caveats_and_samples():
    summary = summarize_event_by_factor_context(
        _df(),
        "event_vwap_reclaim",
        "forward_return_5m",
        ["factor_leadership_style"],
        min_events=2,
    )
    momentum = summary.set_index("factor_leadership_style").loc["momentum"]
    low_vol = summary.set_index("factor_leadership_style").loc["low_volatility"]

    assert momentum["event_count"] == 2
    assert momentum["event_expectancy"] == pytest.approx(0.4)
    assert low_vol["sample_size_flag"] == "small_sample"
    assert summary["study_caveat"].eq("factor_event_study_is_descriptive_research_only").all()


def test_compare_factor_context_event_outcomes_is_descriptive():
    summary = summarize_event_by_factor_context(
        _df(),
        "event_vwap_reclaim",
        "forward_return_5m",
        ["factor_leadership_style"],
    )
    comparison = compare_factor_context_event_outcomes(summary)

    assert comparison.loc[0, "momentum_event_count"] == 2
    assert comparison.loc[0, "value_event_count"] == 2
    assert comparison.loc[0, "low_volatility_event_count"] == 1
    assert comparison.loc[0, "comparison_caveat"] == "descriptive_factor_context_comparison_not_edge_claim"


def test_build_factor_event_outcome_table_uses_catalog_metadata():
    table = build_factor_event_outcome_table(
        _df(),
        _catalog(),
        ["forward_return_5m"],
        ["factor_leadership_style"],
    )
    assert set(table["event_family"]) == {"vwap"}
    assert set(table["event_direction"]) == {"long"}
    assert set(table["factor_leadership_style"]) == {"momentum", "value", "low_volatility"}


def test_factor_context_coverage_flags_low_sample_contexts():
    coverage = summarize_factor_context_coverage(
        _df(),
        ["factor_leadership_style"],
        min_context_rows=3,
    )
    low_vol = coverage.set_index("context_key").loc["factor_leadership_style=low_volatility"]
    assert low_vol["context_sample_flag"] == "small_context_sample"
    assert "__missing_factor_context_rows__" in set(coverage["context_key"])


def test_factor_research_report_packages_tables_without_trade_language():
    report = build_factor_event_research_report(
        _df(),
        _catalog(),
        ["forward_return_5m"],
        ["factor_leadership_style"],
    )
    assert set(report) == {
        "metadata",
        "context_coverage",
        "event_outcomes",
        "factor_context_comparison",
    }
    assert report["metadata"]["forward_outcomes_are_evaluation_only"] is True
    columns = list(report["event_outcomes"].columns) + list(report["factor_context_comparison"].columns)
    forbidden_terms = ("buy", "sell", "entry", "exit", "signal")
    assert not any(term in column.lower() for column in columns for term in forbidden_terms)
