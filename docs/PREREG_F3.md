# Pre-Registration F3 — VIX-Regime-Gated Intraday Momentum

**From:** Research session (Cowork)
**To:** Build Master (Project Build 4) — review and commit
**Date:** 2026-06-15
**Format:** `PREREG_F1`/`PREREG_F2` anatomy. Frozen before implementation. Immutable once committed;
revisions ship as `PREREG_F3_AMENDMENT_1.md`.
**Lineage:** `RESEARCH_F` candidate **F3** ("VIX-regime-gated MIM").
**Family (per `RESEARCH_H`):** Family 1 — Intraday Momentum, **variant** (the MIM predictor, gated by
a distinct regime *variable*: VIX level / term-structure slope). Effective-N contribution set by ONC
clustering.
**Status:** Specification only. Authorizes nothing.

> **⚠ OPEN QUESTION — base predictor (flagged, default chosen, confirm before commit).**
> RESEARCH_F defined F3 as a gate on "the MIM signal." The pure Gao MIM is now assessed as dead
> (decay brief). Gating a dead base is pointless, so **this spec gates the *live* MIM predictor —
> the Baltussen rest-of-day return per `PREREG_MIM_BALTUSSEN` (Config A: prev close→15:30 → 15:30–16:00).**
> If you instead want F3 to gate the Gao base (for completeness) or to run on both, say so and I will
> amend before commit.

---

## 1. Executive Summary (bottom line first)

**Hypothesis:** The live MIM (Baltussen rest-of-day) edge is concentrated when the **VIX regime** is
elevated and/or the **VIX term structure** is unusually flat/inverted — periods of high uncertainty
and constrained liquidity where the gamma-hedging mechanism is strongest (Lucca & Moench; Aleti,
Bollerslev & Siggaard). F3 replaces the base realized-vol gate with a **VIX-level / term-structure
gate**.

**One frozen configuration:** the `PREREG_MIM_BALTUSSEN` Config-A predictor and position, with the
regime gate set to VIX-based buckets (below), evaluated only on gate-active days.

**Honest expected range (pre-registered):**
- Net edge and Sharpe: **comparable to the base MIM** (~0–10 bps; DSR ~0.3–0.7) — F3 is a *gate swap*,
  not a new predictor.
- **Dominant risk = redundancy.** VIX level is collinear with the base realized-vol gate, so F3 must
  prove **incremental value over the realized-vol gate** out-of-sample (binding pre-commitment, §3),
  exactly as F1 had to. If it only matches the realized-vol gate, it is a redundant variant and is
  dropped — *not* counted as a win.
- Probability of clearing **and** beating the realized-vol gate: **~15–25% if real; <5% if noise.**

**Data:** SPY 1-min (on hand) + VIX and the VIX **term-structure sub-indices** (VIX9D, VIX, VIX3M,
VIX6M) and/or VIX futures — **freely available from CBOE**. **Not blocked.**

## 2. Scope
- **In scope:** swap the base MIM regime gate for a VIX-level / term-structure-slope gate; read-only
  forward labels. Same predictor, horizon, direction as `PREREG_MIM_BALTUSSEN`.
- **Out of scope:** any change to the predictor/horizon/direction; GEX/options conditioning; sizing;
  execution; any cell outside §3.

## 3. The frozen, pre-registered configuration
- **Base signal:** `PREREG_MIM_BALTUSSEN` Config A — predictor `r_rod` (prev close→15:30), position
  `long/short/flat` at threshold τ, trade 15:30→16:00. (τ grid inherited: {0, 0.10%, 0.25%, 0.50%}.)
- **Gate variable (causal; measured at prior-session close):** one of
  {`VIX level > trailing rolling median`, `VIX level > 20`, `term-structure slope (VIX3M − VIX9D or
  VIX/VIX3M) in pre-declared "stress" bucket`}. All inputs known before the trading session.
- **Binding incremental-value pre-commitment:** the pre-registered comparison is **F3 net Sharpe
  minus the realized-vol-gated base net Sharpe on held-out data**. F3 is interesting only if this
  difference is positive OOS. (Same discipline as `PREREG_F1`.)
- **Grid:** 4 thresholds × 3 VIX-gate variants = **12 candidates**, frozen here, booked into the trial
  budget (clustered per RESEARCH_H — expected ~1 effective trial, heavily correlated with the base MIM
  and F1).

## 4. Anti-snooping controls (binding one named)
- **Walk-forward OOS on a calmer held-out sub-period** — must reproduce.
- **Deflated Sharpe Ratio with N = effective-N (`RESEARCH_H`) — binding.** F3's 12 cells enter ONC
  clustering with MIM/F1/F2; within-cluster **Holm-Bonferroni** at candidacy.
- **PBO via CSCV** ≤ 0.50.
- **Hansen's SPA** — report-only.

## 5. Negative / placebo controls
- **Scrambled-VIX-gate placebo:** permute the daily gate labels; edge must vanish.
- **Random-direction placebo.**
- **Incremental-redundancy check (F3-specific):** if removing the VIX gate (i.e., the plain
  realized-vol-gated base) yields the same net Sharpe, F3 adds nothing → drop.

## 6. Cost model
Identical regime-aware model to `PREREG_MIM_BALTUSSEN` §6 — time-of-day + VIX-regime aware, closing
window modeled, high-vol cost co-movement charged.

## 7. Acceptance criteria (ALL required)
1. Positive **net** edge after costs on the active subset.
2. Clears **DSR (effective-N)** + within-cluster Holm.
3. **PBO ≤ 0.50**.
4. Reproduces in **walk-forward OOS (calmer sub-period)**.
5. Vanishes under both placebos.
6. **Beats the realized-vol-gated base out-of-sample** (the §3 incremental pre-commitment).

## 8. What would falsify F3
Fails DSR/PBO/walk-forward; **or** net edge ≈ 0 after costs; **or** no incremental value over the
realized-vol gate (VIX gate is a redundant vol proxy). On failure, drop F3 — do not re-slice VIX
buckets.

## 9. Non-goals
No predictor change; no GEX; no sizing; no execution. One frozen gate-swap, full harness.

**HANDOFF status note (Research does not edit HANDOFF.md):** PREREG_F3 filed — VIX-level /
term-structure gate on the **live Baltussen MIM** (base-predictor choice flagged for confirmation),
12 frozen cells, binding test = incremental value over the realized-vol gate. Data free (CBOE VIX
sub-indices); not blocked.

---

## Sources
- Lucca & Moench, "The Pre-FOMC Announcement Drift," *JF* (2015) (high-implied-vol conditioning). https://onlinelibrary.wiley.com/doi/abs/10.1111/jofi.12196
- Aleti, Bollerslev & Siggaard, "Intraday Market Return Predictability…," *Mgmt Science* (2025) (high-uncertainty concentration). https://public.econ.duke.edu/~boller/Papers/MS_2025.pdf
- Baltussen, Da, Lammers & Martens, "Hedging Demand and Market Intraday Momentum," *JFE* (2021). https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3760365
- Internal: `PREREG_MIM_BALTUSSEN.md`, `RESEARCH_H_N_Count_Correction_DSR_Amendment.md`, `RESEARCH_F_Signal_Discovery.md`.

*Research only. No order routing, broker, options, position sizing, or live execution. Where this
conflicts with the authoritative briefs, those govern.*
