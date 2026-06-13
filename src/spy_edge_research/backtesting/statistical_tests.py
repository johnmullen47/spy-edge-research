"""Statistical testing helpers for research-only event validation."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

import numpy as np
import pandas as pd


def calculate_confidence_interval(
    values: Iterable[float],
    *,
    confidence_level: float = 0.95,
) -> tuple[float, float]:
    """Calculate a percentile confidence interval from sampled statistics."""
    _validate_probability(confidence_level, "confidence_level")
    sample = _clean_numeric_array(values)
    if sample.size == 0:
        return (np.nan, np.nan)
    alpha = 1.0 - confidence_level
    lower = float(np.quantile(sample, alpha / 2.0))
    upper = float(np.quantile(sample, 1.0 - alpha / 2.0))
    return lower, upper


def bootstrap_mean_difference(
    event_values: Iterable[float],
    baseline_values: Iterable[float],
    *,
    n_bootstrap: int = 1000,
    confidence_level: float = 0.95,
    seed: int | None = None,
) -> dict[str, Any]:
    """Bootstrap the difference in means between event and baseline samples.

    Note: a sample of size 1 resamples to a constant, producing a degenerate
    (zero-width) interval that understates uncertainty; treat CIs from tiny
    samples (n < ~2, and cautiously n < ~30) as unreliable — see the
    ``small_*_sample`` flags from ``summarize_statistical_test_result``.
    """
    event = _clean_numeric_array(event_values)
    baseline = _clean_numeric_array(baseline_values)
    _validate_resample_inputs(event, baseline, n_bootstrap, confidence_level)
    rng = np.random.default_rng(seed)

    sampled_differences = np.array(
        [
            rng.choice(event, size=event.size, replace=True).mean()
            - rng.choice(baseline, size=baseline.size, replace=True).mean()
            for _ in range(n_bootstrap)
        ]
    )
    ci_lower, ci_upper = calculate_confidence_interval(
        sampled_differences,
        confidence_level=confidence_level,
    )
    return {
        "test_name": "bootstrap_mean_difference",
        "observed_difference": float(event.mean() - baseline.mean()),
        "confidence_level": confidence_level,
        "ci_lower": ci_lower,
        "ci_upper": ci_upper,
        "p_value": np.nan,
        "n_event": int(event.size),
        "n_baseline": int(baseline.size),
        "n_resamples": n_bootstrap,
        "seed": seed,
    }


def bootstrap_hit_rate_difference(
    event_values: Iterable[float],
    baseline_values: Iterable[float],
    *,
    threshold: float = 0.0,
    n_bootstrap: int = 1000,
    confidence_level: float = 0.95,
    seed: int | None = None,
) -> dict[str, Any]:
    """Bootstrap the difference in hit rates above a threshold."""
    event = _clean_numeric_array(event_values)
    baseline = _clean_numeric_array(baseline_values)
    _validate_resample_inputs(event, baseline, n_bootstrap, confidence_level)
    _validate_number(threshold, "threshold")
    rng = np.random.default_rng(seed)

    event_hits = event > threshold
    baseline_hits = baseline > threshold
    sampled_differences = np.array(
        [
            rng.choice(event_hits, size=event_hits.size, replace=True).mean()
            - rng.choice(baseline_hits, size=baseline_hits.size, replace=True).mean()
            for _ in range(n_bootstrap)
        ]
    )
    ci_lower, ci_upper = calculate_confidence_interval(
        sampled_differences,
        confidence_level=confidence_level,
    )
    return {
        "test_name": "bootstrap_hit_rate_difference",
        "observed_difference": float(event_hits.mean() - baseline_hits.mean()),
        "confidence_level": confidence_level,
        "ci_lower": ci_lower,
        "ci_upper": ci_upper,
        "p_value": np.nan,
        "n_event": int(event.size),
        "n_baseline": int(baseline.size),
        "n_resamples": n_bootstrap,
        "seed": seed,
        "threshold": threshold,
    }


def permutation_test_event_vs_baseline(
    event_values: Iterable[float],
    baseline_values: Iterable[float],
    *,
    statistic: str = "mean",
    threshold: float = 0.0,
    n_permutations: int = 1000,
    seed: int | None = None,
) -> dict[str, Any]:
    """Permutation test for event-vs-baseline differences.

    The two-sided p-value counts permutations whose absolute statistic is
    ``>=`` the observed (the conservative convention, ties included). With a
    finite number of permutations the p-value can be exactly 0.0; interpret that
    as "below 1/n_permutations", not as true zero.
    """
    event = _clean_numeric_array(event_values)
    baseline = _clean_numeric_array(baseline_values)
    _validate_positive_int(n_permutations, "n_permutations")
    _validate_non_empty_samples(event, baseline)
    if statistic not in {"mean", "hit_rate"}:
        raise ValueError("statistic must be one of: mean, hit_rate")
    _validate_number(threshold, "threshold")

    observed = _statistic_difference(
        event,
        baseline,
        statistic=statistic,
        threshold=threshold,
    )
    combined = np.concatenate([event, baseline])
    event_size = event.size
    rng = np.random.default_rng(seed)
    permuted = np.empty(n_permutations, dtype=float)
    for index in range(n_permutations):
        shuffled = rng.permutation(combined)
        permuted[index] = _statistic_difference(
            shuffled[:event_size],
            shuffled[event_size:],
            statistic=statistic,
            threshold=threshold,
        )
    p_value = float((np.abs(permuted) >= abs(observed)).mean())
    return {
        "test_name": "permutation_test_event_vs_baseline",
        "statistic": statistic,
        "observed_difference": float(observed),
        "confidence_level": np.nan,
        "ci_lower": np.nan,
        "ci_upper": np.nan,
        "p_value": p_value,
        "n_event": int(event.size),
        "n_baseline": int(baseline.size),
        "n_resamples": n_permutations,
        "seed": seed,
        "threshold": threshold,
    }


def summarize_statistical_test_result(
    result: Mapping[str, Any],
    *,
    small_sample_threshold: int = 30,
) -> pd.DataFrame:
    """Summarize one statistical test result with sample-size warnings."""
    _validate_positive_int(small_sample_threshold, "small_sample_threshold")
    required = [
        "test_name",
        "observed_difference",
        "ci_lower",
        "ci_upper",
        "p_value",
        "n_event",
        "n_baseline",
        "n_resamples",
    ]
    missing = [field for field in required if field not in result]
    if missing:
        raise KeyError(f"result is missing required fields: {missing}")
    n_event = int(result["n_event"])
    n_baseline = int(result["n_baseline"])
    warnings = []
    if n_event < small_sample_threshold:
        warnings.append("small_event_sample")
    if n_baseline < small_sample_threshold:
        warnings.append("small_baseline_sample")
    if pd.isna(result.get("p_value")):
        warnings.append("no_p_value")
    return pd.DataFrame(
        [
            {
                "test_name": result["test_name"],
                "observed_difference": result["observed_difference"],
                "ci_lower": result["ci_lower"],
                "ci_upper": result["ci_upper"],
                "p_value": result["p_value"],
                "n_event": n_event,
                "n_baseline": n_baseline,
                "n_resamples": result["n_resamples"],
                "sample_warning": ",".join(warnings) if warnings else "none",
            }
        ]
    )


def _statistic_difference(
    event: np.ndarray,
    baseline: np.ndarray,
    *,
    statistic: str,
    threshold: float,
) -> float:
    if statistic == "mean":
        return float(event.mean() - baseline.mean())
    return float((event > threshold).mean() - (baseline > threshold).mean())


def _clean_numeric_array(values: Iterable[float]) -> np.ndarray:
    series = pd.to_numeric(pd.Series(list(values)), errors="coerce").dropna()
    return series.to_numpy(dtype=float)


def _validate_resample_inputs(
    event: np.ndarray,
    baseline: np.ndarray,
    n_resamples: int,
    confidence_level: float,
) -> None:
    _validate_positive_int(n_resamples, "n_resamples")
    _validate_probability(confidence_level, "confidence_level")
    _validate_non_empty_samples(event, baseline)


def _validate_non_empty_samples(event: np.ndarray, baseline: np.ndarray) -> None:
    if event.size == 0:
        raise ValueError("event_values must contain at least one numeric value")
    if baseline.size == 0:
        raise ValueError("baseline_values must contain at least one numeric value")


def _validate_probability(value: float, name: str) -> None:
    if not isinstance(value, (int, float)) or isinstance(value, bool) or value <= 0 or value >= 1:
        raise ValueError(f"{name} must be in the interval (0, 1)")


def _validate_positive_int(value: int, name: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise ValueError(f"{name} must be an integer greater than or equal to 1")


def _validate_number(value: float, name: str) -> None:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError(f"{name} must be numeric")
