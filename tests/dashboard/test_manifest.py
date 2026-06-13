import pandas as pd
import pytest

from spy_edge_research.dashboard import (
    build_dashboard_contract,
    build_dashboard_manifest,
    summarize_dashboard_manifest,
)


def _payload(payload_type):
    return build_dashboard_contract(
        payload_type=payload_type,
        tables={"t1": pd.DataFrame({"a": [1]}), "t2": pd.DataFrame({"b": [2]})},
    )


def test_build_manifest():
    manifest = build_dashboard_manifest([_payload("event_study"), _payload("risk_exposure")])
    assert manifest["payload_count"] == 2
    assert manifest["entries"][0]["table_count"] == 2
    assert manifest["manifest_caveat"]


def test_summarize_manifest():
    manifest = build_dashboard_manifest([_payload("event_study")])
    summary = summarize_dashboard_manifest(manifest)
    assert summary.loc[0, "payload_type"] == "event_study"
    assert summary.loc[0, "table_count"] == 2


def test_summarize_requires_entries():
    with pytest.raises(KeyError):
        summarize_dashboard_manifest({"foo": 1})
