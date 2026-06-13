"""Contracts for the decision_support package (Phase 12).

Decision support is the project's human-in-the-loop tier: it takes candidates
that already cleared the research readiness gate and assembles a *descriptive*
review record for a person to consider. It never authorizes a trade, sizes a
position, routes an order, or implies a live/paper execution — those remain
separate, gated modules. This module pins the package caveat, the forbidden-field
guard (a superset of the upstream research guards), and the bundle validator.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pandas as pd

from spy_edge_research._internal._common import created_at_utc, json_safe_value

DECISION_SUPPORT_REPORT_CAVEAT = (
    "decision_support_analysis_is_research_only_requires_human_review"
)

DECISION_SUPPORT_TABLE_FILES: dict[str, str] = {
    "decision_support_review": "decision_support_review.csv",
    "decision_support_summary": "decision_support_summary.csv",
    "decision_support_caveats": "decision_support_caveats.csv",
}

# A superset of the upstream research/sim forbidden tokens. Decision support
# produces analysis a human reviews — never an actionable order, size, or
# execution field.
FORBIDDEN_DECISION_SUPPORT_FIELDS: frozenset[str] = frozenset(
    {
        "buy",
        "sell",
        "entry",
        "exit",
        "approved",
        "live",
        "trade_signal",
        "order",
        "route",
        "routing",
        "broker",
        "brokerage",
        "execution",
        "position_size",
        "sizing",
        "allocation",
        "portfolio",
        "optimal",
        "best",
        "pnl",
        "p_l",
        "profit",
        "money",
        "cash",
        "account",
        "margin",
        "leverage",
    }
)


def create_decision_support_metadata(
    *,
    project_name: str = "SPY Directional Edge Research",
    milestone: str = "102",
    notes: str | None = None,
) -> dict[str, Any]:
    """Create metadata for a decision support report bundle."""
    metadata: dict[str, Any] = {
        "created_at_utc": created_at_utc(),
        "project_name": project_name,
        "milestone": milestone,
        "report_caveat": DECISION_SUPPORT_REPORT_CAVEAT,
    }
    if notes is not None:
        metadata["notes"] = json_safe_value(notes)
    raise_forbidden_decision_support_fields(metadata, name="decision support metadata")
    return metadata


def raise_forbidden_decision_support_fields(
    values: Mapping[str, Any], *, name: str
) -> None:
    """Raise if any field name contains a forbidden actionable/execution token."""
    forbidden = [
        field
        for field in values
        if any(token in str(field).lower() for token in FORBIDDEN_DECISION_SUPPORT_FIELDS)
    ]
    if forbidden:
        raise ValueError(f"{name} contains forbidden fields: {forbidden}")


def validate_decision_support_report_bundle(bundle: Any) -> dict[str, Any]:
    """Validate a decision support report bundle structure and field names."""
    if not isinstance(bundle, dict):
        raise TypeError("bundle must be a dict")
    if "metadata" not in bundle or not isinstance(bundle["metadata"], dict):
        raise KeyError("bundle is missing a metadata dict")
    if "tables" not in bundle or not isinstance(bundle["tables"], dict):
        raise KeyError("bundle is missing a tables dict")
    raise_forbidden_decision_support_fields(
        bundle["metadata"], name="decision support metadata"
    )
    for table_name, table in bundle["tables"].items():
        if not isinstance(table_name, str) or not table_name:
            raise ValueError("bundle table names must be non-empty strings")
        raise_forbidden_decision_support_fields(
            {"table_name": table_name}, name="decision support table name"
        )
        if not isinstance(table, pd.DataFrame):
            raise TypeError(f"{table_name} must be a pandas DataFrame")
        raise_forbidden_decision_support_fields(
            {column: None for column in table.columns}, name=f"{table_name} columns"
        )
    return bundle
