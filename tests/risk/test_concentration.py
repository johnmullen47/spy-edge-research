from __future__ import annotations

import pandas as pd
import pytest

from spy_edge_research.risk import (
    add_exposure_columns,
    compute_group_concentration,
    summarize_concentration,
)


def test_group_concentration_shares() -> None:
    df = pd.DataFrame(
        {"instrument": ["SPY", "SPY", "QQQ"], "direction": ["long", "short", "long"]}
    )
    enriched = add_exposure_columns(df)
    conc = compute_group_concentration(enriched, group_column="instrument").set_index("instrument")
    assert conc.loc["SPY", "group_gross_exposure"] == 2.0
    assert conc.loc["QQQ", "group_gross_exposure"] == 1.0
    assert conc.loc["SPY", "share"] == pytest.approx(2 / 3)


def test_summarize_concentration_hhi() -> None:
    conc = pd.DataFrame({"group": ["x", "y"], "share": [0.75, 0.25]})
    row = summarize_concentration(conc).iloc[0]
    assert row["group_count"] == 2
    assert row["largest_group_share"] == 0.75
    assert row["herfindahl_index"] == pytest.approx(0.625)
    assert row["effective_group_count"] == pytest.approx(1 / 0.625)


def test_concentration_requires_group_column() -> None:
    with pytest.raises(ValueError, match="Missing required columns"):
        compute_group_concentration(pd.DataFrame({"gross_exposure": [1.0]}), group_column="missing")
