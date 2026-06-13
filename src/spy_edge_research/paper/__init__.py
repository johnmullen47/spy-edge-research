"""Research-only paper-trading readiness gating.

Scores candidate research metrics against pre-registered readiness criteria and
emits a gated verdict. This is a research gate, NOT paper trading: it never
authorizes a trade, sizes a position, or runs a paper/live order. The actual
paper-trading simulation layer is a separate, unauthorized module.
"""

from spy_edge_research.paper.readiness_criteria import (
    READINESS_CRITERIA_CAVEAT,
    ReadinessCriteria,
    default_readiness_criteria,
)
from spy_edge_research.paper.readiness_inputs import build_readiness_metrics
from spy_edge_research.paper.readiness_reports import (
    READINESS_REPORT_CAVEAT,
    build_readiness_report_bundle,
    create_readiness_report_metadata,
    export_readiness_report_bundle_to_csv,
    export_readiness_report_bundle_to_json,
    summarize_readiness_report_bundle,
    validate_readiness_report_bundle,
)
from spy_edge_research.paper.readiness_scoring import (
    READINESS_VERDICT_ELIGIBLE,
    READINESS_VERDICT_NOT_READY,
    score_candidate_readiness,
    summarize_readiness_verdict,
)

__all__ = [
    "READINESS_CRITERIA_CAVEAT",
    "READINESS_REPORT_CAVEAT",
    "READINESS_VERDICT_ELIGIBLE",
    "READINESS_VERDICT_NOT_READY",
    "ReadinessCriteria",
    "build_readiness_metrics",
    "build_readiness_report_bundle",
    "create_readiness_report_metadata",
    "default_readiness_criteria",
    "export_readiness_report_bundle_to_csv",
    "export_readiness_report_bundle_to_json",
    "score_candidate_readiness",
    "summarize_readiness_report_bundle",
    "summarize_readiness_verdict",
    "validate_readiness_report_bundle",
]
