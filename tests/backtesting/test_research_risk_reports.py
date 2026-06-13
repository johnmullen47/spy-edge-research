from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from spy_edge_research.backtesting import (
    build_research_risk_report_bundle,
    create_research_risk_report_metadata,
    export_research_risk_report_bundle_to_csv,
    export_research_risk_report_bundle_to_json,
    summarize_research_risk_report_bundle,
    validate_research_risk_report_bundle,
)


def risk_table() -> pd.DataFrame:
    return pd.DataFrame({"risk_metric": ["placebo"], "value": [0.5]})


def test_create_research_risk_report_metadata() -> None:
    metadata = create_research_risk_report_metadata(notes="unit")

    assert metadata["created_at_utc"].endswith("+00:00")
    assert metadata["milestone"] == "49"
    assert metadata["report_caveat"] == "research_risk_report_is_diagnostic_only"
    assert metadata["notes"] == "unit"


def test_build_research_risk_report_bundle_and_summary() -> None:
    bundle = build_research_risk_report_bundle(
        placebo_risk=risk_table(),
        temporal_stability=risk_table(),
        metadata={"milestone": 49},
    )
    summary = summarize_research_risk_report_bundle(bundle)

    assert set(bundle["tables"]) == {"placebo_risk", "temporal_stability", "risk_caveats"}
    assert bundle["metadata"] == {"milestone": 49}
    assert set(summary["table_name"]) == set(bundle["tables"])
    assert "risk_report_is_research_only" in bundle["tables"]["risk_caveats"]["caveat"].tolist()


def test_research_risk_report_exports_csv_and_json(tmp_path: Path) -> None:
    bundle = build_research_risk_report_bundle(placebo_risk=risk_table(), metadata={"milestone": 49})

    written = export_research_risk_report_bundle_to_csv(bundle, tmp_path)
    json_path = export_research_risk_report_bundle_to_json(bundle, tmp_path / "risk.json")
    payload = json.loads(json_path.read_text())

    assert written["metadata"] == tmp_path / "metadata.json"
    assert (tmp_path / "placebo_risk.csv").exists()
    assert payload["metadata"] == {"milestone": 49}
    assert "risk_caveats" in payload["tables"]
    with pytest.raises(FileExistsError, match="Refusing to overwrite"):
        export_research_risk_report_bundle_to_csv(bundle, tmp_path)
    with pytest.raises(FileExistsError, match="already exists"):
        export_research_risk_report_bundle_to_json(bundle, json_path)


def test_research_risk_report_validates_inputs() -> None:
    with pytest.raises(TypeError, match="bundle must be a dict"):
        validate_research_risk_report_bundle("not-a-bundle")
    with pytest.raises(TypeError, match="must be a pandas DataFrame"):
        build_research_risk_report_bundle(placebo_risk={"bad": "table"})  # type: ignore[arg-type]
