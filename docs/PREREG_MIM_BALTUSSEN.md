# Pre-Registration — MIM-Baltussen (Rest-of-Day Intraday Momentum)

**From:** Research session (Cowork)
**To:** Build Master (Project Build 4) — review and commit
**Date:** 2026-06-15
**Format:** Pre-registration in the `PREREG_F1`/`PREREG_F2` / `RESEARCH_C_DECISION` §4 anatomy.
Frozen before any implementation. Immutable once committed; revisions ship as
`PREREG_MIM_BALTUSSEN_AMENDMENT_1.md`.
**Lineage:** replaces/supplements the pure Gao et al. MIM signal (first-30-min/overnight predictor),
which failed Hard Gate A (0/100) and has documented post-2018 OOS failure. Existing Gao-formulation
candidates **remain in the registry as-is**; this is a new, distinct candidate set.
**Family (per `RESEARCH_H`):** Family 1 — Intraday Momentum, **variant** (same economic mechanism,
**different predictor construction**: cumulative rest-of-day return). Effective-N contribution is set
empirically by ONC clustering; expected to remain ~1 unless its returns decorrelate from the existing
MIM cluster.
**Status:** Specification only. Authorizes nothing. Strongest obtainable verdict
`eligible_for_paper_consideration`.

---

## 1. Executive Summary (bottom line first)

**Hypothesis:** The cumulative SPY return from the **previous close to 15:30 ET** ("rest-of-day"
return) positively predicts the **15:30→16:00 ET** return (momentum), because options market-maker
gamma hedging and leveraged-ETF rebalancing impose *structural, forced* end-of-day trading in the
direction of the day's move. This is a supply/demand constraint, not a behavioral/informational
effect, so it is more persistent than the Gao formulation.

**Why this, not pure Gao:** Gao's first-30-min/overnight predictor is largely arbitraged away
post-publication. Baltussen, Da, Lammers & Martens (2021, JFE) show that the *cumulative rest-of-day*
predictor + the gamma-hedging mechanism remains strong and significant across 60+ futures and asset
classes through 2020; Zarattini, Aziz & Barbon (2024) find similar conditioning works through 2024.

**Honest expected range (pre-registered, before results):**
- Net edge: **~0–10 bps per active-day trade**; could be ≤0 once the close-auction/last-30-min cost is
  honestly charged on the high-vol active subset.
- Deflated Sharpe: **~0.3–0.7**. Active on **~30–50% of days** (vol-gated).
- Probability of clearing the harness **net**: **~25–40% if the structural effect persists in SPY
  post-2020; <5% if noise.** This is above the project's base rate (mechanism is structural and the
  predictor is the *live* formulation, not the dead one), but held well below 50% because the effect
  is documented mainly in *futures* and may be weaker/cost-bound in the SPY ETF, and ~"last-30-min on
  a vol-gated subset" is exactly where execution cost co-moves with the edge.

**Data:** SPY 1-min bars (on hand) + VIX (free) for the regime gate. No new data purchase. Not blocked.

## 2. Scope
- **In scope:** one rest-of-day-momentum predictor on existing SPY 1-min bars, into the last-30-min
  window, with a single high-vol regime gate; read-only forward labels for scoring (no-lookahead).
- **Out of scope (non-goals):** order routing, broker, options, sizing/leverage, ES/futures migration
  (a separate future family), GEX conditioning (the shelved F1 path; not in this freeze),
  magnitude-scaled position sizing (explicitly deferred, §3), any predictor/threshold/window not in
  the §3 grid, any tuning after the freeze.

## 3. The frozen, pre-registered configuration grid

- **Predictor (causal):** `r_rod = cumulative SPY log return from prior-session close to 15:30 ET`,
  computed from 1-min bars with timestamp ≤ 15:30. No bar after 15:30 enters the feature.
- **Outcome:** SPY log return over the trade window (see Config A/B), resolved at the 16:00 close.
- **Position (momentum):** `long if r_rod > +τ ; short if r_rod < −τ ; flat otherwise`. Emitted at the
  trade-window open, resolved at 16:00. **A magnitude-scaled position variant (`clip(r_rod/σ_rod)`) is
  explicitly DEFERRED — not part of this pre-registration.** If pursued later it ships as an amendment
  and is charged as additional trials.
- **Regime gate (causal; measured at prior-session close so it is known pre-trade):** one of
  {`unconditional` (baseline), `VIX > 20`, `VIX > trailing rolling median`, `GARCH(1,1) conditional
  vol > trailing median`}.
- **Threshold τ:** {0, 0.10%, 0.25%, 0.50%}.
- **Trade-window configs (no overlap with predictor; no lookahead):**
  - **Config A (primary, Baltussen-canonical):** predictor → 15:30; trade 15:30→16:00.
  - **Config B (secondary):** predictor → 15:00; trade 15:00→16:00.
- **Grid size:** 4 thresholds × 4 regime settings × 2 configs = **32 candidates** (the magnitude-scaled
  variant is deferred and not included). **All 32 are frozen here**; the full count is booked into the
  trial budget (§4).

## 4. Anti-snooping controls (all required; binding one named)
- **Chronological train/test + walk-forward OOS** — final arbiter; must reproduce on a **calmer
  held-out sub-period**, not only a vol-rich window. (The Gao formulation's failure was precisely
  post-sample collapse.)
- **Deflated Sharpe Ratio with N = effective-N (per `RESEARCH_H`) — THE BINDING CONTROL.** The 32
  variants here are **within-family parameter variants**: they enter ONC clustering with the existing
  MIM/F2 candidates and are expected to collapse to ~1 effective trial, **not** 32 independent DSR
  trials. Within-cluster **Holm-Bonferroni** controls the candidacy selection across these variants
  (per `RESEARCH_H` §5). `σ_SR` is computed across cluster representatives.
- **PBO via CSCV** — PBO ≤ 0.50 pass gate.
- **Hansen's SPA** — report-only; DSR/PBO binding.

## 5. Negative / placebo controls
- **Scrambled-predictor placebo:** permute the day↔predictor mapping; edge must vanish.
- **Random-direction placebo:** apply the regime gate to a random-sign signal; edge must vanish.
- **Reversion check (mechanism confirmation):** per Baltussen, the effect should **revert over the
  following days** (structural, not informational). A pre-registered diagnostic: the captured
  last-30-min move partially reverses next session. Failure of reversion weakens the structural claim
  (flag, not an automatic kill).

## 6. Cost model (binding economic control)
`cost_bps(t) = half_spread_bps(t) + k·σ_intraday(t) + impact_sqrt(Q/ADV)`, **time-of-day and
VIX-regime aware**, with explicit modeling of the **15:30–16:00 window and closing-auction dynamics**
(where this strategy trades). Negative-gamma/high-vol days carry higher cost; a flat cost is
prohibited. Net edge is judged after charging the high-vol-day cost co-movement.

## 7. Acceptance criteria (`eligible_for_paper_consideration` only if ALL hold)
1. Positive **net** edge after the regime-aware cost model on the active subset.
2. Clears **Deflated Sharpe Ratio** with **N = effective-N** (RESEARCH_H) and the within-cluster Holm
   candidacy screen.
3. Clears **PBO ≤ 0.50** via CSCV.
4. Reproduces in **walk-forward OOS on a calmer held-out sub-period**.
5. Edge **vanishes under both placebos** (scrambled predictor, random direction).

## 8. What would falsify (route to null / drop this family)
Fails DSR (effective-N) **or** PBO > 0.50 **or** fails walk-forward on the calmer sub-period; **or**
net edge indistinguishable from zero after cost co-movement; **or** edge survives only on a hand-picked
cell. On failure, do **not** re-slice into finer thresholds/windows — drop the Baltussen variant and
route to the F3/F4/F5 candidates or the null.

## 9. Non-goals (restated for the implementer)
No magnitude-scaled sizing (deferred); no GEX/options conditioning (shelved F1); no ES/futures
migration; no grid beyond §3; no execution. One frozen predictor family, full harness, honest verdict.

**HANDOFF status note (for Build Master; Research does not edit HANDOFF.md):** PREREG_MIM_BALTUSSEN
filed — rest-of-day predictor (prev close→15:30) → 15:30–16:00 momentum, high-vol-gated, **32 frozen
variants** = one within-family cluster under RESEARCH_H (effective-N ~+1, not +32). Magnitude-scaled
sizing deferred. Runnable on existing SPY+VIX data. Gao-formulation candidates retained unchanged.

---

## Sources
- Baltussen, Da, Lammers & Martens, "Hedging Demand and Market Intraday Momentum," *JFE* (2021). https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3760365
- Gao, Han, Li & Zhou, "Market Intraday Momentum," *JFE* (2018) (formulation being superseded). https://www.sciencedirect.com/science/article/abs/pii/S0304405X18301351
- Rosa, OOS failure of Gao MIM, *J. Futures Markets* (2022). https://onlinelibrary.wiley.com/doi/abs/10.1002/fut.22375
- Zarattini, Aziz & Barbon, "Beat the Market…SPY" (2024; gamma-conditioned, through 2024; practitioner). https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4824172
- Bailey & López de Prado, "The Deflated Sharpe Ratio." https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2460551
- Internal: `RESEARCH_H_N_Count_Correction_DSR_Amendment.md`, `RESEARCH_F_Signal_Discovery.md`.

*Research only. No order routing, broker, options, position sizing, or live execution. Where this
conflicts with `MASTER_PROJECT_BRIEF.md`, `CHATGPT_RESEARCH_PHASE_BRIEF.md`, or `README.md`, those are
authoritative.*
