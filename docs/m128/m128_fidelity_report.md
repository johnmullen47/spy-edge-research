# M128 — Fidelity Report (Step 1.6)

**Reference:** Heston, Korajczyk & Sadka (2010), "Intraday Patterns in the Cross-section of
Stock Returns," *Journal of Finance* 65(4):1369–1407.
**Scored BEFORE any cross-sectional result** (execution-freeze honored). Date: 2026-06-16.

Fidelity scale per axis: **Exact / Close / Approximate / Different**. Per the M128 protocol,
**if overall fidelity < Close, M128 is classified EXPLORATORY, not confirmatory.**

| Axis | HKS 2010 | M128 implementation | Score |
|---|---|---|---|
| **Universe** | CRSP point-in-time universe of NYSE/AMEX/NASDAQ common stocks (very broad, thousands of names); survivorship-correct by construction. | Top-150 by trailing-12m dollar volume from Alpaca active∪inactive us_equity roster, monthly rebalance, ETFs excluded. Delisted bars retained; roster has residual purged-ticker gaps. Liquidity proxy, **not** point-in-time index/CRSP constituents; far fewer names (150 vs thousands). | **Approximate** |
| **Horizon / Lag** | Half-hour-frequency periodicity; strongest at lag-1 day and at multiples of the trading day; documents weekly structure too. | Pre-registered lags L ∈ {1, 5, 10, 22} trading days; L=5 primary, L=1 co-primary (HKS's strongest horizon). Same-bucket alignment across days. | **Close** |
| **Predictor construction** | Half-hour intraday returns on a 13-interval RTH grid; cross-sectional regressions of interval-k return on lagged interval-k return; market/portfolio adjustment used. | 13-bucket RTH grid, clock-keyed, intraday-only returns; cross-sectional demean (market neutralization) within (date,bucket); Fama-MacBeth pooled-bucket slope. | **Close** |
| **Estimator / inference** | Fama-MacBeth cross-sectional regressions; time-series average of slopes with t-stats. | Fama-MacBeth per-date pooled slope; Newey-West(12) HAC t-stat on the slope mean. | **Close** |
| **Execution assumptions** | Academic predictive study; predictability documented at the return level, also via portfolio sorts. | Confirmatory test is cost-free predictive R²/slope (matches the paper); a separate economic-significance layer applies realistic costs. | **Close** |
| **Cost assumptions** | Notes that high-frequency turnover erodes tradeability; effect is primarily a return-predictability finding. | `RegimeAwareCostModel` applied to a decile L/S at 30-min holding; gross-to-net reported pre-result. | **Close** |
| **Sample period / venue** | 1990s–2000s US equities (their sample). | 2017–2026 US equities, Alpaca SIP consolidated. Different era (post-publication; McLean-Pontiff decay risk applies). | **Approximate** |

## Overall classification

The single material deviation is the **universe** axis: a 150-name liquidity-filtered proxy
rather than HKS's point-in-time CRSP cross-section of thousands of common stocks. This is the
known, prompt-anticipated deviation. The sample period is also a different (post-publication)
era. All other axes (lag, predictor, estimator, execution, cost) are **Close**.

**Overall fidelity: APPROXIMATE** (dragged below Close by the universe and era axes).

**Therefore M128 is EXPLORATORY, not confirmatory.** This is honest and expected: M128 cannot
claim a literature-grade confirmatory replication of HKS because it does not reconstruct the
point-in-time CRSP universe. What M128 *can* deliver rigorously:

1. A powered, preregistered, survivorship-controlled, negative-control-clean test of whether the
   HKS same-half-hour continuation effect is present in the **liquid US-stock cross-section**
   (top-150 ADV) over 2017–2026, at approximately the published magnitude.
2. An honest cost-adjusted economic-significance assessment.

A null here is interpretable as "the effect is absent or sub-threshold in the liquid large-cap
cross-section in the modern era," not as a refutation of HKS on its original universe. A positive
here is suggestive but not a confirmatory replication (universe fidelity < Close). Both readings
are stated in `M128_PREREG.yaml` and will be repeated in `m128_results.md`.

## Why the relative estimator limits survivorship sensitivity

HKS's effect is a *relative* (cross-sectional) continuation, estimated here on market-neutralized
(demeaned) returns via a slope through the origin. Survivorship bias chiefly distorts *mean*
returns (survivors outperform); it distorts the *cross-sectional autocorrelation of demeaned
half-hour returns* far less. Combined with Alpaca's retention of delisted bars, residual roster
gaps (purged tickers) are expected to bias the FM slope negligibly. This is the basis for scoring
the universe "Approximate" rather than "Different" despite the non-point-in-time construction.
