import json
from pathlib import Path

import pandas as pd
import pytest

from spy_edge_research.backtesting import (
    build_sector_rotation_report_bundle,
    build_sector_rotation_snapshot,
    create_sector_rotation_report_metadata,
    export_sector_rotation_report_bundle_to_csv,
    export_sector_rotation_report_bundle_to_json,
    summarize_sector_leadership_persistence,
    summarize_sector_rotation_report_bundle,
    validate_sector_rotation_report_bundle,
)


def _sector_context_df():
    return pd.DataFrame(
        {
            "timestamp": pd.date_range("2024-01-02 09:31", periods=4, freq="min"),
            "XLK_return_1": [0.01, 0.02, -0.01, 0.03],
            "XLF_return_1": [-0.01, -0.02, 0.01, 0.01],
            "XLU_return_1": [0.00, 0.01, 0.02, -0.01],
            "XLK_relative_return_vs_SPY_1": [0.00, 0.01, -0.02, 0.02],
            "XLF_relative_return_vs_SPY_1": [-0.02, -0.03, 0.00, 0.00],
            "XLU_relative_return_vs_SPY_1": [-0.01, 0.00, 0.01, -0.02],
            "sector_leadership_symbol": ["XLK", "XLK", "XLU", "XLK"],
            "sector_laggard_symbol": ["XLF", "XLF", "XLK", "XLU"],
            "sector_leadership_group": ["cyclical", "cyclical", "defensive", "cyclical"],
            "sector_breadth_fraction_positive": [0.5, 2 / 3, 2 / 3, 2 / 3],
            "sector_dispersion_return_std": [0.008, 0.017, 0.012, 0.016],
            "sector_high_dispersion_context": [0, 1, 0, 1],
            "primary_sector_context": [
                "sector_neutral",
                "sector_confirmed",
                "sector_divergent",
                "sector_confirmed",
            ],
        }
    )


def _event_report():
    return {
        "event_outcomes": pd.DataFrame(
            {
                "event_column": ["event_vwap_reclaim"],
                "outcome_column": ["forward_return_5m"],
                "event_count": [3],
                "study_caveat": ["sector_event_study_is_descriptive_research_only"],
            }
        ),
        "context_coverage": pd.DataFrame(
            {
                "context_key": ["primary_sector_context=sector_confirmed"],
                "context_sample_count": [2],
                "context_sample_flag": ["ok"],
            }
        ),
    }


def test_create_sector_rotation_report_metadata_includes_research_caveat():
    metadata = create_sector_rotation_report_metadata(package_name="sector_run_001")

    assert metadata["created_at_utc"].endswith("+00:00")
    assert metadata["milestone"] == "65"
    assert metadata["package_name"] == "sector_run_001"
    assert metadata["report_caveat"] == "sector_rotation_report_is_descriptive_leadership_research_only"


def test_build_sector_rotation_snapshot_uses_latest_row_without_recommendation_fields():
    snapshot = build_sector_rotation_snapshot(
        _sector_context_df(),
        sector_symbols=["XLK", "XLF", "XLU"],
        sector_groups={"XLK": "cyclical", "XLF": "cyclical", "XLU": "defensive"},
    )

    xlk = snapshot.set_index("sector_symbol").loc["XLK"]
    assert xlk["sector_return"] == pytest.approx(0.03)
    assert xlk["is_leadership_context"] == 1
    assert xlk["primary_sector_context"] == "sector_confirmed"
    forbidden = ("buy", "sell", "entry", "exit", "allocation", "portfolio")
    assert not any(term in column for column in snapshot.columns for term in forbidden)


def test_summarize_sector_leadership_persistence_counts_symbols_and_groups():
    summary = summarize_sector_leadership_persistence(_sector_context_df(), min_observations=2)
    symbol_rows = summary.loc[summary["context_type"].eq("sector_symbol")].set_index("context_value")
    group_rows = summary.loc[summary["context_type"].eq("sector_group")].set_index("context_value")

    assert symbol_rows.loc["XLK", "observation_count"] == 3
    assert symbol_rows.loc["XLK", "longest_consecutive_observations"] == 2
    assert symbol_rows.loc["XLU", "sample_flag"] == "small_sample"
    assert group_rows.loc["cyclical", "observation_count"] == 3


def test_build_sector_rotation_report_bundle_packages_tables_and_caveats():
    bundle = build_sector_rotation_report_bundle(
        sector_context_df=_sector_context_df(),
        sector_symbols=["XLK", "XLF", "XLU"],
        sector_groups={"XLK": "cyclical", "XLF": "cyclical", "XLU": "defensive"},
        sector_event_report=_event_report(),
        metadata={"milestone": "65"},
    )

    assert set(bundle["tables"]) == {
        "sector_rotation_snapshot",
        "sector_leadership_persistence",
        "sector_event_outcomes",
        "sector_context_coverage",
        "sector_rotation_caveats",
    }
    assert bundle["metadata"]["report_caveat"] == "sector_rotation_report_is_descriptive_leadership_research_only"
    assert "sample_size_and_coverage_require_research_review" in bundle["tables"]["sector_rotation_caveats"]["caveat"].tolist()


def test_summarize_and_export_sector_rotation_report_bundle(tmp_path: Path):
    bundle = build_sector_rotation_report_bundle(
        sector_context_df=_sector_context_df(),
        sector_symbols=["XLK", "XLF", "XLU"],
        sector_event_report=_event_report(),
    )

    summary = summarize_sector_rotation_report_bundle(bundle)
    written = export_sector_rotation_report_bundle_to_csv(bundle, tmp_path)
    json_path = export_sector_rotation_report_bundle_to_json(bundle, tmp_path / "sector_rotation_report.json")
    payload = json.loads(json_path.read_text())

    assert "sector_rotation_snapshot" in summary["table_name"].tolist()
    assert (tmp_path / "sector_rotation_snapshot.csv").exists()
    assert written["metadata"] == tmp_path / "metadata.json"
    assert payload["metadata"]["milestone"] == "65"
    assert "sector_rotation_caveats" in payload["tables"]


def test_sector_rotation_report_validation_and_overwrite_policy(tmp_path: Path):
    with pytest.raises(TypeError, match="bundle must be a dict"):
        validate_sector_rotation_report_bundle("not-a-bundle")
    with pytest.raises(ValueError, match="forbidden fields"):
        build_sector_rotation_report_bundle(
            sector_context_df=_sector_context_df(),
            sector_symbols=["XLK"],
            metadata={"allocation_notes": "not allowed"},
        )

    bundle = build_sector_rotation_report_bundle(
        sector_context_df=_sector_context_df(),
        sector_symbols=["XLK", "XLF", "XLU"],
    )
    export_sector_rotation_report_bundle_to_csv(bundle, tmp_path)
    with pytest.raises(FileExistsError, match="Refusing to overwrite"):
        export_sector_rotation_report_bundle_to_csv(bundle, tmp_path)

    json_path = tmp_path / "bundle.json"
    export_sector_rotation_report_bundle_to_json(bundle, json_path)
    with pytest.raises(FileExistsError, match="already exists"):
        export_sector_rotation_report_bundle_to_json(bundle, json_path)
