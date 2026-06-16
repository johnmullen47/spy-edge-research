# m127_power_report

**Milestone:** M127 · **Steps 1B + 1C + 1D** · **Date:** 2026-06-16 (original)
**Original verdict: NO-GO (BLOCKED)** — based on the intraday data *on disk* (~502-day SPY
CSVs). **SUPERSEDED in part by the 2026-06-16 data-availability audit — see the addendum
below.**

---

## ⚑ ADDENDUM (2026-06-16) — Alpaca SIP unblocks the SPY-primary path

A read-only audit of the *already-configured, already-paid* data subscriptions (no new
spend) found that the original blocker was an artifact of only a partial CSV being on disk —
**not** a subscription limit:

- **Alpaca SIP is active and full-history on the current plan:** SPY 1-minute, **2016-01-01 →
  real-time** (a live bar at 2026-06-16 11:53Z was confirmed; the old "free-tier SIP blocks
  the recent ~15 months" note is stale for this account). That is **≈ 2,620 full-volume
  trading days** — **~3.5× the 733-day requirement** for 80% power at the Bonferroni alpha.
- Earliest Alpaca **IEX** SPY minute = 2020-07-27 (≈1,490 days, but thin single-venue volume).
- **Polygon** REST is free/limited (~2 years SPY only; `NOT_AUTHORIZED` deeper) and **does not
  serve futures** — redundant here.
- **yfinance** caps at ~30 days of 1-min — unusable.
- **No configured source serves futures (ES/MES/NQ/MNQ).**

**Revised classification:**

| Path | Instrument / series | N (days) | Power @ Bonferroni (r=0.13) | Class | Cost |
|---|---|---|---|---|---|
| **SPY-primary (recommended)** | **SPY SIP 2016→now (Alpaca, full volume)** | **~2,620** | **>0.999** | **`adequately_powered`** | **$0 (already paid)** |
| SPY robustness | SPY IEX 2020→now (thin) | ~1,490 | >0.99 (but volume-distorted) | exploratory (fidelity ⚠) | $0 |
| Futures-primary (mission's intended) | ES/MES (H_b native base) | 0 (no source) | — | **still BLOCKED** | new vendor (paid) |

**Revised verdict:**
- **SPY-primary M127 (H_a + H_b on Alpaca SIP 2016→now): GO is now possible — adequately
  powered, $0 new spend.** The required action is simply to fetch the deeper SIP history
  (`fetch_spy_bars.py --feed sip --start 2016-01-01`), which the tooling already supports.
  Fidelity caveat: this tests the SPY **ETF**, not futures, so H_b is evaluated off its native
  (futures) instrument → score "Close, different instrument," not "Exact" (record in the
  Step 1.6 fidelity report when M127 is re-commissioned).
- **Futures-primary M127 (ES/MES, as originally specified): remains BLOCKED** — no configured
  source provides futures; this is the only genuine new-spend item.

Everything below is the original Step 1B–1D analysis (unchanged; it correctly described the
*on-disk* data but understated what the *subscriptions* can fetch).

---

## 1B — Trial budget & multiple-testing

- **Pre-registered confirmatory test count:** `k = 7` (hard cap k ≤ 7 respected).
- **Correction:** **Bonferroni** (stricter than the repo's BH-FDR for a small fixed `k`,
  and the mission says use the stricter). Family-wise alpha `α_family = 0.05`.
- **Per-test alpha:** `α = 0.05 / 7 = 0.00714` (two-sided), critical `z = 2.6901`.
- **Confirmatory vs exploratory:** only `adequately_powered` instruments (power ≥ 0.80 at α)
  may host confirmatory tests; `underpowered` series are exploratory/monitoring only and
  must not be read as evidence for or against the effect.

## 1C — Power analysis

**Method.** One observation per trading day (predictor → last-30-min return), Fisher-z test
of a single correlation. Required N for power `1−β`:
`N = ((z_{1−α/2} + z_{1−β}) / atanh(r))² + 3`. Power at given N:
`Φ(atanh(r)·√(N−3) − z_{1−α/2})`.

**Effect sizes (literature, Step 2 citations).** Canonical in-sample R² ≈ 1.6% → **|corr| ≈
0.13** (Gao et al. 2018; Baltussen et al. 2021 treat rest-of-day as at least as strong). This
is the *unconditional, full-volume, long-history* magnitude — the only figure the canonical
papers pin down precisely.

**Required sample (80% power):**

| Alpha | Required trading days (r = 0.13) |
|---|---|
| Bonferroni per-test (0.00714) | **733** |
| Uncorrected (0.05) | 462 |

**Available series, classified:**

| Instrument / series | N (days) | Power @ Bonferroni (r=0.13) | Power @ 0.05 | MDE @ Bonferroni, 80% | Class |
|---|---|---|---|---|---|
| SPY SIP (full-vol, 2023–2024) | 502 | **0.59** | 0.83 | r ≈ 0.158 | `underpowered` |
| SPY IEX (thin, 2024–2026) | 499 | **0.59** | 0.83 | r ≈ 0.158 | `underpowered` |
| QQQ/IWM/DIA (fetchable) | ≤ ~500 (same feed limits) | ~0.59 | ~0.83 | ~0.158 | `underpowered` |
| ES/MES/NQ/MNQ (primary) | **0 (absent, unfetchable)** | — | — | — | **unavailable** |
| SIP+IEX spliced union | ~861 | 0.87 | — | — | **disqualified** (mixes feeds; fidelity violation) |

- The MDE (minimum detectable effect at 80% power, Bonferroni) for the ~500-day SPY series is
  **r ≈ 0.16**, i.e. ~1.2× the canonical 0.13 — so even the best available series can only
  reliably detect an effect *larger* than the one documented. (Prior analysis put the M126
  MDE at ~3× canonical; the focused single-correlation framing here is better but still short.)

**High-volatility-conditioned primary test (Gao concentration).** A high-vol subsample is
~1/3 of days (~167). The conditioning *raises* the per-test effect size, which can offset the
smaller N — but **only if** the conditioned correlation is large:

| Assumed conditioned r | Power @ Bonferroni (N≈167) | Required N |
|---|---|---|
| 0.20 | 0.46 | 306 |
| 0.25 | 0.72 | 194 |
| **0.30** | **0.90** | 133 |
| 0.35 | 0.98 | 96 |

The conditioned test reaches ≥80% power only at r ≳ 0.30 (≈2.3× the unconditional 0.13). **The
canonical papers do not document a precise conditioned correlation** — they report the effect
is "stronger" on high-vol days, not "r ≈ 0.30." Classifying this test `adequately_powered`
would require *assuming* an undocumented magnitude, which the mission forbids (and which the
quality standard's "not aimed at the weakest/most-favorable specification" rule warns against).
It is therefore classified `underpowered/indeterminate`, not confirmatory-eligible.

## 1D — Blocking condition (BLOCKING)

**All instruments eligible for confirmatory testing are `underpowered`** at the documented
canonical effect size (corr 0.13) and the pre-registered Bonferroni alpha:

- SPY (both feeds) and any Alpaca-fetchable ETF: ~59% power — below the 0.80 threshold.
- The conditioned high-vol test is adequately powered only under an undocumented effect-size
  assumption → cannot be counted as confirmatory.
- The mission's **primary instrument (ES/MES)** and the **futures evidence base for H_b** are
  **absent and unfetchable** with current tooling — the design cannot even be instantiated at
  its intended primary.

→ **STOP. Do not implement M127.** See `m127_blocker_report.md` for the required data and the
recommended next action. **Go/No-Go: NO-GO.**
