"""Tests for cross-sectional value/quality/momentum features (MOD 13)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from spy_edge_research.signal_engine.value_quality_momentum_features import (
    COMPOSITE_RANK,
    MOMENTUM_SCORE,
    QUALITY_SCORE,
    VALUE_SCORE,
    add_cross_sectional_factor_ranks,
    add_momentum_score,
    add_value_quality_momentum_features,
)

SYMBOLS = ["SPY", "QQQ", "IWM"]


def _frame(n: int = 60, seed: int = 1) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    df = pd.DataFrame(
        {"timestamp": pd.date_range("2024-01-02 09:30", periods=n, freq="1min", tz="America/New_York")}
    )
    for s in SYMBOLS:
        df[f"{s}_close"] = 100 + np.cumsum(rng.normal(0, 0.1, n))
    return df


def test_momentum_score_is_trailing_return():
    df = _frame()
    out = add_momentum_score(df, symbols=SYMBOLS, lookback=10)
    expected = df["SPY_close"].pct_change(10)
    pd.testing.assert_series_equal(
        out[f"SPY_{MOMENTUM_SCORE}"], expected, check_names=False
    )


def test_scores_are_causal_no_lookahead():
    # A feature at row k must not change when later rows are removed.
    df = _frame(n=60)
    full = add_value_quality_momentum_features(df, symbols=SYMBOLS)
    k = 40
    truncated = add_value_quality_momentum_features(df.iloc[: k + 1].copy(), symbols=SYMBOLS)
    for score in (MOMENTUM_SCORE, QUALITY_SCORE, VALUE_SCORE, COMPOSITE_RANK):
        full_val = full[f"SPY_{score}"].iloc[k]
        trunc_val = truncated[f"SPY_{score}"].iloc[k]
        assert full_val == pytest.approx(trunc_val, nan_ok=True)


def test_cross_sectional_rank_is_pct_rank_across_symbols():
    # Hand-built scores: SPY < IWM < QQQ at row 0 -> ranks 1/3, 1, 2/3.
    df = pd.DataFrame(
        {
            "SPY_momentum_score": [0.1],
            "QQQ_momentum_score": [0.3],
            "IWM_momentum_score": [0.2],
        }
    )
    out = add_cross_sectional_factor_ranks(df, symbols=SYMBOLS, score_name="momentum_score")
    assert out["SPY_momentum_score_xs_rank"].iloc[0] == pytest.approx(1 / 3)
    assert out["IWM_momentum_score_xs_rank"].iloc[0] == pytest.approx(2 / 3)
    assert out["QQQ_momentum_score_xs_rank"].iloc[0] == pytest.approx(1.0)


def test_composite_rank_is_mean_of_three_score_ranks():
    out = add_value_quality_momentum_features(_frame(), symbols=SYMBOLS)
    rank_cols = [f"SPY_{s}_xs_rank" for s in (MOMENTUM_SCORE, QUALITY_SCORE, VALUE_SCORE)]
    expected = out[rank_cols].mean(axis=1)
    pd.testing.assert_series_equal(out[f"SPY_{COMPOSITE_RANK}"], expected, check_names=False)


def test_missing_price_column_raises():
    df = _frame().drop(columns=["IWM_close"])
    with pytest.raises(ValueError):
        add_momentum_score(df, symbols=SYMBOLS, lookback=5)


def test_duplicate_symbols_rejected():
    with pytest.raises(ValueError, match="duplicate"):
        add_momentum_score(_frame(), symbols=["SPY", "SPY"], lookback=5)
