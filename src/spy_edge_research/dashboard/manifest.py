"""Traceability manifest for exported dashboard contract payloads.

Records which payloads were generated, their schema version, and their tables,
so a dashboard export run is reproducible and auditable.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import pandas as pd

from spy_edge_research.dashboard.contracts import (
    DASHBOARD_SCHEMA_VERSION,
    validate_dashboard_contract,
)


DASHBOARD_MANIFEST_CAVEAT = "dashboard_manifest_is_descriptive_provenance_only"


def build_dashboard_manifest(payloads: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Build a manifest describing a set of validated dashboard payloads."""
    entries: list[dict[str, Any]] = []
    for payload in payloads:
        validated = validate_dashboard_contract(dict(payload))
        entries.append(
            {
                "payload_type": validated["payload_type"],
                "schema_version": validated["schema_version"],
                "generated_at_utc": validated["generated_at_utc"],
                "table_count": len(validated["tables"]),
                "tables": sorted(validated["tables"]),
            }
        )
    return {
        "schema_version": DASHBOARD_SCHEMA_VERSION,
        "payload_count": len(entries),
        "entries": entries,
        "manifest_caveat": DASHBOARD_MANIFEST_CAVEAT,
    }


def summarize_dashboard_manifest(manifest: Mapping[str, Any]) -> pd.DataFrame:
    """Return a per-payload summary table for a dashboard manifest."""
    if not isinstance(manifest, Mapping) or "entries" not in manifest:
        raise KeyError("manifest must be a mapping containing entries")
    rows = [
        {
            "payload_type": entry.get("payload_type"),
            "schema_version": entry.get("schema_version"),
            "table_count": entry.get("table_count"),
        }
        for entry in manifest["entries"]
    ]
    return pd.DataFrame(rows, columns=["payload_type", "schema_version", "table_count"])
