"""Tests for report assembly/round-trip and readiness eligibility (MOD 14)."""

from __future__ import annotations

import json

import pandas as pd

from spy_edge_research.simulation import (
    ExecutionModel,
    build_simulation_report,
    select_eligible_candidates,
    write_simulation_report,
)


def test_build_report_has_caveat_and_tables(rising_market, candidates):
    report = build_simulation_report(rising_market, candidates, execution=ExecutionModel(cost_bps=1.0))
    assert report["sim_caveat"] == "simulation_only_no_broker_no_real_money"
    assert set(report["tables"]) == {"trades", "equity_curve", "summary"}
    assert report["metadata"]["skipped_non_directional"] == 1
    assert report["metadata"]["simulated_candidate_count"] == 2


def test_report_write_and_reload_round_trip(rising_market, candidates, tmp_path):
    report = build_simulation_report(rising_market, candidates)
    target = write_simulation_report(report, tmp_path / "sim.json")
    assert target.exists()
    payload = json.loads(target.read_text(encoding="utf-8"))
    assert payload["sim_caveat"] == "simulation_only_no_broker_no_real_money"
    assert len(payload["tables"]["trades"]) == 4


def test_eligibility_gate_filters_to_eligible_only(candidates):
    not_ready = pd.DataFrame(
        {"candidate_id": ["c_long_5m", "c_short_5m"], "verdict": ["not_ready", "not_ready"]}
    )
    assert select_eligible_candidates(candidates, not_ready) == []

    mixed = pd.DataFrame(
        {
            "candidate_id": ["c_long_5m", "c_short_5m"],
            "verdict": ["eligible_for_paper_consideration", "not_ready"],
        }
    )
    selected = [c["candidate_id"] for c in select_eligible_candidates(candidates, mixed)]
    assert selected == ["c_long_5m"]


def test_eligibility_empty_verdicts_returns_nothing(candidates):
    assert select_eligible_candidates(candidates, pd.DataFrame()) == []
