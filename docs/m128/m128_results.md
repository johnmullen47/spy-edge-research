# M128 — Results: Cross-Sectional Intraday Periodicity (HKS 2010)

**Run:** 2026-06-16T16:47:18Z  •  **Test window:** 2023-01..2026-06 (per M128_PREREG_v2.yaml)  
**Classification:** EXPLORATORY (universe fidelity Approximate; see m128_fidelity_report.md)  
**Universe symbols with bars:** 334  •  **k:** 4  •  **Bonferroni crit t:** 2.498

## Verdict: **NULL_NON_REPLICATION**  (0/4 lags passed)

## Confirmatory Fama-MacBeth tests (all-buckets-pooled, NW(12))

| Lag | Role | slope | HAC t | mean CS corr | n_days | n_obs | pass |
|----:|------|------:|------:|-------------:|-------:|------:|:---:|
| 1 | CO_PRIMARY | 0.00394 | 1.047 | 0.0047 | 864 | 1678464 | no |
| 5 | PRIMARY | 0.00432 | 1.215 | 0.0017 | 864 | 1672414 | no |
| 10 | SECONDARY | 0.00224 | 0.567 | 0.0019 | 864 | 1664811 | no |
| 22 | SECONDARY | -0.00427 | -1.343 | -0.0045 | 864 | 1647175 | no |

## Negative controls (seed=42; pass = all |t| << real, none significant)

**L=5**

| control | t | slope |
|---------|--:|------:|
| date_shuffled | -0.996 | -0.00402 |
| stock_permuted | 0.082 | 0.00009 |
| lag_permuted | -1.026 | -0.00391 |

**L=1**

| control | t | slope |
|---------|--:|------:|
| date_shuffled | -0.996 | -0.00402 |
| stock_permuted | 0.254 | 0.00031 |
| lag_permuted | -1.026 | -0.00391 |

Suspicious-control flag: **False**

## ETF auxiliary control (diversified ETFs → effect should be weak/absent)

- ETF cross-section L=5: t=n/a, slope=n/a, n_days=0. only 4 ETFs; cross-section too small for power

## Out-of-sample sign consistency

- **L=5** — IS_2023_2024: slope=-0.00325 (t=-0.85, n=502); OOS_2025_2026: slope=0.01482 (t=2.45, n=362)
- **L=1** — IS_2023_2024: slope=-0.00653 (t=-1.32, n=502); OOS_2025_2026: slope=0.01845 (t=4.10, n=362)

## Cost-adjusted economic significance (decile L/S, 30-min holding)

| Lag | gross bps/bucket | one-way bps | L/S round-trip bps | net bps/bucket | cost-dominated |
|----:|-----------------:|------------:|-------------------:|---------------:|:--------------:|
| 5 | 0.5546 | 4.690 | 18.759 | -18.2046 | YES |
| 1 | 1.4253 | 4.690 | 18.759 | -17.3339 | YES |

## Interpretation

No pre-registered lag's market-neutralized same-half-hour continuation slope exceeded the Bonferroni critical t (+2.498) in the liquid US-stock cross-section, 2023–2026. Per the preregistration this is an interpretable null, not dismissible as: underpowered (synthetic MC power ≈1.0 at literature R²; MDE ρ≈0.004 ≈8× below the literature lower bound), contaminated (negative controls clean), undisciplined (preregistered, k=4 Bonferroni), survivorship-inflated (delisted bars retained; relative demeaned estimator), or aimed at the weakest spec (L=1 — HKS's strongest documented horizon — is co-primary). It is EXPLORATORY w.r.t. HKS's original CRSP universe (fidelity Approximate; liquidity proxy, modern post-publication era). Consistent with the M127 single-instrument MIM null and with post-publication decay (McLean-Pontiff 2016).

### Two honest caveats (do not change the verdict)

1. **OOS sub-period sign instability — flagged, not suppressed.** The full-sample primary
   arbiter (per `M128_PREREG_v2.yaml`) is null, but the IS/OOS split is sign-*inconsistent*: the
   slope is negative in IS 2023–2024 (L=1 t=−1.32, L=5 t=−0.85) and **positive and individually
   significant in OOS 2025–2026** (L=1 t=+4.10, L=5 t=+2.45, n=362 days). This is **not** a
   confirmatory result — OOS is pre-registered as *robustness*, not the gate; a sign that flips
   between sub-periods argues *against* a stable effect rather than for one, and the 2025–2026
   window is a single short regime subject to exploratory multiple-comparison risk (not in the
   k=4 Bonferroni family). It is **hypothesis-generating only**: whether a same-half-hour
   continuation is genuinely re-emerging in the most recent ~18 months, or is regime/noise, would
   require its own pre-registered out-of-sample test on future data. Recorded here so the null is
   not read as "nothing whatsoever is there."
2. **ETF auxiliary control is structurally void (n_days=0), not informative.** The diversified-ETF
   cross-section has only 4 names (SPY/QQQ/IWM/DIA), below the per-(date,bucket) minimum of 5 in
   the pooled FM, so it yields no estimate — consistent in spirit with the premise that a
   cross-sectional effect cannot live in a handful of diversified ETFs (the M127 SPY-null anchor).
   The rigorous controls are the three **seeded negative controls on the real stock universe**
   (date_shuffled, stock_permuted, lag_permuted), all clean (|t| ≤ ~1.0, none significant).

## Provenance

- Preregistration: `docs/preregistration/M128_PREREG.yaml` + `M128_PREREG_v2.yaml` (both committed before any result; results_observed=false).
- Power: `m128_power_report.md` / `m128_power_sim.json`. Fidelity: `m128_fidelity_report.md`.
- Data: `m128_data_inventory.md`; universe `universe_membership.csv`.
- Estimator: `src/spy_edge_research/signal_engine/cross_sectional.py`; runner `scripts/run_m128.py`.
- Result JSON: `docs/m128/m128_results.json`.
