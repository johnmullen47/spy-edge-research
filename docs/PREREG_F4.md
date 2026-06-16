# Pre-Registration F4 — Overnight-Gap-Conditioned Intraday Momentum

**From:** Research session (Cowork)
**To:** Build Master (Project Build 4) — review and commit
**Date:** 2026-06-15
**Format:** `PREREG_F1`/`PREREG_F2` anatomy. Frozen before implementation. Immutable once committed;
revisions ship as `PREREG_F4_AMENDMENT_1.md`.
**Lineage:** `RESEARCH_F` candidate **F4** ("overnight-gap-conditioned MIM").
**Family (per `RESEARCH_H`):** Family 1 — Intraday Momentum, **variant** (MIM predictor conditioned on
a distinct variable: the overnight gap). Effective-N contribution set by ONC clustering.
**Status:** Specification only. Authorizes nothing.

> **⚠ OPEN QUESTION — base predictor (flagged, default chosen).** As with F3, this conditions the
> **live Baltussen MIM predictor** (`PREREG_MIM_BALTUSSEN` Config A), not the dead Gao base. Confirm
> or override before commit.
>
> **⚠ STRUCTURAL NOTE.** The Baltussen predictor `r_rod` (prev close→15:30) **already contains** the
> overnight gap as its first component. F4 therefore tests whether *separating and conditioning on*
> the overnight-gap component adds information beyond the undecomposed predictor — consistent with the
> Lou–Polk–Skouras "tug of war" that overnight and intraday returns carry distinct dynamics. This is a
> genuine incremental-information test, not a simple gate (see §3 binding pre-commitment).

---

## 1. Executive Summary (bottom line first)

**Hypothesis:** Conditioning the MIM signal on the **sign and bucketed magnitude of the overnight
gap** (today's open − prior close) improves it — e.g., momentum is stronger/cleaner when the overnight
gap and the intraday move **agree**, and weaker/noisier when they disagree (overnight↔intraday
tug-of-war).

**One frozen configuration:** the `PREREG_MIM_BALTUSSEN` Config-A predictor and position, with an
overnight-gap conditioner that (a) gates activation by gap-magnitude bucket and (b) optionally
modulates position by gap-sign agreement.

**Honest expected range (pre-registered):**
- Net edge / Sharpe: **comparable to base MIM** (~0–10 bps; DSR ~0.3–0.7).
- **Dominant risk = no incremental information.** Because `r_rod` already embeds the gap, F4 must beat
  the undecomposed base predictor **out-of-sample** (binding, §3). If it doesn't, it is a redundant
  re-parameterization and is dropped.
- Probability of clearing **and** beating the base: **~15–25% if real; <5% if noise.**

**Data:** SPY 1-min bars only (overnight gap = today's open vs prior close). **On hand. Not blocked.**

## 2. Scope
- **In scope:** add an overnight-gap conditioner (gate + optional sign-agreement modifier) to the live
  MIM predictor; read-only forward labels.
- **Out of scope:** changing the core predictor/horizon/direction; GEX/options conditioning; sizing;
  execution; cells outside §3.

## 3. The frozen, pre-registered configuration
- **Base signal:** `PREREG_MIM_BALTUSSEN` Config A (predictor prev close→15:30; trade 15:30→16:00;
  threshold grid {0, 0.10%, 0.25%, 0.50%}).
- **Overnight gap (causal):** `gap = open_t − close_{t−1}` (log), known at 09:30, well before the
  trade. Bucketed by pre-declared magnitude terciles of a **shifted trailing** gap distribution (no
  current-day leakage).
- **Conditioner variants (pre-declared):**
  - **G1 — magnitude gate:** trade only when |gap| is in the top trailing tercile (large-gap days).
  - **G2 — sign-agreement modifier:** take the momentum position only when `sign(gap) == sign(r_rod)`
    (overnight and intraday agree); stand aside on disagreement.
  - **G3 — combined:** G1 ∧ G2.
- **Binding incremental-value pre-commitment:** F4 net Sharpe must exceed the undecomposed
  base-MIM net Sharpe **out-of-sample**. (Mirrors F1/F3 discipline.)
- **Grid:** 4 thresholds × 3 conditioner variants (G1/G2/G3) = **12 candidates**, frozen, booked into
  the trial budget (clustered per RESEARCH_H).

## 4. Anti-snooping controls (binding one named)
- **Walk-forward OOS on a calmer held-out sub-period** — must reproduce.
- **Deflated Sharpe Ratio with N = effective-N (`RESEARCH_H`) — binding.** F4's 12 cells enter ONC
  clustering with MIM/F1/F2/F3; within-cluster **Holm-Bonferroni** at candidacy.
- **PBO via CSCV** ≤ 0.50; **Hansen's SPA** report-only.

## 5. Negative / placebo controls
- **Scrambled-gap placebo:** permute the daily gap labels; edge must vanish.
- **Random-direction placebo.**
- **Decomposition-redundancy check (F4-specific):** if the undecomposed base predictor matches F4's
  net Sharpe OOS, the gap conditioning adds no information → drop.

## 6. Cost model
Identical regime-aware model to `PREREG_MIM_BALTUSSEN` §6 (time-of-day + VIX-regime aware, closing
window modeled, high-vol cost co-movement charged). Note: gating to large-gap days may concentrate
trades on higher-cost sessions — charged honestly.

## 7. Acceptance criteria (ALL required)
1. Positive **net** edge after costs on the active subset.
2. Clears **DSR (effective-N)** + within-cluster Holm.
3. **PBO ≤ 0.50**.
4. Reproduces in **walk-forward OOS (calmer sub-period)**.
5. Vanishes under both placebos.
6. **Beats the undecomposed base MIM out-of-sample** (the §3 incremental pre-commitment).

## 8. What would falsify F4
Fails DSR/PBO/walk-forward; **or** net edge ≈ 0 after costs; **or** no incremental value over the
undecomposed base. On failure, drop F4 — do not re-slice gap buckets.

## 9. Non-goals
No predictor change; no GEX; no sizing; no execution. One frozen conditioner set, full harness.

**HANDOFF status note (Research does not edit HANDOFF.md):** PREREG_F4 filed — overnight-gap
conditioning (magnitude gate / sign-agreement modifier) on the **live Baltussen MIM**, 12 frozen
cells; binding test = incremental information beyond the undecomposed predictor (which already embeds
the gap). Data on hand; not blocked.

---

## Sources
- Lou, Polk & Skouras, "A Tug of War: Overnight Versus Intraday Expected Returns," *JFE* (2019). https://personal.lse.ac.uk/polk/research/TugOfWar.pdf
- Akbas, Boehmer, Jiang & Koch, "Overnight returns, daytime reversals, and future stock returns," *JFE* (2021). https://www.sciencedirect.com/science/article/abs/pii/S0304405X21004116
- Baltussen, Da, Lammers & Martens, "Hedging Demand and Market Intraday Momentum," *JFE* (2021). https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3760365
- Internal: `PREREG_MIM_BALTUSSEN.md`, `RESEARCH_H_N_Count_Correction_DSR_Amendment.md`, `RESEARCH_F_Signal_Discovery.md`.

*Research only. No order routing, broker, options, position sizing, or live execution. Where this
conflicts with the authoritative briefs, those govern.*
