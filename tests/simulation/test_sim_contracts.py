"""Tests for the simulation forbidden-field validator and caveat (MOD 14)."""

from __future__ import annotations

import pandas as pd
import pytest

from spy_edge_research.simulation import (
    SIM_CAVEAT,
    validate_sim_field_name,
    validate_sim_report,
)


def test_pnl_and_entry_exit_field_names_are_allowed():
    # These cross the *research* guards but are allowed in the sim layer.
    for name in ("entry_price", "exit_price", "pnl_points", "net_return_bps"):
        assert validate_sim_field_name(name) == name


@pytest.mark.parametrize(
    "name",
    ["broker_id", "live_order", "order_route", "account_balance", "option_chain", "margin_call"],
)
def test_live_execution_field_names_are_rejected(name):
    with pytest.raises(ValueError, match="forbidden simulation field"):
        validate_sim_field_name(name)


def test_report_requires_sim_caveat():
    report = {"tables": {"summary": pd.DataFrame({"trade_count": [0]})}}
    with pytest.raises(ValueError, match="sim_caveat"):
        validate_sim_report(report)


def test_report_rejects_forbidden_column():
    report = {
        "sim_caveat": SIM_CAVEAT,
        "tables": {"trades": pd.DataFrame({"broker_route": ["x"]})},
    }
    with pytest.raises(ValueError, match="forbidden simulation field"):
        validate_sim_report(report)


def test_report_rejects_forbidden_metadata_key():
    report = {
        "sim_caveat": SIM_CAVEAT,
        "tables": {"summary": pd.DataFrame({"trade_count": [0]})},
        "metadata": {"account_id": "abc"},
    }
    with pytest.raises(ValueError, match="forbidden simulation field"):
        validate_sim_report(report)


def test_valid_report_passes():
    report = {
        "sim_caveat": SIM_CAVEAT,
        "tables": {"summary": pd.DataFrame({"trade_count": [1], "pnl_points": [0.5]})},
        "metadata": {"bar_count": 30},
    }
    assert validate_sim_report(report)["sim_caveat"] == SIM_CAVEAT
