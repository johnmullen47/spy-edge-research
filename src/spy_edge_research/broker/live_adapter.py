"""Live execution adapter (Phase 14) — inert unless explicitly enabled.

This is the only module in the project that can place a real-money order, and it
is designed to be impossible to trigger by accident. Three independent gates must
all hold:

1. **Env flag** — the process env must set ``SPY_EDGE_ALLOW_LIVE=1``. Without it
   the constructor refuses to build the adapter at all (fail closed).
2. **Per-order human approval** — every ``submit_intent`` call requires a
   ``human_approval_token`` that matches that specific intent's id. There is no
   batch path and no autonomous path: a human must confirm each order by id.
3. **Limits + kill-switch** — the same hard caps and manual halt as the sandbox.

There is deliberately no dry-run mode here; a live submission requires a
configured broker client. Credentials come from the environment, never the repo.
Even with all gates open, real runs are only meaningful after Hard Gate A (an
edge that reached ``eligible`` on real data) — that is an operational
precondition, enforced upstream, not in this code.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from spy_edge_research.broker.audit import append_audit_event
from spy_edge_research.broker.order_intent import OrderIntent
from spy_edge_research.broker.safety import (
    BrokerSafetyError,
    KillSwitch,
    TradingLimits,
    check_order_against_limits,
)
from spy_edge_research.broker.alpaca_adapter import LIVE_ENDPOINT, _coerce_response

LIVE_MODE = "live"
LIVE_ENABLE_ENV_VAR = "SPY_EDGE_ALLOW_LIVE"
LIVE_ENABLE_ENV_VALUE = "1"


class BrokerLiveDisabledError(RuntimeError):
    """Raised when the live adapter is built without the enabling env flag."""


@dataclass(frozen=True)
class LiveBrokerConfig:
    """Live broker configuration. There is intentionally no dry-run mode."""

    mode: str = LIVE_MODE
    endpoint: str = LIVE_ENDPOINT


class AlpacaLiveAdapter:
    """Submit human-approved intents as REAL orders, behind every safety gate."""

    def __init__(
        self,
        config: LiveBrokerConfig | None = None,
        *,
        limits: TradingLimits,
        kill_switch: KillSwitch | None = None,
        audit_path: str | Path,
        client: Any | None = None,
        env: Mapping[str, str] | None = None,
    ):
        cfg = config or LiveBrokerConfig()
        if cfg.mode != LIVE_MODE:
            raise ValueError(f"AlpacaLiveAdapter requires mode {LIVE_MODE!r}")
        if cfg.endpoint != LIVE_ENDPOINT:
            raise ValueError("live mode must use the Alpaca live endpoint")
        environment = env if env is not None else os.environ
        if environment.get(LIVE_ENABLE_ENV_VAR) != LIVE_ENABLE_ENV_VALUE:
            raise BrokerLiveDisabledError(
                f"live execution is disabled; set {LIVE_ENABLE_ENV_VAR}="
                f"{LIVE_ENABLE_ENV_VALUE} in the environment to enable it"
            )
        self._config = cfg
        self._limits = limits
        self._kill_switch = kill_switch or KillSwitch()
        self._audit_path = Path(audit_path)
        self._client = client

    @property
    def kill_switch(self) -> KillSwitch:
        return self._kill_switch

    def submit_intent(
        self,
        intent: OrderIntent,
        *,
        human_approval_token: str,
        open_position_quantity: float = 0.0,
        realized_daily_loss_points: float = 0.0,
    ) -> dict[str, Any]:
        """Place a REAL order only if the per-order approval + every gate holds."""
        append_audit_event(
            self._audit_path,
            "live_intent_received",
            {
                "intent_id": intent.intent_id,
                "candidate_id": intent.candidate_id,
                "symbol": intent.symbol,
                "side": intent.side,
                "quantity": intent.quantity,
                "endpoint": self._config.endpoint,
            },
        )

        # Gate 2: per-order human approval. The token must match this exact intent.
        if not intent.human_approved or human_approval_token != intent.intent_id:
            append_audit_event(
                self._audit_path,
                "live_intent_rejected",
                {
                    "intent_id": intent.intent_id,
                    "violations": ["missing_per_order_human_approval"],
                },
            )
            raise BrokerSafetyError(["missing_per_order_human_approval"])

        # Gate 3: limits + kill-switch.
        violations = check_order_against_limits(
            intent,
            limits=self._limits,
            open_position_quantity=open_position_quantity,
            realized_daily_loss_points=realized_daily_loss_points,
            kill_switch=self._kill_switch,
        )
        if violations:
            append_audit_event(
                self._audit_path,
                "live_intent_rejected",
                {"intent_id": intent.intent_id, "violations": violations},
            )
            raise BrokerSafetyError(violations)

        if self._client is None:
            append_audit_event(
                self._audit_path,
                "live_intent_rejected",
                {"intent_id": intent.intent_id, "violations": ["no_broker_client"]},
            )
            raise RuntimeError("live adapter requires a configured broker client")

        broker_response = self._client.submit_order(
            symbol=intent.symbol,
            qty=intent.quantity,
            side=intent.side,
            type=intent.order_type,
            time_in_force=intent.time_in_force,
        )
        result = {
            "status": "live_submitted",
            "intent_id": intent.intent_id,
            "endpoint": self._config.endpoint,
            "submitted": True,
            "broker_response": _coerce_response(broker_response),
        }
        append_audit_event(self._audit_path, "live_intent_result", result)
        return result
