import json
from pathlib import Path

import pandas as pd
import pytest

from spy_edge_research.paper import (
    build_readiness_report_bundle,
    create_readiness_report_metadata,
    export_readiness_report_bundle_to_csv,
    export_readiness_report_bundle_to_json,
    score_candidate_readiness,
    summarize_readiness_report_bundle,
    summarize_readiness_verdict,
    validate_readiness_report_bundle,
)


def _scorecard_and_verdict():
    metrics = {
        "oos_positive_expectancy_difference_splits": 3,
        "oos_mean_sample_size": 50.0,
        "negative_control_passed": True,
        "multiple_testing_passed": True,
        "temporal_stable_period_count": 3,
        "max_pairwise_jaccard": 0.5,
    }
    scorecard = score_candidate_readiness(metrics)
    return scorecard, summarize_readiness_verdict(scorecard)


def test_create_metadata_includes_research_caveat():
    metadata = create_readiness_report_metadata(package_name="readiness_run_001")
    assert metadata["milestone"] == "92"
    assert metadata["report_caveat"] == "readiness_report_is_research_gate_not_trade_authorization"


def test_build_and_validate_bundle():
    scorecard, verdict = _scorecard_and_verdict()
    bundle = build_readiness_report_bundle(scorecard=scorecard, verdict=verdict)
    assert set(bundle["tables"]) == {"readiness_scorecard", "readiness_verdict", "readiness_caveats"}
    validate_readiness_report_bundle(bundle)
    summary = summarize_readiness_report_bundle(bundle)
    assert "readiness_verdict" in summary["table_name"].tolist()


def test_export_csv_and_json(tmp_path: Path):
    scorecard, verdict = _scorecard_and_verdict()
    bundle = build_readiness_report_bundle(scorecard=scorecard, verdict=verdict)

    written = export_readiness_report_bundle_to_csv(bundle, tmp_path)
    assert (tmp_path / "readiness_scorecard.csv").exists()
    assert written["metadata"] == tmp_path / "metadata.json"

    json_path = export_readiness_report_bundle_to_json(bundle, tmp_path / "readiness.json")
    payload = json.loads(json_path.read_text())
    assert "readiness_verdict" in payload["tables"]
    with pytest.raises(FileExistsError):
        export_readiness_report_bundle_to_json(bundle, tmp_path / "readiness.json")


def test_metadata_rejects_forbidden_fields():
    scorecard, verdict = _scorecard_and_verdict()
    with pytest.raises(ValueError, match="forbidden"):
        build_readiness_report_bundle(
            scorecard=scorecard,
            verdict=verdict,
            metadata={"allocation_notes": "not allowed"},
        )
