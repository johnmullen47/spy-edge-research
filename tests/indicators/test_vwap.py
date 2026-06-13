from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from spy_edge_research.indicators import calculate_intraday_vwap


def test_intraday_vwap_resets_and_uses_cumulative_values_only() -> None:
    df = pd.DataFrame(
        {
            "timestamp": pd.to_datetime(
                [
                    "2024-01-02 09:31",
                    "2024-01-02 09:32",
                    "2024-01-03 09:31",
                    "2024-01-03 09:32",
                ]
            ).tz_localize("America/New_York"),
            "high": [12.0, 15.0, 21.0, 24.0],
            "low": [9.0, 12.0, 18.0, 21.0],
            "close": [9.0, 12.0, 21.0, 24.0],
            "volume": [100.0, 300.0, 200.0, 200.0],
        },
        index=pd.Index(["a", "b", "c", "d"], name="row"),
    )
    original = df.copy(deep=True)

    result = calculate_intraday_vwap(df)

    assert result.index.equals(df.index)
    assert result["typical_price"].tolist() == pytest.approx([10.0, 13.0, 20.0, 23.0])
    assert result["vwap"].tolist() == pytest.approx([10.0, 12.25, 20.0, 21.5])
    assert result["vwap_distance"].tolist() == pytest.approx([-1.0, -0.25, 1.0, 2.5])
    assert result["vwap_distance_pct"].tolist() == pytest.approx([-0.1, -0.25 / 12.25, 0.05, 2.5 / 21.5])
    pd.testing.assert_frame_equal(df, original)

    truncated = calculate_intraday_vwap(df.iloc[:2])
    pd.testing.assert_series_equal(result["vwap"].iloc[:2], truncated["vwap"])


def test_intraday_vwap_handles_zero_cumulative_volume() -> None:
    df = pd.DataFrame(
        {
            "timestamp": pd.date_range("2024-01-02 09:31", periods=2, freq="1min"),
            "high": [10.0, 13.0],
            "low": [10.0, 10.0],
            "close": [10.0, 13.0],
            "volume": [0.0, 100.0],
        }
    )

    result = calculate_intraday_vwap(df)

    assert np.isnan(result.loc[0, "vwap"])
    assert result.loc[1, "vwap"] == 12.0


def test_intraday_vwap_requires_columns() -> None:
    with pytest.raises(ValueError, match="Missing required columns"):
        calculate_intraday_vwap(pd.DataFrame({"close": [1.0]}))
