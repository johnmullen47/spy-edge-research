"""Tests for the regime-conditioned intraday-momentum forward-outcome study (M111)."""

import numpy as np
import pandas as pd
import pytest

from spy_edge_research.backtesting import (
    INTRADAY_MOMENTUM_STUDY_CAVEAT,
    build_intraday_momentum_research_report,
    export_intraday_momentum_research_report_to_csv,
    intraday_momentum_regime_lift,
    summarize_intraday_momentum_outcomes,
)


def _decision_frame():
    # Hand-built decision-bar frame (one row per session decision bar) with known
    # regimes, open-return signs, and forward outcomes (bps).
    return pd.DataFrame(
        {
            "mim_decision_bar": [True] * 6,
            "mim_vol_regime": ["high", "high", "normal", "normal", "high", "normal"],
            "mim_open_return": [0.01, 0.01, 0.01, -0.01, -0.01, -0.01],
            "forward_return_bps_30m": [20.0, 40.0, -5.0, 8.0, -30.0, 2.0],
        }
    )


def test_summarize_long_outcomes_by_regime():
    summary = summarize_intraday_momentum_outcomes(
        _decision_frame(), outcome_col="forward_return_bps_30m", direction="long"
    )
    assert list(summary["regime"]) == ["high", "normal", "all"]
    high = summary.set_index("regime").loc["high"]
    # Long, high-vol rows: outcomes 20 and 40 bps -> mean 30, both positive.
    assert high["n"] == 2
    assert high["mean_forward_return_bps"] == pytest.approx(30.0)
    assert high["mean_directional_return_bps"] == pytest.approx(30.0)
    assert high["hit_rate"] == pytest.approx(1.0)
    # All long rows (open_return > 0): 20, 40, -5 -> mean ~18.33.
    allr = summary.set_index("regime").loc["all"]
    assert allr["n"] == 3
    assert allr["mean_forward_return_bps"] == pytest.approx((20 + 40 - 5) / 3)


def test_summarize_short_flips_directional_sign():
    summary = summarize_intraday_momentum_outcomes(
        _decision_frame(), outcome_col="forward_return_bps_30m", direction="short"
    )
    high = summary.set_index("regime").loc["high"]
    # Short, high-vol rows: open_return < 0 -> outcome -30. Directional = +30
    # (price fell as the short predicted) -> hit.
    assert high["n"] == 1
    assert high["mean_forward_return_bps"] == pytest.approx(-30.0)
    assert high["mean_directional_return_bps"] == pytest.approx(30.0)
    assert high["hit_rate"] == pytest.approx(1.0)


def test_regime_lift_is_high_minus_all():
    summary = summarize_intraday_momentum_outcomes(
        _decision_frame(), outcome_col="forward_return_bps_30m", direction="long"
    )
    lift = intraday_momentum_regime_lift(summary).iloc[0]
    high_mean = summary.set_index("regime").loc["high"]["mean_directional_return_bps"]
    all_mean = summary.set_index("regime").loc["all"]["mean_directional_return_bps"]
    assert lift["high_minus_all_lift_bps"] == pytest.approx(high_mean - all_mean)
    assert lift["lift_caveat"] == INTRADAY_MOMENTUM_STUDY_CAVEAT


def test_empty_direction_yields_nan_rows():
    df = _decision_frame()
    df["mim_open_return"] = -0.01  # no long rows at all
    summary = summarize_intraday_momentum_outcomes(
        df, outcome_col="forward_return_bps_30m", direction="long"
    )
    assert (summary["n"] == 0).all()
    assert summary["mean_forward_return_bps"].isna().all()


def test_build_report_and_export(tmp_path):
    report = build_intraday_momentum_research_report(
        _decision_frame(), label_columns=["forward_return_bps_30m"]
    )
    assert report["metadata"]["report_caveat"] == INTRADAY_MOMENTUM_STUDY_CAVEAT
    outcomes = report["tables"]["regime_outcomes"]
    # 2 directions x 3 regimes for the single label.
    assert len(outcomes) == 6
    assert set(outcomes["direction"]) == {"long", "short"}
    written = export_intraday_momentum_research_report_to_csv(report, tmp_path / "mim")
    assert written["regime_outcomes"].exists()
    assert written["metadata"].exists()


def test_direction_validation():
    with pytest.raises(ValueError, match="direction must be"):
        summarize_intraday_momentum_outcomes(
            _decision_frame(), outcome_col="forward_return_bps_30m", direction="sideways"
        )
