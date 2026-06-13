from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from spy_edge_research.backtesting import (
    build_event_study_report_bundle,
    create_research_run_metadata,
    export_report_bundle_to_csv,
    export_report_bundle_to_json,
    normalize_report_table,
    summarize_report_bundle,
    validate_report_table,
)


def sample_event_study_results() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "event_column": [
                "event_vwap_loss_bearish",
                "event_vwap_reclaim_bullish",
                "event_prior_day_high_break_above",
            ],
            "event_family": ["vwap", "vwap", "zone"],
            "label_column": [
                "forward_return_5m",
                "forward_return_5m",
                "forward_direction_5m",
            ],
            "event_count": [3, 12, 8],
            "event_rate": [0.08123, 0.30456, 0.20789],
            "difference_from_overall": [-0.003, 0.003, 0.080],
        }
    )


def sample_diagnostics() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "event_column": ["event_vwap_loss_bearish", "event_vwap_reclaim_bullish"],
            "has_min_events": [False, True],
            "sample_size_warning": ["event_count_below_minimum", ""],
        }
    )


def sample_label_coverage() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "label_column": ["forward_return_5m"],
            "row_count": [100],
            "non_missing_count": [95],
            "missing_count": [5],
        }
    )


def test_validate_report_table_accepts_valid_dataframes() -> None:
    table = sample_event_study_results()

    validated = validate_report_table(
        table,
        required_columns=["event_column", "label_column"],
        table_name="event_study_results",
    )

    assert validated is table


def test_validate_report_table_raises_on_non_dataframe_input() -> None:
    with pytest.raises(TypeError, match="must be a pandas DataFrame"):
        validate_report_table({"event_column": []})  # type: ignore[arg-type]


def test_validate_report_table_raises_when_required_columns_are_missing() -> None:
    with pytest.raises(KeyError, match="missing required columns"):
        validate_report_table(
            sample_event_study_results(),
            required_columns=["event_column", "missing_column"],
            table_name="event_study_results",
        )


def test_normalize_report_table_returns_copy_and_does_not_mutate_input() -> None:
    table = sample_event_study_results()
    original = table.copy(deep=True)

    normalized = normalize_report_table(
        table,
        sort_columns=["event_column"],
        round_decimals=2,
    )

    assert normalized is not table
    pd.testing.assert_frame_equal(table, original)


def test_normalize_report_table_sorts_only_by_explicit_sort_columns() -> None:
    table = sample_event_study_results()

    default_normalized = normalize_report_table(table)
    sorted_normalized = normalize_report_table(table, sort_columns=["event_column"])

    assert default_normalized["event_column"].tolist() == table["event_column"].tolist()
    assert sorted_normalized["event_column"].tolist() == sorted(table["event_column"])


def test_normalize_report_table_reorders_columns_without_dropping_unspecified_columns() -> None:
    table = sample_event_study_results()

    normalized = normalize_report_table(
        table,
        column_order=["label_column", "event_column"],
    )

    assert normalized.columns.tolist()[:2] == ["label_column", "event_column"]
    assert set(normalized.columns) == set(table.columns)
    assert len(normalized.columns) == len(table.columns)


def test_normalize_report_table_rounds_numeric_float_columns_when_requested() -> None:
    normalized = normalize_report_table(sample_event_study_results(), round_decimals=2)

    assert normalized["event_rate"].tolist() == [0.08, 0.30, 0.21]
    assert normalized["event_count"].tolist() == [3, 12, 8]


def test_build_event_study_report_bundle_includes_only_provided_tables() -> None:
    bundle = build_event_study_report_bundle(
        sample_event_study_results(),
        label_coverage=sample_label_coverage(),
        metadata={"milestone": 13},
    )

    assert list(bundle["tables"]) == ["event_study_results", "label_coverage"]
    assert bundle["metadata"] == {"milestone": 13}


def test_build_event_study_report_bundle_copies_tables_and_does_not_mutate_inputs() -> None:
    results = sample_event_study_results()
    diagnostics = sample_diagnostics()
    original_results = results.copy(deep=True)
    original_diagnostics = diagnostics.copy(deep=True)

    bundle = build_event_study_report_bundle(results, diagnostics=diagnostics)
    bundle["tables"]["event_study_results"].loc[0, "event_column"] = "changed"
    bundle["tables"]["diagnostics"].loc[0, "sample_size_warning"] = "changed"

    pd.testing.assert_frame_equal(results, original_results)
    pd.testing.assert_frame_equal(diagnostics, original_diagnostics)


def test_summarize_report_bundle_reports_table_names_counts_and_columns() -> None:
    bundle = build_event_study_report_bundle(
        sample_event_study_results(),
        diagnostics=sample_diagnostics(),
    )

    summary = summarize_report_bundle(bundle)

    assert summary["table_name"].tolist() == ["event_study_results", "diagnostics"]
    assert summary["row_count"].tolist() == [3, 2]
    assert summary["column_count"].tolist() == [6, 3]
    assert summary.loc[0, "columns"] == sample_event_study_results().columns.tolist()


def test_export_report_bundle_to_csv_writes_expected_csv_files(tmp_path: Path) -> None:
    bundle = build_event_study_report_bundle(
        sample_event_study_results(),
        diagnostics=sample_diagnostics(),
        label_coverage=sample_label_coverage(),
    )

    written = export_report_bundle_to_csv(bundle, tmp_path)

    assert set(written) == {"event_study_results", "diagnostics", "label_coverage"}
    assert (tmp_path / "event_study_results.csv").exists()
    assert (tmp_path / "diagnostics.csv").exists()
    assert (tmp_path / "label_coverage.csv").exists()


def test_export_report_bundle_to_csv_writes_metadata_json_when_metadata_exists(
    tmp_path: Path,
) -> None:
    bundle = build_event_study_report_bundle(
        sample_event_study_results(),
        metadata={"milestone": 13, "label_columns": ["forward_return_5m"]},
    )

    written = export_report_bundle_to_csv(bundle, tmp_path)
    metadata = json.loads((tmp_path / "metadata.json").read_text())

    assert written["metadata"] == tmp_path / "metadata.json"
    assert metadata == {"label_columns": ["forward_return_5m"], "milestone": 13}


def test_export_report_bundle_to_csv_respects_overwrite_false(tmp_path: Path) -> None:
    bundle = build_event_study_report_bundle(sample_event_study_results())
    export_report_bundle_to_csv(bundle, tmp_path)

    with pytest.raises(FileExistsError, match="Refusing to overwrite"):
        export_report_bundle_to_csv(bundle, tmp_path)


def test_export_report_bundle_to_json_writes_json_file_with_metadata_and_records(
    tmp_path: Path,
) -> None:
    bundle = build_event_study_report_bundle(
        sample_event_study_results(),
        metadata={"milestone": 13},
    )
    output_path = tmp_path / "bundle.json"

    written = export_report_bundle_to_json(bundle, output_path)
    payload = json.loads(output_path.read_text())

    assert written == output_path
    assert payload["metadata"] == {"milestone": 13}
    assert list(payload["tables"]) == ["event_study_results"]
    assert payload["tables"]["event_study_results"][0]["event_column"] == (
        "event_vwap_loss_bearish"
    )


def test_export_report_bundle_to_json_respects_overwrite_false(tmp_path: Path) -> None:
    bundle = build_event_study_report_bundle(sample_event_study_results())
    output_path = tmp_path / "bundle.json"
    export_report_bundle_to_json(bundle, output_path)

    with pytest.raises(FileExistsError, match="already exists"):
        export_report_bundle_to_json(bundle, output_path)


def test_create_research_run_metadata_includes_created_at_utc_and_provided_fields() -> None:
    metadata = create_research_run_metadata(
        milestone=13,
        data_start="2024-01-02",
        data_end="2024-01-31",
        label_columns=["forward_return_5m"],
        event_count=3,
        notes="research export",
    )

    assert metadata["created_at_utc"].endswith("+00:00")
    assert metadata["project_name"] == "SPY Directional Edge Research"
    assert metadata["milestone"] == 13
    assert metadata["data_start"] == "2024-01-02"
    assert metadata["data_end"] == "2024-01-31"
    assert metadata["label_columns"] == ["forward_return_5m"]
    assert metadata["event_count"] == 3
    assert metadata["notes"] == "research export"


def test_report_export_functions_do_not_create_buy_sell_entry_or_exit_columns(
    tmp_path: Path,
) -> None:
    bundle = build_event_study_report_bundle(
        sample_event_study_results(),
        diagnostics=sample_diagnostics(),
        label_coverage=sample_label_coverage(),
    )
    outputs = [
        normalize_report_table(sample_event_study_results()),
        summarize_report_bundle(bundle),
        *bundle["tables"].values(),
    ]
    export_report_bundle_to_csv(bundle, tmp_path / "csv")
    export_report_bundle_to_json(bundle, tmp_path / "bundle.json")

    forbidden = ("buy", "sell", "entry", "exit")
    for output in outputs:
        assert not any(word in column for column in output.columns for word in forbidden)


def test_report_export_functions_do_not_create_confidence_score_rank_or_edge_columns(
    tmp_path: Path,
) -> None:
    bundle = build_event_study_report_bundle(
        sample_event_study_results(),
        diagnostics=sample_diagnostics(),
    )
    outputs = [
        normalize_report_table(sample_event_study_results()),
        summarize_report_bundle(bundle),
        *bundle["tables"].values(),
    ]
    export_report_bundle_to_csv(bundle, tmp_path / "csv")
    export_report_bundle_to_json(bundle, tmp_path / "bundle.json")

    forbidden = ("confidence", "score", "rank", "edge")
    for output in outputs:
        assert not any(word in column for column in output.columns for word in forbidden)


def test_report_functions_do_not_sort_by_difference_from_overall_by_default() -> None:
    table = sample_event_study_results()

    normalized = normalize_report_table(table)
    bundle = build_event_study_report_bundle(table)

    assert normalized["difference_from_overall"].tolist() == [-0.003, 0.003, 0.080]
    assert bundle["tables"]["event_study_results"]["event_column"].tolist() == table[
        "event_column"
    ].tolist()


def test_event_reports_do_not_import_feature_generation_modules() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    report_text = (repo_root / "src/spy_edge_research/backtesting/event_reports.py").read_text()
    forbidden_imports = (
        "spy_edge_research.signal_engine",
        "spy_edge_research.indicators",
        "spy_edge_research.market_structure",
        "spy_edge_research.market_regime",
        "spy_edge_research.support_resistance",
    )

    assert not any(forbidden in report_text for forbidden in forbidden_imports)
