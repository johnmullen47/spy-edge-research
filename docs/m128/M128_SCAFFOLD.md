# M128 Scaffold — Intraday Cross-Sectional Continuation/Reversal (DO NOT RUN)

**Status:** Scaffold only (interfaces + TODOs). No experiments, scans, or alpha search.
**Code:** `src/spy_edge_research/signal_engine/cross_sectional_scaffold.py` (all stubs raise
`NotImplementedError`).

## Why M128 exists

M127 tested MIM on a single instrument (SPY) and found a well-powered null. But the periodicity
/ continuation effects (Heston-Korajczyk-Sadka 2010; RESEARCH_I bucket 3) are **cross-sectional**
— defined *across many stocks*, not within one diversified ETF. M127's ETF null is therefore the
*expected* control outcome for a cross-sectional effect, not a test of it. M128 would test the
effect where it actually lives: the **stock cross-section**.

## Design (to be frozen at M128 — Gate 0.5 first, same discipline as M127)

- **Universe: stocks first** (point-in-time membership; **no survivorship bias**).
- **Predictor/target:** same-clock-time (e.g., 30-min bucket) returns aligned across days,
  per stock; test continuation of a stock's own same-bucket return.
- **Controls (mandatory):**
  - **Market/beta neutralization** before the continuation test (else it is just market
    autocorrelation, not a cross-sectional anomaly).
  - **Liquidity screen** (ADV / price floor), applied point-in-time.
  - **ETFs (SPY/QQQ/…) as NEGATIVE controls** — a true cross-sectional effect should be
    weak/absent on a single diversified ETF (anchored by the M127 SPY null).
- **Same harness as M127:** preregistration freeze → power/MDE → fidelity ≥ Close → negative
  controls → auditable artifacts. Do not start without Gate 0.5 passing on the stock universe.

## Blockers to resolve before M128

1. **Stock-universe intraday data** with point-in-time membership — not in the repo; Alpaca can
   fetch individual stock minute bars (IEX-thin or SIP), but survivorship-correct membership and
   liquidity history must be sourced.
2. A cross-sectional power analysis (effect size, N = stocks × days) — distinct from M127's
   single-series power.

**Until then: scaffold only. No M128 experiments.**
