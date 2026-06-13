"""Read-only service facade over the event-research workflow.

Runs the existing event-research workflow and returns a structured, JSON-friendly
service response, plus a thin export helper. This is research orchestration only:
it reads an in-memory DataFrame, never fetches live data, and produces no trade
instructions, signals, or execution outputs.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from spy_edge_research.backtesting.event_workflows import (
    build_event_research_workflow_outputs,
    export_event_research_workflow_outputs,
    get_event_research_workflow_table_names,
    validate_event_research_workflow_outputs,
)


@dataclass(frozen=True)
class WorkflowServiceResponse:
    """A structured response from the event-research workflow service."""

    outputs: dict[str, Any]
    table_names: list[str]
    report_summary: pd.DataFrame


def run_event_research_workflow_service(
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
) -> WorkflowServiceResponse:
    """Run the event-research workflow and return a structured service response."""
    outputs = build_event_research_workflow_outputs(
        df,
        label_columns=label_columns,
        event_columns=event_columns,
        catalog=catalog,
        regime_column=regime_column,
        min_events=min_events,
        min_event_rate=min_event_rate,
        group_columns=group_columns,
        metadata=metadata,
    )
    validate_event_research_workflow_outputs(outputs)
    return WorkflowServiceResponse(
        outputs=outputs,
        table_names=get_event_research_workflow_table_names(outputs),
        report_summary=outputs["report_summary"].copy(),
    )


def export_workflow_service_response(
    response: WorkflowServiceResponse,
    output_dir: str | Path,
    *,
    overwrite: bool = False,
) -> dict[str, Path]:
    """Export a workflow service response's report bundle to CSV artifacts."""
    if not isinstance(response, WorkflowServiceResponse):
        raise TypeError("response must be a WorkflowServiceResponse")
    return export_event_research_workflow_outputs(
        response.outputs,
        output_dir,
        overwrite=overwrite,
    )
