"""Research-only negative control and placebo diagnostics."""

from __future__ import annotations

from collections.abc import Iterable

import numpy as np
import pandas as pd

from spy_edge_research.backtesting.event_forward_outcomes import (
    calculate_event_expectancy,
    calculate_event_hit_rate,
)

from spy_edge_research._internal._common import (
    normalize_columns as _normalize_columns,
    require_columns as _require_columns,
)


def build_shifted_condition_control(
    df: pd.DataFrame,
    condition_column: str,
    *,
    shift_periods: int = 1,
    output_column: str | None = None,
) -> pd.DataFrame:
    """Add a shifted condition control column for placebo review."""
    _require_columns(df, [condition_column])
    if not isinstance(shift_periods, int) or isinstance(shift_periods, bool) or shift_periods == 0:
        raise ValueError("shift_periods must be a non-zero integer")
    result = df.copy()
    target = output_column or f"{condition_column}_shift_control_{shift_periods}"
    result[target] = result[condition_column].fillna(False).astype(bool).shift(
        shift_periods,
        fill_value=False,
    )
    return result


def build_random_condition_control(
    df: pd.DataFrame,
    condition_column: str,
    *,
    seed: int | None = None,
    output_column: str | None = None,
) -> pd.DataFrame:
    """Add a deterministic random permutation control column."""
    _require_columns(df, [condition_column])
    result = df.copy()
    target = output_column or f"{condition_column}_random_control"
    values = result[condition_column].fillna(False).astype(bool).to_numpy()
    rng = np.random.default_rng(seed)
    result[target] = rng.permutation(values)
    return result


def evaluate_negative_control_outcomes(
    df: pd.DataFrame,
    condition_column: str,
    control_columns: Iterable[str],
    outcome_column: str,
    *,
    hit_rate_threshold: float = 0.0,
) -> pd.DataFrame:
    """Compare original condition outcomes to negative controls."""
    controls = _normalize_columns(control_columns, "control_columns")
    _require_columns(df, [condition_column, outcome_column, *controls])
    rows = [
        _condition_summary(
            df,
            condition_column,
            outcome_column,
            control_name="observed_condition",
            hit_rate_threshold=hit_rate_threshold,
        )
    ]
    rows.extend(
        _condition_summary(
            df,
            control,
            outcome_column,
            control_name=control,
            hit_rate_threshold=hit_rate_threshold,
        )
        for control in controls
    )
    return pd.DataFrame(rows)


def summarize_negative_control_risk(control_results: pd.DataFrame) -> pd.DataFrame:
    """Summarize whether controls resemble or exceed observed diagnostics."""
    _require_columns(control_results, ["control_name", "expectancy_difference", "hit_rate_difference"])
    observed = control_results.loc[control_results["control_name"].eq("observed_condition")]
    if observed.empty:
        raise ValueError("control_results must include observed_condition")
    observed_row = observed.iloc[0]
    controls = control_results.loc[~control_results["control_name"].eq("observed_condition")]
    control_expectancy = pd.to_numeric(controls["expectancy_difference"], errors="coerce")
    control_hit_rate = pd.to_numeric(controls["hit_rate_difference"], errors="coerce")
    return pd.DataFrame(
        [
            {
                "control_count": int(len(controls)),
                "observed_expectancy_difference": observed_row["expectancy_difference"],
                "max_control_expectancy_difference": np.nan
                if control_expectancy.empty
                else float(control_expectancy.max()),
                "controls_at_or_above_observed_expectancy": int(
                    control_expectancy.ge(observed_row["expectancy_difference"]).sum()
                ),
                "observed_hit_rate_difference": observed_row["hit_rate_difference"],
                "max_control_hit_rate_difference": np.nan
                if control_hit_rate.empty
                else float(control_hit_rate.max()),
                "controls_at_or_above_observed_hit_rate": int(
                    control_hit_rate.ge(observed_row["hit_rate_difference"]).sum()
                ),
                "risk_caveat": "negative_controls_are_data_mining_diagnostics_only",
            }
        ]
    )


def _condition_summary(
    df: pd.DataFrame,
    condition_column: str,
    outcome_column: str,
    *,
    control_name: str,
    hit_rate_threshold: float,
) -> dict[str, object]:
    mask = df[condition_column].fillna(False).astype(bool)
    outcomes = pd.to_numeric(df[outcome_column], errors="coerce")
    valid = outcomes.notna()
    sample = outcomes.loc[mask & valid]
    baseline = outcomes.loc[valid]
    expectancy = calculate_event_expectancy(sample)
    baseline_expectancy = calculate_event_expectancy(baseline)
    hit_rate = calculate_event_hit_rate(sample, threshold=hit_rate_threshold)
    baseline_hit_rate = calculate_event_hit_rate(baseline, threshold=hit_rate_threshold)
    return {
        "control_name": control_name,
        "condition_column": condition_column,
        "sample_size": int(sample.count()),
        "baseline_sample_size": int(baseline.count()),
        "expectancy": expectancy,
        "baseline_expectancy": baseline_expectancy,
        "expectancy_difference": expectancy - baseline_expectancy,
        "hit_rate": hit_rate,
        "baseline_hit_rate": baseline_hit_rate,
        "hit_rate_difference": hit_rate - baseline_hit_rate,
        "control_caveat": "negative_control_result_is_not_edge_evidence",
    }

