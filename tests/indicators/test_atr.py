from __future__ import annotations

import pandas as pd
import pytest

from spy_edge_research.indicators import calculate_atr


def test_atr_true_range_handles_gaps_and_uses_trailing_mean() -> None:
    df = pd.DataFrame(
        {
            "high": [11.0, 15.0, 14.0, 18.0],
            "low": [9.0, 13.0, 10.0, 17.0],
            "close": [10.0, 14.0, 11.0, 17.5],
        }
    )
    original = df.copy(deep=True)

    result = calculate_atr(df, window=3)

    assert result["true_range"].tolist() == [2.0, 5.0, 4.0, 7.0]
    assert result["atr_3"].iloc[:2].isna().all()
    assert result["atr_3"].tolist()[2:] == pytest.approx([11.0 / 3.0, 16.0 / 3.0])
    assert result["atr_3_pct"].iloc[2] == pytest.approx((11.0 / 3.0) / 11.0)
    pd.testing.assert_frame_equal(df, original)


def test_atr_validates_inputs() -> None:
    with pytest.raises(ValueError, match="window"):
        calculate_atr(pd.DataFrame({"high": [1.0], "low": [1.0], "close": [1.0]}), window=0)
    with pytest.raises(ValueError, match="Missing required columns"):
        calculate_atr(pd.DataFrame({"high": [1.0]}))
