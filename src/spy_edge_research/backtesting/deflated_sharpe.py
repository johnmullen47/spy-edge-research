"""Deflated Sharpe Ratio and Probability of Backtest Overfitting (Build 4 / M108).

Implements the modern anti-overfitting stack prescribed by López de Prado for
short-sample strategy research:

- **Probabilistic Sharpe Ratio (PSR)** — Bailey & López de Prado (2012): the
  probability that an observed Sharpe ratio exceeds a benchmark, correcting for
  sample length, skewness, and (excess) kurtosis of the return stream.
- **Expected maximum Sharpe ratio under N trials** — the inflation a researcher
  should *expect* purely from selecting the best of N independent backtests.
- **Deflated Sharpe Ratio (DSR)** — Bailey & López de Prado (2014): the PSR with
  the benchmark set to that expected maximum, so a Sharpe that is merely the
  luckiest of many trials deflates toward 0.5 (a coin flip) and below.
- **Probability of Backtest Overfitting (PBO)** via Combinatorially Symmetric
  Cross-Validation (CSCV) — Bailey, Borwein, López de Prado & Zhu (2017): the
  fraction of CSCV splits in which the in-sample-best configuration lands below
  the out-of-sample median. PBO >= 0.5 means selection is no better than chance.

This module is **research-only measurement**. Nothing here authorizes a trade,
sizes a position, or implies a live/paper order. The functions are pure: given
the same inputs they return the same outputs, with no I/O and no global state.

No SciPy dependency: the standard-normal CDF uses :func:`math.erf` and the
inverse-CDF uses Acklam's rational approximation (accurate to ~1e-9), keeping the
package free of heavy numerical dependencies (numpy/pandas only).
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Sequence
from itertools import combinations
from typing import Any

import numpy as np
import pandas as pd

# Euler-Mascheroni constant, used in the expected-maximum-Sharpe approximation.
_EULER_MASCHERONI = 0.5772156649015329

DEFLATED_SHARPE_CAVEAT = (
    "deflated_sharpe_and_pbo_are_research_diagnostics_not_trade_authorization"
)

# Acklam's inverse-normal-CDF coefficients.
_A = (
    -3.969683028665376e01,
    2.209460984245205e02,
    -2.759285104469687e02,
    1.383577518672690e02,
    -3.066479806614716e01,
    2.506628277459239e00,
)
_B = (
    -5.447609879822406e01,
    1.615858368580409e02,
    -1.556989798598866e02,
    6.680131188771972e01,
    -1.328068155288572e01,
)
_C = (
    -7.784894002430293e-03,
    -3.223964580411365e-01,
    -2.400758277161838e00,
    -2.549732539343734e00,
    4.374664141464968e00,
    2.938163982698783e00,
)
_D = (
    7.784695709041462e-03,
    3.224671290700398e-01,
    2.445134137142996e00,
    3.754408661907416e00,
)


def standard_normal_cdf(x: float) -> float:
    """Standard-normal cumulative distribution function ``Phi(x)``."""
    return 0.5 * (1.0 + math.erf(float(x) / math.sqrt(2.0)))


def standard_normal_ppf(p: float) -> float:
    """Inverse standard-normal CDF (quantile) via Acklam's approximation.

    Defined on the open interval ``(0, 1)``. Raises for values outside it.
    """
    p = float(p)
    if not 0.0 < p < 1.0:
        raise ValueError("p must be in the open interval (0, 1)")
    p_low = 0.02425
    p_high = 1.0 - p_low
    if p < p_low:
        q = math.sqrt(-2.0 * math.log(p))
        x = (((((_C[0] * q + _C[1]) * q + _C[2]) * q + _C[3]) * q + _C[4]) * q + _C[5]) / (
            (((_D[0] * q + _D[1]) * q + _D[2]) * q + _D[3]) * q + 1.0
        )
    elif p <= p_high:
        q = p - 0.5
        r = q * q
        x = (((((_A[0] * r + _A[1]) * r + _A[2]) * r + _A[3]) * r + _A[4]) * r + _A[5]) * q / (
            ((((_B[0] * r + _B[1]) * r + _B[2]) * r + _B[3]) * r + _B[4]) * r + 1.0
        )
    else:
        q = math.sqrt(-2.0 * math.log(1.0 - p))
        x = -(((((_C[0] * q + _C[1]) * q + _C[2]) * q + _C[3]) * q + _C[4]) * q + _C[5]) / (
            (((_D[0] * q + _D[1]) * q + _D[2]) * q + _D[3]) * q + 1.0
        )
    # One Halley refinement step for full double precision.
    e = standard_normal_cdf(x) - p
    u = e * math.sqrt(2.0 * math.pi) * math.exp(x * x / 2.0)
    return x - u / (1.0 + x * u / 2.0)


def sharpe_ratio(returns: Iterable[float], *, ddof: int = 1) -> float:
    """Non-annualized Sharpe ratio (mean / standard deviation) of a return stream.

    Returns ``nan`` for fewer than two finite observations or zero dispersion.
    """
    sample = _clean(returns)
    if sample.size < 2:
        return float("nan")
    std = float(sample.std(ddof=ddof))
    if not np.isfinite(std) or std == 0.0:
        return float("nan")
    return float(sample.mean()) / std


def probabilistic_sharpe_ratio(
    returns: Iterable[float],
    *,
    benchmark_sr: float = 0.0,
) -> float:
    """Probabilistic Sharpe Ratio: ``P(true SR > benchmark_sr)``.

    Corrects the observed Sharpe for sample length and the non-normality
    (skewness, kurtosis) of ``returns``. Returns ``nan`` when the inputs are too
    small or degenerate to estimate.
    """
    sample = _clean(returns)
    if sample.size < 2:
        return float("nan")
    observed = sharpe_ratio(sample)
    if not np.isfinite(observed):
        return float("nan")
    skew, kurt = _skew_kurtosis(sample)
    return probabilistic_sharpe_ratio_from_moments(
        observed_sr=observed,
        n_returns=int(sample.size),
        skewness=skew,
        kurtosis=kurt,
        benchmark_sr=benchmark_sr,
    )


def probabilistic_sharpe_ratio_from_moments(
    *,
    observed_sr: float,
    n_returns: int,
    skewness: float,
    kurtosis: float,
    benchmark_sr: float = 0.0,
) -> float:
    """PSR from precomputed return moments.

    ``kurtosis`` is the Pearson (non-excess) kurtosis: 3.0 for a normal
    distribution. ``n_returns`` is the number of return observations.
    """
    if n_returns < 2:
        return float("nan")
    denominator = 1.0 - skewness * observed_sr + (kurtosis - 1.0) / 4.0 * observed_sr**2
    if not np.isfinite(denominator) or denominator <= 0.0:
        return float("nan")
    z = (observed_sr - benchmark_sr) * math.sqrt(n_returns - 1) / math.sqrt(denominator)
    return standard_normal_cdf(z)


def expected_maximum_sharpe_ratio(*, sharpe_variance: float, n_trials: int) -> float:
    """Expected maximum Sharpe across ``n_trials`` independent trials under the null.

    This is the Sharpe a researcher should expect to observe *purely by
    selecting the best of N trials*, given the cross-trial variance of the
    Sharpe estimates. With one trial (or non-positive variance) there is no
    selection inflation and the expected maximum is 0.0.
    """
    if n_trials < 1:
        raise ValueError("n_trials must be >= 1")
    if n_trials == 1 or not np.isfinite(sharpe_variance) or sharpe_variance <= 0.0:
        return 0.0
    sd = math.sqrt(sharpe_variance)
    term_a = (1.0 - _EULER_MASCHERONI) * standard_normal_ppf(1.0 - 1.0 / n_trials)
    term_b = _EULER_MASCHERONI * standard_normal_ppf(1.0 - 1.0 / (n_trials * math.e))
    return sd * (term_a + term_b)


def deflated_sharpe_ratio(
    returns: Iterable[float],
    trial_sharpe_ratios: Iterable[float],
) -> dict[str, Any]:
    """Deflated Sharpe Ratio of ``returns`` given the family of trial Sharpes.

    ``trial_sharpe_ratios`` are the Sharpe estimates of every configuration that
    was tried (including this one). Their count is the trial multiplicity ``N``
    and their variance estimates the selection-induced Sharpe dispersion. The
    DSR is the PSR with the benchmark set to the expected maximum Sharpe under
    that many trials — so a Sharpe that is merely the luckiest of many deflates
    toward (and below) 0.5.

    Returns a dict with ``deflated_sharpe_ratio``, the ``observed_sharpe_ratio``,
    the ``expected_max_sharpe_ratio`` benchmark, ``n_trials``, and ``n_returns``.
    """
    trials = _clean(trial_sharpe_ratios)
    n_trials = int(trials.size)
    if n_trials < 1:
        raise ValueError("trial_sharpe_ratios must contain at least one finite value")
    variance = float(trials.var(ddof=1)) if n_trials > 1 else 0.0
    benchmark = expected_maximum_sharpe_ratio(sharpe_variance=variance, n_trials=n_trials)
    sample = _clean(returns)
    observed = sharpe_ratio(sample)
    dsr = probabilistic_sharpe_ratio(sample, benchmark_sr=benchmark)
    return {
        "deflated_sharpe_ratio": dsr,
        "observed_sharpe_ratio": observed,
        "expected_max_sharpe_ratio": benchmark,
        "n_trials": n_trials,
        "n_returns": int(sample.size),
        "caveat": DEFLATED_SHARPE_CAVEAT,
    }


def probability_of_backtest_overfitting(
    performance: Any,
    *,
    n_splits: int = 10,
) -> dict[str, Any]:
    """Probability of Backtest Overfitting via CSCV.

    ``performance`` is a 2-D array-like / DataFrame of shape ``(T, N)``: ``T``
    time observations (rows) by ``N`` candidate configurations (columns), each
    cell a per-period performance figure (e.g. a return or expectancy
    difference). The rows are partitioned into ``n_splits`` contiguous blocks;
    for every way of choosing ``n_splits / 2`` blocks as the in-sample set, the
    in-sample-best column's *out-of-sample rank* is recorded. PBO is the fraction
    of splits whose in-sample winner lands at or below the OOS median (logit
    <= 0).

    Returns a dict with ``pbo``, ``n_combinations``, ``n_strategies``,
    ``n_splits`` (the even count actually used), and the ``logits`` list.
    """
    matrix = _as_matrix(performance)
    t_obs, n_strategies = matrix.shape
    if n_strategies < 2:
        raise ValueError("PBO requires at least 2 candidate configurations (columns)")
    if n_splits < 2 or n_splits % 2 != 0:
        raise ValueError("n_splits must be an even integer >= 2")
    if t_obs < n_splits:
        raise ValueError(
            f"need at least n_splits={n_splits} observations, got {t_obs}"
        )

    blocks = np.array_split(np.arange(t_obs), n_splits)
    half = n_splits // 2
    logits: list[float] = []
    for train_block_ids in combinations(range(n_splits), half):
        train_rows = np.concatenate([blocks[b] for b in train_block_ids])
        test_block_ids = [b for b in range(n_splits) if b not in train_block_ids]
        test_rows = np.concatenate([blocks[b] for b in test_block_ids])

        train_perf = _column_sharpes(matrix[train_rows])
        test_perf = _column_sharpes(matrix[test_rows])
        best = int(np.argmax(train_perf))
        # Out-of-sample relative rank of the in-sample winner: 1 = worst, N = best.
        order = np.argsort(np.argsort(test_perf, kind="mergesort"), kind="mergesort")
        rank = int(order[best]) + 1
        omega = rank / (n_strategies + 1)
        omega = min(max(omega, 1e-12), 1.0 - 1e-12)
        logits.append(math.log(omega / (1.0 - omega)))

    logit_array = np.asarray(logits, dtype=float)
    pbo = float((logit_array <= 0.0).mean()) if logit_array.size else float("nan")
    return {
        "pbo": pbo,
        "n_combinations": int(logit_array.size),
        "n_strategies": int(n_strategies),
        "n_splits": int(n_splits),
        "logits": [float(v) for v in logit_array],
        "caveat": DEFLATED_SHARPE_CAVEAT,
    }


# --- Adapters over out-of-sample per-split results --------------------------
#
# The candidate OOS validation step (``evaluate_candidate_registry_oos``)
# produces one row per (candidate, split) with an ``oos_expectancy_difference``.
# That is exactly the (T splits x N candidates) panel the deflation stack needs:
# each candidate's per-split series is its "return" stream, and the family of
# candidates is the trial multiplicity. These adapters reshape those research
# numbers into DSR / PBO without recomputing any edge.


def summarize_candidate_deflated_sharpe(
    oos_results: pd.DataFrame,
    *,
    candidate_column: str = "candidate_id",
    split_column: str = "split_number",
    value_column: str = "oos_expectancy_difference",
) -> pd.DataFrame:
    """Per-candidate Deflated Sharpe from per-split OOS expectancy differences.

    Each candidate's across-split ``value_column`` series is treated as its
    return stream; the family of per-candidate in-sample Sharpe estimates sets
    the trial multiplicity and variance for the deflation benchmark. One row per
    candidate. Candidates with fewer than two finite splits get ``nan``.
    """
    columns = [
        "candidate_id",
        "deflated_sharpe_ratio",
        "observed_sharpe_ratio",
        "expected_max_sharpe_ratio",
        "n_trials",
        "n_splits",
        "deflated_sharpe_caveat",
    ]
    if oos_results.empty:
        return pd.DataFrame(columns=columns)
    for required in (candidate_column, value_column):
        if required not in oos_results.columns:
            raise ValueError(f"oos_results is missing required column: {required}")

    series_by_candidate: dict[str, np.ndarray] = {}
    for candidate_id, group in oos_results.groupby(candidate_column, sort=True):
        series_by_candidate[str(candidate_id)] = _clean(group[value_column])

    trial_sharpes = [
        sharpe_ratio(series)
        for series in series_by_candidate.values()
    ]
    finite_trial_sharpes = [s for s in trial_sharpes if np.isfinite(s)]
    n_trials = len(series_by_candidate)
    variance = (
        float(np.var(finite_trial_sharpes, ddof=1))
        if len(finite_trial_sharpes) > 1
        else 0.0
    )
    benchmark = expected_maximum_sharpe_ratio(
        sharpe_variance=variance, n_trials=max(n_trials, 1)
    )

    rows: list[dict[str, Any]] = []
    for candidate_id, series in series_by_candidate.items():
        observed = sharpe_ratio(series)
        dsr = probabilistic_sharpe_ratio(series, benchmark_sr=benchmark)
        rows.append(
            {
                "candidate_id": candidate_id,
                "deflated_sharpe_ratio": dsr,
                "observed_sharpe_ratio": observed,
                "expected_max_sharpe_ratio": benchmark,
                "n_trials": int(n_trials),
                "n_splits": int(series.size),
                "deflated_sharpe_caveat": DEFLATED_SHARPE_CAVEAT,
            }
        )
    return pd.DataFrame(rows, columns=columns)


def portfolio_pbo_from_oos(
    oos_results: pd.DataFrame,
    *,
    candidate_column: str = "candidate_id",
    split_column: str = "split_number",
    value_column: str = "oos_expectancy_difference",
    n_splits: int | None = None,
) -> dict[str, Any]:
    """Portfolio Probability of Backtest Overfitting from OOS per-split results.

    Pivots ``oos_results`` into a (split x candidate) matrix of ``value_column``
    and runs CSCV. ``n_splits`` defaults to the largest even number of available
    splits, capped at 16 to bound the combinatorial blow-up. Returns the PBO dict
    (``pbo`` is ``nan`` when there are too few splits/candidates to evaluate).
    """
    if oos_results.empty:
        return _empty_pbo()
    for required in (candidate_column, split_column, value_column):
        if required not in oos_results.columns:
            raise ValueError(f"oos_results is missing required column: {required}")

    matrix = oos_results.pivot_table(
        index=split_column,
        columns=candidate_column,
        values=value_column,
        aggfunc="mean",
    ).sort_index()
    # Drop candidates/splits that are not fully observed so CSCV sees a dense panel.
    matrix = matrix.dropna(axis=1, how="any").dropna(axis=0, how="any")
    n_obs, n_candidates = matrix.shape
    if n_candidates < 2 or n_obs < 2:
        return _empty_pbo()

    if n_splits is None:
        even = n_obs if n_obs % 2 == 0 else n_obs - 1
        n_splits = max(2, min(even, 16))
    if n_obs < n_splits:
        return _empty_pbo()
    return probability_of_backtest_overfitting(matrix.to_numpy(dtype=float), n_splits=n_splits)


def _empty_pbo() -> dict[str, Any]:
    return {
        "pbo": float("nan"),
        "n_combinations": 0,
        "n_strategies": 0,
        "n_splits": 0,
        "logits": [],
        "caveat": DEFLATED_SHARPE_CAVEAT,
    }


def _column_sharpes(block: np.ndarray) -> np.ndarray:
    """Sharpe of each column of a 2-D block; degenerate columns map to -inf."""
    mean = block.mean(axis=0)
    std = block.std(axis=0, ddof=1) if block.shape[0] > 1 else np.zeros(block.shape[1])
    with np.errstate(divide="ignore", invalid="ignore"):
        sharpe = np.where(std > 0, mean / std, -np.inf)
    return np.where(np.isfinite(sharpe), sharpe, -np.inf)


def _skew_kurtosis(sample: np.ndarray) -> tuple[float, float]:
    """Population skewness and Pearson (non-excess) kurtosis of a sample."""
    n = sample.size
    mean = sample.mean()
    centered = sample - mean
    m2 = np.mean(centered**2)
    if m2 <= 0.0:
        return 0.0, 3.0
    m3 = np.mean(centered**3)
    m4 = np.mean(centered**4)
    skew = float(m3 / m2**1.5)
    kurt = float(m4 / m2**2)
    return skew, kurt


def _clean(values: Iterable[float]) -> np.ndarray:
    series = pd.to_numeric(pd.Series(list(values)), errors="coerce").dropna()
    return series.to_numpy(dtype=float)


def _as_matrix(performance: Any) -> np.ndarray:
    if isinstance(performance, pd.DataFrame):
        array = performance.to_numpy(dtype=float)
    else:
        array = np.asarray(performance, dtype=float)
    if array.ndim != 2:
        raise ValueError("performance must be 2-dimensional (T observations x N configs)")
    if np.isnan(array).any():
        raise ValueError("performance must not contain NaN; drop or impute first")
    return array
