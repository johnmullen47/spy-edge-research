"""Alpaca sandbox adapter (Phase 13) — paper endpoint only, no real money.

Turns a human-approved ``OrderIntent`` into a dry-run order against Alpaca's
*paper-trading* endpoint, enforcing the kill-switch and trading limits and
appending a full audit trail. This stage is hard-pinned to the paper endpoint:
the constructor refuses any mode other than ``"sandbox"`` and any endpoint other
than the paper URL, so it is structurally impossible to reach a live endpoint
from here. The later live adapter (Phase 14) extends this behind an explicit
env flag plus per-order human approval.

``alpaca-py`` is an optional dependency: with ``dry_run=True`` (the default) the
adapter never touches the network and needs no credentials, so it is fully
testable offline. A real paper submission requires ``dry_run=False`` and an
injected (or constructed) client.
"""

from __future__ import annotations

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

PAPER_ENDPOINT = "https://paper-api.alpaca.markets"
# Defined for the later live stage; the sandbox adapter must never use it.
LIVE_ENDPOINT = "https://api.alpaca.markets"

SANDBOX_MODE = "sandbox"

try:  # optional dependency, skipped gracefully like matplotlib
    import alpaca  # type: ignore  # noqa: F401

    ALPACA_AVAILABLE = True
except ImportError:  # pragma: no cover - exercised only where alpaca is absent
    ALPACA_AVAILABLE = False


@dataclass(frozen=True)
class BrokerConfig:
    """Sandbox broker configuration. Stage 13 supports the paper endpoint only."""

    mode: str = SANDBOX_MODE
    endpoint: str = PAPER_ENDPOINT
    dry_run: bool = True


class AlpacaSandboxAdapter:
    """Submit human-approved intents as dry-run paper orders, fully audited."""

    def __init__(
        self,
        config: BrokerConfig | None = None,
        *,
        limits: TradingLimits | None = None,
        kill_switch: KillSwitch | None = None,
        audit_path: str | Path,
        client: Any | None = None,
    ):
        cfg = config or BrokerConfig()
        if cfg.mode != SANDBOX_MODE:
            raise ValueError(
                f"AlpacaSandboxAdapter supports {SANDBOX_MODE!r} mode only; "
                f"got {cfg.mode!r}. Live execution is a separate gated stage."
            )
        if cfg.endpoint != PAPER_ENDPOINT:
            raise ValueError(
                "sandbox mode must use the Alpaca paper endpoint; refusing "
                f"endpoint {cfg.endpoint!r}"
            )
        self._config = cfg
        self._limits = limits or TradingLimits()
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
        open_position_quantity: float = 0.0,
        realized_daily_loss_points: float = 0.0,
    ) -> dict[str, Any]:
        """Validate and (dry-run or paper-)submit an intent; audit every step."""
        append_audit_event(
            self._audit_path,
            "intent_received",
            {
                "intent_id": intent.intent_id,
                "candidate_id": intent.candidate_id,
                "symbol": intent.symbol,
                "side": intent.side,
                "quantity": intent.quantity,
                "mode": self._config.mode,
                "dry_run": self._config.dry_run,
            },
        )

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
                "intent_rejected",
                {"intent_id": intent.intent_id, "violations": violations},
            )
            raise BrokerSafetyError(violations)

        if self._config.dry_run or self._client is None:
            result = {
                "status": "dry_run_accepted",
                "intent_id": intent.intent_id,
                "symbol": intent.symbol,
                "side": intent.side,
                "quantity": intent.quantity,
                "endpoint": self._config.endpoint,
                "submitted": False,
            }
        else:
            broker_response = self._client.submit_order(
                symbol=intent.symbol,
                qty=intent.quantity,
                side=intent.side,
                type=intent.order_type,
                time_in_force=intent.time_in_force,
            )
            result = {
                "status": "paper_submitted",
                "intent_id": intent.intent_id,
                "endpoint": self._config.endpoint,
                "submitted": True,
                "broker_response": _coerce_response(broker_response),
            }

        append_audit_event(self._audit_path, "intent_result", result)
        return result


def _coerce_response(response: Any) -> Any:
    """Best-effort conversion of a broker SDK response into audit-safe data."""
    if isinstance(response, (str, int, float, bool)) or response is None:
        return response
    if isinstance(response, dict):
        return {str(key): _coerce_response(value) for key, value in response.items()}
    for attr in ("_raw", "__dict__"):
        data = getattr(response, attr, None)
        if isinstance(data, dict):
            return {str(key): _coerce_response(value) for key, value in data.items()}
    return str(response)
