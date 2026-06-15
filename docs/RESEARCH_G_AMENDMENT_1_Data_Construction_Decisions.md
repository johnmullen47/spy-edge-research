# Research G — Amendment 1: Data Construction Decisions (F1)

**From:** Research session (Cowork)
**To:** Build Master (Code session) — review and commit
**Date:** 2026-06-15
**Status:** Binding pre-registration addendum. Resolves the open questions in
`RESEARCH_G_F1_Options_Data_Sourcing.md` §5. **Must be committed before the F1 implementation
milestone begins.** Immutable once committed; further changes ship as `RESEARCH_G_AMENDMENT_2.md`.
**Amends:** `RESEARCH_G_F1_Options_Data_Sourcing.md` (§5 Q2/Q3/Q4/Q5/Q6) and refines
`PREREG_F1_gamma_gated_momentum.md` (§3 gate source; §4.2 trial-budget cells) — **via this new
document, not by editing either immutable original.**
**Commit convention:** `research: add RESEARCH_G_AMENDMENT_1_Data_Construction_Decisions.md from Cowork Master Agent`

---

## 0. Purpose

`RESEARCH_G` §5 left seven construction questions open. John has now resolved all decision-bearing
ones; this addendum locks them as binding pre-registration choices so the F1 gamma gate is fully
specified before any backtest code is written. **With Decision 3 below, every open question in the
amendment is closed.** Locking these degrees of freedom pre-result is what keeps the gamma-sign gate
from being implicitly calibrated against the outcomes it is meant to predict.

## 1. Decision 1 — Gamma source: **SPX option chains** (locked)

The net-dealer-gamma gate for F1 is computed from **SPX index option chains**, not SPY.

- **Rationale:** institutional dealer positioning concentrates in SPX (large notional per contract;
  the primary index-hedging vehicle). SPY and SPX are ~0.995 correlated, so the gamma-regime *sign*
  transmits cleanly to SPY price action even though the absolute notional scales differ.
- **Why the cross-instrument choice is safe for F1 specifically:** the F1 gate uses only the **sign**
  of net dealer gamma (negative → momentum regime; non-negative → reversal/stand-aside). A sign gate
  is invariant to the SPX-vs-SPY notional scaling (≈10× level, $100 multiplier, OI differences) —
  only the sign of the aggregate must transmit, and at ~0.995 correlation it does. Trades are still
  executed in SPY (unchanged); only the *gate input* is SPX.
- **Supersession of `PREREG_F1`:** PREREG_F1 §4.2 booked four cells —
  {primary stand-aside, secondary flip} × {SPX-based GEX, SPY-based GEX robustness}. This amendment
  **designates SPX-based GEX as the locked primary source** and **moves the SPY-based GEX variant to
  a deferred, post-result robustness check** (not part of the primary F1 run). Net effect: F1's
  **primary trial budget drops from 4 cells to 2** ({stand-aside, flip} × {SPX}). This is the correct
  direction — fewer researcher degrees of freedom, fewer trials. Per `RESEARCH_H`, the deferred
  SPY-based and 0DTE-inclusive variants, **if** later run, must be counted as additional trials in
  the effective-N budget.

## 2. Decision 2 — 0DTE handling: **exclude 0DTE; use ≥1DTE only** (locked, primary analysis)

The net-dealer-gamma sum **excludes same-day-expiry (0DTE) contracts**; only contracts with
**≥1 day to expiry as of the prior-session EOD snapshot** enter the gamma computation.

- **Rationale:** 0DTE gamma magnitude exploded post-2022 and would impose a **structural break** in
  the gamma series if included, making pre-2022 and post-2022 regime signs non-comparable. Excluding
  0DTE keeps the gate definition stable across the full 2016+ study window. (0DTE contracts at an EOD
  snapshot are also largely expired/expiring and add noise rather than dealer-positioning signal at
  that timestamp.)
- **Precise rule:** when computing net dealer gamma from the prior-session end-of-day SPX chain,
  filter to `DTE ≥ 1` as of that snapshot date.
- **Status:** this is the **primary analysis**. A **0DTE-inclusive sensitivity** is **permitted only
  as a post-result robustness check**, after the primary F1 verdict, and (per `RESEARCH_H`) counts as
  an additional trial if run. It may not be substituted for the primary specification.

## 3. Decision 3 — Gamma computation method: **Polygon-provided Greeks** (locked, primary analysis)

The per-contract gamma entering the net-dealer-gamma sum is taken from **Polygon's
vendor-provided Greeks** (Polygon computes delta/gamma/theta/vega per contract).

- **Rationale:** uses the same vendor pipeline as the chains; avoids implementing and validating a
  bespoke implied-volatility solver, reducing moving parts and numerical-error surface in the primary
  build.
- **Dependency acknowledged:** this inherits Polygon's Black-Scholes assumptions (interest-rate and
  dividend treatment). This is acceptable **because the gate uses only the sign of the aggregate net
  gamma**, which is robust to modest per-contract IV/Greek differences — the same sign-invariance
  argument that justifies Decision 1.
- **Status:** **primary.** A **self-computed IV/gamma sensitivity** — solve IV from chain mid-prices
  and recompute gamma — is **permitted only as a deferred post-result robustness check**, and per
  `RESEARCH_H` counts as an additional trial if run. It may not replace the primary specification.

## 4. Data source confirmed — **Polygon.io options (2016+)**

- **Source:** Polygon.io options flat files (OPRA-sourced), SPX chains at the same tier. **WRDS** is
  out (no institutional access); **CBOE DataShop** is deprioritized on cost.
- **Study window consequence:** Polygon trade history begins **2016**, so the F1 study window is
  **2016–present**, accepting the loss of the 2010–2015 pre-0DTE years. A 2016–2026 window still
  contains a usable pre-0DTE (2016–2021) vs. 0DTE-era (2022+) contrast, at reduced statistical power
  — which the effective-N DSR harness (`RESEARCH_H`) will reflect.

## 5. Resolution map against `RESEARCH_G` §5 — all closed

| §5 Question | Resolution |
|---|---|
| Q1 — Budget (mo vs one-time) | Resolved *by source choice* — Polygon tier, not CBOE's $3k/$72k paths. |
| Q2 — Study window / source | **Polygon, 2016–present** (§4). |
| Q3 — WRDS / academic access | **No** — not factored in. |
| Q4 — SPX vs SPY gamma | **SPX** (Decision 1). |
| Q5 — Greek source vs self-computed IV/gamma | **Polygon-provided Greeks (primary)**; self-computed IV deferred (Decision 3). |
| Q6 — 0DTE handling | **Exclude (≥1DTE)** for primary; 0DTE-inclusive deferred (Decision 2). |
| Q7 — Data-source lock tag | Process step for Build Master (git tag at implementation start). |

## 6. Implementation notes (for Build Master)

1. **These decisions are locked before any F1 backtest code is written.** Tag the data-source lock at
   the F1 implementation milestone start (RESEARCH_G §5 Q7).
2. **OI-completeness verification gate (pre-backtest, blocking).** F1's gamma sum needs full-chain
   **historical open interest by strike for SPX back to 2016**. Polygon's clean historical depth is
   quotes-from-2022 / trades-from-2016, and **historical daily OI specifically** is the field most
   likely to be thin or snapshot-only pre-2022. Before committing to the backtest, verify SPX daily
   OI completeness across 2016–2021. If OI is materially incomplete pre-2022, the SPX+Polygon+2016
   combination is not buildable as specified and the choice must be revisited (a further amendment) —
   CBOE DataShop returns as the fallback. This conditions implementation; it does not reopen the
   locked decisions.
3. **Gamma computation (Q5) is locked to Polygon-provided Greeks** (Decision 3). No IV solver is
   required for the primary build; the self-computed-IV path is a deferred robustness check only.

## 7. Interaction with the harness

Locking SPX-primary + ≥1DTE + Polygon Greeks closes F1's data-construction degrees of freedom and
keeps F1's **primary cell count at 2** ({stand-aside, flip} × {SPX}). These 2 cells enter the global
effective-N trial budget per `RESEARCH_H` (clustered with the existing MIM/F2 candidates; F1 is a
Family-1 variant whose marginal effective-trial contribution is set empirically). Deferred robustness
variants (SPY-based GEX; 0DTE-inclusive; self-computed IV) are **not** counted unless and until run,
at which point each is charged as an additional trial.

**HANDOFF status note (for Build Master to incorporate; Research does not edit HANDOFF.md):**
RESEARCH_G Amendment 1 filed — F1 gamma gate locked to **SPX chains, ≥1DTE only, Polygon-provided
Greeks, Polygon 2016+**. Supersedes PREREG_F1's SPX/SPY co-equal cells (SPX now primary; SPY
deferred); F1 primary budget now 2 cells. **All amendment open questions are closed.** One blocking
pre-code item remains for Build Master: verify **SPX OI completeness for 2016–2021** (Polygon
historical OI may be thin pre-2022 → CBOE fallback if it fails).

---

*Research only. No order routing, broker, options, position sizing, or live execution. This amendment
locks data-construction choices; it changes no harness threshold. Where it conflicts with
`MASTER_PROJECT_BRIEF.md`, `CHATGPT_RESEARCH_PHASE_BRIEF.md`, or `README.md`, those are authoritative.*
