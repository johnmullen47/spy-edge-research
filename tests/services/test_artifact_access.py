import json

import pandas as pd
import pytest

from spy_edge_research.services import (
    LoadedReportBundle,
    discover_report_bundles,
    load_report_bundle_csv_dir,
    load_report_bundle_json,
)


def _payload():
    return {
        "metadata": {"milestone": "74", "report_caveat": "x"},
        "tables": {
            "exposure_summary": [{"gross_exposure": 2.0, "net_exposure": 0.0}],
            "caveats": [{"caveat": "c"}],
        },
    }


def test_load_report_bundle_json(tmp_path):
    path = tmp_path / "bundle.json"
    path.write_text(json.dumps(_payload()))

    bundle = load_report_bundle_json(path)
    assert isinstance(bundle, LoadedReportBundle)
    assert bundle.metadata["milestone"] == "74"
    assert set(bundle.tables) == {"exposure_summary", "caveats"}
    assert bundle.tables["exposure_summary"].loc[0, "gross_exposure"] == 2.0


def test_load_report_bundle_json_requires_tables(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text(json.dumps({"metadata": {}}))
    with pytest.raises(KeyError, match="tables"):
        load_report_bundle_json(path)


def test_load_report_bundle_csv_dir(tmp_path):
    (tmp_path / "metadata.json").write_text(json.dumps({"milestone": "74"}))
    pd.DataFrame([{"gross_exposure": 2.0}]).to_csv(tmp_path / "exposure_summary.csv", index=False)

    bundle = load_report_bundle_csv_dir(tmp_path)
    assert bundle.metadata["milestone"] == "74"
    assert "exposure_summary" in bundle.tables


def test_load_csv_dir_requires_tables(tmp_path):
    (tmp_path / "metadata.json").write_text("{}")
    with pytest.raises(ValueError, match="no CSV tables"):
        load_report_bundle_csv_dir(tmp_path)


def test_discover_report_bundles(tmp_path):
    (tmp_path / "bundle.json").write_text(json.dumps(_payload()))
    sub = tmp_path / "csv_run"
    sub.mkdir()
    (sub / "metadata.json").write_text("{}")
    pd.DataFrame([{"a": 1}]).to_csv(sub / "table.csv", index=False)

    discovered = discover_report_bundles(tmp_path)
    assert set(discovered["kind"]) == {"json", "csv_dir"}
    assert discovered.loc[discovered["kind"] == "json", "table_count"].iloc[0] == 2
