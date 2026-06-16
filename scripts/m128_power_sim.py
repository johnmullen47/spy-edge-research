#!/usr/bin/env python3
"""M128 Gate 0.5 — power simulation (SYNTHETIC; freeze-compliant).

Monte-Carlo power for the cross-sectional Fama-MacBeth same-bucket continuation test.
Generates synthetic balanced panels (D days x B buckets x S stocks) with a planted
same-bucket lag-L cross-sectional correlation rho, runs the SAME estimator used in the
real test (cross-sectional demean -> pooled per-date slope -> NW(12) mean t-stat), and
reports empirical power at the Bonferroni critical t, the null false-positive rate, the
realized std of the daily slope, and the minimum detectable effect (MDE).

No real market data touched. Writes docs/m128/m128_power_sim.json. Numpy only.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

# Match the real design.
N_STOCKS = 150
N_BUCKETS = 13
N_DAYS = 2350          # ~9.4 trading years (2017-01 .. 2026-06); realized N reported at run
NW_LAGS = 12
CRIT_T = 2.498         # Bonferroni two-sided, alpha=0.05/k, k=4
LAGS = [1, 5, 10, 22]
# Literature cross-sectional R^2 0.1-0.3% per half-hour (HKS 2010) -> rho = sqrt(R^2).
RHO_GRID = [0.0, 0.02, 0.0316, 0.0447, 0.0548]   # incl. null(0.0) and R^2=.1/.2/.3%
REPS = 120          # ample for power estimates (SE ~ 0.03 at p=0.9); effect is ~1.0 at lit rho
MDE_REPS = 80


def nw_t_mean(g: np.ndarray, lags: int = NW_LAGS) -> float:
    g = g[~np.isnan(g)]
    n = g.size
    if n < 3:
        return float("nan")
    e = g - g.mean()
    gamma0 = np.dot(e, e) / n
    lrv = gamma0
    m = min(lags, n - 1)
    for l in range(1, m + 1):
        w = 1.0 - l / (m + 1)
        lrv += 2.0 * w * np.dot(e[l:], e[:-l]) / n
    lrv = max(lrv, 0.0)
    se = np.sqrt(lrv / n)
    return float(g.mean() / se) if se > 0 else float("nan")


def simulate_once(rho: float, lag: int, rng: np.random.Generator):
    """One synthetic panel; returns (t_stat, std_gamma, mean_gamma).

    Vectorized generator: for rho<=0.055, the AR(lag) process x[d]=rho*x[d-lag]+c*eps[d]
    is reproduced to machine-negligible error by its truncated MA form
    x[d] = c*(eps[d] + rho*eps[d-lag] + rho^2*eps[d-2lag] + rho^3*eps[d-3lag]),
    since rho^4 <= 9e-6. This yields the same same-bucket lag-L cross-sectional corr ~ rho
    and ~0 at non-multiple lags, and runs instantly.
    """
    eps = rng.standard_normal((N_DAYS, N_BUCKETS, N_STOCKS), dtype=np.float32)
    c = np.sqrt(max(1 - rho**2, 0.0))
    arr = eps.copy()
    coef = rho
    for k in range(1, 4):
        shifted = np.zeros_like(eps)
        shifted[k * lag:] = eps[: N_DAYS - k * lag]
        arr += coef * shifted
        coef *= rho
    arr *= c
    # Cross-sectional demean per (day, bucket) over stocks (market neutralization).
    ad = arr - arr.mean(axis=2, keepdims=True)
    X = ad[:-lag]      # predictor = lagged
    Y = ad[lag:]       # target = today
    num = (X * Y).sum(axis=(1, 2))
    den = (X * X).sum(axis=(1, 2))
    g = num / den
    return nw_t_mean(g), float(np.std(g)), float(np.mean(g))


def power_for(rho: float, lag: int, reps: int, seed: int):
    rng = np.random.default_rng(seed)
    ts, stds, means = [], [], []
    for _ in range(reps):
        t, s, m = simulate_once(rho, lag, rng)
        ts.append(t)
        stds.append(s)
        means.append(m)
    ts = np.array(ts)
    return {
        "rho": rho,
        "implied_R2_pct": round(100 * rho**2, 4),
        "power_at_crit": float(np.mean(np.abs(ts) > CRIT_T)),
        "median_t": float(np.median(ts)),
        "mean_realized_slope": float(np.mean(means)),
        "mean_std_daily_slope": float(np.mean(stds)),
    }


def main() -> None:
    out_path = Path("docs/m128/m128_power_sim.json")
    result = {
        "config": {
            "n_stocks": N_STOCKS, "n_buckets": N_BUCKETS, "n_days": N_DAYS,
            "nw_lags": NW_LAGS, "crit_t": CRIT_T, "reps": REPS,
            "rho_grid": RHO_GRID, "lags": LAGS,
        },
        "by_lag": {},
    }
    for lag in LAGS:
        rows = []
        for i, rho in enumerate(RHO_GRID):
            rows.append(power_for(rho, lag, REPS, seed=1000 * lag + i))
            print(f"lag={lag} rho={rho:.4f} power={rows[-1]['power_at_crit']:.3f} "
                  f"med_t={rows[-1]['median_t']:.2f}", file=sys.stderr, flush=True)
        result["by_lag"][lag] = rows

    # MDE: smallest rho with >=0.80 power at lag=5 (primary), fine grid.
    rng_grid = np.round(np.arange(0.004, 0.030, 0.002), 4)
    mde = None
    for rho in rng_grid:
        p = power_for(float(rho), 5, MDE_REPS, seed=7)["power_at_crit"]
        print(f"MDE scan lag=5 rho={rho:.4f} power={p:.3f}", file=sys.stderr, flush=True)
        if p >= 0.80:
            mde = float(rho)
            break
    result["mde_rho_lag5_80pct"] = mde
    result["mde_R2_pct_lag5"] = round(100 * mde**2, 5) if mde else None

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, indent=2))
    print(json.dumps({"mde_rho_lag5_80pct": mde, "by_lag_keys": list(result["by_lag"])}, indent=2))


if __name__ == "__main__":
    main()
