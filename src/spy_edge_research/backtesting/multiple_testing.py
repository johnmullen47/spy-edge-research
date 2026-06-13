"""Multiple-hypothesis risk helpers for research validation."""

from __future__ import annotations

from collections.abc import Iterable

import numpy as np
import pandas as pd

from spy_edge_research._internal._common import (
    normalize_columns as _normalize_columns,
    require_columns as _require_columns,
)


def count_tested_hypotheses(
    results: pd.DataFrame,
    group_columns: Iterable[str] | None = None,
) -> int | pd.DataFrame:
    """Count tested hypotheses overall or by grouping columns."""
    if group_columns is None:
        return int(len(results))
    groups = _normalize_columns(group_columns, "group_columns")
    _require_columns(results, groups)
    return (
        results.groupby(groups, dropna=False)
        .size()
        .reset_index(name="hypothesis_count")
        .sort_values(groups, kind="mergesort")
        .reset_index(drop=True)
    )


def apply_bonferroni_adjustment(
    results: pd.DataFrame,
    *,
    p_value_col: str = "p_value",
    output_col: str = "p_value_bonferroni",
    n_tests: int | None = None,
) -> pd.DataFrame:
    """Add Bonferroni-adjusted p-values.

    The multiplicity family size defaults to the number of rows with a valid
    (non-NaN) p-value, so rows that carry no p-value (e.g. bootstrap confidence
    intervals, which set ``p_value=NaN``) do not enlarge the correction family.
    If the intended family is larger than the p-value-bearing rows present here,
    pass ``n_tests`` explicitly to avoid under-correcting the family-wise error
    rate.
    """
    _require_columns(results, [p_value_col])
    if n_tests is not None and (not isinstance(n_tests, int) or isinstance(n_tests, bool) or n_tests < 1):
        raise ValueError("n_tests must be an integer greater than or equal to 1")
    result = results.copy()
    p_values = pd.to_numeric(result[p_value_col], errors="coerce")
    test_count = n_tests if n_tests is not None else int(p_values.notna().sum())
    result[output_col] = (p_values * test_count).clip(upper=1.0)
    return result


def apply_false_discovery_rate_adjustment(
    results: pd.DataFrame,
    *,
    p_value_col: str = "p_value",
    output_col: str = "p_value_fdr_bh",
) -> pd.DataFrame:
    """Add Benjamini-Hochberg false-discovery-rate adjusted p-values."""
    _require_columns(results, [p_value_col])
    result = results.copy()
    p_values = pd.to_numeric(result[p_value_col], errors="coerce")
    adjusted = pd.Series(np.nan, index=result.index, dtype="float64")
    valid = p_values.dropna().sort_values(kind="mergesort")
    m = len(valid)
    if m:
        ranks = np.arange(1, m + 1)
        raw_adjusted = valid.to_numpy() * m / ranks
        monotonic = np.minimum.accumulate(raw_adjusted[::-1])[::-1]
        adjusted.loc[valid.index] = np.clip(monotonic, 0.0, 1.0)
    result[output_col] = adjusted
    return result


def summarize_multiple_testing_risk(
    results: pd.DataFrame,
    *,
    p_value_col: str = "p_value",
    alpha: float = 0.05,
) -> pd.DataFrame:
    """Summarize unadjusted and adjusted discovery counts.

    ``multiple_testing_warning`` is a coarse research heuristic on the number of
    tested hypotheses: ``high`` at >= 100 (Bonferroni becomes very strict —
    prefer FDR), ``moderate`` at >= 20, else ``low``. It is advisory only.
    """
    _validate_probability(alpha, "alpha")
    adjusted = apply_false_discovery_rate_adjustment(
        apply_bonferroni_adjustment(results, p_value_col=p_value_col),
        p_value_col=p_value_col,
    )
    p_values = pd.to_numeric(adjusted[p_value_col], errors="coerce")
    bonferroni = adjusted["p_value_bonferroni"]
    fdr = adjusted["p_value_fdr_bh"]
    tested = int(p_values.notna().sum())
    return pd.DataFrame(
        [
            {
                "tested_hypotheses": tested,
                "alpha": alpha,
                "unadjusted_below_alpha": int(p_values.lt(alpha).sum()),
                "bonferroni_below_alpha": int(bonferroni.lt(alpha).sum()),
                "fdr_bh_below_alpha": int(fdr.lt(alpha).sum()),
                "multiple_testing_warning": "high"
                if tested >= 100
                else "moderate"
                if tested >= 20
                else "low",
            }
        ]
    )


def _validate_probability(value: float, name: str) -> None:
    if not isinstance(value, (int, float)) or isinstance(value, bool) or value <= 0 or value >= 1:
        raise ValueError(f"{name} must be in the interval (0, 1)")
