"""Research-only portfolio/risk exposure diagnostics.

Descriptive exposure, signal-overlap, concentration, and advisory limit checks
for candidate edge sets. No position sizing, allocation, portfolio construction,
order generation, or trade-readiness claims.
"""

from spy_edge_research.risk.concentration import (
    compute_group_concentration,
    summarize_concentration,
)
from spy_edge_research.risk.exposure import (
    add_exposure_columns,
    summarize_exposure,
)
from spy_edge_research.risk.exposure_limits import (
    ExposureLimits,
    evaluate_exposure_limits,
)
from spy_edge_research.risk.risk_reports import (
    build_risk_exposure_report_bundle,
    create_risk_exposure_report_metadata,
    export_risk_exposure_report_bundle_to_csv,
    export_risk_exposure_report_bundle_to_json,
    summarize_risk_exposure_report_bundle,
    validate_risk_exposure_report_bundle,
)
from spy_edge_research.risk.signal_overlap import (
    compute_event_mask_overlap,
    summarize_signal_overlap,
)

__all__ = [
    "ExposureLimits",
    "add_exposure_columns",
    "build_risk_exposure_report_bundle",
    "compute_event_mask_overlap",
    "compute_group_concentration",
    "create_risk_exposure_report_metadata",
    "evaluate_exposure_limits",
    "export_risk_exposure_report_bundle_to_csv",
    "export_risk_exposure_report_bundle_to_json",
    "summarize_concentration",
    "summarize_exposure",
    "summarize_risk_exposure_report_bundle",
    "summarize_signal_overlap",
    "validate_risk_exposure_report_bundle",
]
