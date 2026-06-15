"""Regime-aware transaction-cost model (MOD 14 / M114).

The binding economic control from ``RESEARCH_C_DECISION.md`` §4.5. The flat
round-trip charge of :class:`~spy_edge_research.simulation.execution_model.ExecutionModel`
(M107) is the honest *floor*; it is also dangerous for a volatility-gated strategy
because a flat low cost **flatters** exactly the trades the signal concentrates on.
The edge in the MIM family lives on high-volatility days — and so do spreads and
slippage. Charging a constant cost there books a phantom edge. §4.5 therefore
**prohibits a flat low cost** for the economic-significance evaluation and requires:

    cost_bps(t) = half_spread_bps(t) + k * sigma_intraday_bps(t) + impact_sqrt(Q / ADV)

made **time-of-day and VIX-regime aware**, so the open/close and high-vol penalty
*co-moves* with the edge. The cost is charged **at point-of-fill**: each fill is
priced with the regime that prevailed at *its own* bar (entry-bar regime for the
entry, exit-bar regime for the exit), never a portfolio average.

This module is a pure, deterministic, research-only measurement component — no I/O,
no randomness, no trade authorization. It computes a one-way (per-fill) cost in
basis points from regime inputs known at that bar; the caller charges round-trip =
entry one-way + exit one-way.

Regime axes reuse existing project conventions:

- **Time of day** — the seven :data:`~spy_edge_research.backtesting.time_of_day.SESSION_BUCKETS`
  (``open`` and ``power_hour`` carry the widest spreads; the midday buckets the
  tightest), via :func:`~spy_edge_research.backtesting.time_of_day.assign_intraday_session_bucket`.
- **VIX regime** — there is no real VIX in the SPY 1-minute data, so the
  ``volatility_regime`` proxy (``low_volatility`` / ``normal_volatility`` /
  ``high_volatility``, per ``market_regime.classify_volatility_regime``) scales the
  spread; ``None`` is treated as ``normal_volatility`` (multiplier 1.0).
- **Intraday realized volatility** — ``sigma_intraday_bps`` is the continuous
  realized-vol term (e.g. ``intraday_realized_vol_so_far`` / ``mim_realized_vol``),
  expressed in basis points; it is the lever that makes cost co-move with the edge.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass, field

import pandas as pd

from spy_edge_research.backtesting.time_of_day import (
    SESSION_BUCKETS,
    assign_intraday_session_bucket,
)

# Default time-of-day half-spread multipliers — a U-shape over the regular session:
# widest at the open and into the close, tightest at midday. ``outside_regular``
# (pre/post-market) is the widest of all. Multiplicative on the base half-spread.
DEFAULT_TIME_OF_DAY_MULTIPLIERS: dict[str, float] = {
    "open": 1.6,
    "post_open": 1.2,
    "mid_morning": 1.0,
    "lunch": 1.1,
    "afternoon": 1.0,
    "power_hour": 1.4,
    "outside_regular": 2.0,
}

# Default VIX-regime (volatility-proxy) half-spread multipliers. High-vol regimes
# widen spreads; the high multiplier is what makes the cost co-move with a vol-gated
# edge so a phantom edge cannot survive (RESEARCH_C §4.5).
DEFAULT_VOL_REGIME_MULTIPLIERS: dict[str, float] = {
    "low_volatility": 0.8,
    "normal_volatility": 1.0,
    "high_volatility": 1.6,
}

_DEFAULT_VOL_REGIME = "normal_volatility"


@dataclass(frozen=True)
class RegimeAwareCostModel:
    """Regime-aware one-way transaction cost in basis points (RESEARCH_C §4.5).

    ``cost_bps`` returns the **one-way** (single-fill) cost. The caller charges a
    round trip as ``entry_cost + exit_cost``, each evaluated at its own bar's
    regime (point-of-fill). All coefficients are non-negative and all multipliers
    strictly positive; a degenerate all-zero configuration is allowed but is
    explicitly the prohibited "flat zero" floor, not a regime-aware cost.
    """

    base_half_spread_bps: float = 0.5  # half the quoted spread at a normal midday bar
    vol_coef_k: float = 0.10  # k: bps of slippage per bp of intraday realized vol
    impact_coef_bps: float = 0.0  # square-root market-impact coefficient (opt-in)
    adv: float = 1.0  # average daily volume used in the Q/ADV impact ratio
    time_of_day_multipliers: Mapping[str, float] = field(
        default_factory=lambda: dict(DEFAULT_TIME_OF_DAY_MULTIPLIERS)
    )
    vol_regime_multipliers: Mapping[str, float] = field(
        default_factory=lambda: dict(DEFAULT_VOL_REGIME_MULTIPLIERS)
    )

    def __post_init__(self) -> None:
        for name, value in (
            ("base_half_spread_bps", self.base_half_spread_bps),
            ("vol_coef_k", self.vol_coef_k),
            ("impact_coef_bps", self.impact_coef_bps),
        ):
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                raise ValueError(f"{name} must be numeric")
            if value < 0:
                raise ValueError(f"{name} must be >= 0")
        if not isinstance(self.adv, (int, float)) or isinstance(self.adv, bool):
            raise ValueError("adv must be numeric")
        if self.adv <= 0:
            raise ValueError("adv must be > 0")
        for label, table in (
            ("time_of_day_multipliers", self.time_of_day_multipliers),
            ("vol_regime_multipliers", self.vol_regime_multipliers),
        ):
            if not table:
                raise ValueError(f"{label} must not be empty")
            for key, mult in table.items():
                if not isinstance(mult, (int, float)) or isinstance(mult, bool):
                    raise ValueError(f"{label}[{key!r}] must be numeric")
                if mult <= 0:
                    raise ValueError(f"{label}[{key!r}] must be > 0")

    def cost_bps(
        self,
        *,
        session_bucket: str,
        sigma_intraday_bps: float,
        volatility_regime: str | None = None,
        quantity: float = 1.0,
    ) -> float:
        """One-way (per-fill) cost in bps for a fill in the given regime.

        ``session_bucket`` is one of
        :data:`~spy_edge_research.backtesting.time_of_day.SESSION_BUCKETS`;
        ``sigma_intraday_bps`` is the intraday realized volatility at the fill bar
        in basis points (negative/NaN is floored to 0); ``volatility_regime`` is the
        ``low_/normal_/high_volatility`` proxy (``None`` → normal); ``quantity`` is
        the order size feeding the ``Q/ADV`` square-root impact term.
        """
        if session_bucket not in self.time_of_day_multipliers:
            raise ValueError(
                f"unknown session_bucket {session_bucket!r}; "
                f"expected one of {sorted(self.time_of_day_multipliers)}"
            )
        regime = volatility_regime if volatility_regime is not None else _DEFAULT_VOL_REGIME
        if regime not in self.vol_regime_multipliers:
            raise ValueError(
                f"unknown volatility_regime {regime!r}; "
                f"expected one of {sorted(self.vol_regime_multipliers)} or None"
            )
        if quantity <= 0:
            raise ValueError("quantity must be > 0")

        sigma = float(sigma_intraday_bps)
        if not math.isfinite(sigma) or sigma < 0.0:
            sigma = 0.0

        tod_mult = float(self.time_of_day_multipliers[session_bucket])
        regime_mult = float(self.vol_regime_multipliers[regime])

        half_spread = self.base_half_spread_bps * tod_mult * regime_mult
        vol_term = self.vol_coef_k * sigma
        impact = self.impact_coef_bps * math.sqrt(float(quantity) / self.adv)
        return float(half_spread + vol_term + impact)

    def cost_bps_at(
        self,
        timestamp: object,
        *,
        sigma_intraday_bps: float,
        volatility_regime: str | None = None,
        quantity: float = 1.0,
        timezone: str = "America/New_York",
    ) -> float:
        """One-way cost for a fill at ``timestamp``; derives the session bucket.

        Convenience wrapper that maps a bar-close timestamp to its session bucket
        via :func:`assign_intraday_session_bucket`, then defers to :meth:`cost_bps`.
        """
        bucket = assign_intraday_session_bucket(pd.Timestamp(timestamp), timezone=timezone)
        return self.cost_bps(
            session_bucket=bucket,
            sigma_intraday_bps=sigma_intraday_bps,
            volatility_regime=volatility_regime,
            quantity=quantity,
        )


__all__ = [
    "RegimeAwareCostModel",
    "DEFAULT_TIME_OF_DAY_MULTIPLIERS",
    "DEFAULT_VOL_REGIME_MULTIPLIERS",
    "SESSION_BUCKETS",
]
