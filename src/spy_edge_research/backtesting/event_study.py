"""Research-only named-event study utilities.

Event-study functions may read forward-looking label columns because they are
evaluation utilities. They do not generate causal features, trade signals,
rankings, optimization results, or edge claims.
"""

from __future__ import annotations

from collections.abc import Iterable

import numpy as np
import pandas as pd

from spy_edge_research.signal_engine.event_catalog import (
    build_named_event_catalog,
    validate_event_catalog,
)

from spy_edge_research._internal._common import (
    normalize_columns as _normalize_columns,
    require_columns as _require_columns,
)

EVENT_STUDY_COLUMNS: list[str] = [
    "event_column",
    "event_family",
    "event_direction",
    "label_column",
    "event_count",
    "event_rate",
    "label_mean_on_event",
    "overall_label_mean",
    "difference_from_overall",
]

FREQUENCY_COLUMNS: list[str] = [
    "event_column",
    "event_family",
    "event_direction",
    "event_count",
    "event_rate",
]

REGIME_COLUMNS: list[str] = [
    "event_column",
    "event_family",
    "event_direction",
    "regime",
    "regime_count",
    "event_count",
    "event_rate",
]


def evaluate_event_column(
    df: pd.DataFrame,
    event_column: str,
    label_columns: Iterable[str],
    *,
    min_events: int = 1,
) -> pd.DataFrame:
    """Evaluate one event column against one or more existing label columns."""
    _validate_min_events(min_events)
    labels = _normalize_columns(label_columns, "label_columns")
    _require_columns(df, [event_column, *labels])

    event_occurs = df[event_column].fillna(False).astype(bool)
    event_count = int(event_occurs.sum())
    event_rate = np.nan if len(df) == 0 else event_count / len(df)

    rows = []
    for label_column in labels:
        label_values = pd.to_numeric(df[label_column], errors="coerce")
        if event_count < min_events:
            label_mean_on_event = np.nan
            difference_from_overall = np.nan
        else:
            label_mean_on_event = float(label_values.loc[event_occurs].mean())
            difference_from_overall = label_mean_on_event - float(label_values.mean())
        rows.append(
            {
                "event_column": event_column,
                "event_family": "unknown",
                "event_direction": "unknown",
                "label_column": label_column,
                "event_count": event_count,
                "event_rate": event_rate,
                "label_mean_on_event": label_mean_on_event,
                "overall_label_mean": float(label_values.mean()),
                "difference_from_overall": difference_from_overall,
            }
        )
    return pd.DataFrame(rows, columns=EVENT_STUDY_COLUMNS)


def evaluate_event_catalog(
    df: pd.DataFrame,
    catalog: pd.DataFrame,
    label_columns: Iterable[str],
    *,
    min_events: int = 1,
) -> pd.DataFrame:
    """Evaluate every event in a validated catalog against label columns."""
    _validate_min_events(min_events)
    labels = _normalize_columns(label_columns, "label_columns")
    validated = validate_event_catalog(catalog)
    _require_columns(df, labels)
    if validated.empty:
        return pd.DataFrame(columns=EVENT_STUDY_COLUMNS)

    rows: list[dict[str, float | int | str]] = []
    for event in validated.itertuples(index=False):
        event_column = event.event_column
        _require_columns(df, [event_column])
        event_occurs = df[event_column].fillna(False).astype(bool)
        event_count = int(event_occurs.sum())
        event_rate = np.nan if len(df) == 0 else event_count / len(df)

        for label_column in labels:
            label_values = pd.to_numeric(df[label_column], errors="coerce")
            overall_label_mean = float(label_values.mean())
            if event_count < min_events:
                label_mean_on_event = np.nan
                difference_from_overall = np.nan
            else:
                label_mean_on_event = float(label_values.loc[event_occurs].mean())
                difference_from_overall = label_mean_on_event - overall_label_mean
            rows.append(
                {
                    "event_column": event_column,
                    "event_family": event.event_family,
                    "event_direction": event.event_direction,
                    "label_column": label_column,
                    "event_count": event_count,
                    "event_rate": event_rate,
                    "label_mean_on_event": label_mean_on_event,
                    "overall_label_mean": overall_label_mean,
                    "difference_from_overall": difference_from_overall,
                }
            )
    return pd.DataFrame(rows, columns=EVENT_STUDY_COLUMNS)


def evaluate_named_events(
    df: pd.DataFrame,
    label_columns: Iterable[str],
    event_columns: Iterable[str] | None = None,
    catalog: pd.DataFrame | None = None,
    *,
    min_events: int = 1,
) -> pd.DataFrame:
    """Build or validate a catalog, then run a research-only event study."""
    if catalog is None:
        catalog = build_named_event_catalog(df=df, event_columns=event_columns)
    else:
        catalog = validate_event_catalog(catalog)
    return evaluate_event_catalog(
        df,
        catalog,
        label_columns,
        min_events=min_events,
    )


def event_frequency_summary(
    df: pd.DataFrame,
    catalog: pd.DataFrame,
) -> pd.DataFrame:
    """Return event occurrence frequencies without reading label columns."""
    validated = validate_event_catalog(catalog)
    rows = []
    for event in validated.itertuples(index=False):
        event_column = event.event_column
        _require_columns(df, [event_column])
        event_count = int(df[event_column].fillna(False).astype(bool).sum())
        rows.append(
            {
                "event_column": event_column,
                "event_family": event.event_family,
                "event_direction": event.event_direction,
                "event_count": event_count,
                "event_rate": np.nan if len(df) == 0 else event_count / len(df),
            }
        )
    return pd.DataFrame(rows, columns=FREQUENCY_COLUMNS)


def event_regime_summary(
    df: pd.DataFrame,
    catalog: pd.DataFrame,
    regime_column: str,
) -> pd.DataFrame:
    """Summarize event frequency by an existing causal regime/context column."""
    validated = validate_event_catalog(catalog)
    _require_columns(df, [regime_column])

    rows = []
    for event in validated.itertuples(index=False):
        event_column = event.event_column
        _require_columns(df, [event_column])
        event_occurs = df[event_column].fillna(False).astype(bool)
        for regime, regime_df in df.groupby(regime_column, dropna=False, sort=False):
            regime_count = len(regime_df)
            event_count = int(event_occurs.loc[regime_df.index].sum())
            rows.append(
                {
                    "event_column": event_column,
                    "event_family": event.event_family,
                    "event_direction": event.event_direction,
                    "regime": regime,
                    "regime_count": regime_count,
                    "event_count": event_count,
                    "event_rate": np.nan
                    if regime_count == 0
                    else event_count / regime_count,
                }
            )
    return pd.DataFrame(rows, columns=REGIME_COLUMNS)


def _validate_min_events(min_events: int) -> None:
    if not isinstance(min_events, int) or isinstance(min_events, bool) or min_events < 1:
        raise ValueError("min_events must be an integer greater than or equal to 1")
