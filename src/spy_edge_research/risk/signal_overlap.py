"""Research-only signal-overlap diagnostics across candidate event masks.

These helpers describe how redundant a set of candidate event triggers are
(co-occurrence, Jaccard, correlation) so research can flag candidates that are
not independent. They are descriptive only: the overlap tables are not features,
trading signals, or position sizes.
"""

from __future__ import annotations

from collections.abc import Iterable
from itertools import combinations

import pandas as pd


OVERLAP_CAVEAT = "signal_overlap_is_descriptive_redundancy_research_only"

_OVERLAP_COLUMNS: tuple[str, ...] = (
    "left_signal",
    "right_signal",
    "left_count",
    "right_count",
    "both_count",
    "either_count",
    "jaccard",
    "co_occurrence_rate",
    "correlation",
    "overlap_caveat",
)


def compute_event_mask_overlap(
    df: pd.DataFrame,
    mask_columns: Iterable[str],
) -> pd.DataFrame:
    """Compute pairwise overlap between boolean/0-1 candidate event masks."""
    columns = list(mask_columns)
    if len(columns) < 2:
        raise ValueError("mask_columns must contain at least two columns")
    _require_columns(df, columns)

    masks = {column: df[column].fillna(False).astype(bool) for column in columns}
    rows: list[dict[str, object]] = []
    for left, right in combinations(columns, 2):
        left_mask = masks[left]
        right_mask = masks[right]
        left_count = int(left_mask.sum())
        right_count = int(right_mask.sum())
        both = int((left_mask & right_mask).sum())
        either = int((left_mask | right_mask).sum())
        smaller = min(left_count, right_count)
        rows.append(
            {
                "left_signal": left,
                "right_signal": right,
                "left_count": left_count,
                "right_count": right_count,
                "both_count": both,
                "either_count": either,
                "jaccard": float(both / either) if either else float("nan"),
                "co_occurrence_rate": float(both / smaller) if smaller else float("nan"),
                "correlation": _safe_correlation(left_mask, right_mask),
                "overlap_caveat": OVERLAP_CAVEAT,
            }
        )
    return pd.DataFrame(rows, columns=list(_OVERLAP_COLUMNS))


def summarize_signal_overlap(
    overlap_table: pd.DataFrame,
    *,
    jaccard_threshold: float = 0.5,
) -> pd.DataFrame:
    """Summarize pairwise overlap and count redundant pairs above a threshold."""
    _validate_unit_fraction(jaccard_threshold, "jaccard_threshold")
    _require_columns(overlap_table, ["jaccard"])
    jaccard = pd.to_numeric(overlap_table["jaccard"], errors="coerce").dropna()
    return pd.DataFrame(
        [
            {
                "pair_count": int(len(overlap_table)),
                "max_jaccard": float(jaccard.max()) if not jaccard.empty else float("nan"),
                "mean_jaccard": float(jaccard.mean()) if not jaccard.empty else float("nan"),
                "redundant_pair_count": int((jaccard >= jaccard_threshold).sum()),
                "jaccard_threshold": float(jaccard_threshold),
                "summary_caveat": OVERLAP_CAVEAT,
            }
        ]
    )


def _safe_correlation(left: pd.Series, right: pd.Series) -> float:
    # A constant mask has zero variance; correlation is undefined -> NaN.
    if left.nunique() < 2 or right.nunique() < 2:
        return float("nan")
    return float(left.astype(float).corr(right.astype(float)))


def _require_columns(df: pd.DataFrame, columns: Iterable[str]) -> None:
    missing = [column for column in columns if column not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")


def _validate_unit_fraction(value: float, name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a number between 0 and 1")
    if value < 0 or value > 1:
        raise ValueError(f"{name} must be between 0 and 1")
