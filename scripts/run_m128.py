#!/usr/bin/env python3
"""M128 — run the preregistered cross-sectional HKS continuation test (POST-FREEZE).

Requires (committed BEFORE this runs): data inventory, power report, M128_PREREG.yaml,
fidelity report. Loads the no-lookahead universe membership + 30-min bars, builds the
bucket-return panel and member mask, runs the Fama-MacBeth test at each pre-registered lag,
the seeded negative controls, an ETF auxiliary control, the OOS sign-consistency split, and
the cost-adjusted economic-significance layer. Writes docs/m128/m128_results.{md,json}.

Research diagnostic; authorizes nothing.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from spy_edge_research.signal_engine.cross_sectional import (
    BUCKET_STARTS,
    N_BUCKETS,
    build_bucket_returns,
    cross_sectional_continuation_test,
    decile_long_short_bucket_returns,
    negative_controls,
)
from spy_edge_research.simulation.cost_model import RegimeAwareCostModel
from spy_edge_research.backtesting.time_of_day import assign_intraday_session_bucket

BASE = Path("data/raw/m128")
BARS_DIR = BASE / "bars30"
OUT_DIR = Path("docs/m128")
LAGS = [1, 5, 10, 22]
PRIMARY, CO_PRIMARY = 5, 1
CRIT_T = 2.498
CONTROL_ETFS = ["SPY", "QQQ", "IWM", "DIA"]
TZ = "America/New_York"


def load_membership():
    memb = pd.read_csv(BASE / "universe_membership.csv")
    by_month = {m: set(g["symbol"]) for m, g in memb.groupby("rebalance_month")}
    return memb, by_month


def load_bars(symbols):
    out = {}
    for s in symbols:
        p = BARS_DIR / f"{s}.csv"
        if not p.exists():
            continue
        df = pd.read_csv(p)
        if len(df):
            out[s] = df
    return out


def build_mask(frames, by_month):
    dates = sorted(set().union(*[set(f.index) for f in frames.values()]))
    cols = sorted(set().union(*[set(f.columns) for f in frames.values()]))
    idx = pd.DatetimeIndex(dates)
    mask = pd.DataFrame(False, index=idx, columns=cols)
    for d in idx:
        members = by_month.get(d.strftime("%Y-%m"))
        if members:
            present = [c for c in cols if c in members]
            mask.loc[d, present] = True
    return mask


def cost_layer(bucket_returns, member_mask, lag):
    """Cost-adjusted economic significance for the decile L/S at one lag."""
    ls = decile_long_short_bucket_returns(bucket_returns, member_mask, lag=lag)
    if ls.empty:
        return None
    gross_mean_bps = float(ls.mean() * 1e4)
    # representative intraday sigma (bps) = cross-bucket std of returns
    all_rets = pd.concat([bucket_returns[b].stack() for b in range(N_BUCKETS)])
    sigma_bps = float(all_rets.std() * 1e4)
    model = RegimeAwareCostModel(base_half_spread_bps=1.0, vol_coef_k=0.05)
    # average one-way cost across buckets (mid-grid session buckets)
    # Use each bucket's END time (start + 30 min) for the session-bucket cost lookup.
    sample_ts = [pd.Timestamp(f"2020-03-02 {h:02d}:{m:02d}:00", tz=TZ) + pd.Timedelta(minutes=30)
                 for (h, m) in BUCKET_STARTS]
    oneway = np.mean([
        model.cost_bps(session_bucket=assign_intraday_session_bucket(ts),
                       sigma_intraday_bps=sigma_bps, volatility_regime="normal")
        for ts in sample_ts
    ])
    oneway = float(oneway)
    roundtrip = 2.0 * oneway              # enter + exit one side
    ls_full_cost = 4.0 * oneway           # long+short, each enter+exit
    return {
        "lag": lag,
        "n_bucket_obs": int(ls.size),
        "gross_ls_mean_bps_per_bucket": round(gross_mean_bps, 4),
        "sigma_intraday_bps": round(sigma_bps, 2),
        "oneway_cost_bps": round(oneway, 3),
        "roundtrip_cost_bps": round(roundtrip, 3),
        "ls_full_roundtrip_cost_bps": round(ls_full_cost, 3),
        "net_ls_mean_bps_per_bucket": round(gross_mean_bps - ls_full_cost, 4),
        "cost_dominated": bool(gross_mean_bps - ls_full_cost <= 0),
    }


def oos_split(bucket_returns, member_mask, lag):
    """IS 2017-2021 vs OOS 2022-2026 FM slope sign consistency."""
    def sub(frames, lo, hi):
        return {b: f[(f.index >= lo) & (f.index <= hi)] for b, f in frames.items()}
    res = {}
    for name, lo, hi in [("IS_2017_2021", "2017-01-01", "2021-12-31"),
                         ("OOS_2022_2026", "2022-01-01", "2026-12-31")]:
        lo_ts = pd.Timestamp(lo, tz=TZ)
        hi_ts = pd.Timestamp(hi, tz=TZ)
        sf = sub(bucket_returns, lo_ts, hi_ts)
        sm = member_mask[(member_mask.index >= lo_ts) & (member_mask.index <= hi_ts)]
        r = cross_sectional_continuation_test(sf, sm, lag=lag, label=name)
        res[name] = r.as_dict()
    return res


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    memb, by_month = load_membership()
    universe_syms = sorted(set(memb["symbol"]))
    bars = load_bars(universe_syms)
    print(f"Loaded bars for {len(bars)}/{len(universe_syms)} universe symbols.")
    frames = build_bucket_returns(bars)
    mask = build_mask(frames, by_month)

    # Confirmatory tests
    confirmatory = []
    for lag in LAGS:
        r = cross_sectional_continuation_test(frames, mask, lag=lag,
                                              label=f"H_cs L={lag}")
        d = r.as_dict()
        d["passed_confirmatory"] = bool(r.t_stat is not None and r.t_stat > CRIT_T)
        d["role"] = ("PRIMARY" if lag == PRIMARY else
                     "CO_PRIMARY" if lag == CO_PRIMARY else "SECONDARY")
        confirmatory.append(d)
        print(f"L={lag:2d} slope={r.mean_slope:+.5f} t={r.t_stat:+.3f} "
              f"corr={r.mean_cs_corr:+.4f} n_days={r.n_days}")

    # Negative controls for primary + co-primary
    controls = {}
    suspicious = False
    for lag in (PRIMARY, CO_PRIMARY):
        c = negative_controls(frames, mask, lag=lag, seed=42)
        controls[f"L={lag}"] = {k: v.as_dict() for k, v in c.items()}
        for k, v in c.items():
            if v.t_stat is not None and abs(v.t_stat) >= CRIT_T:
                suspicious = True

    # ETF auxiliary control (4-name cross-section; expected weak/absent)
    etf_bars = load_bars(CONTROL_ETFS)
    etf_frames = build_bucket_returns(etf_bars)
    etf_mask = pd.DataFrame(True, index=sorted(set().union(*[set(f.index) for f in etf_frames.values()])),
                            columns=CONTROL_ETFS)
    etf_ctrl = cross_sectional_continuation_test(etf_frames, etf_mask, lag=PRIMARY,
                                                 label="ETF_cross_section").as_dict()
    etf_ctrl["caveat_small_N"] = f"only {len(etf_bars)} ETFs; cross-section too small for power"

    # OOS sign-consistency for primary + co-primary
    oos = {f"L={lag}": oos_split(frames, mask, lag) for lag in (PRIMARY, CO_PRIMARY)}

    # Cost-adjusted economic significance for primary + co-primary
    economics = {f"L={lag}": cost_layer(frames, mask, lag) for lag in (PRIMARY, CO_PRIMARY)}

    primary = next(c for c in confirmatory if c["lag"] == PRIMARY)
    co_primary = next(c for c in confirmatory if c["lag"] == CO_PRIMARY)
    n_passed = sum(1 for c in confirmatory if c["passed_confirmatory"])
    if suspicious:
        verdict = "SUSPICIOUS_STOP"
    elif primary["passed_confirmatory"] or co_primary["passed_confirmatory"]:
        verdict = "REPLICATION_SUPPORTED_EXPLORATORY"
    else:
        verdict = "NULL_NON_REPLICATION"

    result = {
        "run_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "classification": "EXPLORATORY (universe fidelity Approximate; see m128_fidelity_report.md)",
        "crit_t": CRIT_T,
        "k": len(LAGS),
        "n_universe_symbols_with_bars": len(bars),
        "confirmatory": confirmatory,
        "negative_controls": controls,
        "etf_auxiliary_control": etf_ctrl,
        "oos_sign_consistency": oos,
        "economics_cost_gate": economics,
        "suspicious": suspicious,
        "summary": {
            "confirmatory_passed": n_passed,
            "confirmatory_total": len(LAGS),
            "verdict": verdict,
        },
    }
    (OUT_DIR / "m128_results.json").write_text(json.dumps(result, indent=2))
    print(f"\nVERDICT: {verdict}  ({n_passed}/{len(LAGS)} lags passed)")
    print(f"Wrote {OUT_DIR/'m128_results.json'}")


if __name__ == "__main__":
    main()
