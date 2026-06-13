"""Research-only event study conditioned on value/quality/momentum factor scores (MOD 13).

Buckets rows by a causal factor score (or its cross-sectional rank) and summarizes
the forward outcome label within each bucket, plus the descriptive top-minus-bottom
spread and coverage. Causality is preserved by construction: the score is a feature
(current/prior rows only) and the outcome is a ``forward_*`` label — this study
relates the two but never feeds the label back into a feature. The spread is a
descriptive research statistic, not an edge claim, allocation, or trade signal.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from spy_edge_research._internal._common import (
    created_at_utc,
    json_safe_mapping,
    raise_if_exists,
    require_columns,
)

VQM_EVENT_STUDY_CAVEAT = "vqm_factor_outcome_study_is_descriptive_research_not_edge_claim"

BUCKET_SUMMARY_COLUMNS: tuple[str, ...] = (
    "bucket",
    "count",
    "score_min",
    "score_max",
    "outcome_mean",
    "outcome_std",
)


def summarize_outcomes_by_factor_score(
    df: pd.DataFrame,
    *,
    score_col: str,
    outcome_col: str,
    n_buckets: int = 5,
) -> pd.DataFrame:
    """Bucket rows by ``score_col`` (quantile) and summarize ``outcome_col`` per bucket.

    Buckets are ordered low→high by score. Rows missing either the score or the
    outcome are dropped. Uses rank-based quantiles so heavily-tied scores still
    bucket; bucket count may be fewer than ``n_buckets`` when the data is degenerate.
    """
    if not isinstance(n_buckets, int) or isinstance(n_buckets, bool) or n_buckets < 1:
        raise ValueError("n_buckets must be an integer >= 1")
    require_columns(df, [score_col, outcome_col])

    work = df[[score_col, outcome_col]].copy()
    work[score_col] = pd.to_numeric(work[score_col], errors="coerce")
    work[outcome_col] = pd.to_numeric(work[outcome_col], errors="coerce")
    work = work.dropna(subset=[score_col, outcome_col])
    if work.empty:
        return pd.DataFrame(columns=list(BUCKET_SUMMARY_COLUMNS))

    # Rank-based quantile bucketing is robust to ties; drop empty edge bins.
    ranks = work[score_col].rank(method="first")
    try:
        bucket = pd.qcut(ranks, q=min(n_buckets, work[score_col].nunique()), labels=False, duplicates="drop")
    except ValueError:
        bucket = pd.Series(0, index=work.index)
    work = work.assign(_bucket=bucket.astype(int))

    rows: list[dict[str, Any]] = []
    for bucket_id, group in work.groupby("_bucket", sort=True):
        rows.append(
            {
                "bucket": int(bucket_id),
                "count": int(len(group)),
                "score_min": float(group[score_col].min()),
                "score_max": float(group[score_col].max()),
                "outcome_mean": float(group[outcome_col].mean()),
                "outcome_std": float(group[outcome_col].std(ddof=0)),
            }
        )
    return pd.DataFrame(rows, columns=list(BUCKET_SUMMARY_COLUMNS))


def factor_score_bucket_spread(bucket_summary: pd.DataFrame) -> pd.DataFrame:
    """Descriptive top-minus-bottom bucket spread of the outcome mean (one row)."""
    require_columns(bucket_summary, ["bucket", "outcome_mean", "count"])
    if bucket_summary.empty:
        return pd.DataFrame(
            [{"top_bucket": None, "bottom_bucket": None, "top_outcome_mean": np.nan,
              "bottom_outcome_mean": np.nan, "outcome_mean_spread": np.nan,
              "spread_caveat": VQM_EVENT_STUDY_CAVEAT}]
        )
    ordered = bucket_summary.sort_values("bucket", kind="mergesort")
    top = ordered.iloc[-1]
    bottom = ordered.iloc[0]
    return pd.DataFrame(
        [
            {
                "top_bucket": int(top["bucket"]),
                "bottom_bucket": int(bottom["bucket"]),
                "top_outcome_mean": float(top["outcome_mean"]),
                "bottom_outcome_mean": float(bottom["outcome_mean"]),
                "outcome_mean_spread": float(top["outcome_mean"]) - float(bottom["outcome_mean"]),
                "spread_caveat": VQM_EVENT_STUDY_CAVEAT,
            }
        ]
    )


def summarize_factor_score_coverage(
    df: pd.DataFrame,
    *,
    score_col: str,
    outcome_col: str,
) -> pd.DataFrame:
    """Row counts: total, non-null score, non-null outcome, and usable (both)."""
    require_columns(df, [score_col, outcome_col])
    score = pd.to_numeric(df[score_col], errors="coerce")
    outcome = pd.to_numeric(df[outcome_col], errors="coerce")
    return pd.DataFrame(
        [
            {
                "total_rows": int(len(df)),
                "non_null_score": int(score.notna().sum()),
                "non_null_outcome": int(outcome.notna().sum()),
                "usable_rows": int((score.notna() & outcome.notna()).sum()),
            }
        ]
    )


def build_vqm_event_research_report(
    df: pd.DataFrame,
    *,
    score_col: str,
    outcome_col: str,
    n_buckets: int = 5,
    metadata: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a small VQM factor-outcome research report bundle."""
    bucket_summary = summarize_outcomes_by_factor_score(
        df, score_col=score_col, outcome_col=outcome_col, n_buckets=n_buckets
    )
    spread = factor_score_bucket_spread(bucket_summary)
    coverage = summarize_factor_score_coverage(df, score_col=score_col, outcome_col=outcome_col)
    report_metadata = {
        "created_at_utc": created_at_utc(),
        "score_col": score_col,
        "outcome_col": outcome_col,
        "n_buckets": int(n_buckets),
        "report_caveat": VQM_EVENT_STUDY_CAVEAT,
    }
    report_metadata.update(dict(metadata or {}))
    return {
        "metadata": json_safe_mapping(report_metadata),
        "tables": {
            "bucket_outcomes": bucket_summary,
            "bucket_spread": spread,
            "coverage": coverage,
        },
    }


def export_vqm_event_research_report_to_csv(
    report: Mapping[str, Any],
    output_dir: str | Path,
    *,
    overwrite: bool = False,
) -> dict[str, Path]:
    """Export a VQM report bundle's tables (+ metadata) to deterministic CSV files."""
    tables = report.get("tables")
    if not isinstance(tables, Mapping):
        raise KeyError("report must contain a tables mapping")
    output_path = Path(output_dir)
    targets = {name: output_path / f"{name}.csv" for name in tables}
    targets["metadata"] = output_path / "metadata.json"
    raise_if_exists(targets.values(), overwrite=overwrite)
    output_path.mkdir(parents=True, exist_ok=True)
    written: dict[str, Path] = {}
    for name, table in tables.items():
        if not isinstance(table, pd.DataFrame):
            raise TypeError(f"tables.{name} must be a DataFrame")
        table.to_csv(targets[name], index=False)
        written[name] = targets[name]
    targets["metadata"].write_text(
        json.dumps(dict(report.get("metadata", {})), indent=2, sort_keys=True), encoding="utf-8"
    )
    written["metadata"] = targets["metadata"]
    return written
