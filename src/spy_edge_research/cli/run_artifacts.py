"""Run-directory layout and run-manifest writer for the MOD 11 pipeline runner.

Defines the deterministic on-disk layout of a single pipeline run and writes a
``run_manifest.json`` that records stage status, provenance, and research
caveats. This module only arranges paths and serializes metadata; it never
fetches data, makes a trade decision, or produces execution outputs.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from spy_edge_research.backtesting.event_reports import create_research_run_metadata

RUN_MANIFEST_CAVEAT = "pipeline_run_is_descriptive_research_only_not_trade_instructions"
RUN_DIR_PREFIX = "run_"


@dataclass(frozen=True)
class RunPaths:
    """Resolved artifact paths for a single pipeline run."""

    run_dir: Path
    report_bundle_dir: Path
    candidates_path: Path
    dashboard_path: Path
    dashboard_manifest_path: Path
    readiness_scorecard_path: Path
    readiness_verdict_path: Path
    run_manifest_path: Path


def build_run_paths(output_root: str | Path, run_id: str) -> RunPaths:
    """Compute the deterministic artifact layout for a run under ``output_root``."""
    if not isinstance(run_id, str) or not run_id:
        raise ValueError("run_id must be a non-empty string")
    run_dir = Path(output_root) / f"{RUN_DIR_PREFIX}{run_id}"
    return RunPaths(
        run_dir=run_dir,
        report_bundle_dir=run_dir / "report_bundle",
        candidates_path=run_dir / "candidates" / "candidate_edges.json",
        dashboard_path=run_dir / "dashboard" / "event_study.json",
        dashboard_manifest_path=run_dir / "dashboard" / "manifest.json",
        readiness_scorecard_path=run_dir / "readiness" / "scorecard.csv",
        readiness_verdict_path=run_dir / "readiness" / "verdict.csv",
        run_manifest_path=run_dir / "run_manifest.json",
    )


def prepare_run_dir(paths: RunPaths, *, overwrite: bool) -> None:
    """Create the run directory, refusing to clobber an existing one unless asked."""
    if paths.run_dir.exists() and not overwrite:
        raise FileExistsError(f"{paths.run_dir} already exists")
    paths.run_dir.mkdir(parents=True, exist_ok=True)


def write_run_manifest(
    paths: RunPaths,
    *,
    run_id: str,
    input_path: str | Path,
    stages: Sequence[Mapping[str, Any]],
    metrics: Mapping[str, Any],
    extra_caveats: Sequence[str] | None = None,
    overwrite: bool = False,
) -> Path:
    """Write the run manifest recording provenance, stage status, and caveats."""
    target = paths.run_manifest_path
    if target.exists() and not overwrite:
        raise FileExistsError(f"{target} already exists")
    target.parent.mkdir(parents=True, exist_ok=True)

    base = create_research_run_metadata(
        milestone="97",
        notes="MOD 11 unified pipeline runner",
    )
    caveats = [RUN_MANIFEST_CAVEAT, *(extra_caveats or [])]
    payload: dict[str, Any] = {
        **base,
        "pipeline_name": "spy_edge_research.cli.run_pipeline",
        "run_id": run_id,
        "input_path": str(input_path),
        "stages": [dict(stage) for stage in stages],
        "metrics": dict(metrics),
        "caveats": caveats,
    }
    target.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return target
