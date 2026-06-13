"""Research-only visualization helpers for event-study artifacts.

These helpers prepare deterministic tables and optional matplotlib charts from
existing event-study and diagnostic outputs. They do not create causal features,
trade signals, rankings, optimizations, or edge claims.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

import pandas as pd

EVENT_COUNT_COLUMNS: list[str] = ["event_column", "label_column", "event_count", "event_rate"]
LABEL_COVERAGE_COLUMNS: list[str] = [
    "label_column",
    "row_count",
    "non_missing_count",
    "missing_count",
    "non_missing_rate",
    "missing_rate",
]
EVENT_COVERAGE_COLUMNS: list[str] = [
    "event_column",
    "row_count",
    "true_count",
    "false_count",
    "missing_count",
    "true_rate",
    "missing_rate",
]
GROUPED_EVENT_COUNT_COLUMNS: list[str] = [
    "total_event_count",
    "mean_event_rate",
    "row_count",
]


def validate_visualization_table(
    table: pd.DataFrame,
    *,
    required_columns: Iterable[str] | None = None,
    table_name: str = "table",
) -> pd.DataFrame:
    """Validate that a DataFrame can be used by visualization helpers."""
    if not isinstance(table_name, str) or not table_name:
        raise ValueError("table_name must be a non-empty string")
    if not isinstance(table, pd.DataFrame):
        raise TypeError(f"{table_name} must be a pandas DataFrame")

    if required_columns is not None:
        columns = _normalize_columns(required_columns, "required_columns")
        missing = [column for column in columns if column not in table.columns]
        if missing:
            raise KeyError(f"{table_name} is missing required columns: {missing}")

    return table


def prepare_event_count_table(
    results: pd.DataFrame,
    *,
    group_columns: Iterable[str] | None = None,
) -> pd.DataFrame:
    """Prepare deterministic event-count summaries for visualization."""
    validate_visualization_table(
        results,
        required_columns=EVENT_COUNT_COLUMNS,
        table_name="event_study_results",
    )

    if group_columns is None:
        identity_columns = [
            column
            for column in ["event_column", "event_family", "event_direction", "label_column"]
            if column in results.columns
        ]
        output_columns = [*identity_columns, "event_count", "event_rate"]
        prepared = results.loc[:, output_columns].copy()
        return _sort_copy(prepared, identity_columns)

    groups = _normalize_columns(group_columns, "group_columns")
    validate_visualization_table(
        results,
        required_columns=[*groups, "event_count", "event_rate"],
        table_name="event_study_results",
    )
    if results.empty:
        return pd.DataFrame(columns=[*groups, *GROUPED_EVENT_COUNT_COLUMNS])

    summary = (
        results.groupby(groups, dropna=False, sort=True)
        .agg(
            total_event_count=("event_count", "sum"),
            mean_event_rate=("event_rate", "mean"),
            row_count=("event_count", "size"),
        )
        .reset_index()
    )
    return summary.loc[:, [*groups, *GROUPED_EVENT_COUNT_COLUMNS]]


def prepare_label_coverage_table(
    label_coverage: pd.DataFrame,
    *,
    round_decimals: int | None = None,
) -> pd.DataFrame:
    """Prepare label coverage diagnostics for deterministic visualization."""
    validate_visualization_table(
        label_coverage,
        required_columns=LABEL_COVERAGE_COLUMNS,
        table_name="label_coverage",
    )
    prepared = _sort_copy(label_coverage.copy(), ["label_column"])
    return _round_float_columns(prepared, round_decimals)


def prepare_event_coverage_table(
    event_coverage: pd.DataFrame,
    *,
    round_decimals: int | None = None,
) -> pd.DataFrame:
    """Prepare event coverage diagnostics for deterministic visualization."""
    validate_visualization_table(
        event_coverage,
        required_columns=EVENT_COVERAGE_COLUMNS,
        table_name="event_coverage",
    )
    prepared = _sort_copy(event_coverage.copy(), ["event_column"])
    return _round_float_columns(prepared, round_decimals)


def prepare_grouped_summary_table(
    grouped_summary: pd.DataFrame,
    *,
    group_columns: Iterable[str],
) -> pd.DataFrame:
    """Prepare grouped event-study summaries sorted by group identity only."""
    groups = _normalize_columns(group_columns, "group_columns")
    validate_visualization_table(
        grouped_summary,
        required_columns=groups,
        table_name="grouped_summary",
    )
    return _sort_copy(grouped_summary.copy(), groups)


def build_event_study_visualization_bundle(
    *,
    event_study_results: pd.DataFrame | None = None,
    label_coverage: pd.DataFrame | None = None,
    event_coverage: pd.DataFrame | None = None,
    grouped_summary: pd.DataFrame | None = None,
    metadata: Mapping[str, Any] | None = None,
    group_columns: Iterable[str] | None = None,
) -> dict[str, Any]:
    """Build visualization-ready tables and metadata from research artifacts."""
    tables: dict[str, pd.DataFrame] = {}

    if event_study_results is not None:
        tables["event_counts"] = prepare_event_count_table(
            event_study_results,
            group_columns=group_columns,
        )
    if label_coverage is not None:
        tables["label_coverage"] = prepare_label_coverage_table(label_coverage)
    if event_coverage is not None:
        tables["event_coverage"] = prepare_event_coverage_table(event_coverage)
    if grouped_summary is not None:
        if group_columns is None:
            tables["grouped_summary"] = validate_visualization_table(
                grouped_summary,
                table_name="grouped_summary",
            ).copy()
        else:
            tables["grouped_summary"] = prepare_grouped_summary_table(
                grouped_summary,
                group_columns=group_columns,
            )

    return {
        "metadata": dict(metadata or {}),
        "tables": tables,
    }


def plot_event_counts(
    event_count_table: pd.DataFrame,
    *,
    ax: Any | None = None,
    title: str | None = None,
) -> Any:
    """Plot event counts as a simple matplotlib bar chart."""
    table = validate_visualization_table(event_count_table, table_name="event_count_table")
    count_column = _first_existing_column(table, ["event_count", "total_event_count"])
    if count_column is None:
        raise KeyError("event_count_table must contain event_count or total_event_count")
    labels = _display_labels(table, excluded_columns={count_column, "event_rate", "mean_event_rate", "row_count"})
    return _bar_chart(table, labels, [count_column], ax=ax, title=title, ylabel="count")


def plot_label_coverage(
    label_coverage_table: pd.DataFrame,
    *,
    ax: Any | None = None,
    title: str | None = None,
) -> Any:
    """Plot non-missing and missing label coverage as a bar chart."""
    table = validate_visualization_table(
        label_coverage_table,
        required_columns=["label_column", "non_missing_count", "missing_count"],
        table_name="label_coverage_table",
    )
    return _bar_chart(
        table,
        table["label_column"].astype(str).tolist(),
        ["non_missing_count", "missing_count"],
        ax=ax,
        title=title,
        ylabel="rows",
    )


def plot_event_coverage(
    event_coverage_table: pd.DataFrame,
    *,
    ax: Any | None = None,
    title: str | None = None,
) -> Any:
    """Plot true and missing event coverage as a bar chart."""
    table = validate_visualization_table(
        event_coverage_table,
        required_columns=["event_column", "true_count", "missing_count"],
        table_name="event_coverage_table",
    )
    return _bar_chart(
        table,
        table["event_column"].astype(str).tolist(),
        ["true_count", "missing_count"],
        ax=ax,
        title=title,
        ylabel="rows",
    )


def _bar_chart(
    table: pd.DataFrame,
    labels: list[str],
    value_columns: list[str],
    *,
    ax: Any | None,
    title: str | None,
    ylabel: str,
) -> Any:
    import matplotlib.pyplot as plt

    if ax is None:
        _, ax = plt.subplots()

    x_positions = list(range(len(table)))
    if len(value_columns) == 1:
        ax.bar(x_positions, pd.to_numeric(table[value_columns[0]], errors="coerce"))
    else:
        width = 0.8 / len(value_columns)
        start = -0.4 + width / 2
        for offset, column in enumerate(value_columns):
            positions = [x + start + offset * width for x in x_positions]
            ax.bar(positions, pd.to_numeric(table[column], errors="coerce"), width=width, label=column)
        ax.legend()

    ax.set_xticks(x_positions)
    ax.set_xticklabels(labels, rotation=45, ha="right")
    ax.set_ylabel(ylabel)
    if title is not None:
        ax.set_title(title)
    return ax


def _display_labels(table: pd.DataFrame, *, excluded_columns: set[str]) -> list[str]:
    if "event_column" in table.columns:
        if "label_column" in table.columns and table["event_column"].duplicated(keep=False).any():
            return (
                table["event_column"].astype(str) + " | " + table["label_column"].astype(str)
            ).tolist()
        return table["event_column"].astype(str).tolist()

    label_columns = [column for column in table.columns if column not in excluded_columns]
    return table.loc[:, label_columns].astype(str).agg(" | ".join, axis=1).tolist()


def _first_existing_column(table: pd.DataFrame, columns: list[str]) -> str | None:
    for column in columns:
        if column in table.columns:
            return column
    return None


def _sort_copy(table: pd.DataFrame, sort_columns: list[str]) -> pd.DataFrame:
    if not sort_columns:
        return table.copy().reset_index(drop=True)
    return table.sort_values(sort_columns, kind="mergesort").reset_index(drop=True)


def _round_float_columns(table: pd.DataFrame, round_decimals: int | None) -> pd.DataFrame:
    if round_decimals is None:
        return table
    if not isinstance(round_decimals, int) or isinstance(round_decimals, bool):
        raise ValueError("round_decimals must be an integer when provided")
    float_columns = table.select_dtypes(include=["float"]).columns
    table.loc[:, float_columns] = table.loc[:, float_columns].round(round_decimals)
    return table


def _normalize_columns(columns: Iterable[str], name: str) -> list[str]:
    if isinstance(columns, str):
        normalized = [columns]
    else:
        normalized = list(columns)
    if not normalized or not all(isinstance(column, str) and column for column in normalized):
        raise ValueError(f"{name} must contain at least one column name")
    return normalized
