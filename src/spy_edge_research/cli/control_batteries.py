"""Control batteries for the MOD 11 pipeline (M101).

Runs the three research-control batteries — negative controls, multiple-testing
family-size risk, and temporal stability — over the pipeline's candidate set and
reduces each to the scalar the readiness gate consumes
(``negative_control_passed``, ``multiple_testing_passed``,
``temporal_stable_period_count``).

This is glue only: it reuses the already-committed battery implementations in
``backtesting/`` and reimplements no statistics. Every output is a descriptive
research diagnostic — never a trade signal, order, or authorization. The causal /
no-lookahead invariant is unchanged: forward-return columns are read as outcome
labels only, never as event inputs.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from spy_edge_research.backtesting.negative_controls import (
    build_random_condition_control,
    build_shifted_condition_control,
    evaluate_negative_control_outcomes,
    summarize_negative_control_risk,
)
from spy_edge_research.backtesting.multiple_testing import count_tested_hypotheses
from spy_edge_research.backtesting.temporal_stability import (
    assign_temporal_period,
    summarize_metric_by_period,
    summarize_temporal_stability,
)

CONTROL_BATTERY_CAVEAT = (
    "control_battery_results_are_research_diagnostics_not_trade_authorization"
)
MULTIPLE_TESTING_HEURISTIC_CAVEAT = (
    "multiple_testing_gate_is_family_size_heuristic_no_p_values_in_basic_pipeline"
)
TEMPORAL_COUNT_CAVEAT = (
    "temporal_stable_period_count_is_active_period_count_not_metric_stability"
)

_TIMESTAMP_CANDIDATE_COLUMNS = ("timestamp", "datetime", "date", "time")
_INTERNAL_TIMESTAMP_COLUMN = "__control_battery_timestamp__"


@dataclass(frozen=True)
class ControlBatteryConfig:
    """Tunable inputs for the control batteries (deterministic defaults)."""

    shift_periods: tuple[int, ...] = (1, 2, 3)
    n_random_controls: int = 5
    random_seed: int = 0
    temporal_period: str = "M"
    timestamp_column: str | None = None  # auto-detect when None
    multiple_testing_high_count: int = 100  # warning == "high" at/above this


@dataclass
class ControlBatteryResults:
    """Per-candidate and portfolio control outcomes, plus artifact tables."""

    per_candidate: dict[str, dict[str, Any]]
    multiple_testing_passed: bool
    tested_hypotheses: int
    multiple_testing_warning: str
    negative_control_table: pd.DataFrame
    temporal_stability_table: pd.DataFrame
    multiple_testing_table: pd.DataFrame
    caveats: list[str] = field(default_factory=list)


def run_control_batteries(
    df: pd.DataFrame,
    registry: pd.DataFrame,
    *,
    config: ControlBatteryConfig | None = None,
) -> ControlBatteryResults:
    """Run the three control batteries over ``registry`` candidates against ``df``.

    ``registry`` is an in-memory candidate edge registry (each row carries
    ``candidate_id``, ``name`` = the event/condition column, and a ``context``
    mapping holding ``label_column`` = the forward-return outcome column).
    """
    cfg = config or ControlBatteryConfig()
    caveats = [
        CONTROL_BATTERY_CAVEAT,
        MULTIPLE_TESTING_HEURISTIC_CAVEAT,
        TEMPORAL_COUNT_CAVEAT,
    ]

    # Portfolio-level multiple-testing family-size guard. The basic pipeline does
    # not compute per-candidate p-values, so we apply the module's own coarse
    # family-size heuristic: a large search family raises multiple-testing risk.
    tested = int(count_tested_hypotheses(registry))
    warning = (
        "high"
        if tested >= cfg.multiple_testing_high_count
        else "moderate"
        if tested >= 20
        else "low"
    )
    multiple_testing_passed = warning != "high"
    multiple_testing_table = pd.DataFrame(
        [
            {
                "tested_hypotheses": tested,
                "high_count_threshold": cfg.multiple_testing_high_count,
                "multiple_testing_warning": warning,
                "multiple_testing_passed": multiple_testing_passed,
                "multiple_testing_caveat": MULTIPLE_TESTING_HEURISTIC_CAVEAT,
            }
        ]
    )

    ts_df, ts_col = _ensure_timestamp(df, cfg.timestamp_column)

    per_candidate: dict[str, dict[str, Any]] = {}
    nc_rows: list[pd.DataFrame] = []
    ts_rows: list[pd.DataFrame] = []

    for _, row in registry.iterrows():
        candidate_id = str(row["candidate_id"])
        event_column = str(row.get("name", ""))
        context = row.get("context")
        outcome_column = (
            str(context.get("label_column", ""))
            if isinstance(context, Mapping)
            else ""
        )

        nc_passed, nc_summary = _negative_control_for(
            df, event_column, outcome_column, cfg
        )
        temporal_count, ts_summary = _temporal_stability_for(
            ts_df, ts_col, event_column, outcome_column, cfg
        )

        per_candidate[candidate_id] = {
            "negative_control_passed": nc_passed,
            "temporal_stable_period_count": temporal_count,
        }
        if nc_summary is not None:
            nc_summary = nc_summary.copy()
            nc_summary.insert(0, "candidate_id", candidate_id)
            nc_rows.append(nc_summary)
        if ts_summary is not None:
            ts_summary = ts_summary.copy()
            ts_summary.insert(0, "candidate_id", candidate_id)
            ts_rows.append(ts_summary)

    negative_control_table = (
        pd.concat(nc_rows, ignore_index=True) if nc_rows else pd.DataFrame()
    )
    temporal_stability_table = (
        pd.concat(ts_rows, ignore_index=True) if ts_rows else pd.DataFrame()
    )

    return ControlBatteryResults(
        per_candidate=per_candidate,
        multiple_testing_passed=multiple_testing_passed,
        tested_hypotheses=tested,
        multiple_testing_warning=warning,
        negative_control_table=negative_control_table,
        temporal_stability_table=temporal_stability_table,
        multiple_testing_table=multiple_testing_table,
        caveats=caveats,
    )


def _ensure_timestamp(
    df: pd.DataFrame, timestamp_column: str | None
) -> tuple[pd.DataFrame, str | None]:
    """Return (frame, timestamp_column) for the temporal battery, or (df, None)."""
    if timestamp_column and timestamp_column in df.columns:
        return df, timestamp_column
    for candidate in _TIMESTAMP_CANDIDATE_COLUMNS:
        if candidate in df.columns:
            return df, candidate
    if isinstance(df.index, pd.DatetimeIndex):
        out = df.copy()
        out[_INTERNAL_TIMESTAMP_COLUMN] = df.index
        return out, _INTERNAL_TIMESTAMP_COLUMN
    return df, None


def _negative_control_for(
    df: pd.DataFrame,
    event_column: str,
    outcome_column: str,
    cfg: ControlBatteryConfig,
) -> tuple[bool, pd.DataFrame | None]:
    """Pass iff the observed edge is finite and beats every negative control."""
    if not event_column or event_column not in df.columns:
        return False, None
    if not outcome_column or outcome_column not in df.columns:
        return False, None

    work = df
    control_columns: list[str] = []
    for shift in cfg.shift_periods:
        target = f"{event_column}_shift_control_{shift}"
        work = build_shifted_condition_control(
            work, event_column, shift_periods=shift, output_column=target
        )
        control_columns.append(target)
    for index in range(cfg.n_random_controls):
        target = f"{event_column}_random_control_{index}"
        work = build_random_condition_control(
            work, event_column, seed=cfg.random_seed + index, output_column=target
        )
        control_columns.append(target)

    if not control_columns:
        return False, None

    results = evaluate_negative_control_outcomes(
        work, event_column, control_columns, outcome_column
    )
    summary = summarize_negative_control_risk(results)
    observed = summary.iloc[0]["observed_expectancy_difference"]
    at_or_above = int(summary.iloc[0]["controls_at_or_above_observed_expectancy"])
    passed = bool(pd.notna(observed) and at_or_above == 0)
    summary = summary.copy()
    summary["negative_control_passed"] = passed
    return passed, summary


def _temporal_stability_for(
    ts_df: pd.DataFrame,
    ts_col: str | None,
    event_column: str,
    outcome_column: str,
    cfg: ControlBatteryConfig,
) -> tuple[int, pd.DataFrame | None]:
    """Count distinct calendar periods in which the event produced an outcome."""
    if ts_col is None:
        return 0, None
    if not event_column or event_column not in ts_df.columns:
        return 0, None
    if not outcome_column or outcome_column not in ts_df.columns:
        return 0, None

    mask = ts_df[event_column].fillna(False).astype(bool)
    sub = ts_df.loc[mask, [ts_col, outcome_column]]
    if sub.empty:
        return 0, None

    sub = assign_temporal_period(sub, ts_col, period=cfg.temporal_period)
    by_period = summarize_metric_by_period(sub, "temporal_period", [outcome_column])
    stability = summarize_temporal_stability(by_period, [f"{outcome_column}_mean"])
    count = int(stability.iloc[0]["non_missing_period_count"])
    stability = stability.copy()
    stability["temporal_stable_period_count"] = count
    return count, stability
