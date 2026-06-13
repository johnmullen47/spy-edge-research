"""Research-only multi-instrument context event outcome studies."""

from __future__ import annotations

from collections.abc import Iterable

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


MULTI_INSTRUMENT_CONTEXT_COLUMNS = [
    "context_key",
    "context_sample_count",
    "context_coverage_rate",
    "context_sample_flag",
]
MULTI_INSTRUMENT_CAVEAT = "multi_instrument_event_study_is_descriptive_research_only"


def summarize_event_by_instrument_context(
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
    """Summarize one event/outcome pair inside cross-instrument contexts."""
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
        context_sample_count = len(context_df)
        rows.append(
            {
                **_context_record(contexts, context_values, context_sample_count, total_rows),
                **summary.to_dict(),
                "study_caveat": MULTI_INSTRUMENT_CAVEAT,
            }
        )
    return pd.DataFrame(rows, columns=_study_columns(contexts))


def compare_confirmed_vs_divergent_event_outcomes(
    summary_table: pd.DataFrame,
    *,
    context_column: str = "cross_trend_context",
    confirmed_value: str = "confirmed",
    divergent_value: str = "divergent",
) -> pd.DataFrame:
    """Compare descriptive outcome rows for confirmed and divergent contexts."""
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
    keys = ["event_column", "outcome_column"]
    confirmed = summary_table.loc[summary_table[context_column].eq(confirmed_value)]
    divergent = summary_table.loc[summary_table[context_column].eq(divergent_value)]
    merged = confirmed.merge(
        divergent,
        on=keys,
        suffixes=("_confirmed", "_divergent"),
        how="outer",
    )
    if merged.empty:
        return pd.DataFrame(
            columns=[
                *keys,
                "confirmed_event_count",
                "divergent_event_count",
                "expectancy_difference_confirmed_minus_divergent",
                "hit_rate_difference_confirmed_minus_divergent",
                "comparison_caveat",
            ]
        )
    result = pd.DataFrame(
        {
            "event_column": merged["event_column"],
            "outcome_column": merged["outcome_column"],
            "confirmed_event_count": merged["event_count_confirmed"].fillna(0).astype(int),
            "divergent_event_count": merged["event_count_divergent"].fillna(0).astype(int),
            "expectancy_difference_confirmed_minus_divergent": (
                merged["event_expectancy_confirmed"] - merged["event_expectancy_divergent"]
            ),
            "hit_rate_difference_confirmed_minus_divergent": (
                merged["event_hit_rate_confirmed"] - merged["event_hit_rate_divergent"]
            ),
            "comparison_caveat": "descriptive_context_comparison_not_edge_claim",
        }
    )
    return result


def build_multi_instrument_event_outcome_table(
    df: pd.DataFrame,
    catalog: pd.DataFrame,
    outcome_columns: Iterable[str],
    context_columns: Iterable[str],
    *,
    hit_rate_threshold: float = 0.0,
    min_events: int = 1,
    min_context_rows: int = 1,
) -> pd.DataFrame:
    """Build context-conditioned outcome rows for each catalog event."""
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
                summarize_event_by_instrument_context(
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


def summarize_multi_instrument_context_coverage(
    df: pd.DataFrame,
    context_columns: Iterable[str],
    *,
    min_context_rows: int = 1,
) -> pd.DataFrame:
    """Summarize cross-instrument context availability and sample sizes."""
    contexts = _normalize_columns(context_columns, "context_columns")
    _validate_positive_int(min_context_rows, "min_context_rows")
    _require_columns(df, contexts)
    total_rows = len(df)
    rows: list[dict[str, object]] = []
    for context_values, context_df in _iter_context_groups(df, contexts):
        rows.append(_context_record(contexts, context_values, len(context_df), total_rows, min_context_rows))
    rows.append(
        {
            "context_key": "__missing_context_rows__",
            "context_sample_count": int(df[contexts].isna().any(axis=1).sum()),
            "context_coverage_rate": (
                float(df[contexts].isna().any(axis=1).sum() / total_rows) if total_rows else float("nan")
            ),
            "context_sample_flag": "diagnostic",
            **{context: None for context in contexts},
        }
    )
    return pd.DataFrame(rows, columns=[*MULTI_INSTRUMENT_CONTEXT_COLUMNS, *contexts])


def build_multi_instrument_research_report(
    df: pd.DataFrame,
    catalog: pd.DataFrame,
    outcome_columns: Iterable[str],
    context_columns: Iterable[str],
    *,
    hit_rate_threshold: float = 0.0,
    min_events: int = 1,
    min_context_rows: int = 1,
) -> dict[str, object]:
    """Build deterministic report tables for multi-instrument event review."""
    contexts = _normalize_columns(context_columns, "context_columns")
    outcome_table = build_multi_instrument_event_outcome_table(
        df,
        catalog,
        outcome_columns,
        contexts,
        hit_rate_threshold=hit_rate_threshold,
        min_events=min_events,
        min_context_rows=min_context_rows,
    )
    comparison_table = (
        compare_confirmed_vs_divergent_event_outcomes(outcome_table, context_column=contexts[0])
        if contexts and not outcome_table.empty
        else pd.DataFrame()
    )
    return {
        "metadata": {
            "report_caveat": MULTI_INSTRUMENT_CAVEAT,
            "forward_outcomes_are_evaluation_only": True,
            "context_columns": contexts,
            "outcome_columns": _normalize_columns(outcome_columns, "outcome_columns"),
        },
        "context_coverage": summarize_multi_instrument_context_coverage(
            df,
            contexts,
            min_context_rows=min_context_rows,
        ),
        "event_outcomes": outcome_table,
        "confirmed_vs_divergent": comparison_table,
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
        "context_coverage_rate": (
            float(context_sample_count / total_rows) if total_rows else float("nan")
        ),
        "context_sample_flag": "ok" if context_sample_count >= min_context_rows else "small_context_sample",
        **values,
    }


def _study_columns(contexts: list[str]) -> list[str]:
    return [
        *MULTI_INSTRUMENT_CONTEXT_COLUMNS,
        *contexts,
        *EVENT_FORWARD_OUTCOME_COLUMNS,
        "study_caveat",
    ]

