"""Research-only directional exposure aggregation for candidate edge sets.

These helpers describe the aggregate directional exposure implied by a set of
candidate hypotheses. They are descriptive research diagnostics only: they do
not size positions, allocate capital, construct portfolios, or emit orders.
"""

from __future__ import annotations

from collections.abc import Iterable

import pandas as pd


EXPOSURE_CAVEAT = "exposure_is_descriptive_research_not_position_sizing"

_EXPOSURE_SUMMARY_FIELDS: tuple[str, ...] = (
    "candidate_count",
    "long_count",
    "short_count",
    "neutral_count",
    "gross_exposure",
    "net_exposure",
    "net_exposure_abs",
    "exposure_caveat",
)


def add_exposure_columns(
    candidates: pd.DataFrame,
    *,
    direction_column: str = "direction",
    weight_column: str | None = None,
) -> pd.DataFrame:
    """Add ``signed_exposure`` and ``gross_exposure`` columns to a candidate set.

    ``weight`` defaults to 1.0 per candidate. Exposure is descriptive only and
    is not a position size.
    """
    _require_columns(candidates, [direction_column])
    result = candidates.copy()

    signs = result[direction_column].map(_direction_sign)
    if signs.isna().any():
        bad = sorted(result.loc[signs.isna(), direction_column].dropna().astype(str).unique())
        raise ValueError(f"Unsupported direction values: {bad}")

    if weight_column is None:
        weights = pd.Series(1.0, index=result.index)
    else:
        _require_columns(candidates, [weight_column])
        weights = pd.to_numeric(result[weight_column], errors="coerce")
        if weights.isna().any():
            raise ValueError(f"{weight_column} must contain only non-null numeric weights")
        if (weights < 0).any():
            raise ValueError(f"{weight_column} must contain only non-negative weights")

    result["signed_exposure"] = signs.astype(float) * weights.astype(float)
    result["gross_exposure"] = weights.astype(float).abs()
    return result


def summarize_exposure(
    candidates: pd.DataFrame,
    *,
    group_columns: Iterable[str] | None = None,
    direction_column: str = "direction",
    weight_column: str | None = None,
) -> pd.DataFrame:
    """Summarize gross/net directional exposure, optionally grouped."""
    enriched = add_exposure_columns(
        candidates,
        direction_column=direction_column,
        weight_column=weight_column,
    )

    if group_columns:
        groups = list(group_columns)
        _require_columns(enriched, groups)
        rows: list[dict[str, object]] = []
        for keys, group in enriched.groupby(groups, dropna=False, sort=True):
            key_tuple = keys if isinstance(keys, tuple) else (keys,)
            rows.append({**dict(zip(groups, key_tuple)), **_exposure_row(group)})
        return pd.DataFrame(rows, columns=[*groups, *_EXPOSURE_SUMMARY_FIELDS])

    return pd.DataFrame([_exposure_row(enriched)], columns=list(_EXPOSURE_SUMMARY_FIELDS))


def _exposure_row(group: pd.DataFrame) -> dict[str, object]:
    signed = group["signed_exposure"]
    net = float(signed.sum())
    return {
        "candidate_count": int(len(group)),
        "long_count": int((signed > 0).sum()),
        "short_count": int((signed < 0).sum()),
        "neutral_count": int((signed == 0).sum()),
        "gross_exposure": float(group["gross_exposure"].sum()),
        "net_exposure": net,
        "net_exposure_abs": abs(net),
        "exposure_caveat": EXPOSURE_CAVEAT,
    }


def _direction_sign(value: object) -> float | None:
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in ("long", "bullish", "buy"):
            return 1.0
        if lowered in ("short", "bearish", "sell"):
            return -1.0
        if lowered in ("flat", "neutral", "none", ""):
            return 0.0
        return None
    if isinstance(value, bool):
        return 1.0 if value else 0.0
    if value in (1, 1.0):
        return 1.0
    if value in (-1, -1.0):
        return -1.0
    if value in (0, 0.0):
        return 0.0
    if pd.isna(value):
        return None
    return None


def _require_columns(df: pd.DataFrame, columns: Iterable[str]) -> None:
    missing = [column for column in columns if column not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")
