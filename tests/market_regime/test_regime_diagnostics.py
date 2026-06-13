from __future__ import annotations

import pandas as pd
import pytest

from spy_edge_research.market_regime import (
    regime_duration_summary,
    regime_transition_counts,
    regime_value_counts,
)


def test_regime_value_counts_counts_proportions_and_sorts() -> None:
    df = pd.DataFrame({"regime": ["A", "B", "A", "C", "A", "B"]})
    original = df.copy(deep=True)

    result = regime_value_counts(df, "regime")

    assert result["regime"].tolist() == ["A", "B", "C"]
    assert result["count"].tolist() == [3, 2, 1]
    assert result["proportion"].tolist() == pytest.approx([0.5, 1 / 3, 1 / 6])
    pd.testing.assert_frame_equal(df, original)

    with pytest.raises(ValueError, match="Missing required columns"):
        regime_value_counts(df, "missing")


def test_regime_transition_counts_counts_adjacent_transitions() -> None:
    df = pd.DataFrame({"regime": ["A", "A", "B", "A", "B", "B"]})
    original = df.copy(deep=True)

    result = regime_transition_counts(df, "regime")

    transitions = {
        (row.from_regime, row.to_regime): row.count for row in result.itertuples(index=False)
    }
    assert transitions == {("A", "A"): 1, ("A", "B"): 2, ("B", "A"): 1, ("B", "B"): 1}
    assert result.iloc[0]["count"] == 2
    pd.testing.assert_frame_equal(df, original)

    with pytest.raises(ValueError, match="Missing required columns"):
        regime_transition_counts(df, "missing")


def test_regime_duration_summary_summarizes_consecutive_runs() -> None:
    df = pd.DataFrame({"regime": ["A", "A", "B", "B", "B", "A", "C"]})
    original = df.copy(deep=True)

    result = regime_duration_summary(df, "regime")

    by_regime = result.set_index("regime")
    assert by_regime.loc["A", "n_runs"] == 2
    assert by_regime.loc["A", "average_duration_bars"] == pytest.approx(1.5)
    assert by_regime.loc["A", "median_duration_bars"] == pytest.approx(1.5)
    assert by_regime.loc["A", "max_duration_bars"] == 2
    assert by_regime.loc["B", "n_runs"] == 1
    assert by_regime.loc["B", "max_duration_bars"] == 3
    assert by_regime.loc["C", "n_runs"] == 1
    assert by_regime.loc["C", "max_duration_bars"] == 1
    pd.testing.assert_frame_equal(df, original)

    with pytest.raises(ValueError, match="Missing required columns"):
        regime_duration_summary(df, "missing")
