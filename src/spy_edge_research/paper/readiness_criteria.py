"""Declarative, pre-registered paper-trading readiness criteria.

These criteria define what evidence a candidate must show before it could even
be *considered* for a future, separately-authorized paper-trading layer. They
are research gates only: nothing here authorizes a trade, sizes a position, or
implies a live or paper order.
"""

from __future__ import annotations

from dataclasses import dataclass


READINESS_CRITERIA_CAVEAT = "readiness_criteria_are_research_gates_not_trade_authorization"


@dataclass(frozen=True)
class ReadinessCriteria:
    """Pre-registered thresholds. ``None`` / ``False`` disables a criterion."""

    min_oos_positive_splits: int | None = 2
    min_oos_mean_sample_size: float | None = 30.0
    require_negative_control_pass: bool = True
    require_multiple_testing_pass: bool = True
    min_temporal_stable_periods: int | None = 2
    max_pairwise_jaccard: float | None = 0.8


def default_readiness_criteria() -> ReadinessCriteria:
    """Return the conservative default research readiness criteria."""
    return ReadinessCriteria()
