from __future__ import annotations

import pandas as pd
import pytest

from spy_edge_research.market_data.validators import validate_ohlcv_schema


def valid_ohlcv_frame() -> pd.DataFrame:
    timestamps = pd.date_range(
        "2024-01-02 09:31",
        periods=3,
        freq="1min",
        tz="America/New_York",
    )
    return pd.DataFrame(
        {
            "timestamp": timestamps,
            "symbol": ["SPY", "SPY", "SPY"],
            "open": [100.0, 101.0, 102.0],
            "high": [101.0, 102.0, 103.0],
            "low": [99.0, 100.0, 101.0],
            "close": [100.5, 101.5, 102.5],
            "volume": [1000, 1100, 1200],
        }
    )


def test_accepts_valid_ohlcv_dataframe() -> None:
    df = valid_ohlcv_frame()

    result = validate_ohlcv_schema(df)

    assert list(result.columns) == [
        "timestamp",
        "symbol",
        "open",
        "high",
        "low",
        "close",
        "volume",
    ]
    assert len(result) == 3


def test_rejects_duplicate_timestamps() -> None:
    df = valid_ohlcv_frame()
    df.loc[1, "timestamp"] = df.loc[0, "timestamp"]

    with pytest.raises(ValueError, match="Duplicate"):
        validate_ohlcv_schema(df)


def test_rejects_unsorted_timestamps() -> None:
    df = valid_ohlcv_frame().iloc[[1, 0, 2]].reset_index(drop=True)

    with pytest.raises(ValueError, match="sorted"):
        validate_ohlcv_schema(df)


def test_rejects_invalid_ohlc_relationships() -> None:
    df = valid_ohlcv_frame()
    df.loc[0, "high"] = 98.0

    with pytest.raises(ValueError, match="OHLC"):
        validate_ohlcv_schema(df)


def test_rejects_wrong_symbol() -> None:
    df = valid_ohlcv_frame()
    df.loc[1, "symbol"] = "QQQ"

    with pytest.raises(ValueError, match="symbol"):
        validate_ohlcv_schema(df)


def test_rejects_negative_volume() -> None:
    df = valid_ohlcv_frame()
    df.loc[1, "volume"] = -1

    with pytest.raises(ValueError, match="Volume"):
        validate_ohlcv_schema(df)
