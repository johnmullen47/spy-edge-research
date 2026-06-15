"""Tests for the pure run_pipeline orchestration (MOD 11)."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from spy_edge_research.cli.pipeline import PipelineConfig, run_pipeline
from spy_edge_research.services.artifact_access import load_report_bundle_csv_dir
from spy_edge_research.backtesting.candidate_edges import read_candidate_edge_registry


def _run(csv: Path, out: Path, *, config: PipelineConfig | None = None, **kw):
    return run_pipeline(
        csv,
        out,
        run_id="TESTRUN",
        config=config or PipelineConfig(horizons_minutes=(5, 15)),
        **kw,
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
        paths.negative_control_path,
        paths.temporal_stability_path,
        paths.multiple_testing_path,
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


def test_intraday_momentum_family_flows_through_same_gate(synth_ohlcv_csv, tmp_path):
    # The regime-conditioned MIM family (Build 4 Path 2) is opt-in; when enabled it
    # joins the candidate set as event_mim_* candidates through the SAME pipeline
    # and the SAME Hard-Gate-A readiness gate — a new family, not a new gate.
    config = PipelineConfig(
        horizons_minutes=(5, 15), include_intraday_momentum=True
    )
    result = _run(synth_ohlcv_csv, tmp_path / "reports", config=config)
    registry = read_candidate_edge_registry(result.paths.candidates_path)
    mim = registry[registry["name"].str.startswith("event_mim_")]
    assert not mim.empty, "MIM family did not reach the candidate registry"
    # The gate must stay closed on this tiny synthetic data (the honest result).
    verdicts = result.readiness_verdicts
    assert verdicts is not None and not verdicts.empty
    assert not (verdicts["verdict"] == "eligible_for_paper_consideration").any()


def test_intraday_momentum_off_by_default(synth_ohlcv_csv, tmp_path):
    result = _run(synth_ohlcv_csv, tmp_path / "reports")
    registry = read_candidate_edge_registry(result.paths.candidates_path)
    assert registry["name"].str.startswith("event_mim_").sum() == 0


def test_pipeline_run_manifest_parses_and_records_stages(synth_ohlcv_csv, tmp_path):
    result = _run(synth_ohlcv_csv, tmp_path / "reports")
    manifest = json.loads(result.paths.run_manifest_path.read_text(encoding="utf-8"))

    assert manifest["run_id"] == "TESTRUN"
    stage_names = {stage["stage"] for stage in manifest["stages"]}
    assert {
        "load",
        "indicators",
        "events",
        "labels",
        "event_study",
        "control_batteries",
        "readiness",
    } <= stage_names
    # Batteries run by default, so the not-run caveat must be ABSENT and the
    # battery diagnostic caveat present.
    assert "control_batteries_not_run_in_basic_pipeline" not in manifest["caveats"]
    assert (
        "control_battery_results_are_research_diagnostics_not_trade_authorization"
        in manifest["caveats"]
    )


def test_pipeline_control_batteries_can_be_disabled(synth_ohlcv_csv, tmp_path):
    config = PipelineConfig(horizons_minutes=(5, 15), run_control_batteries=False)
    result = _run(synth_ohlcv_csv, tmp_path / "reports", config=config)
    manifest = json.loads(result.paths.run_manifest_path.read_text(encoding="utf-8"))
    # When disabled, the run must disclose that the batteries were not run.
    assert "control_batteries_not_run_in_basic_pipeline" in manifest["caveats"]
    skipped = [
        stage
        for stage in manifest["stages"]
        if stage["stage"] == "control_batteries"
    ]
    assert skipped and skipped[0]["status"] == "skipped"


def test_pipeline_readiness_is_research_gate_not_authorization(synth_ohlcv_csv, tmp_path):
    result = _run(synth_ohlcv_csv, tmp_path / "reports")
    verdicts = result.readiness_verdicts
    assert verdicts is not None and not verdicts.empty
    # The fixture spans two days within a single calendar month, so temporal
    # stability cannot reach the >=2-period bar — no candidate is eligible. A
    # gate that stays closed on this data is the honest, desirable result.
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
