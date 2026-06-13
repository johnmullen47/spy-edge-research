"""In-memory multi-symbol dataframe alignment helpers."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import pandas as pd


DEFAULT_ALIGNMENT_KEYS = ["timestamp"]
ALIGNMENT_SUMMARY_COLUMNS = [
    "symbol",
    "row_count",
    "unique_key_count",
    "duplicate_key_count",
    "missing_key_count",
    "panel_row_count",
    "panel_coverage_rate",
]


def validate_symbol_frame_map(
    symbol_frames: Mapping[str, pd.DataFrame],
    *,
    key_columns: Sequence[str] | str = DEFAULT_ALIGNMENT_KEYS,
) -> dict[str, pd.DataFrame]:
    """Validate an in-memory mapping from symbol to dataframe."""
    if not isinstance(symbol_frames, Mapping) or not symbol_frames:
        raise ValueError("symbol_frames must be a non-empty mapping")
    keys = _normalize_columns(key_columns, "key_columns")
    normalized: dict[str, pd.DataFrame] = {}
    for symbol, frame in symbol_frames.items():
        normalized_symbol = _normalize_symbol(symbol)
        if not isinstance(frame, pd.DataFrame):
            raise TypeError(f"frame for {normalized_symbol} must be a pandas DataFrame")
        _require_columns(frame, keys)
        if normalized_symbol in normalized:
            raise ValueError(f"Duplicate symbol after normalization: {normalized_symbol}")
        normalized[normalized_symbol] = frame.copy()
    return dict(sorted(normalized.items()))


def prefix_symbol_columns(
    frame: pd.DataFrame,
    symbol: str,
    *,
    key_columns: Sequence[str] | str = DEFAULT_ALIGNMENT_KEYS,
) -> pd.DataFrame:
    """Prefix non-key columns with a symbol to avoid collisions."""
    keys = _normalize_columns(key_columns, "key_columns")
    _require_columns(frame, keys)
    normalized_symbol = _normalize_symbol(symbol)
    rename_map = {
        column: f"{normalized_symbol}_{column}"
        for column in frame.columns
        if column not in keys and not str(column).startswith(f"{normalized_symbol}_")
    }
    return frame.rename(columns=rename_map).copy()


def align_symbol_frames(
    symbol_frames: Mapping[str, pd.DataFrame],
    *,
    key_columns: Sequence[str] | str = DEFAULT_ALIGNMENT_KEYS,
    how: str = "inner",
    fill_method: str | None = None,
) -> pd.DataFrame:
    """Join symbol dataframes on timestamp/session keys."""
    keys = _normalize_columns(key_columns, "key_columns")
    if how not in {"inner", "outer"}:
        raise ValueError("how must be 'inner' or 'outer'")
    if fill_method not in {None, "ffill"}:
        raise ValueError("fill_method must be None or 'ffill'")
    frames = validate_symbol_frame_map(symbol_frames, key_columns=keys)

    panel: pd.DataFrame | None = None
    for symbol, frame in frames.items():
        prepared = prefix_symbol_columns(frame, symbol, key_columns=keys)
        prepared = prepared.drop_duplicates(subset=keys, keep="first")
        prepared = prepared.sort_values(keys, kind="mergesort")
        panel = prepared if panel is None else panel.merge(prepared, on=keys, how=how, sort=True)

    result = panel if panel is not None else pd.DataFrame(columns=keys)
    result = result.sort_values(keys, kind="mergesort").reset_index(drop=True)
    if fill_method == "ffill":
        non_keys = [column for column in result.columns if column not in keys]
        result[non_keys] = result[non_keys].ffill()
        result.attrs["fill_caveat"] = "forward_fill_was_explicit_and_uses_prior_rows_only"
    return result


def build_multi_symbol_panel(
    symbol_frames: Mapping[str, pd.DataFrame],
    *,
    key_columns: Sequence[str] | str = DEFAULT_ALIGNMENT_KEYS,
    how: str = "inner",
    fill_method: str | None = None,
) -> pd.DataFrame:
    """Build a prefixed multi-symbol panel from in-memory frames."""
    return align_symbol_frames(
        symbol_frames,
        key_columns=key_columns,
        how=how,
        fill_method=fill_method,
    )


def summarize_symbol_alignment(
    symbol_frames: Mapping[str, pd.DataFrame],
    panel: pd.DataFrame | None = None,
    *,
    key_columns: Sequence[str] | str = DEFAULT_ALIGNMENT_KEYS,
) -> pd.DataFrame:
    """Summarize per-symbol timestamp coverage against an aligned panel."""
    keys = _normalize_columns(key_columns, "key_columns")
    frames = validate_symbol_frame_map(symbol_frames, key_columns=keys)
    if panel is None:
        panel = align_symbol_frames(frames, key_columns=keys, how="outer")
    _require_columns(panel, keys)
    panel_keys = panel[keys].drop_duplicates()
    panel_row_count = len(panel_keys)
    rows: list[dict[str, Any]] = []
    for symbol, frame in frames.items():
        missing_key_count = int(frame[keys].isna().any(axis=1).sum())
        unique_key_count = int(frame[keys].dropna().drop_duplicates().shape[0])
        duplicate_key_count = int(len(frame) - frame[keys].drop_duplicates().shape[0])
        coverage = (
            float(unique_key_count / panel_row_count)
            if panel_row_count
            else float("nan")
        )
        rows.append(
            {
                "symbol": symbol,
                "row_count": int(len(frame)),
                "unique_key_count": unique_key_count,
                "duplicate_key_count": duplicate_key_count,
                "missing_key_count": missing_key_count,
                "panel_row_count": int(panel_row_count),
                "panel_coverage_rate": coverage,
            }
        )
    return pd.DataFrame(rows, columns=ALIGNMENT_SUMMARY_COLUMNS)


def filter_aligned_symbol_universe(
    symbol_frames: Mapping[str, pd.DataFrame],
    *,
    key_columns: Sequence[str] | str = DEFAULT_ALIGNMENT_KEYS,
    min_coverage_rate: float = 1.0,
) -> dict[str, pd.DataFrame]:
    """Keep symbols whose timestamp coverage meets a minimum panel coverage."""
    if not isinstance(min_coverage_rate, (int, float)) or not 0 <= min_coverage_rate <= 1:
        raise ValueError("min_coverage_rate must be between 0 and 1")
    frames = validate_symbol_frame_map(symbol_frames, key_columns=key_columns)
    summary = summarize_symbol_alignment(frames, key_columns=key_columns)
    keep = set(summary.loc[summary["panel_coverage_rate"].ge(min_coverage_rate), "symbol"])
    return {symbol: frame.copy() for symbol, frame in frames.items() if symbol in keep}


def _normalize_columns(columns: Sequence[str] | str, name: str) -> list[str]:
    if isinstance(columns, str):
        normalized = [columns]
    else:
        normalized = list(columns)
    if not normalized or not all(isinstance(column, str) and column for column in normalized):
        raise ValueError(f"{name} must contain at least one column name")
    return normalized


def _normalize_symbol(symbol: str) -> str:
    if not isinstance(symbol, str) or not symbol.strip():
        raise ValueError("symbol keys must be non-empty strings")
    return symbol.strip().upper()


def _require_columns(frame: pd.DataFrame, columns: list[str]) -> None:
    missing = [column for column in columns if column not in frame.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")
