import pandas as pd
import pytest

from spy_edge_research.backtesting import (
    build_macro_event_outcome_table,
    build_macro_event_research_report,
    compare_macro_regime_event_outcomes,
    summarize_event_by_macro_regime,
    summarize_macro_context_coverage,
)


def _df():
    return pd.DataFrame(
        {
            "event_vwap_reclaim": [1, 0, 1, 1, 0, 1, 1],
            "forward_return_5m": [0.3, -0.1, 0.2, -0.4, 0.1, 0.5, 0.0],
            "macro_risk_context": [
                "risk_on",
                "risk_on",
                "risk_off",
                "risk_off",
                "risk_mixed",
                "risk_on",
                "risk_mixed",
            ],
            "macro_rates_context": [
                "rates_down",
                "rates_down",
                "rates_up",
                "rates_up",
                "rates_mixed",
                "rates_down",
                "rates_mixed",
            ],
            "macro_credit_context": [
                "credit_risk_on",
                "credit_risk_on",
                "credit_risk_off",
                "credit_risk_off",
                "credit_mixed",
                "credit_risk_on",
                "credit_mixed",
            ],
            "macro_commodity_context": [
                "commodity_up",
                "commodity_up",
                "commodity_down",
                "commodity_down",
                "commodity_mixed",
                "commodity_up",
                "commodity_mixed",
            ],
            "macro_volatility_proxy_context": [
                "volatility_proxy_down",
                "volatility_proxy_down",
                "volatility_proxy_up",
                "volatility_proxy_up",
                "volatility_proxy_mixed",
                "volatility_proxy_down",
                "volatility_proxy_mixed",
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


def test_summarize_event_by_macro_regime_includes_caveats_and_samples():
    summary = summarize_event_by_macro_regime(
        _df(),
        "event_vwap_reclaim",
        "forward_return_5m",
        ["macro_risk_context"],
        min_events=2,
    )

    risk_on = summary.set_index("macro_risk_context").loc["risk_on"]
    mixed = summary.set_index("macro_risk_context").loc["risk_mixed"]

    assert risk_on["event_count"] == 2
    assert risk_on["event_expectancy"] == pytest.approx(0.4)
    assert mixed["sample_size_flag"] == "small_sample"
    assert summary["study_caveat"].eq("macro_event_study_is_descriptive_research_only").all()


def test_compare_macro_regime_event_outcomes_is_descriptive():
    summary = summarize_event_by_macro_regime(
        _df(),
        "event_vwap_reclaim",
        "forward_return_5m",
        ["macro_risk_context"],
    )

    comparison = compare_macro_regime_event_outcomes(summary)

    assert comparison.loc[0, "risk_on_event_count"] == 2
    assert comparison.loc[0, "risk_off_event_count"] == 2
    assert comparison.loc[0, "mixed_event_count"] == 1
    assert comparison.loc[0, "comparison_caveat"] == "descriptive_macro_regime_comparison_not_edge_claim"


def test_build_macro_event_outcome_table_uses_catalog_metadata():
    table = build_macro_event_outcome_table(
        _df(),
        _catalog(),
        ["forward_return_5m"],
        ["macro_risk_context"],
    )

    assert set(table["event_family"]) == {"vwap"}
    assert set(table["event_direction"]) == {"long"}
    assert set(table["macro_risk_context"]) == {"risk_on", "risk_off", "risk_mixed"}


def test_macro_context_coverage_flags_low_sample_contexts():
    coverage = summarize_macro_context_coverage(
        _df(),
        ["macro_risk_context"],
        min_context_rows=3,
    )

    mixed = coverage.set_index("context_key").loc["macro_risk_context=risk_mixed"]
    assert mixed["context_sample_flag"] == "small_context_sample"
    assert "__missing_macro_context_rows__" in set(coverage["context_key"])


def test_research_report_packages_tables_without_trade_language():
    report = build_macro_event_research_report(
        _df(),
        _catalog(),
        ["forward_return_5m"],
        ["macro_risk_context"],
    )

    assert set(report) == {
        "metadata",
        "context_coverage",
        "event_outcomes",
        "macro_regime_comparison",
    }
    assert report["metadata"]["forward_outcomes_are_evaluation_only"] is True
    columns = list(report["event_outcomes"].columns) + list(report["macro_regime_comparison"].columns)
    forbidden_terms = ("buy", "sell", "entry", "exit", "signal")
    assert not any(term in column.lower() for column in columns for term in forbidden_terms)


def test_missing_required_columns_raise_clear_errors():
    with pytest.raises(ValueError, match="Missing required columns"):
        summarize_event_by_macro_regime(
            _df().drop(columns=["macro_risk_context"]),
            "event_vwap_reclaim",
            "forward_return_5m",
            ["macro_risk_context"],
        )
