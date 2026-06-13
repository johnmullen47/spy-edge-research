"""Research-only event-study workflow composition helpers.

These helpers compose existing catalog, event-study, diagnostics, reporting,
and visualization-prep utilities into reproducible research artifacts. They do
not create causal features, trade signals, rankings, optimizations, or edge
claims.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

import pandas as pd

from spy_edge_research.backtesting.event_diagnostics import diagnose_event_study
from spy_edge_research.backtesting.event_reports import (
    build_event_study_report_bundle,
    create_research_run_metadata,
    export_report_bundle_to_csv,
    summarize_report_bundle,
)
from spy_edge_research.backtesting.event_study import (
    evaluate_event_catalog,
    event_frequency_summary,
    event_regime_summary,
)
from spy_edge_research.backtesting.event_visualizations import (
    build_event_study_visualization_bundle,
)
from spy_edge_research.signal_engine.event_catalog import (
    build_named_event_catalog,
    validate_event_catalog,
)

WORKFLOW_REQUIRED_KEYS: tuple[str, ...] = (
    "catalog",
    "event_study_results",
    "diagnostics",
    "frequency_summary",
    "visualization_bundle",
    "report_bundle",
    "report_summary",
    "metadata",
)


def build_event_research_workflow_outputs(
    df: pd.DataFrame,
    *,
    label_columns: Iterable[str],
    event_columns: Iterable[str] | None = None,
    catalog: pd.DataFrame | None = None,
    regime_column: str | None = None,
    min_events: int = 10,
    min_event_rate: float | None = None,
    group_columns: Iterable[str] | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Run the research-only event-study artifact workflow.

    The returned dictionary contains deterministic tables and bundles. The
    input DataFrame is read only, no files are written, and no plots are
    created.
    """
    labels = _normalize_columns(label_columns, "label_columns")
    groups = None if group_columns is None else _normalize_columns(group_columns, "group_columns")

    if catalog is None:
        workflow_catalog = build_named_event_catalog(df=df, event_columns=event_columns)
    else:
        workflow_catalog = validate_event_catalog(catalog)
    workflow_catalog = validate_event_catalog(workflow_catalog)
    events = workflow_catalog["event_column"].tolist()

    workflow_metadata = create_event_research_metadata(
        label_columns=labels,
        event_columns=events,
    )
    workflow_metadata.update(dict(metadata or {}))
    workflow_metadata.setdefault("label_columns", labels)
    workflow_metadata.setdefault("event_columns", events)

    event_study_results = evaluate_event_catalog(
        df,
        workflow_catalog,
        labels,
        min_events=min_events,
    )
    diagnostics = diagnose_event_study(
        df,
        event_study_results,
        label_columns=labels,
        event_columns=events,
        min_events=min_events,
        min_event_rate=min_event_rate,
        group_columns=groups,
    )
    frequency_summary = event_frequency_summary(df, workflow_catalog)

    outputs: dict[str, Any] = {
        "catalog": workflow_catalog.copy(),
        "event_study_results": event_study_results,
        "diagnostics": diagnostics,
        "frequency_summary": frequency_summary,
        "metadata": workflow_metadata,
    }
    if regime_column is not None:
        outputs["regime_summary"] = event_regime_summary(df, workflow_catalog, regime_column)

    report_bundle = build_event_study_report_bundle(
        event_study_results,
        diagnostics=diagnostics["results_with_sample_flags"],
        label_coverage=diagnostics["label_coverage"],
        event_coverage=diagnostics.get("event_coverage"),
        grouped_summary=diagnostics.get("grouped_summary"),
        metadata=workflow_metadata,
    )
    visualization_bundle = build_event_study_visualization_bundle(
        event_study_results=event_study_results,
        label_coverage=diagnostics["label_coverage"],
        event_coverage=diagnostics.get("event_coverage"),
        grouped_summary=diagnostics.get("grouped_summary"),
        metadata=workflow_metadata,
        group_columns=groups,
    )

    outputs["visualization_bundle"] = visualization_bundle
    outputs["report_bundle"] = report_bundle
    outputs["report_summary"] = summarize_report_bundle(report_bundle)
    return outputs


def create_event_research_metadata(
    *,
    project_name: str = "SPY Directional Edge Research",
    workflow_name: str = "event_research_workflow",
    milestone: str = "15",
    label_columns: Iterable[str] | None = None,
    event_columns: Iterable[str] | None = None,
    notes: str | None = None,
) -> dict[str, Any]:
    """Create workflow-level metadata for research artifacts."""
    metadata = create_research_run_metadata(
        project_name=project_name,
        milestone=milestone,
        label_columns=label_columns,
        notes=notes,
    )
    metadata["workflow_name"] = workflow_name
    if event_columns is not None:
        metadata["event_columns"] = list(event_columns)
    return metadata


def validate_event_research_workflow_outputs(outputs: dict[str, Any]) -> dict[str, Any]:
    """Validate the expected workflow output dictionary structure."""
    if not isinstance(outputs, dict):
        raise TypeError("outputs must be a dict")

    missing = [key for key in WORKFLOW_REQUIRED_KEYS if key not in outputs]
    if missing:
        raise KeyError(f"outputs is missing required keys: {missing}")

    _require_dataframe(outputs["catalog"], "catalog")
    _require_dataframe(outputs["event_study_results"], "event_study_results")
    _require_dataframe(outputs["frequency_summary"], "frequency_summary")
    _require_dataframe(outputs["report_summary"], "report_summary")
    if "regime_summary" in outputs:
        _require_dataframe(outputs["regime_summary"], "regime_summary")

    diagnostics = outputs["diagnostics"]
    if not isinstance(diagnostics, Mapping):
        raise TypeError("diagnostics must be a mapping")
    for table_name, table in diagnostics.items():
        _require_dataframe(table, f"diagnostics.{table_name}")

    _validate_bundle(outputs["report_bundle"], "report_bundle")
    _validate_bundle(outputs["visualization_bundle"], "visualization_bundle")

    if not isinstance(outputs["metadata"], Mapping):
        raise TypeError("metadata must be a mapping")
    return outputs


def export_event_research_workflow_outputs(
    outputs: dict[str, Any],
    output_dir: str | Path,
    *,
    overwrite: bool = False,
) -> dict[str, Path]:
    """Export workflow report-bundle tables and metadata to CSV artifacts."""
    validate_event_research_workflow_outputs(outputs)
    return export_report_bundle_to_csv(
        outputs["report_bundle"],
        output_dir,
        overwrite=overwrite,
    )


def get_event_research_workflow_table_names(outputs: dict[str, Any]) -> list[str]:
    """Return sorted names of DataFrame/table artifacts in workflow outputs."""
    validate_event_research_workflow_outputs(outputs)

    table_names = {
        key for key, value in outputs.items() if isinstance(value, pd.DataFrame)
    }
    table_names.update(f"diagnostics.{name}" for name in outputs["diagnostics"])
    table_names.update(f"report_bundle.{name}" for name in outputs["report_bundle"]["tables"])
    table_names.update(
        f"visualization_bundle.{name}" for name in outputs["visualization_bundle"]["tables"]
    )
    return sorted(table_names)


def _validate_bundle(bundle: Any, bundle_name: str) -> None:
    if not isinstance(bundle, Mapping):
        raise TypeError(f"{bundle_name} must be a mapping")
    tables = bundle.get("tables")
    if not isinstance(tables, Mapping):
        raise KeyError(f"{bundle_name} must contain a tables mapping")
    for table_name, table in tables.items():
        _require_dataframe(table, f"{bundle_name}.{table_name}")
    metadata = bundle.get("metadata", {})
    if metadata is not None and not isinstance(metadata, Mapping):
        raise TypeError(f"{bundle_name} metadata must be a mapping")


def _require_dataframe(value: Any, name: str) -> None:
    if not isinstance(value, pd.DataFrame):
        raise TypeError(f"{name} must be a pandas DataFrame")


def _normalize_columns(columns: Iterable[str], name: str) -> list[str]:
    if isinstance(columns, str):
        normalized = [columns]
    else:
        normalized = list(columns)
    if not normalized or not all(isinstance(column, str) and column for column in normalized):
        raise ValueError(f"{name} must contain at least one column name")
    return normalized
