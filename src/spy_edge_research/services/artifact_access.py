"""Read-only access to committed research report artifacts.

Loads report bundles (records-oriented JSON, or a CSV directory) produced by the
project's ``export_*_to_json`` / ``export_*_to_csv`` helpers into typed,
in-memory objects. This is an offline, read-only research surface: it never
fetches live data, mutates artifacts on disk, or produces trade instructions.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd


ARTIFACT_ACCESS_CAVEAT = "research_artifact_access_is_read_only_offline_research"


@dataclass(frozen=True)
class LoadedReportBundle:
    """An in-memory, read-only view of a committed report bundle."""

    metadata: dict[str, Any]
    tables: dict[str, pd.DataFrame]
    source_path: str


def load_report_bundle_json(path: str | Path) -> LoadedReportBundle:
    """Load a records-oriented JSON report bundle from disk."""
    target = Path(path)
    payload = json.loads(target.read_text(encoding="utf-8"))
    _validate_payload(payload, str(target))
    tables = {str(name): pd.DataFrame(records) for name, records in payload["tables"].items()}
    return LoadedReportBundle(dict(payload.get("metadata", {})), tables, str(target))


def load_report_bundle_csv_dir(directory: str | Path) -> LoadedReportBundle:
    """Load a CSV-directory report bundle (``metadata.json`` + ``*.csv`` tables)."""
    base = Path(directory)
    if not base.is_dir():
        raise NotADirectoryError(f"{base} is not a directory")
    metadata: dict[str, Any] = {}
    metadata_path = base / "metadata.json"
    if metadata_path.exists():
        loaded = json.loads(metadata_path.read_text(encoding="utf-8"))
        if not isinstance(loaded, Mapping):
            raise TypeError("metadata.json must contain a JSON object")
        metadata = dict(loaded)
    tables = {csv_path.stem: pd.read_csv(csv_path) for csv_path in sorted(base.glob("*.csv"))}
    if not tables:
        raise ValueError(f"no CSV tables found in {base}")
    return LoadedReportBundle(metadata, tables, str(base))


def discover_report_bundles(root: str | Path) -> pd.DataFrame:
    """Discover JSON and CSV-directory report bundles under a root directory."""
    base = Path(root)
    if not base.is_dir():
        raise NotADirectoryError(f"{base} is not a directory")
    rows: list[dict[str, Any]] = []
    for json_path in sorted(base.rglob("*.json")):
        if json_path.name == "metadata.json":
            continue
        try:
            payload = json.loads(json_path.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            continue
        if isinstance(payload, Mapping) and isinstance(payload.get("tables"), Mapping):
            rows.append({"path": str(json_path), "kind": "json", "table_count": len(payload["tables"])})
    for metadata_path in sorted(base.rglob("metadata.json")):
        directory = metadata_path.parent
        csv_count = len(list(directory.glob("*.csv")))
        if csv_count:
            rows.append({"path": str(directory), "kind": "csv_dir", "table_count": csv_count})
    return pd.DataFrame(rows, columns=["path", "kind", "table_count"])


def _validate_payload(payload: Any, source: str) -> None:
    if not isinstance(payload, Mapping):
        raise TypeError(f"{source} must contain a JSON object")
    if not isinstance(payload.get("tables"), Mapping):
        raise KeyError(f"{source} is missing a tables object")
