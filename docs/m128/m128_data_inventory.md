# M128 — Data Inventory (Gate 0.5, Step 1B)

**Date:** 2026-06-16. Written BEFORE any cross-sectional result (execution-freeze honored).
Universe construction and data inventory are explicitly pre-freeze deliverables (not a
predictor→target result).

## 1. Data adequacy probe (`scripts/m128_probe_alpaca.py`)

Three decision-critical questions, answered empirically against Alpaca SIP:

| Q | Result |
|---|---|
| **Q1.** SIP 30-min bars for arbitrary stocks back to 2016? | **YES.** AAPL/MSFT/JPM return 30Min bars for Jan-2016 and into May-2026 (HTTP 200, non-empty). |
| **Q2.** Are bars RETAINED for DELISTED symbols? *(survivorship crux)* | **YES.** All six probed delistings returned bars during their active life: TWTR (2022-09), ATVI (2023-08), XLNX (2021-11), CELG (2019-08), WORK (2021-05), DISCA (2022-02). |
| **Q3.** Does `/v2/assets` expose inactive/delisted names? | **PARTIAL.** 13,824 active + 19,256 inactive us_equity. Inactive captures XLNX/CELG/WORK but **not** TWTR/ATVI/DISCA (purged from the registry even though their bars remain fetchable). |

**Implication:** A survivorship-*controlled* universe is constructible (return data exists for
delisted names) → M128 is **NOT data-blocked**. Residual gap: the asset roster is an incomplete
record of every ticker that ever traded (some purged), so a roster-driven universe omits a few
genuinely-liquid names that later delisted (TWTR, ATVI). Disclosed; magnitude quantified below.

## 2. Universe construction (no-lookahead)

Pipeline (all scripts stdlib/pandas, credentials never committed):

1. `m128_fetch_roster.py` — roster = active ∪ inactive us_equity; mechanical common-stock
   symbol filter `^[A-Z]{1,5}$` or `^[A-Z]{1,4}\.[A-Z]$`. **Kept 31,745** symbols
   (active_raw 13,824; inactive_raw 19,256; dropped_nonstd 1,100 warrants/units/preferreds).
2. `m128_scan_daily_volume.py` — daily SIP bars (raw) 2016-01-01..2026-06-13 for the full
   roster; streamed to per-(symbol,month) dollar-volume aggregates
   (`daily_dollar_volume.csv`). This is the no-lookahead liquidity primitive.
3. `m128_build_universe.py` — at each monthly rebalance r, trailing-12-month ADV uses ONLY
   months r-12..r-1 (strictly prior). Require ≥200 trading days of history. Exclude ETFs/ETNs/
   funds (name-token filter + explicit high-volume ETF set). Rank by ADV; take **top 150**.
   First rebalance 2017-01 (2016 = burn-in); last 2026-06.

**Survivorship control:** the roster includes Alpaca's inactive (delisted) names, and bars are
retained for them, so delisted stocks can be and are members during their liquid lifetimes and
exit the universe when they stop trading. The build tracks entries/exits.

<!-- UNIVERSE_SUMMARY_START -->
**Universe summary** (`data/raw/m128/universe_summary.json`, 2026-06-16):

| Metric | Value |
|---|---|
| Top-N per month | 150 (full every month) |
| Rebalance months | 114 (2017-01 .. 2026-06) |
| Membership rows | 17,100 |
| Distinct symbols ever in-universe | **341** |
| Mean monthly turnover (symmetric) | **2.05%** (low — a stable liquid universe) |
| ETF-like names excluded | 6,061 |
| Min trailing days required | 200 |
| Names with `inactive` (delisted) status while in-universe | **14 (4.1%)** |
| Names exiting before final month (liquidity-rank churn + delisting) | 191 (56.0%) |

- **Top-10 (2017-01):** AAPL, META, AMZN, MSFT, BAC, GOOGL, GOOG, BABA, JPM, WFC.
- **Top-10 (2026-06):** NVDA, TSLA, AAPL, MSFT, MU, AMZN, AMD, META, GOOGL, PLTR.
- **Delisted large-caps captured in-universe** (survivorship control working): AABA (Altaba),
  AGN (Allergan→AbbVie), ALXN (Alexion→AstraZeneca), CELG (Celgene→BMS), CXO (Concho→COP),
  DWDP (DowDuPont), ESRX (Express Scripts→Cigna), MYL (Mylan→Viatris), RHT (Red Hat→IBM),
  RTN (Raytheon merger), SHPG (Shire→Takeda), WORK (Slack→CRM), WP (Worldpay), XLNX (Xilinx→AMD).

**Residual survivorship gap (disclosed):** a few liquid names that delisted are *absent* from the
Alpaca asset roster despite having fetchable bars (TWTR, ATVI, DISCA — see Q3). These ≈3–5 names
(~1% of the 341-name pool) are the irreducible gap from using the asset registry as the roster.
Direction of bias on the FM slope: negligible, because the estimator is a *relative* (demeaned)
cross-sectional slope, not a mean-return measure (see `m128_fidelity_report.md`).
<!-- UNIVERSE_SUMMARY_END -->

## 3. 30-minute bar pipeline

`m128_fetch_universe_bars.py` pulls 30Min SIP RTH bars (raw) for the UNION of all symbols ever
in the universe (+ negative-control ETFs SPY/QQQ/IWM/DIA), 2016-01-01..2026-06-13 (2016 included
so the lag reach-back from early-2017 has data). One canonical OHLCV CSV per symbol in
`data/raw/m128/bars30/`. RTH only (09:30–16:00 ET), deduped, ascending.

## 4. Session definitions & missing-data treatment

- **Timezone:** America/New_York. **Session:** RTH only → 13 half-hour buckets
  (09:30→10:00, …, 15:30→16:00), clock-keyed by bar start time.
- **Bucket returns:** within-day mark path `[open of first bar, then each bucket's close]`;
  `ret_b = log(mark_b / mark_{b-1})`. All intraday (no overnight). Causal.
- **Halted/short days:** clock-keyed buckets; a day contributes only the buckets present. A
  stock with a missing bucket simply has no observation for that (date,bucket); it is dropped
  pairwise in the cross-sectional regression, never forward-filled.
- **Membership masking:** a stock contributes to a (date,bucket) cross-section only if it is a
  universe member on that date. The lag reach-back from early-2017 into 2016 (where membership
  is undefined) is masked out → the effective test sample starts a few trading days into 2017.

## 5. Trial budget (Step 1C)

k = 4 pre-registered trials (lags L ∈ {1,5,10,22}, all-buckets-pooled). Hard cap 7. Bonferroni
α/k = 0.0125, two-sided crit t = 2.498. Locked in `M128_PREREG.yaml`.
