from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from spy_edge_research.backtesting import (
    directional_profit_factor_equivalent,
    evaluate_baselines,
    evaluate_prediction_column,
    evaluate_prediction_columns,
    find_baseline_prediction_columns,
)


def sample_evaluation_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "baseline_a": [1, -1, 0, 1, -1],
            "baseline_b": [-1, -1, 1, 0, 1],
            "forward_return_5m": [0.02, -0.01, 0.00, -0.03, 0.04],
            "forward_return_bps_5m": [200.0, -100.0, 0.0, -300.0, 400.0],
            "forward_direction_5m": [1, -1, 0, -1, 1],
            "label_valid_5m": [True, True, True, True, False],
            "forward_return_10m": [0.01, 0.02, -0.01, -0.02, 0.03],
            "forward_return_bps_10m": [100.0, 200.0, -100.0, -200.0, 300.0],
            "forward_direction_10m": [1, 1, -1, -1, 1],
            "label_valid_10m": [True, True, True, False, False],
        },
        index=pd.Index(["a", "b", "c", "d", "e"], name="row"),
    )


def test_directional_profit_factor_equivalent_handles_core_cases() -> None:
    assert directional_profit_factor_equivalent(
        pd.Series([0.02, -0.01, 0.03, np.nan])
    ) == pytest.approx(5.0)
    assert directional_profit_factor_equivalent(pd.Series([0.02, 0.03, np.nan])) == np.inf
    assert directional_profit_factor_equivalent(pd.Series([-0.02, -0.03, np.nan])) == 0.0
    assert np.isnan(directional_profit_factor_equivalent(pd.Series([0.0, np.nan])))


def test_evaluate_prediction_column_computes_metrics_without_mutation() -> None:
    df = sample_evaluation_frame()
    original = df.copy(deep=True)

    result = evaluate_prediction_column(df, "baseline_a", horizons_minutes=(5, 10))

    assert result["horizon_minutes"].tolist() == [5, 10]
    row_5m = result.loc[result["horizon_minutes"] == 5].iloc[0]
    assert row_5m["prediction_col"] == "baseline_a"
    assert row_5m["n_rows"] == 5
    assert row_5m["n_label_valid"] == 4
    assert row_5m["n_predictions"] == 3
    assert row_5m["n_neutral"] == 1
    assert row_5m["coverage"] == pytest.approx(0.75)
    assert row_5m["accuracy"] == pytest.approx(2 / 3)
    assert row_5m["average_forward_return"] == pytest.approx((-0.02) / 3)
    assert row_5m["median_forward_return"] == pytest.approx(-0.01)
    assert row_5m["average_directional_return"] == pytest.approx(0.0)
    assert row_5m["median_directional_return"] == pytest.approx(0.01)
    assert row_5m["win_rate_directional_return"] == pytest.approx(2 / 3)
    assert row_5m["profit_factor_equivalent"] == pytest.approx(1.0)
    assert row_5m["bullish_predictions"] == 2
    assert row_5m["bearish_predictions"] == 1

    row_10m = result.loc[result["horizon_minutes"] == 10].iloc[0]
    assert row_10m["n_label_valid"] == 3
    assert row_10m["n_predictions"] == 2
    assert row_10m["n_neutral"] == 1
    assert row_10m["accuracy"] == pytest.approx(0.5)
    pd.testing.assert_frame_equal(df, original)


def test_evaluate_prediction_column_handles_zero_predictions_and_zero_valid_labels() -> None:
    df = pd.DataFrame(
        {
            "baseline_neutral": [0, 0],
            "forward_return_5m": [0.01, -0.01],
            "forward_return_bps_5m": [100.0, -100.0],
            "forward_direction_5m": [1, -1],
            "label_valid_5m": [True, True],
            "forward_return_10m": [0.01, -0.01],
            "forward_return_bps_10m": [100.0, -100.0],
            "forward_direction_10m": [1, -1],
            "label_valid_10m": [False, False],
        }
    )

    result = evaluate_prediction_column(
        df,
        "baseline_neutral",
        horizons_minutes=(5, 10),
    )

    row_5m = result.loc[result["horizon_minutes"] == 5].iloc[0]
    assert row_5m["coverage"] == 0.0
    assert np.isnan(row_5m["accuracy"])
    assert np.isnan(row_5m["average_forward_return"])
    assert np.isnan(row_5m["profit_factor_equivalent"])

    row_10m = result.loc[result["horizon_minutes"] == 10].iloc[0]
    assert row_10m["n_label_valid"] == 0
    assert np.isnan(row_10m["coverage"])
    assert np.isnan(row_10m["win_rate_directional_return"])


def test_evaluate_prediction_column_validates_prediction_and_label_columns() -> None:
    df = sample_evaluation_frame()

    with pytest.raises(ValueError, match="Missing required columns"):
        evaluate_prediction_column(df, "missing", horizons_minutes=(5,))
    with pytest.raises(ValueError, match="Missing required columns"):
        evaluate_prediction_column(
            df.drop(columns=["forward_return_bps_5m"]),
            "baseline_a",
            horizons_minutes=(5,),
        )
    invalid = df.copy()
    invalid.loc["a", "baseline_a"] = 2
    with pytest.raises(ValueError, match="values must be one of"):
        evaluate_prediction_column(invalid, "baseline_a", horizons_minutes=(5,))


def test_evaluate_prediction_columns_concatenates_in_expected_order() -> None:
    df = sample_evaluation_frame()

    result = evaluate_prediction_columns(
        df,
        ("baseline_a", "baseline_b"),
        horizons_minutes=(5, 10),
    )

    assert result["prediction_col"].tolist() == [
        "baseline_a",
        "baseline_a",
        "baseline_b",
        "baseline_b",
    ]
    assert result["horizon_minutes"].tolist() == [5, 10, 5, 10]


def test_find_baseline_prediction_columns_preserves_column_order() -> None:
    df = pd.DataFrame(
        {
            "close": [100.0],
            "baseline_first": [1],
            "feature": [3.0],
            "baseline_second": [-1],
        }
    )

    assert find_baseline_prediction_columns(df) == (
        "baseline_first",
        "baseline_second",
    )


def test_evaluate_baselines_evaluates_all_found_baselines_and_requires_one() -> None:
    df = sample_evaluation_frame()

    result = evaluate_baselines(df, horizons_minutes=(5,))

    assert result["prediction_col"].tolist() == ["baseline_a", "baseline_b"]
    assert result["horizon_minutes"].tolist() == [5, 5]
    with pytest.raises(ValueError, match="No baseline"):
        evaluate_baselines(df.drop(columns=["baseline_a", "baseline_b"]), horizons_minutes=(5,))
