"""Tests for the causal position simulator (MOD 14)."""

from __future__ import annotations

import pytest

from spy_edge_research.simulation import ExecutionModel, simulate_candidate_positions


def test_entries_and_exits_land_on_expected_bars(rising_market, candidates):
    sim = simulate_candidate_positions(rising_market, candidates, execution=ExecutionModel(cost_bps=0))
    longs = [t for t in sim["trades"] if t.candidate_id == "c_long_5m"]
    # events fire at bars 2,5,8; horizon 5 -> exits at 7,10,13.
    assert sorted(t.entry_bar for t in longs) == [2, 5, 8]
    assert sorted(t.exit_bar for t in longs) == [7, 10, 13]
    assert all(t.holding_bars == 5 for t in longs)


def test_gross_return_matches_forward_label(rising_market, candidates):
    sim = simulate_candidate_positions(rising_market, candidates, execution=ExecutionModel(cost_bps=0))
    bar2 = next(t for t in sim["trades"] if t.candidate_id == "c_long_5m" and t.entry_bar == 2)
    expected_bps = (100.70 / 100.20 - 1) * 10_000
    assert bar2.gross_return_bps == pytest.approx(expected_bps, abs=1e-6)
    # long in a rising market is positive; short is negative.
    assert bar2.gross_return_bps > 0
    short = next(t for t in sim["trades"] if t.candidate_id == "c_short_5m")
    assert short.gross_return_bps < 0


def test_cost_reduces_net_return(rising_market, candidates):
    sim = simulate_candidate_positions(rising_market, candidates, execution=ExecutionModel(cost_bps=2.0))
    trade = sim["trades"][0]
    assert trade.net_return_bps == pytest.approx(trade.gross_return_bps - 2.0, abs=1e-9)


def test_non_directional_candidates_are_skipped_not_dropped(rising_market, candidates):
    sim = simulate_candidate_positions(rising_market, candidates)
    assert sim["skipped_non_directional"] == 1
    assert all(t.candidate_id != "c_neutral" for t in sim["trades"])


def test_unresolvable_horizon_opens_no_position(rising_market):
    # event_late fires at bar 28; a 5-bar horizon cannot resolve within the day.
    late = [{"candidate_id": "c_late", "name": "event_late", "direction": "long", "horizon": "5m"}]
    sim = simulate_candidate_positions(rising_market, late)
    assert sim["trades"] == []


def test_no_exit_bar_exceeds_available_rows(rising_market, candidates):
    sim = simulate_candidate_positions(rising_market, candidates)
    n = len(rising_market)
    assert all(t.exit_bar < n for t in sim["trades"])
