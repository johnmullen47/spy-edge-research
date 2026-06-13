from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from spy_edge_research.backtesting import (
    build_research_package_comparison_bundle,
    build_research_package_manifest,
    compare_research_package_artifacts,
    compare_research_package_decisions,
    compare_research_package_maturity,
    create_research_package_manifest_record,
    export_research_package_comparison_bundle_to_csv,
    export_research_package_comparison_bundle_to_json,
    summarize_research_package_comparison_bundle,
)


def manifest(package_id: str, artifact_name: str) -> dict[str, object]:
    return build_research_package_manifest(
        [
            create_research_package_manifest_record(
                package_id=package_id,
                artifact_name=artifact_name,
                artifact_path=f"{artifact_name}.csv",
                artifact_type="csv",
            )
        ],
        metadata={"package_id": package_id},
    )


def test_package_comparison_tables_do_not_rank_packages() -> None:
    manifests = {"a": manifest("pkg_a", "risk"), "b": manifest("pkg_b", "traceability")}
    maturity = {
        "a": pd.DataFrame(
            {"research_maturity_score": [0.4], "maturity_band": ["early_review"]}
        ),
        "b": pd.DataFrame(
            {"research_maturity_score": [0.7], "maturity_band": ["partial_review"]}
        ),
    }
    decisions = {
        "a": pd.DataFrame({"decision": ["continue_study"], "decision_count": [2]}),
        "b": pd.DataFrame({"decision": ["needs_more_data"], "decision_count": [1]}),
    }

    artifact_table = compare_research_package_artifacts(manifests)
    maturity_table = compare_research_package_maturity(maturity)
    decision_table = compare_research_package_decisions(decisions)

    assert artifact_table["package_id"].tolist() == ["pkg_a", "pkg_b"]
    assert maturity_table["comparison_caveat"].str.contains("not_trade_readiness").all()
    assert decision_table["decision_count"].tolist() == [2, 1]
    combined_text = " ".join(
        artifact_table.astype(str).to_numpy().ravel().tolist()
        + maturity_table.astype(str).to_numpy().ravel().tolist()
        + decision_table.astype(str).to_numpy().ravel().tolist()
    )
    assert "best" not in combined_text.lower()
    assert "rank" not in combined_text.lower()


def test_package_comparison_bundle_exports(tmp_path: Path) -> None:
    bundle = build_research_package_comparison_bundle(
        manifests={"a": manifest("pkg_a", "risk")},
        maturity_tables={
            "a": pd.DataFrame(
                {"research_maturity_score": [0.4], "maturity_band": ["early_review"]}
            )
        },
        metadata={"milestone": "55"},
    )
    summary = summarize_research_package_comparison_bundle(bundle)
    csv_paths = export_research_package_comparison_bundle_to_csv(bundle, tmp_path / "csv")
    json_path = export_research_package_comparison_bundle_to_json(
        bundle,
        tmp_path / "comparison.json",
    )

    assert set(bundle["tables"]) == {
        "artifact_coverage",
        "caveat_inventory",
        "maturity_comparison",
    }
    assert summary["table_name"].tolist() == [
        "artifact_coverage",
        "caveat_inventory",
        "maturity_comparison",
    ]
    assert csv_paths["artifact_coverage"].exists()
    assert json_path.exists()
    with pytest.raises(FileExistsError, match="already exists|Refusing"):
        export_research_package_comparison_bundle_to_json(bundle, json_path)
