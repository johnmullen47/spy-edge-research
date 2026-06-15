"""Regression tests for the real-data Hard Gate A driver."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace

import pandas as pd


def _load_script_module():
    script_path = Path(__file__).resolve().parents[2] / "scripts" / "run_hard_gate_a.py"
    spec = importlib.util.spec_from_file_location("run_hard_gate_a_script", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_hard_gate_a_driver_enables_intraday_momentum_and_end_of_day_reversal(
    monkeypatch, tmp_path, capsys
):
    module = _load_script_module()
    captured = {}

    def fake_run_pipeline(input_csv, output_root, *, run_id, config, overwrite):
        captured["input_csv"] = input_csv
        captured["output_root"] = output_root
        captured["run_id"] = run_id
        captured["config"] = config
        captured["overwrite"] = overwrite
        return SimpleNamespace(
            run_dir=tmp_path / "reports" / run_id,
            stages=[],
            readiness_verdicts=pd.DataFrame(
                {"verdict": ["not_ready"], "candidate_id": ["event_mim_long_30m"]}
            ),
        )

    monkeypatch.setattr(module, "run_pipeline", fake_run_pipeline)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_hard_gate_a.py",
            "--input",
            "data/raw/spy_1min.csv",
            "--output",
            str(tmp_path / "reports"),
        ],
    )

    module.main()

    assert captured["config"].include_intraday_momentum is True
    assert captured["config"].include_end_of_day_reversal is True
    assert captured["config"].horizons_minutes == (5, 15, 30)
    assert captured["config"].oos_initial_train_size == 30000
    assert captured["config"].oos_test_size == 7500
    assert captured["config"].oos_step_size == 7500
    assert captured["overwrite"] is True
    assert "Hard Gate A" in capsys.readouterr().out
