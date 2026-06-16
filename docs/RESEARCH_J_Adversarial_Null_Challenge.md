# Research J — Adversarial Challenge to the M126 Null Result

**From:** Build Master (Project Build 5), adversarial-research mode
**To:** Dispatch / John
**Date:** 2026-06-16
**Branch:** `research/J-adversarial-null` (tip of M126)
**Status:** Research memo — **NOT a pre-registration, NOT immutable.** May be revised
as `RESEARCH_J` in place (unlike the frozen `PREREG_*` / `RESEARCH_[A-I]` records).
**Companion records:** `RESULTS_M126_HARD_GATE_A.md`, `RESEARCH_I_Retail_Quant_Method_Sweep.md`,
`RESEARCH_H_N_Count_Correction_DSR_Amendment.md`, `PREREG_F1`–`PREREG_F10`.

---

## 0. The question being adversarially tested

The project ran Hard Gate A across **672 candidates in 12 signal families** spanning all
five durable mechanism buckets (behavioral under-/over-reaction, risk premia, structural
forced-flow, microstructure/rebalancing, macro/calendar) and found **0/672 eligible**
(effective-N 318, PBO 0.096, 38 within-cluster Holm survivors that passed multiple-testing
but cleared no full gate). Instrument: the **IEX** SPY 1-min feed (189,663 bars, ~2 years),
plus CBOE daily VIX and the Fed calendar.

**John's challenge:** *"If there were nothing here, why do so many retail quant traders
claim profit?"*

This memo steel-mans the case **against** our own null. It assesses six hypotheses for why a
real edge could exist that our harness would still report as null, rates each, and renders an
honest verdict. The goal is to find the most likely way we are **wrong**, not to defend the
result.

A prior worth stating up front: "retail traders claim profit" is weak evidence for an edge.
The rigorous base rate (H2) is that **>80% of day traders lose and <1% are reliably
profitable** (Barber-Lee-Liu-Odean), claims are survivorship-filtered and rarely net-of-cost
or risk-adjusted, and published edges decay ~58% post-publication (McLean-Pontiff). So the
question is really: *is there a small, real, structural effect that survives in some form our
672-candidate sweep on this instrument/feed could not see?* That is a much more defensible
proposition than "retail traders are right," and it is where H1 and H6 below have teeth.

---

## 1. H1 — Wrong instrument / resolution

**Claim:** The documented effects are sub-daily and/or cross-sectional and/or leverage-/
futures-based phenomena. Run on a single thin-feed equity ETF at the resolutions we used,
they have little left to find.

**Evidence FOR (strong):**
- **MIM is a 30-minute effect, not a daily one.** Gao-Han-Li-Zhou (JFE 2018) define it as
  *the first half-hour return predicts the last half-hour return* on the SPY ETF 1993-2013,
  and report it is **stronger on high-volatility, high-volume, recession and macro-news
  days**. It is intrinsically a within-day, microstructure-timed effect; there is no
  daily-bar analog.
- **ORB's documented profitability requires leverage + cross-sectional selection + ~zero
  costs.** Zarattini-Barbon-Aziz (2024, SSRN 4729284) get their headline returns on **7,000
  stocks 2016-2023, restricted to "stocks in play"** (unusual relative volume) and **3×
  leveraged ETFs (TQQQ)**, assuming $0.0005/share commission, **no bid-ask spread, no
  slippage**. Our F8 is deliberately the opposite: un-leveraged SPY, no cross-sectional
  selection, full half-spread charged. The literature itself predicts F8 fails on plain SPY —
  and PREREG_F8 said so.
- **Intraday periodicity (HKS 2010) is a cross-sectional effect.** Heston-Korajczyk-Sadka
  document same-half-hour-bucket continuation **across the cross-section of stocks**; the
  mechanism (Bogousslavsky 2016) is infrequent institutional rebalancing spread across many
  names. On a single instrument it collapses to own-autocorrelation, which is weaker and, at
  the bid-ask level, contaminated by bounce. PREREG_F9 flagged exactly this.
- **The feed is thin.** IEX carries ~1-2% of consolidated SPY volume (per the project's own
  data note). Microstructure-sensitive signals (F8/F9, intraday MIM) are precisely the ones a
  thin, noisy print stream degrades most.

**Evidence AGAINST:**
- Resolution is **not** uniformly wrong. The intraday families (MIM-Baltussen, F8, F9) ran at
  the correct intraday resolution (1-min bars, 30-min / to-close outcomes), not at daily bars.
  So "everything was tested at daily resolution" is false — the daily framing applies only to
  F6/F7/F10 (which are *intended* daily/weekly and which the literature also supports as such).
- The Baltussen rest-of-day predictor was tested at its native 15:30→16:00 window (256
  MIM-Baltussen candidates) and still failed — so for that family, resolution was right and
  the instrument (SPY) is the same one the futures literature generalizes to.

**Strength: HIGH (the strongest single hypothesis).** The published edges for ORB and
periodicity are demonstrably *not* single-instrument, un-leveraged, full-cost SPY phenomena,
and MIM is a high-vol-day microstructure effect that a thin feed degrades. We very likely ran
faithful implementations of effects whose *native habitat* (leverage, cross-section, futures,
full-volume tape) we cannot reproduce here. This does not resurrect a tradable SPY edge — it
explains the null without requiring "nothing exists."

---

## 2. H2 — Survivorship / selection bias in the "retail profit" prior

**Claim:** The premise behind John's question is contaminated. Visible "profitable" retail
systems are the survivors of a massive hidden population of failures.

**Evidence FOR (very strong):**
- **Barber, Lee, Liu & Odean (Taiwan):** >80% of day traders lose money; **<1% are reliably
  profitable** net of costs, and that <1% is hard to distinguish from luck.
- **McLean & Pontiff (JF 2016):** published anomaly returns decay **~58%** out-of-sample /
  post-publication. The very edges retail systems are built on are half-gone by the time
  they're packaged.
- **Bailey-Borwein-López de Prado-Zhu:** with enough trials, backtest overfitting *guarantees*
  high in-sample Sharpes with **negative** OOS expectancy — exactly the artifact a deflated
  test exists to strip out. Most retail "edges" are un-deflated in-sample fits.
- Our own harness already produced the in-sample illusion and killed it: the M105-era run had
  15 "eligible" candidates at 0.06-0.46 bps — pure sub-cost noise that the economic-significance
  floor and FDR removed. That is the retail-claim pattern reproduced and falsified in-house.

**Evidence AGAINST:**
- H2 explains why *claims* are unreliable, but it does not by itself prove **our** null is
  correct — it removes a bad reason to doubt the null rather than supporting an edge. It is an
  argument about the prior, not about our data.

**Strength: HIGH as a rebuttal to the premise; N/A as evidence for a hidden edge.** John's
question has a clean answer — selection bias plus decay plus overfitting fully accounts for the
gap between claimed and evidenced, with no edge required. This is the single most complete
answer to *"why do they claim profit?"*

---

## 3. H3 — DSR/PBO gate too strict for a single instrument

**Claim:** The deflation stack was built for large cross-sectional trial sets and long track
records. On one instrument with a short sample, it is near-unclearable regardless of whether a
small edge exists.

**Evidence FOR (moderate-to-strong, and quantifiable):**
- The Deflated Sharpe benchmark is the **expected maximum** Sharpe under the null across N
  trials: `SR0 = sigma_SR · [(1-gamma)·Z^-1(1-1/N) + gamma·Z^-1(1-1/(N·e))]`. At our
  **N_eff = 318**, `Z^-1(1-1/318) ≈ 2.73` and `Z^-1(1-1/(318·e)) ≈ 3.05`, so
  **SR0 ≈ 2.91 · sigma_SR** — the bar sits ~2.9 cross-trial standard deviations above zero
  before the candidate even starts.
- The DSR multiplies the excess `(SR_hat - SR0)` by `√(T-1)`, where **T is the number of OOS
  observations** — here the walk-forward per-split panel, on the order of **tens**, not the
  hundreds-to-thousands the test assumes. Bailey-López de Prado's **Minimum Track Record
  Length** formalizes this: to reject "true SR ≤ benchmark" at 95% you need a track length that
  grows with the benchmark and the inverse of the excess Sharpe. A 2-year single-instrument
  sample, reduced to ~tens of independent walk-forward observations, is **structurally
  power-starved** for clearing DSR ≥ 0.95 at N=318.
- Concretely: a single-instrument intraday strategy with a genuine but modest edge
  (annualized Sharpe ~0.3-0.6, the honest pre-registered range for these families) cannot, on
  this sample length, push the per-split Sharpe far enough above a ~2.9·sigma_SR benchmark to
  clear 0.95. The test is doing its job (controlling Type-I) but with very low power (high
  Type-II) in this regime.

**Evidence AGAINST (important — this is not a free pass):**
- **PBO = 0.096 is low and is *not* a power-limited test.** CSCV legitimately operates on the
  dense survivor panel; a low PBO says the in-sample ranking is **not** overfit — i.e., the
  candidates that look best in-sample do *not* systematically collapse OOS. If there were a real
  sub-threshold edge being masked only by DSR strictness, we would still expect it to surface as
  positive (if small) net economic edge — but the failing_reasons show candidates also failing
  **economic_edge_bps_below_min** (sub-1bp) and **negative_control_not_passed**, which are
  **not** DSR-strictness artifacts. Multiple independent gates fail, not just DSR.
- RESEARCH_H deliberately set N_eff to the *effective* (clustered) trial count, already the
  least-harsh principled choice; the M124 fix moved it off the degenerate ceiling (it is 318,
  not 671). So the gate is already as lenient as the methodology honestly allows.

**Strength: MODERATE.** H3 is a real and correctly-diagnosed power limitation — DSR at N=318 on
~tens of OOS observations is close to unclearable for a single instrument, so "0/672 cleared
DSR" is weak evidence of edge-*absence*. But it is **not** evidence of edge-*presence*: the
economic-floor and negative-control failures, plus the low PBO, are independent of DSR and point
the same way (no economically meaningful, control-robust signal). H3 downgrades our confidence in
"there is definitely nothing" without supporting "there is something."

---

## 4. H4 — The 38 Holm survivors: real sub-threshold signal or noise?

**Claim:** 38 candidates passed the within-cluster Holm-Bonferroni screen (statistically
non-zero positive OOS edge after multiple-testing within their cluster) yet cleared no full
gate. Maybe they are a real, small, sub-threshold signal rather than noise.

**Data note.** The M126 run reported the aggregate (38 Holm survivors of 318 clusters,
PBO 0.096) but its per-candidate scorecard lived in a now-removed worktree and `reports/`
is gitignored, so the per-survivor family/Sharpe/DSR-gap breakdown is not preserved. A
regeneration run (control-batteries off) reproduces it deterministically; that profiling
is listed as a recommended next experiment (§7) rather than blocking this memo. The
assessment below rests on the recorded aggregates plus the M126 `failing_reasons` sample
(survivors fail predominantly on `economic_edge_bps_below_min`, `negative_control_not_passed`,
and `deflated_sharpe_below_min`).

**Evidence FOR:**
- 38 surviving a Holm screen across 318 clusters is **more than the ~5% (≈16) you would expect
  by chance** at alpha=0.05 if every cluster were pure noise — suggesting a non-trivial fraction
  carry genuine, if tiny, positive OOS edge.
- PBO 0.096 says the in-sample/OOS ranking is stable, consistent with these being persistent-but-
  small effects rather than overfit flukes.

**Evidence AGAINST:**
- Holm controls family-wise error *within a cluster* on the **edge-positive** test; it says
  nothing about **economic magnitude**. The full-gate failure reasons are dominated by
  `economic_edge_bps_below_min` (sub-1bp net) and `negative_control_not_passed` — i.e. the
  survivors are statistically-distinguishable-from-zero but **economically sub-cost** and/or
  fail the scrambled/placebo controls. A 0.2-0.5 bp net edge is "real" in a p-value sense and
  worthless in a tradable sense once the regime-aware close-auction cost is charged.
- With 318 clusters, 38 survivors is also consistent with a modestly-elevated false-discovery
  count under residual within-cluster correlation, not a coherent family-concentrated signal.

**Strength: LOW-TO-MODERATE.** The 38 survivors are best read as **"sub-cost real-ish noise"** —
likely a mix of a few genuine micro-effects and residual multiple-testing artifacts, none
economically tradable on this instrument after honest costs. They are the most interesting place
to *look harder* (especially if concentrated in the structural-flow families), but they are not a
suppressed tradable edge. Profiling them (family concentration, per-survivor observed Sharpe, and
gap to the DSR 0.95 threshold) would determine whether this rating nudges up (if concentrated in
the MIM-Baltussen / F3 / F4 gamma-flow cluster, which would reinforce H6) or down (if scattered
across unrelated families, implying residual multiple-testing noise) — see §7.

---

## 5. H5 — Regime change / publication decay

**Claim:** The effects were strongest in their original samples and have decayed; our 2024-2026
window is post-decay.

**Evidence FOR (strong for the older effects):**
- **Timing of the source samples:** Gao MIM 1993-2013; HKS periodicity ~1990s-2000s cross-section;
  Baltussen 1974-2020; ORB 2016-2023. Our test window (2024-2026) is **after** all of them.
- **McLean-Pontiff** decay (~58%) applies directly: MIM and periodicity have been public and
  arbitraged for 8-15 years. The project's own lineage notes the **Gao first-half-hour MIM has
  documented post-2018 OOS failure** (the −0.63 Sharpe QuantConnect replication) — which is *why*
  the project pivoted to the Baltussen rest-of-day formulation in the first place.
- Pre-FOMC drift (Lucca-Moench) is the textbook decayed effect — gone post-~2015 — and our F5
  placebo confirmed it null on our data, exactly as designed.

**Evidence AGAINST:**
- **Baltussen (2021) explicitly argues the structural-flow MIM is more persistent** because it is
  mechanical (gamma hedging, LETF rebalancing), not informational — and they find it across 60+
  futures through 2020. If any effect should *not* have fully decayed, it is the structural one we
  centered the project on (MIM-Baltussen). Yet it was null here — which points more to H1
  (instrument/feed) than to decay.
- FOMC-cycle (F10, Cieslak et al.) had no strong decay claim and still came back null — but the
  sample is too short (H3 power) to adjudicate decay vs absence for a weekly effect.

**Strength: MODERATE-TO-HIGH for the behavioral/calendar effects (MIM-Gao, periodicity, pre-FOMC);
LOW as an explanation for the structural-flow null.** Decay convincingly explains why the *old
behavioral* families are null, but it does **not** explain the structural MIM-Baltussen null
(which the literature says should persist) — that one is better explained by H1/H6.

---

## 6. H6 — F1 (gamma-gated MIM) is the real edge, blocked by data

**Claim:** The genuine, persistent edge is dealer-gamma-driven intraday momentum; the families we
ran are price-only shadows of it, and we cannot see the real signal without options/GEX data.

**Evidence FOR (strong mechanism, growing relevance):**
- **Baltussen et al. (2021, JFE)** provide direct academic evidence linking market intraday
  momentum to **gamma-hedging demand**: hedging short-gamma requires trading *with* the move,
  mechanically creating momentum; the effect is significant across 60+ futures 1974-2020 and
  **reverts over subsequent days** (a structural, not informational, signature).
- **0DTE options now dominate SPX volume**, so dealer intraday hedging flows are **structurally
  larger and more relevant** to short-term price than at any time in the source samples (Dim-
  Eraker-Vilkov; Cboe gamma research). The GEX regime sign (positive → mean-reversion/suppression;
  negative → momentum) is exactly the conditioning variable F1 specifies.
- This is the one hypothesis pointing at a *specific, testable, currently-unobserved* variable
  (prior-session net dealer gamma) rather than a general caveat.

**Evidence AGAINST (this is the key adversarial point):**
- The project **already tested the price-only manifestation of the gamma effect** — MIM-Baltussen
  is *precisely* the Baltussen rest-of-day predictor that the 2021 paper shows captures the
  gamma-hedging momentum **without** options data. It contributed **256 candidates** and was
  **null on SPY/IEX**. So the claim "the real edge is invisible without options data" is
  substantially undercut: the literature says the price-only proxy already embeds most of the
  gamma signal, and it failed here. The explicit GEX gate (F1) could add *incremental* value, but
  PREREG_F1 itself flags that gamma-negative days ≈ high-vol days, so the GEX gate risks being a
  redundant proxy for the realized-vol gate we already tested (and which was null).
- F1 remains **blocked on EOD SPX/SPY option-chain data** (RESEARCH_G confirmed Polygon free has
  no historical OI; CBOE required) — so this is a genuine unknown, but its prior is **weakened**,
  not strengthened, by the MIM-Baltussen null.

**Strength: MODERATE.** Mechanistically the most credible "real edge" candidate, and the only one
naming a concrete missing variable — but the project already falsified its price-only shadow on
this instrument, so the incremental edge from explicit GEX must be both real *and* orthogonal to
the realized-vol gate to rescue the null. That is possible but not probable. Worth acquiring the
option data to settle, with a deliberately low prior.

---

## 7. Verdict

**The null stands as a statement about this instrument and feed; it does NOT stand as a universal
"there is no edge in these mechanisms."** The honest reading:

1. **The result is correct for what it tested.** 0/672 is not a harness failure. Multiple
   *independent* gates fail together (economic floor, negative control, walk-forward, DSR), PBO is
   low (0.096, not overfit), and the M124 effective-N fix means the DSR trial count is defensible
   (318, not the degenerate ceiling). There is no tradable, control-robust, net-of-cost edge in the
   SPY/IEX data we ran.

2. **But we are partly running the wrong tests for the wrong instrument (H1) with a power-starved
   gate (H3).** The published edges are largely cross-sectional (HKS periodicity), leveraged + 
   selection-based (ORB), futures-based (Baltussen), or sub-daily high-vol-day microstructure
   (MIM) — and our single, thin-feed, un-leveraged SPY ETF at full honest cost is their degraded
   habitat. DSR at N=318 on ~tens of OOS observations is near-unclearable for a single instrument
   regardless of a small edge. So the null is **much stronger evidence against a *retail-tradable
   SPY edge*** than against the *underlying mechanisms existing somewhere*.

3. **John's question has a clean answer (H2):** retail "profit" claims are survivorship-filtered,
   rarely net-of-cost or risk-adjusted, built on ~58%-decayed published edges, and pattern-match
   the in-sample-overfit illusion our own harness generated and then killed. No real edge is
   required to explain the claims.

**So: the null partially stands — fully for "is there a deflation-clearing, cost-robust directional
edge in SPY/IEX over 2024-2026?" (yes, null is solid), but it should *not* be read as "these
mechanisms are dead." The honest next moves are instrument/data changes, not more candidates on the
same tape.**

### Ranking by explanatory power (most → least)

1. **H1 — wrong instrument/resolution.** Strongest. Directly explains why ORB/periodicity/MIM,
   whose native habitats are leverage/cross-section/futures/full-volume-tape, find little on
   un-leveraged thin-feed SPY. Hard academic support.
2. **H2 — survivorship/decay in the prior.** Strongest *answer to John's question*; fully accounts
   for the claimed-vs-evidenced gap with no edge needed. (Explains the premise, not our data.)
3. **H3 — DSR power on a single instrument/short sample.** Real, quantified power limitation that
   weakens "definitely nothing," but offset by the low PBO and independent economic/control
   failures.
4. **H5 — publication decay.** Convincing for the *old behavioral* families (Gao-MIM, periodicity,
   pre-FOMC), weak for the structural-flow family that should persist.
5. **H6 — hidden gamma edge.** Best mechanism story and the only concrete missing variable, but its
   price-only proxy (MIM-Baltussen) was already tested and null, lowering the prior.
6. **H4 — the 38 Holm survivors.** Least explanatory: best read as sub-cost real-ish noise, the
   place to look harder but not a suppressed tradable edge.

### Recommended next experiments (in priority order)

- **Re-run on a full-volume consolidated/SIP tape and on ES futures** (H1) — the single highest-value
  change; tests whether the intraday families were starved by the IEX feed and whether the
  futures-native Baltussen effect appears where it is documented.
- **Acquire EOD SPX option chains and run F1 / GEX-conditioning** (H6) — settle the one concrete
  missing variable; keep a low prior given the MIM-Baltussen null.
- **Extend the sample backward** (H3/H5) — more OOS observations directly raise DSR power and let us
  separate decay from absence for the daily/weekly families.
- **Profile the 38 Holm survivors** (H4) — if concentrated in the structural-flow cluster
  (MIM-Baltussen/F3/F4), that sharpens where H1/H6 would pay off.

*Research only. No order routing, broker, options, position sizing, or live execution. This is an
adversarial analysis memo, revisable; it changes no gate and authorizes nothing.*

## Sources
- Gao, Han, Li & Zhou, "Market Intraday Momentum," *JFE* 129(2):394-414 (2018). https://www.sciencedirect.com/science/article/abs/pii/S0304405X18301351
- Baltussen, Da, Lammers & Martens, "Hedging Demand and Market Intraday Momentum," *JFE* (2021). https://www.sciencedirect.com/science/article/abs/pii/S0304405X21001598
- Heston, Korajczyk & Sadka, "Intraday Patterns in the Cross-section of Stock Returns," *JF* 65(4) (2010). https://onlinelibrary.wiley.com/doi/abs/10.1111/j.1540-6261.2010.01573.x
- Bogousslavsky, "Infrequent Rebalancing, Return Autocorrelation, and Seasonality," *JF* 71(6) (2016). https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2308366
- Zarattini, Barbon & Aziz, "A Profitable Day Trading Strategy For The U.S. Equity Market," SSRN 4729284 (2024). https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4729284
- Zarattini & Aziz, "Can Day Trading Really Be Profitable? (ORB)," SSRN 4416622 (2023). https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4416622
- McLean & Pontiff, "Does Academic Research Destroy Stock Return Predictability?," *JF* (2016). https://onlinelibrary.wiley.com/doi/abs/10.1111/jofi.12365
- Barber, Lee, Liu & Odean, "Do Individual Day Traders Make Money? Evidence from Taiwan." https://faculty.haas.berkeley.edu/odean/papers/Day%20Traders/Day%20Trade%20040330.pdf
- Bailey & López de Prado, "The Deflated Sharpe Ratio," (2014). https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2460551
- Bailey & López de Prado, "The Sharpe Ratio Efficient Frontier" (PSR / Minimum Track Record Length), (2012). https://papers.ssrn.com/sol3/papers.cfm?abstract_id=1821643
- Bailey, Borwein, López de Prado & Zhu, "The Probability of Backtest Overfitting" (CSCV/PBO). https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2326253
- Cieslak, Morse & Vissing-Jorgensen, "Stock Returns over the FOMC Cycle," *JF* 74(5) (2019). https://onlinelibrary.wiley.com/doi/abs/10.1111/jofi.12818
- Dim, Eraker & Vilkov, "0DTEs: Trading, Gamma Risk and Volatility Propagation." https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4692190
- Internal: `RESULTS_M126_HARD_GATE_A.md`, `RESEARCH_I_Retail_Quant_Method_Sweep.md`, `RESEARCH_H_N_Count_Correction_DSR_Amendment.md`, `PREREG_F1_gamma_gated_momentum.md`, `PREREG_F8.md`, `PREREG_F9.md`.
