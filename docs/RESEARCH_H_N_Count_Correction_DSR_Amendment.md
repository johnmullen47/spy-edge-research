# Research H — N-Count Correction and DSR Methodology Amendment

**From:** Research session (Cowork)
**To:** Build Master (Code session) — review and commit
**Date:** 2026-06-15
**Status:** Pre-registration / methodology amendment. **Must be committed and immutable before any
implementation change to the DSR N-count.** Revisions ship as `RESEARCH_H_AMENDMENT_1.md`, never
edits.
**Supersedes:** the "N counts EVERY regime cell ever evaluated" clause of `RESEARCH_C_DECISION.md`
§4.3 and the M109 N-fix dispatch — **for the cross-trial DSR input only.** All other anti-snooping
controls in those documents remain in force. This document logs the change explicitly rather than
editing the originals (pre-registration integrity).
**Commit convention:** `research: add RESEARCH_H_N_Count_Correction_DSR_Amendment.md from Cowork Master Agent`

---

## 0. Executive Summary — the flaw, the fix, and the honest concern

**The flaw.** The harness sets the Deflated Sharpe Ratio trial count to `N = len(registry)` — total
candidate count (N=100 at M118: 66 MIM variants + 34 F2 variants). Bailey & López de Prado's DSR
deflates an observed Sharpe against the *expected maximum* Sharpe under the null **across N
independent trials**. Parameter variants within one signal family (q50 vs q75 vol gate; 15-min vs
45-min predictor window) are **not independent** — they are near-duplicates of one hypothesis.
Counting 100 correlated variants as 100 independent trials inflates the expected-max benchmark and
over-deflates the DSR, so even a genuinely strong signal cannot clear the gate. This was identified
as a theoretical defect; it is corrected here at the methodology level, not by inspecting which
candidates are close to clearing.

**The fix (and why it is *not* the naive one).** The intuitive fix — "set N = number of economic
families (=2)" — is itself **wrong, in the over-lenient direction**, and is the exact "reduce N"
move `RESEARCH_C` §4.3 and the M109 dispatch named as *the canonical false-discovery move*. Two
reasons: (1) the DSR already discounts correlation through its cross-trial Sharpe-variance term
`σ_SR`, so collapsing N to the family count double-counts the discount; (2) a single family can
contain *decorrelated* variants — e.g., a gamma-gated vs. a realized-vol-gated momentum signal trade
on different days — and lumping them as one trial ignores real selection bias from searching across
gates. **The correct fix is `N = the effective number of independent trials`, estimated by
clustering the candidate return streams (López de Prado's multiple-testing solution), bounded below
by the family count and above by the total count.** It equals the family count *only* in the limit
where the variants truly are perfectly correlated — i.e., only when that lenience is actually
earned.

**The honest concern, met head-on.** This change makes the gate easier to clear, and it is being
made after observing 0/100. That demands scrutiny, so three integrity facts are pre-committed here:
1. The chosen estimator (effective-N via clustering) is **strictly more conservative than the
   family-count method that was first proposed** — effective-N ≥ family count, always. We are
   adopting the *less* lenient of the two principled options.
2. Effective-N is computed **mechanically** from the strategies' return-correlation structure on
   training data only, with **all hyperparameters frozen in §4 below before results are seen**. N is
   not tuned to make any candidate pass.
3. **Exactly one input changes** — the DSR's N (and the basis for `σ_SR`). The DSR formula, its
   acceptance threshold (≥ 0.95), PBO ≤ 0.50, the net-of-cost floor, walk-forward OOS, and the
   placebo battery are **all unchanged**. We do not loosen two controls at once.

If, after this correction, candidates still fail, that is the result. If they clear, they clear a
gate whose only amendment is provably derivable from the DSR's own definition.

---

## 1. Formal definition of "signal family"

A **signal family** is one distinct directional hypothesis, identified a priori (before data) by the
triple:

> **(predictor variable, return-horizon class, direction type)**

Two candidates belong to the **same family** iff they share all three. Everything else — the
**regime/conditioning gate** (realized-vol quantile, VIX level, dealer-gamma sign, overnight-gap
bucket, macro-calendar flag), the **gate threshold**, the **entry/exit lag**, and **window-length
tuning** — is a **variant axis**, not a new family.

Rationale: the economic edge claim under test is "*predictor X predicts the sign of the return over
horizon H*." The gate only selects *when* the claim is evaluated; it does not change the claim. This
keeps "family" immune to data snooping (it is declared from mechanism, not fitted) and prevents
family-count inflation by re-labeling gates as hypotheses.

**Critical consequence (this is why family-count N is wrong):** because two *variants* of one family
can still produce *decorrelated* return streams, the number of families is a **lower bound** on the
number of independent trials, not the trial count itself. The trial count is recovered empirically by
clustering (§3–§4).

## 2. Family classification (existing candidates + reserved)

| Family | Hypothesis (predictor / horizon / direction) | Members | A-priori family count |
|---|---|---|---|
| **Family 1 — Intraday Momentum (MIM)** | sign(early-session return) / into regular-session close / continuation | 66 MIM variants (vol-quantile gates q50/q70/q75, 15m/45m windows, entry lags) **+ F1 gamma-gate + F3 VIX-gate + F4 overnight-gap-gate + F5 pre-FOMC-gate (placebo)** | 1 |
| **Family 2 — End-of-Day Reversal (F2)** | pre-close window return / last hour / reversal | 34 F2 variants (window, magnitude-scaling) | 1 |

**Decision on F1 (commissioned):** F1 is **not** a new family. It shares Family 1's predictor
(sign of the early-session return) and horizon (into close); the dealer-gamma sign is a
*conditioning gate*, i.e., a variant axis. **Justification and the key subtlety:** classifying F1 as
a Family-1 variant does **not** mean it is "free" in the trial count. Its contribution to the
*effective* N is set empirically by clustering. Per `PREREG_F1` (gamma-negative days ≈ high-vol
days), F1's returns may be highly correlated with the vol-gated MIM variants → it then adds **< 1**
effective trial; if it proves decorrelated, it adds **~1**. Family-count N cannot represent this — it
must call F1 either 0 or 1 new families — whereas effective-N charges its true marginal independence.
This is the concrete demonstration that effective-N dominates family-count.

**F3 / F4 / F5 (commission asked to reserve family numbers 3–5):** under the §1 definition these are
**conditioning variants of Family 1**, not new families — they share MIM's predictor and horizon and
differ only in the gate (VIX, overnight-gap, pre-FOMC calendar). I am therefore **refining the
commission's provisional numbering**: they are reserved as **Family-1 variant axes (V-F3, V-F4,
V-F5)**, not Families 3–5. Their marginal contribution to effective-N is, again, determined by
clustering when each is pre-registered. (F5 remains a placebo expected to fail, per `RESEARCH_F`.) If
a future candidate introduces a genuinely new predictor or horizon — e.g., an ES-futures
multi-hour-horizon signal — *that* opens Family 3.

**A-priori family count (the effective-N floor): 2.**

## 3. Amended DSR methodology — what changes, what stays

**Unchanged (the DSR formula itself):**

```
DSR  = Z[ ( (SR̂ − SR₀) · √(T−1) ) / √( 1 − γ₃·SR̂ + ((γ₄−1)/4)·SR̂² ) ]
```

where `Z` = standard-normal CDF, `SR̂` = candidate's observed (non-annualized) Sharpe, `T` = number
of return observations, `γ₃`/`γ₄` = skew/kurtosis of the candidate's returns. The non-normality and
sample-length adjustments are untouched.

**Unchanged benchmark form:**

```
SR₀ = σ_SR · [ (1 − γ)·Z⁻¹(1 − 1/N) + γ·Z⁻¹(1 − 1/(N·e)) ],   γ = Euler–Mascheroni ≈ 0.5772
```

**What changes — exactly two coupled inputs:**
1. **`N` → `N_eff`**, the effective number of independent trials (§4), replacing `len(registry)`.
2. **`σ_SR`** is computed across the **N_eff cluster representatives**, not across all 100 raw
   variants. (These are the same object — the dispersion of Sharpes across *independent* trials — now
   measured on the correct, de-duplicated set.)

Nothing else in the DSR computation changes.

## 4. Effective-N specification (frozen hyperparameters)

Pre-registered, frozen before results are viewed:

1. **Return matrix.** `R` = per-period returns (per-trade P&L series, or daily if a candidate is
   inactive intraday) for all M candidates, computed on the **walk-forward training folds only** — never
   the held-out test fold (no leakage). Correlations are among *strategy returns* (structure), never
   between a strategy and its forward label (outcome), so clustering cannot peek at which candidate wins.
2. **Distance.** `d_ij = √( ½ · (1 − ρ_ij) )` on the candidate return-correlation matrix `ρ`.
3. **Clustering.** López de Prado's **ONC (Optimal Number of Clusters)** — base clustering by
   silhouette-scored K-means on the correlation-distance matrix, with the standard recursive
   higher-quality-cluster refinement; fixed `random_state` (pre-registered seed). If ONC is
   unavailable in-repo, the frozen fallback is agglomerative hierarchical clustering with **average
   linkage** and K chosen by maximum mean silhouette over K ∈ [2, M].
4. **Effective N.** `N_eff = clip( K_clusters, K_floor, K_ceil )` with **K_floor = a-priori family
   count = 2** and **K_ceil = total candidate count M**. (At M118, `N_eff ∈ [2, 100]`.)
5. **Representatives & `σ_SR`.** Each cluster's representative is its **best-Sharpe member**; `σ_SR`
   = standard deviation of those K representative Sharpes.

**Auditability:** the training-fold definition, distance metric, clustering algorithm + seed, the
[2, M] bounds, and the representative rule are all fixed here. The implementation is checkable
against this section.

## 5. Within-family (within-cluster) multiple-testing correction

Effective-N handles **cross-cluster** selection bias. **Within** a cluster, selecting the best of
several correlated variants is residual selection that the DSR's N_eff does not see. Pre-registered
control, applied at the **candidacy stage, before DSR**:

- Within each cluster, compute each variant's significance and apply **Holm–Bonferroni** (more
  powerful than plain Bonferroni, still FWE-controlling) across that cluster's variant count.
- A cluster is **carried forward as a candidate only if its best member survives the Holm-adjusted
  threshold (α = 0.05)**. That surviving best member's Sharpe is what enters the DSR (with N = N_eff).
- This is a single coherent two-stage procedure: **within-cluster Holm (FWE) → cross-cluster DSR
  (effective-N)** — replacing the prior "treat every variant as an independent DSR trial" approach.

(If one prefers the a-priori *family* rather than the empirical *cluster* as the within-correction
unit, Holm over the family's full variant set is acceptable and is weakly more conservative when a
family's variants are decorrelated; the cross-trial DSR input must remain N_eff regardless.)

## 6. Amended Hard Gate A eligibility

The eligibility **logic is unchanged**; only the DSR's N input is amended. A candidate is
`eligible_for_paper_consideration` iff **all** hold:

1. **Net-of-cost edge > 0** under the regime-aware (vol/time-of-day) cost model on its active subset.
2. **DSR ≥ 0.95**, computed with **N = N_eff** (§4) and the within-cluster Holm candidacy screen (§5).
3. **PBO ≤ 0.50** via CSCV (unchanged; CSCV legitimately operates on the dense survivor panel).
4. **Reproduces in walk-forward OOS** on a calmer held-out sub-period (unchanged).
5. **Edge vanishes under the pre-registered placebos** (scrambled gate, random direction; bounce-only
   synthetic for F2) (unchanged).

**Thresholds held fixed:** DSR ≥ 0.95 and PBO ≤ 0.50 are **unchanged from the current harness**. We
amend the N *definition* only; we do not also move the thresholds. Changing N and a threshold
together would compound the loosening and is explicitly prohibited by this pre-registration.

## 7. Pre-registration statement

This document commits the N-count methodology **before** the corresponding implementation change.
The methodology is derived from the DSR's definition (N = independent trials) and from the
documented correlation structure of parameter variants — **not** from any observation of which
candidates are near the gate. The estimator is bounded below by the family count, so it cannot be
more lenient than the family-count proposal it replaces; its hyperparameters are frozen in §4; and
exactly one harness input is changed. Build Master will implement against §3–§6 and the implementation
will be audited against this file. If implementation reveals a needed change, it is logged in
`RESEARCH_H_AMENDMENT_1.md`, not edited here.

**HANDOFF status note (for Build Master to incorporate; Research does not edit HANDOFF.md):**
RESEARCH_H filed — DSR N amended from total-count (100) to **effective-N via ONC clustering**, bounded
[family-count = 2, total = 100], with within-cluster Holm candidacy and `σ_SR` over cluster
representatives. Supersedes the "N = every cell" clause of RESEARCH_C §4.3 / M109 for the cross-trial
DSR input only; all other gates and thresholds unchanged. Expected effect: N falls from 100 toward the
number of genuinely independent bets, raising achievable DSR; magnitude depends on the empirical
cluster count.

---

## Sources
- Bailey & López de Prado, "The Deflated Sharpe Ratio: Correcting for Selection Bias, Backtest Overfitting and Non-Normality." https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2460551
- Bailey, Borwein, López de Prado & Zhu, "The Probability of Backtest Overfitting" (CSCV/PBO). https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2326253
- López de Prado, "A Data Science Solution to the Multiple-Testing Problem" / *Machine Learning for Asset Managers* (ONC clustering; effective number of independent trials). https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3469090
- Harvey & Liu, "Evaluating Trading Strategies" (haircut Sharpe; Holm / BHY multiple-testing). https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2474755
- Harvey, Liu & Zhu, "…and the Cross-Section of Expected Returns" (multiple-testing hurdle). https://academic.oup.com/rfs/article-abstract/29/1/5/1843824
- Internal: `RESEARCH_C_DECISION.md` §4.3 (superseded N clause), M109 N-fix dispatch, `PREREG_F1_gamma_gated_momentum.md`, `RESEARCH_F_Signal_Discovery.md`.

*Research only. No order routing, broker, options, position sizing, or live execution. This amendment
changes a single statistical input and loosens nothing else. Where it conflicts with
`MASTER_PROJECT_BRIEF.md`, `CHATGPT_RESEARCH_PHASE_BRIEF.md`, or `README.md`, those are authoritative.*
