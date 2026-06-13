"""Build and write versioned dashboard contract payloads from research artifacts.

Turns loaded report bundles into stable, frontend-ready JSON payloads. Read-only
and descriptive: payloads carry research tables and provenance only.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from spy_edge_research.dashboard.contracts import (
    build_dashboard_contract,
    validate_dashboard_contract,
)
from spy_edge_research.services.artifact_access import LoadedReportBundle


def build_dashboard_payload_from_bundle(
    bundle: LoadedReportBundle,
    *,
    payload_type: str,
    source_metadata: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a dashboard contract payload from a loaded report bundle."""
    if not isinstance(bundle, LoadedReportBundle):
        raise TypeError("bundle must be a LoadedReportBundle")
    source: dict[str, Any] = {"source_path": bundle.source_path}
    for key in ("milestone", "report_caveat"):
        if key in bundle.metadata:
            source[key] = bundle.metadata[key]
    if source_metadata:
        source.update(dict(source_metadata))
    return build_dashboard_contract(
        payload_type=payload_type,
        tables=bundle.tables,
        source_metadata=source,
    )


def export_dashboard_payload_to_json(
    payload: Mapping[str, Any],
    output_path: str | Path,
    *,
    overwrite: bool = False,
) -> Path:
    """Validate and write a dashboard contract payload to one JSON file."""
    validated = validate_dashboard_contract(dict(payload))
    target = Path(output_path)
    if target.exists() and not overwrite:
        raise FileExistsError(f"{target} already exists")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(validated, indent=2, sort_keys=True), encoding="utf-8")
    return target
