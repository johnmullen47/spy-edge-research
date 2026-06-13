from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from spy_edge_research.signal_engine import (
    add_recent_event_sequence_features,
    build_event_sequence,
    encode_recent_event_sequence,
    find_event_sequences,
    summarize_event_sequence_counts,
)


EVENT_COLUMNS = [
    "event_vwap_reclaim_bullish",
    "event_trailing_breakout_20",
    "event_vwap_loss_bearish",
]


def sample_sequence_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "timestamp": pd.date_range("2024-01-02 09:31", periods=5, freq="1min"),
            "event_vwap_reclaim_bullish": [True, False, True, False, np.nan],
            "event_trailing_breakout_20": [False, True, True, False, False],
            "event_vwap_loss_bearish": [False, False, False, True, False],
            "future_outcome_label": [0.01, -0.02, 0.03, 0.00, 0.01],
        },
        index=pd.Index(["a", "b", "c", "d", "e"], name="row"),
    )


def test_build_event_sequence_orders_events_by_row_and_column_without_mutation() -> None:
    df = sample_sequence_frame()
    original = df.copy(deep=True)

    sequence = build_event_sequence(df, EVENT_COLUMNS, timestamp_col="timestamp")

    assert sequence["sequence_index"].tolist() == [0, 1, 2, 3, 4]
    assert sequence["row_position"].tolist() == [0, 1, 2, 2, 3]
    assert sequence["row_label"].tolist() == ["a", "b", "c", "c", "d"]
    assert sequence["event_column"].tolist() == [
        "event_vwap_reclaim_bullish",
        "event_trailing_breakout_20",
        "event_vwap_reclaim_bullish",
        "event_trailing_breakout_20",
        "event_vwap_loss_bearish",
    ]
    assert sequence["timestamp"].tolist() == [
        pd.Timestamp("2024-01-02 09:31"),
        pd.Timestamp("2024-01-02 09:32"),
        pd.Timestamp("2024-01-02 09:33"),
        pd.Timestamp("2024-01-02 09:33"),
        pd.Timestamp("2024-01-02 09:34"),
    ]
    pd.testing.assert_frame_equal(df, original)


def test_find_event_sequences_matches_consecutive_event_tape_patterns() -> None:
    sequence = build_event_sequence(sample_sequence_frame(), EVENT_COLUMNS)

    matches = find_event_sequences(
        sequence,
        ["event_vwap_reclaim_bullish", "event_trailing_breakout_20"],
    )

    assert matches["pattern"].tolist() == [
        "event_vwap_reclaim_bullish>event_trailing_breakout_20",
        "event_vwap_reclaim_bullish>event_trailing_breakout_20",
    ]
    assert matches["start_sequence_index"].tolist() == [0, 2]
    assert matches["end_sequence_index"].tolist() == [1, 3]
    assert matches["start_row_position"].tolist() == [0, 2]
    assert matches["end_row_position"].tolist() == [1, 2]

    tight_span = find_event_sequences(
        sequence,
        ["event_vwap_reclaim_bullish", "event_trailing_breakout_20"],
        max_span_rows=0,
    )
    assert tight_span["start_sequence_index"].tolist() == [2]


def test_encode_recent_event_sequence_uses_only_past_and_current_rows() -> None:
    df = sample_sequence_frame()

    encoded = encode_recent_event_sequence(df, EVENT_COLUMNS, lookback_bars=2)

    assert encoded.tolist() == [
        "event_vwap_reclaim_bullish",
        "event_vwap_reclaim_bullish>event_trailing_breakout_20",
        "event_trailing_breakout_20>event_vwap_reclaim_bullish>event_trailing_breakout_20",
        "event_vwap_reclaim_bullish>event_trailing_breakout_20>event_vwap_loss_bearish",
        "event_vwap_loss_bearish",
    ]

    changed_future = df.copy(deep=True)
    changed_future.loc["e", "event_vwap_reclaim_bullish"] = True
    revised = encode_recent_event_sequence(changed_future, EVENT_COLUMNS, lookback_bars=2)

    assert revised.loc["a":"d"].tolist() == encoded.loc["a":"d"].tolist()
    assert revised.loc["e"] == "event_vwap_loss_bearish>event_vwap_reclaim_bullish"


def test_add_recent_event_sequence_features_adds_sequence_and_count() -> None:
    df = sample_sequence_frame()

    result = add_recent_event_sequence_features(
        df,
        EVENT_COLUMNS,
        lookback_bars=3,
        max_events=2,
    )

    assert "recent_event_sequence_3" in result.columns
    assert "recent_event_count_3" in result.columns
    assert result.loc["c", "recent_event_sequence_3"] == (
        "event_vwap_reclaim_bullish>event_trailing_breakout_20"
    )
    assert result.loc["c", "recent_event_count_3"] == 2
    assert "recent_event_sequence_3" not in df.columns


def test_summarize_event_sequence_counts_counts_encoded_sequences() -> None:
    df = sample_sequence_frame()
    enriched = add_recent_event_sequence_features(df, EVENT_COLUMNS, lookback_bars=1)

    counts = summarize_event_sequence_counts(enriched, "recent_event_sequence_1")

    assert counts["sequence_count"].sum() == len(df)
    assert counts.loc[counts["event_sequence"] == "", "sequence_count"].iloc[0] == 1
    assert counts["sequence_rate"].sum() == pytest.approx(1.0)


def test_event_sequence_helpers_validate_inputs() -> None:
    df = sample_sequence_frame()

    with pytest.raises(ValueError, match="Missing required columns"):
        build_event_sequence(df, ["missing_event"])
    with pytest.raises(ValueError, match="lookback_bars"):
        encode_recent_event_sequence(df, EVENT_COLUMNS, lookback_bars=0)
    with pytest.raises(ValueError, match="max_events"):
        encode_recent_event_sequence(df, EVENT_COLUMNS, lookback_bars=2, max_events=0)
    with pytest.raises(ValueError, match="sequence_column"):
        summarize_event_sequence_counts(pd.DataFrame({"sequence": ["a"]}))
    with pytest.raises(ValueError, match="pattern"):
        find_event_sequences(build_event_sequence(df, EVENT_COLUMNS), [])


def test_event_sequence_helpers_do_not_read_outcomes_or_create_signal_columns() -> None:
    df = sample_sequence_frame()
    without_outcome = df.drop(columns=["future_outcome_label"])

    sequence = build_event_sequence(without_outcome, EVENT_COLUMNS)
    enriched = add_recent_event_sequence_features(without_outcome, EVENT_COLUMNS, lookback_bars=2)

    assert len(sequence) == 5
    forbidden = ("buy", "sell", "entry", "exit", "confidence", "signal")
    assert not any(word in column for column in sequence.columns for word in forbidden)
    assert not any(word in column for column in enriched.columns for word in forbidden)
