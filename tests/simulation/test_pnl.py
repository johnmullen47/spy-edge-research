"""Tests for P&L, equity curve, and drawdown (MOD 14)."""

from __future__ import annotations

import pytest

from spy_edge_research.simulation import (
    ExecutionModel,
    build_equity_curve,
    build_trade_ledger,
    max_drawdown_points,
    simulate_candidate_positions,
    summarize_simulation,
)


def _trades(rising_market, candidates, cost_bps=0.0):
    sim = simulate_candidate_positions(
        rising_market, candidates, execution=ExecutionModel(cost_bps=cost_bps)
    )
    return sim["trades"]


def test_trade_ledger_is_sorted_and_complete(rising_market, candidates):
    ledger = build_trade_ledger(_trades(rising_market, candidates))
    # 3 long + 1 short = 4 directional trades.
    assert len(ledger) == 4
    assert list(ledger["exit_bar"]) == sorted(ledger["exit_bar"])
    assert {"pnl_points", "net_return_bps", "exit_reason"} <= set(ledger.columns)


def test_summary_win_rate_and_total_pnl(rising_market, candidates):
    trades = _trades(rising_market, candidates)
    equity = build_equity_curve(trades)
    summary = summarize_simulation(trades, equity).iloc[0]
    assert summary["trade_count"] == 4
    # 3 winning longs, 1 losing short.
    assert summary["win_rate"] == pytest.approx(0.75)
    assert summary["total_pnl_points"] == pytest.approx(sum(t.pnl_points for t in trades))


def test_max_drawdown_is_nonnegative_and_matches_short_loss(rising_market, candidates):
    trades = _trades(rising_market, candidates)
    equity = build_equity_curve(trades)
    dd = max_drawdown_points(equity)
    assert dd >= 0.0
    # The only losing trade is the short; drawdown is at least its magnitude.
    short_loss = abs(min(t.pnl_points for t in trades))
    assert dd >= short_loss - 1e-9


def test_empty_trades_produce_empty_curve_and_zero_summary():
    equity = build_equity_curve([])
    assert equity.empty
    summary = summarize_simulation([], equity).iloc[0]
    assert summary["trade_count"] == 0
    assert summary["total_pnl_points"] == 0.0
    assert summary["max_drawdown_points"] == 0.0
