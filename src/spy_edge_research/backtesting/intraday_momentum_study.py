"""Regime-conditioned forward-outcome study for the intraday-momentum family (M111).

Relates the causal MIM decision-bar signal (``signal_engine.intraday_momentum_features``)
to forward-return *labels*, conditioned on the realized-volatility regime. It answers
the Path 2 research question — does ``sign(open->window-end return)`` momentum continue
into the rest of the session, and is that continuation concentrated in the high-vol
regime? — while preserving causality by construction: the signal/regime are features
(current/prior rows only) and the outcome is a ``forward_*`` label, never fed back.

Every output is a descriptive research statistic, NOT an edge claim, allocation, or
trade signal. The "regime lift" (high-minus-all directional mean) is the quantity the
regime-conditioning thesis predicts to be positive; it is reported, not asserted.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from spy_edge_research._internal._common import (
    created_at_utc,
    json_safe_mapping,
    raise_if_exists,
    require_columns,
)
from spy_edge_research.signal_engine.intraday_momentum_features import (
    VOL_REGIME_HIGH,
    VOL_REGIME_NORMAL,
)

INTRADAY_MOMENTUM_STUDY_CAVEAT = (
    "intraday_momentum_regime_study_is_descriptive_research_not_edge_claim"
)

OUTCOME_SUMMARY_COLUMNS: tuple[str, ...] = (
    "direction",
    "regime",
    "n",
    "mean_forward_return_bps",
    "mean_directional_return_bps",
    "hit_rate",
)


def summarize_intraday_momentum_outcomes(
    df: pd.DataFrame,
    *,
    outcome_col: str,
    direction: str,
    decision_col: str = "mim_decision_bar",
    regime_col: str = "mim_vol_regime",
    open_return_col: str = "mim_open_return",
) -> pd.DataFrame:
    """Summarize MIM forward outcomes by volatility regime for one direction.

    ``direction`` is ``"long"`` (decision-bar rows with a positive open return) or
    ``"short"`` (negative). ``outcome_col`` is a forward-return *label* in basis
    points (e.g. ``forward_return_bps_30m``). One row per regime bucket — ``high``,
    ``normal``, and ``all`` (every decision row in this direction). The directional
    return flips sign for shorts, so a positive ``mean_directional_return_bps`` is
    continuation in the hypothesized direction; ``hit_rate`` is the fraction with
    positive directional return.
    """
    sign = _direction_sign(direction)
    require_columns(df, [outcome_col, decision_col, regime_col, open_return_col])

    decision = df[decision_col].fillna(False).astype(bool)
    open_return = pd.to_numeric(df[open_return_col], errors="coerce")
    outcome = pd.to_numeric(df[outcome_col], errors="coerce")
    direction_mask = decision & (open_return > 0 if sign > 0 else open_return < 0)

    work = pd.DataFrame(
        {
            "regime": df[regime_col].astype("string"),
            "outcome": outcome,
            "directional": outcome * sign,
        }
    ).loc[direction_mask]
    work = work.dropna(subset=["outcome"])

    rows: list[dict[str, Any]] = []
    for regime in (VOL_REGIME_HIGH, VOL_REGIME_NORMAL, "all"):
        group = work if regime == "all" else work.loc[work["regime"] == regime]
        rows.append(_outcome_row(direction, regime, group))
    return pd.DataFrame(rows, columns=list(OUTCOME_SUMMARY_COLUMNS))


def intraday_momentum_regime_lift(summary: pd.DataFrame) -> pd.DataFrame:
    """High-minus-all directional-mean lift (the regime-conditioning quantity).

    A positive lift is what the regime-conditioned thesis predicts — the edge
    concentrates in the high-vol regime — but it is a descriptive statistic, not a
    validated edge. One row.
    """
    require_columns(summary, ["regime", "mean_directional_return_bps", "n", "direction"])
    high = summary.loc[summary["regime"] == VOL_REGIME_HIGH]
    allr = summary.loc[summary["regime"] == "all"]
    direction = str(summary["direction"].iloc[0]) if not summary.empty else ""
    high_mean = float(high["mean_directional_return_bps"].iloc[0]) if not high.empty else np.nan
    all_mean = float(allr["mean_directional_return_bps"].iloc[0]) if not allr.empty else np.nan
    high_n = int(high["n"].iloc[0]) if not high.empty else 0
    return pd.DataFrame(
        [
            {
                "direction": direction,
                "high_regime_directional_mean_bps": high_mean,
                "all_directional_mean_bps": all_mean,
                "high_minus_all_lift_bps": high_mean - all_mean,
                "high_regime_n": high_n,
                "lift_caveat": INTRADAY_MOMENTUM_STUDY_CAVEAT,
            }
        ]
    )


def build_intraday_momentum_research_report(
    df: pd.DataFrame,
    *,
    label_columns: Sequence[str],
    directions: Sequence[str] = ("long", "short"),
    decision_col: str = "mim_decision_bar",
    regime_col: str = "mim_vol_regime",
    open_return_col: str = "mim_open_return",
    metadata: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a MIM regime-outcome research bundle across labels and directions.

    For each (outcome label, direction) it stacks the regime summary and the lift.
    Descriptive research only; the report is allowed to show no edge.
    """
    if not label_columns:
        raise ValueError("label_columns must be a non-empty sequence")
    summaries: list[pd.DataFrame] = []
    lifts: list[pd.DataFrame] = []
    for outcome_col in label_columns:
        for direction in directions:
            summary = summarize_intraday_momentum_outcomes(
                df,
                outcome_col=outcome_col,
                direction=direction,
                decision_col=decision_col,
                regime_col=regime_col,
                open_return_col=open_return_col,
            )
            lift = intraday_momentum_regime_lift(summary)
            summary = summary.copy()
            summary.insert(0, "outcome_col", outcome_col)
            lift = lift.copy()
            lift.insert(0, "outcome_col", outcome_col)
            summaries.append(summary)
            lifts.append(lift)

    report_metadata = {
        "created_at_utc": created_at_utc(),
        "label_columns": list(label_columns),
        "directions": list(directions),
        "report_caveat": INTRADAY_MOMENTUM_STUDY_CAVEAT,
    }
    report_metadata.update(dict(metadata or {}))
    return {
        "metadata": json_safe_mapping(report_metadata),
        "tables": {
            "regime_outcomes": pd.concat(summaries, ignore_index=True),
            "regime_lift": pd.concat(lifts, ignore_index=True),
        },
    }


def export_intraday_momentum_research_report_to_csv(
    report: Mapping[str, Any],
    output_dir: str | Path,
    *,
    overwrite: bool = False,
) -> dict[str, Path]:
    """Export a MIM report bundle's tables (+ metadata) to deterministic files."""
    tables = report.get("tables")
    if not isinstance(tables, Mapping):
        raise KeyError("report must contain a tables mapping")
    output_path = Path(output_dir)
    targets = {name: output_path / f"{name}.csv" for name in tables}
    targets["metadata"] = output_path / "metadata.json"
    raise_if_exists(targets.values(), overwrite=overwrite)
    output_path.mkdir(parents=True, exist_ok=True)
    written: dict[str, Path] = {}
    for name, table in tables.items():
        if not isinstance(table, pd.DataFrame):
            raise TypeError(f"tables.{name} must be a DataFrame")
        table.to_csv(targets[name], index=False)
        written[name] = targets[name]
    targets["metadata"].write_text(
        json.dumps(dict(report.get("metadata", {})), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    written["metadata"] = targets["metadata"]
    return written


def _outcome_row(direction: str, regime: str, group: pd.DataFrame) -> dict[str, Any]:
    if group.empty:
        return {
            "direction": direction,
            "regime": regime,
            "n": 0,
            "mean_forward_return_bps": np.nan,
            "mean_directional_return_bps": np.nan,
            "hit_rate": np.nan,
        }
    directional = group["directional"]
    return {
        "direction": direction,
        "regime": regime,
        "n": int(len(group)),
        "mean_forward_return_bps": float(group["outcome"].mean()),
        "mean_directional_return_bps": float(directional.mean()),
        "hit_rate": float((directional > 0).mean()),
    }


def _direction_sign(direction: str) -> int:
    if direction == "long":
        return 1
    if direction == "short":
        return -1
    raise ValueError("direction must be 'long' or 'short'")
