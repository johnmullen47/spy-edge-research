"""Research-only conditional event outcome study helpers.

These helpers evaluate already-created causal events inside existing causal
context buckets. They read forward outcomes only as evaluation targets and do
not create signals, optimize parameters, test significance, or claim edge.
"""

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


CONDITIONAL_EVENT_EDGE_PREFIX_COLUMNS: list[str] = [
    "context_key",
    "context_sample_count",
]


def group_event_outcomes_by_context(
    df: pd.DataFrame,
    event_column: str,
    outcome_column: str,
    context_columns: Iterable[str],
    *,
    event_family: str = "unknown",
    event_direction: str = "unknown",
    hit_rate_threshold: float = 0.0,
    min_events: int = 1,
) -> pd.DataFrame:
    """Evaluate one event/outcome pair separately within context buckets."""
    contexts = _normalize_columns(context_columns, "context_columns")
    _require_columns(df, [event_column, outcome_column, *contexts])

    rows: list[dict[str, object]] = []
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
                **_context_record(contexts, context_values, len(context_df)),
                **summary.to_dict(),
            }
        )
    return pd.DataFrame(rows, columns=_conditional_columns(contexts))


def summarize_conditional_event_edge(
    df: pd.DataFrame,
    catalog: pd.DataFrame,
    outcome_columns: Iterable[str],
    context_columns: Iterable[str],
    *,
    hit_rate_threshold: float = 0.0,
    min_events: int = 1,
) -> pd.DataFrame:
    """Summarize catalog events against outcomes within context buckets."""
    validated = validate_event_catalog(catalog)
    outcomes = _normalize_columns(outcome_columns, "outcome_columns")
    contexts = _normalize_columns(context_columns, "context_columns")
    _require_columns(df, [*outcomes, *contexts])
    if validated.empty:
        return pd.DataFrame(columns=_conditional_columns(contexts))

    tables = []
    for event in validated.itertuples(index=False):
        _require_columns(df, [event.event_column])
        for outcome_column in outcomes:
            tables.append(
                group_event_outcomes_by_context(
                    df,
                    event.event_column,
                    outcome_column,
                    contexts,
                    event_family=event.event_family,
                    event_direction=event.event_direction,
                    hit_rate_threshold=hit_rate_threshold,
                    min_events=min_events,
                )
            )
    if not tables:
        return pd.DataFrame(columns=_conditional_columns(contexts))
    return pd.concat(tables, ignore_index=True)


def filter_event_contexts_by_sample_size(
    conditional_table: pd.DataFrame,
    *,
    min_events: int,
    min_baseline_count: int = 1,
) -> pd.DataFrame:
    """Keep conditional rows with enough event and baseline observations."""
    _validate_positive_int(min_events, "min_events")
    _validate_positive_int(min_baseline_count, "min_baseline_count")
    _require_columns(conditional_table, ["event_count", "baseline_count"])
    mask = (
        conditional_table["event_count"].ge(min_events)
        & conditional_table["baseline_count"].ge(min_baseline_count)
    )
    return conditional_table.loc[mask].copy().reset_index(drop=True)


def rank_conditional_event_edges(
    conditional_table: pd.DataFrame,
    *,
    sort_by: str = "expectancy_difference",
    ascending: bool = False,
    min_events: int | None = None,
    min_baseline_count: int = 1,
) -> pd.DataFrame:
    """Sort conditional event rows for research review without claiming edge."""
    _require_columns(conditional_table, [sort_by])
    ranked = conditional_table.copy()
    if min_events is not None:
        ranked = filter_event_contexts_by_sample_size(
            ranked,
            min_events=min_events,
            min_baseline_count=min_baseline_count,
        )
    ranked = ranked.sort_values(
        by=sort_by,
        ascending=ascending,
        na_position="last",
        kind="mergesort",
    ).reset_index(drop=True)
    ranked.insert(0, "research_rank", range(1, len(ranked) + 1))
    return ranked


def _iter_context_groups(
    df: pd.DataFrame,
    contexts: list[str],
):
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
) -> dict[str, object]:
    values = dict(zip(contexts, context_values))
    context_key = "|".join(f"{column}={values[column]}" for column in contexts)
    return {
        "context_key": context_key,
        "context_sample_count": context_sample_count,
        **values,
    }


def _conditional_columns(contexts: list[str]) -> list[str]:
    return [
        *CONDITIONAL_EVENT_EDGE_PREFIX_COLUMNS,
        *contexts,
        *EVENT_FORWARD_OUTCOME_COLUMNS,
    ]

