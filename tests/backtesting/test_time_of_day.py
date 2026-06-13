from __future__ import annotations

import pandas as pd
import pytest

from spy_edge_research.backtesting import (
    assign_intraday_session_bucket,
    compare_session_bucket_outcomes,
    detect_time_of_day_edge_concentration,
    summarize_event_by_session_bucket,
)
from spy_edge_research.signal_engine import build_named_event_catalog


def sample_time_of_day_frame() -> pd.DataFrame:
    timestamps = pd.to_datetime(
        [
            "2024-01-02 09:31",
            "2024-01-02 10:15",
            "2024-01-02 11:30",
            "2024-01-02 12:30",
            "2024-01-02 14:00",
            "2024-01-02 15:30",
            "2024-01-02 16:15",
        ]
    ).tz_localize("America/New_York")
    return pd.DataFrame(
        {
            "timestamp": timestamps,
            "event_vwap_reclaim_bullish": [True, False, True, False, False, True, False],
            "event_vwap_loss_bearish": [False, True, False, False, True, False, False],
            "directional_forward_return_5m": [0.020, -0.010, 0.030, 0.000, 0.015, 0.040, -0.020],
        },
        index=pd.Index(["a", "b", "c", "d", "e", "f", "g"], name="row"),
    )


def test_assign_intraday_session_bucket_boundaries() -> None:
    tz = "America/New_York"

    cases = {
        "2024-01-02 09:31": "open",
        "2024-01-02 10:00": "open",
        "2024-01-02 10:01": "post_open",
        "2024-01-02 11:01": "mid_morning",
        "2024-01-02 12:01": "lunch",
        "2024-01-02 13:31": "afternoon",
        "2024-01-02 15:01": "power_hour",
        "2024-01-02 16:00": "power_hour",
        "2024-01-02 16:01": "outside_regular",
    }
    for timestamp, expected in cases.items():
        assert assign_intraday_session_bucket(pd.Timestamp(timestamp, tz=tz)) == expected


def test_summarize_event_by_session_bucket_uses_context_local_baselines_without_mutation() -> None:
    df = sample_time_of_day_frame()
    original = df.copy(deep=True)
    catalog = build_named_event_catalog(event_columns=["event_vwap_reclaim_bullish"])

    result = summarize_event_by_session_bucket(
        df,
        catalog,
        ["directional_forward_return_5m"],
    )

    assert "session_bucket" in result.columns
    assert "session_bucket" not in df.columns
    open_row = result.loc[result["session_bucket"] == "open"].iloc[0]
    assert open_row["event_count"] == 1
    assert open_row["baseline_count"] == 1
    assert open_row["event_expectancy"] == pytest.approx(0.020)
    assert open_row["baseline_expectancy"] == pytest.approx(0.020)
    power_hour = result.loc[result["session_bucket"] == "power_hour"].iloc[0]
    assert power_hour["event_count"] == 1
    assert power_hour["event_expectancy"] == pytest.approx(0.040)
    pd.testing.assert_frame_equal(df, original)


def test_compare_session_bucket_outcomes_compares_bucket_to_overall_baseline() -> None:
    df = sample_time_of_day_frame()

    result = compare_session_bucket_outcomes(df, ["directional_forward_return_5m"])

    assert result["session_bucket"].tolist() == [
        "open",
        "post_open",
        "mid_morning",
        "lunch",
        "afternoon",
        "power_hour",
        "outside_regular",
    ]
    assert result["bucket_count"].tolist() == [1, 1, 1, 1, 1, 1, 1]
    baseline = (0.020 - 0.010 + 0.030 + 0.000 + 0.015 + 0.040 - 0.020) / 7
    assert result.loc[result["session_bucket"] == "power_hour", "bucket_expectancy"].iloc[
        0
    ] == pytest.approx(0.040)
    assert result["baseline_expectancy"].unique().tolist() == pytest.approx([baseline])


def test_detect_time_of_day_edge_concentration_flags_concentrated_rows() -> None:
    df = sample_time_of_day_frame()
    catalog = build_named_event_catalog(event_columns=["event_vwap_reclaim_bullish"])
    table = summarize_event_by_session_bucket(
        df,
        catalog,
        ["directional_forward_return_5m"],
    )

    result = detect_time_of_day_edge_concentration(
        table,
        min_events=1,
        concentration_threshold=0.30,
    )

    assert "event_count_share" in result.columns
    assert "is_time_of_day_concentrated" in result.columns
    concentrated = result.loc[result["is_time_of_day_concentrated"]]
    assert set(concentrated["session_bucket"]) == {"open", "mid_morning", "power_hour"}
    assert concentrated["event_count_share"].tolist() == pytest.approx([1 / 3, 1 / 3, 1 / 3])


def test_time_of_day_helpers_validate_inputs() -> None:
    df = sample_time_of_day_frame()
    catalog = build_named_event_catalog(event_columns=["event_vwap_reclaim_bullish"])

    with pytest.raises(ValueError, match="Missing required columns"):
        summarize_event_by_session_bucket(
            df.drop(columns=["timestamp"]),
            catalog,
            ["directional_forward_return_5m"],
        )
    with pytest.raises(ValueError, match="Missing required columns"):
        compare_session_bucket_outcomes(df, ["missing_outcome"])
    with pytest.raises(ValueError, match="min_events"):
        detect_time_of_day_edge_concentration(pd.DataFrame(), min_events=0)
    with pytest.raises(ValueError, match="concentration_threshold"):
        detect_time_of_day_edge_concentration(
            pd.DataFrame(
                {
                    "event_column": ["event"],
                    "outcome_column": ["outcome"],
                    "event_count": [1],
                    "expectancy_difference": [0.1],
                }
            ),
            min_events=1,
            concentration_threshold=1.5,
        )


def test_time_of_day_helpers_do_not_create_signal_columns() -> None:
    df = sample_time_of_day_frame()
    catalog = build_named_event_catalog(event_columns=["event_vwap_reclaim_bullish"])

    event_summary = summarize_event_by_session_bucket(
        df,
        catalog,
        ["directional_forward_return_5m"],
    )
    bucket_summary = compare_session_bucket_outcomes(df, ["directional_forward_return_5m"])

    forbidden = ("buy", "sell", "entry", "exit", "confidence", "signal")
    assert not any(word in column for column in event_summary.columns for word in forbidden)
    assert not any(word in column for column in bucket_summary.columns for word in forbidden)
