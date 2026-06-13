from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from spy_edge_research.indicators import calculate_bollinger_bands


def test_bollinger_bands_use_trailing_rolling_calculations() -> None:
    df = pd.DataFrame({"close": [10.0, 12.0, 14.0, 16.0]})
    original = df.copy(deep=True)

    result = calculate_bollinger_bands(df, window=3, num_std=2.0)
    rolling = df["close"].rolling(3)
    expected_mid = rolling.mean()
    expected_std = rolling.std()
    expected_upper = expected_mid + 2.0 * expected_std
    expected_lower = expected_mid - 2.0 * expected_std
    expected_width = expected_upper - expected_lower

    assert result["bb_mid_3"].iloc[:2].isna().all()
    pd.testing.assert_series_equal(result["bb_mid_3"], expected_mid, check_names=False)
    pd.testing.assert_series_equal(result["bb_upper_3"], expected_upper, check_names=False)
    pd.testing.assert_series_equal(result["bb_lower_3"], expected_lower, check_names=False)
    pd.testing.assert_series_equal(
        result["bb_percent_b_3"],
        (df["close"] - expected_lower) / expected_width,
        check_names=False,
    )
    pd.testing.assert_frame_equal(df, original)


def test_bollinger_percent_b_is_nan_for_zero_width() -> None:
    result = calculate_bollinger_bands(pd.DataFrame({"close": [10.0, 10.0]}), window=2)

    assert np.isnan(result.loc[1, "bb_percent_b_2"])


def test_bollinger_bands_validates_inputs() -> None:
    with pytest.raises(ValueError, match="window"):
        calculate_bollinger_bands(pd.DataFrame({"close": [1.0]}), window=0)
    with pytest.raises(ValueError, match="num_std"):
        calculate_bollinger_bands(pd.DataFrame({"close": [1.0]}), num_std=0)
    with pytest.raises(ValueError, match="Missing required columns"):
        calculate_bollinger_bands(pd.DataFrame({"open": [1.0]}))
