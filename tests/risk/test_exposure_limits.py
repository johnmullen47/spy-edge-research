from __future__ import annotations

import pandas as pd
import pytest

from spy_edge_research.risk import (
    ExposureLimits,
    add_exposure_columns,
    compute_event_mask_overlap,
    compute_group_concentration,
    evaluate_exposure_limits,
    summarize_concentration,
    summarize_exposure,
    summarize_signal_overlap,
)


def test_limits_flag_breaches() -> None:
    candidates = pd.DataFrame(
        {"instrument": ["SPY", "SPY", "SPY"], "direction": ["long", "long", "long"]}
    )
    enriched = add_exposure_columns(candidates)
    exposure = summarize_exposure(candidates)
    concentration = summarize_concentration(
        compute_group_concentration(enriched, group_column="instrument")
    )
    limits = ExposureLimits(max_gross_exposure=2.0, max_net_exposure_abs=2.0, max_group_share=0.9)

    checks = evaluate_exposure_limits(
        limits=limits,
        exposure_summary=exposure,
        concentration_summary=concentration,
    ).set_index("check")

    assert checks.loc["gross_exposure", "status"] == "exceeds_limit"
    assert checks.loc["gross_exposure", "flag"] == "gross_exposure_exceeds_limit"
    assert checks.loc["net_exposure_abs", "status"] == "exceeds_limit"
    assert checks.loc["largest_group_share", "status"] == "exceeds_limit"
    assert checks.loc["largest_group_share", "flag"] == "concentration_exceeds_limit"


def test_limits_ok_and_not_evaluated() -> None:
    exposure = summarize_exposure(pd.DataFrame({"direction": ["long", "short"]}))
    checks = evaluate_exposure_limits(
        limits=ExposureLimits(max_gross_exposure=10.0),
        exposure_summary=exposure,
    ).set_index("check")
    assert checks.loc["gross_exposure", "status"] == "ok"
    assert checks.loc["gross_exposure", "flag"] is None
    assert checks.loc["net_exposure_abs", "status"] == "not_evaluated"


def test_overlap_limit_flag() -> None:
    df = pd.DataFrame({"a": [True, True, False], "b": [True, True, False]})
    overlap = summarize_signal_overlap(compute_event_mask_overlap(df, ["a", "b"]))
    checks = evaluate_exposure_limits(
        limits=ExposureLimits(max_pairwise_jaccard=0.5),
        overlap_summary=overlap,
    ).set_index("check")
    assert checks.loc["max_pairwise_jaccard", "status"] == "exceeds_limit"
    assert checks.loc["max_pairwise_jaccard", "flag"] == "risk_overlap_too_high"


def test_limits_requires_dataclass() -> None:
    with pytest.raises(TypeError, match="ExposureLimits"):
        evaluate_exposure_limits(limits={"max_gross_exposure": 1.0})
