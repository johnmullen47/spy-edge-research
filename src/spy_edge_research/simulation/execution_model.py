"""Deterministic execution assumptions for the simulation layer (MOD 14).

A single, explicit, deterministic fill model: entries and exits fill at the bar
close, and a round-trip cost (in basis points) is charged against the gross
return. There is no randomness, no slippage distribution, and no broker — these
are research assumptions for a *simulation*, stated plainly so results are
reproducible and auditable.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ExecutionModel:
    """Deterministic fill/cost assumptions for the position simulator."""

    cost_bps: float = 1.0  # round-trip cost charged against gross return
    quantity: float = 1.0  # fixed unit size; this layer does not size positions

    def __post_init__(self) -> None:
        if self.cost_bps < 0:
            raise ValueError("cost_bps must be >= 0")
        if self.quantity <= 0:
            raise ValueError("quantity must be > 0")

    def net_return_bps(self, gross_return_bps: float) -> float:
        """Apply the round-trip cost to a gross directional return (in bps)."""
        return float(gross_return_bps) - self.cost_bps

    def pnl_points(self, entry_price: float, net_return_bps: float) -> float:
        """Convert a net return (bps) on one unit into price-points P&L."""
        return float(entry_price) * (net_return_bps / 10_000.0) * self.quantity
