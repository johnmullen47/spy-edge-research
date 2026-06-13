"""Typed order intent built only from a human-approved decision-support record.

An ``OrderIntent`` is the boundary object between the research/decision tier and
the broker. It is NOT itself an order: in the sandbox adapter it produces a
dry-run record against Alpaca's paper endpoint, and in the later live adapter it
can only be submitted behind an explicit env flag plus per-order human approval.
An intent can only be constructed from a decision-support review record that a
human has explicitly approved — it is never auto-derived from a candidate.

This module lives inside the authorized broker boundary, so order/side
vocabulary is expected here; the research forbidden-field guards do not apply.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

ORDER_INTENT_CAVEAT = "order_intent_is_a_sandbox_dry_run_object_not_a_live_order"

# Map a research direction to an equity order side at the broker edge.
_DIRECTION_TO_SIDE = {"long": "buy", "short": "sell"}


@dataclass(frozen=True)
class OrderIntent:
    """A human-approved intent to place an equity order (not yet an order)."""

    intent_id: str
    candidate_id: str
    symbol: str
    side: str  # "buy" or "sell"
    quantity: float
    order_type: str = "market"
    time_in_force: str = "day"
    human_approved: bool = False
    intent_caveat: str = ORDER_INTENT_CAVEAT


def build_order_intent_from_review(
    review_record: Mapping[str, Any],
    *,
    intent_id: str,
    symbol: str,
    quantity: float,
    human_approved: bool,
    order_type: str = "market",
    time_in_force: str = "day",
) -> OrderIntent:
    """Build an ``OrderIntent`` from a decision-support review record.

    Requires ``human_approved=True`` — the caller asserts that a human reviewed
    and approved this specific intent. The record's ``direction`` is mapped to an
    equity order side; non-directional candidates are rejected.
    """
    if not human_approved:
        raise ValueError(
            "order intent requires explicit human approval; refusing to build "
            "an intent from an unapproved review record"
        )
    if quantity <= 0:
        raise ValueError("quantity must be positive")

    candidate_id = str(review_record.get("candidate_id", ""))
    if not candidate_id:
        raise ValueError("review_record must carry a candidate_id")

    direction = str(review_record.get("direction", "")).lower()
    side = _DIRECTION_TO_SIDE.get(direction)
    if side is None:
        raise ValueError(
            f"cannot map direction {direction!r} to an order side "
            "(expected 'long' or 'short')"
        )

    return OrderIntent(
        intent_id=str(intent_id),
        candidate_id=candidate_id,
        symbol=str(symbol),
        side=side,
        quantity=float(quantity),
        order_type=str(order_type),
        time_in_force=str(time_in_force),
        human_approved=True,
    )
