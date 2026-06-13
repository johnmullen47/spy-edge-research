from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from spy_edge_research.backtesting import (
    build_research_review_workflow_outputs,
    create_research_review_metadata,
    export_research_review_workflow_outputs,
    summarize_research_review_workflow_outputs,
)


def tables() -> dict[str, pd.DataFrame]:
    return {
        "risk_summary": pd.DataFrame({"metric": ["placebo"], "value": [0.5]}),
        "decision_summary": pd.DataFrame({"decision": ["continue_study"], "count": [1]}),
    }


def test_create_research_review_metadata() -> None:
    metadata = create_research_review_metadata(notes="unit")

    assert metadata["created_at_utc"].endswith("+00:00")
    assert metadata["milestone"] == "53"
    assert metadata["workflow_caveat"] == "research_review_workflow_is_not_strategy_execution"
    assert metadata["notes"] == "unit"


def test_build_and_summarize_research_review_workflow_outputs() -> None:
    outputs = build_research_review_workflow_outputs(
        package_id="pkg_a",
        tables=tables(),
        metadata={"milestone": 53},
    )
    summary = summarize_research_review_workflow_outputs(outputs)

    assert outputs["metadata"] == {"milestone": 53}
    assert len(outputs["manifest"]["artifacts"]) == 2
    assert set(summary["table_name"]) == {"risk_summary", "decision_summary"}


def test_export_research_review_workflow_outputs(tmp_path: Path) -> None:
    outputs = build_research_review_workflow_outputs(package_id="pkg_a", tables=tables())

    written = export_research_review_workflow_outputs(outputs, tmp_path)

    assert (tmp_path / "risk_summary.csv").exists()
    assert written["manifest"] == tmp_path / "research_package_manifest.json"
    with pytest.raises(FileExistsError, match="Refusing to overwrite"):
        export_research_review_workflow_outputs(outputs, tmp_path)


def test_research_review_workflow_validates_inputs() -> None:
    with pytest.raises(ValueError, match="package_id"):
        build_research_review_workflow_outputs(package_id="", tables=tables())
    with pytest.raises(TypeError, match="must be a pandas DataFrame"):
        build_research_review_workflow_outputs(package_id="pkg", tables={"bad": []})  # type: ignore[dict-item]
    with pytest.raises(KeyError, match="tables"):
        summarize_research_review_workflow_outputs({"metadata": {}})
