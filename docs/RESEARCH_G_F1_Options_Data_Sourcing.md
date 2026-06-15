# RESEARCH_G_F1_Options_Data_Sourcing.md

**Research wing: Auto-Trader SPY | Signal: F1 — Dealer Gamma Sign-Gated Intraday Momentum**  
**Author:** Claude (Cowork research session)  
**Date:** 2026-06-15  
**Status:** PRE-BACKTEST — this document must be committed and immutable before any F1 backtest is run  
**Pre-registration reference:** `docs/PREREG_F1_gamma_gated_momentum.md`

---

> **⚠ Pre-Registration Integrity Notice**
>
> The data source selection documented here is made *prior to any backtesting of the F1 signal*. Choosing or switching data sources after observing backtest results would constitute a form of specification search / p-hacking, even if unintentional — it allows the regime-gate parameters to be implicitly calibrated against the very data they are meant to predict. Once a source is selected and locked below, it must not be changed without explicitly logging the reason and re-running the full pre-registration protocol.

---

## 1. Executive Summary

**Recommended primary source: CBOE DataShop — Option EOD Summary (SPY).** At $500/month for an ongoing subscription (or $400 as a one-time ad-hoc historical pull), CBOE DataShop provides the most authoritative, OPRA-sourced end-of-day options chain data available to a solo researcher at a defensible cost. Coverage begins in 2004, depth is complete for the critical 2010–present window, and the data includes OHLC prices, open interest, volume, and an optional Greeks/IV add-on at the 15:45 ET snapshot. Critically, CBOE offers a **free trial covering up to 6 months of historical EOD data** — sufficient to validate the pipeline before committing to a paid subscription. SPX index data requires an additional CGI license (from ~$1,000/month), so **SPY (the ETF) is the operationally correct underlying for cost-constrained solo work**, and it is already the execution instrument in the broader project.

**Runner-up: Polygon.io Options Flat Files.** Developer-friendly, OPRA-sourced, accessible via S3 bucket download, and directly compatible with the project's existing parquet/CSV pipeline. The key limitation is historical depth: quotes are available only from 2022 onward, and trades from 2016 — insufficient for a full 2010–present backtest on its own. Polygon becomes the right choice if the study period is shortened to 2016–present or 2022–present, which would sacrifice the pre-0DTE control period but would still allow a meaningful 0DTE-era analysis.

---

## 2. Comparison Table

| Source | Coverage | Cost (USD) | Format | Key Limitations |
|---|---|---|---|---|
| **CBOE DataShop** | 2004–present (some products to 1990) | $500/mo subscription; $400 one-time historical pull; +~$1k/mo CGI license for SPX index bid/ask | Flat files (daily delivery) + optional S3 | SPX requires separate CGI license; ETF/stock options (SPY) included at base price |
| **OptionMetrics Ivy DB** | Jan 1996–present | ~$10k–$50k+/year institutional; free via WRDS if at subscribing university | SQL query / flat file export via WRDS | Requires institutional or university access; pricing opaque for individual researchers; no self-serve signup |
| **Polygon.io** | Trades: 2016+; Quotes: 2022+ | Business plans start ~$199+/month per asset class; flat-file S3 tier higher | REST API + S3 flat files (CSV/parquet) | Historical quote depth insufficient for pre-2016 study window; 2022 start for full quote data |
| **Alpaca Markets** | Feb 2024–present only | Free with Algo Trader Plus ($99/mo) | REST API (alpaca-py SDK) | Entirely unusable for historical backtest (coverage starts 2024); only suitable for live paper-trading regime detection |
| **Nasdaq Data Link (Quandl)** | Varies by dataset; limited options chain datasets | Varies; many datasets paywalled | REST API + CSV | No comprehensive maintained options chain product; best datasets (OptionMetrics) repackaged here at similar or higher cost |
| **Interactive Brokers TWS** | Active contracts only; **no expired options** | Included with IBKR account (commissions apply) | TWS API (Python ib_insync) | Cannot retrieve historical data for expired contracts — entirely disqualifying for backtesting |
| **WRDS (via university)** | 1996–present (OptionMetrics); other datasets vary | Free to researchers at subscribing institutions | SQL query / bulk extract | Requires current faculty/PhD affiliation at subscribing university; not available to independent researchers |
| **Unusual Whales** | Historical options trades (depth unclear; likely 2017+) | $250/mo (full market historical trades) | REST API (100+ endpoints); CSV download | Retail-oriented; historical chain depth and OI completeness unverified for quantitative research use; 3-month CSV window on base plan |
| **Market Chameleon** | 2014–present | Subscription-based (tiered); export limited to 25 downloads/24h on premium | Web UI + CSV export; machine-readable data feed add-on | Download throttle (25/day) impractical for bulk historical chain ingestion; not pipeline-friendly |

---

## 3. Per-Source Detail

### 3.1 CBOE DataShop *(Recommended)*

CBOE DataShop (formerly Livevol Data Shop) is the official CBOE historical options data marketplace, sourced directly from OPRA. The **Option EOD Summary** product delivers end-of-day snapshots with OHLC prices, VWAP, trade volume, and open interest for every listed option on U.S. stocks, ETFs, and indices. An optional add-on provides implied volatility and Greeks (delta, gamma, vega, theta, rho) calculated at the 15:45 ET snapshot — directly eliminating the need to compute Black-Scholes gamma from raw chain data. Subscription pricing is $500/month for continuous delivery; historical ad-hoc pulls (one-time bulk orders) are $400/request per calendar month of data. A free trial covering up to 6 months of historical EOD data is available to qualifying new subscribers (both Options Members and non-Members), making it practical to validate the pipeline before paying.

**SPX vs. SPY note:** Underlying bid/ask prices for *index* options (^SPX, ^OEX) require a separate Cboe Global Indices (CGI) license starting at approximately $1,000/month. SPY ETF options do **not** require the CGI license and are included at the base $500/month rate. Since the F1 signal uses SPY as its execution instrument and dealer gamma from SPY options is a reasonable proxy for index dealer positioning, using SPY chains avoids the CGI license overhead entirely.

**Estimated storage (SPY, 2010–present, EOD):** SPY options have grown from roughly 5,000 active contracts/day (2010) to 50,000+ contracts/day post-2022 with 0DTE. Assuming an average of ~15,000 contracts/day × 3,750 trading days × ~300 bytes/record uncompressed ≈ **~17GB uncompressed; ~3–5GB in snappy-compressed parquet**. The 0DTE-era portion (2022–present) is disproportionately large but remains manageable on a single developer machine.

---

### 3.2 OptionMetrics Ivy DB *(Gold Standard, Institutionally Gated)*

OptionMetrics IvyDB US is the academic and institutional benchmark for historical options research, with coverage of every U.S. equity and index option since January 1996. It provides end-of-day prices, standardized implied volatilities (interpolated to fixed moneyness/maturity grid), and pre-calculated Greeks for the full option chain. In 2025, OptionMetrics added intraday snapshot tiers (10am, 2pm, 3:45pm) for subscribers. The data is the "citation standard" in academic finance (Gao, Han, Li, and Zhou 2018 — the paper motivating F1 — would have used OptionMetrics or a CBOE predecessor feed). Pricing is not publicly listed; institutional contracts typically run $10,000–$50,000+/year. The primary access path for cost-constrained researchers is via **WRDS** (see §3.7) at a subscribing university. Without institutional affiliation, OptionMetrics is not practically accessible to a solo researcher.

---

### 3.3 Polygon.io *(Good Developer Experience; Limited Historical Depth)*

Polygon.io sources its options data from OPRA, covering all 17 U.S. options exchanges. The flat-files offering delivers daily compressed CSV/parquet files to an S3-compatible endpoint — an architecture directly compatible with the project's existing ingestion pipeline. Real-time and delayed Greeks (delta, gamma, theta, vega) are computed per contract. **However, historical quote data is only available from 2022, and trade data from 2016** — insufficient for a full 2010–present study period. Business plan pricing starts at approximately $199+/month per asset class; the flat-files tier (for bulk S3 access) is priced separately and higher. Polygon is the right choice if the study window is narrowed to 2016–present (trades) or 2022–present (quotes), which would cover the critical 0DTE period but sacrifice the pre-weekly-expiry control years.

---

### 3.4 Alpaca Markets *(Disqualified for Historical Backtest)*

Alpaca's options historical data API is available only from February 2024 forward, with access provided via the alpaca-py SDK under an Algo Trader Plus subscription ($99/month). While Alpaca is already embedded in the project for SPY equity execution, its options data is categorically unsuitable for the F1 backtest which requires a study window starting no later than 2010. Its value to this project is limited to: (a) real-time 0DTE regime detection once F1 is deployed live, and (b) confirming that the live data feed matches the backtested signal construction. Do not use for historical work.

---

### 3.5 Nasdaq Data Link (formerly Quandl) *(Thin Options Coverage)*

Following Nasdaq's 2018 acquisition of Quandl and the 2021 rebranding to Nasdaq Data Link, the platform aggregates financial datasets from 400+ publishers. Options-specific coverage is inconsistent: the platform's strongest datasets are either repackaged OptionMetrics (with no cost advantage over direct access) or limited thematic products without full chain OI and Greeks. No comprehensive, researcher-grade EOD options chain product was found in current search results. This source is not recommended unless a specific third-party options dataset appears in the Data Link catalog meeting the minimum field requirements at a materially lower cost than CBOE DataShop — which would need to be re-verified at time of decision.

---

### 3.6 Interactive Brokers TWS API *(Disqualified for Backtesting)*

The IB TWS API can retrieve historical bar data and option chain data, but with a critical limitation: **it does not provide historical data for expired option contracts**. Only currently active contract iterations can be queried. Additionally, the API enforces strict pacing limits (≤60 requests per 10-minute window, no repeat identical requests within 15 seconds). These constraints make IBKR entirely unusable as a source for backtesting expired SPY options chains spanning 2010–present. The TWS API remains useful for live signal computation once F1 is deployed.

---

### 3.7 WRDS — Wharton Research Data Services *(Free If Eligible; Gated by University Affiliation)*

WRDS provides cloud-based SQL access to OptionMetrics and dozens of other institutional datasets. Eligible researchers (faculty, PhD students, and some masters/undergraduate researchers at subscribing universities) access the data free as part of their institution's annual subscription. The data quality is identical to direct OptionMetrics access. WRDS accounts are institution-generated — there is no individual purchase path. If you have current academic affiliation (or can establish one via a visiting researcher arrangement), WRDS is unambiguously the best value. If not, WRDS is unavailable, and CBOE DataShop is the fallback.

---

### 3.8 Unusual Whales and Market Chameleon *(Retail-Grade; Pipeline-Hostile)*

**Unusual Whales** offers a historical options trades API at $250/month for full market coverage, with 100+ REST endpoints covering Greek exposure (including GEX aggregates), dark pool flow, and options order flow. The platform's curated GEX metric (dealer gamma exposure by strike) is useful for quick validation but is a black-box calculation — re-deriving it from raw OI with full transparency is not possible here. CSV download is restricted to the last 3 months on base plans. The historical depth for full-chain open interest data has not been independently verified; the emphasis is on flow/trade data, not EOD OI snapshots. Not recommended as a primary source for F1 computation but could serve as a **secondary validation** of the computed GEX signal.

**Market Chameleon** provides options chain data back to 2014 via a web interface and machine-readable data feed. The 25-export-per-24h download cap on the premium subscription makes bulk historical ingestion for 12+ years of daily chains infeasible without either scraping (TOS concern) or an enterprise arrangement. The data feed product includes Greeks updated daily. Like Unusual Whales, Market Chameleon is acceptable for human-readable cross-checks but not for automated pipeline ingestion at scale.

---

## 4. Implementation Path

The existing pipeline ingests SPY 1-minute OHLCV bars as CSV/parquet files. The following steps integrate CBOE DataShop EOD options chains:

**Step 1 — Data acquisition (pre-backtest, one-time)**
- Sign up for CBOE DataShop free trial at `datashop.cboe.com` and request the 6-month historical EOD Open-Close trial dataset for SPY options.
- Validate the schema against the field requirements below (§4.1).
- If schema is valid, place a one-time ad-hoc historical order ($400/calendar month × number of months required) or subscribe at $500/month.
- Decision checkpoint: confirm source selection here before triggering any order that covers the backtest window.

**Step 2 — Schema mapping**

Minimum required fields from CBOE DataShop EOD delivery:

| CBOE field | Internal field | Notes |
|---|---|---|
| `expiration_date` | `expiry` | YYYY-MM-DD |
| `strike_price` | `strike` | Float, dollars |
| `call_put` | `option_type` | 'C' or 'P' |
| `open_interest` | `oi` | Contracts |
| `close` or `settlement_price` | `close_price` | Use settlement for index |
| `bid` / `ask` (if available) | `bid` / `ask` | For mid-price IV calc |
| `volume` | `volume` | Contracts traded |
| `underlying_close` | `spot` | EOD spot price of SPY |

If the Greek add-on is purchased, `gamma` is delivered directly at 15:45 ET, eliminating the Black-Scholes computation step.

**Step 3 — Daily chain ingestion script** (`data/options/ingest_cboe_eod.py`)

```python
# Pseudocode — full implementation in ingestion layer
import pandas as pd
from pathlib import Path

def load_cboe_eod(date: str, raw_dir: Path) -> pd.DataFrame:
    """Load and normalize a single-day CBOE DataShop EOD file."""
    path = raw_dir / f"option_eod_{date.replace('-','')}.csv.gz"
    df = pd.read_csv(path, parse_dates=['expiration_date'])
    df = df[df['underlying_symbol'] == 'SPY'].copy()
    df['dte'] = (df['expiration_date'] - pd.Timestamp(date)).dt.days
    return df[['expiration_date','strike_price','call_put',
               'open_interest','close','volume','underlying_close','dte']]
```

**Step 4 — Net dealer gamma computation** (`signals/gamma/compute_gex.py`)

```python
# Net dealer gamma = sum over all contracts of (OI × BS_gamma × 100 × spot)
# Sign convention: market makers assumed net short options
# => dealer_gamma = -1 × sum(OI_i × Γ_i × 100 × S)
# Negative dealer_gamma → dealers short gamma → hedge = BUY rallies, SELL dips (momentum-reinforcing)

def compute_net_dealer_gamma(chain: pd.DataFrame, spot: float, r: float = 0.05) -> float:
    from scipy.stats import norm
    import numpy as np
    results = []
    for _, row in chain.iterrows():
        T = max(row['dte'], 0.5) / 365.0  # floor at 0.5 days for 0DTE
        if row['close'] <= 0 or T <= 0:
            continue
        try:
            iv = implied_vol(row['close'], spot, row['strike_price'], T, r, row['call_put'])
        except Exception:
            continue
        d1 = (np.log(spot / row['strike_price']) + (r + 0.5*iv**2)*T) / (iv * np.sqrt(T))
        gamma = norm.pdf(d1) / (spot * iv * np.sqrt(T))
        # Dealer assumed short: multiply by -1
        results.append(-1 * row['open_interest'] * gamma * 100 * spot)
    return sum(results)
```

**Step 5 — Regime gate integration** (`signals/f1_gamma_gated_momentum.py`)

```python
# EOD dealer gamma is computed from prior-day chain
# Gate fires on NEGATIVE dealer_gamma (dealers short)
# Combined with realized vol gate (already in pre-reg)

def f1_regime_gate(date: str, gamma_series: pd.Series, vol_series: pd.Series) -> bool:
    dealer_gamma_t_minus_1 = gamma_series.loc[date]
    rv_t_minus_1 = vol_series.loc[date]
    return (dealer_gamma_t_minus_1 < 0) and (rv_t_minus_1 > VOL_THRESHOLD)
```

**Step 6 — Storage layout**

```
data/
  options/
    raw/
      cboe_eod/
        YYYYMMDD.csv.gz        # one file per trading day, SPY full chain
    processed/
      spy_net_dealer_gamma.parquet   # date-indexed Series of net dealer gamma values
      spy_options_eod.parquet        # filtered/normalized chain for full period
```

Estimated processed storage: ~3–5 GB (snappy parquet, SPY-only chains, 2010–present).

---

## 5. Open Questions for John to Resolve

The following decisions must be made before placing any data order or running any backtest. Answers should be documented in a `DECISIONS.md` or directly appended to the pre-registration document.

**Q1 — Budget range (monthly vs. one-time)**  
CBOE DataShop offers both a $500/month ongoing subscription and $400/calendar-month ad-hoc historical pulls. For a solo backtesting project, the ad-hoc path (buy only the years needed, once) likely costs less total. Covering 2010–2025 as one-time pulls = 15 years × 12 months × $400 = $72,000 — clearly not viable. The subscription at $500/month for 6 months while running the backtest = $3,000 total, then cancel. What is the realistic budget ceiling?

**Q2 — Study window (2010–present vs. 2016–present vs. 2022–present)**  
The 2010–present window captures the full pre-weekly, weekly, and 0DTE eras but requires CBOE DataShop (only source with pre-2016 coverage at solo-researcher cost). Shortening to 2016–present opens up Polygon.io (trades available from 2016). Shortening to 2022–present makes Polygon.io quotes available and reduces cost dramatically. However, shortening reduces statistical power and removes the pre-0DTE control period that motivates the hypothesis. The pre-registration should specify this window explicitly.

**Q3 — Academic affiliation**  
Do you have current or pending faculty/PhD affiliation at a WRDS-subscribing university? If yes, WRDS/OptionMetrics is free and is strictly superior data. WRDS would immediately become the recommended primary source. List of subscribing institutions is at `wrds-www.wharton.upenn.edu`.

**Q4 — SPX vs. SPY as gamma source**  
SPX options have substantially larger notional per contract and are the primary hedging vehicle for large dealers, making SPX chains arguably a better proxy for dealer net gamma. However, SPX data requires the $1,000/month CGI license on CBOE DataShop. Alternatively, SPY chains (10× smaller notional) are a reasonable proxy and are available at base price. The pre-registration should specify which underlying's chain is used to compute the regime gate.

**Q5 — Greek add-on vs. self-computed gamma**  
CBOE DataShop offers a pre-computed Greeks/IV add-on at the 15:45 ET snapshot for an additional fee. Using this eliminates the need to implement an implied-volatility solver and reduces numerical error. However, it introduces a dependency on CBOE's Black-Scholes implementation (interest rate assumptions, dividend treatment). For pre-registration integrity, the choice between pre-computed and self-computed gamma must be locked in before backtesting. The add-on cost was not publicly listed; contact DataShop directly.

**Q6 — 0DTE handling**  
Post-2022, SPY 0DTE options (options expiring the same day) account for the majority of volume. Their gamma spikes violently intraday and is largely meaningless at EOD (all have expired). The pre-registration should specify whether 0DTE contracts are included or excluded from the net dealer gamma calculation. Excluding them (dte > 0 filter) is safer for consistency across the full study window, since pre-2022 there were few/no true 0DTE contracts.

**Q7 — Data source lock-in timestamp**  
After answering Q1–Q6, the resolved data source choice should be committed to the repository with a git tag (e.g., `data-source-locked-v1`) and a timestamp. Any later change to the data source requires incrementing a pre-registration version number and re-running full backtests from scratch under the new specification.

---

## 6. Secondary Validation Sources

Regardless of primary source chosen, consider these free/low-cost cross-checks:

- **FlashAlpha GEX API** (`flashalpha.com`) — Free tier provides single-expiration GEX snapshots; Growth plan provides historical snapshots back to 2018 for SPY. Useful for sanity-checking the sign and order-of-magnitude of computed net dealer gamma, not as a primary data source.
- **SpotGamma** (`spotgamma.com`) — Provides GEX charts and data; has historically published a free daily SPX gamma level. No bulk historical API for backtesting.
- **GEX-Metrix** (`gexmetrix.com`) — Live SPX GEX dashboard using CBOE options data in real-time. Useful for live regime monitoring once signal is deployed.

---

## 7. Source References

- [CBOE DataShop — Option EOD Summary](https://datashop.cboe.com/option-eod-summary)
- [CBOE DataShop — Data Products](https://datashop.cboe.com/data-products)
- [CBOE DataShop — Academic Discount](https://datashop.cboe.com/academic-discount)
- [OptionMetrics — IvyDB US](https://optionmetrics.com/united-states/)
- [OptionMetrics — Data Products](https://optionmetrics.com/data-products/)
- [OptionMetrics on WRDS](https://wrds-www.wharton.upenn.edu/pages/about/data-vendors/optionmetrics/)
- [Polygon.io — Options Flat Files Overview](https://polygon.io/docs/flat-files/options/overview)
- [Polygon.io — Options for Business](https://polygon.io/business-options)
- [Alpaca — Historical Option Data Docs](https://docs.alpaca.markets/us/docs/historical-option-data)
- [Interactive Brokers — Historical Data Limitations](https://interactivebrokers.github.io/tws-api/historical_limitations.html)
- [IBKR Quant Blog — Historical Options & Futures via TWS API](https://www.interactivebrokers.com/campus/ibkr-quant-news/historical-options-futures-data-using-tws-api/)
- [WRDS — Wharton Research Data Services](https://wrds-www.wharton.upenn.edu/)
- [Unusual Whales — Data Shop](https://unusualwhales.com/data_shop)
- [Unusual Whales — Pricing](https://unusualwhales.com/pricing)
- [Market Chameleon — Subscription Compare](https://marketchameleon.com/Subscription/Compare)
- [Market Chameleon — Historical Option Chain Data (instructional)](https://marketchameleon.com/Instructional-Stock-and-Options-Trading-Videos/409/How-to-get-Historical-Option-Chain-Price-Data-Using-Market-Chameleon)
- [FlashAlpha — Historical GEX API](https://flashalpha.com/articles/historical-gex-api-backtesting-gamma-exposure-strategies)

---

*This document was produced as a research brief prior to any backtesting of the F1 signal. It is intended to be committed to the repository as an immutable research artifact. Do not modify this document after the data source selection in §5 has been resolved and committed.*
