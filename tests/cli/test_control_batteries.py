"""Tests for the MOD 11 control batteries (M101) and the readiness-gate flip.

The batteries reduce negative-control, multiple-testing, and temporal-stability
diagnostics into the scalars the readiness gate consumes so a validated candidate
can finally reach ``eligible_for_paper_consideration``. These tests assert (a) the
batteries fire correctly on a known edge versus a null/wrong-direction condition,
and (b) the verdict flips to eligible only when every criterion passes.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from spy_edge_research.cli.control_batteries import (
    ControlBatteryConfig,
    ControlBatteryResults,
    run_control_batteries,
)
from spy_edge_research.cli.pipeline import _score_readiness


def _registry(candidate_id: str, event_column: str, label_column: str) -> pd.DataFrame:
    """Minimal in-memory registry carrying the fields the batteries read."""
    return pd.DataFrame(
        [
            {
                "candidate_id": candidate_id,
                "name": event_column,
                "context": {"label_column": label_column},
            }
        ]
    )


def _daily_frame(*, edge: float, n: int = 120, seed: int = 0) -> pd.DataFrame:
    """Daily bars spanning ~4 calendar months with an event column.

    ``edge`` is added to the forward outcome on event rows: positive = a real
    edge, negative = a wrong-direction (null) condition.
    """
    timestamps = pd.date_range("2024-01-01", periods=n, freq="D")
    rng = np.random.default_rng(seed)
    event = np.zeros(n, dtype=bool)
    event[::3] = True
    outcome = rng.normal(0.0, 0.1, size=n)
    outcome[event] += edge
    return pd.DataFrame(
        {
            "timestamp": timestamps,
            "event_x": event,
            "forward_return_5m": outcome,
        }
    )


def test_negative_control_passes_for_real_edge_and_counts_periods():
    df = _daily_frame(edge=1.0)
    registry = _registry("event_x__5m", "event_x", "forward_return_5m")

    results = run_control_batteries(df, registry)
    per = results.per_candidate["event_x__5m"]

    # A strong, correctly-directed edge beats every negative control.
    assert per["negative_control_passed"] is True
    # Events occur across multiple calendar months.
    assert per["temporal_stable_period_count"] >= 2
    # A single tested hypothesis is low multiple-testing risk.
    assert results.multiple_testing_passed is True
    assert results.tested_hypotheses == 1
    assert results.multiple_testing_warning == "low"


def test_negative_control_fails_for_wrong_direction_condition():
    df = _daily_frame(edge=-1.0)
    registry = _registry("event_x__5m", "event_x", "forward_return_5m")

    results = run_control_batteries(df, registry)
    per = results.per_candidate["event_x__5m"]

    # A wrong-direction condition does not beat the negative controls.
    assert per["negative_control_passed"] is False


def test_multiple_testing_per_candidate_passes_for_real_edge():
    df = _daily_frame(edge=1.0)
    registry = _registry("c_real", "event_x", "forward_return_5m")
    results = run_control_batteries(df, registry)
    # A strong, real edge yields a tiny permutation p-value -> survives FDR.
    assert results.per_candidate["c_real"]["multiple_testing_passed"] is True
    cols = set(results.multiple_testing_table.columns)
    assert {"candidate_id", "p_value", "p_value_fdr_bh", "multiple_testing_passed"} <= cols


def test_multiple_testing_per_candidate_fails_for_null_candidate():
    df = _daily_frame(edge=0.0)
    df["forward_return_5m"] = 0.0  # truly null: zero event-vs-non-event difference
    registry = _registry("c_null", "event_x", "forward_return_5m")
    results = run_control_batteries(df, registry)
    assert results.per_candidate["c_null"]["multiple_testing_passed"] is False


def test_multiple_testing_flags_high_for_large_family():
    df = _daily_frame(edge=1.0)
    registry = pd.concat(
        [_registry(f"c{i}", "event_x", "forward_return_5m") for i in range(150)],
        ignore_index=True,
    )
    results = run_control_batteries(
        df, registry, config=ControlBatteryConfig(multiple_testing_high_count=100)
    )
    assert results.multiple_testing_warning == "high"
    assert results.multiple_testing_passed is False


def _oos_row() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "candidate_id": "c1",
                "oos_positive_expectancy_difference_splits": 3,
                "oos_mean_sample_size": 50.0,
                "oos_mean_expectancy_difference": 0.0002,  # 2 bps, clears the floor
            }
        ]
    )


def _controls(*, negative_control: bool, multiple_testing: bool, temporal: int):
    return ControlBatteryResults(
        per_candidate={
            "c1": {
                "negative_control_passed": negative_control,
                "temporal_stable_period_count": temporal,
            }
        },
        multiple_testing_passed=multiple_testing,
        tested_hypotheses=1,
        multiple_testing_warning="low",
        negative_control_table=pd.DataFrame(),
        temporal_stability_table=pd.DataFrame(),
        multiple_testing_table=pd.DataFrame(),
    )


def test_verdict_flips_to_eligible_when_all_criteria_pass():
    controls = _controls(negative_control=True, multiple_testing=True, temporal=3)
    _, verdict = _score_readiness(_oos_row(), {"max_pairwise_jaccard": 0.1}, controls)
    assert (verdict["verdict"] == "eligible_for_paper_consideration").all()
    assert (verdict["failing_reasons"] == "").all()


def test_verdict_stays_not_ready_when_negative_control_fails():
    controls = _controls(negative_control=False, multiple_testing=True, temporal=3)
    _, verdict = _score_readiness(_oos_row(), {"max_pairwise_jaccard": 0.1}, controls)
    assert (verdict["verdict"] == "not_ready").all()
    assert "negative_control_not_passed" in verdict.iloc[0]["failing_reasons"]


def test_verdict_stays_not_ready_when_temporal_below_min():
    controls = _controls(negative_control=True, multiple_testing=True, temporal=1)
    _, verdict = _score_readiness(_oos_row(), {"max_pairwise_jaccard": 0.1}, controls)
    assert (verdict["verdict"] == "not_ready").all()


def test_verdict_not_ready_without_control_results():
    # Backward-compatible: no batteries -> those criteria are insufficient evidence.
    _, verdict = _score_readiness(_oos_row(), {"max_pairwise_jaccard": 0.1}, None)
    assert (verdict["verdict"] == "not_ready").all()
