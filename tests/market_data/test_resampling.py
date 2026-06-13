from __future__ import annotations

import pandas as pd

from spy_edge_research.market_data.resampling import resample_ohlcv


def five_one_minute_bars() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "timestamp": pd.date_range(
                "2024-01-02 09:31",
                periods=5,
                freq="1min",
                tz="America/New_York",
            ),
            "symbol": ["SPY"] * 5,
            "open": [100.0, 101.0, 102.0, 103.0, 104.0],
            "high": [101.0, 102.0, 103.0, 106.0, 105.0],
            "low": [99.0, 100.0, 101.0, 102.0, 103.0],
            "close": [100.5, 101.5, 102.5, 103.5, 104.5],
            "volume": [100, 200, 300, 400, 500],
        }
    )


def test_resamples_five_one_minute_bars_into_one_five_minute_bar() -> None:
    result = resample_ohlcv(five_one_minute_bars())

    assert len(result) == 1


def test_correctly_calculates_open_high_low_close_and_volume() -> None:
    result = resample_ohlcv(five_one_minute_bars())
    row = result.iloc[0]

    assert row["open"] == 100.0
    assert row["high"] == 106.0
    assert row["low"] == 99.0
    assert row["close"] == 104.5
    assert row["volume"] == 1500


def test_labels_five_minute_candle_by_close_timestamp() -> None:
    result = resample_ohlcv(five_one_minute_bars())

    assert result.loc[0, "timestamp"] == pd.Timestamp(
        "2024-01-02 09:35", tz="America/New_York"
    )


def test_drops_incomplete_candles_by_default() -> None:
    df = five_one_minute_bars().iloc[:4]

    result = resample_ohlcv(df)

    assert result.empty


def test_allows_empty_output_when_incomplete_bars_are_dropped() -> None:
    df = five_one_minute_bars().iloc[:2]

    result = resample_ohlcv(df)

    assert list(result.columns) == [
        "timestamp",
        "symbol",
        "open",
        "high",
        "low",
        "close",
        "volume",
    ]
    assert result.empty


def test_does_not_include_future_bars_in_resampled_candle() -> None:
    df = pd.concat(
        [
            five_one_minute_bars(),
            pd.DataFrame(
                {
                    "timestamp": [
                        pd.Timestamp("2024-01-02 09:36", tz="America/New_York")
                    ],
                    "symbol": ["SPY"],
                    "open": [999.0],
                    "high": [1000.0],
                    "low": [998.0],
                    "close": [999.5],
                    "volume": [9999],
                }
            ),
        ],
        ignore_index=True,
    )

    result = resample_ohlcv(df, drop_incomplete=False)

    candle_0935 = result.loc[
        result["timestamp"] == pd.Timestamp("2024-01-02 09:35", tz="America/New_York")
    ].iloc[0]
    assert candle_0935["high"] == 106.0
    assert candle_0935["close"] == 104.5
