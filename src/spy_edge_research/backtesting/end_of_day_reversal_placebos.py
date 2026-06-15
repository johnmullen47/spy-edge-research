"""Binding economic control + placebos for end-of-day reversal (F2 — M116).

``docs/PREREG_F2_end_of_day_reversal.md`` is explicit (§4.1, §5, §6): F2's failure
mode is not lookahead but a **frictional artifact** — end-of-day reversal is the
effect most vulnerable to **bid-ask bounce** (Roll 1984; Bajgrowicz & Scaillet
2012). So for F2 the **cost / bounce test is THE binding control, not just the
Deflated Sharpe**. Two decisive checks live here:

1. **Bounce-only synthetic placebo (mandatory).** Generate per-session pre-/last-
   window returns from a pure bid-ask-bounce model with **no true reversal**: a flat
   (or random-walk) mid price plus a shared transaction-side bounce at the 15:00
   observation point. The shared bounce makes the observed pre-window and last-window
   returns spuriously *negatively* correlated — the classic Roll effect — so the
   ``-sign(r_pre)`` rule shows a positive **gross** mean that is pure mechanics. The
   control requires that, once the half-spread is charged at every fill, the **net**
   edge on this synthetic is **indistinguishable from zero**. If a bounce-only series
   shows a net edge, the live "edge" is mechanical bounce → kill.

2. **Net-edge-vs-half-spread distinguishability (§6 decisive test).** On any panel,
   ``-sign(r_pre)`` is scored, the full half-spread is charged at every fill, and the
   net per-trade series is tested against zero. ``eligible`` requires a positive net
   edge statistically distinguishable from zero *after* the spread; if the gross
   reversal is indistinguishable from the bounce/half-spread it is not a signal.

Plus the two generic placebos (the apparent edge must VANISH under both):

- **Scrambled-mapping placebo.** Permute which session's ``r_pre`` maps to which
  session's outcome; the edge must vanish.
- **Random-direction placebo.** Replace ``-sign(r_pre)`` with a random +/-1; the edge
  must vanish.

Deterministic given a seed. Descriptive falsification controls, never trade signals.
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

EOD_REVERSAL_PLACEBO_CAVEAT = (
    "end_of_day_reversal_placebo_and_bounce_test_are_falsification_controls_not_edge_claims"
)

# A trade pays the half-spread at every fill; the reversal turns over daily into the
# close, so the round trip is charged at both the entry (15:00) and exit (16:00) fill.
_ROUND_TRIP_FILLS = 2

PLACEBO_COMPARISON_COLUMNS: tuple[str, ...] = (
    "variant",
    "n",
    "mean_directional_return_bps",
    "hit_rate",
)

BOUNCE_TEST_COLUMNS: tuple[str, ...] = (
    "series",
    "n",
    "gross_mean_bps",
    "round_trip_cost_bps",
    "net_mean_bps",
    "net_t_stat",
    "net_distinguishable_from_zero",
    "passes",
)


def generate_bounce_only_panel(
    n_sessions: int,
    *,
    half_spread_bps: float,
    seed: int = 0,
    true_reversal_beta: float = 0.0,
    mid_vol_bps: float = 8.0,
) -> pd.DataFrame:
    """Synthetic per-session ``(r_pre, outcome)`` from a Roll bid-ask-bounce model.

    Returns a frame with ``eod_pre_close_return`` and ``outcome`` columns **in basis
    points**. Mid-price log returns are i.i.d. Gaussian (no drift); the last-window
    mid return optionally carries a *genuine* reversal ``-true_reversal_beta * r_pre``.
    Each of the three observation points (window start, 15:00, 16:00) is hit by a
    random transaction side (+/-1) times the half-spread; the **shared 15:00 bounce**
    enters ``r_pre`` with one sign and ``outcome`` with the opposite, inducing the
    spurious negative autocorrelation. With ``true_reversal_beta = 0`` the panel has
    **no real reversal** — only bounce.
    """
    _validate_positive_int(n_sessions, "n_sessions")
    _validate_non_negative_number(half_spread_bps, "half_spread_bps")
    _validate_non_negative_number(mid_vol_bps, "mid_vol_bps")

    rng = np.random.default_rng(seed)
    hs = float(half_spread_bps)

    mid_pre = rng.normal(0.0, mid_vol_bps, size=n_sessions)
    mid_out = -float(true_reversal_beta) * mid_pre + rng.normal(0.0, mid_vol_bps, size=n_sessions)

    # Transaction side at each observation point: window start, 15:00, 16:00.
    side_start = rng.choice([-1.0, 1.0], size=n_sessions)
    side_mid = rng.choice([-1.0, 1.0], size=n_sessions)
    side_end = rng.choice([-1.0, 1.0], size=n_sessions)

    # Observed window returns = mid return + bounce in/out of each observation point.
    r_pre = mid_pre + hs * (side_mid - side_start)
    outcome = mid_out + hs * (side_end - side_mid)
    return pd.DataFrame({"eod_pre_close_return": r_pre, "outcome": outcome})


def evaluate_reversal_net_edge(
    panel: pd.DataFrame,
    *,
    half_spread_bps: float,
    r_pre_col: str = "eod_pre_close_return",
    outcome_col: str = "outcome",
    t_threshold: float = 2.0,
) -> dict[str, Any]:
    """Score ``-sign(r_pre)`` net of the half-spread; test net edge vs zero (§6).

    The full half-spread is charged at every fill (round trip = ``2 * half_spread``).
    Returns gross/net per-trade means (bps), the net t-stat against zero, and whether
    the net edge is positive and statistically distinguishable from zero — the
    decisive ``eligible`` precondition for F2.
    """
    require_columns(panel, [r_pre_col, outcome_col])
    _validate_non_negative_number(half_spread_bps, "half_spread_bps")

    r_pre = pd.to_numeric(panel[r_pre_col], errors="coerce")
    outcome = pd.to_numeric(panel[outcome_col], errors="coerce")
    mask = r_pre.notna() & outcome.notna() & (np.sign(r_pre) != 0)
    sign = -np.sign(r_pre[mask].to_numpy())  # -sign(r_pre): trade against the move
    realized = outcome[mask].to_numpy()
    n = int(mask.sum())

    round_trip_cost = _ROUND_TRIP_FILLS * float(half_spread_bps)
    if n == 0:
        return {
            "n": 0,
            "gross_mean_bps": float("nan"),
            "round_trip_cost_bps": round_trip_cost,
            "net_mean_bps": float("nan"),
            "net_t_stat": float("nan"),
            "net_distinguishable_from_zero": False,
        }

    gross = sign * realized
    net = gross - round_trip_cost
    net_mean = float(net.mean())
    net_std = float(net.std(ddof=1)) if n > 1 else 0.0
    t_stat = float(net_mean / (net_std / np.sqrt(n))) if net_std > 0 else 0.0
    distinguishable = bool(net_mean > 0.0 and abs(t_stat) >= t_threshold)
    return {
        "n": n,
        "gross_mean_bps": float(gross.mean()),
        "round_trip_cost_bps": round_trip_cost,
        "net_mean_bps": net_mean,
        "net_t_stat": t_stat,
        "net_distinguishable_from_zero": distinguishable,
    }


def build_end_of_day_reversal_bounce_test(
    panel: pd.DataFrame,
    *,
    half_spread_bps: float,
    seed: int = 0,
    r_pre_col: str = "eod_pre_close_return",
    outcome_col: str = "outcome",
    t_threshold: float = 2.0,
) -> pd.DataFrame:
    """The binding F2 control: live net edge vs a matched bounce-only synthetic.

    Row ``observed`` scores ``-sign(r_pre)`` on ``panel`` net of the half-spread.
    Row ``bounce_only_synthetic`` scores the same rule on a no-true-reversal Roll
    bounce series of the same size. F2 **passes** only if the observed net edge is
    distinguishable from zero AND the bounce-only synthetic's is NOT — i.e. the live
    edge is not reproduced by pure bounce.
    """
    require_columns(panel, [r_pre_col, outcome_col])
    n_sessions = int(pd.to_numeric(panel[r_pre_col], errors="coerce").notna().sum())

    observed = evaluate_reversal_net_edge(
        panel,
        half_spread_bps=half_spread_bps,
        r_pre_col=r_pre_col,
        outcome_col=outcome_col,
        t_threshold=t_threshold,
    )
    synthetic_panel = generate_bounce_only_panel(
        max(n_sessions, 1), half_spread_bps=half_spread_bps, seed=seed, true_reversal_beta=0.0
    )
    synthetic = evaluate_reversal_net_edge(
        synthetic_panel, half_spread_bps=half_spread_bps, t_threshold=t_threshold
    )

    rows = [
        _bounce_row("observed", observed, passes=observed["net_distinguishable_from_zero"]),
        _bounce_row(
            "bounce_only_synthetic",
            synthetic,
            # The control PASSES when the bounce series shows NO net edge.
            passes=not synthetic["net_distinguishable_from_zero"],
        ),
    ]
    return pd.DataFrame(rows, columns=list(BOUNCE_TEST_COLUMNS))


def build_end_of_day_reversal_placebo_comparison(
    df: pd.DataFrame,
    *,
    outcome_col: str,
    seed: int = 0,
    decision_col: str = "eod_decision_bar",
    pre_return_col: str = "eod_pre_close_return",
) -> pd.DataFrame:
    """Compare the real ``-sign(r_pre)`` edge against scrambled-mapping + random-direction.

    Returns one row per variant — ``real``, ``scrambled_mapping``,
    ``random_direction`` — with the directional mean (bps, sign-adjusted so positive
    = the reversal call was right) and hit rate over the decision bars. The real
    variant should beat both placebos for the edge to be credible. Deterministic
    given ``seed``.
    """
    require_columns(df, [decision_col, pre_return_col, outcome_col])

    decision = df[decision_col].fillna(False).astype(bool)
    panel = pd.DataFrame(
        {
            "r_pre": pd.to_numeric(df[pre_return_col], errors="coerce"),
            "outcome": pd.to_numeric(df[outcome_col], errors="coerce"),
        }
    ).loc[decision]
    panel = panel.dropna(subset=["r_pre", "outcome"])
    panel = panel[np.sign(panel["r_pre"]) != 0].reset_index(drop=True)

    rng = np.random.default_rng(seed)
    n = int(len(panel))
    r_pre = panel["r_pre"].to_numpy()
    outcome = panel["outcome"].to_numpy()

    real_sign = -np.sign(r_pre)  # the F2 rule
    scrambled_outcome = rng.permutation(outcome)  # break the r_pre -> outcome mapping
    random_sign = rng.choice([-1.0, 1.0], size=n) if n else np.array([])

    rows = [
        _variant_row("real", outcome, real_sign),
        _variant_row("scrambled_mapping", scrambled_outcome, real_sign),
        _variant_row("random_direction", outcome, random_sign),
    ]
    return pd.DataFrame(rows, columns=list(PLACEBO_COMPARISON_COLUMNS))


def build_end_of_day_reversal_placebo_report(
    df: pd.DataFrame,
    *,
    label_columns: Sequence[str],
    half_spread_bps: float,
    seed: int = 0,
    metadata: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Bundle the placebo comparison + bounce test across forward labels."""
    if not label_columns:
        raise ValueError("label_columns must be a non-empty sequence")
    placebo_frames: list[pd.DataFrame] = []
    bounce_frames: list[pd.DataFrame] = []
    for outcome_col in label_columns:
        comparison = build_end_of_day_reversal_placebo_comparison(
            df, outcome_col=outcome_col, seed=seed
        )
        comparison.insert(0, "outcome_col", outcome_col)
        placebo_frames.append(comparison)

        panel = pd.DataFrame(
            {
                "eod_pre_close_return": pd.to_numeric(df["eod_pre_close_return"], errors="coerce"),
                "outcome": pd.to_numeric(df[outcome_col], errors="coerce"),
            }
        ).loc[df["eod_decision_bar"].fillna(False).astype(bool)]
        bounce = build_end_of_day_reversal_bounce_test(
            panel, half_spread_bps=half_spread_bps, seed=seed
        )
        bounce.insert(0, "outcome_col", outcome_col)
        bounce_frames.append(bounce)

    report_metadata = {
        "created_at_utc": created_at_utc(),
        "label_columns": list(label_columns),
        "half_spread_bps": float(half_spread_bps),
        "seed": int(seed),
        "report_caveat": EOD_REVERSAL_PLACEBO_CAVEAT,
    }
    report_metadata.update(dict(metadata or {}))
    return {
        "metadata": json_safe_mapping(report_metadata),
        "tables": {
            "placebo_comparison": pd.concat(placebo_frames, ignore_index=True),
            "bounce_test": pd.concat(bounce_frames, ignore_index=True),
        },
    }


def export_end_of_day_reversal_placebo_report_to_csv(
    report: Mapping[str, Any],
    output_dir: str | Path,
    *,
    overwrite: bool = False,
) -> dict[str, Path]:
    """Export a placebo/bounce report bundle's tables (+ metadata) to deterministic files."""
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


def _variant_row(variant: str, outcome: np.ndarray, sign: np.ndarray) -> dict[str, Any]:
    finite = np.isfinite(outcome) & (sign != 0) if len(sign) else np.array([], dtype=bool)
    if not finite.any():
        return {
            "variant": variant,
            "n": 0,
            "mean_directional_return_bps": np.nan,
            "hit_rate": np.nan,
        }
    directional = outcome[finite] * sign[finite]
    return {
        "variant": variant,
        "n": int(finite.sum()),
        "mean_directional_return_bps": float(directional.mean()),
        "hit_rate": float((directional > 0).mean()),
    }


def _bounce_row(series: str, result: Mapping[str, Any], *, passes: bool) -> dict[str, Any]:
    return {
        "series": series,
        "n": int(result["n"]),
        "gross_mean_bps": result["gross_mean_bps"],
        "round_trip_cost_bps": result["round_trip_cost_bps"],
        "net_mean_bps": result["net_mean_bps"],
        "net_t_stat": result["net_t_stat"],
        "net_distinguishable_from_zero": bool(result["net_distinguishable_from_zero"]),
        "passes": bool(passes),
    }


def _validate_positive_int(value: int, name: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise ValueError(f"{name} must be an integer greater than or equal to 1")


def _validate_non_negative_number(value: float, name: str) -> None:
    if not isinstance(value, (int, float)) or isinstance(value, bool) or value < 0:
        raise ValueError(f"{name} must be a number greater than or equal to 0")
