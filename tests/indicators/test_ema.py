from __future__ import annotations

import pandas as pd
import pytest

from spy_edge_research.indicators import calculate_ema


def test_calculate_ema_matches_pandas_and_adds_distance_fields() -> None:
    df = pd.DataFrame({"close": [10.0, 12.0, 14.0, 13.0]})
    original = df.copy(deep=True)

    result = calculate_ema(df, span=3)
    expected_ema = df["close"].ewm(span=3, adjust=False).mean()

    pd.testing.assert_series_equal(result["ema_3"], expected_ema, check_names=False)
    pd.testing.assert_series_equal(result["ema_3_slope"], expected_ema.diff(), check_names=False)
    pd.testing.assert_series_equal(
        result["ema_3_distance"], df["close"] - expected_ema, check_names=False
    )
    pd.testing.assert_series_equal(
        result["ema_3_distance_pct"],
        (df["close"] - expected_ema) / expected_ema,
        check_names=False,
    )
    pd.testing.assert_frame_equal(df, original)


def test_calculate_ema_validates_inputs() -> None:
    with pytest.raises(ValueError, match="span"):
        calculate_ema(pd.DataFrame({"close": [1.0]}), span=0)
    with pytest.raises(ValueError, match="Missing required columns"):
        calculate_ema(pd.DataFrame({"open": [1.0]}))
