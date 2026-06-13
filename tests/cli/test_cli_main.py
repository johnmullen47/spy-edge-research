"""Tests for the argparse CLI entry point (MOD 11)."""

from __future__ import annotations

from pathlib import Path

import pytest

from spy_edge_research.cli.main import main


def test_run_pipeline_command_succeeds_and_writes_run(synth_ohlcv_csv, tmp_path, capsys):
    out = tmp_path / "reports"
    code = main(
        [
            "run-pipeline",
            "--input", str(synth_ohlcv_csv),
            "--output", str(out),
            "--run-id", "CLIRUN",
            "--horizons", "5,15",
        ]
    )
    assert code == 0
    run_dir = out / "run_CLIRUN"
    assert (run_dir / "run_manifest.json").exists()
    assert (run_dir / "readiness" / "verdict.csv").exists()
    assert "run_id: CLIRUN" in capsys.readouterr().out


def test_run_pipeline_overwrite_guard(synth_ohlcv_csv, tmp_path):
    out = tmp_path / "reports"
    args = ["run-pipeline", "--input", str(synth_ohlcv_csv), "--output", str(out),
            "--run-id", "DUP", "--horizons", "5,15"]
    assert main(args) == 0
    with pytest.raises(FileExistsError):
        main(args)
    assert main([*args, "--overwrite"]) == 0


def test_export_dashboard_command(synth_ohlcv_csv, tmp_path):
    out = tmp_path / "reports"
    main(["run-pipeline", "--input", str(synth_ohlcv_csv), "--output", str(out),
          "--run-id", "EXP", "--horizons", "5,15"])
    bundle = out / "run_EXP" / "report_bundle"
    target = tmp_path / "redo.json"
    code = main(["export-dashboard", "--bundle", str(bundle), "--output", str(target)])
    assert code == 0
    assert target.exists()


def test_score_readiness_command(synth_ohlcv_csv, tmp_path, capsys):
    out = tmp_path / "reports"
    main(["run-pipeline", "--input", str(synth_ohlcv_csv), "--output", str(out),
          "--run-id", "SCORE", "--horizons", "5,15"])
    code = main(["score-readiness", "--run", str(out / "run_SCORE")])
    assert code == 0
    assert "verdict" in capsys.readouterr().out


def test_score_readiness_missing_run_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        main(["score-readiness", "--run", str(tmp_path / "nope")])
