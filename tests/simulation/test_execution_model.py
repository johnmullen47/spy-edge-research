"""Tests for the ExecutionModel cost + slippage assumptions (M107)."""

from __future__ import annotations

import pytest

from spy_edge_research.simulation import ExecutionModel


def test_net_return_subtracts_cost_and_slippage():
    model = ExecutionModel(cost_bps=1.0, slippage_bps=0.5)
    assert model.total_cost_bps == pytest.approx(1.5)
    assert model.net_return_bps(10.0) == pytest.approx(8.5)


def test_default_slippage_is_zero_backward_compatible():
    model = ExecutionModel(cost_bps=2.0)
    assert model.slippage_bps == 0.0
    assert model.net_return_bps(5.0) == pytest.approx(3.0)


def test_negative_slippage_is_rejected():
    with pytest.raises(ValueError, match="slippage_bps"):
        ExecutionModel(slippage_bps=-0.1)


def test_pnl_points_reflect_cost_and_slippage():
    model = ExecutionModel(cost_bps=1.0, slippage_bps=1.0)  # 2 bps total drag
    net = model.net_return_bps(10.0)  # 8 bps
    assert model.pnl_points(100.0, net) == pytest.approx(100.0 * 8.0 / 10_000.0)
