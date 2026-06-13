from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from spy_edge_research.backtesting import (
    build_candidate_edge_registry,
    compare_in_sample_vs_oos_results,
    create_candidate_edge,
    create_time_series_splits,
    evaluate_candidate_edge_in_split,
    evaluate_candidate_registry_oos,
    summarize_oos_edge_stability,
)


_DEFAULT_SPLIT = {"split_number": 0, "train_indices": [0, 1, 2, 3], "test_indices": [4, 5, 6]}


def sample_oos_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "timestamp": pd.date_range("2024-01-02 09:31", periods=10, freq="1min"),
            "event_vwap_reclaim": [
                True,
                False,
                True,
                False,
                True,
                False,
                True,
                False,
                True,
                False,
            ],
            "recent_sequence": [
                "a>b",
                "",
                "a>b",
                "",
                "b>c",
                "a>b",
                "",
                "a>b",
                "",
                "b>c",
            ],
            "session_bucket": [
                "open",
                "open",
                "open",
                "open",
                "lunch",
                "open",
                "open",
                "open",
                "lunch",
                "open",
            ],
            "fwd_5m_return": [
                0.010,
                -0.004,
                0.012,
                -0.002,
                0.003,
                -0.006,
                0.020,
                0.004,
                -0.010,
                0.002,
            ],
        }
    )


def event_candidate(candidate_id: str = "event_vwap_reclaim_5m") -> dict[str, object]:
    return create_candidate_edge(
        candidate_id=candidate_id,
        candidate_type="event",
        name="event_vwap_reclaim",
        direction="long",
        horizon="5m",
        context={"event_column": "event_vwap_reclaim", "outcome_column": "fwd_5m_return"},
        sample_size=3,
        baseline_sample_size=6,
        expectancy=0.008,
        baseline_expectancy=0.003,
        hit_rate=1.0,
        baseline_hit_rate=0.5,
        caveats=["candidate_is_hypothesis"],
        data_start="2024-01-02",
        data_end="2024-01-02",
        reproducibility_metadata={"run_id": "unit"},
    )


def test_evaluate_candidate_edge_in_split_uses_chronological_train_and_oos_windows() -> None:
    df = sample_oos_frame()
    split = {
        "split_number": 0,
        "train_indices": [0, 1, 2, 3],
        "test_indices": [4, 5, 6],
    }

    result = evaluate_candidate_edge_in_split(
        df,
        event_candidate(),
        split,
        min_events=1,
    )

    assert result["candidate_id"] == "event_vwap_reclaim_5m"
    assert result["train_start"] == 0
    assert result["train_end"] == 3
    assert result["test_start"] == 4
    assert result["test_end"] == 6
    assert result["evaluation_target"] == "fwd_5m_return"
    assert result["hypothesis_definition"] == "event:event_vwap_reclaim"
    assert result["train_sample_size"] == 2
    assert result["train_baseline_sample_size"] == 4
    assert result["train_expectancy"] == pytest.approx(0.011)
    assert result["train_baseline_expectancy"] == pytest.approx(0.004)
    assert result["oos_sample_size"] == 2
    assert result["oos_baseline_sample_size"] == 3
    assert result["oos_expectancy"] == pytest.approx(0.0115)
    assert "out_of_sample_result_is_not_edge_proof" in result["caveats"]


def test_evaluate_candidate_registry_oos_handles_event_sequence_and_conditional_candidates() -> None:
    df = sample_oos_frame()
    sequence = create_candidate_edge(
        candidate_id="sequence_ab_5m",
        candidate_type="sequence",
        name="a>b",
        direction="long",
        horizon="5m",
        context={
            "sequence_column": "recent_sequence",
            "event_sequence": "a>b",
            "outcome_column": "fwd_5m_return",
        },
        sample_size=4,
        baseline_sample_size=10,
        expectancy=0.004,
        baseline_expectancy=0.003,
        hit_rate=0.75,
        baseline_hit_rate=0.6,
    )
    conditional = create_candidate_edge(
        candidate_id="conditional_open_reclaim_5m",
        candidate_type="conditional_event",
        name="event_vwap_reclaim",
        direction="long",
        horizon="5m",
        context={
            "event_column": "event_vwap_reclaim",
            "outcome_column": "fwd_5m_return",
            "context_filters": {"session_bucket": "open"},
        },
        sample_size=3,
        baseline_sample_size=8,
        expectancy=0.014,
        baseline_expectancy=0.005,
        hit_rate=1.0,
        baseline_hit_rate=0.625,
    )
    registry = build_candidate_edge_registry([event_candidate(), sequence, conditional])
    splits = create_time_series_splits(df, train_size=4, test_size=3, n_splits=2, step_size=3)

    results = evaluate_candidate_registry_oos(df, registry, splits, min_events=1)

    assert results.shape[0] == 6
    assert set(results["candidate_id"]) == {
        "event_vwap_reclaim_5m",
        "sequence_ab_5m",
        "conditional_open_reclaim_5m",
    }
    conditional_row = results.loc[
        (results["candidate_id"] == "conditional_open_reclaim_5m")
        & (results["split_number"] == 0)
    ].iloc[0]
    assert conditional_row["hypothesis_definition"] == (
        "conditional_event:event_vwap_reclaim|session_bucket=open"
    )
    assert conditional_row["oos_sample_size"] == 1


def test_compare_in_sample_vs_oos_results_adds_descriptive_diagnostics() -> None:
    df = sample_oos_frame()
    split = {
        "split_number": 0,
        "train_indices": [0, 1, 2, 3],
        "test_indices": [4, 5, 6],
    }
    results = pd.DataFrame(
        [evaluate_candidate_edge_in_split(df, event_candidate(), split, min_events=1)]
    )

    compared = compare_in_sample_vs_oos_results(results)

    assert "oos_minus_train_expectancy_difference" in compared.columns
    assert "same_expectancy_difference_sign" in compared.columns
    assert bool(compared.loc[0, "same_expectancy_difference_sign"])


def test_summarize_oos_edge_stability_is_descriptive_across_splits() -> None:
    df = sample_oos_frame()
    registry = build_candidate_edge_registry([event_candidate()])
    splits = create_time_series_splits(df, train_size=4, test_size=3, n_splits=2, step_size=3)
    results = evaluate_candidate_registry_oos(df, registry, splits, min_events=2)

    summary = summarize_oos_edge_stability(results)

    assert summary.to_dict("records")[0]["candidate_id"] == "event_vwap_reclaim_5m"
    assert summary.to_dict("records")[0]["split_count"] == 2
    assert summary.to_dict("records")[0]["small_sample_split_count"] == 1
    assert "stability_summary_is_descriptive_only" in summary.to_dict("records")[0]["caveats"]


def test_oos_validation_rejects_missing_outcome_mapping_and_bad_splits() -> None:
    df = sample_oos_frame()
    candidate = event_candidate()
    candidate["context"] = {"event_column": "event_vwap_reclaim"}

    with pytest.raises(ValueError, match="outcome_column"):
        evaluate_candidate_edge_in_split(
            df,
            candidate,
            {"split_number": 0, "train_indices": [0, 1], "test_indices": [2, 3]},
        )

    with pytest.raises(ValueError, match="overlap"):
        evaluate_candidate_edge_in_split(
            df,
            event_candidate(),
            {"split_number": 0, "train_indices": [0, 1], "test_indices": [1, 2]},
        )


def test_oos_validation_rejects_lookahead_event_column() -> None:
    df = sample_oos_frame()
    candidate = event_candidate(candidate_id="leaky_event_5m")
    candidate["context"] = {
        "event_column": "forward_return_5m",
        "outcome_column": "fwd_5m_return",
    }

    with pytest.raises(ValueError, match="forward-looking"):
        evaluate_candidate_edge_in_split(df, candidate, _DEFAULT_SPLIT)


def test_oos_validation_rejects_lookahead_sequence_column() -> None:
    df = sample_oos_frame()
    candidate = create_candidate_edge(
        candidate_id="leaky_sequence_5m",
        candidate_type="sequence",
        name="a>b",
        direction="long",
        horizon="5m",
        context={
            "sequence_column": "future_sequence",
            "event_sequence": "a>b",
            "outcome_column": "fwd_5m_return",
        },
        sample_size=4,
        baseline_sample_size=10,
        expectancy=0.004,
        baseline_expectancy=0.003,
        hit_rate=0.75,
        baseline_hit_rate=0.6,
    )

    with pytest.raises(ValueError, match="forward-looking"):
        evaluate_candidate_edge_in_split(df, candidate, _DEFAULT_SPLIT)


def test_oos_validation_rejects_lookahead_context_filter_column() -> None:
    df = sample_oos_frame()
    candidate = create_candidate_edge(
        candidate_id="leaky_conditional_5m",
        candidate_type="conditional_event",
        name="event_vwap_reclaim",
        direction="long",
        horizon="5m",
        context={
            "event_column": "event_vwap_reclaim",
            "outcome_column": "fwd_5m_return",
            "context_filters": {"future_regime": "trend"},
        },
        sample_size=3,
        baseline_sample_size=8,
        expectancy=0.014,
        baseline_expectancy=0.005,
        hit_rate=1.0,
        baseline_hit_rate=0.625,
    )

    with pytest.raises(ValueError, match="forward-looking"):
        evaluate_candidate_edge_in_split(df, candidate, _DEFAULT_SPLIT)


def test_oos_validation_allows_forward_looking_outcome_column() -> None:
    # The evaluation target is *supposed* to look forward, so a forward-looking
    # outcome_column name must remain accepted even though trigger columns are guarded.
    df = sample_oos_frame().rename(columns={"fwd_5m_return": "forward_return_5m"})
    candidate = event_candidate()
    candidate["context"] = {
        "event_column": "event_vwap_reclaim",
        "outcome_column": "forward_return_5m",
    }

    result = evaluate_candidate_edge_in_split(df, candidate, _DEFAULT_SPLIT)

    assert result["evaluation_target"] == "forward_return_5m"
    assert result["hypothesis_definition"] == "event:event_vwap_reclaim"


def test_oos_validation_accepts_numpy_scalar_threshold() -> None:
    df = sample_oos_frame()

    result = evaluate_candidate_edge_in_split(
        df,
        event_candidate(),
        _DEFAULT_SPLIT,
        hit_rate_threshold=np.float64(0.0),
    )

    assert result["candidate_id"] == "event_vwap_reclaim_5m"


def test_oos_validation_outputs_avoid_live_trading_readiness_columns() -> None:
    df = sample_oos_frame()
    registry = build_candidate_edge_registry([event_candidate()])
    splits = [{"split_number": 0, "train_indices": [0, 1, 2, 3], "test_indices": [4, 5, 6]}]

    results = evaluate_candidate_registry_oos(df, registry, splits)
    summary = summarize_oos_edge_stability(results)

    forbidden = ("buy", "sell", "entry", "exit", "approved", "live", "trade_signal")
    assert not any(word in column for column in results.columns for word in forbidden)
    assert not any(word in column for column in summary.columns for word in forbidden)
