from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping

import pandas as pd


@dataclass(frozen=True)
class EventDefinition:
    """Defines how one wide feature column becomes named events."""

    feature: str
    name: str
    label: str | None = None
    side: str | None = None
    color: str | None = None
    marker: str | None = None
    threshold: float | None = None
    direction: str = "nonzero"
    metadata: Mapping[str, Any] | None = None


def build_event_catalog(definitions: Iterable[EventDefinition]) -> pd.DataFrame:
    """Convert event definitions into a normalized event catalog."""

    rows: list[dict[str, Any]] = []
    for definition in definitions:
        rows.append(
            {
                "feature": definition.feature,
                "event_name": definition.name,
                "label": definition.label or definition.name,
                "side": definition.side,
                "color": definition.color,
                "marker": definition.marker,
                "threshold": definition.threshold,
                "direction": definition.direction,
                "metadata": dict(definition.metadata or {}),
            }
        )

    catalog = pd.DataFrame(rows)
    if catalog.empty:
        return pd.DataFrame(
            columns=[
                "feature",
                "event_name",
                "label",
                "side",
                "color",
                "marker",
                "threshold",
                "direction",
                "metadata",
            ]
        )

    duplicate_names = catalog["event_name"][catalog["event_name"].duplicated()].unique()
    if len(duplicate_names):
        names = ", ".join(sorted(duplicate_names))
        raise ValueError(f"duplicate event names in catalog: {names}")

    return catalog


def infer_event_catalog(
    features: pd.DataFrame,
    *,
    feature_columns: Iterable[str] | None = None,
    prefix: str = "",
) -> pd.DataFrame:
    """Create a catalog directly from dataframe columns."""

    columns = list(feature_columns or features.columns)
    definitions = [
        EventDefinition(
            feature=column,
            name=f"{prefix}{column}",
            label=column.replace("_", " ").title(),
        )
        for column in columns
    ]
    return build_event_catalog(definitions)


def build_event_tape(
    features: pd.DataFrame,
    catalog: pd.DataFrame,
    *,
    timestamp_column: str | None = None,
    value_column: str = "value",
) -> pd.DataFrame:
    """Expand a wide feature dataframe into one row per triggered event."""

    working = features.copy()
    if timestamp_column is None:
        working = working.reset_index(names="timestamp")
        timestamp_column = "timestamp"

    required_catalog_columns = {"feature", "event_name", "label", "threshold", "direction"}
    missing = required_catalog_columns.difference(catalog.columns)
    if missing:
        raise ValueError(f"catalog missing required columns: {', '.join(sorted(missing))}")

    rows: list[pd.DataFrame] = []
    for event in catalog.to_dict("records"):
        feature = event["feature"]
        if feature not in working.columns:
            raise ValueError(f"feature column not found in dataframe: {feature}")

        values = working[feature]
        mask = _event_mask(values, event.get("direction"), event.get("threshold"))
        if not mask.any():
            continue

        tape = working.loc[mask, [timestamp_column]].copy()
        tape["event_name"] = event["event_name"]
        tape["label"] = event["label"]
        tape["feature"] = feature
        tape[value_column] = values.loc[mask].to_numpy()

        for optional_column in ("side", "color", "marker", "metadata"):
            if optional_column in catalog.columns:
                tape[optional_column] = [event.get(optional_column)] * len(tape)

        rows.append(tape)

    if not rows:
        return pd.DataFrame(
            columns=[
                timestamp_column,
                "event_name",
                "label",
                "feature",
                value_column,
                "side",
                "color",
                "marker",
                "metadata",
            ]
        )

    event_tape = pd.concat(rows, ignore_index=True)
    return event_tape.sort_values([timestamp_column, "event_name"]).reset_index(drop=True)


def build_chart_annotations(
    event_tape: pd.DataFrame,
    *,
    timestamp_column: str = "timestamp",
    price_lookup: pd.Series | Mapping[Any, float] | None = None,
) -> pd.DataFrame:
    """Convert event-tape rows into chart annotation records."""

    required_columns = {timestamp_column, "event_name", "label"}
    missing = required_columns.difference(event_tape.columns)
    if missing:
        raise ValueError(f"event tape missing required columns: {', '.join(sorted(missing))}")

    annotations = event_tape.copy()
    annotations = annotations.rename(
        columns={
            timestamp_column: "x",
            "label": "text",
            "event_name": "id",
        }
    )

    if price_lookup is not None:
        lookup = pd.Series(price_lookup)
        annotations["y"] = annotations["x"].map(lookup)

    output_columns = ["x", "id", "text"]
    for column in ("y", "side", "color", "marker", "feature", "value", "metadata"):
        if column in annotations.columns:
            output_columns.append(column)

    return annotations[output_columns].reset_index(drop=True)


def wide_features_to_chart_annotations(
    features: pd.DataFrame,
    definitions: Iterable[EventDefinition] | None = None,
    *,
    timestamp_column: str | None = None,
    price_lookup: pd.Series | Mapping[Any, float] | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Run the full dataframe -> catalog -> tape -> annotations pipeline."""

    catalog = (
        build_event_catalog(definitions)
        if definitions is not None
        else infer_event_catalog(
            features.drop(columns=[timestamp_column], errors="ignore")
            if timestamp_column
            else features
        )
    )
    tape = build_event_tape(features, catalog, timestamp_column=timestamp_column)
    annotations = build_chart_annotations(
        tape,
        timestamp_column=timestamp_column or "timestamp",
        price_lookup=price_lookup,
    )
    return catalog, tape, annotations


def _event_mask(
    values: pd.Series,
    direction: str | None,
    threshold: float | None,
) -> pd.Series:
    direction = direction or "nonzero"

    if direction == "nonzero":
        return values.fillna(0).ne(0)
    if direction == "truthy":
        return values.fillna(False).astype(bool)
    if direction == "above":
        if threshold is None:
            raise ValueError("direction='above' requires threshold")
        return values.gt(threshold)
    if direction == "at_or_above":
        if threshold is None:
            raise ValueError("direction='at_or_above' requires threshold")
        return values.ge(threshold)
    if direction == "below":
        if threshold is None:
            raise ValueError("direction='below' requires threshold")
        return values.lt(threshold)
    if direction == "at_or_below":
        if threshold is None:
            raise ValueError("direction='at_or_below' requires threshold")
        return values.le(threshold)

    raise ValueError(f"unknown event direction: {direction}")
