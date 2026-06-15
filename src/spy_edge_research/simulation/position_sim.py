"""Causal position simulation over historical bars (MOD 14).

Walks the bars and opens a simulated position each time a candidate's event
signal fires, holding for the candidate's fixed horizon and closing at the
historical close that many bars later (same trading day). The entry *decision*
at bar ``t`` uses only the event column, which is computed causally from rows
``<= t``; the exit price is a known historical bar, so resolving it is causal at
evaluation time. No future row is ever used to *decide* an entry.

Reuses ``backtesting.labels`` forward-price math to resolve exits (the one place
a forward-looking column is the right tool — to close a position opened at ``t``,
not to trigger one).
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from typing import Any

import pandas as pd

from spy_edge_research.backtesting.labels import (
    add_forward_return_labels,
    horizon_to_bars,
)
from spy_edge_research.simulation.contracts import (
    SimFill,
    SimPosition,
    SimTrade,
    VALID_SIDES,
)
from spy_edge_research.simulation.cost_model import RegimeAwareCostModel
from spy_edge_research.simulation.execution_model import ExecutionModel

_DIRECTION_SIGN = {"long": 1.0, "short": -1.0}


def simulate_candidate_positions(
    df: pd.DataFrame,
    candidates: Iterable[Mapping[str, Any]],
    *,
    price_col: str = "close",
    timestamp_col: str = "timestamp",
    bar_interval_minutes: int = 1,
    timezone: str = "America/New_York",
    execution: ExecutionModel | None = None,
    cost_model: RegimeAwareCostModel | None = None,
    intraday_vol_col: str = "intraday_realized_vol_so_far",
    volatility_regime_col: str = "volatility_regime",
    sigma_scale_to_bps: float = 1.0,
) -> dict[str, Any]:
    """Simulate positions for each directional candidate; return positions+trades.

    Each candidate is a mapping with at least ``candidate_id``, ``name`` (the
    event column), ``direction`` (``long``/``short``), and ``horizon`` (e.g.
    ``"15m"``). Non-directional candidates (``neutral``/``unknown``) are skipped
    and counted, never silently dropped.

    When ``cost_model`` is supplied (M114, RESEARCH_C §4.5) the round-trip charge
    is **regime-aware and charged at point-of-fill**: each fill is priced with the
    time-of-day / VIX-regime / intraday-vol that prevailed at *its own* bar
    (``intraday_vol_col`` read at that bar, scaled by ``sigma_scale_to_bps`` into
    basis points; ``volatility_regime_col`` optional → ``normal_volatility`` when
    absent). When ``cost_model is None`` the flat :class:`ExecutionModel` charge is
    applied exactly as before (unchanged behaviour).
    """
    exec_model = execution or ExecutionModel()
    candidate_list = list(candidates)
    frame = df.reset_index(drop=True)
    if price_col not in frame.columns:
        raise ValueError(f"missing price column: {price_col}")

    horizons = _required_horizons(candidate_list)
    labeled = add_forward_return_labels(
        frame,
        horizons_minutes=horizons,
        price_col=price_col,
        timestamp_col=timestamp_col,
        bar_interval_minutes=bar_interval_minutes,
        timezone=timezone,
        prevent_cross_day=True,
    )

    positions: list[SimPosition] = []
    trades: list[SimTrade] = []
    skipped_non_directional = 0

    for candidate in candidate_list:
        side = str(candidate.get("direction"))
        if side not in VALID_SIDES:
            skipped_non_directional += 1
            continue
        event_col = str(candidate.get("name"))
        if event_col not in labeled.columns:
            continue
        horizon_minutes = _horizon_minutes(str(candidate.get("horizon")))
        bars = horizon_to_bars(horizon_minutes, bar_interval_minutes)
        future_col = f"future_close_{horizon_minutes}m"
        bps_col = f"forward_return_bps_{horizon_minutes}m"
        sign = _DIRECTION_SIGN[side]
        candidate_id = str(candidate.get("candidate_id"))

        event_mask = labeled[event_col].fillna(False).astype(bool)
        resolvable = event_mask & labeled[future_col].notna()
        for entry_idx in labeled.index[resolvable]:
            exit_idx = int(entry_idx) + bars
            entry_price = float(labeled.at[entry_idx, price_col])
            exit_price = float(labeled.at[entry_idx, future_col])
            gross_bps = sign * float(labeled.at[entry_idx, bps_col])

            if cost_model is None:
                # Unchanged flat charge: net subtracts cost + slippage; the
                # per-fill applied_cost_bps reflects only the explicit cost half.
                net_bps = exec_model.net_return_bps(gross_bps)
                entry_applied_bps = exec_model.cost_bps / 2.0
                exit_applied_bps = exec_model.cost_bps / 2.0
                trade_cost_bps = exec_model.cost_bps
            else:
                # Regime-aware, charged at point-of-fill (M114, RESEARCH_C §4.5).
                entry_applied_bps = _regime_fill_cost_bps(
                    labeled, int(entry_idx), cost_model,
                    intraday_vol_col, volatility_regime_col, timestamp_col,
                    exec_model.quantity, sigma_scale_to_bps, timezone,
                )
                exit_applied_bps = _regime_fill_cost_bps(
                    labeled, exit_idx, cost_model,
                    intraday_vol_col, volatility_regime_col, timestamp_col,
                    exec_model.quantity, sigma_scale_to_bps, timezone,
                )
                trade_cost_bps = entry_applied_bps + exit_applied_bps
                net_bps = gross_bps - trade_cost_bps
            pnl = exec_model.pnl_points(entry_price, net_bps)

            entry_fill = SimFill(
                bar_index=int(entry_idx),
                timestamp=labeled.at[entry_idx, timestamp_col],
                side=side,
                price=entry_price,
                quantity=exec_model.quantity,
                fill_kind="entry",
                applied_cost_bps=entry_applied_bps,
            )
            exit_fill = SimFill(
                bar_index=exit_idx,
                timestamp=labeled.at[exit_idx, timestamp_col],
                side=side,
                price=exit_price,
                quantity=exec_model.quantity,
                fill_kind="exit",
                applied_cost_bps=exit_applied_bps,
            )
            position_id = f"{candidate_id}#{int(entry_idx)}"
            positions.append(
                SimPosition(
                    position_id=position_id,
                    candidate_id=candidate_id,
                    side=side,
                    entry_fill=entry_fill,
                    exit_fill=exit_fill,
                )
            )
            trades.append(
                SimTrade(
                    position_id=position_id,
                    candidate_id=candidate_id,
                    side=side,
                    entry_bar=int(entry_idx),
                    exit_bar=exit_idx,
                    entry_price=entry_price,
                    exit_price=exit_price,
                    holding_bars=bars,
                    gross_return_bps=gross_bps,
                    cost_bps=trade_cost_bps,
                    net_return_bps=net_bps,
                    pnl_points=pnl,
                    exit_reason="horizon",
                )
            )

    return {
        "positions": positions,
        "trades": trades,
        "skipped_non_directional": skipped_non_directional,
        "bar_count": int(len(frame)),
    }


def _regime_fill_cost_bps(
    labeled: pd.DataFrame,
    idx: int,
    cost_model: RegimeAwareCostModel,
    intraday_vol_col: str,
    volatility_regime_col: str,
    timestamp_col: str,
    quantity: float,
    sigma_scale_to_bps: float,
    timezone: str,
) -> float:
    """One-way regime-aware cost (bps) for the fill at row ``idx``.

    Reads the intraday-vol and (optional) volatility-regime that prevailed at this
    bar — point-of-fill — so a high-vol fill is charged more than a calm one. The
    intraday-vol column is required when a cost model is in use; the regime column
    is optional (absent → ``normal_volatility``).
    """
    if intraday_vol_col not in labeled.columns:
        raise ValueError(
            f"cost_model requires the intraday-vol column {intraday_vol_col!r} in the frame"
        )
    sigma = labeled.at[idx, intraday_vol_col]
    sigma_bps = float(sigma) * float(sigma_scale_to_bps) if pd.notna(sigma) else 0.0

    regime: str | None = None
    if volatility_regime_col in labeled.columns:
        regime_value = labeled.at[idx, volatility_regime_col]
        if pd.notna(regime_value):
            regime = str(regime_value)

    return cost_model.cost_bps_at(
        labeled.at[idx, timestamp_col],
        sigma_intraday_bps=sigma_bps,
        volatility_regime=regime,
        quantity=quantity,
        timezone=timezone,
    )


def _required_horizons(candidates: Iterable[Mapping[str, Any]]) -> tuple[int, ...]:
    horizons = sorted(
        {
            _horizon_minutes(str(candidate.get("horizon")))
            for candidate in candidates
            if str(candidate.get("direction")) in VALID_SIDES
        }
    )
    return tuple(horizons) if horizons else (5,)


def _horizon_minutes(horizon: str) -> int:
    match = re.search(r"(\d+)m?$", horizon)
    if not match:
        raise ValueError(f"cannot parse horizon minutes from {horizon!r}")
    return int(match.group(1))
