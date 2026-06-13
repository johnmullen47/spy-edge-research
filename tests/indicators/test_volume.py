from __future__ import annotations

import pandas as pd
import pytest

from spy_edge_research.indicators import calculate_volume_features


def test_volume_features_are_trailing_and_intraday_mean_resets() -> None:
    df = pd.DataFrame(
        {
            "timestamp": pd.to_datetime(
                [
                    "2024-01-02 09:31",
                    "2024-01-02 09:32",
                    "2024-01-02 09:33",
                    "2024-01-03 09:31",
                    "2024-01-03 09:32",
                ]
            ).tz_localize("America/New_York"),
            "volume": [100.0, 200.0, 400.0, 50.0, 150.0],
        },
        index=pd.Index([10, 11, 12, 13, 14], name="row"),
    )
    original = df.copy(deep=True)

    result = calculate_volume_features(df, window=3)
    expected_sma = df["volume"].rolling(3).mean()
    expected_zscore = (df["volume"] - expected_sma) / df["volume"].rolling(3).std()

    assert result.index.equals(df.index)
    pd.testing.assert_series_equal(result["volume_sma_3"], expected_sma, check_names=False)
    pd.testing.assert_series_equal(
        result["relative_volume_3"], df["volume"] / expected_sma, check_names=False
    )
    pd.testing.assert_series_equal(result["volume_zscore_3"], expected_zscore, check_names=False)
    assert result["volume_expanding_intraday_mean"].tolist() == pytest.approx(
        [100.0, 150.0, 700.0 / 3.0, 50.0, 100.0]
    )
    pd.testing.assert_frame_equal(df, original)

    truncated = calculate_volume_features(df.iloc[:3], window=3)
    pd.testing.assert_series_equal(
        result["volume_expanding_intraday_mean"].iloc[:3],
        truncated["volume_expanding_intraday_mean"],
    )


def test_volume_features_validates_inputs() -> None:
    with pytest.raises(ValueError, match="window"):
        calculate_volume_features(
            pd.DataFrame({"timestamp": [pd.Timestamp("2024-01-02")], "volume": [1.0]}),
            window=0,
        )
    with pytest.raises(ValueError, match="Missing required columns"):
        calculate_volume_features(pd.DataFrame({"volume": [1.0]}))
