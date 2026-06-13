import json

import pandas as pd
import pytest

from spy_edge_research.dashboard import (
    build_dashboard_payload_from_bundle,
    export_dashboard_payload_to_json,
)
from spy_edge_research.services import LoadedReportBundle


def _bundle():
    return LoadedReportBundle(
        metadata={"milestone": "74", "report_caveat": "x"},
        tables={"exposure_summary": pd.DataFrame({"gross_exposure": [2.0]})},
        source_path="mem",
    )


def test_build_payload_from_bundle():
    payload = build_dashboard_payload_from_bundle(_bundle(), payload_type="risk_exposure")
    assert payload["payload_type"] == "risk_exposure"
    assert payload["source"]["milestone"] == "74"
    assert payload["source"]["source_path"] == "mem"
    assert payload["tables"]["exposure_summary"][0]["gross_exposure"] == 2.0


def test_export_payload_to_json(tmp_path):
    payload = build_dashboard_payload_from_bundle(_bundle(), payload_type="risk_exposure")
    path = export_dashboard_payload_to_json(payload, tmp_path / "payload.json")
    loaded = json.loads(path.read_text())
    assert loaded["payload_type"] == "risk_exposure"
    with pytest.raises(FileExistsError):
        export_dashboard_payload_to_json(payload, tmp_path / "payload.json")


def test_build_payload_requires_bundle_type():
    with pytest.raises(TypeError, match="LoadedReportBundle"):
        build_dashboard_payload_from_bundle({"tables": {}}, payload_type="x")
