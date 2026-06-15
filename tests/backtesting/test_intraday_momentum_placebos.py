"""Tests for the Path-2 MIM placebo controls (M113, RESEARCH_C §4.4)."""

import numpy as np
import pandas as pd
import pytest

from spy_edge_research.backtesting import (
    INTRADAY_MOMENTUM_PLACEBO_CAVEAT,
    build_intraday_momentum_placebo_comparison,
    build_intraday_momentum_placebo_report,
    export_intraday_momentum_placebo_report_to_csv,
)


def _edged_frame(n_days: int = 200, seed: int = 0):
    """Decision-bar frame with a REAL edge: in the high-vol regime, momentum
    continues (outcome shares the sign of the open return); elsewhere it is noise.
    """
    rng = np.random.default_rng(seed)
    is_high = rng.random(n_days) < 0.4
    open_return = rng.choice([-1.0, 1.0], size=n_days) * rng.uniform(0.001, 0.01, n_days)
    sign = np.sign(open_return)
    outcome = np.empty(n_days)
    for i in range(n_days):
        if is_high[i]:
            # Strong continuation in the gated regime: +25 bps mean in the signal's
            # direction, modest noise.
            outcome[i] = sign[i] * 25.0 + rng.normal(0, 5.0)
        else:
            outcome[i] = rng.normal(0, 5.0)  # no edge off-regime
    return pd.DataFrame(
        {
            "mim_decision_bar": [True] * n_days,
            "mim_vol_regime": np.where(is_high, "high", "normal"),
            "mim_open_return": open_return,
            "forward_return_bps_30m": outcome,
        }
    )


def test_real_edge_beats_both_placebos():
    df = _edged_frame()
    comp = build_intraday_momentum_placebo_comparison(
        df, outcome_col="forward_return_bps_30m", seed=1
    ).set_index("variant")
    real = comp.loc["real", "mean_directional_return_bps"]
    scrambled = comp.loc["scrambled_gate", "mean_directional_return_bps"]
    random_dir = comp.loc["random_direction", "mean_directional_return_bps"]
    # The genuine gated edge must clearly exceed both falsification controls.
    assert real > scrambled + 5.0
    assert real > random_dir + 5.0
    assert comp.loc["real", "hit_rate"] > comp.loc["random_direction", "hit_rate"]


def test_no_edge_data_does_not_separate_real_from_placebos():
    # Pure noise: the real variant must NOT stand out — the edge "vanishes",
    # which is the control behaving correctly.
    rng = np.random.default_rng(3)
    n = 200
    df = pd.DataFrame(
        {
            "mim_decision_bar": [True] * n,
            "mim_vol_regime": rng.choice(["high", "normal"], size=n),
            "mim_open_return": rng.normal(0, 0.005, n),
            "forward_return_bps_30m": rng.normal(0, 5.0, n),
        }
    )
    comp = build_intraday_momentum_placebo_comparison(
        df, outcome_col="forward_return_bps_30m", seed=2
    ).set_index("variant")
    real = comp.loc["real", "mean_directional_return_bps"]
    scrambled = comp.loc["scrambled_gate", "mean_directional_return_bps"]
    # On noise the real edge is not meaningfully above the scrambled-gate placebo.
    assert abs(real - scrambled) < 5.0


def test_scrambled_gate_preserves_high_day_count():
    df = _edged_frame(n_days=150, seed=5)
    n_high = int((df["mim_vol_regime"] == "high").sum())
    comp = build_intraday_momentum_placebo_comparison(
        df, outcome_col="forward_return_bps_30m", seed=7
    ).set_index("variant")
    # The scrambled gate relabels which days are high but keeps the same count,
    # so its sample size matches the real high-regime sample size.
    assert comp.loc["scrambled_gate", "n"] == comp.loc["real", "n"] == n_high


def test_deterministic_given_seed():
    df = _edged_frame(seed=9)
    a = build_intraday_momentum_placebo_comparison(df, outcome_col="forward_return_bps_30m", seed=4)
    b = build_intraday_momentum_placebo_comparison(df, outcome_col="forward_return_bps_30m", seed=4)
    pd.testing.assert_frame_equal(a, b)


def test_report_build_and_export(tmp_path):
    df = _edged_frame(seed=11)
    report = build_intraday_momentum_placebo_report(
        df, label_columns=["forward_return_bps_30m"], seed=1
    )
    assert report["metadata"]["report_caveat"] == INTRADAY_MOMENTUM_PLACEBO_CAVEAT
    table = report["tables"]["placebo_comparison"]
    assert set(table["variant"]) == {"real", "scrambled_gate", "random_direction"}
    written = export_intraday_momentum_placebo_report_to_csv(report, tmp_path / "placebo")
    assert written["placebo_comparison"].exists()
    assert written["metadata"].exists()


def test_empty_label_columns_rejected():
    df = _edged_frame(seed=12)
    with pytest.raises(ValueError, match="label_columns"):
        build_intraday_momentum_placebo_report(df, label_columns=[])
