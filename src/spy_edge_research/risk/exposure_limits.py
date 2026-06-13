"""Research-only exposure-limit checks.

These helpers compare descriptive exposure/concentration/overlap summaries
against configured limits and emit advisory flags. They never size positions,
generate orders, or imply trade instructions; a flag is a research signal to a
human reviewer, not an action.
"""

from __future__ import annotations

import math
from collections.abc import Iterable
from dataclasses import dataclass

import pandas as pd


LIMIT_CHECK_CAVEAT = "exposure_limit_check_is_advisory_not_an_order"

_LIMIT_CHECK_COLUMNS: tuple[str, ...] = (
    "check",
    "observed",
    "limit",
    "status",
    "flag",
    "check_caveat",
)


@dataclass(frozen=True)
class ExposureLimits:
    """Configured research limits. ``None`` means a check is not evaluated."""

    max_gross_exposure: float | None = None
    max_net_exposure_abs: float | None = None
    max_group_share: float | None = None
    max_pairwise_jaccard: float | None = None


def evaluate_exposure_limits(
    *,
    limits: ExposureLimits,
    exposure_summary: pd.DataFrame | None = None,
    concentration_summary: pd.DataFrame | None = None,
    overlap_summary: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Evaluate configured limits, returning one advisory row per check."""
    if not isinstance(limits, ExposureLimits):
        raise TypeError("limits must be an ExposureLimits instance")

    rows: list[dict[str, object]] = []

    if exposure_summary is not None:
        _require_columns(exposure_summary, ["gross_exposure", "net_exposure_abs"])
        rows.append(
            _check("gross_exposure", _first(exposure_summary, "gross_exposure"),
                   limits.max_gross_exposure, "gross_exposure_exceeds_limit")
        )
        rows.append(
            _check("net_exposure_abs", _first(exposure_summary, "net_exposure_abs"),
                   limits.max_net_exposure_abs, "net_exposure_exceeds_limit")
        )
    if concentration_summary is not None:
        _require_columns(concentration_summary, ["largest_group_share"])
        rows.append(
            _check("largest_group_share", _first(concentration_summary, "largest_group_share"),
                   limits.max_group_share, "concentration_exceeds_limit")
        )
    if overlap_summary is not None:
        _require_columns(overlap_summary, ["max_jaccard"])
        rows.append(
            _check("max_pairwise_jaccard", _first(overlap_summary, "max_jaccard"),
                   limits.max_pairwise_jaccard, "risk_overlap_too_high")
        )

    return pd.DataFrame(rows, columns=list(_LIMIT_CHECK_COLUMNS))


def _check(name: str, observed: float | None, limit: float | None, flag: str) -> dict[str, object]:
    if limit is None or observed is None or (isinstance(observed, float) and math.isnan(observed)):
        status = "not_evaluated"
    elif observed > limit:
        status = "exceeds_limit"
    else:
        status = "ok"
    return {
        "check": name,
        "observed": observed,
        "limit": limit,
        "status": status,
        "flag": flag if status == "exceeds_limit" else None,
        "check_caveat": LIMIT_CHECK_CAVEAT,
    }


def _first(summary: pd.DataFrame, column: str) -> float | None:
    if summary.empty:
        return None
    value = summary.iloc[0][column]
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    return float(value)


def _require_columns(df: pd.DataFrame, columns: Iterable[str]) -> None:
    missing = [column for column in columns if column not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")
