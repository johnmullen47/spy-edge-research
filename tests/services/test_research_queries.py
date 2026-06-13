import pandas as pd
import pytest

from spy_edge_research.services import (
    LoadedReportBundle,
    filter_bundle_table,
    get_bundle_table,
    list_bundle_tables,
    summarize_bundles,
)


def _bundle():
    return LoadedReportBundle(
        metadata={"milestone": "74", "report_caveat": "x"},
        tables={
            "t1": pd.DataFrame({"k": ["a", "b", "a"], "v": [1, 2, 3]}),
            "t2": pd.DataFrame({"x": [1]}),
        },
        source_path="mem",
    )


def test_list_bundle_tables():
    out = list_bundle_tables(_bundle()).set_index("table_name")
    assert out.loc["t1", "row_count"] == 3
    assert out.loc["t2", "column_count"] == 1


def test_get_and_filter_table():
    bundle = _bundle()
    assert len(get_bundle_table(bundle, "t1")) == 3
    filtered = filter_bundle_table(bundle, "t1", "k", "a")
    assert len(filtered) == 2
    with pytest.raises(KeyError):
        get_bundle_table(bundle, "missing")
    with pytest.raises(KeyError):
        filter_bundle_table(bundle, "t1", "missing", "a")


def test_summarize_bundles():
    row = summarize_bundles([_bundle()]).iloc[0]
    assert row["table_count"] == 2
    assert row["total_rows"] == 4
    assert row["milestone"] == "74"
