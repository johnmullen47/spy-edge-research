"""Tests for the F2 binding economic control + placebos (M116)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from spy_edge_research.backtesting.end_of_day_reversal_placebos import (
    build_end_of_day_reversal_bounce_test,
    build_end_of_day_reversal_placebo_comparison,
    build_end_of_day_reversal_placebo_report,
    evaluate_reversal_net_edge,
    generate_bounce_only_panel,
)


# --------------------------------------------------------------------------- #
# Bounce-only synthetic + net-edge-vs-half-spread (the binding control, §5/§6)
# --------------------------------------------------------------------------- #


def test_pure_bounce_has_positive_gross_but_no_net_edge():
    # No true reversal: the Roll bounce induces a spurious GROSS reversal edge that
    # MUST vanish net of the half-spread. This is the phantom the control must kill.
    panel = generate_bounce_only_panel(5000, half_spread_bps=6.0, seed=1, true_reversal_beta=0.0)
    res = evaluate_reversal_net_edge(panel, half_spread_bps=6.0)
    assert res["gross_mean_bps"] > 0  # mechanical bounce shows a gross "edge"
    assert res["net_distinguishable_from_zero"] is False  # ...but no NET edge


def test_true_reversal_above_spread_is_distinguishable_net():
    # A genuine reversal larger than the (small) spread survives net of costs.
    panel = generate_bounce_only_panel(
        5000, half_spread_bps=1.0, seed=2, true_reversal_beta=0.8, mid_vol_bps=20.0
    )
    res = evaluate_reversal_net_edge(panel, half_spread_bps=1.0)
    assert res["net_mean_bps"] > 0
    assert res["net_distinguishable_from_zero"] is True


def test_bounce_test_admits_real_edge_and_flags_pure_bounce():
    # Real-edge observed panel: observed passes; matched bounce-only synthetic shows
    # no edge (control passes) -> F2 passes both rows.
    real_panel = generate_bounce_only_panel(
        5000, half_spread_bps=1.0, seed=3, true_reversal_beta=0.8, mid_vol_bps=20.0
    )
    table = build_end_of_day_reversal_bounce_test(real_panel, half_spread_bps=1.0, seed=3)
    observed = table.set_index("series").loc["observed"]
    synthetic = table.set_index("series").loc["bounce_only_synthetic"]
    assert bool(observed["passes"]) is True
    assert bool(synthetic["passes"]) is True
    assert bool(synthetic["net_distinguishable_from_zero"]) is False

    # A pure-bounce observed series must FAIL the observed leg (net not distinguishable).
    bounce_panel = generate_bounce_only_panel(5000, half_spread_bps=6.0, seed=4)
    table2 = build_end_of_day_reversal_bounce_test(bounce_panel, half_spread_bps=6.0, seed=4)
    assert bool(table2.set_index("series").loc["observed"]["passes"]) is False


# --------------------------------------------------------------------------- #
# Scrambled-mapping + random-direction placebos
# --------------------------------------------------------------------------- #


def _reversal_df(n: int = 400, *, k: float = 0.7, seed: int = 0) -> pd.DataFrame:
    """A frame with a genuine reversal: outcome = -k * r_pre + small noise."""
    rng = np.random.default_rng(seed)
    r_pre = rng.normal(0.0, 10.0, size=n)
    outcome = -k * r_pre + rng.normal(0.0, 1.0, size=n)
    return pd.DataFrame(
        {
            "eod_decision_bar": True,
            "eod_pre_close_return": r_pre,
            "forward_return_60m": outcome,
        }
    )


def test_real_edge_beats_scrambled_and_random_placebos():
    df = _reversal_df()
    cmp = build_end_of_day_reversal_placebo_comparison(
        df, outcome_col="forward_return_60m", seed=0
    ).set_index("variant")
    real = cmp.loc["real", "mean_directional_return_bps"]
    scrambled = cmp.loc["scrambled_mapping", "mean_directional_return_bps"]
    random = cmp.loc["random_direction", "mean_directional_return_bps"]
    assert real > 0
    assert real > scrambled
    assert real > random
    assert cmp.loc["real", "hit_rate"] > 0.5


def test_placebo_report_bundle_has_both_tables():
    df = _reversal_df()
    report = build_end_of_day_reversal_placebo_report(
        df, label_columns=["forward_return_60m"], half_spread_bps=1.0, seed=0
    )
    assert set(report["tables"]) == {"placebo_comparison", "bounce_test"}
    assert not report["tables"]["placebo_comparison"].empty
    assert "report_caveat" in report["metadata"]


# --------------------------------------------------------------------------- #
# Validation
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "kwargs",
    [{"n_sessions": 0}, {"n_sessions": -5}, {"half_spread_bps": -1.0}],
)
def test_generate_bounce_only_panel_validation(kwargs):
    base = {"n_sessions": 10, "half_spread_bps": 1.0}
    base.update(kwargs)
    with pytest.raises(ValueError):
        generate_bounce_only_panel(base.pop("n_sessions"), **base)


def test_evaluate_net_edge_empty_panel_is_safe():
    empty = pd.DataFrame({"eod_pre_close_return": [], "outcome": []})
    res = evaluate_reversal_net_edge(empty, half_spread_bps=1.0)
    assert res["n"] == 0
    assert res["net_distinguishable_from_zero"] is False
