"""Tests for the VQM factor-outcome event study (MOD 13)."""

from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

from spy_edge_research.backtesting.vqm_event_study import (
    build_vqm_event_research_report,
    export_vqm_event_research_report_to_csv,
    factor_score_bucket_spread,
    summarize_factor_score_coverage,
    summarize_outcomes_by_factor_score,
)


def _scored_frame(n: int = 100, seed: int = 2) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    score = np.linspace(0, 1, n)
    # Outcome rises with score so the top bucket beats the bottom (testable sign).
    outcome = score * 0.01 + rng.normal(0, 0.001, n)
    return pd.DataFrame({"score": score, "outcome": outcome})


def test_buckets_are_ordered_and_cover_all_rows():
    summary = summarize_outcomes_by_factor_score(
        _scored_frame(), score_col="score", outcome_col="outcome", n_buckets=5
    )
    assert list(summary["bucket"]) == sorted(summary["bucket"])
    assert summary["count"].sum() == 100
    # score ranges are non-overlapping and increasing.
    assert list(summary["score_min"]) == sorted(summary["score_min"])


def test_spread_is_top_minus_bottom_and_positive_for_monotone_outcome():
    summary = summarize_outcomes_by_factor_score(
        _scored_frame(), score_col="score", outcome_col="outcome", n_buckets=5
    )
    spread = factor_score_bucket_spread(summary).iloc[0]
    expected = summary.iloc[-1]["outcome_mean"] - summary.iloc[0]["outcome_mean"]
    assert spread["outcome_mean_spread"] == pytest.approx(expected)
    assert spread["outcome_mean_spread"] > 0  # outcome rises with score


def test_coverage_counts_usable_rows():
    df = _scored_frame(n=50)
    df.loc[0:4, "outcome"] = np.nan  # 5 rows lose the outcome
    coverage = summarize_factor_score_coverage(df, score_col="score", outcome_col="outcome").iloc[0]
    assert coverage["total_rows"] == 50
    assert coverage["usable_rows"] == 45


def test_empty_after_dropna_returns_empty_summary():
    df = pd.DataFrame({"score": [np.nan, np.nan], "outcome": [0.1, 0.2]})
    summary = summarize_outcomes_by_factor_score(df, score_col="score", outcome_col="outcome")
    assert summary.empty


def test_report_bundle_and_csv_round_trip(tmp_path):
    report = build_vqm_event_research_report(
        _scored_frame(), score_col="score", outcome_col="outcome", n_buckets=4
    )
    assert set(report["tables"]) == {"bucket_outcomes", "bucket_spread", "coverage"}
    assert report["metadata"]["report_caveat"]

    written = export_vqm_event_research_report_to_csv(report, tmp_path)
    assert (tmp_path / "bucket_outcomes.csv").exists()
    meta = json.loads((tmp_path / "metadata.json").read_text())
    assert meta["score_col"] == "score"
    reloaded = pd.read_csv(written["bucket_outcomes"])
    assert len(reloaded) == len(report["tables"]["bucket_outcomes"])


def test_export_refuses_to_clobber(tmp_path):
    report = build_vqm_event_research_report(
        _scored_frame(), score_col="score", outcome_col="outcome"
    )
    export_vqm_event_research_report_to_csv(report, tmp_path)
    with pytest.raises(FileExistsError):
        export_vqm_event_research_report_to_csv(report, tmp_path)
