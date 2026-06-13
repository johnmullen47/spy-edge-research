import json
from pathlib import Path

import pandas as pd
import pytest

from spy_edge_research.backtesting import (
    build_macro_regime_report_bundle,
    build_macro_regime_snapshot,
    create_macro_regime_report_metadata,
    export_macro_regime_report_bundle_to_csv,
    export_macro_regime_report_bundle_to_json,
    summarize_macro_regime_persistence,
    summarize_macro_regime_report_bundle,
    validate_macro_regime_report_bundle,
)


def _macro_context_df():
    return pd.DataFrame(
        {
            "timestamp": pd.date_range("2024-01-02 09:31", periods=4, freq="min"),
            "TLT_return_1": [-0.01, 0.02, 0.01, -0.03],
            "HYG_return_1": [0.02, 0.01, -0.02, 0.01],
            "VIXY_return_1": [-0.03, -0.01, 0.04, -0.02],
            "TLT_relative_return_vs_SPY_1": [-0.02, 0.01, 0.03, -0.04],
            "HYG_relative_return_vs_SPY_1": [0.01, 0.00, 0.00, 0.00],
            "VIXY_relative_return_vs_SPY_1": [-0.04, -0.02, 0.06, -0.03],
            "macro_rates_context": ["rates_up", "rates_down", "rates_down", "rates_up"],
            "macro_credit_context": ["credit_risk_on", "credit_risk_on", "credit_risk_off", "credit_risk_on"],
            "macro_commodity_context": ["commodity_up", "commodity_up", "commodity_down", "commodity_up"],
            "macro_volatility_proxy_context": [
                "volatility_proxy_down",
                "volatility_proxy_down",
                "volatility_proxy_up",
                "volatility_proxy_down",
            ],
            "macro_risk_context": ["risk_on", "risk_on", "risk_off", "risk_on"],
        }
    )


def _event_report():
    return {
        "event_outcomes": pd.DataFrame(
            {
                "event_column": ["event_vwap_reclaim"],
                "outcome_column": ["forward_return_5m"],
                "event_count": [3],
                "study_caveat": ["macro_event_study_is_descriptive_research_only"],
            }
        ),
        "context_coverage": pd.DataFrame(
            {
                "context_key": ["macro_risk_context=risk_on"],
                "context_sample_count": [3],
                "context_sample_flag": ["ok"],
            }
        ),
    }


def test_create_macro_regime_report_metadata_includes_research_caveat():
    metadata = create_macro_regime_report_metadata(package_name="macro_run_001")

    assert metadata["created_at_utc"].endswith("+00:00")
    assert metadata["milestone"] == "69"
    assert metadata["package_name"] == "macro_run_001"
    assert metadata["report_caveat"] == "macro_regime_report_is_descriptive_context_research_only"


def test_build_macro_regime_snapshot_uses_latest_row_without_recommendation_fields():
    snapshot = build_macro_regime_snapshot(
        _macro_context_df(),
        macro_symbols=["TLT", "HYG", "VIXY"],
    )

    tlt = snapshot.set_index("macro_symbol").loc["TLT"]
    assert tlt["macro_return"] == pytest.approx(-0.03)
    assert tlt["macro_risk_context"] == "risk_on"
    forbidden = ("buy", "sell", "entry", "exit", "allocation", "portfolio")
    assert not any(term in column for column in snapshot.columns for term in forbidden)


def test_summarize_macro_regime_persistence_counts_context_values():
    summary = summarize_macro_regime_persistence(
        _macro_context_df(),
        context_columns=["macro_risk_context", "macro_rates_context"],
        min_observations=2,
    )
    risk_rows = summary.loc[summary["context_type"].eq("macro_risk_context")].set_index("context_value")
    rates_rows = summary.loc[summary["context_type"].eq("macro_rates_context")].set_index("context_value")

    assert risk_rows.loc["risk_on", "observation_count"] == 3
    assert risk_rows.loc["risk_on", "longest_consecutive_observations"] == 2
    assert risk_rows.loc["risk_off", "sample_flag"] == "small_sample"
    assert rates_rows.loc["rates_down", "observation_count"] == 2


def test_build_macro_regime_report_bundle_packages_tables_and_caveats():
    bundle = build_macro_regime_report_bundle(
        macro_context_df=_macro_context_df(),
        macro_symbols=["TLT", "HYG", "VIXY"],
        macro_event_report=_event_report(),
        metadata={"milestone": "69"},
    )

    assert set(bundle["tables"]) == {
        "macro_regime_snapshot",
        "macro_regime_persistence",
        "macro_event_outcomes",
        "macro_context_coverage",
        "macro_regime_caveats",
    }
    assert bundle["metadata"]["report_caveat"] == "macro_regime_report_is_descriptive_context_research_only"
    assert "macro_proxies_require_interpretation_review" in bundle["tables"]["macro_regime_caveats"]["caveat"].tolist()


def test_summarize_and_export_macro_regime_report_bundle(tmp_path: Path):
    bundle = build_macro_regime_report_bundle(
        macro_context_df=_macro_context_df(),
        macro_symbols=["TLT", "HYG", "VIXY"],
        macro_event_report=_event_report(),
    )

    summary = summarize_macro_regime_report_bundle(bundle)
    written = export_macro_regime_report_bundle_to_csv(bundle, tmp_path)
    json_path = export_macro_regime_report_bundle_to_json(bundle, tmp_path / "macro_regime_report.json")
    payload = json.loads(json_path.read_text())

    assert "macro_regime_snapshot" in summary["table_name"].tolist()
    assert (tmp_path / "macro_regime_snapshot.csv").exists()
    assert written["metadata"] == tmp_path / "metadata.json"
    assert payload["metadata"]["milestone"] == "69"
    assert "macro_regime_caveats" in payload["tables"]


def test_macro_regime_report_validation_and_overwrite_policy(tmp_path: Path):
    with pytest.raises(TypeError, match="bundle must be a dict"):
        validate_macro_regime_report_bundle("not-a-bundle")
    with pytest.raises(ValueError, match="forbidden fields"):
        build_macro_regime_report_bundle(
            macro_context_df=_macro_context_df(),
            macro_symbols=["TLT"],
            metadata={"allocation_notes": "not allowed"},
        )

    bundle = build_macro_regime_report_bundle(
        macro_context_df=_macro_context_df(),
        macro_symbols=["TLT", "HYG", "VIXY"],
    )
    export_macro_regime_report_bundle_to_csv(bundle, tmp_path)
    with pytest.raises(FileExistsError, match="Refusing to overwrite"):
        export_macro_regime_report_bundle_to_csv(bundle, tmp_path)

    json_path = tmp_path / "bundle.json"
    export_macro_regime_report_bundle_to_json(bundle, json_path)
    with pytest.raises(FileExistsError, match="already exists"):
        export_macro_regime_report_bundle_to_json(bundle, json_path)
