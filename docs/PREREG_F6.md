# Pre-Registration F6 — Variance-Risk-Premium (VRP) Timing

**From:** Research session (Cowork) · **To:** Build Master (Project Build 5) — review and commit
**Date:** 2026-06-15 · Frozen before implementation; immutable once committed.
**Lineage:** RESEARCH_I — method #2 (risk-premia bucket).
**Family (per RESEARCH_H):** NEW Family 3 — Variance Risk Premium timing. Expected to add ~1 effective trial.
**Status:** Specification only. Authorizes nothing.

## 1. Executive Summary
**Hypothesis:** `VRP = VIX²(scaled) − realized variance` positively predicts subsequent SPY returns
(Bollerslev, Tauchen & Zhou 2009, RFS). F6 times SPY exposure on the VRP.

**Honest expected range:** deflated Sharpe ~0.2–0.5, low turnover. Two limits: (i) effect is
weekly–quarterly, not intraday — power-limited on ~2yr sample; (ii) tradable edge far smaller than R².
**P(clear net) ~20–30% if premium persists; <5% if noise.**

**Data:** SPY 1-min (→ realized variance) + VIX daily. No purchase. Not blocked.
**Distinctness:** VIX as a *premium vs realized* — not the VIX level gate of F3.

## 2. Scope
- In scope: VRP-conditioned SPY timing signal at daily/weekly horizon; causal labels.
- Out of scope: options/variance-swap execution, sizing/leverage, broker.

## 3. Frozen configuration grid
- **Predictor (causal):** `VRP_t = (VIX_t)²·(21/252) − RV_t`, where `RV_t` = trailing 21-session
  realized variance from SPY 1-min returns, computed through prior session close. Standardized by
  shifted trailing distribution.
- **Outcome:** forward SPY return over holding horizon H.
- **Position:** `long if VRP_z > +τ ; short if VRP_z < −τ (long/short variant) ; flat otherwise`.
- **Grid:** H ∈ {5 sessions, 21 sessions} × τ ∈ {0, +0.5σ, +1.0σ} × direction ∈ {long-only, long/short}
  = **12 candidates**, frozen, booked into trial budget.

## 4. Anti-snooping controls
- Walk-forward OOS on calmer held-out sub-period — final arbiter.
- DSR with effective-N (RESEARCH_H) + Holm-Bonferroni. Power caveat: report independent holding-period
  observations; "insufficient power" verdict if H=21 leaves too few.
- PBO via CSCV ≤ 0.50; Hansen SPA report-only.

## 5. Placebo controls
- Scrambled-VRP placebo (permute VRP↔date; edge must vanish).
- Random-direction placebo.
- **Realized-vol-only placebo (binding):** replace VRP with realized variance alone; if it matches,
  the premium is not the source → demote.

## 6. Cost model
Regime-aware per PREREG_MIM_BALTUSSEN §6; low turnover (weekly/monthly), so cost is second-order.

## 7. Acceptance criteria (ALL)
Net edge after costs · DSR + Holm · PBO ≤ 0.50 · Walk-forward OOS · Vanishes under all placebos ·
NOT reproduced by realized-vol-only placebo.

## 8. What would falsify F6
DSR/PBO/walk-forward fail; or net edge ≈ 0; or realized-vol-only placebo matches; or insufficient power.

## 9. Non-goals
No variance-swap/options execution; no sizing/leverage; no intraday re-slicing.

**HANDOFF note:** PREREG_F6 — VRP timing (implied−realized), NEW Family 3, 12 cells, data on hand.
Binding risks: low-sample power + premium-vs-vol-level confound.

## Sources
- Bollerslev, Tauchen & Zhou, RFS 22(11):4463–4492 (2009). https://academic.oup.com/rfs/article-abstract/22/11/4463/1565787
- Carr & Wu, RFS (2009). https://academic.oup.com/rfs/article-abstract/22/3/1311/158378
- Internal: RESEARCH_H, RESEARCH_I.

*Research only. No order routing, broker, options, position sizing, or live execution.*
