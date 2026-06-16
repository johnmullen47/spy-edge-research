# Hard Gate A Results — M126 (full F1–F10 candidate set)

**Run:** `reports/run_20260616T040858Z` (gitignored; this file is the durable record).
**Date:** 2026-06-16 · **Data:** IEX SPY 1-min, 189,663 bars + CBOE daily VIX.
**Driver:** `scripts/run_hard_gate_a.py` with all families enabled (MIM, F2, MIM-Baltussen,
F3, F4, F5, F6, F7, F8, F9, F10) + the M124 effective-N fix.

## Headline

**0 of 672 candidates reached `eligible_for_paper_consideration`.** No validated edge.
Broker/live layers stay OFF. A valid, honestly-recorded null across every pre-registered
family in all five mechanism buckets (RESEARCH_I).

## Portfolio metrics

| Metric | Value | Note |
|---|---|---|
| Event columns | 214 | 154 (M122) + 60 (F6–F10) |
| Candidate registry | 672 | 600 (M122) + 72 (F6–F10), per-family horizon-scoped |
| **Effective-N (clusters)** | **318** | M124 fix validated on real data — non-degenerate (was the spurious 600=total at M122) |
| Within-cluster Holm survivors | 38 | none cleared the full gate |
| Portfolio PBO | 0.0959 | ≤ 0.50 |
| Eligible | **0 / 672** | — |

## Per-family verdicts (all `not_ready`)

| Family | Candidates | Eligible | Bucket (RESEARCH_I) |
|---|---|---|---|
| MIM-Baltussen | 256 | 0 | behavioral/structural |
| chart / named events | 84 | 0 | (legacy chart patterns) |
| F4 — overnight gap | 72 | 0 | behavioral |
| F3 — VIX gate | 72 | 0 | behavioral/structural |
| MIM (original) | 48 | 0 | behavioral |
| F5 — FOMC eve (placebo) | 48 | 0 | macro/calendar |
| F9 — intraday periodicity | 20 | 0 | microstructure/rebalancing |
| F2 — EOD reversal | 20 | 0 | microstructure |
| F8 — opening range breakout | 18 | 0 | structural/intraday |
| F10 — FOMC cycle | 12 | 0 | macro/calendar |
| F6 — variance risk premium | 12 | 0 | risk premia |
| F7 — vol-managed | 10 | 0 | risk management |

The 72 new F6–F10 candidates entered at exactly their scoped outcome horizons (F6 6
columns × {5,21}-session; F7 ≈ 6 × {1,5}-session; F8 18 × to-close; F9 ≈ 24 × 30m; F10 6
× {1,5}-session — minor shortfalls where a sparse variant produced no OOS panel). The
per-family scoping held on real data: the multi-session/to-close labels did **not**
cross-expand the 600 intraday candidates.

## Interpretation

- **The M124 effective-N fix is confirmed on real data.** Effective-N = 318 (of 671
  trial candidates) — meaningful clustering, neither the degenerate ceiling (600=total
  at M122) nor the floor. The DSR deflation is now estimated on a defensible trial count.
- **Every new mechanism bucket is null on this sample**, including the stronger-prior
  F10 (FOMC cycle) and F6 (VRP). Consistent with RESEARCH_I's honest expectation: none
  was a high-probability winner, and F7/F8/F9 were pre-registered as likely-fail
  adjudications. The ~2-year IEX sample is also power-limited for the daily/weekly
  families (few independent cycles / holding periods), as F6/F10 flagged.
- This did **not** lower or bypass the gate; thresholds (DSR ≥ 0.95, PBO ≤ 0.50, net-cost
  floor) are unchanged. SPA/Hansen remains deferred (report-only).

**Conclusion:** the project's directional-edge search now spans all five durable
mechanism buckets, evaluated under the full anti-snooping harness with a corrected
effective-N, and finds **no validated intraday/daily edge in SPY**. The broker layers
remain OFF — the designed, desirable outcome.
