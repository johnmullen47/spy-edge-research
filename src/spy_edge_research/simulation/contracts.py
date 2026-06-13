"""Data model and validator for the paper-trading SIMULATION layer (MOD 14).

This is the project's first module past the research-only readiness gate, built
under explicit user authorization (2026-06-13). It simulates positions, fills,
and P&L on *historical* bars only. It is NOT live trading and NOT a broker.

It deliberately has its OWN data model and validator. Sim records use field
names like ``entry_price`` / ``exit_price`` / ``pnl_points`` that the research
modules' guards (``candidate_rule_objects.FORBIDDEN_RULE_OBJECT_FIELDS`` and
``dashboard.contracts.FORBIDDEN_DASHBOARD_FIELDS``) reject — so sim records must
never be round-tripped through those validators. The sim's own boundary, encoded
in ``FORBIDDEN_SIM_FIELDS`` below, is the *next* one out: no real broker, real
money, live/real-time execution, order routing, accounts, or options.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

import pandas as pd

SIM_CAVEAT = "simulation_only_no_broker_no_real_money"

# The boundary that still holds *after* the authorized paper-sim crossing. These
# are matched as whole snake_case tokens (so ``exit_price`` is fine but
# ``order_id`` / ``broker_route`` are rejected).
FORBIDDEN_SIM_FIELDS: frozenset[str] = frozenset(
    {
        "broker",
        "brokerage",
        "live",
        "realtime",
        "route",
        "routing",
        "account",
        "order",
        "option",
        "options",
        "money",
        "cash",
        "deposit",
        "withdraw",
        "fund",
        "margin",
        "leverage",
    }
)

VALID_SIDES: tuple[str, ...] = ("long", "short")
VALID_FILL_KINDS: tuple[str, ...] = ("entry", "exit")
VALID_EXIT_REASONS: tuple[str, ...] = ("horizon",)


@dataclass(frozen=True)
class SimFill:
    """One simulated fill on a historical bar (no broker, no order routing)."""

    bar_index: int
    timestamp: Any
    side: str
    price: float
    quantity: float
    fill_kind: str
    applied_cost_bps: float


@dataclass(frozen=True)
class SimPosition:
    """A simulated position opened from a candidate's event signal."""

    position_id: str
    candidate_id: str
    side: str
    entry_fill: SimFill
    exit_fill: SimFill | None = None

    @property
    def is_open(self) -> bool:
        return self.exit_fill is None


@dataclass(frozen=True)
class SimTrade:
    """A closed simulated position with descriptive, no-cost-of-capital P&L."""

    position_id: str
    candidate_id: str
    side: str
    entry_bar: int
    exit_bar: int
    entry_price: float
    exit_price: float
    holding_bars: int
    gross_return_bps: float
    cost_bps: float
    net_return_bps: float
    pnl_points: float
    exit_reason: str


@dataclass(frozen=True)
class EquityPoint:
    """A point on the simulated equity curve (realized P&L, booked at exits)."""

    bar_index: int
    timestamp: Any
    cumulative_pnl_points: float
    cumulative_net_return_bps: float
    open_position_count: int


def _forbidden_tokens(name: str) -> set[str]:
    return {token for token in str(name).lower().split("_") if token}


def validate_sim_field_name(name: str) -> str:
    """Reject any field/column name that crosses the live-execution boundary."""
    hits = _forbidden_tokens(name) & FORBIDDEN_SIM_FIELDS
    if hits:
        raise ValueError(
            f"forbidden simulation field {name!r}: crosses the live-execution "
            f"boundary (tokens {sorted(hits)})"
        )
    return name


def validate_sim_report(report: Mapping[str, Any]) -> dict[str, Any]:
    """Validate a simulation report: required caveat + no boundary-crossing fields.

    Checks the mandatory ``sim_caveat``, then scans every table's columns and the
    metadata keys for forbidden tokens. This is the guard that keeps the
    simulation layer from drifting toward live/broker/order semantics.
    """
    if not isinstance(report, Mapping):
        raise TypeError("report must be a mapping")
    if report.get("sim_caveat") != SIM_CAVEAT:
        raise ValueError(f"report must carry sim_caveat == {SIM_CAVEAT!r}")

    tables = report.get("tables")
    if not isinstance(tables, Mapping):
        raise KeyError("report must contain a tables mapping")
    for table_name, table in tables.items():
        if not isinstance(table, pd.DataFrame):
            raise TypeError(f"tables.{table_name} must be a pandas DataFrame")
        for column in table.columns:
            validate_sim_field_name(column)

    metadata = report.get("metadata", {})
    if metadata is not None:
        if not isinstance(metadata, Mapping):
            raise TypeError("report metadata must be a mapping")
        for key in metadata:
            validate_sim_field_name(key)
    return dict(report)
