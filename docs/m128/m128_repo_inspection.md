# M128 — Repo Inspection (Step 0)

**Milestone:** M128 (cross-sectional intraday periodicity — Heston-Korajczyk-Sadka 2010, JF)
**Branch:** `milestone/M128` (worktree off `milestone/M127`)
**Date:** 2026-06-16
**Author:** Build Master, replication-engineer mode

Goal of this pass: map existing capabilities so M128 *extends* the M127 harness rather
than reinventing it. M128 is the cross-sectional analogue of M127's single-instrument MIM
null; the statistical machinery (HAC inference, seeded negative controls, preregistration
discipline, cost model, artifact conventions) is reused verbatim where possible.

## Existing capabilities (reusable)

| Component | Path | Reuse in M128 |
|---|---|---|
| HAC / Newey-West bivariate OLS | `src/spy_edge_research/backtesting/mim_regression.py` → `newey_west_t(y, x, lags=None)` | **Reused directly** for the time-series inference on the Fama-MacBeth slope series (NW lag = 12 per prereg, overriding the auto rule). Returns `beta, hac_se, t_stat, r_squared, n, nw_lags`. |
| Result dataclass + `as_dict()` | `mim_regression.py` → `MimRegressionResult` | Pattern copied for `FamaMacBethResult`. |
| Negative-controls template | `mim_regression.py` → `negative_controls(...)` (date_shuffled / permuted_target / randomized_timestamps / lag_permuted, seeded) | Adapted to cross-sectional controls (date-shuffled, stock-permuted, lag-permuted) per the M128 prompt. |
| Deflated Sharpe / PBO | `backtesting/deflated_sharpe.py` | Available for the economic-significance layer (not the confirmatory gate). |
| Multiple testing | `backtesting/multiple_testing.py` (Bonferroni/BH-FDR) | Bonferroni α/k for k pre-registered trials. |
| Cost model | `simulation/cost_model.py` → `RegimeAwareCostModel.cost_bps(...)` | Reused for the pre-result cost gate (Step 1E) and the post-result economic-significance report (Step 4). Formula: `half_spread·tod·regime + k·σ_bps + impact·√(Q/ADV)`. |
| Session buckets | `backtesting/time_of_day.py` → `assign_intraday_session_bucket()` | Maps a 30-min bar to a session bucket for the cost model. |
| Bars loader / schema | `market_data/loaders.py` → `load_ohlcv_csv(path, symbol, timezone)`; `validate_ohlcv_schema`; `filter_regular_session` | Reused for per-stock 30-min RTH bar loading. |
| Resampling | `market_data/resampling.py` → `resample_ohlcv(df, rule)` | Not needed if we fetch native `30Min`; available as fallback. |
| Multi-symbol alignment | `market_data/multi_symbol_alignment.py` | Reference for building the cross-sectional panel. |
| Single-symbol fetcher | `scripts/fetch_spy_bars.py` (stdlib-only; `iter_bars`, paginated, SIP/IEX) | Pattern extended to multi-symbol stock fetch. |

**Test conventions:** `tests/` mirrors `src/`; pytest config in `pyproject.toml`
(`testpaths=["tests"]`, `pythonpath=["src"]`, `-ra --strict-markers`). Tests use pure
synthetic fixtures (freeze-compliant — no real predictor→target relationships in tests),
seed-deterministic, asserting mathematical properties (slope recovery, control nullification).

**Artifact conventions:** results written as paired `docs/mNNN/mNNN_results.{md,json}`; JSON
carries `run_utc`, inputs, per-test rows with `t_stat/beta/r_squared/n`, negative-control
block, `suspicious` flag, and a `summary.verdict`. M128 mirrors this exactly.

## What M128 must add

1. **No-lookahead universe construction** — Alpaca asset roster (active ∪ inactive us_equity)
   → trailing-12m ADV liquidity filter, monthly rebalance, dated membership CSV.
   New scripts: `m128_fetch_roster.py`, `m128_scan_daily_volume.py`, `m128_build_universe.py`.
2. **Multi-stock 30-min bar pipeline** — `m128_fetch_universe_bars.py` (multi-symbol SIP 30Min).
3. **Same-clock-bucket return panel** — per stock, per 30-min RTH bucket, aligned across days
   (implements scaffold `build_same_clock_time_returns`).
4. **Market neutralization** — cross-sectional demeaning per date-bucket (implements scaffold
   `market_neutralize_returns`).
5. **Fama-MacBeth cross-sectional regression harness** — per date-bucket cross-sectional OLS of
   today's bucket return on the same-bucket return L days ago; time-series of slopes → NW(12)
   t-stat (implements scaffold `cross_sectional_continuation_test`). New module:
   `signal_engine/cross_sectional.py` (implements the `cross_sectional_scaffold.py` stubs).
6. **Cross-sectional negative controls** (date-shuffled, stock-permuted, lag-permuted), seeded.
7. **Cost-adjusted economic significance** for a decile long/short, using `RegimeAwareCostModel`.
8. **Passing tests** for the FM harness and universe construction.

## Data adequacy (probe result — see `m128_data_inventory.md`)

`scripts/m128_probe_alpaca.py` confirmed (2026-06-16): Alpaca SIP serves 30-min bars for
arbitrary individual stocks back to Jan 2016, **and retains bars for delisted symbols**
(TWTR, ATVI, XLNX, CELG, WORK, DISCA all returned bars during their active life). The assets
endpoint exposes 13,824 active + 19,256 inactive us_equity. This makes a
survivorship-*controlled* universe constructible → M128 is **not** data-blocked. Residual gap:
the inactive roster is incomplete (a few purged tickers like TWTR/ATVI have fetchable bars but
are absent from the asset registry); quantified and disclosed in the data inventory and
fidelity report.
