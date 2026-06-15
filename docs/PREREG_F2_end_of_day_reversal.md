# Pre-Registration F2 — End-of-Day Reversal

**From:** Research session (Cowork)
**To:** Build Master (Code session) — review and commit
**Date:** 2026-06-15
**Format:** Pre-registration in `RESEARCH_C_DECISION.md` §4 anatomy. Frozen before any conditional
results are viewed. Immutable once committed; revisions ship as `PREREG_F2_AMENDMENT_1.md`.
**Lineage:** `RESEARCH_F_Signal_Discovery.md` candidate **F2**. Mechanism: option-market-maker
hedging and leveraged-ETF rebalancing into the close generate a **reversal** — the pre-close window
return negatively predicts the last-window return (Baltussen, Da & Soebhag; **t = −6.28**).
**Status:** Specification only. Authorizes nothing. Runnable on **existing SPY 1-min data** — no new
data required for the primary configuration. Strongest obtainable verdict
`eligible_for_paper_consideration`.

---

## 1. Executive Summary (bottom line first)

**Hypothesis:** The SPY return over a fixed pre-close window negatively predicts the return over the
final window of the regular session. Trade the **negative** of the pre-close move into the close.

**One frozen configuration:** predictor `r_pre` = return 14:00–15:00 ET (bars ≤15:00);
position = `−sign(r_pre)` held 15:00→16:00 ET, resolved at the 16:00 close. No future bar touches the
feature.

**Honest expected range (pre-registered, before results):**
- Net edge: **~0–6 bps per trade, plausibly ≤0** once the half-spread is charged at the close.
- Deflated Sharpe: **~0.2–0.6**. Active **~every session** (a daily last-hour trade).
- Probability of clearing the full harness **net**: **~20–30% if the effect is real *and
  capturable net of spread*; <5% if noise.**
- **Dominant risk:** the gross t=−6.28 is large, but end-of-day reversal is exactly the effect most
  vulnerable to **bid-ask bounce** — apparent reversal that is a frictional artifact uncapturable
  net of the spread, and reversal rules trade often enough that costs dominate
  ([Bajgrowicz & Scaillet](https://www.sciencedirect.com/science/article/abs/pii/S0304405X1200116X);
  microstructure caution, `RESEARCH_A`). The **cost model is the binding control** (§6), and a
  **bounce-only synthetic placebo** (§5) is mandatory.
- **Frequency cuts both ways:** daily activation gives high statistical power (≈500 samples) *and*
  high cumulative cost sensitivity.

## 2. Scope
- **In scope:** one price-only reversal signal on existing SPY 1-min bars; read-only forward labels
  for scoring (no-lookahead contract).
- **Out of scope (non-goals):** order routing, broker, options, sizing/leverage, ES migration,
  grid search over windows, any second signal family, any tuning after the freeze. (A gamma-positive
  conditioning of F2 is explicitly deferred to a separate, data-gated amendment — see §3.)

## 3. The ONE frozen, pre-registered configuration
- **Predictor (causal):** `r_pre` = log return over 14:00–15:00 ET, from 1-min bars ≤15:00.
- **Position:** `−sign(r_pre)`, emitted at the 15:00 close, resolved at the 16:00 close. Strictly no
  future bar in the feature.
- **Secondary (one pre-declared variant, counted in N):** magnitude-scaled position
  `−clip(r_pre/σ_pre)` using a shifted trailing same-time-of-day `σ_pre` (no current-bar leakage).
- **Deferred (NOT in this freeze; future amendment, needs option data):** conditioning F2 on a
  net-positive gamma regime, where the mechanism predicts reversal should strengthen. Recorded here
  only to keep the audit trail; it is not tested under this pre-registration.
- **Frozen in advance:** both window boundaries, the direction (reversal), the σ estimator for the
  secondary, cost-model parameters, and the **N contribution** (§4.2).

## 4. Anti-snooping controls (all required; binding one named)
### 4.1 Controls
- **Chronological train/test + walk-forward OOS** — must reproduce on a **calmer held-out
  sub-period**, not only a high-vol window.
- **Deflated Sharpe Ratio, N = every cell ever evaluated — binding for selection.** N includes F2's
  cells plus all other cells in the frozen discovery budget (`RESEARCH_F` §4.2).
- **PBO via CSCV** — report PBO < 50% as a pass gate.
- **Hansen's SPA** — report; DSR/PBO binding.
- **Benjamini–Hochberg FDR** — valid only with honest N.
- **THE BINDING ECONOMIC CONTROL for F2 is the cost/bounce test (§6, §5).** Unlike a slow signal,
  F2's failure mode is *frictional artifact*, so the spread test, not just DSR, is decisive.

### 4.2 Trial-budget (N) contribution — pre-registered
F2 books **2 cells**: {primary sign, magnitude-scaled secondary}. Added to the global frozen N
before results are viewed.

## 5. Negative / placebo controls
- **Bounce-only synthetic placebo (mandatory, F2-specific):** generate returns under a pure
  bid-ask-bounce model with **no true reversal**; the strategy must show **no edge** on this
  synthetic series. If it does, the live "edge" is mechanical bounce → kill.
- **Scrambled-mapping placebo:** permute which day's `r_pre` maps to which day's outcome; edge must
  vanish.
- **Random-direction placebo:** randomize the sign; edge must vanish.

## 6. Cost model (binding economic control)
`cost_bps(t) = half_spread_bps(t) + k·σ_intraday(t) + impact_sqrt(Q/ADV)`, time-of-day and
VIX-regime aware, with the **full half-spread charged at every fill** (F2 turns over daily into the
close, where spreads and the closing-auction dynamics matter). **Decisive test:** the net edge must
be **statistically distinguishable from the half-spread**. If the gross reversal is indistinguishable
from the bounce/half-spread, it is not a signal → kill.

## 7. Acceptance criteria (`eligible_for_paper_consideration` only if ALL hold)
1. Positive **net** edge after the regime-aware cost model, **distinguishable from the half-spread**.
2. Clears **Deflated Sharpe Ratio** with N = every cell tested.
3. Clears **PBO < 50%** via CSCV.
4. Reproduces in **walk-forward OOS on a calmer held-out sub-period**.
5. Edge **vanishes on the bounce-only synthetic placebo** and under scrambled-mapping and
   random-direction placebos.

## 8. What would falsify F2 (route to null / drop F2)
Any one of: fails DSR (full N) **or** PBO ≥ 50% **or** fails walk-forward on the calmer sub-period;
**or** net edge not distinguishable from the half-spread (bounce, not signal); **or** edge appears on
the bounce-only synthetic. On failure, do **not** re-slice into finer pre-close windows (the
canonical false-discovery move) — drop F2 and proceed to remaining candidates.

## 9. Non-goals (restated for the implementer)
No grid over windows; no gamma conditioning under this freeze (deferred to amendment); no options; no
sizing; no ES. One frozen hypothesis, full harness, honest verdict.

**HANDOFF status note (for Build Master; Research does not edit HANDOFF.md):** PREREG F2 filed —
price-only end-of-day reversal, **runnable on existing SPY 1-min data now**. Binding control is the
spread/bounce test (mandatory bounce-only synthetic placebo), not just DSR. Recommended to implement
before F1 (which is blocked on option-chain data).

---

## Sources
- Baltussen, Da & Soebhag, "End-of-Day Reversal" (t=−6.28; MM hedging + LETF rebalancing). https://www3.nd.edu/~zda/EOD.pdf
- Bajgrowicz & Scaillet, "Technical Trading Revisited: False Discoveries, Persistence Tests, and Transaction Costs," *JFE* 106(3) (2012). https://www.sciencedirect.com/science/article/abs/pii/S0304405X1200116X
- Lou, Polk & Skouras, "A Tug of War: Overnight Versus Intraday Expected Returns," *JFE* (2019). https://personal.lse.ac.uk/polk/research/TugOfWar.pdf
- Bailey & López de Prado, "The Deflated Sharpe Ratio." https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2460551
- Bailey, Borwein, López de Prado & Zhu, "The Probability of Backtest Overfitting" (PBO/CSCV). https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2326253

*Research only. No order routing, broker, options, position sizing, or live execution. Where this
conflicts with `MASTER_PROJECT_BRIEF.md`, `CHATGPT_RESEARCH_PHASE_BRIEF.md`, or `README.md`, those
are authoritative.*
