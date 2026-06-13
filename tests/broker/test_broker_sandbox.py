"""Tests for the broker preparation sandbox layer (Phase 13)."""

from __future__ import annotations

import pytest

from spy_edge_research.broker import (
    AlpacaSandboxAdapter,
    BrokerConfig,
    BrokerSafetyError,
    KillSwitch,
    LIVE_ENDPOINT,
    PAPER_ENDPOINT,
    TradingLimits,
    build_order_intent_from_review,
    read_audit_log,
)
from spy_edge_research.broker.order_intent import OrderIntent


def _review_record():
    return {"candidate_id": "ev_a__5m", "direction": "long", "requires_human_review": True}


def _intent(quantity: float = 1.0, *, approved: bool = True) -> OrderIntent:
    return OrderIntent(
        intent_id="i1",
        candidate_id="ev_a__5m",
        symbol="SPY",
        side="buy",
        quantity=quantity,
        human_approved=approved,
    )


def test_intent_requires_human_approval():
    with pytest.raises(ValueError, match="human approval"):
        build_order_intent_from_review(
            _review_record(), intent_id="i1", symbol="SPY", quantity=1.0, human_approved=False
        )


def test_intent_maps_direction_to_side():
    intent = build_order_intent_from_review(
        _review_record(), intent_id="i1", symbol="SPY", quantity=1.0, human_approved=True
    )
    assert intent.side == "buy"
    assert intent.human_approved is True

    short = build_order_intent_from_review(
        {"candidate_id": "c", "direction": "short"},
        intent_id="i2",
        symbol="SPY",
        quantity=1.0,
        human_approved=True,
    )
    assert short.side == "sell"


def test_adapter_refuses_non_sandbox_mode_and_live_endpoint(tmp_path):
    audit = tmp_path / "audit.jsonl"
    with pytest.raises(ValueError, match="sandbox"):
        AlpacaSandboxAdapter(BrokerConfig(mode="live"), audit_path=audit)
    with pytest.raises(ValueError, match="paper endpoint"):
        AlpacaSandboxAdapter(
            BrokerConfig(mode="sandbox", endpoint=LIVE_ENDPOINT), audit_path=audit
        )


def test_dry_run_submit_accepts_and_audits(tmp_path):
    audit = tmp_path / "audit.jsonl"
    adapter = AlpacaSandboxAdapter(audit_path=audit)
    result = adapter.submit_intent(_intent())
    assert result["status"] == "dry_run_accepted"
    assert result["submitted"] is False
    assert result["endpoint"] == PAPER_ENDPOINT

    events = read_audit_log(audit)
    kinds = [e["event_kind"] for e in events]
    assert kinds == ["intent_received", "intent_result"]


def test_missing_approval_is_blocked_by_limits(tmp_path):
    audit = tmp_path / "audit.jsonl"
    adapter = AlpacaSandboxAdapter(audit_path=audit)
    with pytest.raises(BrokerSafetyError) as excinfo:
        adapter.submit_intent(_intent(approved=False))
    assert "missing_human_approval" in excinfo.value.violations
    assert [e["event_kind"] for e in read_audit_log(audit)] == [
        "intent_received",
        "intent_rejected",
    ]


def test_quantity_over_limit_is_rejected(tmp_path):
    audit = tmp_path / "audit.jsonl"
    adapter = AlpacaSandboxAdapter(
        audit_path=audit, limits=TradingLimits(max_order_quantity=1.0)
    )
    with pytest.raises(BrokerSafetyError) as excinfo:
        adapter.submit_intent(_intent(quantity=5.0))
    assert "order_quantity_exceeds_limit" in excinfo.value.violations


def test_kill_switch_blocks_submission(tmp_path):
    audit = tmp_path / "audit.jsonl"
    ks = KillSwitch()
    ks.engage("manual halt")
    adapter = AlpacaSandboxAdapter(audit_path=audit, kill_switch=ks)
    with pytest.raises(BrokerSafetyError) as excinfo:
        adapter.submit_intent(_intent())
    assert "kill_switch_engaged" in excinfo.value.violations


class _FakeClient:
    def __init__(self):
        self.calls = []

    def submit_order(self, **kwargs):
        self.calls.append(kwargs)
        return {"id": "paper-123", "status": "accepted", **kwargs}


def test_paper_submit_with_injected_client_calls_and_audits(tmp_path):
    audit = tmp_path / "audit.jsonl"
    client = _FakeClient()
    adapter = AlpacaSandboxAdapter(
        BrokerConfig(dry_run=False), audit_path=audit, client=client
    )
    result = adapter.submit_intent(_intent(quantity=1.0))
    assert result["status"] == "paper_submitted"
    assert result["submitted"] is True
    assert client.calls == [
        {
            "symbol": "SPY",
            "qty": 1.0,
            "side": "buy",
            "type": "market",
            "time_in_force": "day",
        }
    ]
    assert result["broker_response"]["id"] == "paper-123"
