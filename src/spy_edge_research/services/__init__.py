"""Read-only, offline research service layer.

Programmatic access to committed research artifacts (report bundles) and a thin
facade over the event-research workflow. No live data, no write/mutate
endpoints, and nothing execution-adjacent.
"""

from spy_edge_research.services.artifact_access import (
    ARTIFACT_ACCESS_CAVEAT,
    LoadedReportBundle,
    discover_report_bundles,
    load_report_bundle_csv_dir,
    load_report_bundle_json,
)
from spy_edge_research.services.research_queries import (
    filter_bundle_table,
    get_bundle_table,
    list_bundle_tables,
    summarize_bundles,
)
from spy_edge_research.services.workflow_service import (
    WorkflowServiceResponse,
    export_workflow_service_response,
    run_event_research_workflow_service,
)

__all__ = [
    "ARTIFACT_ACCESS_CAVEAT",
    "LoadedReportBundle",
    "WorkflowServiceResponse",
    "discover_report_bundles",
    "export_workflow_service_response",
    "filter_bundle_table",
    "get_bundle_table",
    "list_bundle_tables",
    "load_report_bundle_csv_dir",
    "load_report_bundle_json",
    "run_event_research_workflow_service",
    "summarize_bundles",
]
