"""Effective number of independent trials via ONC clustering (Build 4 / M119).

Implements the RESEARCH_H N-count correction. The Deflated Sharpe Ratio deflates
an observed Sharpe against the expected maximum across **N independent trials**.
Counting every correlated parameter variant as an independent trial
(``N = len(registry)``) over-deflates the DSR (RESEARCH_H §0). The correct N is
the **effective number of independent trials**, estimated by clustering the
candidate return streams (López de Prado's multiple-testing solution) and bounded
below by the a-priori family count and above by the total candidate count.

What this module computes (RESEARCH_H §3-§5), all frozen hyperparameters per §4:

1. **Return matrix** ``R`` — per-candidate across-split OOS series (rows =
   candidates, cols = splits), the same panel the deflation stack already uses.
2. **Distance** ``d_ij = sqrt(0.5 * (1 - rho_ij))`` on the return-correlation
   matrix ``rho``.
3. **Clustering** — López de Prado's ONC if available in-repo; otherwise the
   frozen fallback (RESEARCH_H §4.3): agglomerative hierarchical clustering with
   **average linkage** (UPGMA), K chosen by **maximum mean silhouette** over
   K in [2, M-1]. Only numpy is available here, so the fallback is used.
4. **Effective N** ``N_eff = clip(K, K_floor=family_count, K_ceil=M)``.
5. **Representatives & sigma_SR** — each cluster's best-Sharpe member; sigma_SR is
   the std of those K representative Sharpes.
6. **Within-cluster Holm** — Holm-Bonferroni across a cluster's variants; a
   cluster is carried forward only if its best member survives (FWE alpha=0.05).

Research-only measurement. Nothing here authorizes a trade. Pure functions:
deterministic given inputs (the fallback clustering is deterministic; the
``random_state`` is recorded for ONC parity and does not affect the fallback).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd

from spy_edge_research.backtesting.deflated_sharpe import sharpe_ratio

EFFECTIVE_N_CAVEAT = (
    "effective_n_is_a_research_diagnostic_not_trade_authorization"
)
# Emitted when the return panel is too small/degenerate to cluster (fewer than two
# candidates or fewer than two aligned observations). N_eff then falls back to the
# total candidate count clipped to the floor — the MOST conservative choice (no
# de-duplication credit is given), never more lenient than clustering would be.
EFFECTIVE_N_NO_CLUSTER_CAVEAT = (
    "effective_n_panel_too_small_to_cluster_fell_back_to_total_count"
)

DEFAULT_FAMILY_FLOOR = 2


@dataclass(frozen=True)
class EffectiveNResult:
    """Effective-N estimate plus the cluster structure that produced it."""

    n_eff: int
    k_clusters: int
    total_candidates: int
    family_floor: int
    mean_silhouette: float
    random_state: int
    clustered: bool
    labels: dict[str, int]
    representatives: dict[int, str]
    representative_sharpes: list[float]
    caveat: str = EFFECTIVE_N_CAVEAT
    notes: str = ""

    def as_metadata(self) -> dict[str, Any]:
        """JSON-safe summary for the run manifest."""
        return {
            "n_eff": int(self.n_eff),
            "k_clusters": int(self.k_clusters),
            "total_candidates": int(self.total_candidates),
            "family_floor": int(self.family_floor),
            "mean_silhouette": (
                float(self.mean_silhouette) if np.isfinite(self.mean_silhouette) else None
            ),
            "random_state": int(self.random_state),
            "clustered": bool(self.clustered),
            "cluster_assignments": dict(sorted(self.labels.items())),
            "cluster_representatives": {
                int(k): v for k, v in sorted(self.representatives.items())
            },
            "caveat": self.caveat,
            "notes": self.notes,
        }


def build_candidate_return_matrix(
    oos_results: pd.DataFrame,
    *,
    candidate_column: str = "candidate_id",
    split_column: str = "split_number",
    value_column: str = "oos_expectancy_difference",
) -> pd.DataFrame:
    """Dense (candidate x split) return matrix from the OOS per-split panel.

    Splits not observed for *every* surviving candidate are dropped so the
    correlation matrix is computed on a fully-aligned panel (no leakage; this is
    strategy-return structure only, never a strategy-vs-label correlation).
    """
    for required in (candidate_column, split_column, value_column):
        if required not in oos_results.columns:
            raise ValueError(f"oos_results is missing required column: {required}")
    wide = oos_results.pivot_table(
        index=candidate_column,
        columns=split_column,
        values=value_column,
        aggfunc="mean",
    ).sort_index()
    # Keep only splits present for all candidates so corr is on a dense panel.
    return wide.dropna(axis=1, how="any")


def correlation_distance(corr: np.ndarray) -> np.ndarray:
    """RESEARCH_H §4.2 distance ``sqrt(0.5 * (1 - rho))`` on a correlation matrix.

    Non-finite correlations (e.g. a zero-variance candidate) are treated as
    uncorrelated (``rho = 0`` -> ``d = sqrt(0.5)``). The diagonal is forced to 0.
    """
    rho = np.array(corr, dtype=float, copy=True)
    rho[~np.isfinite(rho)] = 0.0
    rho = np.clip(rho, -1.0, 1.0)
    dist = np.sqrt(np.clip(0.5 * (1.0 - rho), 0.0, None))
    np.fill_diagonal(dist, 0.0)
    return dist


def compute_effective_n(
    oos_results: pd.DataFrame,
    *,
    family_floor: int = DEFAULT_FAMILY_FLOOR,
    random_state: int = 0,
    candidate_column: str = "candidate_id",
    split_column: str = "split_number",
    value_column: str = "oos_expectancy_difference",
) -> EffectiveNResult:
    """Estimate the effective number of independent trials (RESEARCH_H §4).

    ``family_floor`` is the a-priori family count (the effective-N lower bound;
    2 at M118). Returns an :class:`EffectiveNResult`; when the panel is too small
    to cluster, ``n_eff`` falls back to ``clip(total, floor, total) = total`` (the
    most conservative choice) with :data:`EFFECTIVE_N_NO_CLUSTER_CAVEAT`.
    """
    if not isinstance(family_floor, int) or isinstance(family_floor, bool) or family_floor < 1:
        raise ValueError("family_floor must be an integer >= 1")

    matrix = build_candidate_return_matrix(
        oos_results,
        candidate_column=candidate_column,
        split_column=split_column,
        value_column=value_column,
    )
    candidates = [str(c) for c in matrix.index]
    total = len(candidates)
    sharpes = {c: sharpe_ratio(matrix.loc[idx].to_numpy()) for c, idx in zip(candidates, matrix.index)}

    floor = min(family_floor, total) if total >= 1 else family_floor
    ceil = max(total, floor)

    # Too small to cluster -> conservative fallback: every candidate its own trial.
    if total < 2 or matrix.shape[1] < 2:
        labels = {c: i for i, c in enumerate(candidates)}
        reps, rep_sharpes = _representatives(labels, sharpes)
        return EffectiveNResult(
            n_eff=int(np.clip(total, floor, ceil)) if total >= 1 else floor,
            k_clusters=total,
            total_candidates=total,
            family_floor=floor,
            mean_silhouette=float("nan"),
            random_state=int(random_state),
            clustered=False,
            labels=labels,
            representatives=reps,
            representative_sharpes=rep_sharpes,
            caveat=EFFECTIVE_N_NO_CLUSTER_CAVEAT,
            notes="panel_too_small_to_cluster",
        )

    corr = np.corrcoef(matrix.to_numpy(dtype=float))
    dist = correlation_distance(np.atleast_2d(corr))
    labels_by_k = _agglomerative_labels_by_k(dist)
    best_k, best_sil = _optimal_k(dist, labels_by_k)
    label_arr = labels_by_k[best_k]
    labels = {c: int(label_arr[i]) for i, c in enumerate(candidates)}
    reps, rep_sharpes = _representatives(labels, sharpes)
    n_eff = int(np.clip(best_k, floor, ceil))
    return EffectiveNResult(
        n_eff=n_eff,
        k_clusters=int(best_k),
        total_candidates=total,
        family_floor=floor,
        mean_silhouette=float(best_sil),
        random_state=int(random_state),
        clustered=True,
        labels=labels,
        representatives=reps,
        representative_sharpes=rep_sharpes,
        notes="onc_fallback_agglomerative_average_linkage_silhouette",
    )


def candidate_p_values_from_oos(
    oos_results: pd.DataFrame,
    *,
    candidate_column: str = "candidate_id",
    value_column: str = "oos_expectancy_difference",
) -> dict[str, float]:
    """One-sided p-value per candidate that its mean OOS edge is <= 0.

    ``p = 1 - PSR(series, benchmark=0)`` = P(true Sharpe <= 0), the natural
    significance of "this candidate's edge is positive" from the same per-split
    series. Used for the within-cluster Holm screen (RESEARCH_H §5).
    """
    from spy_edge_research.backtesting.deflated_sharpe import probabilistic_sharpe_ratio

    out: dict[str, float] = {}
    for candidate_id, group in oos_results.groupby(candidate_column, sort=True):
        psr = probabilistic_sharpe_ratio(group[value_column], benchmark_sr=0.0)
        out[str(candidate_id)] = float(1.0 - psr) if np.isfinite(psr) else float("nan")
    return out


def within_cluster_holm(
    labels: Mapping[str, int],
    p_values: Mapping[str, float],
    sharpes: Mapping[str, float],
    *,
    alpha: float = 0.05,
) -> dict[int, dict[str, Any]]:
    """Within-cluster Holm-Bonferroni screen (RESEARCH_H §5).

    For each cluster, apply Holm-Bonferroni step-down across its variants' raw
    p-values; the cluster is **carried forward only if its best-Sharpe member
    survives** the Holm-adjusted threshold. Returns, per cluster id:
    ``representative``, ``representative_sharpe``, ``n_variants``,
    ``survived`` (bool), and ``holm_survivors`` (the surviving members).
    """
    if not 0.0 < alpha < 1.0:
        raise ValueError("alpha must be in (0, 1)")
    clusters: dict[int, list[str]] = {}
    for cand, cl in labels.items():
        clusters.setdefault(int(cl), []).append(str(cand))

    out: dict[int, dict[str, Any]] = {}
    for cl, members in clusters.items():
        # Representative = best-Sharpe member (nan Sharpes sort last).
        rep = max(members, key=lambda c: _finite_or(sharpes.get(c), -np.inf))
        survivors = _holm_survivors({m: p_values.get(m, float("nan")) for m in members}, alpha)
        out[cl] = {
            "representative": rep,
            "representative_sharpe": _finite_or(sharpes.get(rep), float("nan")),
            "n_variants": len(members),
            "survived": rep in survivors,
            "holm_survivors": sorted(survivors),
        }
    return out


# --- internals --------------------------------------------------------------


def _representatives(
    labels: Mapping[str, int], sharpes: Mapping[str, float]
) -> tuple[dict[int, str], list[float]]:
    clusters: dict[int, list[str]] = {}
    for cand, cl in labels.items():
        clusters.setdefault(int(cl), []).append(str(cand))
    reps: dict[int, str] = {}
    rep_sharpes: list[float] = []
    for cl in sorted(clusters):
        members = clusters[cl]
        rep = max(members, key=lambda c: _finite_or(sharpes.get(c), -np.inf))
        reps[cl] = rep
        rep_sharpes.append(_finite_or(sharpes.get(rep), float("nan")))
    return reps, rep_sharpes


def _holm_survivors(p_by_member: Mapping[str, float], alpha: float) -> set[str]:
    """Holm-Bonferroni step-down; returns the set of rejected (significant) members."""
    items = [(m, p) for m, p in p_by_member.items() if np.isfinite(p)]
    m = len(items)
    if m == 0:
        return set()
    items.sort(key=lambda kv: kv[1])
    survivors: set[str] = set()
    for rank, (member, p) in enumerate(items):  # rank 0-indexed
        threshold = alpha / (m - rank)
        if p <= threshold:
            survivors.add(member)
        else:
            break  # step-down stops at the first failure
    return survivors


def _agglomerative_labels_by_k(dist: np.ndarray) -> dict[int, np.ndarray]:
    """UPGMA (average-linkage) agglomeration; returns labels for every K in [1, n].

    Lance-Williams update for average linkage:
        D(i+j, x) = (|i|*D(i,x) + |j|*D(j,x)) / (|i| + |j|).
    Deterministic: ties broken by lowest index pair.
    """
    n = dist.shape[0]
    D = np.array(dist, dtype=float, copy=True)
    np.fill_diagonal(D, np.inf)
    sizes = np.ones(n, dtype=float)
    active = list(range(n))
    # root[p] = current active cluster index owning point p
    root = np.arange(n)
    labels_by_k: dict[int, np.ndarray] = {n: _contiguous(root)}

    for k in range(n, 1, -1):
        # find closest active pair
        best = None
        best_d = np.inf
        for ai in range(len(active)):
            i = active[ai]
            for aj in range(ai + 1, len(active)):
                j = active[aj]
                if D[i, j] < best_d:
                    best_d = D[i, j]
                    best = (i, j)
        i, j = best  # type: ignore[misc]
        # merge j into i (UPGMA)
        for x in active:
            if x == i or x == j:
                continue
            D[i, x] = (sizes[i] * D[i, x] + sizes[j] * D[j, x]) / (sizes[i] + sizes[j])
            D[x, i] = D[i, x]
        sizes[i] += sizes[j]
        active.remove(j)
        D[j, :] = np.inf
        D[:, j] = np.inf
        root[root == j] = i
        labels_by_k[k - 1] = _contiguous(root)
    return labels_by_k


def _contiguous(root: np.ndarray) -> np.ndarray:
    """Relabel arbitrary cluster ids to contiguous 0..K-1 (stable by first seen)."""
    out = np.empty_like(root)
    mapping: dict[int, int] = {}
    for idx, r in enumerate(root):
        r = int(r)
        if r not in mapping:
            mapping[r] = len(mapping)
        out[idx] = mapping[r]
    return out


def _optimal_k(dist: np.ndarray, labels_by_k: dict[int, np.ndarray]) -> tuple[int, float]:
    """Pick K in [2, n-1] maximizing mean silhouette (RESEARCH_H §4.3)."""
    n = dist.shape[0]
    best_k = 2
    best_sil = -np.inf
    for k in range(2, n):  # silhouette undefined at k=1 and k=n
        sil = _mean_silhouette(dist, labels_by_k[k])
        if np.isfinite(sil) and sil > best_sil:
            best_sil = sil
            best_k = k
    if not np.isfinite(best_sil):
        # degenerate (e.g. n == 2): no interior K — fall back to n clusters.
        return n, float("nan")
    return best_k, float(best_sil)


def _mean_silhouette(dist: np.ndarray, labels: np.ndarray) -> float:
    """Mean silhouette score on a precomputed distance matrix."""
    n = len(labels)
    unique = np.unique(labels)
    if unique.size < 2 or unique.size >= n:
        return float("nan")
    scores = np.zeros(n, dtype=float)
    for i in range(n):
        same = labels == labels[i]
        same[i] = False
        if not same.any():
            scores[i] = 0.0  # singleton cluster
            continue
        a = dist[i, same].mean()
        b = np.inf
        for cl in unique:
            if cl == labels[i]:
                continue
            other = labels == cl
            if other.any():
                b = min(b, dist[i, other].mean())
        denom = max(a, b)
        scores[i] = 0.0 if denom == 0 else (b - a) / denom
    return float(scores.mean())


def _finite_or(value: Any, default: float) -> float:
    try:
        v = float(value)
    except (TypeError, ValueError):
        return default
    return v if np.isfinite(v) else default
