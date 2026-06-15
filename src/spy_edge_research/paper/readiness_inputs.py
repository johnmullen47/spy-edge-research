"""Assemble readiness metrics from upstream research summaries.

Bridges existing research outputs — OOS stability summaries (from
``summarize_oos_edge_stability``), the MOD 06 risk signal-overlap summary /
exposure-limit checks, and control-pass flags — into the metrics mapping that
``score_candidate_readiness`` consumes. This is a read-only reshaping step: it
moves already-computed research numbers into the gate's input shape and makes no
trade decision of its own.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pandas as pd


def build_readiness_metrics(
    *,
    oos_stability_row: pd.DataFrame | pd.Series | Mapping[str, Any] | None = None,
    exposure_limit_checks: pd.DataFrame | None = None,
    signal_overlap_summary: pd.DataFrame | pd.Series | Mapping[str, Any] | None = None,
    negative_control_passed: bool | None = None,
    multiple_testing_passed: bool | None = None,
    temporal_stable_period_count: int | None = None,
    pbo: float | None = None,
    deflated_sharpe: float | None = None,
) -> dict[str, Any]:
    """Build a readiness metrics mapping from upstream research summaries.

    Only the inputs that are provided (and non-null) contribute a metric; missing
    metrics are left out so the readiness gate can treat them as insufficient
    evidence.
    """
    metrics: dict[str, Any] = {}

    if oos_stability_row is not None:
        row = _as_row(oos_stability_row, "oos_stability_row")
        splits = row.get("oos_positive_expectancy_difference_splits")
        if splits is not None and pd.notna(splits):
            metrics["oos_positive_expectancy_difference_splits"] = int(splits)
        sample = row.get("oos_mean_sample_size")
        if sample is not None and pd.notna(sample):
            metrics["oos_mean_sample_size"] = float(sample)
        edge = row.get("oos_mean_expectancy_difference")
        if edge is not None and pd.notna(edge):
            # Forward returns are fractional; express the out-of-sample edge in
            # basis points for the economic-significance criterion.
            metrics["edge_bps"] = float(edge) * 1e4

    overlap = _extract_max_pairwise_jaccard(exposure_limit_checks, signal_overlap_summary)
    if overlap is not None:
        metrics["max_pairwise_jaccard"] = overlap

    if negative_control_passed is not None:
        metrics["negative_control_passed"] = bool(negative_control_passed)
    if multiple_testing_passed is not None:
        metrics["multiple_testing_passed"] = bool(multiple_testing_passed)
    if temporal_stable_period_count is not None:
        metrics["temporal_stable_period_count"] = int(temporal_stable_period_count)
    if pbo is not None and pd.notna(pbo):
        metrics["pbo"] = float(pbo)
    if deflated_sharpe is not None and pd.notna(deflated_sharpe):
        metrics["deflated_sharpe"] = float(deflated_sharpe)

    return metrics


def _extract_max_pairwise_jaccard(
    exposure_limit_checks: pd.DataFrame | None,
    signal_overlap_summary: pd.DataFrame | pd.Series | Mapping[str, Any] | None,
) -> float | None:
    if signal_overlap_summary is not None:
        row = _as_row(signal_overlap_summary, "signal_overlap_summary")
        value = row.get("max_jaccard")
        if value is not None and pd.notna(value):
            return float(value)
    if exposure_limit_checks is not None:
        if not isinstance(exposure_limit_checks, pd.DataFrame):
            raise TypeError("exposure_limit_checks must be a DataFrame")
        if "check" in exposure_limit_checks.columns:
            match = exposure_limit_checks.loc[exposure_limit_checks["check"] == "max_pairwise_jaccard"]
            if not match.empty:
                value = match.iloc[0].get("observed")
                if value is not None and pd.notna(value):
                    return float(value)
    return None


def _as_row(value: Any, name: str) -> pd.Series:
    if isinstance(value, pd.DataFrame):
        if value.empty:
            raise ValueError(f"{name} must have at least one row")
        return value.iloc[0]
    if isinstance(value, pd.Series):
        return value
    if isinstance(value, Mapping):
        return pd.Series(dict(value))
    raise TypeError(f"{name} must be a DataFrame, Series, or mapping")
