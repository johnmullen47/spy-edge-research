"""Tests for effective-N via ONC clustering (M119, RESEARCH_H)."""

import numpy as np
import pandas as pd
import pytest

from spy_edge_research.backtesting import (
    compute_effective_n,
    correlation_distance,
    summarize_candidate_deflated_sharpe,
    within_cluster_holm,
)
from spy_edge_research.backtesting.effective_n import (
    EFFECTIVE_N_NO_CLUSTER_CAVEAT,
    candidate_p_values_from_oos,
)


def _clustered_oos(n_clusters=3, per_cluster=4, n_splits=14, edge_cluster0=0.0, seed=0):
    """OOS panel of near-duplicate variants grouped into ``n_clusters`` clusters."""
    rng = np.random.default_rng(seed)
    rows = []
    for cl in range(n_clusters):
        base = rng.normal(edge_cluster0 if cl == 0 else 0.0, 1.0, n_splits)
        for v in range(per_cluster):
            cid = f"c{cl}_{v}"
            series = base + rng.normal(0, 0.04, n_splits)  # tight within-cluster corr
            for s in range(n_splits):
                rows.append({"candidate_id": cid, "split_number": s,
                             "oos_expectancy_difference": series[s]})
    return pd.DataFrame(rows)


def test_recovers_cluster_count_as_effective_n():
    oos = _clustered_oos(n_clusters=3, per_cluster=4)
    res = compute_effective_n(oos, family_floor=2)
    assert res.total_candidates == 12
    assert res.k_clusters == 3          # 12 correlated variants -> 3 independent
    assert res.n_eff == 3
    assert res.clustered is True
    assert res.n_eff < res.total_candidates  # the whole point: N drops below 100-style count


def test_effective_n_clipped_to_family_floor_and_total():
    oos = _clustered_oos(n_clusters=5, per_cluster=2)
    # floor above the natural cluster count forces N up to the floor
    res = compute_effective_n(oos, family_floor=8)
    assert res.n_eff >= 8
    assert res.n_eff <= res.total_candidates
    # ceiling: n_eff can never exceed total candidates
    res2 = compute_effective_n(oos, family_floor=2)
    assert res2.n_eff <= res2.total_candidates


def test_decorrelated_candidates_give_more_clusters_than_correlated():
    corr = _clustered_oos(n_clusters=2, per_cluster=5, seed=1)
    # independent noise streams -> little correlation structure -> more clusters
    rng = np.random.default_rng(2)
    rows = []
    for c in range(10):
        for s in range(14):
            rows.append({"candidate_id": f"i{c}", "split_number": s,
                         "oos_expectancy_difference": rng.normal(0, 1)})
    indep = pd.DataFrame(rows)
    n_corr = compute_effective_n(corr, family_floor=2).n_eff
    n_indep = compute_effective_n(indep, family_floor=2).n_eff
    assert n_indep > n_corr


def test_small_panel_falls_back_conservatively():
    # one candidate -> cannot cluster -> n_eff = total, flagged
    rows = [{"candidate_id": "only", "split_number": s,
             "oos_expectancy_difference": float(s)} for s in range(6)]
    res = compute_effective_n(pd.DataFrame(rows), family_floor=2)
    assert res.clustered is False
    assert res.caveat == EFFECTIVE_N_NO_CLUSTER_CAVEAT
    assert res.n_eff == res.total_candidates == 1


def test_correlation_distance_properties():
    corr = np.array([[1.0, 1.0, -1.0], [1.0, 1.0, 0.0], [-1.0, 0.0, 1.0]])
    d = correlation_distance(corr)
    assert np.allclose(np.diag(d), 0.0)
    assert d[0, 1] == pytest.approx(0.0)          # rho=1 -> distance 0
    assert d[0, 2] == pytest.approx(1.0)          # rho=-1 -> distance 1
    assert d[1, 2] == pytest.approx(np.sqrt(0.5))  # rho=0 -> sqrt(1/2)
    # NaN correlation treated as uncorrelated
    assert np.isfinite(correlation_distance(np.array([[1.0, np.nan], [np.nan, 1.0]]))).all()


def test_within_cluster_holm_representative_and_survival():
    labels = {"a": 0, "b": 0, "c": 1}
    sharpes = {"a": 2.0, "b": 0.5, "c": 1.0}      # 'a' is cluster-0 best
    p_values = {"a": 0.001, "b": 0.9, "c": 0.30}
    holm = within_cluster_holm(labels, p_values, sharpes, alpha=0.05)
    assert holm[0]["representative"] == "a"
    assert holm[0]["survived"] is True            # best member a passes Holm
    assert holm[1]["representative"] == "c"
    assert holm[1]["survived"] is False           # c's p=0.30 fails alpha=0.05


def test_within_cluster_holm_kills_cluster_when_best_member_insignificant():
    labels = {"x": 0, "y": 0}
    sharpes = {"x": 3.0, "y": 1.0}                # x is best by Sharpe...
    p_values = {"x": 0.40, "y": 0.001}            # ...but x is not significant
    holm = within_cluster_holm(labels, p_values, sharpes)
    assert holm[0]["representative"] == "x"
    assert holm[0]["survived"] is False           # carried forward only if BEST survives


def test_candidate_p_values_lower_for_stronger_edge():
    oos = _clustered_oos(n_clusters=2, per_cluster=3, edge_cluster0=1.2, seed=5)
    p = candidate_p_values_from_oos(oos)
    edge = [v for k, v in p.items() if k.startswith("c0_")]
    noise = [v for k, v in p.items() if k.startswith("c1_")]
    assert np.nanmean(edge) < np.nanmean(noise)


def test_dsr_effective_n_used_verbatim_not_clamped_up():
    # The M119 path must NOT clamp N up to the survivor panel (the M112 behaviour).
    oos = _clustered_oos(n_clusters=3, per_cluster=4, edge_cluster0=0.6, seed=7)
    res = compute_effective_n(oos, family_floor=2)
    dsr = summarize_candidate_deflated_sharpe(
        oos, effective_n=res.n_eff, sharpe_sample=res.representative_sharpes
    )
    assert (dsr["n_trials"] == res.n_eff).all()      # == 3, far below 12 survivors
    assert res.n_eff < dsr.shape[0]


def test_effective_n_less_deflation_than_full_count():
    # Lower N (effective) -> lower expected-max benchmark -> higher DSR than the
    # full survivor-count deflation. This is the corrective effect of RESEARCH_H.
    oos = _clustered_oos(n_clusters=3, per_cluster=4, edge_cluster0=0.8, seed=3)
    res = compute_effective_n(oos, family_floor=2)
    eff = summarize_candidate_deflated_sharpe(
        oos, effective_n=res.n_eff, sharpe_sample=res.representative_sharpes
    ).set_index("candidate_id")["deflated_sharpe_ratio"]
    full = summarize_candidate_deflated_sharpe(
        oos, n_trials_evaluated=oos["candidate_id"].nunique()
    ).set_index("candidate_id")["deflated_sharpe_ratio"]
    # On the strongest candidate the effective-N DSR is >= the full-count DSR.
    best = eff.idxmax()
    assert eff[best] >= full[best]


def test_compute_effective_n_validates_family_floor():
    oos = _clustered_oos()
    with pytest.raises(ValueError, match="family_floor"):
        compute_effective_n(oos, family_floor=0)


def test_effective_n_metadata_json_safe():
    res = compute_effective_n(_clustered_oos(), family_floor=2)
    meta = res.as_metadata()
    assert meta["n_eff"] == res.n_eff
    assert set(meta["cluster_assignments"]) == set(res.labels)
    import json
    json.dumps(meta)  # must be JSON-serializable
