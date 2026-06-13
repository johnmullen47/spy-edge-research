from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from spy_edge_research.backtesting import (
    build_event_research_workflow_outputs,
    create_event_research_metadata,
    export_event_research_workflow_outputs,
    get_event_research_workflow_table_names,
    validate_event_research_workflow_outputs,
)


def sample_event_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "event_vwap_reclaim_bullish": [True, False, True, False, True, False],
            "event_vwap_loss_bearish": [False, True, False, True, False, False],
            "event_any_support_retest_touch": [False, False, True, False, False, True],
            "directional_regime": ["up", "down", "up", "down", "range", "range"],
            "forward_return_5m": [0.01, -0.02, 0.03, -0.01, 0.00, 0.02],
            "forward_direction_5m": [1, -1, 1, -1, 0, 1],
        },
        index=pd.Index(["a", "b", "c", "d", "e", "f"], name="row"),
    )


def build_outputs(**kwargs: object) -> dict[str, object]:
    return build_event_research_workflow_outputs(
        sample_event_frame(),
        label_columns=["forward_return_5m", "forward_direction_5m"],
        event_columns=["event_vwap_reclaim_bullish", "event_vwap_loss_bearish"],
        min_events=1,
        group_columns=["event_family"],
        **kwargs,
    )


def collect_dataframes(value: object) -> list[pd.DataFrame]:
    frames: list[pd.DataFrame] = []
    if isinstance(value, pd.DataFrame):
        frames.append(value)
    elif isinstance(value, dict):
        for nested in value.values():
            frames.extend(collect_dataframes(nested))
    return frames


def test_create_event_research_metadata_includes_required_workflow_fields() -> None:
    metadata = create_event_research_metadata()

    assert metadata["project_name"] == "SPY Directional Edge Research"
    assert metadata["workflow_name"] == "event_research_workflow"
    assert metadata["milestone"] == "15"
    assert metadata["created_at_utc"].endswith("+00:00")


def test_create_event_research_metadata_includes_provided_columns() -> None:
    metadata = create_event_research_metadata(
        label_columns=["forward_return_5m"],
        event_columns=["event_vwap_reclaim_bullish"],
    )

    assert metadata["label_columns"] == ["forward_return_5m"]
    assert metadata["event_columns"] == ["event_vwap_reclaim_bullish"]


def test_build_event_research_workflow_outputs_returns_expected_top_level_keys() -> None:
    outputs = build_outputs()

    assert list(outputs) == [
        "catalog",
        "event_study_results",
        "diagnostics",
        "frequency_summary",
        "metadata",
        "visualization_bundle",
        "report_bundle",
        "report_summary",
    ]


def test_build_event_research_workflow_outputs_uses_explicit_label_columns() -> None:
    outputs = build_outputs()
    results = outputs["event_study_results"]

    assert isinstance(results, pd.DataFrame)
    assert results["label_column"].tolist() == [
        "forward_return_5m",
        "forward_direction_5m",
        "forward_return_5m",
        "forward_direction_5m",
    ]


def test_build_event_research_workflow_outputs_includes_diagnostics_outputs() -> None:
    diagnostics = build_outputs()["diagnostics"]

    assert list(diagnostics) == [
        "results_with_sample_flags",
        "label_coverage",
        "event_coverage",
        "grouped_summary",
    ]
    assert all(isinstance(table, pd.DataFrame) for table in diagnostics.values())


def test_build_event_research_workflow_outputs_includes_report_bundle_and_summary() -> None:
    outputs = build_outputs()

    assert list(outputs["report_bundle"]["tables"]) == [
        "event_study_results",
        "diagnostics",
        "label_coverage",
        "event_coverage",
        "grouped_summary",
    ]
    assert outputs["report_summary"]["table_name"].tolist() == [
        "event_study_results",
        "diagnostics",
        "label_coverage",
        "event_coverage",
        "grouped_summary",
    ]


def test_build_event_research_workflow_outputs_includes_visualization_bundle() -> None:
    bundle = build_outputs()["visualization_bundle"]

    assert list(bundle["tables"]) == [
        "event_counts",
        "label_coverage",
        "event_coverage",
        "grouped_summary",
    ]


def test_build_event_research_workflow_outputs_adds_regime_summary_only_when_requested() -> None:
    without_regime = build_outputs()
    with_regime = build_outputs(regime_column="directional_regime")

    assert "regime_summary" not in without_regime
    assert "regime_summary" in with_regime
    assert isinstance(with_regime["regime_summary"], pd.DataFrame)


def test_build_event_research_workflow_outputs_does_not_mutate_input_dataframe() -> None:
    df = sample_event_frame()
    original = df.copy(deep=True)

    build_event_research_workflow_outputs(
        df,
        label_columns=["forward_return_5m"],
        event_columns=["event_vwap_reclaim_bullish"],
        min_events=1,
    )

    pd.testing.assert_frame_equal(df, original)


def test_build_event_research_workflow_outputs_does_not_write_files(tmp_path: Path) -> None:
    before = sorted(path.name for path in tmp_path.iterdir())

    build_outputs()

    after = sorted(path.name for path in tmp_path.iterdir())
    assert after == before


def test_build_event_research_workflow_outputs_does_not_create_buy_sell_entry_exit_columns() -> None:
    outputs = build_outputs(regime_column="directional_regime")

    forbidden = ("buy", "sell", "entry", "exit")
    for frame in collect_dataframes(outputs):
        assert not any(word in column for column in frame.columns for word in forbidden)


def test_build_event_research_workflow_outputs_does_not_create_confidence_score_rank_edge_columns() -> None:
    outputs = build_outputs(regime_column="directional_regime")

    forbidden = ("confidence", "score", "rank", "edge")
    for frame in collect_dataframes(outputs):
        assert not any(word in column for column in frame.columns for word in forbidden)


def test_validate_event_research_workflow_outputs_accepts_valid_outputs() -> None:
    outputs = build_outputs()

    assert validate_event_research_workflow_outputs(outputs) is outputs


def test_validate_event_research_workflow_outputs_raises_on_non_dict_input() -> None:
    with pytest.raises(TypeError, match="outputs must be a dict"):
        validate_event_research_workflow_outputs(["not", "a", "mapping"])  # type: ignore[arg-type]


def test_validate_event_research_workflow_outputs_raises_when_required_keys_are_missing() -> None:
    outputs = build_outputs()
    outputs.pop("report_bundle")

    with pytest.raises(KeyError, match="missing required keys"):
        validate_event_research_workflow_outputs(outputs)


def test_export_event_research_workflow_outputs_writes_expected_csv_and_metadata_artifacts(
    tmp_path: Path,
) -> None:
    outputs = build_outputs()

    written = export_event_research_workflow_outputs(outputs, tmp_path)
    metadata = json.loads((tmp_path / "metadata.json").read_text())

    assert set(written) == {
        "event_study_results",
        "diagnostics",
        "label_coverage",
        "event_coverage",
        "grouped_summary",
        "metadata",
    }
    assert (tmp_path / "event_study_results.csv").exists()
    assert (tmp_path / "diagnostics.csv").exists()
    assert (tmp_path / "label_coverage.csv").exists()
    assert (tmp_path / "event_coverage.csv").exists()
    assert (tmp_path / "grouped_summary.csv").exists()
    assert metadata["workflow_name"] == "event_research_workflow"
    assert metadata["milestone"] == "15"


def test_export_event_research_workflow_outputs_respects_overwrite_false(tmp_path: Path) -> None:
    outputs = build_outputs()
    export_event_research_workflow_outputs(outputs, tmp_path)

    with pytest.raises(FileExistsError, match="Refusing to overwrite"):
        export_event_research_workflow_outputs(outputs, tmp_path)


def test_get_event_research_workflow_table_names_returns_sorted_table_names() -> None:
    names = get_event_research_workflow_table_names(
        build_outputs(regime_column="directional_regime")
    )

    assert names == sorted(names)
    assert names == [
        "catalog",
        "diagnostics.event_coverage",
        "diagnostics.grouped_summary",
        "diagnostics.label_coverage",
        "diagnostics.results_with_sample_flags",
        "event_study_results",
        "frequency_summary",
        "regime_summary",
        "report_bundle.diagnostics",
        "report_bundle.event_coverage",
        "report_bundle.event_study_results",
        "report_bundle.grouped_summary",
        "report_bundle.label_coverage",
        "report_summary",
        "visualization_bundle.event_counts",
        "visualization_bundle.event_coverage",
        "visualization_bundle.grouped_summary",
        "visualization_bundle.label_coverage",
    ]


def test_event_workflow_module_does_not_import_or_call_execution_broker_alert_optimizer_or_strategy_modules() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    workflow_text = (
        repo_root / "src/spy_edge_research/backtesting/event_workflows.py"
    ).read_text()
    forbidden_terms = (
        "execution",
        "broker",
        "alert",
        "optimizer",
        "strategy",
    )

    assert not any(term in workflow_text.lower() for term in forbidden_terms)
