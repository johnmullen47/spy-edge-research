"""Descriptive sector leadership research report bundles.

These helpers treat sector rotation as sector-leadership context research only.
They do not create allocation recommendations, portfolio construction outputs,
strategy instructions, execution readiness claims, or sector buy/sell rankings.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import pandas as pd

from spy_edge_research._internal._common import (
    created_at_utc as _created_at_utc,
    dataframe_to_records as _dataframe_to_records,
    json_safe_mapping as _json_safe_mapping,
    json_safe_value as _json_safe_value,
    raise_if_exists as _raise_if_exists,
    require_columns as _require_columns,
    validate_positive_int as _validate_positive_int,
)


SECTOR_ROTATION_REPORT_CAVEAT = "sector_rotation_report_is_descriptive_leadership_research_only"
SECTOR_ROTATION_TABLE_FILES: dict[str, str] = {
    "sector_rotation_snapshot": "sector_rotation_snapshot.csv",
    "sector_leadership_persistence": "sector_leadership_persistence.csv",
    "sector_event_outcomes": "sector_event_outcomes.csv",
    "sector_context_coverage": "sector_context_coverage.csv",
    "sector_rotation_caveats": "sector_rotation_caveats.csv",
}
FORBIDDEN_SECTOR_ROTATION_FIELDS: frozenset[str] = frozenset(
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


def create_sector_rotation_report_metadata(
    *,
    project_name: str = "SPY Directional Edge Research",
    milestone: str = "65",
    package_name: str | None = None,
    notes: str | None = None,
) -> dict[str, Any]:
    """Create metadata for descriptive sector leadership report artifacts."""
    metadata: dict[str, Any] = {
        "created_at_utc": _created_at_utc(),
        "project_name": project_name,
        "milestone": milestone,
        "report_caveat": SECTOR_ROTATION_REPORT_CAVEAT,
        "forward_outcomes_are_evaluation_only": True,
    }
    optional = {"package_name": package_name, "notes": notes}
    for key, value in optional.items():
        if value is not None:
            metadata[key] = _json_safe_value(value)
    _raise_forbidden_fields(metadata, name="sector rotation report metadata")
    return metadata


def build_sector_rotation_snapshot(
    df: pd.DataFrame,
    *,
    sector_symbols: Sequence[str],
    sector_groups: Mapping[str, str] | None = None,
    primary_symbol: str = "SPY",
    return_suffix: str = "return_1",
    timestamp_column: str | None = "timestamp",
) -> pd.DataFrame:
    """Build a latest-row sector leadership and breadth snapshot."""
    sectors = _normalize_symbols(sector_symbols, "sector_symbols")
    primary = _normalize_symbol(primary_symbol)
    groups = {_normalize_symbol(symbol): str(group) for symbol, group in dict(sector_groups or {}).items()}
    return_columns = [_symbol_column(symbol, return_suffix) for symbol in sectors]
    relative_columns = [f"{symbol}_relative_return_vs_{primary}_{return_suffix.removeprefix('return_')}" for symbol in sectors]
    required = return_columns
    if timestamp_column is not None and timestamp_column in df.columns:
        required = [*required, timestamp_column]
    _require_columns(df, return_columns)
    if df.empty:
        return pd.DataFrame(columns=_snapshot_columns())
    latest = df.iloc[-1]
    rows = []
    for symbol, return_column, relative_column in zip(sectors, return_columns, relative_columns):
        rows.append(
            {
                "snapshot_timestamp": latest.get(timestamp_column) if timestamp_column in df.columns else None,
                "sector_symbol": symbol,
                "sector_group": groups.get(symbol, "unknown"),
                "sector_return": _json_safe_value(latest.get(return_column)),
                "sector_relative_return_vs_primary": (
                    _json_safe_value(latest.get(relative_column)) if relative_column in df.columns else None
                ),
                "is_leadership_context": int(latest.get("sector_leadership_symbol") == symbol),
                "is_laggard_context": int(latest.get("sector_laggard_symbol") == symbol),
                "sector_breadth_fraction_positive": _json_safe_value(latest.get("sector_breadth_fraction_positive")),
                "sector_dispersion_return_std": _json_safe_value(latest.get("sector_dispersion_return_std")),
                "sector_high_dispersion_context": _json_safe_value(latest.get("sector_high_dispersion_context")),
                "primary_sector_context": _json_safe_value(latest.get("primary_sector_context")),
                "snapshot_caveat": "latest_row_sector_context_not_allocation_guidance",
            }
        )
    return pd.DataFrame(rows, columns=_snapshot_columns())


def summarize_sector_leadership_persistence(
    df: pd.DataFrame,
    *,
    leadership_symbol_column: str = "sector_leadership_symbol",
    leadership_group_column: str = "sector_leadership_group",
    min_observations: int = 1,
) -> pd.DataFrame:
    """Summarize how often sector leadership symbols and groups appear."""
    _validate_positive_int(min_observations, "min_observations")
    _require_columns(df, [leadership_symbol_column, leadership_group_column])
    total_rows = len(df)
    rows: list[dict[str, Any]] = []
    rows.extend(
        _summarize_persistence_series(
            df[leadership_symbol_column],
            context_type="sector_symbol",
            total_rows=total_rows,
            min_observations=min_observations,
        )
    )
    rows.extend(
        _summarize_persistence_series(
            df[leadership_group_column],
            context_type="sector_group",
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


def build_sector_rotation_report_bundle(
    *,
    sector_context_df: pd.DataFrame,
    sector_symbols: Sequence[str],
    sector_groups: Mapping[str, str] | None = None,
    sector_event_report: Mapping[str, Any] | None = None,
    metadata: Mapping[str, Any] | None = None,
    include_caveat_table: bool = True,
) -> dict[str, Any]:
    """Build a descriptive sector leadership research report bundle."""
    if metadata is not None and not isinstance(metadata, Mapping):
        raise TypeError("metadata must be a mapping when provided")
    bundle_metadata = _json_safe_mapping(metadata or create_sector_rotation_report_metadata())
    if "report_caveat" not in bundle_metadata:
        bundle_metadata["report_caveat"] = SECTOR_ROTATION_REPORT_CAVEAT
    _raise_forbidden_fields(bundle_metadata, name="sector rotation report metadata")

    tables: dict[str, pd.DataFrame] = {
        "sector_rotation_snapshot": build_sector_rotation_snapshot(
            sector_context_df,
            sector_symbols=sector_symbols,
            sector_groups=sector_groups,
        ),
        "sector_leadership_persistence": summarize_sector_leadership_persistence(sector_context_df),
    }
    if sector_event_report is not None:
        if "event_outcomes" in sector_event_report:
            tables["sector_event_outcomes"] = _copy_table(
                sector_event_report["event_outcomes"],
                "sector_event_outcomes",
            )
        if "context_coverage" in sector_event_report:
            tables["sector_context_coverage"] = _copy_table(
                sector_event_report["context_coverage"],
                "sector_context_coverage",
            )
    if include_caveat_table:
        tables["sector_rotation_caveats"] = _build_caveat_table(tables)

    return validate_sector_rotation_report_bundle({"metadata": bundle_metadata, "tables": tables})


def validate_sector_rotation_report_bundle(bundle: Any) -> dict[str, Any]:
    """Validate a sector rotation report bundle structure."""
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
    _raise_forbidden_fields(bundle["metadata"], name="sector rotation report metadata")
    for table_name, table in bundle["tables"].items():
        if not isinstance(table_name, str) or not table_name:
            raise ValueError("bundle table names must be non-empty strings")
        _raise_forbidden_fields({"table_name": table_name}, name="sector rotation table name")
        if not isinstance(table, pd.DataFrame):
            raise TypeError(f"{table_name} must be a pandas DataFrame")
        _raise_forbidden_fields({column: None for column in table.columns}, name=f"{table_name} columns")
    return bundle


def summarize_sector_rotation_report_bundle(bundle: Mapping[str, Any]) -> pd.DataFrame:
    """Return a structural summary of sector rotation report bundle tables."""
    validated = validate_sector_rotation_report_bundle(dict(bundle))
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


def export_sector_rotation_report_bundle_to_csv(
    bundle: Mapping[str, Any],
    output_dir: str | Path,
    *,
    overwrite: bool = False,
) -> dict[str, Path]:
    """Export sector rotation report tables to deterministic CSV files."""
    validated = validate_sector_rotation_report_bundle(dict(bundle))
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    targets: dict[str, Path] = {
        table_name: output_path / SECTOR_ROTATION_TABLE_FILES.get(table_name, f"{table_name}.csv")
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


def export_sector_rotation_report_bundle_to_json(
    bundle: Mapping[str, Any],
    output_path: str | Path,
    *,
    overwrite: bool = False,
) -> Path:
    """Export a sector rotation report bundle to one records-oriented JSON file."""
    validated = validate_sector_rotation_report_bundle(dict(bundle))
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
        "sector_symbol",
        "sector_group",
        "sector_return",
        "sector_relative_return_vs_primary",
        "is_leadership_context",
        "is_laggard_context",
        "sector_breadth_fraction_positive",
        "sector_dispersion_return_std",
        "sector_high_dispersion_context",
        "primary_sector_context",
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
                "persistence_caveat": "leadership_persistence_is_descriptive_context_only",
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
        {"report_section": "overall", "caveat": SECTOR_ROTATION_REPORT_CAVEAT},
        {"report_section": "overall", "caveat": "sector_leadership_context_is_not_allocation_guidance"},
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


def _raise_forbidden_fields(values: Mapping[str, Any], *, name: str) -> None:
    forbidden = [
        field
        for field in values
        if any(token in str(field).lower() for token in FORBIDDEN_SECTOR_ROTATION_FIELDS)
    ]
    if forbidden:
        raise ValueError(f"{name} contains forbidden fields: {forbidden}")
