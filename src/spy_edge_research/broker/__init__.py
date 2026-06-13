"""Broker preparation layer (Phase 13) — Alpaca paper sandbox, no real money.

The first module past decision support. It turns a human-approved order intent
into a dry-run paper-trading order with a full audit trail, enforcing a
kill-switch and hard trading limits. It is hard-pinned to Alpaca's paper
endpoint — reaching a live endpoint is structurally impossible from here. Live
execution is a separate, explicitly gated module. Like ``simulation`` and
``decision_support``, this package is kept out of the top-level package
re-export.
"""

from spy_edge_research.broker.order_intent import (
    ORDER_INTENT_CAVEAT,
    OrderIntent,
    build_order_intent_from_review,
)
from spy_edge_research.broker.safety import (
    BrokerSafetyError,
    KillSwitch,
    TradingLimits,
    check_order_against_limits,
)
from spy_edge_research.broker.audit import append_audit_event, read_audit_log
from spy_edge_research.broker.alpaca_adapter import (
    ALPACA_AVAILABLE,
    LIVE_ENDPOINT,
    PAPER_ENDPOINT,
    SANDBOX_MODE,
    AlpacaSandboxAdapter,
    BrokerConfig,
)

__all__ = [
    "ORDER_INTENT_CAVEAT",
    "OrderIntent",
    "build_order_intent_from_review",
    "BrokerSafetyError",
    "KillSwitch",
    "TradingLimits",
    "check_order_against_limits",
    "append_audit_event",
    "read_audit_log",
    "ALPACA_AVAILABLE",
    "LIVE_ENDPOINT",
    "PAPER_ENDPOINT",
    "SANDBOX_MODE",
    "AlpacaSandboxAdapter",
    "BrokerConfig",
]
