import pandas as pd
import pytest

from spy_edge_research.backtesting import (
    build_sector_event_outcome_table,
    build_sector_event_research_report,
    compare_sector_confirmed_event_outcomes,
    summarize_event_by_sector_context,
    summarize_sector_context_coverage,
)


def _df():
    return pd.DataFrame(
        {
            "event_vwap_reclaim": [1, 0, 1, 1, 0, 1, 1],
            "forward_return_5m": [0.3, -0.1, 0.2, -0.4, 0.1, 0.5, 0.0],
            "primary_sector_context": [
                "sector_confirmed",
                "sector_confirmed",
                "sector_divergent",
                "sector_divergent",
                "sector_neutral",
                "sector_confirmed",
                "sector_neutral",
            ],
            "sector_leadership_group": [
                "cyclical",
                "cyclical",
                "defensive",
                "defensive",
                "unknown",
                "cyclical",
                "unknown",
            ],
            "sector_high_dispersion_context": [0, 0, 1, 1, 0, 0, 0],
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


def test_summarize_event_by_sector_context_includes_caveats_and_samples():
    summary = summarize_event_by_sector_context(
        _df(),
        "event_vwap_reclaim",
        "forward_return_5m",
        ["primary_sector_context"],
        min_events=2,
    )

    confirmed = summary.set_index("primary_sector_context").loc["sector_confirmed"]
    neutral = summary.set_index("primary_sector_context").loc["sector_neutral"]

    assert confirmed["event_count"] == 2
    assert confirmed["event_expectancy"] == pytest.approx(0.4)
    assert neutral["sample_size_flag"] == "small_sample"
    assert summary["study_caveat"].eq("sector_event_study_is_descriptive_research_only").all()


def test_compare_sector_confirmed_event_outcomes_is_descriptive():
    summary = summarize_event_by_sector_context(
        _df(),
        "event_vwap_reclaim",
        "forward_return_5m",
        ["primary_sector_context"],
    )

    comparison = compare_sector_confirmed_event_outcomes(summary)

    assert comparison.loc[0, "sector_confirmed_event_count"] == 2
    assert comparison.loc[0, "sector_divergent_event_count"] == 2
    assert comparison.loc[0, "neutral_event_count"] == 1
    assert comparison.loc[0, "comparison_caveat"] == "descriptive_sector_context_comparison_not_edge_claim"


def test_build_sector_event_outcome_table_uses_catalog_metadata():
    table = build_sector_event_outcome_table(
        _df(),
        _catalog(),
        ["forward_return_5m"],
        ["primary_sector_context"],
    )

    assert set(table["event_family"]) == {"vwap"}
    assert set(table["event_direction"]) == {"long"}
    assert set(table["primary_sector_context"]) == {
        "sector_confirmed",
        "sector_divergent",
        "sector_neutral",
    }


def test_sector_context_coverage_flags_low_sample_contexts():
    coverage = summarize_sector_context_coverage(
        _df(),
        ["primary_sector_context"],
        min_context_rows=3,
    )

    neutral = coverage.set_index("context_key").loc["primary_sector_context=sector_neutral"]
    assert neutral["context_sample_flag"] == "small_context_sample"
    assert "__missing_sector_context_rows__" in set(coverage["context_key"])


def test_research_report_packages_tables_without_trade_language():
    report = build_sector_event_research_report(
        _df(),
        _catalog(),
        ["forward_return_5m"],
        ["primary_sector_context"],
    )

    assert set(report) == {
        "metadata",
        "context_coverage",
        "event_outcomes",
        "sector_context_comparison",
    }
    assert report["metadata"]["forward_outcomes_are_evaluation_only"] is True
    columns = list(report["event_outcomes"].columns) + list(report["sector_context_comparison"].columns)
    forbidden_terms = ("buy", "sell", "entry", "exit", "signal")
    assert not any(term in column.lower() for column in columns for term in forbidden_terms)


def test_missing_required_columns_raise_clear_errors():
    with pytest.raises(ValueError, match="Missing required columns"):
        summarize_event_by_sector_context(
            _df().drop(columns=["primary_sector_context"]),
            "event_vwap_reclaim",
            "forward_return_5m",
            ["primary_sector_context"],
        )
