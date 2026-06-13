from __future__ import annotations

import pandas as pd
import pytest

from spy_edge_research.market_data.loaders import load_ohlcv_csv


def test_loads_valid_csv(tmp_path) -> None:
    path = tmp_path / "spy.csv"
    path.write_text(
        "\n".join(
            [
                "timestamp,symbol,open,high,low,close,volume",
                "2024-01-02 09:31:00-05:00,SPY,100,101,99,100.5,1000",
                "2024-01-02 09:32:00-05:00,SPY,100.5,102,100,101.5,1100",
            ]
        )
    )

    result = load_ohlcv_csv(path)

    assert len(result) == 2
    assert result.loc[0, "symbol"] == "SPY"


def test_normalizes_column_names(tmp_path) -> None:
    path = tmp_path / "spy.csv"
    path.write_text(
        "\n".join(
            [
                "Timestamp,Symbol,Open,High,Low,Close,Volume",
                "2024-01-02 09:31:00-05:00,SPY,100,101,99,100.5,1000",
            ]
        )
    )

    result = load_ohlcv_csv(path)

    assert list(result.columns) == [
        "timestamp",
        "symbol",
        "open",
        "high",
        "low",
        "close",
        "volume",
    ]


def test_parses_timestamps(tmp_path) -> None:
    path = tmp_path / "spy.csv"
    path.write_text(
        "\n".join(
            [
                "timestamp,symbol,open,high,low,close,volume",
                "2024-01-02 09:31:00,SPY,100,101,99,100.5,1000",
            ]
        )
    )

    result = load_ohlcv_csv(path)

    assert isinstance(result["timestamp"].dtype, pd.DatetimeTZDtype)
    assert str(result.loc[0, "timestamp"].tzinfo) == "America/New_York"


def test_rejects_missing_columns(tmp_path) -> None:
    path = tmp_path / "spy.csv"
    path.write_text(
        "\n".join(
            [
                "timestamp,symbol,open,high,low,close",
                "2024-01-02 09:31:00-05:00,SPY,100,101,99,100.5",
            ]
        )
    )

    with pytest.raises(ValueError, match="Missing"):
        load_ohlcv_csv(path)
