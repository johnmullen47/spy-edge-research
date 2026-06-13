"""Tests for the list-runs discovery command (MOD 11)."""

from __future__ import annotations

from spy_edge_research.cli.main import main
from spy_edge_research.services.artifact_access import discover_report_bundles


def test_list_runs_discovers_multiple_runs(synth_ohlcv_csv, tmp_path, capsys):
    out = tmp_path / "reports"
    for run_id in ("R1", "R2"):
        main(["run-pipeline", "--input", str(synth_ohlcv_csv), "--output", str(out),
              "--run-id", run_id, "--horizons", "5,15"])

    discovered = discover_report_bundles(out)
    paths = "\n".join(discovered["path"].tolist())
    assert "run_R1" in paths
    assert "run_R2" in paths

    code = main(["list-runs", "--root", str(out)])
    assert code == 0
    assert "run_R1" in capsys.readouterr().out


def test_list_runs_empty_root(tmp_path, capsys):
    empty = tmp_path / "empty"
    empty.mkdir()
    code = main(["list-runs", "--root", str(empty)])
    assert code == 0
    assert "no report bundles" in capsys.readouterr().out
