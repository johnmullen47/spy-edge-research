# m127_fidelity_report

**Milestone:** M127 · **Step 1.6** · **Date:** 2026-06-16 (written before any real-data
result; freeze-compliant)

Each co-primary hypothesis is scored **against its own source paper** on five dimensions
(Exact / Close / Approximate / Different). A hypothesis with overall fidelity **below Close**
would be reclassified EXPLORATORY and its result not used as evidence for/against the source
finding. **Both H_a and H_b score ≥ Close → both remain confirmatory.**

## H_a — Gao, Han, Li & Zhou (2018), *JFE* 129(2):394–414

| Dimension | Score | Justification |
|---|---|---|
| **Universe** | **Exact** | Gao's headline instrument **is the SPY ETF** (S&P 500 ETF, 1993–2013). We test SPY — the same instrument. |
| **Horizon** | **Exact** | Predictor = first-30-min return from prior close (`log(P_1000/P_prev_close)`); target = last-30-min return (`log(P_1600/P_1530)`). Matches Gao's `r1 → r_last`. |
| **Predictor** | **Exact** | Gao's `r1 = P_{first-half-hour}/P_{prev_close} − 1`, measured from the prior close. Implemented identically (log form). |
| **Execution assumptions** | **Close** | The confirmatory test is Gao's **predictive regression** (no trading frictions in the core predictability claim), which we reproduce. Gao also report a sign-timing strategy with costs; that is an optional non-confirmatory economic layer here. |
| **Cost assumptions** | **Close / N-A** | Confirmatory R²/t-stat claim is cost-free in the paper; our confirmatory test is likewise cost-free, with an optional regime-aware cost layer reported separately. |
| **Sample period** | Approximate | Gao 1993–2013; we use 2016–2026 (post-publication). This is **intentional** (the replication question is whether the effect persists), not a fidelity defect in construction. Flagged for interpretation (decay is a possible null cause). |

**H_a overall fidelity: EXACT–CLOSE → confirmatory.** Same instrument, same windows, same
predictor. The only gap is sample era (later, post-publication) — a feature of a replication,
not a distortion.

## H_b — Baltussen, Da, Lammers & Martens (2021), *JFE* 142(1):377–403

| Dimension | Score | Justification |
|---|---|---|
| **Universe** | **Different (documented)** | Baltussen's evidence base is **60+ futures** (equity/bond/commodity/FX), 1974–2020 — **not** the SPY ETF. We test SPY because no futures data is available (see blocker report). This is the one material fidelity gap. |
| **Horizon** | **Exact** | Predictor = rest-of-day return prior close → start of final 30 min (`log(P_1530/P_prev_close)`); target = final-30-min return. Matches Baltussen's construction. |
| **Predictor** | **Exact** | Rest-of-day cumulative return into the last 30 minutes — identical definition (and identical to the repo's existing `mim_baltussen_features.r_rod`). |
| **Execution assumptions** | **Close** | Confirmatory test = Baltussen's predictive regression (HAC t-stats), reproduced. |
| **Cost assumptions** | **Close / N-A** | As H_a: cost-free confirmatory claim; optional regime-aware cost layer separate. |
| **Sample period** | Approximate | Baltussen 1974–2020; we use 2016–2026 (overlaps the tail, extends past). |

**H_b overall fidelity: CLOSE (with an explicit instrument caveat).** Predictor, horizon and
target are exact; the gap is **instrument (SPY ETF vs futures)**. Per the scoring rule, CLOSE
keeps H_b confirmatory — but the caveat is binding for interpretation: a **null for H_b on SPY
is not a rejection of Baltussen's futures finding**, only evidence about the SPY ETF. The
mechanism (gamma-hedging/LETF-rebalancing forced flow) is futures-/options-centric, so the ETF
is a plausible-but-degraded carrier. If futures data is later acquired, H_b should be re-scored
Universe = Exact and re-run as the true primary.

## Cross-hypothesis notes

- **Daily aggregation** (one observation per trading day) matches both papers' regression
  design and the power analysis.
- **Causality**: both predictors are known at or before the target window start (10:00 / 15:30
  ≤ 15:30); no look-ahead. Enforced in `build_mim_daily_frame` and unit-tested on synthetic
  fixtures.
- **Conditioning** (high-volatility subsample) is taken directly from Gao's documented
  concentration result and is causal (vol measured through 15:30). It is part of the published
  result, not a variant.

**Conclusion:** H_a is a near-exact replication on its native instrument; H_b is a faithful
replication of the predictor/horizon on a *different* (best-available) instrument, flagged
CLOSE with an explicit ETF-vs-futures caveat. Both proceed as confirmatory; neither result may
be read beyond what its fidelity supports.
