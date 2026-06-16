# Research I — Retail Quant Method Sweep (basis for F6–F10)

**From:** Research session (Cowork)
**To:** Build Master (Project Build 5) — review and commit
**Date:** 2026-06-15
**Status:** Permanent research record. Immutable once committed; revisions ship as
`RESEARCH_I_AMENDMENT_1.md`.
**Commit convention:** `RESEARCH_I: retail quant method sweep and F6-F10 pre-regs`
**Companion pre-registrations:** `PREREG_F6.md` (VRP), `PREREG_F7.md` (vol-managed), `PREREG_F8.md`
(ORB), `PREREG_F9.md` (intraday periodicity), `PREREG_F10.md` (FOMC cycle).

---

## 1. Executive Summary (bottom line first)

**A zoom-out from our signal families confirms three things.** (1) The retail-quant space is *not*
dominated by a handful of secret methods; it is a **fragmented application of a small number of
durable return-generating patterns** — risk premia, behavioral under-/over-reaction, microstructure,
structural forced-flow, and macro/calendar. (2) The gap between *claimed* and *evidenced* is enormous:
the rigorous literature shows **most technical rules do not survive data-snooping + costs**, **most
day traders lose** (Barber–Odean: <1% predictably profitable), and **published edges decay ~58%
post-publication** (McLean–Pontiff). (3) Our project is concentrated in **one** of the five pattern
buckets — intraday directional continuation/reversal — and is **under-exploring the other four.**

**The five methods selected for F6–F10 deliberately spread across the under-exploited buckets**, each
peer-reviewed or (for ORB) seriously practitioner-documented, each implementable on **SPY 1-min + VIX
daily with no data purchase**, each distinct from our current families, and each pre-registered with an
**honest — often low — expected probability of clearing Hard Gate A net.** Importantly, under
`RESEARCH_H` these are **new families (3–7)**: they are genuinely decorrelated from the momentum/reversal
cluster, so they **each add ~1 effective trial and raise the DSR bar** — search breadth is paid for in
deflation, exactly as `RESEARCH_E` requires.

**Ranked recommendation (evidence × feasibility × distinctiveness):** **F10 (FOMC cycle) > F6 (VRP) >
F7 (vol-managed) > F8 (ORB) > F9 (intraday periodicity).** None is a high-probability winner; the honest
unconditional base rate that any single one clears a rigorous net OOS harness remains low. F7/F8/F9 are
pre-registered as **likely-fail adjudications** of contested/decayed effects — valuable precisely
because the harness can settle them.

---

## 2. Phase 1 — The retail-quant landscape

### 2.1 What working methods actually exploit (pattern taxonomy)
Durable strategies cluster into five mechanism families. This taxonomy is the spine of the whole field:

1. **Risk premia (compensation for bearing risk).** The most robust and the basis of the systematic
   industry: equity, value, momentum, carry, and the **variance/volatility risk premium**. Cross-asset
   value & momentum premia are documented "everywhere" (Asness, Moskowitz & Pedersen 2013, JF). The VRP
   predicts market returns (Bollerslev, Tauchen & Zhou 2009). *Most reliable; smallest per-trade; needs
   patience and breadth.* → **F6**.
2. **Behavioral under-/over-reaction.** Momentum (underreaction/slow diffusion) and reversal
   (overreaction/liquidity). Real but **decaying and crowded** post-publication (McLean–Pontiff).
   *Our current MIM/EOD families live here.*
3. **Microstructure / liquidity / rebalancing.** Short-term reversal from bid-ask bounce; intraday
   **periodicity** from infrequent rebalancing (Heston–Korajczyk–Sadka 2010; Bogousslavsky 2016). *Often
   un-capturable net of the spread — a cost trap.* → **F9** (and a hazard for F2).
4. **Structural / forced-flow (supply-demand constraints).** Dealer **gamma hedging**, leveraged-ETF
   rebalancing, index reconstitution, options-expiry. *More persistent because it is mechanical, not
   informational* (Baltussen et al. 2021). *Our MIM-Baltussen and shelved F1 live here; ORB partly here.*
   → **F8**.
5. **Macro / calendar / policy.** **FOMC-cycle** equity premium (Cieslak–Morse–Vissing-Jorgensen 2019),
   pre-FOMC drift (decayed), turn-of-month. *Strong but visibility-prone to decay.* → **F10**.

### 2.2 Top documented approaches, by evidence strength
- **Strong, peer-reviewed, replicated:** cross-asset value/momentum premia (Asness et al.); variance
  risk premium (Bollerslev et al.); FOMC-cycle premium (Cieslak et al.); intraday periodicity
  (Heston et al.). Time-series/trend momentum (Moskowitz–Ooi–Pedersen) — strong but **contested**
  (Huang et al. "Is it there?").
- **Strong in-sample, contested out-of-sample:** volatility-managed portfolios (Moreira–Muir 2017 vs.
  Cederburg et al. 2020 / Barroso–Detzel / DeMiguel et al. 2024). A textbook in-sample-vs-real-time gap.
- **Practitioner-documented, academically thin / decayed:** opening-range breakout (Zarattini–Aziz 2023
  — but on **leveraged** ETFs / "stocks in play"); raw VWAP/EMA/breakout rules (folklore — fail
  data-snooping, Sullivan–Timmermann–White 1999; Bajgrowicz–Scaillet 2012). *This is the family our own
  0/42, then 0/100, results already falsified.*

### 2.3 Claimed online vs. actually evidenced
- **Claimed:** "consistent daily profits," indicator-cross systems, course-sold "edges," high-Sharpe
  intraday bots. **Evidenced:** **>80% of day traders lose; <1% are predictably profitable** (Barber,
  Lee, Liu & Odean, Taiwan); **technical rules do not survive data-snooping + costs**
  (Sullivan–Timmermann–White; Bajgrowicz–Scaillet); **edges decay ~58% post-publication**
  (McLean–Pontiff); **backtest overfitting yields negative OOS expectancy** (Bailey–Borwein–López de
  Prado–Zhu). The reliable takeaway: the *method-level* patterns in §2.1 are real; the *retail-influencer
  packaging* of them is mostly noise.
- **Net:** an honest retail edge is **small, capacity-limited, regime-bound, and risk-premium- or
  structure-based** — not a high-Sharpe chart-pattern machine.

### 2.4 Reputable practitioners vs. noise
- **Credible (methods + transparency):** **AQR** (Asness, Moskowitz, Pedersen — factor premia white
  papers, public datasets); **Marcos López de Prado** (backtest overfitting, DSR/PBO, the methodology
  backbone of our own harness); **Ernest Chan** (QTS Capital; *Quantitative Trading* / *Algorithmic
  Trading* / *Machine Trading* — mean-reversion & momentum with honest implementation caveats);
  **Gary Antonacci** (Dual Momentum — strong long-horizon evidence, though the relative leg needs
  multiple assets and OOS robustness is debated); research-grade blogs **Alpha Architect**, **Newfound
  Research / Corey Hoffstein**, **Robot Wealth**, and the **QuantConnect** strategy library (which
  usefully publishes *failures*, e.g., the Gao-MIM −0.63 Sharpe replication we relied on).
- **Noise:** course-sellers promising fixed daily returns, indicator-cross "systems," and unaudited
  track records. Credibility test we applied: *peer review or audited/transparent OOS, mechanism stated,
  costs charged, failures reported.*

---

## 3. Phase 2 — Top-5 selection and comparison to our approach

### 3.1 The five (ranked)
| Rank | Method (file) | Pattern bucket | Evidence | Feasibility (our data) | Distinct from current? | Honest P(clear net) |
|---|---|---|---|---|---|---|
| 1 | **FOMC cycle** (`F10`) | Macro/calendar | **Strong** — JF 2019, even-week premium since 1994 | SPY daily + free Fed calendar | Yes (F5 was only pre-FOMC *eve*) | ~25–35% (decay + few cycles) |
| 2 | **Variance risk premium** (`F6`) | Risk premia | **Strong** — RFS 2009, beats P/E, CAY at quarterly H | SPY 1-min RV + VIX | Yes (premium, not VIX-level gate) | ~20–30% (horizon/power) |
| 3 | **Vol-managed exposure** (`F7`) | Risk management | **Contested** — JF 2017 vs. JFE 2020 / JF 2024 | SPY + VIX | Yes | ~10–20% (likely-fail adjudication) |
| 4 | **Opening range breakout** (`F8`) | Structural/intraday momentum | **Practitioner** — strong but leveraged/stocks-in-play | SPY 1-min | Yes (breakout entry vs rest-of-day) | ~10–20% (un-leveraged SPY) |
| 5 | **Intraday periodicity** (`F9`) | Microstructure/rebalancing | **Peer-reviewed but cross-sectional** — JF 2010 | SPY 1-min | Yes | ~10–20% (single-asset, bounce) |

### 3.2 Where we are in the search space
Our committed/active families all sit in **bucket 2 (behavioral continuation/reversal)** with one foot in **bucket 4 (structural)**. F6–F10 fill the four un-explored buckets. The cost of that breadth is explicit: each is a new, decorrelated family that adds ~1 effective trial to the DSR budget — raising the bar, not loosening gates.

---

## 4. Phase 3 — The pre-registrations (F6–F10)

Each file freezes a ≤~18-candidate grid, classifies the family per `RESEARCH_H`, states data needs (all
on-hand / free), gives mechanism + citations, and pre-registers an honest expected range plus the full
anti-snooping harness (DSR with effective-N, PBO ≤ 0.50, walk-forward OOS on a calmer sub-period,
placebos, regime-aware cost). Method-specific binding controls:
- **F6:** realized-vol-only placebo + power report.
- **F7:** constant-weight placebo + turnover-cost gate + OOS-vs-buy-hold.
- **F8:** half-spread cost test + no-leverage scope.
- **F9:** bounce-only synthetic placebo + half-spread test.
- **F10:** independent-cycle-count power report + pre/post-2015 decay check.

---

## 5. Open questions and data gaps
1. **Base-rate realism.** Treat F6–F10 as a portfolio of cheap experiments mapping the space.
2. **Horizon vs. sample.** F6 and F10 are lower-frequency; power may be the binding constraint.
3. **Single-asset limitation (F9).** Native effect is cross-sectional; SPY-only is degraded.
4. **VIX term-structure data (F3/F6 adjacent).** Futures not on hand — flagged.
5. **No data purchases required for F6–F10.**

---

## Sources
- Asness, Moskowitz & Pedersen, "Value and Momentum Everywhere," *Journal of Finance* 68(3) (2013). https://onlinelibrary.wiley.com/doi/abs/10.1111/jofi.12021
- Bollerslev, Tauchen & Zhou, "Expected Stock Returns and Variance Risk Premia," *RFS* 22(11) (2009). https://academic.oup.com/rfs/article-abstract/22/11/4463/1565787
- Moreira & Muir, "Volatility-Managed Portfolios," *JF* 72(4) (2017). https://onlinelibrary.wiley.com/doi/abs/10.1111/jofi.12513
- Cederburg, O'Doherty, Wang & Yan, "On the performance of volatility-managed portfolios," *JFE* (2020). https://www.sciencedirect.com/science/article/abs/pii/S0304405X2030132X
- DeMiguel, Martín-Utrera & Uppal, "A Multifactor Perspective on Volatility-Managed Portfolios," *JF* (2024). https://onlinelibrary.wiley.com/doi/full/10.1111/jofi.13395
- Zarattini & Aziz, "Can Day Trading Really Be Profitable? (ORB)," SSRN 4416622 (2023). https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4416622
- Heston, Korajczyk & Sadka, "Intraday Patterns in the Cross-section of Stock Returns," *JF* 65(4) (2010). https://onlinelibrary.wiley.com/doi/abs/10.1111/j.1540-6261.2010.01573.x
- Bogousslavsky, "Infrequent Rebalancing, Return Autocorrelation, and Seasonality," *JF* 71(6) (2016). https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2308366
- Cieslak, Morse & Vissing-Jorgensen, "Stock Returns over the FOMC Cycle," *JF* 74(5) (2019). https://onlinelibrary.wiley.com/doi/abs/10.1111/jofi.12818
- Barber, Lee, Liu & Odean, "Do Individual Day Traders Make Money? Evidence from Taiwan." https://faculty.haas.berkeley.edu/odean/papers/Day%20Traders/Day%20Trade%20040330.pdf
- McLean & Pontiff, "Does Academic Research Destroy Stock Return Predictability?," *JF* (2016). https://onlinelibrary.wiley.com/doi/abs/10.1111/jofi.12365
- Sullivan, Timmermann & White, "Data-Snooping, Technical Trading Rule Performance, and the Bootstrap," *JF* 54(5) (1999). https://onlinelibrary.wiley.com/doi/10.1111/0022-1082.00163
- Bajgrowicz & Scaillet, "Technical Trading Revisited," *JFE* 106(3) (2012). https://www.sciencedirect.com/science/article/abs/pii/S0304405X1200116X
- Bailey, Borwein, López de Prado & Zhu, "Pseudo-Mathematics and Financial Charlatanism" (2014). https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2308659
- Antonacci, "Risk Premia Harvesting Through Dual Momentum," SSRN 2042750. https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2042750
- Chan, *Algorithmic Trading: Winning Strategies and Their Rationale* (Wiley).
- Internal: `RESEARCH_E`–`RESEARCH_H`, `RESEARCH_F_Signal_Discovery.md`, `PREREG_F6`–`PREREG_F10`.

*Research only. No order routing, broker, options, position sizing, or live execution.*
