"""Assemble and write paper-trading simulation reports (MOD 14).

Orchestrates the simulation end to end (positions -> trade ledger -> equity
curve -> summary) into one validated, JSON-safe report bundle, and writes it to
disk. The report carries the mandatory ``sim_caveat`` and passes the simulation
forbidden-field validator, so it can never drift toward live/broker/order
semantics. It is descriptive simulation output, not a trade authorization.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

import pandas as pd

from spy_edge_research._internal._common import (
    created_at_utc,
    dataframe_to_records,
    json_safe_mapping,
    raise_if_exists,
)
from spy_edge_research.simulation.contracts import SIM_CAVEAT, validate_sim_report
from spy_edge_research.simulation.execution_model import ExecutionModel
from spy_edge_research.simulation.pnl import (
    build_equity_curve,
    build_trade_ledger,
    summarize_simulation,
)
from spy_edge_research.simulation.position_sim import simulate_candidate_positions


def build_simulation_report(
    df: pd.DataFrame,
    candidates: Iterable[Mapping[str, Any]],
    *,
    execution: ExecutionModel | None = None,
    timestamp_col: str = "timestamp",
    metadata: Mapping[str, Any] | None = None,
    **simulate_kwargs: Any,
) -> dict[str, Any]:
    """Run the simulation and package a validated report bundle."""
    exec_model = execution or ExecutionModel()
    candidate_list = list(candidates)
    sim = simulate_candidate_positions(
        df, candidate_list, execution=exec_model, timestamp_col=timestamp_col, **simulate_kwargs
    )
    trades = sim["trades"]
    timestamps = df.reset_index(drop=True)[timestamp_col] if timestamp_col in df.columns else None

    ledger = build_trade_ledger(trades)
    equity_curve = build_equity_curve(trades, timestamps=timestamps)
    summary = summarize_simulation(trades, equity_curve)

    report_metadata: dict[str, Any] = {
        "created_at_utc": created_at_utc(),
        "candidate_count": len(candidate_list),
        "simulated_candidate_count": len(candidate_list) - sim["skipped_non_directional"],
        "skipped_non_directional": sim["skipped_non_directional"],
        "bar_count": sim["bar_count"],
        "cost_bps": exec_model.cost_bps,
        "quantity": exec_model.quantity,
    }
    report_metadata.update(dict(metadata or {}))

    report = {
        "sim_caveat": SIM_CAVEAT,
        "tables": {
            "trades": ledger,
            "equity_curve": equity_curve,
            "summary": summary,
        },
        "metadata": json_safe_mapping(report_metadata),
    }
    return validate_sim_report(report)


def write_simulation_report(
    report: Mapping[str, Any],
    output_path: str | Path,
    *,
    overwrite: bool = False,
) -> Path:
    """Validate and write a simulation report to one deterministic JSON file."""
    validated = validate_sim_report(report)
    target = Path(output_path)
    raise_if_exists([target], overwrite=overwrite)
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "sim_caveat": validated["sim_caveat"],
        "metadata": dict(validated.get("metadata", {})),
        "tables": {
            name: dataframe_to_records(table)
            for name, table in validated["tables"].items()
        },
    }
    target.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return target
