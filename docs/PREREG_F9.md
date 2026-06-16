# Pre-Registration F9 — Intraday Periodicity (Same-Bucket Continuation)

**From:** Research session (Cowork) · **To:** Build Master (Project Build 5) — review and commit
**Date:** 2026-06-15 · Frozen before implementation; immutable once committed.
**Lineage:** RESEARCH_I — method #5 (microstructure / rebalancing bucket).
**Family (per RESEARCH_H):** NEW Family 6 — Intraday periodicity. Adds ~1 effective trial.
**Status:** Specification only. Authorizes nothing.

## 1. Executive Summary
**Hypothesis:** SPY returns exhibit continuation at half-hour intervals that are exact multiples of a
trading day — the return in a given half-hour predicts the return in the same half-hour on subsequent
days (Heston, Korajczyk & Sadka 2010, JF; mechanism: Bogousslavsky 2016).

**Honest expected range — with structural caveat:** the effect is cross-sectional (across many stocks);
on a single instrument (SPY) it reduces to own same-bucket autocorrelation, weaker and contaminated by
bid-ask bounce. **Deflated Sharpe ~0.1–0.4; P(clear net) ~10–20%.** High turnover → cost-sensitive.
Bounce placebo is the binding control.

**Data:** SPY 1-min. No purchase. Not blocked. *(Single-asset limitation flagged — see §8.)*

## 2. Scope
- In scope: same-half-hour-bucket continuation signal on SPY; causal labels.
- Out of scope: cross-sectional/multi-stock (the effect's native form), options, leverage.

## 3. Frozen configuration grid
- **Bucketing:** 13 half-hour RTH buckets/day.
- **Predictor for bucket b on day t:** aggregate of same-bucket return on prior days via lag set L.
- **Lag aggregation L:** {1 trading day, mean of last 5 same-bucket returns, mean of last 40 same-bucket
  returns (HKS horizon)}.
- **Position:** continuation — `long if agg > +τ ; short if < −τ`; held one bucket (30 min), EOD-flat.
- **Threshold τ:** {0, trailing-σ}.
- **Scope variants:** {all 13 buckets, first+last bucket only}.
- **Grid:** 3 lags × 2 thresholds × 2 scope = **12 candidates**, frozen.

## 4. Anti-snooping controls
- Walk-forward OOS, calmer sub-period.
- DSR with effective-N + Holm.
- PBO via CSCV ≤ 0.50; Hansen SPA report-only.

## 5. Placebo controls
- **Bounce-only synthetic placebo (mandatory, binding for F9):** simulate returns under pure bid-ask
  bounce; strategy must show no edge. If it does, "periodicity" is mechanical bounce → kill.
- Scrambled-bucket placebo (permute bucket↔lag mapping; edge must vanish).
- Random-direction placebo.

## 6. Cost model
Regime-aware per PREREG_MIM_BALTUSSEN §6; **full half-spread at every bucket entry** (high turnover).
Net edge must be distinguishable from the half-spread.

## 7. Acceptance criteria (ALL)
Net edge distinguishable from half-spread · DSR + Holm · PBO ≤ 0.50 · Walk-forward · All placebos
survived (including bounce-only).

## 8. What would falsify F9
DSR/PBO/walk-forward fail; or net edge ≈ half-spread; or edge appears on bounce-only synthetic; or
single-asset version too weak. On failure: drop — native effect is cross-sectional, out of scope.

## 9. Non-goals
No cross-sectional/multi-stock build; no options; no leverage; no sizing.

**HANDOFF note:** PREREG_F9 — same-half-hour-bucket SPY, NEW Family 6, 12 cells, data on hand.
Flagged limitation: native effect is cross-sectional; SPY-only is degraded and bounce-prone.
Binding controls: bounce-only synthetic placebo + half-spread test.

## Sources
- Heston, Korajczyk & Sadka, JF 65(4) (2010). https://onlinelibrary.wiley.com/doi/abs/10.1111/j.1540-6261.2010.01573.x
- Bogousslavsky, JF 71(6) (2016). https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2308366
- Internal: RESEARCH_H, RESEARCH_I.

*Research only. No order routing, broker, options, position sizing, or live execution.*
