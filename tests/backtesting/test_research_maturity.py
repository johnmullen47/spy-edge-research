from __future__ import annotations

import pytest

from spy_edge_research.backtesting import (
    build_research_maturity_table,
    create_research_maturity_record,
    score_research_package_from_diagnostics,
    summarize_research_maturity,
)


def test_create_research_maturity_record_scores_components_without_readiness_claims() -> None:
    record = create_research_maturity_record(
        package_id="pkg_a",
        subject_id="rule_a",
        component_scores={
            "evidence_completeness": 1.0,
            "oos_coverage": 1.0,
            "placebo_risk_control": 0.5,
            "temporal_stability": 0.5,
            "data_quality": 1.0,
            "caveat_control": 0.8,
            "decision_status": 0.5,
        },
    )

    assert record["research_maturity_score"] == pytest.approx(0.7571428571)
    assert record["maturity_band"] == "well_documented"
    assert record["maturity_caveat"] == "maturity_score_is_not_trade_readiness"


def test_build_and_summarize_research_maturity_table() -> None:
    first = score_research_package_from_diagnostics(
        package_id="pkg_b",
        subject_id="rule_b",
        has_oos=True,
        has_placebo=True,
        has_temporal=False,
        has_data_quality=True,
        caveat_count=2,
        decision="continue_study",
    )
    second = score_research_package_from_diagnostics(
        package_id="pkg_a",
        subject_id="rule_a",
        has_oos=False,
        has_placebo=False,
        has_temporal=False,
        has_data_quality=False,
        caveat_count=8,
        decision="retire_from_review",
    )

    table = build_research_maturity_table([first, second])
    summary = summarize_research_maturity(table)

    assert table["package_id"].tolist() == ["pkg_a", "pkg_b"]
    assert summary["package_count"].sum() == 2
    assert set(summary["summary_caveat"]) == {"maturity_summary_is_research_only"}


def test_research_maturity_validates_scores_and_duplicates() -> None:
    with pytest.raises(ValueError, match="score"):
        create_research_maturity_record(
            package_id="pkg",
            subject_id="rule",
            component_scores={"evidence_completeness": 2.0},
        )
    record = score_research_package_from_diagnostics(
        package_id="same",
        subject_id="rule",
        has_oos=True,
        has_placebo=True,
        has_temporal=True,
        has_data_quality=True,
    )
    with pytest.raises(ValueError, match="duplicate"):
        build_research_maturity_table([record, record])
