"""Research-only concentration diagnostics for candidate exposure.

These helpers describe how concentrated a candidate set's gross exposure is
across groups (instrument, family, regime, ...). They are descriptive research
diagnostics only and are not allocation guidance.
"""

from __future__ import annotations

from collections.abc import Iterable

import pandas as pd


CONCENTRATION_CAVEAT = "concentration_is_descriptive_research_only"


def compute_group_concentration(
    candidates_with_exposure: pd.DataFrame,
    *,
    group_column: str,
    exposure_column: str = "gross_exposure",
) -> pd.DataFrame:
    """Aggregate gross exposure by group and compute each group's share."""
    _require_columns(candidates_with_exposure, [group_column, exposure_column])
    frame = candidates_with_exposure.copy()
    frame[exposure_column] = pd.to_numeric(frame[exposure_column], errors="coerce").fillna(0.0)
    total = float(frame[exposure_column].sum())

    grouped = (
        frame.groupby(group_column, dropna=False, sort=True)[exposure_column]
        .sum()
        .reset_index()
        .rename(columns={exposure_column: "group_gross_exposure"})
    )
    grouped["share"] = 0.0 if total == 0 else grouped["group_gross_exposure"] / total
    grouped["concentration_caveat"] = CONCENTRATION_CAVEAT
    return grouped


def summarize_concentration(
    concentration_table: pd.DataFrame,
    *,
    share_column: str = "share",
) -> pd.DataFrame:
    """Summarize concentration via largest share and a Herfindahl index."""
    _require_columns(concentration_table, [share_column])
    shares = pd.to_numeric(concentration_table[share_column], errors="coerce").fillna(0.0)
    hhi = float((shares**2).sum())
    return pd.DataFrame(
        [
            {
                "group_count": int(len(concentration_table)),
                "largest_group_share": float(shares.max()) if len(shares) else 0.0,
                "herfindahl_index": hhi,
                "effective_group_count": float(1.0 / hhi) if hhi > 0 else float("nan"),
                "summary_caveat": "concentration_is_not_edge_evidence",
            }
        ]
    )


def _require_columns(df: pd.DataFrame, columns: Iterable[str]) -> None:
    missing = [column for column in columns if column not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")
