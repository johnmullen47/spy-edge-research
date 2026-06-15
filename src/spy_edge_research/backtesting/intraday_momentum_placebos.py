"""Placebo controls for the regime-conditioned intraday-momentum family (M113).

RESEARCH_C §4.4 requires two negative controls before any MIM result is trusted —
both must make the apparent edge VANISH:

- **Scrambled-gate placebo.** Keep the real directional signal (``sign(r_open)``)
  but randomly permute which decision bars are labelled high-vol. If a randomly
  placed gate produces the same high-regime edge, the volatility gate is noise.
- **Random-direction placebo.** Keep the real high-vol gate but replace the
  direction with a random ±1 per decision bar. If a random direction in the
  high-vol regime produces the same edge, the momentum signal is noise.

The macro / pre-FOMC sub-gate is deliberately **excluded** — the Lucca-Moench
pre-FOMC drift vanished post-2015 (verified in RESEARCH_C §2.0), so it is a dead
control and is not implemented here.

These are deliberate randomizations used only to falsify; they are descriptive
research diagnostics, never trade signals. A small honest fixture will show the
real variant beating both placebos; on real SPY data the expectation (per the
~15–25% survival estimate) is that the edge does NOT clearly beat the placebos —
which is a successful, edge-killing result under the project's philosophy.
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
from spy_edge_research.signal_engine.intraday_momentum_features import VOL_REGIME_HIGH

INTRADAY_MOMENTUM_PLACEBO_CAVEAT = (
    "intraday_momentum_placebo_is_a_falsification_control_not_an_edge_claim"
)

PLACEBO_COMPARISON_COLUMNS: tuple[str, ...] = (
    "variant",
    "n",
    "mean_directional_return_bps",
    "hit_rate",
)


def build_intraday_momentum_placebo_comparison(
    df: pd.DataFrame,
    *,
    outcome_col: str,
    seed: int = 0,
    decision_col: str = "mim_decision_bar",
    regime_col: str = "mim_vol_regime",
    open_return_col: str = "mim_open_return",
) -> pd.DataFrame:
    """Compare the real high-vol-gated MIM edge against its two placebos.

    Returns one row per variant — ``real``, ``scrambled_gate``,
    ``random_direction`` — with the high-regime directional mean (bps) and hit
    rate. ``mean_directional_return_bps`` is sign-adjusted so positive = the
    direction was right; the real variant should beat both placebos for the edge
    to be credible. Deterministic given ``seed``.
    """
    require_columns(df, [decision_col, regime_col, open_return_col, outcome_col])

    decision = df[decision_col].fillna(False).astype(bool)
    panel = pd.DataFrame(
        {
            "is_high": (df[regime_col].astype("string") == VOL_REGIME_HIGH),
            "open_return": pd.to_numeric(df[open_return_col], errors="coerce"),
            "outcome": pd.to_numeric(df[outcome_col], errors="coerce"),
        }
    ).loc[decision]
    panel = panel.dropna(subset=["open_return", "outcome"]).reset_index(drop=True)

    rng = np.random.default_rng(seed)
    n_decisions = int(len(panel))

    real_sign = np.sign(panel["open_return"].to_numpy())
    real_gate = panel["is_high"].to_numpy(dtype=bool)

    # Scrambled gate: same number of high-vol days, randomly relocated.
    scrambled_gate = rng.permutation(real_gate)
    # Random direction: independent ±1 per decision bar (never 0).
    random_sign = rng.choice([-1.0, 1.0], size=n_decisions)

    outcome = panel["outcome"].to_numpy()
    rows = [
        _variant_row("real", outcome, real_sign, real_gate),
        _variant_row("scrambled_gate", outcome, real_sign, scrambled_gate),
        _variant_row("random_direction", outcome, random_sign, real_gate),
    ]
    return pd.DataFrame(rows, columns=list(PLACEBO_COMPARISON_COLUMNS))


def build_intraday_momentum_placebo_report(
    df: pd.DataFrame,
    *,
    label_columns: Sequence[str],
    seed: int = 0,
    metadata: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a placebo-comparison research bundle across forward labels."""
    if not label_columns:
        raise ValueError("label_columns must be a non-empty sequence")
    frames: list[pd.DataFrame] = []
    for outcome_col in label_columns:
        comparison = build_intraday_momentum_placebo_comparison(
            df, outcome_col=outcome_col, seed=seed
        )
        comparison = comparison.copy()
        comparison.insert(0, "outcome_col", outcome_col)
        frames.append(comparison)

    report_metadata = {
        "created_at_utc": created_at_utc(),
        "label_columns": list(label_columns),
        "seed": int(seed),
        "report_caveat": INTRADAY_MOMENTUM_PLACEBO_CAVEAT,
    }
    report_metadata.update(dict(metadata or {}))
    return {
        "metadata": json_safe_mapping(report_metadata),
        "tables": {"placebo_comparison": pd.concat(frames, ignore_index=True)},
    }


def export_intraday_momentum_placebo_report_to_csv(
    report: Mapping[str, Any],
    output_dir: str | Path,
    *,
    overwrite: bool = False,
) -> dict[str, Path]:
    """Export a placebo report bundle's tables (+ metadata) to deterministic files."""
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


def _variant_row(
    variant: str,
    outcome: np.ndarray,
    sign: np.ndarray,
    gate: np.ndarray,
) -> dict[str, Any]:
    selected = gate & np.isfinite(outcome) & (sign != 0)
    if not selected.any():
        return {
            "variant": variant,
            "n": 0,
            "mean_directional_return_bps": np.nan,
            "hit_rate": np.nan,
        }
    directional = outcome[selected] * sign[selected]
    return {
        "variant": variant,
        "n": int(selected.sum()),
        "mean_directional_return_bps": float(directional.mean()),
        "hit_rate": float((directional > 0).mean()),
    }
