"""Research-only factor-context event outcome studies."""

from __future__ import annotations

from collections.abc import Iterable, Mapping

import pandas as pd

from spy_edge_research.backtesting.event_forward_outcomes import (
    EVENT_FORWARD_OUTCOME_COLUMNS,
    summarize_event_forward_returns,
)
from spy_edge_research.signal_engine.event_catalog import validate_event_catalog

from spy_edge_research._internal._common import (
    normalize_columns as _normalize_columns,
    require_columns as _require_columns,
    validate_positive_int as _validate_positive_int,
)


FACTOR_EVENT_STUDY_CAVEAT = "factor_event_study_is_descriptive_research_only"
FACTOR_CONTEXT_COLUMNS = [
    "context_key",
    "context_sample_count",
    "context_coverage_rate",
    "context_sample_flag",
]


def summarize_event_by_factor_context(
    df: pd.DataFrame,
    event_column: str,
    outcome_column: str,
    context_columns: Iterable[str],
    *,
    event_family: str = "unknown",
    event_direction: str = "unknown",
    hit_rate_threshold: float = 0.0,
    min_events: int = 1,
    min_context_rows: int = 1,
) -> pd.DataFrame:
    """Summarize one event/outcome pair inside factor context groups."""
    contexts = _normalize_columns(context_columns, "context_columns")
    _validate_positive_int(min_context_rows, "min_context_rows")
    _require_columns(df, [event_column, outcome_column, *contexts])
    rows: list[dict[str, object]] = []
    total_rows = len(df)
    for context_values, context_df in _iter_context_groups(df, contexts):
        summary = summarize_event_forward_returns(
            context_df,
            event_column,
            [outcome_column],
            event_family=event_family,
            event_direction=event_direction,
            hit_rate_threshold=hit_rate_threshold,
            min_events=min_events,
        ).iloc[0]
        rows.append(
            {
                **_context_record(contexts, context_values, len(context_df), total_rows, min_context_rows),
                **summary.to_dict(),
                "study_caveat": FACTOR_EVENT_STUDY_CAVEAT,
            }
        )
    return pd.DataFrame(rows, columns=_study_columns(contexts))


def compare_factor_context_event_outcomes(
    summary_table: pd.DataFrame,
    *,
    context_column: str = "factor_leadership_style",
    context_values: Mapping[str, str] | None = None,
) -> pd.DataFrame:
    """Compare descriptive event outcomes across factor context values."""
    _require_columns(
        summary_table,
        [
            "event_column",
            "outcome_column",
            context_column,
            "event_count",
            "event_expectancy",
            "event_hit_rate",
        ],
    )
    if context_values is None:
        present = sorted(str(value) for value in summary_table[context_column].dropna().unique())
        labels = {value: value for value in present}
    else:
        labels = dict(context_values)

    keys = ["event_column", "outcome_column"]
    base = summary_table[keys].drop_duplicates().copy()
    for label, value in labels.items():
        subset = summary_table.loc[
            summary_table[context_column].astype(str).eq(str(value)),
            [*keys, "event_count", "event_expectancy", "event_hit_rate"],
        ].rename(
            columns={
                "event_count": f"{label}_event_count",
                "event_expectancy": f"{label}_event_expectancy",
                "event_hit_rate": f"{label}_event_hit_rate",
            }
        )
        base = base.merge(subset, on=keys, how="left")
    for column in [column for column in base.columns if column.endswith("_event_count")]:
        base[column] = base[column].fillna(0).astype(int)
    base["comparison_caveat"] = "descriptive_factor_context_comparison_not_edge_claim"
    return base


def build_factor_event_outcome_table(
    df: pd.DataFrame,
    catalog: pd.DataFrame,
    outcome_columns: Iterable[str],
    context_columns: Iterable[str],
    *,
    hit_rate_threshold: float = 0.0,
    min_events: int = 1,
    min_context_rows: int = 1,
) -> pd.DataFrame:
    """Build factor-context conditioned outcome rows for each catalog event."""
    validated = validate_event_catalog(catalog)
    outcomes = _normalize_columns(outcome_columns, "outcome_columns")
    contexts = _normalize_columns(context_columns, "context_columns")
    _require_columns(df, [*outcomes, *contexts])
    if validated.empty:
        return pd.DataFrame(columns=_study_columns(contexts))
    tables = []
    for event in validated.itertuples(index=False):
        _require_columns(df, [event.event_column])
        for outcome_column in outcomes:
            tables.append(
                summarize_event_by_factor_context(
                    df,
                    event.event_column,
                    outcome_column,
                    contexts,
                    event_family=event.event_family,
                    event_direction=event.event_direction,
                    hit_rate_threshold=hit_rate_threshold,
                    min_events=min_events,
                    min_context_rows=min_context_rows,
                )
            )
    if not tables:
        return pd.DataFrame(columns=_study_columns(contexts))
    return pd.concat(tables, ignore_index=True)


def summarize_factor_context_coverage(
    df: pd.DataFrame,
    context_columns: Iterable[str],
    *,
    min_context_rows: int = 1,
) -> pd.DataFrame:
    """Summarize factor context availability and sample sizes."""
    contexts = _normalize_columns(context_columns, "context_columns")
    _validate_positive_int(min_context_rows, "min_context_rows")
    _require_columns(df, contexts)
    total_rows = len(df)
    rows: list[dict[str, object]] = []
    for context_values, context_df in _iter_context_groups(df, contexts):
        rows.append(_context_record(contexts, context_values, len(context_df), total_rows, min_context_rows))
    missing_count = int(df[contexts].isna().any(axis=1).sum())
    rows.append(
        {
            "context_key": "__missing_factor_context_rows__",
            "context_sample_count": missing_count,
            "context_coverage_rate": float(missing_count / total_rows) if total_rows else float("nan"),
            "context_sample_flag": "diagnostic",
            **{context: None for context in contexts},
        }
    )
    return pd.DataFrame(rows, columns=[*FACTOR_CONTEXT_COLUMNS, *contexts])


def build_factor_event_research_report(
    df: pd.DataFrame,
    catalog: pd.DataFrame,
    outcome_columns: Iterable[str],
    context_columns: Iterable[str],
    *,
    comparison_context_column: str | None = None,
    hit_rate_threshold: float = 0.0,
    min_events: int = 1,
    min_context_rows: int = 1,
) -> dict[str, object]:
    """Build deterministic factor-event report tables for research review."""
    contexts = _normalize_columns(context_columns, "context_columns")
    outcomes = _normalize_columns(outcome_columns, "outcome_columns")
    outcome_table = build_factor_event_outcome_table(
        df,
        catalog,
        outcomes,
        contexts,
        hit_rate_threshold=hit_rate_threshold,
        min_events=min_events,
        min_context_rows=min_context_rows,
    )
    comparison_column = comparison_context_column or contexts[0]
    comparison_table = (
        compare_factor_context_event_outcomes(outcome_table, context_column=comparison_column)
        if not outcome_table.empty and comparison_column in outcome_table.columns
        else pd.DataFrame()
    )
    return {
        "metadata": {
            "report_caveat": FACTOR_EVENT_STUDY_CAVEAT,
            "forward_outcomes_are_evaluation_only": True,
            "context_columns": contexts,
            "outcome_columns": outcomes,
            "comparison_context_column": comparison_column,
        },
        "context_coverage": summarize_factor_context_coverage(
            df,
            contexts,
            min_context_rows=min_context_rows,
        ),
        "event_outcomes": outcome_table,
        "factor_context_comparison": comparison_table,
    }


def _iter_context_groups(df: pd.DataFrame, contexts: list[str]):
    groupby_key = contexts[0] if len(contexts) == 1 else contexts
    for context_values, context_df in df.groupby(groupby_key, dropna=False, sort=False):
        if len(contexts) == 1:
            yield (context_values,), context_df
        else:
            yield tuple(context_values), context_df


def _context_record(
    contexts: list[str],
    context_values: tuple[object, ...],
    context_sample_count: int,
    total_rows: int,
    min_context_rows: int = 1,
) -> dict[str, object]:
    values = dict(zip(contexts, context_values))
    return {
        "context_key": "|".join(f"{column}={values[column]}" for column in contexts),
        "context_sample_count": int(context_sample_count),
        "context_coverage_rate": float(context_sample_count / total_rows) if total_rows else float("nan"),
        "context_sample_flag": "ok" if context_sample_count >= min_context_rows else "small_context_sample",
        **values,
    }


def _study_columns(contexts: list[str]) -> list[str]:
    return [
        *FACTOR_CONTEXT_COLUMNS,
        *contexts,
        *EVENT_FORWARD_OUTCOME_COLUMNS,
        "study_caveat",
    ]

