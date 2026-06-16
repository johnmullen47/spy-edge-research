# M128 — Power Report & Cost Gate (Gate 0.5, Steps 1D–1F)

**Date:** 2026-06-16. Written BEFORE any real-data cross-sectional result. All power numbers
come from a SYNTHETIC Monte-Carlo (`scripts/m128_power_sim.py` → `m128_power_sim.json`); no real
predictor→target relationship was touched.

## 1. Design recap

- Estimator: Fama-MacBeth per-date pooled cross-sectional slope γ[d] (all 13 buckets pooled,
  market-neutralized), NW(12) HAC t-stat on the mean.
- Universe: 150 stocks; ~2,350 trading days (2017-01 .. 2026-06); 13 buckets.
- k = 4 pre-registered lags {1,5,10,22}; Bonferroni α/k = 0.0125; two-sided crit t = **2.498**.
- Literature effect: HKS cross-sectional R² ≈ 0.1–0.3% per half-hour → ρ ≈ 0.032–0.055.

## 2. Analytical MDE (sanity frame)

For an iid daily-slope series, FM t = μ / (s/√T) with μ = mean slope, s = day-to-day slope std,
T ≈ 2,350. 80%-power MDE: μ* = (z\* + 0.84)·s/√T = (2.498 + 0.84)·s/48.5 = 0.0688·s. The synthetic
MC measures s directly (mean std of daily slope) ≈ O(1/√(N_stocks·N_buckets)) for demeaned unit-
variance returns ≈ 1/√(150·13) ≈ 0.0227, with mild inflation from pooling. Even at s ≈ 0.05 the
MDE μ* ≈ 0.0034 — an order of magnitude below the literature slope (ρ ≈ 0.032–0.055). The design
is therefore expected to be **comfortably powered** for the HKS effect at published magnitude;
the MC below confirms this and supplies the authoritative numbers.

<!-- POWER_SIM_START -->
## 3. Monte-Carlo power (authoritative — `m128_power_sim.json`)

150 stocks × 13 buckets × 2,350 days; NW(12); crit t = 2.498; 120 reps/cell. Power = fraction of
reps with |t| > 2.498.

| Effect (ρ) | R² | Power L=1 | Power L=5 | Power L=10 | Power L=22 | median t (L=5) |
|---|---|---|---|---|---|---|
| 0.0000 (null) | 0.000% | 0.008 | 0.025 | 0.000 | 0.025 | −0.06 |
| 0.0200 | 0.040% | 1.000 | 1.000 | 1.000 | 1.000 | 42.6 |
| **0.0316** | **0.100%** *(lit. low)* | **1.000** | **1.000** | **1.000** | **1.000** | **67.3** |
| 0.0447 | 0.200% *(lit. mid)* | 1.000 | 1.000 | 1.000 | 1.000 | 95.6 |
| 0.0548 | 0.300% *(lit. high)* | 1.000 | 1.000 | 1.000 | 1.000 | 117.2 |

- **Power = 1.000 at every literature effect size, for all four lags.** Median t-stats of 67–118
  at literature magnitude — far above the 2.498 bar.
- **Null calibration:** at ρ=0 the rejection rate is 0.0–2.5%, consistent with the nominal
  two-sided α/k = 1.25% (MC noise at 120 reps). The test is well-sized.
- **Realized daily-slope std** ≈ 0.0227, matching the analytical iid baseline 1/√(150·13)=0.0227.
- **MDE (lag 5, ≥80% power):** ρ ≈ **0.004** (R² ≈ 0.0016%) — roughly **8× smaller** than the
  literature lower bound. Enormous headroom.

**Modeling caveat (honest):** the MC assumes cross-sectionally iid demeaned returns. Real
market-neutralized 30-min returns retain residual sector/factor commonality, which would inflate
std(γ) above 0.0227 and reduce power. But with an MDE ~8× below the literature effect, even a
5–10× inflation of std(γ) leaves power ≈ 1.0 at published magnitude. The **realized** std(γ) is
reported alongside the result (`m128_results.json`); if it were implausibly large the power claim
would be revisited there.
<!-- POWER_SIM_END -->

## 4. Classification per test (Step 1D)

Each pre-registered lag is classified `adequately_powered` if empirical power ≥ 0.80 at the
**lower-bound** literature effect (R² = 0.1%, ρ ≈ 0.0316). The MC result (Section 3) drives this
classification; see the go/no-go in Section 6.

## 5. Cost gate (Step 1E — PRE-RESULT)

The confirmatory test is a **cost-free** predictive-slope claim (per M127 precedent); costs gate
only *economic tradeability*, computed here before any result is seen.

- Model: `RegimeAwareCostModel` (`half_spread·tod·regime + k·σ_bps + impact·√(Q/ADV)`),
  `base_half_spread_bps = 1.0`, `vol_coef_k = 0.05`, normal vol regime, liquid large-cap.
- Strategy costed: decile long/short on the lagged same-bucket neutralized return, **30-min
  holding** (one bucket), rebalanced every bucket — i.e. ~13 round trips/day, ~3,250/year. This
  is *extremely* high turnover.
- Gross edge at literature effect: the decile L/S spread per bucket ≈ a small multiple of
  ρ·σ_bucket. With ρ ≈ 0.04 and a half-hour σ ≈ 40–80 bps, the gross decile spread is on the
  order of a few bps per bucket.
- One-way cost for liquid large caps is ≈ 1–3 bps (half-spread + vol term, mid-grid buckets);
  a single L/S round trip pays ≈ 4× one-way (long+short, each enter+exit) ≈ 4–12 bps.

**Pre-result expectation:** at this turnover the round-trip cost (~4–12 bps) is of the same order
as or larger than the gross per-bucket decile spread (~few bps), so the *tradeable* implementation
is likely **cost_dominated**. This does NOT block the scientific test; it means a positive
statistical result would be reported `STATISTICALLY_SIGNIFICANT_BUT_NOT_ECONOMICALLY_VIABLE`
(Step 4). The exact realized gross/net is computed in `m128_results.json` (`economics_cost_gate`).

## 6. Go / No-Go (Step 1F — BLOCKING condition)

Step 1F blocks only if **all** pre-registered tests are underpowered *or* the confirmatory test
itself is cost-gated. Here:

- The confirmatory test is cost-free (predictive slope) — not cost-gated.
- The MC shows the design is adequately powered at literature magnitude (Section 3).

→ **GO** for the confirmatory cross-sectional test. The *economic layer* is separately flagged as
likely cost_dominated (exploratory tradeability), per Section 5. Combined with the fidelity
classification (Approximate → EXPLORATORY), M128 proceeds as a **powered, preregistered,
exploratory** replication. Final go/no-go confirmed against Section 3 numbers below.
