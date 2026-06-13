"""Tests for the pure run_pipeline orchestration (MOD 11)."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from spy_edge_research.cli.pipeline import PipelineConfig, run_pipeline
from spy_edge_research.services.artifact_access import load_report_bundle_csv_dir
from spy_edge_research.backtesting.candidate_edges import read_candidate_edge_registry


def _run(csv: Path, out: Path, **kw):
    return run_pipeline(
        csv, out, run_id="TESTRUN", config=PipelineConfig(horizons_minutes=(5, 15)), **kw
    )


def test_pipeline_writes_all_expected_artifacts(synth_ohlcv_csv, tmp_path):
    result = _run(synth_ohlcv_csv, tmp_path / "reports")
    paths = result.paths

    for path in (
        paths.report_bundle_dir / "event_study_results.csv",
        paths.report_bundle_dir / "metadata.json",
        paths.candidates_path,
        paths.dashboard_path,
        paths.dashboard_manifest_path,
        paths.readiness_scorecard_path,
        paths.readiness_verdict_path,
        paths.run_manifest_path,
    ):
        assert path.exists(), f"missing artifact: {path}"


def test_pipeline_bundle_reloads_and_has_event_study(synth_ohlcv_csv, tmp_path):
    result = _run(synth_ohlcv_csv, tmp_path / "reports")
    bundle = load_report_bundle_csv_dir(result.paths.report_bundle_dir)
    assert "event_study_results" in bundle.tables
    assert not bundle.tables["event_study_results"].empty


def test_pipeline_run_manifest_parses_and_records_stages(synth_ohlcv_csv, tmp_path):
    result = _run(synth_ohlcv_csv, tmp_path / "reports")
    manifest = json.loads(result.paths.run_manifest_path.read_text(encoding="utf-8"))

    assert manifest["run_id"] == "TESTRUN"
    stage_names = {stage["stage"] for stage in manifest["stages"]}
    assert {"load", "indicators", "events", "labels", "event_study", "readiness"} <= stage_names
    # The basic pipeline does not run the control batteries; that must be disclosed.
    assert "control_batteries_not_run_in_basic_pipeline" in manifest["caveats"]


def test_pipeline_readiness_is_research_gate_not_authorization(synth_ohlcv_csv, tmp_path):
    result = _run(synth_ohlcv_csv, tmp_path / "reports")
    verdicts = result.readiness_verdicts
    assert verdicts is not None and not verdicts.empty
    # Without the control batteries, no candidate can be eligible — the honest result.
    assert (verdicts["verdict"] == "not_ready").all()
    assert (
        verdicts["verdict_caveat"]
        == "readiness_score_is_research_gate_not_trade_authorization"
    ).all()


def test_pipeline_candidate_registry_round_trips(synth_ohlcv_csv, tmp_path):
    # Regression: candidate registries must be re-readable (no NaN -> null
    # fields that the reader rejects). Surfaced by the MOD 11 -> MOD 14 handoff.
    result = _run(synth_ohlcv_csv, tmp_path / "reports")
    registry = read_candidate_edge_registry(result.paths.candidates_path)
    assert not registry.empty
    assert registry["hit_rate"].notna().all()


def test_pipeline_refuses_to_clobber_existing_run(synth_ohlcv_csv, tmp_path):
    out = tmp_path / "reports"
    _run(synth_ohlcv_csv, out)
    with pytest.raises(FileExistsError):
        _run(synth_ohlcv_csv, out)
    # ...but --overwrite succeeds.
    result = _run(synth_ohlcv_csv, out, overwrite=True)
    assert result.run_dir.exists()
