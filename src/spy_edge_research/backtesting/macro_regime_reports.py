"""Descriptive macro regime research report bundles.

These helpers treat macro regimes as descriptive research context only. They
do not create allocation recommendations, portfolio construction outputs,
strategy instructions, execution readiness claims, or instrument rankings.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


MACRO_REGIME_REPORT_CAVEAT = "macro_regime_report_is_descriptive_context_research_only"
MACRO_REGIME_TABLE_FILES: dict[str, str] = {
    "macro_regime_snapshot": "macro_regime_snapshot.csv",
    "macro_regime_persistence": "macro_regime_persistence.csv",
    "macro_event_outcomes": "macro_event_outcomes.csv",
    "macro_context_coverage": "macro_context_coverage.csv",
    "macro_regime_caveats": "macro_regime_caveats.csv",
}
FORBIDDEN_MACRO_REGIME_FIELDS: frozenset[str] = frozenset(
    {
        "buy",
        "sell",
        "entry",
        "exit",
        "approved",
        "live",
        "trade_signal",
        "allocation",
        "portfolio",
        "readiness",
        "optimal",
        "best",
        "p_l",
        "pnl",
    }
)


def create_macro_regime_report_metadata(
    *,
    project_name: str = "SPY Directional Edge Research",
    milestone: str = "69",
    package_name: str | None = None,
    notes: str | None = None,
) -> dict[str, Any]:
    """Create metadata for descriptive macro regime report artifacts."""
    metadata: dict[str, Any] = {
        "created_at_utc": _created_at_utc(),
        "project_name": project_name,
        "milestone": milestone,
        "report_caveat": MACRO_REGIME_REPORT_CAVEAT,
        "forward_outcomes_are_evaluation_only": True,
    }
    optional = {"package_name": package_name, "notes": notes}
    for key, value in optional.items():
        if value is not None:
            metadata[key] = _json_safe_value(value)
    _raise_forbidden_fields(metadata, name="macro regime report metadata")
    return metadata


def build_macro_regime_snapshot(
    df: pd.DataFrame,
    *,
    macro_symbols: Sequence[str],
    primary_symbol: str = "SPY",
    return_suffix: str = "return_1",
    timestamp_column: str | None = "timestamp",
) -> pd.DataFrame:
    """Build a latest-row macro proxy and regime snapshot."""
    symbols = _normalize_symbols(macro_symbols, "macro_symbols")
    primary = _normalize_symbol(primary_symbol)
    return_columns = [_symbol_column(symbol, return_suffix) for symbol in symbols]
    _require_columns(df, return_columns)
    if df.empty:
        return pd.DataFrame(columns=_snapshot_columns())
    latest = df.iloc[-1]
    rows = []
    for symbol, return_column in zip(symbols, return_columns):
        relative_column = f"{symbol}_relative_return_vs_{primary}_{return_suffix.removeprefix('return_')}"
        rows.append(
            {
                "snapshot_timestamp": latest.get(timestamp_column) if timestamp_column in df.columns else None,
                "macro_symbol": symbol,
                "macro_return": _json_safe_value(latest.get(return_column)),
                "macro_relative_return_vs_primary": (
                    _json_safe_value(latest.get(relative_column)) if relative_column in df.columns else None
                ),
                "macro_rates_context": _json_safe_value(latest.get("macro_rates_context")),
                "macro_credit_context": _json_safe_value(latest.get("macro_credit_context")),
                "macro_commodity_context": _json_safe_value(latest.get("macro_commodity_context")),
                "macro_volatility_proxy_context": _json_safe_value(latest.get("macro_volatility_proxy_context")),
                "macro_risk_context": _json_safe_value(latest.get("macro_risk_context")),
                "snapshot_caveat": "latest_row_macro_context_not_allocation_guidance",
            }
        )
    return pd.DataFrame(rows, columns=_snapshot_columns())


def summarize_macro_regime_persistence(
    df: pd.DataFrame,
    *,
    context_columns: Sequence[str] = (
        "macro_risk_context",
        "macro_rates_context",
        "macro_credit_context",
        "macro_commodity_context",
        "macro_volatility_proxy_context",
    ),
    min_observations: int = 1,
) -> pd.DataFrame:
    """Summarize how often macro regime context values appear."""
    _validate_positive_int(min_observations, "min_observations")
    contexts = _normalize_columns(context_columns, "context_columns")
    _require_columns(df, contexts)
    total_rows = len(df)
    rows: list[dict[str, Any]] = []
    for column in contexts:
        rows.extend(
            _summarize_persistence_series(
                df[column],
                context_type=column,
                total_rows=total_rows,
                min_observations=min_observations,
            )
        )
    return pd.DataFrame(
        rows,
        columns=[
            "context_type",
            "context_value",
            "observation_count",
            "observation_fraction",
            "longest_consecutive_observations",
            "sample_flag",
            "persistence_caveat",
        ],
    )


def build_macro_regime_report_bundle(
    *,
    macro_context_df: pd.DataFrame,
    macro_symbols: Sequence[str],
    macro_event_report: Mapping[str, Any] | None = None,
    metadata: Mapping[str, Any] | None = None,
    include_caveat_table: bool = True,
) -> dict[str, Any]:
    """Build a descriptive macro regime research report bundle."""
    if metadata is not None and not isinstance(metadata, Mapping):
        raise TypeError("metadata must be a mapping when provided")
    bundle_metadata = _json_safe_mapping(metadata or create_macro_regime_report_metadata())
    if "report_caveat" not in bundle_metadata:
        bundle_metadata["report_caveat"] = MACRO_REGIME_REPORT_CAVEAT
    _raise_forbidden_fields(bundle_metadata, name="macro regime report metadata")

    tables: dict[str, pd.DataFrame] = {
        "macro_regime_snapshot": build_macro_regime_snapshot(
            macro_context_df,
            macro_symbols=macro_symbols,
        ),
        "macro_regime_persistence": summarize_macro_regime_persistence(macro_context_df),
    }
    if macro_event_report is not None:
        if "event_outcomes" in macro_event_report:
            tables["macro_event_outcomes"] = _copy_table(
                macro_event_report["event_outcomes"],
                "macro_event_outcomes",
            )
        if "context_coverage" in macro_event_report:
            tables["macro_context_coverage"] = _copy_table(
                macro_event_report["context_coverage"],
                "macro_context_coverage",
            )
    if include_caveat_table:
        tables["macro_regime_caveats"] = _build_caveat_table(tables)

    return validate_macro_regime_report_bundle({"metadata": bundle_metadata, "tables": tables})


def validate_macro_regime_report_bundle(bundle: Any) -> dict[str, Any]:
    """Validate a macro regime report bundle structure."""
    if not isinstance(bundle, dict):
        raise TypeError("bundle must be a dict")
    if "metadata" not in bundle:
        raise KeyError("bundle is missing metadata")
    if not isinstance(bundle["metadata"], dict):
        raise TypeError("bundle metadata must be a dict")
    if "tables" not in bundle:
        raise KeyError("bundle is missing tables")
    if not isinstance(bundle["tables"], dict):
        raise TypeError("bundle tables must be a dict")
    _raise_forbidden_fields(bundle["metadata"], name="macro regime report metadata")
    for table_name, table in bundle["tables"].items():
        if not isinstance(table_name, str) or not table_name:
            raise ValueError("bundle table names must be non-empty strings")
        _raise_forbidden_fields({"table_name": table_name}, name="macro regime table name")
        if not isinstance(table, pd.DataFrame):
            raise TypeError(f"{table_name} must be a pandas DataFrame")
        _raise_forbidden_fields({column: None for column in table.columns}, name=f"{table_name} columns")
    return bundle


def summarize_macro_regime_report_bundle(bundle: Mapping[str, Any]) -> pd.DataFrame:
    """Return a structural summary of macro regime report bundle tables."""
    validated = validate_macro_regime_report_bundle(dict(bundle))
    rows = [
        {
            "table_name": table_name,
            "row_count": len(table),
            "column_count": len(table.columns),
            "columns": list(table.columns),
        }
        for table_name, table in validated["tables"].items()
    ]
    summary = pd.DataFrame(rows, columns=["table_name", "row_count", "column_count", "columns"])
    if summary.empty:
        return summary
    return summary.sort_values("table_name", kind="mergesort").reset_index(drop=True)


def export_macro_regime_report_bundle_to_csv(
    bundle: Mapping[str, Any],
    output_dir: str | Path,
    *,
    overwrite: bool = False,
) -> dict[str, Path]:
    """Export macro regime report tables to deterministic CSV files."""
    validated = validate_macro_regime_report_bundle(dict(bundle))
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    targets: dict[str, Path] = {
        table_name: output_path / MACRO_REGIME_TABLE_FILES.get(table_name, f"{table_name}.csv")
        for table_name in validated["tables"]
    }
    targets["metadata"] = output_path / "metadata.json"
    _raise_if_exists(targets.values(), overwrite=overwrite)
    written: dict[str, Path] = {}
    for table_name, table in validated["tables"].items():
        target = targets[table_name]
        table.to_csv(target, index=False)
        written[table_name] = target
    metadata_target = targets["metadata"]
    metadata_target.write_text(
        json.dumps(_json_safe_mapping(validated["metadata"]), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    written["metadata"] = metadata_target
    return written


def export_macro_regime_report_bundle_to_json(
    bundle: Mapping[str, Any],
    output_path: str | Path,
    *,
    overwrite: bool = False,
) -> Path:
    """Export a macro regime report bundle to one records-oriented JSON file."""
    validated = validate_macro_regime_report_bundle(dict(bundle))
    target = Path(output_path)
    if target.exists() and not overwrite:
        raise FileExistsError(f"{target} already exists")
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "metadata": _json_safe_mapping(validated["metadata"]),
        "tables": {
            table_name: _dataframe_to_records(table)
            for table_name, table in validated["tables"].items()
        },
    }
    target.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return target


def _snapshot_columns() -> list[str]:
    return [
        "snapshot_timestamp",
        "macro_symbol",
        "macro_return",
        "macro_relative_return_vs_primary",
        "macro_rates_context",
        "macro_credit_context",
        "macro_commodity_context",
        "macro_volatility_proxy_context",
        "macro_risk_context",
        "snapshot_caveat",
    ]


def _summarize_persistence_series(
    values: pd.Series,
    *,
    context_type: str,
    total_rows: int,
    min_observations: int,
) -> list[dict[str, Any]]:
    rows = []
    clean = values.dropna()
    for context_value, count in clean.value_counts(sort=False).items():
        longest_run = _longest_run(values, context_value)
        rows.append(
            {
                "context_type": context_type,
                "context_value": context_value,
                "observation_count": int(count),
                "observation_fraction": float(count / total_rows) if total_rows else float("nan"),
                "longest_consecutive_observations": int(longest_run),
                "sample_flag": "ok" if count >= min_observations else "small_sample",
                "persistence_caveat": "macro_regime_persistence_is_descriptive_context_only",
            }
        )
    return rows


def _longest_run(values: pd.Series, target: Any) -> int:
    longest = 0
    current = 0
    for value in values:
        if value == target:
            current += 1
            longest = max(longest, current)
        else:
            current = 0
    return longest


def _build_caveat_table(tables: Mapping[str, pd.DataFrame]) -> pd.DataFrame:
    rows = [
        {"report_section": "overall", "caveat": MACRO_REGIME_REPORT_CAVEAT},
        {"report_section": "overall", "caveat": "macro_regime_context_is_not_allocation_guidance"},
        {"report_section": "overall", "caveat": "macro_proxies_require_interpretation_review"},
        {"report_section": "overall", "caveat": "forward_outcomes_remain_evaluation_only"},
        {"report_section": "overall", "caveat": "sample_size_and_coverage_require_research_review"},
    ]
    for table_name, table in tables.items():
        for column in table.columns:
            if "caveat" not in column:
                continue
            for caveat in table[column].dropna().unique().tolist():
                rows.append({"report_section": table_name, "caveat": caveat})
    return pd.DataFrame(rows, columns=["report_section", "caveat"]).drop_duplicates().reset_index(drop=True)


def _copy_table(table: Any, table_name: str) -> pd.DataFrame:
    if not isinstance(table, pd.DataFrame):
        raise TypeError(f"{table_name} must be a pandas DataFrame")
    return table.copy(deep=True)


def _raise_if_exists(paths: Any, *, overwrite: bool) -> None:
    if overwrite:
        return
    existing = [path for path in paths if Path(path).exists()]
    if existing:
        raise FileExistsError(f"Refusing to overwrite existing files: {existing}")


def _dataframe_to_records(table: pd.DataFrame) -> list[dict[str, Any]]:
    records = table.replace({pd.NaT: None}).to_dict(orient="records")
    return [{str(key): _json_safe_value(value) for key, value in row.items()} for row in records]


def _json_safe_mapping(values: Mapping[str, Any]) -> dict[str, Any]:
    return {str(key): _json_safe_value(value) for key, value in values.items()}


def _json_safe_value(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, pd.Timestamp):
        return None if pd.isna(value) else value.isoformat()
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, np.generic):
        return _json_safe_value(value.item())
    if isinstance(value, float) and np.isnan(value):
        return None
    if isinstance(value, Mapping):
        return _json_safe_mapping(value)
    if isinstance(value, list):
        return [_json_safe_value(item) for item in value]
    if isinstance(value, tuple):
        return [_json_safe_value(item) for item in value]
    return value


def _created_at_utc() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _symbol_column(symbol: str, suffix: str) -> str:
    return f"{_normalize_symbol(symbol)}_{suffix.strip('_')}"


def _normalize_symbol(symbol: str) -> str:
    if not isinstance(symbol, str) or not symbol.strip():
        raise ValueError("symbols must be non-empty strings")
    return symbol.strip().upper()


def _normalize_symbols(symbols: Sequence[str], name: str) -> list[str]:
    if isinstance(symbols, str):
        symbols = [symbols]
    normalized = [_normalize_symbol(symbol) for symbol in symbols]
    if not normalized:
        raise ValueError(f"{name} must contain at least one symbol")
    return normalized


def _normalize_columns(columns: Sequence[str], name: str) -> list[str]:
    if isinstance(columns, str):
        normalized = [columns]
    else:
        normalized = list(columns)
    if not normalized or not all(isinstance(column, str) and column for column in normalized):
        raise ValueError(f"{name} must contain at least one column name")
    return normalized


def _require_columns(df: pd.DataFrame, columns: list[str]) -> None:
    missing = [column for column in columns if column not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")


def _validate_positive_int(value: int, name: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise ValueError(f"{name} must be an integer greater than or equal to 1")


def _raise_forbidden_fields(values: Mapping[str, Any], *, name: str) -> None:
    forbidden = [
        field
        for field in values
        if any(token in str(field).lower() for token in FORBIDDEN_MACRO_REGIME_FIELDS)
    ]
    if forbidden:
        raise ValueError(f"{name} contains forbidden fields: {forbidden}")
