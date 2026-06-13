"""Readiness-gated candidate selection for the simulation layer (MOD 14).

The paper-trading readiness gate (MOD 10) is the research boundary; this module
applies it as a filter so the simulator can be run *only* on candidates that
cleared the gate. Simulating a candidate never authorizes a trade — but keeping
this gate explicit preserves the project's discipline that nothing reaches the
post-gate tier without meeting the evidence bar.

``simulate_candidate_positions`` itself accepts any candidate list; callers that
want the gated subset filter through ``select_eligible_candidates`` first.
Running the simulator on not-yet-eligible candidates is permitted for *research*
(studying historical behavior), but such a run is descriptive only and must not
be presented as gated or authorized.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

import pandas as pd

from spy_edge_research.paper.readiness_scoring import READINESS_VERDICT_ELIGIBLE


def select_eligible_candidates(
    candidates: Iterable[Mapping[str, Any]],
    verdicts: pd.DataFrame,
    *,
    candidate_id_column: str = "candidate_id",
    verdict_column: str = "verdict",
) -> list[dict[str, Any]]:
    """Return only candidates whose readiness verdict is eligible.

    ``verdicts`` is a per-candidate readiness verdict table (as written by the
    MOD 11 runner / produced by ``summarize_readiness_verdict``). Candidates with
    no verdict row, or a non-eligible verdict, are excluded.
    """
    if not isinstance(verdicts, pd.DataFrame):
        raise TypeError("verdicts must be a DataFrame")
    if verdicts.empty or candidate_id_column not in verdicts.columns:
        return []
    eligible_ids = set(
        verdicts.loc[
            verdicts[verdict_column] == READINESS_VERDICT_ELIGIBLE, candidate_id_column
        ].astype(str)
    )
    return [
        dict(candidate)
        for candidate in candidates
        if str(candidate.get("candidate_id")) in eligible_ids
    ]
