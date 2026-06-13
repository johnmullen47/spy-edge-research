"""Read-only query helpers over loaded research report bundles.

These functions answer structural research questions about already-loaded report
bundles. They are read-only and offline; they do not mutate artifacts, fetch
live data, or emit trade instructions.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import pandas as pd

from spy_edge_research.services.artifact_access import LoadedReportBundle


def list_bundle_tables(bundle: LoadedReportBundle) -> pd.DataFrame:
    """List the tables in a loaded bundle with row/column counts."""
    rows = [
        {"table_name": name, "row_count": len(table), "column_count": len(table.columns)}
        for name, table in bundle.tables.items()
    ]
    out = pd.DataFrame(rows, columns=["table_name", "row_count", "column_count"])
    if out.empty:
        return out
    return out.sort_values("table_name", kind="mergesort").reset_index(drop=True)


def get_bundle_table(bundle: LoadedReportBundle, table_name: str) -> pd.DataFrame:
    """Return a copy of one table from a loaded bundle."""
    if table_name not in bundle.tables:
        raise KeyError(f"table not found: {table_name}")
    return bundle.tables[table_name].copy()


def filter_bundle_table(
    bundle: LoadedReportBundle,
    table_name: str,
    column: str,
    value: Any,
) -> pd.DataFrame:
    """Return rows of a bundle table where ``column`` equals ``value``."""
    table = get_bundle_table(bundle, table_name)
    if column not in table.columns:
        raise KeyError(f"column not found in {table_name}: {column}")
    return table.loc[table[column] == value].reset_index(drop=True)


def summarize_bundles(bundles: Sequence[LoadedReportBundle]) -> pd.DataFrame:
    """Summarize one row per loaded bundle (table count, total rows, metadata)."""
    rows = [
        {
            "source_path": bundle.source_path,
            "table_count": len(bundle.tables),
            "total_rows": int(sum(len(table) for table in bundle.tables.values())),
            "milestone": bundle.metadata.get("milestone"),
            "report_caveat": bundle.metadata.get("report_caveat"),
        }
        for bundle in bundles
    ]
    return pd.DataFrame(
        rows,
        columns=["source_path", "table_count", "total_rows", "milestone", "report_caveat"],
    )
