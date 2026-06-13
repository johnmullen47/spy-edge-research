import json
from pathlib import Path

import pandas as pd
import pytest

from spy_edge_research.backtesting import (
    build_factor_rotation_report_bundle,
    build_factor_rotation_snapshot,
    create_factor_rotation_report_metadata,
    export_factor_rotation_report_bundle_to_csv,
    export_factor_rotation_report_bundle_to_json,
    summarize_factor_leadership_persistence,
    summarize_factor_rotation_report_bundle,
    validate_factor_rotation_report_bundle,
)


def _factor_context_df():
    return pd.DataFrame(
        {
            "timestamp": pd.date_range("2024-01-02 09:31", periods=4, freq="min"),
            "MTUM_return_1": [0.01, 0.02, -0.01, 0.03],
            "VLUE_return_1": [-0.01, -0.02, 0.01, 0.01],
            "USMV_return_1": [0.00, 0.01, 0.02, -0.01],
            "MTUM_relative_return_vs_SPY_1": [0.00, 0.01, -0.02, 0.02],
            "VLUE_relative_return_vs_SPY_1": [-0.02, -0.03, 0.00, 0.00],
            "USMV_relative_return_vs_SPY_1": [-0.01, 0.00, 0.01, -0.02],
            "factor_leadership_symbol": ["MTUM", "MTUM", "USMV", "MTUM"],
            "factor_laggard_symbol": ["VLUE", "VLUE", "MTUM", "USMV"],
            "factor_leadership_style": ["momentum", "momentum", "low_volatility", "momentum"],
            "factor_dispersion_return_std": [0.008, 0.017, 0.012, 0.016],
            "factor_high_dispersion_context": [0, 1, 0, 1],
        }
    )


def _event_report():
    return {
        "event_outcomes": pd.DataFrame(
            {
                "event_column": ["event_vwap_reclaim"],
                "outcome_column": ["forward_return_5m"],
                "event_count": [3],
                "study_caveat": ["factor_event_study_is_descriptive_research_only"],
            }
        ),
        "context_coverage": pd.DataFrame(
            {
                "context_key": ["factor_leadership_style=momentum"],
                "context_sample_count": [3],
                "context_sample_flag": ["ok"],
            }
        ),
    }


def test_create_factor_rotation_report_metadata_includes_research_caveat():
    metadata = create_factor_rotation_report_metadata(package_name="factor_run_001")
    assert metadata["created_at_utc"].endswith("+00:00")
    assert metadata["milestone"] == "78"
    assert metadata["package_name"] == "factor_run_001"
    assert metadata["report_caveat"] == "factor_rotation_report_is_descriptive_leadership_research_only"


def test_build_factor_rotation_snapshot_uses_latest_row_without_recommendation_fields():
    snapshot = build_factor_rotation_snapshot(
        _factor_context_df(),
        factor_symbols=["MTUM", "VLUE", "USMV"],
        factor_styles={"MTUM": "momentum", "VLUE": "value", "USMV": "low_volatility"},
    )
    mtum = snapshot.set_index("factor_symbol").loc["MTUM"]
    assert mtum["factor_return"] == pytest.approx(0.03)
    assert mtum["is_leadership_context"] == 1
    forbidden = ("buy", "sell", "entry", "exit", "allocation", "portfolio")
    assert not any(term in column for column in snapshot.columns for term in forbidden)


def test_summarize_factor_leadership_persistence_counts_symbols_and_styles():
    summary = summarize_factor_leadership_persistence(_factor_context_df(), min_observations=2)
    symbol_rows = summary.loc[summary["context_type"].eq("factor_symbol")].set_index("context_value")
    style_rows = summary.loc[summary["context_type"].eq("factor_style")].set_index("context_value")

    assert symbol_rows.loc["MTUM", "observation_count"] == 3
    assert symbol_rows.loc["MTUM", "longest_consecutive_observations"] == 2
    assert symbol_rows.loc["USMV", "sample_flag"] == "small_sample"
    assert style_rows.loc["momentum", "observation_count"] == 3


def test_build_factor_rotation_report_bundle_packages_tables_and_caveats():
    bundle = build_factor_rotation_report_bundle(
        factor_context_df=_factor_context_df(),
        factor_symbols=["MTUM", "VLUE", "USMV"],
        factor_styles={"MTUM": "momentum", "VLUE": "value", "USMV": "low_volatility"},
        factor_event_report=_event_report(),
        metadata={"milestone": "78"},
    )
    assert set(bundle["tables"]) == {
        "factor_rotation_snapshot",
        "factor_leadership_persistence",
        "factor_event_outcomes",
        "factor_context_coverage",
        "factor_rotation_caveats",
    }
    assert bundle["metadata"]["report_caveat"] == "factor_rotation_report_is_descriptive_leadership_research_only"


def test_summarize_and_export_factor_rotation_report_bundle(tmp_path: Path):
    bundle = build_factor_rotation_report_bundle(
        factor_context_df=_factor_context_df(),
        factor_symbols=["MTUM", "VLUE", "USMV"],
        factor_event_report=_event_report(),
    )
    summary = summarize_factor_rotation_report_bundle(bundle)
    written = export_factor_rotation_report_bundle_to_csv(bundle, tmp_path)
    json_path = export_factor_rotation_report_bundle_to_json(bundle, tmp_path / "factor_rotation_report.json")
    payload = json.loads(json_path.read_text())

    assert "factor_rotation_snapshot" in summary["table_name"].tolist()
    assert (tmp_path / "factor_rotation_snapshot.csv").exists()
    assert written["metadata"] == tmp_path / "metadata.json"
    assert "factor_rotation_caveats" in payload["tables"]


def test_factor_rotation_report_validation_and_overwrite_policy(tmp_path: Path):
    with pytest.raises(TypeError, match="bundle must be a dict"):
        validate_factor_rotation_report_bundle("not-a-bundle")
    with pytest.raises(ValueError, match="forbidden fields"):
        build_factor_rotation_report_bundle(
            factor_context_df=_factor_context_df(),
            factor_symbols=["MTUM"],
            metadata={"allocation_notes": "not allowed"},
        )

    bundle = build_factor_rotation_report_bundle(
        factor_context_df=_factor_context_df(),
        factor_symbols=["MTUM", "VLUE", "USMV"],
    )
    export_factor_rotation_report_bundle_to_csv(bundle, tmp_path)
    with pytest.raises(FileExistsError, match="Refusing to overwrite"):
        export_factor_rotation_report_bundle_to_csv(bundle, tmp_path)
