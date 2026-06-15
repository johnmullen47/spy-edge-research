"""Paper-trading SIMULATION layer (MOD 14).

The project's first module past the research-only readiness gate, built under
explicit user authorization. It simulates positions, fills, and P&L on
*historical* bars only — no real broker, no real money, no live execution, no
order routing, no options. It has its own data model and forbidden-field
validator (``contracts.validate_sim_report``); its records must never be
round-tripped through the research modules' validators.
"""

from spy_edge_research.simulation.contracts import (
    SIM_CAVEAT,
    FORBIDDEN_SIM_FIELDS,
    EquityPoint,
    SimFill,
    SimPosition,
    SimTrade,
    validate_sim_field_name,
    validate_sim_report,
)
from spy_edge_research.simulation.cost_model import (
    DEFAULT_TIME_OF_DAY_MULTIPLIERS,
    DEFAULT_VOL_REGIME_MULTIPLIERS,
    RegimeAwareCostModel,
)
from spy_edge_research.simulation.execution_model import ExecutionModel
from spy_edge_research.simulation.position_sim import simulate_candidate_positions
from spy_edge_research.simulation.pnl import (
    build_equity_curve,
    build_trade_ledger,
    max_drawdown_points,
    summarize_simulation,
)
from spy_edge_research.simulation.eligibility import select_eligible_candidates
from spy_edge_research.simulation.sim_reports import (
    build_simulation_report,
    write_simulation_report,
)

__all__ = [
    "SIM_CAVEAT",
    "FORBIDDEN_SIM_FIELDS",
    "EquityPoint",
    "SimFill",
    "SimPosition",
    "SimTrade",
    "validate_sim_field_name",
    "validate_sim_report",
    "ExecutionModel",
    "RegimeAwareCostModel",
    "DEFAULT_TIME_OF_DAY_MULTIPLIERS",
    "DEFAULT_VOL_REGIME_MULTIPLIERS",
    "simulate_candidate_positions",
    "build_equity_curve",
    "build_trade_ledger",
    "max_drawdown_points",
    "summarize_simulation",
    "select_eligible_candidates",
    "build_simulation_report",
    "write_simulation_report",
]
