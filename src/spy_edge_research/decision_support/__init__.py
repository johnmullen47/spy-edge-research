"""Human-in-the-loop decision support tier (Phase 12).

Takes candidates that cleared the research readiness gate and assembles a
descriptive review surface for a human to consider. It authorizes nothing, sizes
nothing, and routes no orders — broker preparation and live execution are
separate, gated modules. Like ``simulation``, this post-gate package is kept out
of the top-level package re-export so it is never mistaken for the core
research stack.
"""

from spy_edge_research.decision_support.contracts import (
    DECISION_SUPPORT_REPORT_CAVEAT,
    DECISION_SUPPORT_TABLE_FILES,
    FORBIDDEN_DECISION_SUPPORT_FIELDS,
    create_decision_support_metadata,
    raise_forbidden_decision_support_fields,
    validate_decision_support_report_bundle,
)
from spy_edge_research.decision_support.recommendation import (
    REVIEW_RECORD_COLUMNS,
    build_decision_support_records,
    summarize_decision_support,
)
from spy_edge_research.decision_support.reports import (
    build_decision_support_report_bundle,
    export_decision_support_report_bundle_to_csv,
    export_decision_support_report_bundle_to_json,
    summarize_decision_support_report_bundle,
)

__all__ = [
    "DECISION_SUPPORT_REPORT_CAVEAT",
    "DECISION_SUPPORT_TABLE_FILES",
    "FORBIDDEN_DECISION_SUPPORT_FIELDS",
    "create_decision_support_metadata",
    "raise_forbidden_decision_support_fields",
    "validate_decision_support_report_bundle",
    "REVIEW_RECORD_COLUMNS",
    "build_decision_support_records",
    "summarize_decision_support",
    "build_decision_support_report_bundle",
    "export_decision_support_report_bundle_to_csv",
    "export_decision_support_report_bundle_to_json",
    "summarize_decision_support_report_bundle",
]
