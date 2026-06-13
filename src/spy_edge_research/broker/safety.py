"""Safety primitives for the broker layer: limits and a kill-switch.

These bind on every order submission in both the sandbox (Phase 13) and the
later live (Phase 14) adapter. They are intentionally conservative: an order is
rejected unless it clears the kill-switch and every limit. Defaults are tiny so
that a misconfiguration fails closed rather than open.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # avoid an import cycle; only needed for type hints
    from spy_edge_research.broker.order_intent import OrderIntent


class BrokerSafetyError(RuntimeError):
    """Raised when an order intent fails a kill-switch or limit check."""

    def __init__(self, violations: Sequence[str]):
        self.violations = list(violations)
        super().__init__(
            "order intent rejected by safety checks: " + ", ".join(self.violations)
        )


@dataclass(frozen=True)
class TradingLimits:
    """Hard caps applied to every order. Defaults are deliberately minimal."""

    max_order_quantity: float = 1.0
    max_open_position_quantity: float = 1.0
    max_daily_loss_points: float = 1.0


@dataclass
class KillSwitch:
    """A manual halt. When engaged, no order intent may be submitted."""

    engaged: bool = False
    reason: str | None = None

    def engage(self, reason: str | None = None) -> None:
        self.engaged = True
        self.reason = reason

    def reset(self) -> None:
        self.engaged = False
        self.reason = None


def check_order_against_limits(
    intent: "OrderIntent",
    *,
    limits: TradingLimits,
    open_position_quantity: float = 0.0,
    realized_daily_loss_points: float = 0.0,
    kill_switch: KillSwitch | None = None,
) -> list[str]:
    """Return a list of violation codes (empty == the order may proceed)."""
    violations: list[str] = []
    if kill_switch is not None and kill_switch.engaged:
        violations.append("kill_switch_engaged")
    if not intent.human_approved:
        violations.append("missing_human_approval")
    if intent.quantity <= 0:
        violations.append("non_positive_quantity")
    if intent.quantity > limits.max_order_quantity:
        violations.append("order_quantity_exceeds_limit")
    if open_position_quantity + intent.quantity > limits.max_open_position_quantity:
        violations.append("open_position_quantity_exceeds_limit")
    if realized_daily_loss_points >= limits.max_daily_loss_points:
        violations.append("daily_loss_limit_reached")
    return violations
