from __future__ import annotations

import importlib.util
from pathlib import Path

import pandas as pd
import pytest

from spy_edge_research.backtesting import (
    build_event_study_visualization_bundle,
    plot_event_counts,
    plot_event_coverage,
    plot_label_coverage,
    prepare_event_count_table,
    prepare_event_coverage_table,
    prepare_grouped_summary_table,
    prepare_label_coverage_table,
    validate_visualization_table,
)


def sample_event_study_results() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "event_column": [
                "event_vwap_loss_bearish",
                "event_prior_day_high_break_above",
                "event_vwap_reclaim_bullish",
                "event_vwap_reclaim_bullish",
            ],
            "event_family": ["vwap", "zone", "vwap", "vwap"],
            "event_direction": ["short", "long", "long", "long"],
            "label_column": [
                "forward_return_5m",
                "forward_direction_5m",
                "forward_direction_5m",
                "forward_return_5m",
            ],
            "event_count": [3, 8, 12, 12],
            "event_rate": [0.08, 0.20, 0.30, 0.30],
            "label_mean_on_event": [-0.002, 0.100, 0.200, 0.004],
            "overall_label_mean": [0.001, 0.020, 0.010, 0.001],
            "difference_from_overall": [-0.003, 0.080, 0.190, 0.003],
        }
    )


def sample_label_coverage() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "label_column": ["forward_return_5m", "forward_direction_5m"],
            "row_count": [100, 100],
            "non_missing_count": [95, 90],
            "missing_count": [5, 10],
            "non_missing_rate": [0.95, 0.90],
            "missing_rate": [0.05, 0.10],
        }
    )


def sample_event_coverage() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "event_column": [
                "event_z_high_break",
                "event_a_vwap_reclaim",
                "event_m_loss",
            ],
            "row_count": [100, 100, 100],
            "true_count": [5, 40, 10],
            "false_count": [95, 60, 85],
            "missing_count": [0, 0, 5],
            "true_rate": [0.05, 0.40, 0.10],
            "missing_rate": [0.00, 0.00, 0.05],
        }
    )


def sample_grouped_summary() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "event_family": ["zone", "vwap", "vwap"],
            "event_direction": ["long", "short", "long"],
            "row_count": [1, 1, 2],
            "total_event_count": [8, 3, 24],
            "mean_event_rate": [0.20, 0.08, 0.30],
            "mean_difference_from_overall": [0.080, -0.003, 0.0965],
        }
    )


def matplotlib_available() -> bool:
    return importlib.util.find_spec("matplotlib") is not None


def test_validate_visualization_table_accepts_valid_dataframes() -> None:
    table = sample_event_study_results()

    validated = validate_visualization_table(
        table,
        required_columns=["event_column", "label_column"],
        table_name="event_study_results",
    )

    assert validated is table


def test_validate_visualization_table_raises_on_non_dataframe_input() -> None:
    with pytest.raises(TypeError, match="must be a pandas DataFrame"):
        validate_visualization_table({"event_column": []})  # type: ignore[arg-type]


def test_validate_visualization_table_raises_when_required_columns_are_missing() -> None:
    with pytest.raises(KeyError, match="missing required columns"):
        validate_visualization_table(
            sample_event_study_results(),
            required_columns=["event_column", "missing_column"],
            table_name="event_study_results",
        )


def test_prepare_event_count_table_returns_deterministic_rows_without_mutating_input() -> None:
    results = sample_event_study_results()
    original = results.copy(deep=True)

    prepared = prepare_event_count_table(results)

    assert prepared["event_column"].tolist() == [
        "event_prior_day_high_break_above",
        "event_vwap_loss_bearish",
        "event_vwap_reclaim_bullish",
        "event_vwap_reclaim_bullish",
    ]
    assert prepared.columns.tolist() == [
        "event_column",
        "event_family",
        "event_direction",
        "label_column",
        "event_count",
        "event_rate",
    ]
    pd.testing.assert_frame_equal(results, original)


def test_prepare_event_count_table_with_group_columns_aggregates_descriptive_fields() -> None:
    prepared = prepare_event_count_table(
        sample_event_study_results(),
        group_columns=["event_family", "event_direction"],
    )

    assert prepared.columns.tolist() == [
        "event_family",
        "event_direction",
        "total_event_count",
        "mean_event_rate",
        "row_count",
    ]
    assert prepared["event_family"].tolist() == ["vwap", "vwap", "zone"]
    assert prepared["event_direction"].tolist() == ["long", "short", "long"]
    assert prepared["total_event_count"].tolist() == [24, 3, 8]
    assert prepared["row_count"].tolist() == [2, 1, 1]


def test_prepare_event_count_table_does_not_sort_by_difference_from_overall() -> None:
    prepared = prepare_event_count_table(sample_event_study_results())

    assert "difference_from_overall" not in prepared.columns
    assert prepared["event_column"].tolist()[0] == "event_prior_day_high_break_above"
    assert prepared["event_column"].tolist()[-1] == "event_vwap_reclaim_bullish"


def test_prepare_label_coverage_table_sorts_alphabetically_by_label_column() -> None:
    prepared = prepare_label_coverage_table(sample_label_coverage())

    assert prepared["label_column"].tolist() == [
        "forward_direction_5m",
        "forward_return_5m",
    ]


def test_prepare_event_coverage_table_sorts_alphabetically_by_event_column() -> None:
    prepared = prepare_event_coverage_table(sample_event_coverage())

    assert prepared["event_column"].tolist() == [
        "event_a_vwap_reclaim",
        "event_m_loss",
        "event_z_high_break",
    ]


def test_prepare_event_coverage_table_does_not_sort_by_true_rate_by_default() -> None:
    prepared = prepare_event_coverage_table(sample_event_coverage())

    assert prepared["true_rate"].tolist() == [0.40, 0.10, 0.05]


def test_prepare_grouped_summary_table_sorts_by_group_columns_only() -> None:
    prepared = prepare_grouped_summary_table(
        sample_grouped_summary(),
        group_columns=["event_family", "event_direction"],
    )

    assert prepared["event_family"].tolist() == ["vwap", "vwap", "zone"]
    assert prepared["event_direction"].tolist() == ["long", "short", "long"]
    assert prepared["mean_difference_from_overall"].tolist() == [0.0965, -0.003, 0.080]


def test_build_event_study_visualization_bundle_includes_only_provided_tables() -> None:
    bundle = build_event_study_visualization_bundle(
        event_study_results=sample_event_study_results(),
        label_coverage=sample_label_coverage(),
        metadata={"milestone": 14},
    )

    assert list(bundle["tables"]) == ["event_counts", "label_coverage"]
    assert bundle["metadata"] == {"milestone": 14}


def test_build_event_study_visualization_bundle_copies_tables_and_does_not_mutate_inputs() -> None:
    results = sample_event_study_results()
    label_coverage = sample_label_coverage()
    original_results = results.copy(deep=True)
    original_label_coverage = label_coverage.copy(deep=True)

    bundle = build_event_study_visualization_bundle(
        event_study_results=results,
        label_coverage=label_coverage,
    )
    bundle["tables"]["event_counts"].loc[0, "event_column"] = "changed"
    bundle["tables"]["label_coverage"].loc[0, "label_column"] = "changed"

    pd.testing.assert_frame_equal(results, original_results)
    pd.testing.assert_frame_equal(label_coverage, original_label_coverage)


def test_visualization_helpers_do_not_create_buy_sell_entry_or_exit_columns() -> None:
    bundle = build_event_study_visualization_bundle(
        event_study_results=sample_event_study_results(),
        label_coverage=sample_label_coverage(),
        event_coverage=sample_event_coverage(),
        grouped_summary=sample_grouped_summary(),
        group_columns=["event_family", "event_direction"],
    )
    outputs = [
        prepare_event_count_table(sample_event_study_results()),
        prepare_event_count_table(sample_event_study_results(), group_columns=["event_family"]),
        prepare_label_coverage_table(sample_label_coverage()),
        prepare_event_coverage_table(sample_event_coverage()),
        prepare_grouped_summary_table(sample_grouped_summary(), group_columns=["event_family"]),
        *bundle["tables"].values(),
    ]

    forbidden = ("buy", "sell", "entry", "exit")
    for output in outputs:
        assert not any(word in column for column in output.columns for word in forbidden)


def test_visualization_helpers_do_not_create_confidence_score_rank_or_edge_columns() -> None:
    bundle = build_event_study_visualization_bundle(
        event_study_results=sample_event_study_results(),
        label_coverage=sample_label_coverage(),
        event_coverage=sample_event_coverage(),
        grouped_summary=sample_grouped_summary(),
        group_columns=["event_family", "event_direction"],
    )
    outputs = [
        prepare_event_count_table(sample_event_study_results()),
        prepare_event_count_table(sample_event_study_results(), group_columns=["event_family"]),
        prepare_label_coverage_table(sample_label_coverage()),
        prepare_event_coverage_table(sample_event_coverage()),
        prepare_grouped_summary_table(sample_grouped_summary(), group_columns=["event_family"]),
        *bundle["tables"].values(),
    ]

    forbidden = ("confidence", "score", "rank", "edge")
    for output in outputs:
        assert not any(word in column for column in output.columns for word in forbidden)


def test_visualization_helpers_do_not_filter_to_top_bottom_best_or_worst_events() -> None:
    results = sample_event_study_results()

    ungrouped = prepare_event_count_table(results)
    grouped = prepare_event_count_table(results, group_columns=["event_family"])

    assert len(ungrouped) == len(results)
    assert grouped["row_count"].sum() == len(results)


def test_plot_event_counts_returns_matplotlib_axis_object_if_available() -> None:
    if not matplotlib_available():
        pytest.skip("matplotlib is not installed")
    import matplotlib

    matplotlib.use("Agg")
    from matplotlib.axes import Axes

    ax = plot_event_counts(prepare_event_count_table(sample_event_study_results()))

    assert isinstance(ax, Axes)


def test_plot_label_coverage_returns_matplotlib_axis_object_if_available() -> None:
    if not matplotlib_available():
        pytest.skip("matplotlib is not installed")
    import matplotlib

    matplotlib.use("Agg")
    from matplotlib.axes import Axes

    ax = plot_label_coverage(prepare_label_coverage_table(sample_label_coverage()))

    assert isinstance(ax, Axes)


def test_plot_event_coverage_returns_matplotlib_axis_object_if_available() -> None:
    if not matplotlib_available():
        pytest.skip("matplotlib is not installed")
    import matplotlib

    matplotlib.use("Agg")
    from matplotlib.axes import Axes

    ax = plot_event_coverage(prepare_event_coverage_table(sample_event_coverage()))

    assert isinstance(ax, Axes)


def test_plotting_functions_do_not_mutate_inputs_if_matplotlib_is_available() -> None:
    if not matplotlib_available():
        pytest.skip("matplotlib is not installed")
    import matplotlib

    matplotlib.use("Agg")

    event_counts = prepare_event_count_table(sample_event_study_results())
    label_coverage = prepare_label_coverage_table(sample_label_coverage())
    event_coverage = prepare_event_coverage_table(sample_event_coverage())
    original_event_counts = event_counts.copy(deep=True)
    original_label_coverage = label_coverage.copy(deep=True)
    original_event_coverage = event_coverage.copy(deep=True)

    plot_event_counts(event_counts)
    plot_label_coverage(label_coverage)
    plot_event_coverage(event_coverage)

    pd.testing.assert_frame_equal(event_counts, original_event_counts)
    pd.testing.assert_frame_equal(label_coverage, original_label_coverage)
    pd.testing.assert_frame_equal(event_coverage, original_event_coverage)


def test_event_visualizations_do_not_import_feature_generation_modules() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    visualization_text = (
        repo_root / "src/spy_edge_research/backtesting/event_visualizations.py"
    ).read_text()
    forbidden_imports = (
        "spy_edge_research.signal_engine",
        "spy_edge_research.indicators",
        "spy_edge_research.market_structure",
        "spy_edge_research.market_regime",
        "spy_edge_research.support_resistance",
    )

    assert not any(forbidden in visualization_text for forbidden in forbidden_imports)
