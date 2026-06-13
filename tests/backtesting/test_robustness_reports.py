from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from spy_edge_research.backtesting import (
    build_and_export_robustness_report,
    build_robustness_report_bundle,
    create_robustness_report_metadata,
    export_robustness_report_bundle_to_csv,
    export_robustness_report_bundle_to_json,
    summarize_robustness_report_bundle,
    validate_robustness_report_bundle,
)


def sample_oos_results() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "candidate_id": ["candidate_a", "candidate_a"],
            "candidate_type": ["event", "event"],
            "name": ["event_vwap_reclaim", "event_vwap_reclaim"],
            "direction": ["long", "long"],
            "horizon": ["5m", "5m"],
            "oos_expectancy_difference": [0.001, -0.0002],
            "oos_hit_rate_difference": [0.05, -0.01],
            "oos_sample_size": [12, 4],
            "oos_sample_size_flag": ["ok", "small_sample"],
            "caveats": [
                ["out_of_sample_result_is_not_edge_proof"],
                ["small_sample_in_split"],
            ],
        }
    )


def sample_parameter_sensitivity() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "metric_column": ["expectancy_difference", "hit_rate_difference"],
            "parameter_set_count": [4, 4],
            "non_missing_count": [4, 4],
            "metric_min": [-0.0001, -0.02],
            "metric_max": [0.001, 0.05],
            "metric_range": [0.0011, 0.07],
            "metric_mean": [0.0004, 0.015],
            "metric_std": [0.0005, 0.03],
            "relative_range": [2.75, 4.67],
            "sensitivity_flag": ["high_variation", "high_variation"],
            "caveats": [["parameter_sensitivity_is_descriptive_only"], []],
        }
    )


def test_create_robustness_report_metadata_includes_caveat_and_timestamp() -> None:
    metadata = create_robustness_report_metadata(
        package_name="robustness_run_001",
        notes="unit test",
    )

    assert metadata["created_at_utc"].endswith("+00:00")
    assert metadata["project_name"] == "SPY Directional Edge Research"
    assert metadata["milestone"] == "36"
    assert metadata["package_name"] == "robustness_run_001"
    assert metadata["report_caveat"] == "robustness_report_is_descriptive_only"


def test_build_robustness_report_bundle_auto_adds_oos_stability_and_caveats() -> None:
    oos_results = sample_oos_results()
    sensitivity = sample_parameter_sensitivity()

    bundle = build_robustness_report_bundle(
        oos_validation_results=oos_results,
        parameter_sensitivity_summary=sensitivity,
        metadata={"milestone": "36"},
    )

    assert set(bundle["tables"]) == {
        "oos_validation_results",
        "oos_stability_summary",
        "parameter_sensitivity_summary",
        "robustness_caveats",
    }
    assert bundle["metadata"]["report_caveat"] == "robustness_report_is_descriptive_only"
    assert bundle["tables"]["oos_stability_summary"]["candidate_id"].tolist() == [
        "candidate_a"
    ]
    assert "small_sample_in_split" in bundle["tables"]["robustness_caveats"]["caveat"].tolist()

    bundle["tables"]["oos_validation_results"].loc[0, "candidate_id"] = "changed"
    assert oos_results.loc[0, "candidate_id"] == "candidate_a"


def test_summarize_robustness_report_bundle_reports_structural_table_info() -> None:
    bundle = build_robustness_report_bundle(
        oos_validation_results=sample_oos_results(),
        parameter_sensitivity_summary=sample_parameter_sensitivity(),
    )

    summary = summarize_robustness_report_bundle(bundle)

    assert summary["table_name"].tolist() == [
        "oos_stability_summary",
        "oos_validation_results",
        "parameter_sensitivity_summary",
        "robustness_caveats",
    ]
    caveat_rows = len(bundle["tables"]["robustness_caveats"])
    assert summary["row_count"].tolist() == [1, 2, 2, caveat_rows]


def test_export_robustness_report_bundle_to_csv_and_json(tmp_path: Path) -> None:
    bundle = build_robustness_report_bundle(
        oos_validation_results=sample_oos_results(),
        parameter_sensitivity_summary=sample_parameter_sensitivity(),
        metadata={"milestone": "36"},
    )

    written = export_robustness_report_bundle_to_csv(bundle, tmp_path)
    json_path = export_robustness_report_bundle_to_json(
        bundle,
        tmp_path / "robustness_report.json",
    )
    payload = json.loads(json_path.read_text())

    assert set(written) == {
        "metadata",
        "oos_validation_results",
        "oos_stability_summary",
        "parameter_sensitivity_summary",
        "robustness_caveats",
    }
    assert (tmp_path / "oos_validation_results.csv").exists()
    assert (tmp_path / "parameter_sensitivity_summary.csv").exists()
    assert json_path == tmp_path / "robustness_report.json"
    assert payload["metadata"]["milestone"] == "36"
    assert "robustness_caveats" in payload["tables"]


def test_build_and_export_robustness_report_returns_bundle_paths_and_summary(
    tmp_path: Path,
) -> None:
    result = build_and_export_robustness_report(
        output_dir=tmp_path,
        oos_validation_results=sample_oos_results(),
        parameter_sensitivity_summary=sample_parameter_sensitivity(),
        metadata={"milestone": "36"},
    )

    assert set(result) == {"bundle", "written_paths", "summary"}
    assert result["summary"]["table_name"].tolist()[0] == "oos_stability_summary"
    assert result["written_paths"]["metadata"] == tmp_path / "metadata.json"


def test_robustness_report_helpers_validate_inputs_and_overwrite_policy(
    tmp_path: Path,
) -> None:
    with pytest.raises(TypeError, match="bundle must be a dict"):
        validate_robustness_report_bundle("not-a-bundle")
    with pytest.raises(TypeError, match="must be a pandas DataFrame"):
        build_robustness_report_bundle(
            oos_validation_results={"not": "a-dataframe"}  # type: ignore[arg-type]
        )
    with pytest.raises(ValueError, match="forbidden fields"):
        build_robustness_report_bundle(metadata={"best_setting": "nope"})

    bundle = build_robustness_report_bundle(oos_validation_results=sample_oos_results())
    export_robustness_report_bundle_to_csv(bundle, tmp_path)
    with pytest.raises(FileExistsError, match="Refusing to overwrite"):
        export_robustness_report_bundle_to_csv(bundle, tmp_path)

    json_path = tmp_path / "bundle.json"
    export_robustness_report_bundle_to_json(bundle, json_path)
    with pytest.raises(FileExistsError, match="already exists"):
        export_robustness_report_bundle_to_json(bundle, json_path)


def test_robustness_report_outputs_avoid_live_trading_readiness_columns() -> None:
    bundle = build_robustness_report_bundle(
        oos_validation_results=sample_oos_results(),
        parameter_sensitivity_summary=sample_parameter_sensitivity(),
    )
    summary = summarize_robustness_report_bundle(bundle)

    forbidden = (
        "best",
        "optimal",
        "buy",
        "sell",
        "entry",
        "exit",
        "approved",
        "live",
        "trade_signal",
    )
    for table in bundle["tables"].values():
        assert not any(word in column for column in table.columns for word in forbidden)
    assert not any(word in column for column in summary.columns for word in forbidden)
