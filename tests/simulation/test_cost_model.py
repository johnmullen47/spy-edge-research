"""Tests for the regime-aware transaction-cost model (M114, RESEARCH_C §4.5)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from spy_edge_research.simulation import (
    ExecutionModel,
    RegimeAwareCostModel,
    simulate_candidate_positions,
)


# --------------------------------------------------------------------------- #
# Unit tests — the pure cost component
# --------------------------------------------------------------------------- #


def test_cost_increases_monotonically_with_intraday_vol():
    # The binding §4.5 property: cost MUST co-move with realized vol so a vol-gated
    # edge cannot book a phantom profit. A flat cost would violate this.
    model = RegimeAwareCostModel(base_half_spread_bps=1.0, vol_coef_k=0.5)
    costs = [
        model.cost_bps(session_bucket="mid_morning", sigma_intraday_bps=s)
        for s in (0.0, 1.0, 5.0, 20.0)
    ]
    assert costs == sorted(costs)
    assert costs[0] < costs[-1]
    # The vol term is exactly k * sigma above the half-spread floor.
    assert costs[1] - costs[0] == pytest.approx(0.5, abs=1e-12)


def test_time_of_day_is_u_shaped():
    model = RegimeAwareCostModel(base_half_spread_bps=1.0, vol_coef_k=0.0)
    open_c = model.cost_bps(session_bucket="open", sigma_intraday_bps=0.0)
    mid_c = model.cost_bps(session_bucket="mid_morning", sigma_intraday_bps=0.0)
    power_c = model.cost_bps(session_bucket="power_hour", sigma_intraday_bps=0.0)
    afternoon_c = model.cost_bps(session_bucket="afternoon", sigma_intraday_bps=0.0)
    outside_c = model.cost_bps(session_bucket="outside_regular", sigma_intraday_bps=0.0)
    assert open_c > mid_c  # open is dearer than midday
    assert power_c > afternoon_c  # into-the-close is dearer than mid-afternoon
    assert outside_c > open_c  # pre/post-market widest of all


def test_vix_regime_widens_spread_monotonically():
    model = RegimeAwareCostModel(base_half_spread_bps=1.0, vol_coef_k=0.0)
    low = model.cost_bps(session_bucket="lunch", sigma_intraday_bps=0.0, volatility_regime="low_volatility")
    normal = model.cost_bps(session_bucket="lunch", sigma_intraday_bps=0.0, volatility_regime="normal_volatility")
    high = model.cost_bps(session_bucket="lunch", sigma_intraday_bps=0.0, volatility_regime="high_volatility")
    assert low < normal < high


def test_none_regime_is_normal():
    model = RegimeAwareCostModel(vol_coef_k=0.0)
    none_c = model.cost_bps(session_bucket="lunch", sigma_intraday_bps=0.0, volatility_regime=None)
    normal_c = model.cost_bps(session_bucket="lunch", sigma_intraday_bps=0.0, volatility_regime="normal_volatility")
    assert none_c == pytest.approx(normal_c, abs=1e-12)


def test_square_root_market_impact():
    # With the spread and vol terms zeroed, only the sqrt(Q/ADV) impact remains;
    # quadrupling size should exactly double the impact cost.
    model = RegimeAwareCostModel(base_half_spread_bps=0.0, vol_coef_k=0.0, impact_coef_bps=3.0, adv=100.0)
    c1 = model.cost_bps(session_bucket="lunch", sigma_intraday_bps=0.0, quantity=1.0)
    c4 = model.cost_bps(session_bucket="lunch", sigma_intraday_bps=0.0, quantity=4.0)
    assert c1 == pytest.approx(3.0 * np.sqrt(1.0 / 100.0), abs=1e-12)
    assert c4 == pytest.approx(2.0 * c1, abs=1e-12)


def test_negative_or_nan_sigma_floored_to_zero():
    model = RegimeAwareCostModel(base_half_spread_bps=1.0, vol_coef_k=0.5)
    floor = model.cost_bps(session_bucket="lunch", sigma_intraday_bps=0.0)
    assert model.cost_bps(session_bucket="lunch", sigma_intraday_bps=-5.0) == pytest.approx(floor)
    assert model.cost_bps(session_bucket="lunch", sigma_intraday_bps=float("nan")) == pytest.approx(floor)


def test_cost_bps_at_derives_session_bucket_from_timestamp():
    model = RegimeAwareCostModel(base_half_spread_bps=1.0, vol_coef_k=0.0)
    open_ts = pd.Timestamp("2024-01-02 09:45", tz="America/New_York")
    lunch_ts = pd.Timestamp("2024-01-02 12:30", tz="America/New_York")
    assert model.cost_bps_at(open_ts, sigma_intraday_bps=0.0) == pytest.approx(
        model.cost_bps(session_bucket="open", sigma_intraday_bps=0.0)
    )
    assert model.cost_bps_at(lunch_ts, sigma_intraday_bps=0.0) == pytest.approx(
        model.cost_bps(session_bucket="lunch", sigma_intraday_bps=0.0)
    )


def test_unknown_bucket_and_regime_raise():
    model = RegimeAwareCostModel()
    with pytest.raises(ValueError, match="session_bucket"):
        model.cost_bps(session_bucket="nope", sigma_intraday_bps=0.0)
    with pytest.raises(ValueError, match="volatility_regime"):
        model.cost_bps(session_bucket="lunch", sigma_intraday_bps=0.0, volatility_regime="extreme")
    with pytest.raises(ValueError, match="quantity"):
        model.cost_bps(session_bucket="lunch", sigma_intraday_bps=0.0, quantity=0.0)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"base_half_spread_bps": -1.0},
        {"vol_coef_k": -0.1},
        {"impact_coef_bps": -2.0},
        {"adv": 0.0},
        {"vol_coef_k": True},  # bool is not an acceptable numeric
        {"time_of_day_multipliers": {"open": 0.0}},
        {"vol_regime_multipliers": {}},
    ],
)
def test_invalid_configuration_rejected(kwargs):
    with pytest.raises(ValueError):
        RegimeAwareCostModel(**kwargs)


# --------------------------------------------------------------------------- #
# Integration tests — charged at point-of-fill through the simulator
# --------------------------------------------------------------------------- #


def _open_session_frame(sigma_bps: float, *, regime: str = "normal_volatility", n: int = 12) -> pd.DataFrame:
    """One day of bars wholly inside the 'open' bucket, with vol + regime columns."""
    timestamps = [
        pd.Timestamp("2024-01-02 09:31", tz="America/New_York") + pd.Timedelta(minutes=i)
        for i in range(n)
    ]
    price = pd.Series(100.0 + np.arange(n) * 0.10)
    df = pd.DataFrame(
        {
            "timestamp": timestamps,
            "symbol": "SPY",
            "open": price,
            "high": price + 0.05,
            "low": price - 0.05,
            "close": price,
            "volume": 1000,
            "intraday_realized_vol_so_far": float(sigma_bps),
            "volatility_regime": regime,
        }
    )
    df["event_long"] = 0
    df.loc[[2], "event_long"] = 1
    return df


_LONG = [{"candidate_id": "c_long_5m", "name": "event_long", "direction": "long", "horizon": "5m"}]


def test_regime_cost_charged_at_point_of_fill_exact_value():
    # base 1.0 * open 1.6 * normal 1.0 = 1.6 half-spread; vol term 0.5*2.0 = 1.0;
    # one-way 2.6, round trip (entry+exit, both 'open', same sigma) = 5.2.
    model = RegimeAwareCostModel(base_half_spread_bps=1.0, vol_coef_k=0.5)
    sim = simulate_candidate_positions(
        _open_session_frame(2.0), _LONG, execution=ExecutionModel(cost_bps=99.0), cost_model=model
    )
    trade = sim["trades"][0]
    assert trade.cost_bps == pytest.approx(5.2, abs=1e-9)  # NOT the flat 99.0
    assert trade.net_return_bps == pytest.approx(trade.gross_return_bps - 5.2, abs=1e-9)
    assert trade.entry_bar == 2 and trade.exit_bar == 7


def test_high_vol_fill_costs_more_than_calm_fill():
    model = RegimeAwareCostModel(base_half_spread_bps=1.0, vol_coef_k=0.5)
    calm = simulate_candidate_positions(_open_session_frame(2.0), _LONG, cost_model=model)["trades"][0]
    stormy = simulate_candidate_positions(_open_session_frame(40.0), _LONG, cost_model=model)["trades"][0]
    assert stormy.cost_bps > calm.cost_bps
    # Same gross edge, strictly lower net on the high-vol day — the §4.5 co-movement.
    assert stormy.gross_return_bps == pytest.approx(calm.gross_return_bps, abs=1e-9)
    assert stormy.net_return_bps < calm.net_return_bps


def test_regime_cost_can_zero_a_gross_positive_edge():
    # A gross-positive trade goes net-negative once the high-vol regime cost exceeds it.
    model = RegimeAwareCostModel(base_half_spread_bps=2.0, vol_coef_k=1.0)
    trade = simulate_candidate_positions(
        _open_session_frame(60.0, regime="high_volatility"), _LONG, cost_model=model
    )["trades"][0]
    assert trade.gross_return_bps > 0
    assert trade.net_return_bps < 0


def test_cost_model_none_preserves_flat_behaviour():
    frame = _open_session_frame(40.0)
    flat = simulate_candidate_positions(frame, _LONG, execution=ExecutionModel(cost_bps=2.0))["trades"][0]
    assert flat.cost_bps == pytest.approx(2.0, abs=1e-12)
    assert flat.net_return_bps == pytest.approx(flat.gross_return_bps - 2.0, abs=1e-12)


def test_missing_intraday_vol_column_raises_when_cost_model_supplied():
    frame = _open_session_frame(2.0).drop(columns=["intraday_realized_vol_so_far"])
    with pytest.raises(ValueError, match="intraday-vol column"):
        simulate_candidate_positions(frame, _LONG, cost_model=RegimeAwareCostModel())


def test_sigma_scale_to_bps_converts_fractional_vol():
    # If the vol column carries a return fraction (0.0002 = 2 bps), the caller
    # scales it; the charged cost then matches a 2-bp sigma.
    model = RegimeAwareCostModel(base_half_spread_bps=1.0, vol_coef_k=0.5)
    scaled = simulate_candidate_positions(
        _open_session_frame(0.0002), _LONG, cost_model=model, sigma_scale_to_bps=10_000.0
    )["trades"][0]
    direct = simulate_candidate_positions(_open_session_frame(2.0), _LONG, cost_model=model)["trades"][0]
    assert scaled.cost_bps == pytest.approx(direct.cost_bps, abs=1e-9)
