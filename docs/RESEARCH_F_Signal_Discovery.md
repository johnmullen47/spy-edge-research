# Research F — Signal-Discovery Survey: Regime-Conditioned Intraday Predictability Beyond MIM

**From:** Research session (Cowork)
**To:** Build Master (Code session) — review and commit
**Date:** 2026-06-15
**Status:** Literature survey feeding the Stage-0 discovery layer of `RESEARCH_E`. Identifies
candidate signals/regimes; does **not** authorize anything. Pre-registrations follow in Task 3.
**Context:** Build 4 @ M113 (892 tests); M114 regime-aware cost model in flight. Active signal:
realized-early-session-vol-gated intraday momentum (MIM) on SPY. Hard Gate A negative (0/42),
unchanged.

---

## 1. Executive Summary (bottom line first)

**The literature offers roughly five regime/conditioning axes with genuine pedigree beyond
realized early-session volatility — but only two are both mechanism-backed and plausibly alive
post-2015: (a) options-dealer gamma sign, and (b) the end-of-day / last-half-hour effects tied to
dealer hedging and leveraged-ETF rebalancing. Calendar (pre-FOMC) and pure overnight-drift effects
are real in-sample but have visibly decayed or die net of costs. Sentiment proxies (put/call, IV
skew, breadth) are weak as standalone directional signals and best used only as secondary gates.**

Four headline conclusions:

1. **The strongest *new* mechanism is dealer gamma.** Negative dealer gamma mechanically forces
   hedging *with* the move (momentum); positive gamma forces hedging *against* it (reversal). This
   is grounded in market structure, is *growing* with 0DTE volume rather than decaying, and is the
   one regime gate with a clean causal story that the killed chart-pattern menu never touched
   ([Baltussen, Da & Soebhag, "End-of-Day Reversal"](https://www3.nd.edu/~zda/EOD.pdf);
   [Dim, Eraker & Vilkov, "0DTEs: Trading, Gamma Risk and Volatility Propagation"](https://papers.ssrn.com/sol3/papers.cfm?abstractid=4692190)).

2. **Calendar conditioning (pre-FOMC) is the cautionary tale.** The pre-FOMC drift was large and
   significant in-sample (Lucca & Moench) and *strongest exactly where MIM is strongest* (high
   implied vol, flat yield curve) — but an explicit follow-up finds it **disappeared after 2015**.
   It belongs in the harness as a **placebo / decay check**, not a primary gate
   ([Lucca & Moench 2015](https://onlinelibrary.wiley.com/doi/abs/10.1111/jofi.12196);
   ["The disappearing pre-FOMC announcement drift"](https://www.sciencedirect.com/science/article/abs/pii/S1544612320315956)).

3. **Overnight/intraday return decomposition is real but not a standalone net edge in SPY** — the
   daily overnight-vs-intraday difference is not statistically significant (t≈1.90) and goes from
   +717% gross to −32% net once costs are applied (carried from `RESEARCH_B`;
   [SSGA via Alpha Architect](https://alphaarchitect.com/trading-costs-wipe-out-the-overnight-return-anomaly/)).
   It is useful only as a *conditioning variable* (gap size / overnight sign), not as a tradable signal.

4. **On the methodology questions:** a *legitimate* discovery-phase screen is an economic-prior +
   exploration/validation-holdout filter that **reduces compute and noise but does not launder the
   trial count** — every configuration examined still counts toward DSR's N. A thorough but
   *disciplined* search of this family implies **N on the order of 80–200**, which raises the DSR
   per-trial Sharpe benchmark `Φ⁻¹(1−1/N)` from ~1.98 (N=42) to ~2.3–2.6 — affordable; brute-forcing
   to N≈1000 pushes it to ~3.1 (the Harvey "t>3" regime) and is self-defeating (§4).

---

## 2. Regime / conditioning indicators beyond realized early-session volatility

Each is rated on *mechanism strength* and *post-2015 survival*. A signal is only as good as the gate
it is conditioned on; these are the gates worth pre-registering.

### 2.1 Options-dealer gamma sign — **mechanism: strong; survival: likely (growing)**
Dealer delta-hedging of net options inventory conditions intraday behavior: net-negative gamma →
hedge with the move → momentum; net-positive gamma → hedge against → mean reversion. Baltussen, Da &
Soebhag document a market-level **end-of-day reversal with t = −6.28** (end-of-day return negatively
predicts the last-hour return), attributing it to option-market-maker hedging and leveraged-ETF
rebalancing ([EOD Reversal](https://www3.nd.edu/~zda/EOD.pdf)). With 0DTE options now a majority of
SPX option volume, intraday hedging pressure is structurally larger and concentrated within the
session ([Dim, Eraker & Vilkov](https://papers.ssrn.com/sol3/papers.cfm?abstractid=4692190);
[Cboe, 0DTE & market volatility](https://cdn.cboe.com/resources/education/research_publications/gammasqueezes.pdf)).
The Zarattini–Aziz–Barbon SPY intraday-momentum study explicitly tests whether dealer-gamma imbalance
predicts changes in strategy profitability ([SSRN 4824172](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4824172)).
**Caveat (per `RESEARCH_C` verification):** the Zarattini paper is a practitioner, non-peer-reviewed,
single-window in-sample backtest whose Sharpe 1.33 includes added machinery; treat its gamma result
as *direction-of-inquiry*, not validation.

### 2.2 VIX level / term-structure — **mechanism: moderate; survival: moderate**
Intraday momentum / pre-announcement edges concentrate when implied vol is high (Lucca & Moench;
Aleti, Bollerslev & Siggaard's "high economic uncertainty" finding, carried from `RESEARCH_A`). VIX
term-structure level/slope/curvature carry return-predictive content
([Yoon 2022, J. Futures Markets](https://onlinelibrary.wiley.com/doi/full/10.1002/fut.22317)). Best
used as a *continuous regime gate* alongside realized vol, not as a separate signal. Risk: VIX and
realized vol are collinear — adding VIX as a second gate must be charged to N, not treated as free.

### 2.3 Overnight-gap magnitude / sign — **mechanism: moderate; survival: moderate**
The overnight gap is the natural "first move" analog to MIM's early-session window and a candidate
conditioning variable. Overnight-vs-daytime reversals positively predict close-to-close returns
([Akbas et al. 2021](https://www.sciencedirect.com/science/article/abs/pii/S0304405X21004116); Lou,
Polk & Skouras "Tug of War," carried from `RESEARCH_B`). Use as a gate (gap size buckets / sign),
not as a standalone strategy (§3).

### 2.4 Scheduled-macro calendar (FOMC/CPI) — **mechanism: moderate; survival: WEAK post-2015**
Pre-FOMC drift: large average equity excess returns in the ~24h before scheduled FOMC decisions,
**higher when the yield-curve slope is low and implied vol is high** (i.e., overlapping the MIM
regime), Lucca & Moench, JF 2015, 70(1):329–371
([Wiley](https://onlinelibrary.wiley.com/doi/abs/10.1111/jofi.12196)). **But** a direct follow-up
finds the drift **essentially disappeared after 2015**
([Sci. Direct](https://www.sciencedirect.com/science/article/abs/pii/S1544612320315956)). MIM itself
is "stronger on macro-news-release days" (Gao et al., carried from `RESEARCH_A`). **Recommendation:
enter calendar conditioning as a pre-registered placebo expected to fail / a decay monitor**, never
as a primary gate.

### 2.5 Sentiment proxies — put/call ratio, IV skew, market breadth — **mechanism: weak; survival: weak**
Put/call ratio and IV skew are popular sentiment inputs with some predictive association, but no
clean, replicated, cost-surviving *intraday directional* edge as standalones
([VIX/skew overview](https://onlinelibrary.wiley.com/doi/full/10.1002/fut.22317)). Treat as
**tertiary gates only**, and only if a primary mechanism-backed signal already clears — adding them
first mostly inflates N.

## 3. Overnight / intraday / open-to-close predictability on SPY — what the t-stats say

- **Overnight vs. intraday decomposition:** virtually all long-run SPY *price* gain accrues overnight
  (+717% overnight vs +12% intraday, gross, 1993–2020), BUT the daily overnight-minus-intraday
  difference is **not significant (paired t ≈ 1.90, p ≈ 0.06)**, is fat-tailed/period-concentrated,
  and goes to **−32% net** after spread + commission
  ([SSGA via Alpha Architect](https://alphaarchitect.com/trading-costs-wipe-out-the-overnight-return-anomaly/)).
  **Verdict: not a standalone net edge in SPY; usable only as a conditioning variable.**
- **Within-period continuation, cross-period reversal:** Lou, Polk & Skouras — overnight predicts
  overnight, intraday predicts intraday, with an offsetting cross-period reversal persisting for years
  (carried from `RESEARCH_B`; [LSE PDF](https://personal.lse.ac.uk/polk/research/TugOfWar.pdf)).
- **End-of-day reversal:** end-of-day returns negatively predict the last-hour return, **t = −6.28**,
  mechanism = option-MM hedging + leveraged-ETF rebalancing
  ([Baltussen, Da & Soebhag](https://www3.nd.edu/~zda/EOD.pdf)). This is the strongest *recent*,
  *mechanism-backed*, intraday-specific statistic in the survey.
- **Intraday momentum (MIM baseline):** first-half-hour predicts last-half-hour, **t ≈ 7.53**,
  concentrated on high-vol/high-volume/news days (Gao, Han, Li & Zhou 2018, carried from `RESEARCH_A`)
  — but practitioner replication shows post-~2017 flattening (QuantConnect, carried from `RESEARCH_A`).

**Net for SPY:** the durable, mechanism-grounded intraday statistics are the **continuation (MIM,
t≈7.5) and end-of-day-reversal (t≈−6.3) effects**, both now best understood through **dealer hedging
flows** — which is why §2.1 (gamma sign) is the highest-value new gate.

## 4. Pre-screening: what is a *legitimate* discovery-phase screen, and the trial-budget N

### 4.1 What counts as legitimate (and what doesn't)
A discovery screen is legitimate when it **reduces noise and compute without manufacturing or hiding
false discoveries**. The defensible toolkit:

- **Economic/mechanism prior first.** Pre-specify the causal story (e.g., "negative gamma → hedging
  pressure → continuation") *before* fitting. Theory-first conditioning is what separates MIM and
  EOD-reversal from chart folklore.
- **Exploration / validation holdout ("generic holdout").** Carve a discovery set; keep a sealed
  validation set the screen never touches
  ([Generic Holdout](https://arxiv.org/pdf/1809.05596)). **Critical limit, stated explicitly in the
  literature: a holdout does *not* solve multiple testing** — it controls model complexity for a
  *single* test, not for the count of hypotheses explored
  ([same](https://arxiv.org/pdf/1809.05596); [QuantPedia IS/OOS](https://quantpedia.com/in-sample-vs-out-of-sample-analysis-of-trading-strategies/)).
- **Coarse min-sample + effect-size + one-perturbation-robustness filters.** Cheap, monotone screens
  that only ever *remove* candidates.
- **Report-only stepwise methods** to rank, not to authorize: Romano–Wolf stepwise FWE control, which
  captures cross-test dependence and is more powerful than Bonferroni
  ([Romano & Wolf 2005, Econometrica](https://onlinelibrary.wiley.com/doi/abs/10.1111/j.1468-0262.2005.00615.x));
  Harvey–Liu haircut-Sharpe / Holm / BHY for the eventual hurdle
  ([Harvey & Liu, "Evaluating Trading Strategies"](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2474755)).

**Illegitimate:** any screen whose discarded trials are *not counted* toward the multiple-testing
budget. That is the exact false-discovery move the M109 N-fix forbids. Stage 0's value is cheaper
*compute* and better *priors*, **not** a smaller N.

### 4.2 Appropriate trial budget N, and the DSR implication
The DSR benchmark is the expected maximum Sharpe under the null across N independent trials; the
dominant term is `Φ⁻¹(1 − 1/N)` (DSR uses the Euler-corrected Gumbel form, but this term governs the
scaling). The hurdle grows slowly (∝ √(2 ln N)), so a *disciplined* expansion is affordable:

| Trial budget N | `Φ⁻¹(1 − 1/N)` per-trial Sharpe benchmark | Interpretation |
|---|---|---|
| 42 (current) | ≈ 1.98 | today's bar |
| 80 | ≈ 2.26 | small theory-guided expansion |
| 150 | ≈ 2.50 | full disciplined family search |
| 300 | ≈ 2.71 | aggressive; near Harvey hurdle |
| 1000 | ≈ 3.09 | brute force → self-defeating |

**Recommendation:** budget **N ≈ 80–150** for a thorough but theory-guided search of this family
(≈5 mechanism-backed signal/gate families × a few pre-declared parameterizations × 2 directions),
and **freeze that N before looking at results**. Going from 42 → 150 raises the per-trial benchmark
~26% (1.98 → 2.50) — a real but payable cost. The discipline: each *new* family added to Stage 0 must
be booked into N, so expansion is justified only when its mechanism prior is strong enough to beat the
higher bar. This is the quantitative form of `RESEARCH_E` §3 ("you pay for each look in deflation").

## 5. Candidate register (feeds Task 3 pre-registrations — not yet authorized)

| # | Candidate signal / gate | Source (t-stat / effect) | Post-2015? | One-line definition (implementable) |
|---|---|---|---|---|
| F1 | **Gamma-sign-gated intraday momentum** | Baltussen/Da/Soebhag EOD reversal **t=−6.28**; Dim/Eraker/Vilkov 0DTE | **Likely (growing)** | Take MIM-style continuation only when estimated dealer gamma is net-negative; flip to reversal when net-positive, measured pre-trade from prior-session option OI. |
| F2 | **End-of-day reversal** | Baltussen/Da/Soebhag **t=−6.28** | **Likely** | Predict the last-hour return as the negative of the prior end-of-day window return, on the existing SPY 1-min data. |
| F3 | **VIX-regime-gated MIM** | Lucca/Moench; Aleti/Bollerslev (uncertainty) | Moderate | MIM signal active only when VIX level (or term-structure slope) is in a pre-declared elevated bucket. |
| F4 | **Overnight-gap-conditioned MIM** | Akbas 2021; Lou/Polk/Skouras | Moderate | Condition MIM direction/size on the sign and bucketed magnitude of the overnight gap. |
| F5 | **Pre-FOMC calendar gate (PLACEBO/decay monitor)** | Lucca/Moench JF2015; disappearing-drift 2020 | **No (decayed)** | Flag scheduled-FOMC eve days; enter as a pre-registered placebo expected to fail — a decay check, not a gate. |
| F6 | **Sentiment secondary gate (put/call, IV skew)** | sentiment literature (weak) | Weak | Only as a tertiary filter on an already-clearing primary signal; not tested standalone. |

Priority for Task 3 pre-registration: **F1 and F2 first** (strongest mechanism + recent survival,
both runnable on data already owned), F3/F4 as conditioning variants, F5 as a mandatory placebo, F6
deferred.

## 6. Negative space — what the survey says is *not* worth a primary test
- Standalone overnight-drift trading in SPY (dies net of costs, t≈1.9).
- Put/call ratio or IV skew as standalone intraday direction signals (no replicated cost-surviving edge).
- Calendar drift (pre-FOMC) as a primary gate (decayed post-2015).
- Any re-slice of the killed 42 chart patterns (the 0/42 null already covers these).

**HANDOFF status note (for Build Master to incorporate; Research does not edit HANDOFF.md):**
Research F filed — discovery-survey complete. Highest-value new gate is dealer-gamma sign (F1/F2),
both mechanism-backed and runnable on existing SPY data; calendar (F5) enters as a placebo/decay
monitor. Recommended frozen discovery trial budget N≈80–150 (DSR benchmark ~2.26–2.50). Task 3
(pre-registration docs for F1, F2, then F3–F5) pending.

---

## Sources
- Gao, Han, Li & Zhou, "Market Intraday Momentum," *JFE* (2018). https://www.sciencedirect.com/science/article/abs/pii/S0304405X18301351
- Aleti, Bollerslev & Siggaard, "Intraday Market Return Predictability…," *Management Science* (2025). https://public.econ.duke.edu/~boller/Papers/MS_2025.pdf
- Baltussen, Da & Soebhag, "End-of-Day Reversal" (t=−6.28; MM hedging + LETF rebalancing). https://www3.nd.edu/~zda/EOD.pdf
- Dim, Eraker & Vilkov, "0DTEs: Trading, Gamma Risk and Volatility Propagation." https://papers.ssrn.com/sol3/papers.cfm?abstractid=4692190
- Cboe, "0DTE Index Options and Market Volatility." https://cdn.cboe.com/resources/education/research_publications/gammasqueezes.pdf
- Zarattini, Aziz & Barbon, "Beat the Market: An Effective Intraday Momentum Strategy for SPY," SFI WP 24-97 (practitioner; see RESEARCH_C caveat). https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4824172
- Lucca & Moench, "The Pre-FOMC Announcement Drift," *Journal of Finance* 70(1):329–371 (2015). https://onlinelibrary.wiley.com/doi/abs/10.1111/jofi.12196
- "The disappearing pre-FOMC announcement drift" (post-2015 decay). https://www.sciencedirect.com/science/article/abs/pii/S1544612320315956
- Lou, Polk & Skouras, "A Tug of War: Overnight Versus Intraday Expected Returns," *JFE* (2019). https://personal.lse.ac.uk/polk/research/TugOfWar.pdf
- Akbas, Boehmer, Jiang & Koch, "Overnight returns, daytime reversals, and future stock returns," *JFE* (2021). https://www.sciencedirect.com/science/article/abs/pii/S0304405X21004116
- State Street/SSGA overnight-anomaly cost analysis (via Alpha Architect). https://alphaarchitect.com/trading-costs-wipe-out-the-overnight-return-anomaly/
- Yoon, "VIX option-implied volatility slope and VIX futures returns," *J. Futures Markets* (2022). https://onlinelibrary.wiley.com/doi/full/10.1002/fut.22317
- Harvey & Liu, "Evaluating Trading Strategies" (haircut Sharpe; Bonferroni/Holm/BHY). https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2474755
- Romano & Wolf, "Stepwise Multiple Testing as Formalized Data Snooping," *Econometrica* 73(4):1237–1282 (2005). https://onlinelibrary.wiley.com/doi/abs/10.1111/j.1468-0262.2005.00615.x
- "The Generic Holdout: Preventing False-Discoveries in Adaptive Data Science." https://arxiv.org/pdf/1809.05596
- QuantPedia, "In-Sample vs. Out-Of-Sample Analysis of Trading Strategies." https://quantpedia.com/in-sample-vs-out-of-sample-analysis-of-trading-strategies/

*Research only. No order routing, broker, options, position sizing, or live execution. Strongest
permitted verdict: `eligible_for_paper_consideration`. Survey identifies candidates; it authorizes
nothing. Where this conflicts with `MASTER_PROJECT_BRIEF.md`, `CHATGPT_RESEARCH_PHASE_BRIEF.md`, or
`README.md`, those are authoritative.*
