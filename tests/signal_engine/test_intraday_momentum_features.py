"""Tests for the regime-conditioned intraday-momentum signal family (M110)."""

import numpy as np
import pandas as pd
import pytest

from spy_edge_research.signal_engine import (
    add_intraday_momentum_features,
    find_intraday_momentum_event_columns,
)
from spy_edge_research.signal_engine.intraday_momentum_features import (
    VOL_REGIME_HIGH,
    VOL_REGIME_NORMAL,
    VOL_REGIME_UNKNOWN,
)


def _day_bars(date: pd.Timestamp, *, drift_per_bar: float, vol: float, seed: int):
    """One day of 1-min bars 09:30–10:30 with a controlled open->10:00 drift/vol."""
    times = pd.date_range(
        date + pd.Timedelta("9:30:00"), date + pd.Timedelta("10:30:00"), freq="1min"
    )
    rng = np.random.default_rng(seed)
    rets = drift_per_bar + rng.normal(0.0, vol, size=len(times))
    rets[0] = 0.0  # first bar anchors the session open at 100
    prices = 100.0 * np.cumprod(1.0 + rets)
    close = pd.Series(prices, index=times)
    open_ = close.shift(1)
    open_.iloc[0] = 100.0
    return pd.DataFrame(
        {
            "timestamp": times,
            "open": open_.to_numpy(),
            "high": np.maximum(open_.to_numpy(), close.to_numpy()),
            "low": np.minimum(open_.to_numpy(), close.to_numpy()),
            "close": close.to_numpy(),
            "volume": 1000.0,
        }
    )


def _frame(specs):
    """specs: list of (drift_per_bar, vol). One trading day per spec."""
    start = pd.Timestamp("2024-01-02")
    frames = [
        _day_bars(start + pd.Timedelta(days=i), drift_per_bar=d, vol=v, seed=100 + i)
        for i, (d, v) in enumerate(specs)
    ]
    return pd.concat(frames, ignore_index=True)


def test_one_decision_bar_per_day_at_window_end():
    df = _frame([(0.0001, 0.0003)] * 4)
    out = add_intraday_momentum_features(df)
    assert int(out["mim_decision_bar"].sum()) == 4
    decision = out[out["mim_decision_bar"]]
    local = pd.to_datetime(decision["timestamp"]).dt.tz_localize("America/New_York")
    assert (local.dt.hour == 10).all()
    assert (local.dt.minute == 0).all()


def test_open_return_value_is_causal_open_to_window_end():
    df = _frame([(0.0002, 0.0001)])
    out = add_intraday_momentum_features(df)
    row = out[out["mim_decision_bar"]].iloc[0]
    # close at 10:00 (bar index 30 within the day) over the 100.0 session open.
    close_at_1000 = df.iloc[30]["close"]
    assert row["mim_open_return"] == pytest.approx(close_at_1000 / 100.0 - 1.0)
    # Off-decision bars carry no decision value.
    assert out.loc[~out["mim_decision_bar"], "mim_open_return"].isna().all()


def test_threshold_is_unknown_until_lookback_history_exists():
    df = _frame([(0.0001, 0.0003)] * 6)
    out = add_intraday_momentum_features(df, realized_vol_lookback_days=3)
    decision = out[out["mim_decision_bar"]].reset_index(drop=True)
    # First 3 sessions have no full trailing window -> threshold NaN -> unknown.
    assert decision.loc[:2, "mim_vol_threshold"].isna().all()
    assert (decision.loc[:2, "mim_vol_regime"] == VOL_REGIME_UNKNOWN).all()
    # Later sessions get a threshold and a high/normal label.
    assert decision.loc[3:, "mim_vol_threshold"].notna().all()
    assert decision.loc[3:, "mim_vol_regime"].isin(
        [VOL_REGIME_HIGH, VOL_REGIME_NORMAL]
    ).all()


def test_high_vol_day_is_flagged_after_calm_history():
    # Five calm sessions then one clearly high-vol session.
    specs = [(0.0001, 0.0002)] * 5 + [(0.0001, 0.0030)]
    df = _frame(specs)
    out = add_intraday_momentum_features(df, realized_vol_lookback_days=5)
    decision = out[out["mim_decision_bar"]].reset_index(drop=True)
    last = decision.iloc[-1]
    assert last["mim_realized_vol"] >= last["mim_vol_threshold"]
    assert last["mim_vol_regime"] == VOL_REGIME_HIGH
    assert bool(last["mim_high_vol_regime"]) is True


def test_event_columns_gate_and_only_fire_on_decision_bars():
    specs = [(0.0001, 0.0002)] * 5 + [(0.0005, 0.0030), (-0.0005, 0.0030)]
    df = _frame(specs)
    out = add_intraday_momentum_features(df, realized_vol_lookback_days=5)
    cols = find_intraday_momentum_event_columns(out)
    assert cols == [
        "event_mim_long",
        "event_mim_long_all",
        "event_mim_short",
        "event_mim_short_all",
    ]
    # Events never fire off the decision bar.
    off = out.loc[~out["mim_decision_bar"], cols]
    assert not off.to_numpy().any()
    # Gated long implies the ungated long AND the high-vol regime.
    assert (out["event_mim_long"] <= out["event_mim_long_all"]).all()
    fired = out[out["event_mim_long"]]
    if not fired.empty:
        assert fired["mim_high_vol_regime"].all()
        assert (fired["mim_open_return"] > 0).all()
    # Long and short are mutually exclusive.
    assert not (out["event_mim_long_all"] & out["event_mim_short_all"]).any()


def test_long_and_short_split_by_open_return_sign():
    df = _frame([(0.0008, 0.0001), (-0.0008, 0.0001)])
    out = add_intraday_momentum_features(df, realized_vol_lookback_days=1)
    # With lookback=1 every session after the first gets a threshold; the second
    # day has a negative drift -> short baseline fires, long does not.
    second = out[out["mim_decision_bar"]].iloc[1]
    assert second["mim_open_return"] < 0
    assert bool(out.loc[out["mim_decision_bar"], "event_mim_short_all"].iloc[1]) is True
    assert bool(out.loc[out["mim_decision_bar"], "event_mim_long_all"].iloc[1]) is False


def test_validation_errors():
    df = _frame([(0.0001, 0.0003)])
    with pytest.raises(ValueError, match="Missing required columns"):
        add_intraday_momentum_features(df.drop(columns=["close"]))
    with pytest.raises(ValueError, match="high_vol_quantile"):
        add_intraday_momentum_features(df, high_vol_quantile=1.5)
    with pytest.raises(ValueError, match="realized_vol_lookback_days"):
        add_intraday_momentum_features(df, realized_vol_lookback_days=0)
    with pytest.raises(ValueError, match="clock"):
        add_intraday_momentum_features(df, momentum_window_end="bad")
    with pytest.raises(ValueError, match="clock boundaries"):
        add_intraday_momentum_features(
            df, session_open="10:00", momentum_window_end="09:30"
        )
