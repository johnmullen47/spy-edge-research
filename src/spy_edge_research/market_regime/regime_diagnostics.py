"""Descriptive diagnostics for market-regime labels."""

from __future__ import annotations

import pandas as pd


def regime_value_counts(
    df: pd.DataFrame,
    regime_col: str,
    normalize: bool = False,
) -> pd.DataFrame:
    """Return counts and proportions for each regime value.

    ``normalize`` is accepted for API symmetry with pandas but the descriptive
    output always includes raw counts and proportions.
    """
    _require_columns(df, [regime_col])

    counts = df[regime_col].value_counts(dropna=False, normalize=False)
    total = len(df)
    result = counts.rename_axis("regime").reset_index(name="count")
    result["proportion"] = result["count"] / total if total else 0.0
    return result.sort_values("count", ascending=False).reset_index(drop=True)


def regime_transition_counts(
    df: pd.DataFrame,
    regime_col: str,
) -> pd.DataFrame:
    """Count previous-row to current-row regime transitions."""
    _require_columns(df, [regime_col])

    transitions = pd.DataFrame(
        {
            "from_regime": df[regime_col].shift(1).iloc[1:],
            "to_regime": df[regime_col].iloc[1:],
        }
    )
    if transitions.empty:
        return pd.DataFrame(columns=["from_regime", "to_regime", "count"])

    result = (
        transitions.value_counts(dropna=False)
        .rename("count")
        .reset_index()
        .sort_values("count", ascending=False)
        .reset_index(drop=True)
    )
    return result


def regime_duration_summary(
    df: pd.DataFrame,
    regime_col: str,
) -> pd.DataFrame:
    """Summarize consecutive same-regime run durations in bars."""
    _require_columns(df, [regime_col])

    if df.empty:
        return pd.DataFrame(
            columns=[
                "regime",
                "n_runs",
                "average_duration_bars",
                "median_duration_bars",
                "max_duration_bars",
            ]
        )

    regimes = df[regime_col]
    run_id = regimes.ne(regimes.shift(1)).cumsum()
    runs = (
        pd.DataFrame({"regime": regimes, "run_id": run_id})
        .groupby(["run_id", "regime"], dropna=False)
        .size()
        .rename("duration")
        .reset_index()
    )
    return (
        runs.groupby("regime", dropna=False)["duration"]
        .agg(
            n_runs="count",
            average_duration_bars="mean",
            median_duration_bars="median",
            max_duration_bars="max",
        )
        .reset_index()
    )


def _require_columns(df: pd.DataFrame, columns: list[str]) -> None:
    missing = [column for column in columns if column not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")
