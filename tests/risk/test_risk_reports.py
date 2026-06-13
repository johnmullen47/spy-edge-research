from __future__ import annotations

import json

import pandas as pd
import pytest

from spy_edge_research.risk import (
    add_exposure_columns,
    build_risk_exposure_report_bundle,
    compute_group_concentration,
    export_risk_exposure_report_bundle_to_csv,
    export_risk_exposure_report_bundle_to_json,
    summarize_exposure,
    summarize_risk_exposure_report_bundle,
    validate_risk_exposure_report_bundle,
)


def make_bundle() -> dict:
    candidates = pd.DataFrame({"instrument": ["SPY", "QQQ"], "direction": ["long", "short"]})
    exposure = summarize_exposure(candidates)
    concentration = compute_group_concentration(
        add_exposure_columns(candidates), group_column="instrument"
    )
    return build_risk_exposure_report_bundle(
        exposure_summary=exposure,
        exposure_concentration=concentration,
    )


def test_build_and_validate_bundle() -> None:
    bundle = make_bundle()
    assert "exposure_summary" in bundle["tables"]
    assert "risk_exposure_caveats" in bundle["tables"]
    validate_risk_exposure_report_bundle(bundle)

    summary = summarize_risk_exposure_report_bundle(bundle)
    assert set(summary["table_name"]) >= {
        "exposure_summary",
        "exposure_concentration",
        "risk_exposure_caveats",
    }


def test_export_csv_and_json(tmp_path) -> None:
    bundle = make_bundle()

    csv_paths = export_risk_exposure_report_bundle_to_csv(bundle, tmp_path / "csv")
    assert csv_paths["exposure_summary"].exists()
    assert csv_paths["metadata"].exists()

    json_path = export_risk_exposure_report_bundle_to_json(bundle, tmp_path / "bundle.json")
    payload = json.loads(json_path.read_text())
    assert "exposure_summary" in payload["tables"]
    assert payload["metadata"]["report_caveat"]


def test_bundle_rejects_forbidden_column() -> None:
    bad = pd.DataFrame({"allocation": [1.0]})
    with pytest.raises(ValueError, match="forbidden"):
        build_risk_exposure_report_bundle(exposure_summary=bad)
