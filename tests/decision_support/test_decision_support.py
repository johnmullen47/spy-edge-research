"""Tests for the decision_support package (Phase 12)."""

from __future__ import annotations

import json

import pandas as pd
import pytest

from spy_edge_research.decision_support import (
    DECISION_SUPPORT_REPORT_CAVEAT,
    build_decision_support_records,
    build_decision_support_report_bundle,
    export_decision_support_report_bundle_to_csv,
    export_decision_support_report_bundle_to_json,
    summarize_decision_support,
    validate_decision_support_report_bundle,
)


def _candidates():
    return [
        {
            "candidate_id": "ev_a__5m",
            "direction": "long",
            "horizon": "5m",
            "sample_size": 60,
            "expectancy_difference": 0.42,
        },
        {
            "candidate_id": "ev_b__15m",
            "direction": "short",
            "horizon": "15m",
            "sample_size": 40,
            "expectancy_difference": 0.31,
        },
    ]


def _verdicts(eligible_ids):
    return pd.DataFrame(
        [
            {
                "candidate_id": cid,
                "verdict": "eligible_for_paper_consideration"
                if cid in eligible_ids
                else "not_ready",
            }
            for cid in ("ev_a__5m", "ev_b__15m")
        ]
    )


def test_only_eligible_candidates_become_review_records():
    records = build_decision_support_records(_candidates(), _verdicts({"ev_a__5m"}))
    assert list(records["candidate_id"]) == ["ev_a__5m"]
    assert bool(records.iloc[0]["requires_human_review"]) is True
    assert records.iloc[0]["review_caveat"] == DECISION_SUPPORT_REPORT_CAVEAT
    assert (records["verdict"] == "eligible_for_paper_consideration").all()


def test_no_eligible_candidates_yields_empty_records():
    records = build_decision_support_records(_candidates(), _verdicts(set()))
    assert records.empty
    summary = summarize_decision_support(records)
    assert int(summary.iloc[0]["review_candidate_count"]) == 0


def test_risk_flags_are_surfaced_on_records():
    checks = pd.DataFrame(
        [
            {"check": "max_pairwise_jaccard", "status": "exceeds_limit", "flag": "risk_overlap_too_high"},
            {"check": "max_group_share", "status": "ok", "flag": None},
        ]
    )
    records = build_decision_support_records(
        _candidates(), _verdicts({"ev_a__5m"}), exposure_limit_checks=checks
    )
    assert "risk_overlap_too_high" in records.iloc[0]["risk_flags"]


def test_bundle_validator_rejects_forbidden_column():
    bad = pd.DataFrame([{"candidate_id": "x", "order_size": 100}])
    with pytest.raises(ValueError, match="forbidden"):
        validate_decision_support_report_bundle(
            {"metadata": {"report_caveat": DECISION_SUPPORT_REPORT_CAVEAT}, "tables": {"t": bad}}
        )


def test_bundle_round_trips_to_csv_and_json(tmp_path):
    records = build_decision_support_records(_candidates(), _verdicts({"ev_a__5m", "ev_b__15m"}))
    summary = summarize_decision_support(records)
    bundle = build_decision_support_report_bundle(records=records, summary=summary)

    csv_dir = tmp_path / "ds_csv"
    written = export_decision_support_report_bundle_to_csv(bundle, csv_dir)
    assert (csv_dir / "decision_support_review.csv").exists()
    assert written["metadata"].exists()
    reloaded = pd.read_csv(csv_dir / "decision_support_review.csv")
    assert len(reloaded) == 2

    json_path = tmp_path / "ds.json"
    export_decision_support_report_bundle_to_json(bundle, json_path)
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["metadata"]["report_caveat"] == DECISION_SUPPORT_REPORT_CAVEAT
    assert len(payload["tables"]["decision_support_review"]) == 2


def test_csv_export_refuses_to_clobber(tmp_path):
    records = build_decision_support_records(_candidates(), _verdicts({"ev_a__5m"}))
    bundle = build_decision_support_report_bundle(records=records)
    out = tmp_path / "ds_csv"
    export_decision_support_report_bundle_to_csv(bundle, out)
    with pytest.raises(FileExistsError):
        export_decision_support_report_bundle_to_csv(bundle, out)
    # ...but overwrite succeeds.
    export_decision_support_report_bundle_to_csv(bundle, out, overwrite=True)
