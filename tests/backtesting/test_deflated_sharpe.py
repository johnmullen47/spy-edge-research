"""Tests for the Deflated Sharpe Ratio / PBO deflation stack (M108)."""

import math

import numpy as np
import pandas as pd
import pytest

from spy_edge_research.backtesting import (
    DEFLATED_SHARPE_CAVEAT,
    deflated_sharpe_ratio,
    expected_maximum_sharpe_ratio,
    portfolio_pbo_from_oos,
    probabilistic_sharpe_ratio,
    probabilistic_sharpe_ratio_from_moments,
    probability_of_backtest_overfitting,
    sharpe_ratio,
    summarize_candidate_deflated_sharpe,
)
from spy_edge_research.backtesting.deflated_sharpe import (
    standard_normal_cdf,
    standard_normal_ppf,
)


# --- normal CDF / PPF -------------------------------------------------------


def test_standard_normal_cdf_known_values():
    assert standard_normal_cdf(0.0) == pytest.approx(0.5)
    assert standard_normal_cdf(1.96) == pytest.approx(0.975, abs=1e-3)
    assert standard_normal_cdf(-1.96) == pytest.approx(0.025, abs=1e-3)


def test_ppf_is_inverse_of_cdf():
    for p in (0.01, 0.1, 0.5, 0.84, 0.975, 0.999):
        assert standard_normal_cdf(standard_normal_ppf(p)) == pytest.approx(p, abs=1e-9)


def test_ppf_rejects_out_of_domain():
    with pytest.raises(ValueError):
        standard_normal_ppf(0.0)
    with pytest.raises(ValueError):
        standard_normal_ppf(1.0)


# --- sharpe / PSR -----------------------------------------------------------


def test_sharpe_ratio_basic():
    rng = np.random.default_rng(0)
    returns = rng.normal(0.001, 0.01, size=500)
    expected = returns.mean() / returns.std(ddof=1)
    assert sharpe_ratio(returns) == pytest.approx(expected)


def test_sharpe_ratio_degenerate_inputs():
    assert math.isnan(sharpe_ratio([0.01]))
    assert math.isnan(sharpe_ratio([0.01, 0.01, 0.01]))  # zero dispersion


def test_psr_increases_with_sample_size():
    # Same Sharpe, more observations -> more confident it beats zero.
    short = probabilistic_sharpe_ratio_from_moments(
        observed_sr=0.1, n_returns=50, skewness=0.0, kurtosis=3.0
    )
    long = probabilistic_sharpe_ratio_from_moments(
        observed_sr=0.1, n_returns=500, skewness=0.0, kurtosis=3.0
    )
    assert 0.5 < short < long < 1.0


def test_psr_at_benchmark_is_half():
    # Observed Sharpe exactly at the benchmark -> coin flip.
    psr = probabilistic_sharpe_ratio_from_moments(
        observed_sr=0.2, n_returns=200, skewness=0.0, kurtosis=3.0, benchmark_sr=0.2
    )
    assert psr == pytest.approx(0.5, abs=1e-9)


def test_psr_penalizes_negative_skew_and_fat_tails():
    base = probabilistic_sharpe_ratio_from_moments(
        observed_sr=0.15, n_returns=250, skewness=0.0, kurtosis=3.0
    )
    skewed = probabilistic_sharpe_ratio_from_moments(
        observed_sr=0.15, n_returns=250, skewness=-1.0, kurtosis=3.0
    )
    fat = probabilistic_sharpe_ratio_from_moments(
        observed_sr=0.15, n_returns=250, skewness=0.0, kurtosis=8.0
    )
    assert skewed < base
    assert fat < base


# --- expected max sharpe ----------------------------------------------------


def test_expected_max_sharpe_grows_with_trials_and_variance():
    one = expected_maximum_sharpe_ratio(sharpe_variance=0.04, n_trials=1)
    assert one == 0.0  # no selection inflation with a single trial
    few = expected_maximum_sharpe_ratio(sharpe_variance=0.04, n_trials=10)
    many = expected_maximum_sharpe_ratio(sharpe_variance=0.04, n_trials=1000)
    assert 0.0 < few < many
    louder = expected_maximum_sharpe_ratio(sharpe_variance=0.25, n_trials=10)
    assert louder > few


def test_expected_max_sharpe_rejects_bad_trials():
    with pytest.raises(ValueError):
        expected_maximum_sharpe_ratio(sharpe_variance=0.1, n_trials=0)
    assert expected_maximum_sharpe_ratio(sharpe_variance=0.0, n_trials=10) == 0.0


# --- deflated sharpe --------------------------------------------------------


def test_deflated_sharpe_below_psr_under_many_trials():
    rng = np.random.default_rng(1)
    returns = rng.normal(0.02, 0.1, size=400)  # genuinely positive Sharpe
    psr = probabilistic_sharpe_ratio(returns, benchmark_sr=0.0)
    # 200 trials with dispersed Sharpes -> high expected-max benchmark.
    trial_sharpes = rng.normal(0.0, 0.3, size=200)
    result = deflated_sharpe_ratio(returns, trial_sharpes)
    assert result["expected_max_sharpe_ratio"] > 0.0
    assert result["n_trials"] == 200
    assert result["deflated_sharpe_ratio"] < psr
    assert result["caveat"] == DEFLATED_SHARPE_CAVEAT


def test_deflated_sharpe_single_trial_equals_psr():
    rng = np.random.default_rng(2)
    returns = rng.normal(0.01, 0.05, size=300)
    result = deflated_sharpe_ratio(returns, [sharpe_ratio(returns)])
    assert result["expected_max_sharpe_ratio"] == 0.0
    assert result["deflated_sharpe_ratio"] == pytest.approx(
        probabilistic_sharpe_ratio(returns, benchmark_sr=0.0)
    )


def test_deflated_sharpe_requires_trials():
    with pytest.raises(ValueError):
        deflated_sharpe_ratio([0.01, 0.02, 0.03], [])


# --- PBO via CSCV -----------------------------------------------------------


def test_pbo_high_for_pure_noise():
    # Pure-noise configs: in-sample winner has no OOS edge -> PBO near 0.5.
    rng = np.random.default_rng(3)
    matrix = rng.normal(0.0, 1.0, size=(240, 12))
    result = probability_of_backtest_overfitting(matrix, n_splits=10)
    assert 0.30 <= result["pbo"] <= 0.70
    assert result["n_strategies"] == 12
    assert result["n_combinations"] == math.comb(10, 5)


def test_pbo_low_for_one_genuinely_dominant_config():
    # One config has a real, persistent positive mean; the rest are noise.
    rng = np.random.default_rng(4)
    matrix = rng.normal(0.0, 1.0, size=(240, 8))
    matrix[:, 0] += 1.5  # dominant in every sub-period
    result = probability_of_backtest_overfitting(matrix, n_splits=10)
    assert result["pbo"] < 0.1


def test_pbo_validates_shape_and_splits():
    with pytest.raises(ValueError):
        probability_of_backtest_overfitting(np.zeros((100, 1)), n_splits=10)
    with pytest.raises(ValueError):
        probability_of_backtest_overfitting(np.zeros((100, 4)), n_splits=5)  # odd
    with pytest.raises(ValueError):
        probability_of_backtest_overfitting(np.zeros((4, 4)), n_splits=10)  # too few rows
    with pytest.raises(ValueError):
        probability_of_backtest_overfitting(np.array([np.nan, 0.0]).reshape(1, 2))


# --- OOS adapters -----------------------------------------------------------


def _oos_results(n_candidates: int, n_splits: int, *, edge_for_first: float, seed: int):
    rng = np.random.default_rng(seed)
    rows = []
    for c in range(n_candidates):
        base = edge_for_first if c == 0 else 0.0
        for s in range(n_splits):
            rows.append(
                {
                    "candidate_id": f"c{c}",
                    "split_number": s,
                    "oos_expectancy_difference": base + rng.normal(0.0, 0.001),
                }
            )
    return pd.DataFrame(rows)


def test_summarize_candidate_deflated_sharpe_shape_and_ranking():
    oos = _oos_results(6, 20, edge_for_first=0.003, seed=5)
    summary = summarize_candidate_deflated_sharpe(oos)
    assert list(summary["candidate_id"]) == [f"c{i}" for i in range(6)]
    assert (summary["n_trials"] == 6).all()
    # The genuinely-positive candidate should carry the highest deflated Sharpe.
    best = summary.set_index("candidate_id")["deflated_sharpe_ratio"]
    assert best["c0"] == best.max()


def test_summarize_candidate_deflated_sharpe_empty():
    out = summarize_candidate_deflated_sharpe(pd.DataFrame())
    assert out.empty
    assert "deflated_sharpe_ratio" in out.columns


def test_full_trial_budget_deflates_harder_than_survivor_count():
    # M112 regression (Build Master blocker): the DSR must deflate against the
    # FULL pre-OOS trial budget, not the OOS-survivor panel. Passing the larger
    # budget must STRICTLY raise the expected-max-Sharpe benchmark and STRICTLY
    # lower every candidate's deflated Sharpe vs the survivor-only fallback.
    oos = _oos_results(6, 20, edge_for_first=0.003, seed=8)  # 6 survivors
    survivor = summarize_candidate_deflated_sharpe(oos)  # fallback, N = 6
    full = summarize_candidate_deflated_sharpe(oos, n_trials_evaluated=42)  # N = 42

    assert (survivor["n_trials"] == 6).all()
    assert (full["n_trials"] == 42).all()
    assert full["expected_max_sharpe_ratio"].iloc[0] > survivor["expected_max_sharpe_ratio"].iloc[0]
    s = survivor.set_index("candidate_id")["deflated_sharpe_ratio"]
    f = full.set_index("candidate_id")["deflated_sharpe_ratio"]
    assert (f < s).all()
    # The fallback path flags N as a lower bound; the full-budget path does not.
    from spy_edge_research.backtesting.deflated_sharpe import (
        DEFLATED_SHARPE_N_LOWER_BOUND_CAVEAT,
    )

    assert (survivor["deflated_sharpe_caveat"] == DEFLATED_SHARPE_N_LOWER_BOUND_CAVEAT).all()
    assert (full["deflated_sharpe_caveat"] == DEFLATED_SHARPE_CAVEAT).all()


def test_n_trials_clamped_to_at_least_panel_size():
    # The invariant n_trials_used >= panel columns must always hold (clamp up).
    oos = _oos_results(6, 20, edge_for_first=0.0, seed=9)
    out = summarize_candidate_deflated_sharpe(oos, n_trials_evaluated=2)  # below 6
    assert (out["n_trials"] == 6).all()


def test_n_trials_evaluated_validation():
    oos = _oos_results(4, 12, edge_for_first=0.0, seed=10)
    with pytest.raises(ValueError, match="n_trials_evaluated"):
        summarize_candidate_deflated_sharpe(oos, n_trials_evaluated=0)


def test_portfolio_pbo_from_oos_roundtrip():
    oos = _oos_results(8, 16, edge_for_first=0.0, seed=6)
    result = portfolio_pbo_from_oos(oos)
    assert 0.0 <= result["pbo"] <= 1.0
    assert result["n_strategies"] == 8


def test_portfolio_pbo_from_oos_too_few_splits():
    oos = _oos_results(4, 1, edge_for_first=0.0, seed=7)
    result = portfolio_pbo_from_oos(oos)
    assert math.isnan(result["pbo"])
    assert result["n_combinations"] == 0
