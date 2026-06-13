"""Research-only data quality and coverage impact helpers."""

from __future__ import annotations

from collections.abc import Iterable

import pandas as pd


def summarize_column_coverage(
    df: pd.DataFrame,
    columns: Iterable[str],
) -> pd.DataFrame:
    """Summarize non-missing coverage for selected columns."""
    selected = _normalize_columns(columns, "columns")
    _require_columns(df, selected)
    rows = []
    row_count = len(df)
    for column in selected:
        non_missing = int(df[column].notna().sum())
        rows.append(
            {
                "column": column,
                "row_count": row_count,
                "non_missing_count": non_missing,
                "missing_count": row_count - non_missing,
                "coverage_rate": 0.0 if row_count == 0 else non_missing / row_count,
                "coverage_caveat": "coverage_summary_is_research_diagnostic_only",
            }
        )
    return pd.DataFrame(rows)


def summarize_session_coverage(
    df: pd.DataFrame,
    session_column: str,
    *,
    date_column: str | None = None,
) -> pd.DataFrame:
    """Summarize row coverage by session/context bucket."""
    required = [session_column]
    if date_column is not None:
        required.append(date_column)
    _require_columns(df, required)
    rows = []
    for session, group in df.groupby(session_column, dropna=False, sort=True):
        rows.append(
            {
                "session_value": session,
                "row_count": len(group),
                "unique_date_count": None
                if date_column is None
                else int(group[date_column].nunique()),
                "coverage_caveat": "session_coverage_is_descriptive_only",
            }
        )
    return pd.DataFrame(rows)


def evaluate_quality_filter_impact(
    df: pd.DataFrame,
    quality_mask_column: str,
    metric_columns: Iterable[str],
) -> pd.DataFrame:
    """Compare metric means inside versus outside a quality mask."""
    metrics = _normalize_columns(metric_columns, "metric_columns")
    _require_columns(df, [quality_mask_column, *metrics])
    mask = df[quality_mask_column].fillna(False).astype(bool)
    rows = []
    for metric in metrics:
        included = pd.to_numeric(df.loc[mask, metric], errors="coerce").dropna()
        excluded = pd.to_numeric(df.loc[~mask, metric], errors="coerce").dropna()
        rows.append(
            {
                "metric_column": metric,
                "included_count": int(included.count()),
                "excluded_count": int(excluded.count()),
                "included_mean": None if included.empty else float(included.mean()),
                "excluded_mean": None if excluded.empty else float(excluded.mean()),
                "mean_difference_included_minus_excluded": None
                if included.empty or excluded.empty
                else float(included.mean() - excluded.mean()),
                "impact_caveat": "quality_filter_impact_is_descriptive_only",
            }
        )
    return pd.DataFrame(rows)


def summarize_required_context_coverage(
    df: pd.DataFrame,
    required_columns: Iterable[str],
) -> pd.DataFrame:
    """Summarize complete-case coverage for required context columns."""
    columns = _normalize_columns(required_columns, "required_columns")
    _require_columns(df, columns)
    complete = df[columns].notna().all(axis=1)
    return pd.DataFrame(
        [
            {
                "required_column_count": len(columns),
                "row_count": len(df),
                "complete_context_count": int(complete.sum()),
                "incomplete_context_count": int((~complete).sum()),
                "complete_context_rate": 0.0 if len(df) == 0 else float(complete.mean()),
                "coverage_caveat": "context_coverage_is_research_diagnostic_only",
            }
        ]
    )


def _normalize_columns(columns: Iterable[str], name: str) -> list[str]:
    if isinstance(columns, str):
        normalized = [columns]
    else:
        normalized = list(columns)
    if not normalized or not all(isinstance(column, str) and column for column in normalized):
        raise ValueError(f"{name} must contain at least one column name")
    return normalized


def _require_columns(df: pd.DataFrame, columns: Iterable[str]) -> None:
    missing = [column for column in columns if column not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")
