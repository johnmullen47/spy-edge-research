import pandas as pd
import pytest

from spy_edge_research.dashboard import (
    DASHBOARD_SCHEMA_VERSION,
    build_dashboard_contract,
    validate_dashboard_contract,
)


def test_build_contract_envelope():
    payload = build_dashboard_contract(
        payload_type="event_study",
        tables={"summary": pd.DataFrame({"event_count": [3], "event_expectancy": [0.4]})},
    )
    assert payload["schema_version"] == DASHBOARD_SCHEMA_VERSION
    assert payload["payload_type"] == "event_study"
    assert payload["tables"]["summary"][0]["event_count"] == 3
    assert payload["generated_at_utc"].endswith("+00:00")
    assert payload["dashboard_caveat"]


def test_build_contract_requires_tables():
    with pytest.raises(ValueError, match="non-empty mapping"):
        build_dashboard_contract(payload_type="x", tables={})


def test_validate_rejects_bad_schema_version():
    payload = build_dashboard_contract(payload_type="x", tables={"t": pd.DataFrame({"a": [1]})})
    payload["schema_version"] = "9.9"
    with pytest.raises(ValueError, match="schema_version"):
        validate_dashboard_contract(payload)


def test_contract_rejects_forbidden_columns():
    with pytest.raises(ValueError, match="forbidden"):
        build_dashboard_contract(payload_type="x", tables={"t": pd.DataFrame({"allocation": [1]})})
