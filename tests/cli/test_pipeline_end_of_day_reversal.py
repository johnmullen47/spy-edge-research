"""Pipeline integration for the end-of-day reversal (F2) family (M116).

F2 must flow through the SAME candidate / Hard-Gate-A pipeline as every other
family — a new set of candidates through the same gate, not a new gate — and its
to-close hold horizon must be added so the signal resolves at the close.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from spy_edge_research.backtesting.candidate_edges import read_candidate_edge_registry
from spy_edge_research.cli.pipeline import PipelineConfig, run_pipeline


def _afternoon_csv(tmp_path: Path, *, days: int = 4) -> Path:
    """Bars 13:30->16:00 ET for several days, so the 14:00-15:00 and 15:00-16:00
    windows (and the 60-min to-close label) are all present."""
    rng = np.random.default_rng(11)
    rows = []
    for day in range(days):
        day_start = pd.Timestamp("2024-01-02 13:30:00", tz="America/New_York") + pd.Timedelta(days=day)
        price = 100.0 + np.cumsum(rng.normal(0, 0.05, size=151))
        for i in range(151):  # 13:30 .. 16:00
            ts = day_start + pd.Timedelta(minutes=i)
            p = float(price[i])
            rows.append(
                {
                    "timestamp": ts,
                    "symbol": "SPY",
                    "open": p,
                    "high": p + 0.05,
                    "low": p - 0.05,
                    "close": p,
                    "volume": 1500,
                }
            )
    csv_path = tmp_path / "afternoon_bars.csv"
    pd.DataFrame(rows).to_csv(csv_path, index=False)
    return csv_path


def _run(csv: Path, out: Path, **cfg_kwargs):
    return run_pipeline(
        csv, out, run_id="t", config=PipelineConfig(**cfg_kwargs), overwrite=True
    )


def test_end_of_day_reversal_family_flows_through_same_gate(tmp_path):
    csv = _afternoon_csv(tmp_path)
    result = _run(
        csv, tmp_path / "out", horizons_minutes=(5, 15), include_end_of_day_reversal=True
    )
    registry = read_candidate_edge_registry(result.paths.candidates_path)
    eod = registry[registry["name"].str.startswith("event_eod_reversal_")]
    assert not eod.empty, "F2 family did not reach the candidate registry"
    # The to-close (60m) hold horizon was appended, so F2 resolves at the close.
    assert eod["horizon"].astype(str).str.contains("60").any()


def test_end_of_day_reversal_off_by_default(tmp_path):
    csv = _afternoon_csv(tmp_path)
    result = _run(csv, tmp_path / "out", horizons_minutes=(5, 15))
    registry = read_candidate_edge_registry(result.paths.candidates_path)
    assert registry["name"].str.startswith("event_eod_reversal_").sum() == 0
    # No to-close horizon is added when F2 is off.
    assert (registry["horizon"].astype(str) == "60m").sum() == 0


def test_enabling_f2_grows_the_candidate_registry(tmp_path):
    csv = _afternoon_csv(tmp_path)
    off = read_candidate_edge_registry(
        _run(csv, tmp_path / "off", horizons_minutes=(5, 15)).paths.candidates_path
    )
    on = read_candidate_edge_registry(
        _run(
            csv, tmp_path / "on", horizons_minutes=(5, 15), include_end_of_day_reversal=True
        ).paths.candidates_path
    )
    # F2 adds candidates (its event columns x horizons); N = len(registry) grows,
    # which is the honest deflation cost of looking in one more place.
    assert len(on) > len(off)
