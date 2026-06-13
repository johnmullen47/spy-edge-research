"""Research-only macro-regime event outcome studies."""

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


MACRO_EVENT_STUDY_CAVEAT = "macro_event_study_is_descriptive_research_only"
MACRO_CONTEXT_COLUMNS = [
    "context_key",
    "context_sample_count",
    "context_coverage_rate",
    "context_sample_flag",
]


def summarize_event_by_macro_regime(
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
    """Summarize one event/outcome pair inside macro regime groups."""
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
                "study_caveat": MACRO_EVENT_STUDY_CAVEAT,
            }
        )
    return pd.DataFrame(rows, columns=_study_columns(contexts))


def compare_macro_regime_event_outcomes(
    summary_table: pd.DataFrame,
    *,
    context_column: str = "macro_risk_context",
    context_values: Mapping[str, str] | None = None,
) -> pd.DataFrame:
    """Compare descriptive event outcomes across named macro regimes."""
    labels = dict(
        context_values
        or {
            "risk_on": "risk_on",
            "risk_off": "risk_off",
            "mixed": "risk_mixed",
            "rates_up": "rates_up",
            "rates_down": "rates_down",
            "credit_risk_on": "credit_risk_on",
            "credit_risk_off": "credit_risk_off",
            "commodity_up": "commodity_up",
            "commodity_down": "commodity_down",
            "volatility_proxy_up": "volatility_proxy_up",
            "volatility_proxy_down": "volatility_proxy_down",
        }
    )
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
    base = summary_table[keys].drop_duplicates().copy()
    for label, value in labels.items():
        subset = summary_table.loc[
            summary_table[context_column].eq(value),
            [*keys, "event_count", "event_expectancy", "event_hit_rate"],
        ]
        subset = subset.rename(
            columns={
                "event_count": f"{label}_event_count",
                "event_expectancy": f"{label}_event_expectancy",
                "event_hit_rate": f"{label}_event_hit_rate",
            }
        )
        base = base.merge(subset, on=keys, how="left")
    count_columns = [column for column in base.columns if column.endswith("_event_count")]
    for column in count_columns:
        base[column] = base[column].fillna(0).astype(int)
    base["comparison_caveat"] = "descriptive_macro_regime_comparison_not_edge_claim"
    return base


def build_macro_event_outcome_table(
    df: pd.DataFrame,
    catalog: pd.DataFrame,
    outcome_columns: Iterable[str],
    context_columns: Iterable[str],
    *,
    hit_rate_threshold: float = 0.0,
    min_events: int = 1,
    min_context_rows: int = 1,
) -> pd.DataFrame:
    """Build macro-regime conditioned outcome rows for each catalog event."""
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
                summarize_event_by_macro_regime(
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


def summarize_macro_context_coverage(
    df: pd.DataFrame,
    context_columns: Iterable[str],
    *,
    min_context_rows: int = 1,
) -> pd.DataFrame:
    """Summarize macro context availability and sample sizes."""
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
            "context_key": "__missing_macro_context_rows__",
            "context_sample_count": missing_count,
            "context_coverage_rate": float(missing_count / total_rows) if total_rows else float("nan"),
            "context_sample_flag": "diagnostic",
            **{context: None for context in contexts},
        }
    )
    return pd.DataFrame(rows, columns=[*MACRO_CONTEXT_COLUMNS, *contexts])


def build_macro_event_research_report(
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
    """Build deterministic macro-event report tables for research review."""
    contexts = _normalize_columns(context_columns, "context_columns")
    outcomes = _normalize_columns(outcome_columns, "outcome_columns")
    outcome_table = build_macro_event_outcome_table(
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
        compare_macro_regime_event_outcomes(outcome_table, context_column=comparison_column)
        if not outcome_table.empty and comparison_column in outcome_table.columns
        else pd.DataFrame()
    )
    return {
        "metadata": {
            "report_caveat": MACRO_EVENT_STUDY_CAVEAT,
            "forward_outcomes_are_evaluation_only": True,
            "context_columns": contexts,
            "outcome_columns": outcomes,
            "comparison_context_column": comparison_column,
        },
        "context_coverage": summarize_macro_context_coverage(
            df,
            contexts,
            min_context_rows=min_context_rows,
        ),
        "event_outcomes": outcome_table,
        "macro_regime_comparison": comparison_table,
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
        *MACRO_CONTEXT_COLUMNS,
        *contexts,
        *EVENT_FORWARD_OUTCOME_COLUMNS,
        "study_caveat",
    ]

