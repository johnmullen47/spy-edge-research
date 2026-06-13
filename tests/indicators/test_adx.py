from __future__ import annotations

import pandas as pd
import pytest

from spy_edge_research.indicators import calculate_adx


def test_adx_directional_movement_and_columns_are_causal() -> None:
    df = pd.DataFrame(
        {
            "high": [10.0, 12.0, 11.0, 13.0, 14.0],
            "low": [8.0, 9.0, 7.0, 8.0, 10.0],
            "close": [9.0, 11.0, 8.0, 12.0, 13.0],
        }
    )
    original = df.copy(deep=True)

    result = calculate_adx(df, window=2)

    assert result["plus_dm"].tolist() == [0.0, 2.0, 0.0, 2.0, 1.0]
    assert result["minus_dm"].tolist() == [0.0, 0.0, 2.0, 0.0, 0.0]
    for column in ["plus_di_2", "minus_di_2", "dx_2", "adx_2"]:
        assert column in result.columns
    assert result["plus_di_2"].iloc[0] != result["plus_di_2"].iloc[0]
    assert result["minus_di_2"].iloc[0] != result["minus_di_2"].iloc[0]
    assert result["adx_2"].iloc[:2].isna().all()
    pd.testing.assert_frame_equal(df, original)

    truncated = calculate_adx(df.iloc[:3], window=2)
    pd.testing.assert_series_equal(result["dx_2"].iloc[:3], truncated["dx_2"])


def test_adx_validates_inputs() -> None:
    with pytest.raises(ValueError, match="window"):
        calculate_adx(pd.DataFrame({"high": [1.0], "low": [1.0], "close": [1.0]}), window=0)
    with pytest.raises(ValueError, match="Missing required columns"):
        calculate_adx(pd.DataFrame({"high": [1.0]}))
