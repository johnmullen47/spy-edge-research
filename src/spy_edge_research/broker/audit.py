"""Append-only JSONL audit log for the broker layer.

Every intent, approval, safety rejection, submission, and broker response is
appended as one JSON line. The log is the broker layer's source of truth for
what happened; it is never rewritten in place. No credentials or secrets are
ever written here — callers must not pass them in the event payload.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from spy_edge_research._internal._common import created_at_utc, json_safe_mapping


def append_audit_event(
    audit_path: str | Path,
    event_kind: str,
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    """Append one timestamped event to the JSONL audit log and return it."""
    path = Path(audit_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    record: dict[str, Any] = {
        "event_at_utc": created_at_utc(),
        "event_kind": str(event_kind),
        **json_safe_mapping(dict(payload)),
    }
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True) + "\n")
    return record


def read_audit_log(audit_path: str | Path) -> list[dict[str, Any]]:
    """Read all events from a JSONL audit log (empty list if absent)."""
    path = Path(audit_path)
    if not path.exists():
        return []
    events: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            events.append(json.loads(line))
    return events
