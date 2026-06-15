# Pre-Registration F1 — Gamma-Sign-Gated Intraday Momentum

**From:** Research session (Cowork)
**To:** Build Master (Code session) — review and commit
**Date:** 2026-06-15
**Format:** Pre-registration in `RESEARCH_C_DECISION.md` §4 anatomy. Frozen before any conditional
results are viewed. Per the pre-registration integrity rule, this file is immutable once committed;
revisions ship as `PREREG_F1_AMENDMENT_1.md`.
**Lineage:** `RESEARCH_F_Signal_Discovery.md` candidate **F1**. Mechanism: dealer option-gamma sign
conditions whether intraday flow amplifies (momentum) or dampens (reversal) an initial move.
**Status:** Specification only. Authorizes nothing. Strongest obtainable verdict
`eligible_for_paper_consideration`.

---

## 1. Executive Summary (bottom line first)

**Hypothesis:** Intraday time-series momentum on SPY is conditional on the dealer gamma regime —
it is present when aggregate dealer gamma is **net-negative** (hedging trades *with* the move) and
absent/reversing when **net-positive** (hedging trades *against* it). Gate on the sign of estimated
net dealer gamma, known from the **prior session's** option chain (causal, no-lookahead).

**One frozen configuration:** `sign(r_open)` over the 09:30–10:00 ET window, taken **only on
net-negative-gamma days**, resolved at the regular-session close; stand aside on net-positive-gamma
days (primary). A single pre-declared secondary flips to reversal on net-positive days.

**Honest expected range (pre-registered, before results):**
- Net edge: **~0–10 bps per active-day trade** (could be ≤0 after high-vol cost co-movement).
- Deflated Sharpe: **~0.2–0.6**. Active on **~30–50% of days** (negative-gamma days are common).
- Probability of clearing the full harness **net**: **~25–35% if the effect is real *and incremental
  to the realized-vol gate*; <5% if it is noise** (the harness's designed Type-I rate).
- **Dominant risk:** gamma-negative days ≈ high-vol days, so the gamma gate may be a noisy proxy for
  the realized-vol gate already under test (Path 2). F1 must prove **incremental** value or it is
  redundant (see §3, §6).

**Data dependency (blocker flag):** F1 requires historical end-of-day SPX **or** SPY option chains
(open interest by strike) across the sample to estimate net gamma. If that data is not yet in the
repo, **F1 is blocked pending acquisition** — F2 (price-only) is runnable now and should precede it.

## 2. Scope

- **In scope:** one intraday TSM signal on existing SPY 1-min bars, gated by the **sign** of a
  causally-estimated net dealer-gamma series derived from prior-session option open interest.
  Read-only forward labels for scoring (no-lookahead contract).
- **Out of scope (non-goals):** order routing, broker, options *execution*, sizing/leverage, ES
  migration, intraday-updating gamma, multi-threshold gamma grids, any second signal family, any
  tuning after the freeze. Using option data to *estimate the gate* is in scope; trading options is not.

## 3. The ONE frozen, pre-registered configuration

- **Signal (causal):** at 10:00 ET compute `r_open` from 1-min bars in 09:30–10:00 (≤10:00 only).
  Position emitted at the 10:00 close, resolved at the 16:00 close. No future bar touches the feature.
- **Gate — net dealer gamma SIGN (single, binary, theory-derived):** from the **prior session's**
  end-of-day option chain, compute net dealer gamma
  `GEX = Σ_k γ_k · OI_k · 100 · S² · sign_k`, under the pre-registered naive dealer-sign convention
  (dealer long calls / short puts). The **sign of GEX** (negative vs. non-negative), fixed from the
  prior close, is the only gate. It is known before 09:30 → strictly causal.
  - **Primary:** trade `sign(r_open)` only when `GEX < 0`; stand aside when `GEX ≥ 0`.
  - **Secondary (one pre-declared variant, counted in N):** when `GEX ≥ 0`, take `−sign(r_open)`
    (reversal).
- **Incremental-value pre-commitment (binding, see §6):** the gamma gate must outperform the
  **realized-vol gate baseline** (Path 2's gate) on the *same* signal. The pre-registered comparison
  is the gamma-gated net Sharpe minus the vol-gated net Sharpe on held-out data; F1 is only
  interesting if this difference is positive out-of-sample.
- **Frozen in advance:** window definition, GEX formula + sign convention, gate threshold (sign=0
  boundary), forward window, cost-model parameters, and the **N contribution** (see §4.2). No
  post-freeze degrees of freedom.

## 4. Anti-snooping controls (all required; binding one named)

### 4.1 Controls
- **Chronological train/test + walk-forward OOS** — final arbiter; must reproduce on a **calmer
  held-out sub-period**, not only the vol-rich window.
- **Deflated Sharpe Ratio, N = every cell ever evaluated — THE BINDING CONTROL.** N includes the
  F1 cells **and** all cells from Path 2 and any other family in the frozen discovery budget
  (`RESEARCH_F` §4.2: N≈80–150). F1's failure mode is selection across regime gates on a short
  sample; DSR is the tool for exactly that.
- **PBO via CSCV** — report PBO < 50% as a pass gate.
- **Hansen's SPA** — search-aware p-value; report, DSR/PBO binding.
- **Benjamini–Hochberg FDR** — valid only if N is honestly enumerated; no post-hoc cells without
  re-counting.

### 4.2 Trial-budget (N) contribution — pre-registered
F1 books **4 cells**: {primary stand-aside, secondary flip} × {SPX-based GEX, SPY-based GEX
robustness}. These 4 are added to the global frozen N before results are viewed. The SPY-based GEX
is a robustness axis, not a free second shot.

## 5. Negative / placebo controls
- **Scrambled-gamma-sign placebo:** randomly permute the daily GEX-sign labels across days; the edge
  must vanish. If a scrambled gamma sign "works," the gate is noise.
- **Random-direction placebo:** apply the gamma gate to a random-sign signal; the edge must vanish.
- **Sign-convention robustness:** re-estimate GEX under an alternative dealer-sign assumption; the
  result must not hinge on a single convention. Dependence on one convention is fragility (flag; kills
  only if the surviving convention is also the one that fails OOS).

## 6. Cost model (binding economic control)
`cost_bps(t) = half_spread_bps(t) + k·σ_intraday(t) + impact_sqrt(Q/ADV)`, **time-of-day and
VIX-regime aware**. Negative-gamma days are disproportionately high-vol, so cost co-moves with the
active subset; a flat cost is prohibited (it would flatter the strategy and book a phantom edge). Net
edge is judged **after** charging the high-vol-day cost co-movement.

## 7. Acceptance criteria (`eligible_for_paper_consideration` only if ALL hold)
1. Positive **net** edge after the regime-aware cost model on the active (negative-gamma) subset.
2. Clears **Deflated Sharpe Ratio** with N = every cell tested (incl. Path 2 + F1 cells).
3. Clears **PBO < 50%** via CSCV.
4. Reproduces in **walk-forward OOS on a calmer held-out sub-period**.
5. Edge **vanishes under both placebos** (scrambled gamma, random direction).
6. **Incremental over the realized-vol gate** out-of-sample (the §3 pre-commitment) — F1 must beat,
   not merely match, the vol gate.
7. Not dependent on a single GEX sign convention.

## 8. What would falsify F1 (route to null / drop F1)
Any one of: fails DSR (full N) **or** PBO ≥ 50% **or** fails walk-forward on the calmer sub-period;
**or** net edge indistinguishable from zero after cost co-movement; **or** no incremental value over
the realized-vol gate (the gamma gate is then a redundant vol proxy); **or** the edge needs a single
hand-picked GEX convention. On failure, do **not** re-slice into finer gamma buckets (the canonical
false-discovery move) — drop F1 and proceed to F2 / remaining candidates.

## 9. Non-goals (restated for the implementer)
No intraday-updating gamma; no grid over windows/thresholds; no options execution; no sizing; no ES.
One frozen hypothesis, full harness, honest verdict.

**HANDOFF status note (for Build Master; Research does not edit HANDOFF.md):** PREREG F1 filed —
gamma-sign-gated MIM, **blocked pending EOD option-chain data**; binding test is incremental value
over the realized-vol gate. Sequence after F2 (which is runnable on existing data).

---

## Sources
- Baltussen, Da & Soebhag, "End-of-Day Reversal" (dealer-hedging / LETF mechanism; t=−6.28). https://www3.nd.edu/~zda/EOD.pdf
- Dim, Eraker & Vilkov, "0DTEs: Trading, Gamma Risk and Volatility Propagation." https://papers.ssrn.com/sol3/papers.cfm?abstractid=4692190
- Cboe, "0DTE Index Options and Market Volatility." https://cdn.cboe.com/resources/education/research_publications/gammasqueezes.pdf
- Zarattini, Aziz & Barbon, "Beat the Market…SPY" (gamma-imbalance tests; practitioner, see RESEARCH_C caveat). https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4824172
- Gao, Han, Li & Zhou, "Market Intraday Momentum" (MIM baseline, t≈7.5). https://www.sciencedirect.com/science/article/abs/pii/S0304405X18301351
- Bailey & López de Prado, "The Deflated Sharpe Ratio." https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2460551
- Bailey, Borwein, López de Prado & Zhu, "The Probability of Backtest Overfitting" (PBO/CSCV). https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2326253

*Research only. No order routing, broker, options, position sizing, or live execution. Where this
conflicts with `MASTER_PROJECT_BRIEF.md`, `CHATGPT_RESEARCH_PHASE_BRIEF.md`, or `README.md`, those
are authoritative.*
