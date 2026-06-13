"""Research-only temporal stability diagnostics."""

from __future__ import annotations

from collections.abc import Iterable

import numpy as np
import pandas as pd

from spy_edge_research._internal._common import (
    normalize_columns as _normalize_columns,
    require_columns as _require_columns,
)


def assign_temporal_period(
    df: pd.DataFrame,
    timestamp_column: str,
    *,
    period: str = "M",
    output_column: str = "temporal_period",
) -> pd.DataFrame:
    """Assign calendar periods for temporal stability review."""
    _require_columns(df, [timestamp_column])
    result = df.copy()
    timestamps = pd.to_datetime(result[timestamp_column], errors="coerce")
    result[output_column] = timestamps.dt.to_period(period).astype(str)
    return result


def summarize_metric_by_period(
    df: pd.DataFrame,
    period_column: str,
    metric_columns: Iterable[str],
    *,
    id_column: str | None = None,
) -> pd.DataFrame:
    """Summarize metric distributions by period."""
    metrics = _normalize_columns(metric_columns, "metric_columns")
    required = [period_column, *metrics]
    if id_column is not None:
        required.append(id_column)
    _require_columns(df, required)
    rows = []
    for period_value, group in df.groupby(period_column, dropna=False, sort=True):
        row = {
            "temporal_period": period_value,
            "row_count": len(group),
            "unique_item_count": np.nan
            if id_column is None
            else int(group[id_column].nunique()),
        }
        for metric in metrics:
            values = pd.to_numeric(group[metric], errors="coerce").dropna()
            row[f"{metric}_mean"] = np.nan if values.empty else float(values.mean())
            row[f"{metric}_min"] = np.nan if values.empty else float(values.min())
            row[f"{metric}_max"] = np.nan if values.empty else float(values.max())
        row["summary_caveat"] = "temporal_summary_is_descriptive_only"
        rows.append(row)
    return pd.DataFrame(rows)


def summarize_temporal_stability(
    period_summary: pd.DataFrame,
    metric_mean_columns: Iterable[str],
) -> pd.DataFrame:
    """Summarize variation of period-level metric means."""
    metrics = _normalize_columns(metric_mean_columns, "metric_mean_columns")
    _require_columns(period_summary, metrics)
    rows = []
    for metric in metrics:
        values = pd.to_numeric(period_summary[metric], errors="coerce").dropna()
        metric_range = np.nan if values.empty else float(values.max() - values.min())
        metric_mean = np.nan if values.empty else float(values.mean())
        rows.append(
            {
                "metric_mean_column": metric,
                "period_count": int(len(period_summary)),
                "non_missing_period_count": int(values.count()),
                "period_mean_min": np.nan if values.empty else float(values.min()),
                "period_mean_max": np.nan if values.empty else float(values.max()),
                "period_mean_range": metric_range,
                "relative_period_range": np.nan
                if values.empty
                else float(abs(metric_range) / max(abs(metric_mean), 1e-12)),
                "stability_caveat": "temporal_stability_is_not_edge_evidence",
            }
        )
    return pd.DataFrame(rows)


def flag_temporal_concentration(
    period_summary: pd.DataFrame,
    sample_count_column: str,
    *,
    high_share_threshold: float = 0.5,
) -> pd.DataFrame:
    """Flag whether samples are concentrated in a few periods."""
    _require_columns(period_summary, [sample_count_column])
    if high_share_threshold <= 0 or high_share_threshold > 1:
        raise ValueError("high_share_threshold must be in (0, 1]")
    counts = pd.to_numeric(period_summary[sample_count_column], errors="coerce").fillna(0)
    total = float(counts.sum())
    largest = float(counts.max()) if len(counts) else 0.0
    share = 0.0 if total == 0 else largest / total
    return pd.DataFrame(
        [
            {
                "period_count": int(len(period_summary)),
                "total_samples": total,
                "largest_period_samples": largest,
                "largest_period_share": share,
                "temporal_concentration_flag": "high"
                if share >= high_share_threshold
                else "not_high",
                "concentration_caveat": "temporal_concentration_is_descriptive_only",
            }
        ]
    )

