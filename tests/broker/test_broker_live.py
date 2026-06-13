"""Tests for the gated live execution adapter (Phase 14).

No test here places a real order: every test injects a fake client and passes the
enabling env flag as an explicit dict, never touching the real environment.
"""

from __future__ import annotations

import pytest

from spy_edge_research.broker import (
    AlpacaLiveAdapter,
    BrokerLiveDisabledError,
    BrokerSafetyError,
    KillSwitch,
    LIVE_ENABLE_ENV_VAR,
    LiveBrokerConfig,
    PAPER_ENDPOINT,
    TradingLimits,
)
from spy_edge_research.broker.alpaca_adapter import LIVE_ENDPOINT
from spy_edge_research.broker.audit import read_audit_log
from spy_edge_research.broker.order_intent import OrderIntent

_ENABLED_ENV = {LIVE_ENABLE_ENV_VAR: "1"}


def _intent(quantity: float = 1.0, *, approved: bool = True) -> OrderIntent:
    return OrderIntent(
        intent_id="live-1",
        candidate_id="ev_a__5m",
        symbol="SPY",
        side="buy",
        quantity=quantity,
        human_approved=approved,
    )


class _FakeClient:
    def __init__(self):
        self.calls = []

    def submit_order(self, **kwargs):
        self.calls.append(kwargs)
        return {"id": "live-abc", "status": "accepted", **kwargs}


def _adapter(tmp_path, *, env=_ENABLED_ENV, client=None, limits=None, kill_switch=None):
    return AlpacaLiveAdapter(
        limits=limits or TradingLimits(max_order_quantity=1.0),
        audit_path=tmp_path / "live_audit.jsonl",
        client=client if client is not None else _FakeClient(),
        kill_switch=kill_switch,
        env=env,
    )


def test_construction_without_env_flag_is_disabled(tmp_path):
    with pytest.raises(BrokerLiveDisabledError):
        AlpacaLiveAdapter(
            limits=TradingLimits(),
            audit_path=tmp_path / "a.jsonl",
            client=_FakeClient(),
            env={},  # flag absent
        )


def test_construction_refuses_non_live_endpoint(tmp_path):
    with pytest.raises(ValueError, match="live endpoint"):
        AlpacaLiveAdapter(
            LiveBrokerConfig(endpoint=PAPER_ENDPOINT),
            limits=TradingLimits(),
            audit_path=tmp_path / "a.jsonl",
            client=_FakeClient(),
            env=_ENABLED_ENV,
        )


def test_submit_without_matching_token_is_rejected_and_places_no_order(tmp_path):
    client = _FakeClient()
    adapter = _adapter(tmp_path, client=client)
    with pytest.raises(BrokerSafetyError) as excinfo:
        adapter.submit_intent(_intent(), human_approval_token="wrong-id")
    assert "missing_per_order_human_approval" in excinfo.value.violations
    assert client.calls == []  # no real order attempted
    assert [e["event_kind"] for e in read_audit_log(tmp_path / "live_audit.jsonl")] == [
        "live_intent_received",
        "live_intent_rejected",
    ]


def test_submit_with_matching_token_places_order_and_audits(tmp_path):
    client = _FakeClient()
    adapter = _adapter(tmp_path, client=client)
    result = adapter.submit_intent(_intent(), human_approval_token="live-1")
    assert result["status"] == "live_submitted"
    assert result["submitted"] is True
    assert result["endpoint"] == LIVE_ENDPOINT
    assert client.calls == [
        {
            "symbol": "SPY",
            "qty": 1.0,
            "side": "buy",
            "type": "market",
            "time_in_force": "day",
        }
    ]
    kinds = [e["event_kind"] for e in read_audit_log(tmp_path / "live_audit.jsonl")]
    assert kinds == ["live_intent_received", "live_intent_result"]


def test_quantity_over_limit_is_rejected(tmp_path):
    client = _FakeClient()
    adapter = _adapter(tmp_path, client=client, limits=TradingLimits(max_order_quantity=1.0))
    with pytest.raises(BrokerSafetyError) as excinfo:
        adapter.submit_intent(_intent(quantity=10.0), human_approval_token="live-1")
    assert "order_quantity_exceeds_limit" in excinfo.value.violations
    assert client.calls == []


def test_kill_switch_blocks_live_submission(tmp_path):
    client = _FakeClient()
    ks = KillSwitch()
    ks.engage("halt")
    adapter = _adapter(tmp_path, client=client, kill_switch=ks)
    with pytest.raises(BrokerSafetyError) as excinfo:
        adapter.submit_intent(_intent(), human_approval_token="live-1")
    assert "kill_switch_engaged" in excinfo.value.violations
    assert client.calls == []


def test_no_client_cannot_submit(tmp_path):
    adapter = AlpacaLiveAdapter(
        limits=TradingLimits(max_order_quantity=1.0),
        audit_path=tmp_path / "live_audit.jsonl",
        client=None,
        env=_ENABLED_ENV,
    )
    with pytest.raises(RuntimeError, match="broker client"):
        adapter.submit_intent(_intent(), human_approval_token="live-1")
