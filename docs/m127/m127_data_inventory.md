# m127_data_inventory

**Milestone:** M127 · **Step 1A** · **Date:** 2026-06-16

## Intraday bar data present in the repo

| File | Instrument | Feed | Range | Trading days | Bars/day (median) | Volume fidelity | Notes |
|---|---|---|---|---|---|---|---|
| `data/raw/spy_1min.csv` | SPY ETF | **IEX** | 2024-06-14 → 2026-06-12 | **499** | 388 (RTH=390) | **~1–2% of consolidated** (single venue) | thin/understated volume; recent window |
| `data/raw/spy_1min_sip.csv` | SPY ETF | **SIP** | 2023-01-03 → 2024-12-31 | **502** | 390 | full consolidated | older window; free-tier SIP blocks recent ~15 months |
| `data/raw/vix_daily.csv` | VIX/VIX9D/VIX3M | CBOE | 1990 → 2026-06-15 | (daily) | 1 | n/a | daily regime input only (M122) |

**No other instruments exist.** None of the mission's required universe is present:
ES, MES, NQ, MNQ (futures) — **absent**; QQQ, IWM, DIA (ETFs) — **absent**.

## Per-field detail (the two SPY series)

- **Bar resolution:** 1-minute, OHLCV, `timestamp,symbol,open,high,low,close,volume`.
- **Session definition:** Regular Trading Hours (RTH) 09:30–16:00 ET; the vendor's last
  bar is 15:59 (≈ the 16:00 print). 390 bars/full RTH day. **The MIM windows are defined
  on RTH:** first-30-min = 09:30→10:00; last-30-min = 15:30→16:00; rest-of-day = prior
  close → 15:30. (No ambiguity for SPY RTH; futures would require an explicit RTH-vs-Globex
  pre-registration decision — flagged, not silently chosen.)
- **Missing periods:** IEX has reduced-bar days (min 47 bars — half-days / early closes);
  SIP min 308. Half-days are handled by the existing causal feature code (windows keyed to
  clock time, last bar via `duplicated`).
- **Corporate actions:** fetched `--adjustment raw`; SPY had no splits in either window, so
  raw is acceptable. (No dividend adjustment — irrelevant for intraday same-day returns.)
- **Futures roll handling:** N/A (no futures data).
- **Overlap:** the two feeds overlap 2024-06-14 → 2024-12-31 (~140 days) on **different
  feeds** (SIP full-volume vs IEX thin). They are **not** a single homogeneous series.

## Acquirability with current tooling

- **Other equity ETFs (QQQ/IWM/DIA):** fetchable via `scripts/fetch_spy_bars.py --symbol …`
  (Alpaca stocks), but under the **same feed limits** as SPY — free tier = IEX (thin) for
  recent data; SIP only for older history. So they would inherit the same short/thin
  constraints and add no power for the canonical (full-volume, long-history) effect.
- **Futures (ES/MES/NQ/MNQ):** **NOT acquirable** with the repo's tooling. Alpaca's
  market-data API used here serves equities only; there is no futures fetcher and no
  configured futures vendor. The mission's **primary** instrument is therefore unavailable.

## Implications for Gate 0.5

- The **only** confirmatory-eligible candidate series are the two SPY feeds (~500 days each).
- The mission-designated **primary instrument (ES/MES)** and the entire **futures evidence
  base for H_b** are absent and not fetchable → the literature-faithful primary design
  cannot be instantiated.
- A SIP+IEX spliced union reaches ~861 distinct calendar trading days, but **mixes a
  full-volume and a thin feed across the splice** — a data-quality/fidelity violation for a
  volume-/microstructure-sensitive intraday effect — so it does not constitute a single
  clean, adequately-powered, literature-faithful series. Documented and rejected, not used.

→ Proceed to `m127_power_report.md` for the formal power classification.
