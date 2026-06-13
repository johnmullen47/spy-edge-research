"""Deterministic synthetic fixtures for the MOD 11 CLI/pipeline tests."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest


def _synth_ohlcv(n: int = 240, seed: int = 7) -> pd.DataFrame:
    """Two trading days of 1-minute SPY-shaped bars, fully deterministic."""
    rng = np.random.default_rng(seed)
    start = pd.Timestamp("2024-01-02 09:30:00", tz="America/New_York")
    timestamps: list[pd.Timestamp] = []
    for day in range(2):
        day_start = start + pd.Timedelta(days=day)
        timestamps.extend(day_start + pd.Timedelta(minutes=i) for i in range(n // 2))
    price = 100 + np.cumsum(rng.normal(0, 0.05, size=n))
    return pd.DataFrame(
        {
            "timestamp": pd.DatetimeIndex(timestamps),
            "symbol": "SPY",
            "open": price,
            "high": price + rng.uniform(0.01, 0.1, size=n),
            "low": price - rng.uniform(0.01, 0.1, size=n),
            "close": price,
            "volume": rng.integers(1000, 5000, size=n),
        }
    )


@pytest.fixture()
def synth_ohlcv_csv(tmp_path: Path) -> Path:
    """Write a synthetic OHLCV CSV and return its path."""
    csv_path = tmp_path / "bars.csv"
    _synth_ohlcv().to_csv(csv_path, index=False)
    return csv_path
