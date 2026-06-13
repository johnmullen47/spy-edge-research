from __future__ import annotations

import pandas as pd
import pytest

from spy_edge_research.risk import add_exposure_columns, summarize_exposure


def sample() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "candidate_id": ["a", "b", "c", "d"],
            "instrument": ["SPY", "SPY", "QQQ", "QQQ"],
            "direction": ["long", "short", "long", "neutral"],
        }
    )


def test_add_exposure_columns_signs_and_gross() -> None:
    out = add_exposure_columns(sample())
    assert out["signed_exposure"].tolist() == [1.0, -1.0, 1.0, 0.0]
    assert out["gross_exposure"].tolist() == [1.0, 1.0, 1.0, 1.0]


def test_summarize_exposure_overall() -> None:
    row = summarize_exposure(sample()).iloc[0]
    assert row["candidate_count"] == 4
    assert row["long_count"] == 2
    assert row["short_count"] == 1
    assert row["neutral_count"] == 1
    assert row["gross_exposure"] == 4.0
    assert row["net_exposure"] == 1.0
    assert row["net_exposure_abs"] == 1.0
    assert row["exposure_caveat"]


def test_summarize_exposure_grouped_by_instrument() -> None:
    grouped = summarize_exposure(sample(), group_columns=["instrument"]).set_index("instrument")
    assert grouped.loc["SPY", "gross_exposure"] == 2.0
    assert grouped.loc["SPY", "net_exposure"] == 0.0
    assert grouped.loc["QQQ", "net_exposure"] == 1.0


def test_exposure_with_weight_column() -> None:
    df = sample()
    df["weight"] = [2.0, 1.0, 3.0, 5.0]
    out = add_exposure_columns(df, weight_column="weight")
    assert out["signed_exposure"].tolist() == [2.0, -1.0, 3.0, 0.0]
    assert out["gross_exposure"].tolist() == [2.0, 1.0, 3.0, 5.0]


def test_unsupported_direction_raises() -> None:
    df = sample()
    df.loc[0, "direction"] = "sideways"
    with pytest.raises(ValueError, match="Unsupported direction"):
        add_exposure_columns(df)


def test_negative_weight_raises() -> None:
    df = sample()
    df["weight"] = [1.0, -2.0, 1.0, 1.0]
    with pytest.raises(ValueError, match="non-negative"):
        add_exposure_columns(df, weight_column="weight")
