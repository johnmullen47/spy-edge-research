"""Versioned, frontend-ready dashboard data-contract layer.

Builds stable JSON payloads from research artifacts for a future dashboard. Data
contracts only: descriptive research tables + provenance, no UI, no live data,
and no trade-instruction / signal / readiness fields.
"""

from spy_edge_research.dashboard.contracts import (
    DASHBOARD_CONTRACT_CAVEAT,
    DASHBOARD_SCHEMA_VERSION,
    build_dashboard_contract,
    validate_dashboard_contract,
)
from spy_edge_research.dashboard.export import (
    build_dashboard_payload_from_bundle,
    export_dashboard_payload_to_json,
)
from spy_edge_research.dashboard.manifest import (
    DASHBOARD_MANIFEST_CAVEAT,
    build_dashboard_manifest,
    summarize_dashboard_manifest,
)

__all__ = [
    "DASHBOARD_CONTRACT_CAVEAT",
    "DASHBOARD_MANIFEST_CAVEAT",
    "DASHBOARD_SCHEMA_VERSION",
    "build_dashboard_contract",
    "build_dashboard_manifest",
    "build_dashboard_payload_from_bundle",
    "export_dashboard_payload_to_json",
    "summarize_dashboard_manifest",
    "validate_dashboard_contract",
]
