"""Causal event sequence helpers.

Sequence features are derived only from already-created event columns at or
before the current row. They are research features, not trading signals.
"""

from __future__ import annotations

from collections.abc import Iterable

import pandas as pd


EVENT_SEQUENCE_COLUMNS: list[str] = [
    "sequence_index",
    "row_position",
    "row_label",
    "event_column",
]

EVENT_SEQUENCE_MATCH_COLUMNS: list[str] = [
    "pattern",
    "start_sequence_index",
    "end_sequence_index",
    "start_row_position",
    "end_row_position",
    "matched_sequence",
]


def build_event_sequence(
    df: pd.DataFrame,
    event_columns: Iterable[str],
    *,
    timestamp_col: str | None = None,
) -> pd.DataFrame:
    """Expand event columns into a causal event tape ordered by row."""
    events = _normalize_columns(event_columns, "event_columns")
    required = [*events]
    if timestamp_col is not None:
        required.append(timestamp_col)
    _require_columns(df, required)

    rows: list[dict[str, object]] = []
    sequence_index = 0
    for row_position, (row_label, row) in enumerate(df.iterrows()):
        for event_column in events:
            if _is_event_true(row[event_column]):
                record = {
                    "sequence_index": sequence_index,
                    "row_position": row_position,
                    "row_label": row_label,
                    "event_column": event_column,
                }
                if timestamp_col is not None:
                    record[timestamp_col] = row[timestamp_col]
                rows.append(record)
                sequence_index += 1

    columns = [*EVENT_SEQUENCE_COLUMNS]
    if timestamp_col is not None:
        columns.append(timestamp_col)
    return pd.DataFrame(rows, columns=columns)


def find_event_sequences(
    event_sequence: pd.DataFrame,
    pattern: Iterable[str],
    *,
    max_span_rows: int | None = None,
    separator: str = ">",
) -> pd.DataFrame:
    """Find consecutive event-tape patterns in an event sequence table."""
    pattern_events = _normalize_columns(pattern, "pattern")
    _validate_optional_non_negative_int(max_span_rows, "max_span_rows")
    _require_columns(event_sequence, EVENT_SEQUENCE_COLUMNS)

    rows = []
    event_names = event_sequence["event_column"].tolist()
    pattern_length = len(pattern_events)
    for start in range(0, len(event_names) - pattern_length + 1):
        end = start + pattern_length
        if event_names[start:end] != pattern_events:
            continue
        window = event_sequence.iloc[start:end]
        start_row_position = int(window["row_position"].iloc[0])
        end_row_position = int(window["row_position"].iloc[-1])
        if max_span_rows is not None and end_row_position - start_row_position > max_span_rows:
            continue
        rows.append(
            {
                "pattern": separator.join(pattern_events),
                "start_sequence_index": int(window["sequence_index"].iloc[0]),
                "end_sequence_index": int(window["sequence_index"].iloc[-1]),
                "start_row_position": start_row_position,
                "end_row_position": end_row_position,
                "matched_sequence": separator.join(window["event_column"].tolist()),
            }
        )
    return pd.DataFrame(rows, columns=EVENT_SEQUENCE_MATCH_COLUMNS)


def encode_recent_event_sequence(
    df: pd.DataFrame,
    event_columns: Iterable[str],
    *,
    lookback_bars: int,
    max_events: int | None = None,
    separator: str = ">",
) -> pd.Series:
    """Encode events observed from the trailing/current row window."""
    events = _normalize_columns(event_columns, "event_columns")
    _require_columns(df, events)
    _validate_positive_int(lookback_bars, "lookback_bars")
    _validate_optional_positive_int(max_events, "max_events")

    encoded: list[str] = []
    for row_position in range(len(df)):
        start = max(0, row_position - lookback_bars + 1)
        recent_events: list[str] = []
        window = df.iloc[start : row_position + 1]
        for _, row in window.iterrows():
            for event_column in events:
                if _is_event_true(row[event_column]):
                    recent_events.append(event_column)
        if max_events is not None:
            recent_events = recent_events[-max_events:]
        encoded.append(separator.join(recent_events))
    return pd.Series(encoded, index=df.index, name=f"recent_event_sequence_{lookback_bars}")


def add_recent_event_sequence_features(
    df: pd.DataFrame,
    event_columns: Iterable[str],
    *,
    lookback_bars: int,
    max_events: int | None = None,
    separator: str = ">",
    output_prefix: str = "recent_event",
) -> pd.DataFrame:
    """Add causal recent-event sequence and count features."""
    if not isinstance(output_prefix, str) or not output_prefix:
        raise ValueError("output_prefix must be a non-empty string")

    sequence = encode_recent_event_sequence(
        df,
        event_columns,
        lookback_bars=lookback_bars,
        max_events=max_events,
        separator=separator,
    )
    result = df.copy()
    sequence_col = f"{output_prefix}_sequence_{lookback_bars}"
    count_col = f"{output_prefix}_count_{lookback_bars}"
    result[sequence_col] = sequence
    result[count_col] = sequence.map(lambda value: 0 if value == "" else len(value.split(separator)))
    return result


def summarize_event_sequence_counts(
    sequences: pd.Series | pd.DataFrame,
    sequence_column: str | None = None,
) -> pd.DataFrame:
    """Count encoded event sequence frequencies."""
    if isinstance(sequences, pd.DataFrame):
        if sequence_column is None:
            raise ValueError("sequence_column is required when sequences is a DataFrame")
        _require_columns(sequences, [sequence_column])
        values = sequences[sequence_column]
    else:
        values = sequences

    counts = values.fillna("").value_counts(dropna=False).rename_axis("event_sequence")
    result = counts.reset_index(name="sequence_count")
    total = int(result["sequence_count"].sum())
    result["sequence_rate"] = result["sequence_count"] / total if total else pd.NA
    return result


def _normalize_columns(columns: Iterable[str], name: str) -> list[str]:
    if isinstance(columns, str):
        normalized = [columns]
    else:
        normalized = list(columns)
    if not normalized or not all(isinstance(column, str) and column for column in normalized):
        raise ValueError(f"{name} must contain at least one column name")
    return normalized


def _is_event_true(value: object) -> bool:
    if pd.isna(value):
        return False
    return bool(value)


def _require_columns(df: pd.DataFrame, columns: list[str]) -> None:
    missing = [column for column in columns if column not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")


def _validate_positive_int(value: int, name: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise ValueError(f"{name} must be an integer greater than or equal to 1")


def _validate_optional_positive_int(value: int | None, name: str) -> None:
    if value is not None:
        _validate_positive_int(value, name)


def _validate_optional_non_negative_int(value: int | None, name: str) -> None:
    if value is not None and (
        not isinstance(value, int) or isinstance(value, bool) or value < 0
    ):
        raise ValueError(f"{name} must be an integer greater than or equal to 0")
