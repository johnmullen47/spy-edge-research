"""Research-only run registry helpers for artifact manifests.

These utilities consume artifact manifest JSON files and build deterministic
run-level inventories. They do not read artifact file contents, create signals,
rank runs, optimize thresholds, simulate P/L, or claim edge.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterable, Mapping
from copy import deepcopy
from pathlib import Path
from typing import Any

import pandas as pd

from spy_edge_research.backtesting.event_artifacts import (
    read_artifact_manifest,
    validate_artifact_manifest,
)

from spy_edge_research._internal._common import (
    created_at_utc as _created_at_utc,
    json_safe_mapping as _json_safe_mapping,
    normalize_columns as _normalize_columns,
)

RUN_SUMMARY_COLUMNS: tuple[str, ...] = (
    "run_id",
    "manifest_path",
    "artifact_count",
    "artifact_types",
    "project_name",
    "created_at_utc",
    "metadata_keys",
)

REGISTRY_ARTIFACT_COLUMNS: tuple[str, ...] = (
    "run_id",
    "manifest_path",
    "artifact_name",
    "artifact_path",
    "artifact_type",
    "description",
    "row_count",
    "column_count",
    "artifact_created_at_utc",
)

METADATA_CONSISTENCY_COLUMNS: tuple[str, ...] = (
    "run_id",
    "metadata_key",
    "present",
)

FORBIDDEN_RUN_FIELDS: frozenset[str] = frozenset(
    {
        "buy",
        "sell",
        "entry",
        "exit",
        "confidence",
        "score",
        "rank",
        "edge",
        "best_event",
        "selected_event",
        "p_l",
        "pnl",
        "profit",
    }
)


def validate_run_registry(registry: Any) -> dict[str, Any]:
    """Validate a research run registry structure."""
    if not isinstance(registry, dict):
        raise TypeError("registry must be a dict")

    if "metadata" not in registry:
        raise KeyError("registry is missing metadata")
    if not isinstance(registry["metadata"], dict):
        raise TypeError("registry metadata must be a dict")

    if "runs" not in registry:
        raise KeyError("registry is missing runs")
    runs = registry["runs"]
    if not isinstance(runs, list):
        raise TypeError("registry runs must be a list")

    seen_run_ids: set[str] = set()
    for index, run in enumerate(runs):
        _validate_run_record(run, record_name=f"runs[{index}]")
        run_id = run["run_id"]
        if run_id in seen_run_ids:
            raise ValueError(f"registry contains duplicate run_id: {run_id}")
        seen_run_ids.add(run_id)

    return registry


def create_run_record(
    *,
    run_id: str,
    manifest_path: str | Path,
    manifest: Mapping[str, Any] | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Create one research run record."""
    _validate_non_empty_string(run_id, "run_id")
    _validate_non_empty_string(str(manifest_path), "manifest_path")
    if metadata is not None and not isinstance(metadata, Mapping):
        raise TypeError("metadata must be a mapping when provided")

    record: dict[str, Any] = {
        "created_at_utc": _created_at_utc(),
        "manifest_path": str(manifest_path),
        "run_id": run_id,
    }
    if manifest is not None:
        manifest_copy = _json_safe_mapping(manifest)
        validate_artifact_manifest(manifest_copy)
        record["manifest"] = manifest_copy
    if metadata is not None:
        record["metadata"] = _json_safe_mapping(metadata)

    _validate_run_record(record, record_name="run_record")
    return record


def build_run_registry(
    run_records: Iterable[Mapping[str, Any]],
    *,
    metadata: Mapping[str, Any] | None = None,
    project_name: str = "SPY Directional Edge Research",
    registry_version: str = "1.0",
) -> dict[str, Any]:
    """Build a registry dictionary from run records."""
    _validate_non_empty_string(project_name, "project_name")
    _validate_non_empty_string(registry_version, "registry_version")
    if metadata is not None and not isinstance(metadata, Mapping):
        raise TypeError("metadata must be a mapping when provided")

    runs = [
        _copy_and_validate_run_record(record, record_name=f"run_records[{index}]")
        for index, record in enumerate(run_records)
    ]
    registry_metadata = _json_safe_mapping(metadata or {})
    registry_metadata["created_at_utc"] = _created_at_utc()
    registry_metadata["project_name"] = project_name
    registry_metadata["registry_version"] = registry_version

    registry = {
        "metadata": registry_metadata,
        "runs": runs,
    }
    validate_run_registry(registry)
    return registry


def discover_manifest_paths(
    root_dir: str | Path,
    *,
    pattern: str = "**/manifest.json",
) -> list[Path]:
    """Find manifest JSON files under a directory without reading them."""
    root_path = Path(root_dir)
    if not root_path.exists():
        raise FileNotFoundError(f"{root_path} does not exist")
    return sorted(root_path.glob(pattern), key=lambda path: str(path))


def load_run_registry_from_manifests(
    manifest_paths: Iterable[str | Path],
    *,
    base_dir: str | Path | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Load multiple artifact manifests and build a deterministic run registry."""
    if metadata is not None and not isinstance(metadata, Mapping):
        raise TypeError("metadata must be a mapping when provided")

    records = []
    for path in manifest_paths:
        manifest_path = Path(path)
        manifest = read_artifact_manifest(manifest_path)
        manifest_metadata = manifest.get("metadata", {})
        run_id = _run_id_from_manifest_or_path(
            manifest_metadata,
            manifest_path,
            base_dir=base_dir,
        )
        records.append(
            create_run_record(
                run_id=run_id,
                manifest_path=_format_manifest_path(manifest_path, base_dir=base_dir),
                manifest=manifest,
                metadata=manifest_metadata,
            )
        )

    records = sorted(records, key=lambda record: record["run_id"])
    return build_run_registry(records, metadata=metadata)


def summarize_run_registry(registry: Mapping[str, Any]) -> pd.DataFrame:
    """Return a deterministic DataFrame summary of registered runs."""
    validated = validate_run_registry(dict(registry))
    rows = []
    for run in validated["runs"]:
        manifest = run.get("manifest")
        manifest_metadata = manifest.get("metadata", {}) if isinstance(manifest, dict) else {}
        artifacts = manifest.get("artifacts", []) if isinstance(manifest, dict) else []
        artifact_types = sorted(
            {
                artifact.get("artifact_type")
                for artifact in artifacts
                if artifact.get("artifact_type") is not None
            }
        )
        run_metadata = run.get("metadata", {})
        rows.append(
            {
                "run_id": run["run_id"],
                "manifest_path": run["manifest_path"],
                "artifact_count": len(artifacts),
                "artifact_types": artifact_types,
                "project_name": manifest_metadata.get("project_name"),
                "created_at_utc": run.get("created_at_utc"),
                "metadata_keys": sorted(run_metadata.keys()),
            }
        )

    summary = pd.DataFrame(rows, columns=RUN_SUMMARY_COLUMNS)
    if summary.empty:
        return summary
    return summary.sort_values("run_id", kind="mergesort").reset_index(drop=True)


def summarize_registry_artifacts(registry: Mapping[str, Any]) -> pd.DataFrame:
    """Return one structural inventory row per artifact across all runs."""
    validated = validate_run_registry(dict(registry))
    rows = []
    for run in validated["runs"]:
        manifest = run.get("manifest")
        if not isinstance(manifest, dict):
            continue
        for artifact in manifest["artifacts"]:
            rows.append(
                {
                    "run_id": run["run_id"],
                    "manifest_path": run["manifest_path"],
                    "artifact_name": artifact.get("name"),
                    "artifact_path": artifact.get("path"),
                    "artifact_type": artifact.get("artifact_type"),
                    "description": artifact.get("description"),
                    "row_count": artifact.get("row_count"),
                    "column_count": artifact.get("column_count"),
                    "artifact_created_at_utc": artifact.get("created_at_utc"),
                }
            )

    summary = pd.DataFrame(rows, columns=REGISTRY_ARTIFACT_COLUMNS)
    if summary.empty:
        return summary
    return summary.sort_values(["run_id", "artifact_name"], kind="mergesort").reset_index(
        drop=True
    )


def validate_run_metadata_consistency(
    registry: Mapping[str, Any],
    required_metadata_keys: Iterable[str] | None = None,
) -> pd.DataFrame:
    """Return metadata key presence rows for each run."""
    validated = validate_run_registry(dict(registry))
    run_metadata = {
        run["run_id"]: run.get("metadata", {})
        for run in validated["runs"]
    }
    if required_metadata_keys is None:
        metadata_keys = sorted(
            {
                key
                for metadata in run_metadata.values()
                for key in metadata
            }
        )
    else:
        metadata_keys = _normalize_columns(required_metadata_keys, "required_metadata_keys")

    rows = [
        {
            "run_id": run_id,
            "metadata_key": metadata_key,
            "present": metadata_key in metadata,
        }
        for run_id, metadata in run_metadata.items()
        for metadata_key in metadata_keys
    ]
    summary = pd.DataFrame(rows, columns=METADATA_CONSISTENCY_COLUMNS)
    if summary.empty:
        return summary
    return summary.sort_values(["run_id", "metadata_key"], kind="mergesort").reset_index(
        drop=True
    )


def write_run_registry(
    registry: Mapping[str, Any],
    output_path: str | Path,
    *,
    overwrite: bool = False,
) -> Path:
    """Write a validated run registry to deterministic JSON."""
    validated = validate_run_registry(deepcopy(dict(registry)))
    target = Path(output_path)
    if target.exists() and not overwrite:
        raise FileExistsError(f"{target} already exists")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(validated, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return target


def read_run_registry(path: str | Path) -> dict[str, Any]:
    """Read and validate a run registry JSON file."""
    registry = json.loads(Path(path).read_text(encoding="utf-8"))
    validate_run_registry(registry)
    return registry


def _copy_and_validate_run_record(
    record: Mapping[str, Any],
    *,
    record_name: str,
) -> dict[str, Any]:
    if not isinstance(record, Mapping):
        raise TypeError(f"{record_name} must be a mapping")
    copied = _json_safe_mapping(record)
    _validate_run_record(copied, record_name=record_name)
    return copied


def _validate_run_record(record: Any, *, record_name: str) -> None:
    if not isinstance(record, dict):
        raise TypeError(f"{record_name} must be a dict")

    missing = [field for field in ("run_id", "manifest_path") if field not in record]
    if missing:
        raise KeyError(f"{record_name} is missing required fields: {missing}")

    _validate_non_empty_string(record["run_id"], f"{record_name}.run_id")
    _validate_non_empty_string(record["manifest_path"], f"{record_name}.manifest_path")

    if "created_at_utc" in record and record["created_at_utc"] is not None:
        if not isinstance(record["created_at_utc"], str):
            raise TypeError(f"{record_name}.created_at_utc must be a string")
    if "metadata" in record and record["metadata"] is not None:
        if not isinstance(record["metadata"], dict):
            raise TypeError(f"{record_name}.metadata must be a dict")
    if "manifest" in record and record["manifest"] is not None:
        validate_artifact_manifest(record["manifest"])

    forbidden = sorted(FORBIDDEN_RUN_FIELDS.intersection(record))
    if forbidden:
        raise KeyError(f"{record_name} contains forbidden research-only fields: {forbidden}")


def _run_id_from_manifest_or_path(
    manifest_metadata: Mapping[str, Any],
    manifest_path: Path,
    *,
    base_dir: str | Path | None,
) -> str:
    run_id = manifest_metadata.get("run_id")
    if isinstance(run_id, str) and run_id:
        return run_id
    return _sanitize_run_id(_format_manifest_path(manifest_path, base_dir=base_dir))


def _sanitize_run_id(path_value: str) -> str:
    without_suffix = str(Path(path_value).with_suffix(""))
    sanitized = re.sub(r"[^A-Za-z0-9]+", "_", without_suffix).strip("_").lower()
    return sanitized or "manifest"


def _format_manifest_path(path: str | Path, *, base_dir: str | Path | None) -> str:
    path_obj = Path(path)
    if base_dir is None:
        return str(path_obj)

    try:
        return str(path_obj.relative_to(Path(base_dir)))
    except ValueError:
        return str(path_obj)


def _validate_non_empty_string(value: Any, name: str) -> None:
    if not isinstance(value, str):
        raise TypeError(f"{name} must be a string")
    if not value:
        raise ValueError(f"{name} must be non-empty")

