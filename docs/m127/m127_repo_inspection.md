# m127_repo_inspection

**Milestone:** M127 (literature-faithful MIM replication, ship version)
**Date:** 2026-06-16 · **Branch:** `milestone/M127`
**Purpose:** Step 0 — enumerate existing capabilities, reusable modules, and gaps before Gate 0.5.

## Bottom line

The repository **already contains literature-faithful MIM predictors and a full
anti-snooping evaluation harness.** The implementation for M127 is largely *reuse*, not
new code. The binding constraint is **data**, not architecture (see Gate 0.5 / power
report). Therefore M127's go/no-go is decided entirely by data adequacy.

## Existing capabilities (reusable as-is)

| Capability | Module | Relevance to M127 |
|---|---|---|
| **H_b predictor (rest-of-day → last 30 min)** | `signal_engine/mim_baltussen_features.py` | This **is** the Baltussen rest-of-day MIM predictor (`r_rod` = prior close → 15:30, outcome 15:30→16:00), built causally in M121. Directly reusable for H_b. |
| **H_a-form predictor (early-window momentum)** | `signal_engine/intraday_momentum_features.py` | Open→window-end momentum with regime gate (M110); the Gao first-window family lives here. Reusable/adaptable for H_a. |
| Forward / session / to-close labels | `backtesting/labels.py` | `add_forward_labels`, `add_session_forward_return_labels`, `add_to_close_forward_return_label` (M125) — supply the last-30-min target and multi-horizon outcomes. |
| Candidate registry | `backtesting/candidate_edges.py` | Validated candidate records + registry. |
| Walk-forward OOS | `backtesting/oos_validation.py` | Chronological splits + per-split expectancy panel. |
| Deflated Sharpe / PBO (CSCV) | `backtesting/deflated_sharpe.py` | DSR, PSR, portfolio PBO. |
| Effective-N (ONC clustering) | `backtesting/effective_n.py` | Trial-count correction (M124-fixed: pairwise-complete correlation; non-degenerate). |
| Regime-aware cost model | `simulation/cost_model.py` | `RegimeAwareCostModel` (half-spread + k·σ + sqrt-impact), time-of-day/VIX aware — the close-window cost the MIM literature is sensitive to. |
| Readiness gate | `paper/readiness_scoring.py`, `paper/readiness_inputs.py` | `eligible_for_paper_consideration` verdict. |
| Pipeline orchestration | `cli/pipeline.py` (`run_pipeline`) | Threads features → labels → study → registry → OOS → deflation → controls → readiness. |
| Hard Gate A driver | `scripts/run_hard_gate_a.py` | End-to-end real-data runner. |
| Data loaders | `market_data/loaders.py`, `market_data/vix_loader.py` | OHLCV + daily VIX. |
| Equity bar fetch | `scripts/fetch_spy_bars.py` | Alpaca **stocks** bars (any symbol, `--feed iex/sip`). **No futures.** |
| Negative controls | `backtesting/intraday_momentum_placebos.py`, `cli/control_batteries.py` | Scrambled-gate / random-direction / permutation controls — reusable for Step 3. |

## Missing pieces (relative to a powered, literature-faithful MIM replication)

1. **Multi-instrument intraday data.** No futures (ES/MES/NQ/MNQ) and no QQQ/IWM/DIA
   intraday bars exist in the repo. Only SPY (two feeds). **This is the blocker.**
2. **Futures data acquisition path.** `fetch_spy_bars.py` is Alpaca-stocks-only; there is
   no futures fetcher and Alpaca's free tier does not serve futures. ES/MES long history
   (Baltussen 1974–2020) is unreachable with current tooling.
3. **A literature-faithful *regression* test harness.** The papers report a Newey-West OLS
   of the last-30-min return on the predictor (R²/β/t-stat) and an in-sample correlation.
   The repo evaluates via event-study + edge-gate, not the simple OLS the papers report.
   For a fidelity-≥Close replication a small `mim_regression` harness (OLS + HAC SE +
   correlation + conditioning splits) is the cleanest addition — **but it is pointless to
   build before the data gate passes.**
4. **Power/MDE utility.** Computed ad-hoc here; worth formalizing into
   `backtesting/power.py` once instruments are powered.
5. **Futures session-definition handling** (RTH vs full/Globex) for the first-30/last-30/
   rest-of-day windows — only relevant once futures data is acquired; would need explicit
   pre-registration (flagged as a clarification item rather than silently chosen).

## Recommended additions (deferred until Gate 0.5 passes)

- Acquire long-history intraday **ES/MES** (and/or full-history SPY 1993–) from a futures-
  capable vendor; add a `fetch_futures_bars.py` with explicit roll + session handling.
- Add `backtesting/mim_regression.py` (HAC OLS + correlation + literature conditioning
  splits) for a paper-faithful confirmatory test alongside the existing edge-gate.
- Formalize `backtesting/power.py` (Fisher-z power/MDE) and wire into the pre-registration.

**Conclusion:** architecture is ready; the replication is data-blocked. Proceed to Gate 0.5.
