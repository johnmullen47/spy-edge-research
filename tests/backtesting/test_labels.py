from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from spy_edge_research.backtesting import (
    add_directional_forward_outcome_labels,
    add_forward_direction_labels,
    add_forward_labels,
    add_forward_path_outcome_labels,
    add_forward_return_labels,
    horizon_to_bars,
)


def sample_bars(
    closes: list[float] | None = None,
    timestamps: pd.Series | pd.DatetimeIndex | None = None,
) -> pd.DataFrame:
    close_values = closes or [100.0, 101.0, 102.0, 103.0, 104.0]
    high_values = [value + 0.5 for value in close_values]
    low_values = [value - 0.5 for value in close_values]
    timestamp_values = timestamps
    if timestamp_values is None:
        timestamp_values = pd.date_range(
            "2024-01-02 09:31",
            periods=len(close_values),
            freq="1min",
            tz="America/New_York",
        )
    return pd.DataFrame(
        {
            "timestamp": timestamp_values,
            "high": high_values,
            "low": low_values,
            "close": close_values,
            "causal_feature": [value * 2 for value in close_values],
        },
        index=pd.Index([f"row_{idx}" for idx in range(len(close_values))], name="row"),
    )


def test_horizon_to_bars_converts_minutes_to_bars() -> None:
    assert horizon_to_bars(5, 1) == 5
    assert horizon_to_bars(10, 5) == 2


def test_horizon_to_bars_validates_inputs() -> None:
    with pytest.raises(ValueError, match="evenly divisible"):
        horizon_to_bars(7, 5)
    with pytest.raises(ValueError, match="horizon_minutes"):
        horizon_to_bars(0, 1)
    with pytest.raises(ValueError, match="bar_interval_minutes"):
        horizon_to_bars(5, 0)


def test_add_forward_return_labels_adds_expected_values_without_mutation() -> None:
    df = sample_bars([100.0, 101.0, 102.0, 103.0, 104.0])
    original = df.copy(deep=True)

    result = add_forward_return_labels(df, horizons_minutes=(1, 2))

    expected_columns = {
        "future_close_1m",
        "forward_return_1m",
        "forward_return_bps_1m",
        "label_valid_1m",
        "future_close_2m",
        "forward_return_2m",
        "forward_return_bps_2m",
        "label_valid_2m",
    }
    assert expected_columns.issubset(result.columns)
    assert result.index.equals(df.index)
    assert len(result) == len(df)
    pd.testing.assert_series_equal(
        result["future_close_1m"],
        pd.Series(
            [101.0, 102.0, 103.0, 104.0, np.nan],
            index=df.index,
            name="future_close_1m",
        ),
    )
    assert result["forward_return_1m"].iloc[:4].tolist() == pytest.approx(
        [0.01, 1 / 101, 1 / 102, 1 / 103]
    )
    assert result["forward_return_bps_1m"].iloc[:4].tolist() == pytest.approx(
        [100.0, 10_000 / 101, 10_000 / 102, 10_000 / 103]
    )
    assert result["label_valid_1m"].tolist() == [True, True, True, True, False]
    assert result["label_valid_2m"].tolist() == [True, True, True, False, False]
    assert result["forward_return_2m"].iloc[-2:].isna().all()
    assert result["forward_return_bps_2m"].iloc[-2:].isna().all()
    pd.testing.assert_frame_equal(df, original)


def test_add_forward_return_labels_validates_required_inputs() -> None:
    df = sample_bars()

    with pytest.raises(ValueError, match="Missing required columns"):
        add_forward_return_labels(df.drop(columns=["close"]))
    with pytest.raises(ValueError, match="Missing required columns"):
        add_forward_return_labels(df.drop(columns=["timestamp"]), prevent_cross_day=True)
    with pytest.raises(ValueError, match="horizon_minutes"):
        add_forward_return_labels(df, horizons_minutes=(0,))
    with pytest.raises(ValueError, match="evenly divisible"):
        add_forward_return_labels(df, horizons_minutes=(7,), bar_interval_minutes=5)


def test_forward_return_labels_do_not_cross_local_trading_dates_when_prevented() -> None:
    timestamps = pd.to_datetime(
        [
            "2024-01-02 15:58",
            "2024-01-02 15:59",
            "2024-01-02 16:00",
            "2024-01-03 09:31",
            "2024-01-03 09:32",
            "2024-01-03 09:33",
        ]
    ).tz_localize("America/New_York")
    df = sample_bars([100.0, 101.0, 102.0, 200.0, 201.0, 202.0], timestamps)

    prevented = add_forward_return_labels(df, horizons_minutes=(2,), prevent_cross_day=True)
    crossing = add_forward_return_labels(df, horizons_minutes=(2,), prevent_cross_day=False)

    pd.testing.assert_series_equal(
        prevented["future_close_2m"],
        pd.Series(
            [102.0, np.nan, np.nan, 202.0, np.nan, np.nan],
            index=df.index,
            name="future_close_2m",
        ),
    )
    assert prevented["label_valid_2m"].tolist() == [True, False, False, True, False, False]
    pd.testing.assert_series_equal(
        crossing["future_close_2m"],
        pd.Series(
            [102.0, 200.0, 201.0, 202.0, np.nan, np.nan],
            index=df.index,
            name="future_close_2m",
        ),
    )
    assert crossing["label_valid_2m"].tolist() == [True, True, True, True, False, False]


def test_forward_return_labels_support_larger_bar_intervals() -> None:
    df = sample_bars(
        [100.0, 101.0, 102.0, 103.0, 104.0],
        pd.date_range("2024-01-02 09:35", periods=5, freq="5min", tz="America/New_York"),
    )

    result = add_forward_return_labels(
        df,
        horizons_minutes=(10, 15),
        bar_interval_minutes=5,
    )

    pd.testing.assert_series_equal(
        result["future_close_10m"],
        pd.Series(
            [102.0, 103.0, 104.0, np.nan, np.nan],
            index=df.index,
            name="future_close_10m",
        ),
    )
    pd.testing.assert_series_equal(
        result["future_close_15m"],
        pd.Series(
            [103.0, 104.0, np.nan, np.nan, np.nan],
            index=df.index,
            name="future_close_15m",
        ),
    )
    with pytest.raises(ValueError, match="evenly divisible"):
        add_forward_return_labels(df, horizons_minutes=(7,), bar_interval_minutes=5)


def test_add_forward_direction_labels_maps_thresholded_targets_without_mutation() -> None:
    df = pd.DataFrame(
        {
            "forward_return_bps_5m": [12.0, -15.0, 3.0, -4.0, np.nan],
            "label_valid_5m": [True, True, True, True, False],
        },
        index=pd.Index(["a", "b", "c", "d", "e"], name="row"),
    )
    original = df.copy(deep=True)

    result = add_forward_direction_labels(df, horizons_minutes=(5,), threshold_bps=5.0)

    assert result["forward_direction_5m"].tolist()[:4] == [1.0, -1.0, 0.0, 0.0]
    assert np.isnan(result["forward_direction_5m"].iloc[4])
    assert result.index.equals(df.index)
    pd.testing.assert_frame_equal(df, original)


def test_add_forward_direction_labels_validates_inputs() -> None:
    df = pd.DataFrame({"forward_return_bps_5m": [1.0]})

    with pytest.raises(ValueError, match="Missing required columns"):
        add_forward_direction_labels(df, horizons_minutes=(5,))
    with pytest.raises(ValueError, match="threshold_bps"):
        add_forward_direction_labels(
            pd.DataFrame({"forward_return_bps_5m": [1.0], "label_valid_5m": [True]}),
            horizons_minutes=(5,),
            threshold_bps=-0.1,
        )


def test_add_forward_labels_composes_all_label_columns_without_mutation() -> None:
    df = sample_bars([100.0, 101.0, 99.0, 99.5])
    original = df.copy(deep=True)

    result = add_forward_labels(df, horizons_minutes=(1,), threshold_bps=20.0)

    expected_columns = {
        "timestamp",
        "close",
        "causal_feature",
        "future_close_1m",
        "forward_return_1m",
        "forward_return_bps_1m",
        "label_valid_1m",
        "forward_direction_1m",
    }
    assert expected_columns.issubset(result.columns)
    assert len(result) == len(df)
    assert result.index.equals(df.index)
    assert result["forward_direction_1m"].iloc[:3].tolist() == [1.0, -1.0, 1.0]
    assert np.isnan(result["forward_direction_1m"].iloc[3])
    pd.testing.assert_frame_equal(df, original)


def test_future_row_changes_only_targeted_prior_labels_and_preserves_features() -> None:
    df = sample_bars([100.0, 101.0, 102.0, 103.0, 104.0])
    changed = df.copy(deep=True)
    changed.loc["row_3", "close"] = 110.0

    baseline = add_forward_labels(df, horizons_minutes=(2,))
    revised = add_forward_labels(changed, horizons_minutes=(2,))

    assert revised.loc["row_1", "future_close_2m"] == 110.0
    assert baseline.loc["row_1", "future_close_2m"] == 103.0
    assert revised.drop(index="row_1")["future_close_2m"].equals(
        baseline.drop(index="row_1")["future_close_2m"]
    )
    pd.testing.assert_series_equal(baseline["causal_feature"], df["causal_feature"])
    pd.testing.assert_series_equal(revised["causal_feature"], changed["causal_feature"])
    assert "forward_return_2m" not in df.columns
    assert "forward_return_2m" not in changed.columns


def test_add_forward_path_outcome_labels_excludes_current_bar_without_mutation() -> None:
    df = sample_bars([100.0, 101.0, 99.0, 103.0])
    df["high"] = [110.0, 102.0, 104.0, 105.0]
    df["low"] = [90.0, 98.0, 97.0, 102.0]
    original = df.copy(deep=True)

    result = add_forward_path_outcome_labels(df, horizons_minutes=(2,))

    assert result.loc["row_0", "future_high_2m"] == 104.0
    assert result.loc["row_0", "future_low_2m"] == 97.0
    assert result.loc["row_0", "forward_mfe_2m"] == pytest.approx(0.04)
    assert result.loc["row_0", "forward_mae_2m"] == pytest.approx(-0.03)
    assert result.loc["row_0", "forward_mfe_bps_2m"] == pytest.approx(400.0)
    assert result.loc["row_0", "forward_mae_bps_2m"] == pytest.approx(-300.0)
    assert result["path_label_valid_2m"].tolist() == [True, True, False, False]
    pd.testing.assert_frame_equal(df, original)


def test_forward_path_outcome_labels_do_not_cross_local_trading_dates_when_prevented() -> None:
    timestamps = pd.to_datetime(
        [
            "2024-01-02 15:59",
            "2024-01-02 16:00",
            "2024-01-03 09:31",
            "2024-01-03 09:32",
        ]
    ).tz_localize("America/New_York")
    df = sample_bars([100.0, 101.0, 200.0, 201.0], timestamps)
    df["high"] = [101.0, 102.0, 205.0, 206.0]
    df["low"] = [99.0, 100.0, 198.0, 199.0]

    prevented = add_forward_path_outcome_labels(df, horizons_minutes=(1,), prevent_cross_day=True)
    crossing = add_forward_path_outcome_labels(df, horizons_minutes=(1,), prevent_cross_day=False)

    pd.testing.assert_series_equal(
        prevented["future_high_1m"],
        pd.Series([102.0, np.nan, 206.0, np.nan], index=df.index, name="future_high_1m"),
    )
    pd.testing.assert_series_equal(
        prevented["future_low_1m"],
        pd.Series([100.0, np.nan, 199.0, np.nan], index=df.index, name="future_low_1m"),
    )
    assert prevented["path_label_valid_1m"].tolist() == [True, False, True, False]
    pd.testing.assert_series_equal(
        crossing["future_high_1m"],
        pd.Series([102.0, 205.0, 206.0, np.nan], index=df.index, name="future_high_1m"),
    )
    pd.testing.assert_series_equal(
        crossing["future_low_1m"],
        pd.Series([100.0, 198.0, 199.0, np.nan], index=df.index, name="future_low_1m"),
    )


def test_add_directional_forward_outcome_labels_normalizes_long_and_short_hypotheses() -> None:
    df = sample_bars([100.0, 101.0, 99.0])
    df["high"] = [101.0, 102.0, 104.0]
    df["low"] = [99.0, 98.0, 97.0]
    labeled = add_forward_return_labels(df, horizons_minutes=(1,))
    labeled = add_forward_path_outcome_labels(labeled, horizons_minutes=(1,))
    labeled["event_direction"] = ["long", "short", "long"]

    result = add_directional_forward_outcome_labels(labeled, horizons_minutes=(1,))

    assert result.loc["row_0", "directional_forward_return_1m"] == pytest.approx(0.01)
    assert result.loc["row_1", "directional_forward_return_1m"] == pytest.approx(
        1 - 99.0 / 101.0
    )
    assert result.loc["row_1", "directional_forward_mfe_1m"] == pytest.approx(
        101.0 / 97.0 - 1
    )
    assert result.loc["row_1", "directional_forward_mae_1m"] == pytest.approx(
        101.0 / 104.0 - 1
    )
    assert result.loc["row_1", "directional_forward_return_bps_1m"] == pytest.approx(
        (1 - 99.0 / 101.0) * 10_000
    )


def test_forward_path_outcome_labels_validate_required_inputs() -> None:
    df = sample_bars()

    with pytest.raises(ValueError, match="Missing required columns"):
        add_forward_path_outcome_labels(df.drop(columns=["high"]), horizons_minutes=(1,))
    with pytest.raises(ValueError, match="Missing required columns"):
        add_forward_path_outcome_labels(
            df.drop(columns=["timestamp"]),
            horizons_minutes=(1,),
            prevent_cross_day=True,
        )
    with pytest.raises(ValueError, match="horizon_minutes"):
        add_forward_path_outcome_labels(df, horizons_minutes=(0,))


def test_directional_forward_outcome_labels_validate_direction_values() -> None:
    df = sample_bars([100.0, 101.0])
    labeled = add_forward_return_labels(df, horizons_minutes=(1,))
    labeled = add_forward_path_outcome_labels(labeled, horizons_minutes=(1,))
    labeled["event_direction"] = ["sideways", "long"]

    with pytest.raises(ValueError, match="Unsupported direction values"):
        add_directional_forward_outcome_labels(labeled, horizons_minutes=(1,))
