# Pre-Registration F7 — Volatility-Managed Exposure

**From:** Research session (Cowork) · **To:** Build Master (Project Build 5) — review and commit
**Date:** 2026-06-15 · Frozen before implementation; immutable once committed.
**Lineage:** RESEARCH_I — method #3 (risk-management bucket).
**Family (per RESEARCH_H):** NEW Family 4 — Volatility-managed exposure. Adds ~1 effective trial.
**Status:** Specification only. Authorizes nothing.

## 1. Executive Summary
**Hypothesis:** Scaling SPY exposure inversely to conditional volatility improves risk-adjusted return
(Moreira & Muir 2017, JF).

**Honest expected range — deliberately LOW.** This is actively contested. Cederburg et al. (2020) find
no OOS outperformance; Barroso & Detzel find it doesn't survive costs; DeMiguel et al. (2024) confirm
in-sample alpha is largely not implementable in real time. **Pre-registered expectation: likely failure.
Deflated Sharpe ~0.0–0.3; P(clear net) ~10–20%. F7's value is adjudication, not edge.**

**Data:** SPY 1-min (realized vol) + VIX daily. No purchase. Not blocked.

## 2. Scope
- In scope: inverse-vol position-weighting timing rule on SPY; read-only forward labels.
- Out of scope: leverage > 1 (de-risking only, weights ∈ [0,1]), options, broker.

## 3. Frozen configuration grid
- **Vol estimator (causal, through prior close):** σ̂_t ∈ {trailing 21-session realized vol from
  SPY 1-min, VIX level, GARCH(1,1) conditional vol}.
- **Weight:** `w_t = clip(σ_target / σ̂_t, 0, 1)` (de-risking only).
- **Outcome:** w_t × next-period SPY return.
- **Grid:** 3 vol estimators × σ_target ∈ {trailing-median σ̂, 10% annualized} × rebalance ∈
  {daily, weekly} = **12 candidates**, frozen.

## 4. Anti-snooping controls
- Walk-forward OOS, calmer sub-period — decisive (the literature's whole dispute is OOS). Must beat
  buy-and-hold SPY net Sharpe out-of-sample.
- DSR with effective-N (own cluster, ~+1); within-cluster Holm.
- PBO via CSCV ≤ 0.50; Hansen SPA report-only.
- **Turnover/cost gate (binding):** net of regime-aware cost at every rebalance, managed Sharpe must
  exceed unmanaged.

## 5. Placebo controls
- Scrambled-vol placebo (permute σ̂↔date; Sharpe improvement must vanish).
- **Constant-weight placebo (binding):** fixed average weight must NOT match managed Sharpe.

## 6. Cost model
Regime-aware per PREREG_MIM_BALTUSSEN §6; turnover is the binding term.

## 7. Acceptance criteria (ALL)
Managed net Sharpe > unmanaged OOS · DSR + Holm · PBO ≤ 0.50 · Walk-forward · Both placebos survived.

## 8. What would falsify F7 (expected)
No OOS Sharpe improvement; or improvement erased by cost; or constant-weight placebo matches; or
fails DSR/PBO. **A clean failure is the expected, informative result.**

## 9. Non-goals
No leverage; no options; no sizing; no intraday re-slicing.

**HANDOFF note:** PREREG_F7 — inverse-vol exposure, NEW Family 4, 12 cells, data on hand.
Pre-registered as likely-fail adjudication; binding controls: OOS + turnover-cost + constant-weight placebo.

## Sources
- Moreira & Muir, JF 72(4) (2017). https://onlinelibrary.wiley.com/doi/abs/10.1111/jofi.12513
- Cederburg et al., JFE (2020). https://www.sciencedirect.com/science/article/abs/pii/S0304405X2030132X
- DeMiguel et al., JF (2024). https://onlinelibrary.wiley.com/doi/full/10.1111/jofi.13395
- Internal: RESEARCH_H, RESEARCH_I.

*Research only. No order routing, broker, options, position sizing, or live execution.*
