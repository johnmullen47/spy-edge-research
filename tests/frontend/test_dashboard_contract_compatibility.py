"""Pin the dashboard contract shape the MOD 12 frontend depends on.

The frontend (`frontend/index.html`) is a static, dependency-free viewer with no
JS test runner available here. This test instead guards the *contract* the UI
reads: it builds a real dashboard payload and asserts the exact envelope keys and
table shape the viewer relies on, plus the research-only invariants (caveat
present, no forbidden fields). If the backend schema drifts from the UI's
assumptions, this fails in CI.
"""

from __future__ import annotations

import pandas as pd

from spy_edge_research.dashboard.contracts import (
    DASHBOARD_CONTRACT_CAVEAT,
    DASHBOARD_SCHEMA_VERSION,
    FORBIDDEN_DASHBOARD_FIELDS,
    build_dashboard_contract,
)

# The envelope keys the frontend reads (frontend/index.html: render()).
UI_REQUIRED_KEYS = (
    "schema_version",
    "payload_type",
    "generated_at_utc",
    "tables",
    "source",
    "dashboard_caveat",
)
# The schema version the viewer targets (frontend/index.html: SCHEMA_EXPECTED).
UI_TARGET_SCHEMA = "1.0"


def _payload() -> dict:
    return build_dashboard_contract(
        payload_type="event_study",
        tables={
            "event_study_results": pd.DataFrame(
                {"event_column": ["e1", "e2"], "difference_from_overall": [0.1, -0.2]}
            )
        },
        source_metadata={"source_path": "reports/run_x/report_bundle", "milestone": "15"},
    )


def test_envelope_has_every_key_the_ui_reads():
    payload = _payload()
    for key in UI_REQUIRED_KEYS:
        assert key in payload, f"frontend reads {key!r} but contract lacks it"


def test_schema_version_matches_ui_target():
    assert str(DASHBOARD_SCHEMA_VERSION) == UI_TARGET_SCHEMA
    assert str(_payload()["schema_version"]) == UI_TARGET_SCHEMA


def test_tables_are_name_to_records_mapping():
    # The UI iterates Object.entries(tables) and expects each value to be an
    # array of record objects.
    tables = _payload()["tables"]
    assert isinstance(tables, dict)
    for name, records in tables.items():
        assert isinstance(name, str)
        assert isinstance(records, list)
        assert all(isinstance(row, dict) for row in records)


def test_caveat_present_and_no_forbidden_fields():
    payload = _payload()
    assert payload["dashboard_caveat"] == DASHBOARD_CONTRACT_CAVEAT
    for records in payload["tables"].values():
        for row in records:
            for column in row:
                assert not any(token in column.lower() for token in FORBIDDEN_DASHBOARD_FIELDS)
