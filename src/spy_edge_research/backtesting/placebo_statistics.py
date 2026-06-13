"""Research-only expanded placebo statistics."""

from __future__ import annotations

from collections.abc import Iterable

import numpy as np
import pandas as pd

from spy_edge_research.backtesting.negative_controls import (
    build_random_condition_control,
    build_shifted_condition_control,
    evaluate_negative_control_outcomes,
)


def build_shifted_control_grid(
    df: pd.DataFrame,
    condition_column: str,
    shift_periods: Iterable[int],
) -> tuple[pd.DataFrame, list[str]]:
    """Add multiple shifted placebo control columns."""
    result = df.copy()
    control_columns: list[str] = []
    for period in shift_periods:
        result = build_shifted_condition_control(result, condition_column, shift_periods=period)
        control_columns.append(f"{condition_column}_shift_control_{period}")
    return result, control_columns


def build_repeated_random_controls(
    df: pd.DataFrame,
    condition_column: str,
    *,
    n_controls: int,
    seed: int | None = None,
    prefix: str | None = None,
) -> tuple[pd.DataFrame, list[str]]:
    """Add repeated deterministic random placebo columns."""
    if not isinstance(n_controls, int) or isinstance(n_controls, bool) or n_controls < 1:
        raise ValueError("n_controls must be an integer greater than or equal to 1")
    result = df.copy()
    rng = np.random.default_rng(seed)
    control_columns = []
    name_prefix = prefix or f"{condition_column}_random_placebo"
    for index in range(1, n_controls + 1):
        column = f"{name_prefix}_{index:03d}"
        result = build_random_condition_control(
            result,
            condition_column,
            seed=int(rng.integers(0, 2**32 - 1)),
            output_column=column,
        )
        control_columns.append(column)
    return result, control_columns


def evaluate_placebo_control_suite(
    df: pd.DataFrame,
    condition_column: str,
    outcome_column: str,
    *,
    shift_periods: Iterable[int] | None = None,
    n_random_controls: int = 0,
    seed: int | None = None,
    hit_rate_threshold: float = 0.0,
) -> pd.DataFrame:
    """Evaluate shifted and random placebo controls together."""
    result = df.copy()
    control_columns: list[str] = []
    if shift_periods is not None:
        result, shifted = build_shifted_control_grid(result, condition_column, shift_periods)
        control_columns.extend(shifted)
    if n_random_controls:
        result, random_controls = build_repeated_random_controls(
            result,
            condition_column,
            n_controls=n_random_controls,
            seed=seed,
        )
        control_columns.extend(random_controls)
    if not control_columns:
        raise ValueError("at least one placebo control must be requested")
    return evaluate_negative_control_outcomes(
        result,
        condition_column,
        control_columns,
        outcome_column,
        hit_rate_threshold=hit_rate_threshold,
    )


def summarize_placebo_percentile_ranks(placebo_results: pd.DataFrame) -> pd.DataFrame:
    """Summarize observed metric percentile ranks against placebo controls."""
    _require_columns(placebo_results, ["control_name", "expectancy_difference", "hit_rate_difference"])
    observed = placebo_results.loc[placebo_results["control_name"].eq("observed_condition")]
    if observed.empty:
        raise ValueError("placebo_results must include observed_condition")
    observed_row = observed.iloc[0]
    controls = placebo_results.loc[~placebo_results["control_name"].eq("observed_condition")]
    expectancy = pd.to_numeric(controls["expectancy_difference"], errors="coerce").dropna()
    hit_rate = pd.to_numeric(controls["hit_rate_difference"], errors="coerce").dropna()
    return pd.DataFrame(
        [
            {
                "placebo_control_count": int(len(controls)),
                "observed_expectancy_difference": observed_row["expectancy_difference"],
                "expectancy_placebo_percentile_rank": _percentile_rank(
                    expectancy,
                    observed_row["expectancy_difference"],
                ),
                "expectancy_control_exceedance_rate": _exceedance_rate(
                    expectancy,
                    observed_row["expectancy_difference"],
                ),
                "observed_hit_rate_difference": observed_row["hit_rate_difference"],
                "hit_rate_placebo_percentile_rank": _percentile_rank(
                    hit_rate,
                    observed_row["hit_rate_difference"],
                ),
                "hit_rate_control_exceedance_rate": _exceedance_rate(
                    hit_rate,
                    observed_row["hit_rate_difference"],
                ),
                "placebo_caveat": "placebo_statistics_are_research_diagnostics_only",
            }
        ]
    )


def _percentile_rank(values: pd.Series, observed: float) -> float:
    if values.empty or pd.isna(observed):
        return np.nan
    return float(values.le(observed).mean())


def _exceedance_rate(values: pd.Series, observed: float) -> float:
    if values.empty or pd.isna(observed):
        return np.nan
    return float(values.ge(observed).mean())


def _require_columns(df: pd.DataFrame, columns: list[str]) -> None:
    missing = [column for column in columns if column not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")
