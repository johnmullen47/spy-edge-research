# RESEARCH_K: Untested Technical Analysis Domains and Future Research Directions

**Status:** Prospective — for future workers on this project  
**Author:** Auto-Trader Master Agent (Cowork), 2026-06-16  
**Immutable once committed; amendments ship as RESEARCH_K_AMENDMENT_1.md**

---

## Context

The project through v0.3 (M100–M128) tested a specific slice of technical analysis: intraday same-time-of-day return continuation effects (MIM, Gao 2018; HKS cross-sectional, Baltussen 2021). Both milestones returned null results consistent with post-publication decay (McLean-Pontiff 2016: ~58% average decay across 97 anomalies). Hard Gate A remains NEGATIVE at 0/672 candidates eligible (M126).

This memo catalogues untested technical analysis domains, evaluates each against the project's constraints (no new data spend, Alpaca SIP already available), and proposes a priority ordering for future work.

---

## What the Project Has and Has Not Tested

**Tested:**
- Intraday same-time-of-day momentum (MIM) on SPY, 2016–2026 — NULL
- Cross-sectional intraday periodicity (HKS) on 334-stock universe, 2023–2026 — NULL
- Factor families F1–F10 across 672 candidates (M126) — 0 eligible after Hard Gate A
- Confirmatory HAC regression replication of MIM on SPY — NULL_NON_REPLICATION

**Not tested (this document):**
- See sections below

---

## Priority 1: Within Current Data Constraints ($0 New Spend)

These are testable with Alpaca SIP minute/daily bars already in hand. Each deserves a preregistered milestone before execution.

### 1a. Overnight / Open Decomposition

**Hypothesis:** The equity premium accrues disproportionately overnight (close-to-open), not during regular trading hours (RTH). Overnight gap patterns and open auction effects may exhibit systematic structure exploitable at retail scale.

**Literature:** Lou, Polk, Skouras (2019, JFE) — nearly all equity premium accrues overnight across global markets. Hendershott, Jones, Menkveld (2011) on algorithmic trading and overnight price discovery.

**Data:** Alpaca SIP provides open and close prices for all symbols → overnight returns calculable at $0 additional cost.

**Why this is the highest-priority extension:** The project exclusively tested RTH intraday signals. The overnight half of the return distribution has not been touched. Academic grounding is strong. Implementation straightforward given existing pipeline.

**Suggested milestone:** M129 — Overnight Return Decomposition. Preregister: long-minus-short overnight momentum signal vs. RTH counterpart, Fama-MacBeth or HAC regression, same universe as M128.

### 1b. OOS HKS Signal (Preregistered IS/OOS Split)

**Hypothesis:** The M128 OOS sub-period (2025–2026) showed a sign-unstable positive slope for the HKS effect (L=1 t=4.10, L=5 t=2.45) not present in the full IS period. This is hypothesis-generating only — the OOS window is too short and the IS result was null. A properly pre-registered IS/OOS split at a longer OOS window could evaluate whether this is noise or a real regime shift.

**Data:** Same Alpaca SIP data, $0 additional cost.

**Caution:** The t-statistics above are NOT a green light for trading. They were observed post-hoc on a short window. Any test must be pre-registered before examining the specific sub-periods, with Bonferroni or Holm correction for the implicit multi-testing.

**Suggested milestone:** M130 — Preregistered IS/OOS HKS Regime Test.

### 1c. Multi-Day Momentum and Short-Term Reversal

**Hypothesis:** Daily-horizon cross-sectional momentum (Jegadeesh-Titman, 1993) and short-term 1-week reversal (Jegadeesh, 1990) effects may persist at residual levels after decay.

**Data:** Alpaca daily bars, $0 additional cost.

**Priority rating: LOWER.** Post-publication decay on both effects is well-documented and extensive. Transaction costs at retail scale make even a real signal marginal. Recommend only after 1a and 1b are complete.

---

## Priority 2: Requires New Data Spend

These are credible research directions but blocked by data constraints unless new vendors are engaged.

### 2a. ES/MES Futures — Decisive H_b Test

**Hypothesis:** The M127 null for H_b (SPY-vs-futures basis as MIM mechanism) may be driven by using SPY as a futures proxy. ES/MES futures provide the decisive test.

**Data needed:** Databento, IQFeed, or CME DataSuite — minute-bar ES/MES futures back to 2016. Estimated cost: $50–$200/month depending on vendor and history window.

**Why it matters:** This is the one remaining decisive test of the MIM mechanism hypothesis. All other H_b tests were compromised by SPY-as-futures-proxy limitations (noted in m127_fidelity_report.md). Verdict would either confirm or definitively close the MIM mechanism branch.

### 2b. Options-Derived Signals (F1, Volatility Surface)

**Hypothesis:** Gamma exposure (GEX), put-call ratio, and implied volatility surface signals may contain return-predictive information not captured by price-based signals alone. F1 (gamma-gated MIM) was pre-scoped in M126 but remained data-blocked.

**Data needed:** Polygon.io options chain (minute-bar strikes, IV surface) or CBOE historical options data. Estimated cost: $100–$300/month.

### 2c. Order Flow and Market Microstructure

**Hypothesis:** Order flow imbalance, bid-ask spread dynamics, Kyle's lambda, and Amihud illiquidity signals may contain return-predictive information at horizons the project hasn't tested.

**Data needed:** Tick-by-tick or Level 2 order book data — significantly more expensive than current data stack (~$500+/month for quality sources). Noted here for completeness; unlikely to be cost-effective for retail-scale deployment even if an edge is found.

---

## Not Recommended for Serious Research Effort

The following domains are either theoretically weak, heavily arbitraged, or practically untestable within the project's constraints without disproportionate statistical risk:

- **Classic retail TA indicators** (RSI, MACD, Bollinger Bands, moving average crossovers): Low theoretical grounding, high data-mining risk, extensive informal testing by retail community with no rigorous evidence. Not worth the statistical testing budget.
- **Seasonality effects** (turn-of-month, day-of-week, January effect, pre-holiday drift): Published anomalies with well-documented decay; no evidence these survive transaction costs at retail scale.
- **Chart pattern recognition** (head-and-shoulders, support/resistance, triangle patterns): No reliable operationalization for systematic testing; results in the literature are inconsistent.

---

## Interaction with Hard Gate A

**Hard Gate A remains the gating constraint for live trading regardless of which domain is tested next.** Any milestone result — even a positive in-sample signal — must clear DSR + PBO + IS-Sharpe before the live layer is enabled. The security constraints in `docs/PROJECT_HANDOFF.md` and `src/` are immutable.

The overnight decomposition and OOS HKS tests are most likely to generate hypotheses worth formalizing into Gate A candidates. Multi-day momentum has the weakest prior given known decay.

---

## Recommended Milestone Sequence

| Priority | Milestone | Domain | Data Cost | Gate A Candidate? |
|---|---|---|---|---|
| 1 | M129 | Overnight/open decomposition | $0 | Possible |
| 2 | M130 | Pre-registered OOS HKS split | $0 | Low (hypothesis-generating) |
| 3 | M131 | ES/MES futures H_b test | ~$100–200/mo | Depends on result |
| 4 | M132 | Multi-day momentum/reversal | $0 | Low (decay) |
| 5 | M133 | Options-derived signals (F1) | ~$200–300/mo | Unknown |

---

## References

- Gao, C., Haggard, K., Li, X. (2018). *Intraday Momentum: The First Half-Hour Return Predicts the Last Half-Hour Return.* Journal of Financial Markets.
- Baltussen, G., Swinkels, L., Van Vliet, P. (2021). *Global Factor Premiums.* Journal of Financial Economics.
- Lou, D., Polk, C., Skouras, S. (2019). *A Tug of War: Overnight Versus Intraday Expected Returns.* Journal of Financial Economics.
- McLean, R.D., Pontiff, J. (2016). *Does Academic Research Destroy Stock Return Predictability?* Journal of Finance.
- Jegadeesh, N. (1990). *Evidence of Predictable Behavior of Security Returns.* Journal of Finance.
- Jegadeesh, N., Titman, S. (1993). *Returns to Buying Winners and Selling Losers.* Journal of Finance.
- Moskowitz, T., Ooi, Y.H., Pedersen, L.H. (2012). *Time Series Momentum.* Journal of Financial Economics.
