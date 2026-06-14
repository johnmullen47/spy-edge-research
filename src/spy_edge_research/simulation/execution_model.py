"""Deterministic execution assumptions for the simulation layer (MOD 14).

A single, explicit, deterministic fill model: entries and exits fill at the bar
close, and a round-trip *cost* plus a round-trip *slippage* charge (both in basis
points) are subtracted from the gross return. The two are kept separate so the
research caveats are honest about what each represents:

- ``cost_bps`` — commissions / fees (the broker's explicit charge).
- ``slippage_bps`` — market-impact / spread cost: the gap between the bar close
  the simulator fills at and the price a real order would actually achieve.

There is still no randomness or per-fill slippage *distribution* — this is a flat,
conservative round-trip assumption, stated plainly so results are reproducible and
auditable. A dynamic (volatility/volume-scaled) slippage model could extend this
later; the flat charge is the honest floor.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ExecutionModel:
    """Deterministic fill/cost/slippage assumptions for the position simulator."""

    cost_bps: float = 1.0  # round-trip commissions/fees charged against gross return
    slippage_bps: float = 0.0  # round-trip market-impact/spread cost
    quantity: float = 1.0  # fixed unit size; this layer does not size positions

    def __post_init__(self) -> None:
        if self.cost_bps < 0:
            raise ValueError("cost_bps must be >= 0")
        if self.slippage_bps < 0:
            raise ValueError("slippage_bps must be >= 0")
        if self.quantity <= 0:
            raise ValueError("quantity must be > 0")

    @property
    def total_cost_bps(self) -> float:
        """Total round-trip drag charged against gross return (cost + slippage)."""
        return self.cost_bps + self.slippage_bps

    def net_return_bps(self, gross_return_bps: float) -> float:
        """Apply the round-trip cost and slippage to a gross return (in bps)."""
        return float(gross_return_bps) - self.total_cost_bps

    def pnl_points(self, entry_price: float, net_return_bps: float) -> float:
        """Convert a net return (bps) on one unit into price-points P&L."""
        return float(entry_price) * (net_return_bps / 10_000.0) * self.quantity
