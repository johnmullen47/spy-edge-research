import pandas as pd
import pytest

from spy_edge_research.services import (
    WorkflowServiceResponse,
    export_workflow_service_response,
    list_bundle_tables,
    load_report_bundle_csv_dir,
    run_event_research_workflow_service,
)


def _df():
    return pd.DataFrame(
        {
            "event_vwap_reclaim": [1, 0, 1, 1, 0, 1, 1, 0, 1, 0],
            "forward_return_5m": [0.3, -0.1, 0.2, -0.4, 0.1, 0.5, 0.0, 0.2, -0.3, 0.1],
        }
    )


def _catalog():
    return pd.DataFrame(
        {
            "event_column": ["event_vwap_reclaim"],
            "event_name": ["event_vwap_reclaim"],
            "event_family": ["vwap"],
            "event_direction": ["long"],
            "is_directional": [True],
        }
    )


def test_run_workflow_service_returns_response():
    response = run_event_research_workflow_service(
        _df(),
        label_columns=["forward_return_5m"],
        catalog=_catalog(),
        min_events=1,
    )
    assert isinstance(response, WorkflowServiceResponse)
    assert response.table_names
    assert isinstance(response.report_summary, pd.DataFrame)


def test_export_and_reload_workflow_artifacts(tmp_path):
    response = run_event_research_workflow_service(
        _df(),
        label_columns=["forward_return_5m"],
        catalog=_catalog(),
        min_events=1,
    )
    written = export_workflow_service_response(response, tmp_path)
    assert (tmp_path / "metadata.json").exists()
    assert written["metadata"] == tmp_path / "metadata.json"

    bundle = load_report_bundle_csv_dir(tmp_path)
    assert len(list_bundle_tables(bundle)) >= 1


def test_export_requires_response_type():
    with pytest.raises(TypeError, match="WorkflowServiceResponse"):
        export_workflow_service_response({"outputs": {}}, "ignored")
