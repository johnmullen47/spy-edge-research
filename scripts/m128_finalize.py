#!/usr/bin/env python3
"""M128 finalize — render docs/m128/m128_results.md from m128_results.json.

Verdict-adaptive narrative + tables (confirmatory, negative controls, ETF control, OOS,
economics). Run after run_m128.py. Research diagnostic; authorizes nothing.
"""
from __future__ import annotations

import json
from pathlib import Path

OUT = Path("docs/m128")


def f(x, p=4):
    return "n/a" if x is None else f"{x:.{p}f}"


def main() -> None:
    r = json.loads((OUT / "m128_results.json").read_text())
    s = r["summary"]
    verdict = s["verdict"]
    L = []
    L.append("# M128 — Results: Cross-Sectional Intraday Periodicity (HKS 2010)\n")
    L.append(f"**Run:** {r['run_utc']}  •  **Test window:** {r.get('test_window','')}  ")
    L.append(f"**Classification:** {r['classification']}  ")
    L.append(f"**Universe symbols with bars:** {r['n_universe_symbols_with_bars']}  •  "
             f"**k:** {r['k']}  •  **Bonferroni crit t:** {r['crit_t']}\n")
    L.append(f"## Verdict: **{verdict}**  ({s['confirmatory_passed']}/{s['confirmatory_total']} lags passed)\n")

    L.append("## Confirmatory Fama-MacBeth tests (all-buckets-pooled, NW(12))\n")
    L.append("| Lag | Role | slope | HAC t | mean CS corr | n_days | n_obs | pass |")
    L.append("|----:|------|------:|------:|-------------:|-------:|------:|:---:|")
    for c in r["confirmatory"]:
        L.append(f"| {c['lag']} | {c['role']} | {f(c['mean_slope'],5)} | {f(c['t_stat'],3)} | "
                 f"{f(c['mean_cs_corr'])} | {c['n_days']} | {c['n_obs_total']} | "
                 f"{'YES' if c['passed_confirmatory'] else 'no'} |")
    L.append("")

    L.append("## Negative controls (seed=42; pass = all |t| << real, none significant)\n")
    for lag_key, ctrls in r["negative_controls"].items():
        L.append(f"**{lag_key}**\n")
        L.append("| control | t | slope |")
        L.append("|---------|--:|------:|")
        for name, v in ctrls.items():
            L.append(f"| {name} | {f(v['t_stat'],3)} | {f(v['mean_slope'],5)} |")
        L.append("")
    L.append(f"Suspicious-control flag: **{r['suspicious']}**\n")

    etf = r["etf_auxiliary_control"]
    L.append("## ETF auxiliary control (diversified ETFs → effect should be weak/absent)\n")
    L.append(f"- ETF cross-section L={etf['lag']}: t={f(etf['t_stat'],3)}, slope={f(etf['mean_slope'],5)}, "
             f"n_days={etf['n_days']}. {etf.get('caveat_small_N','')}\n")

    L.append("## Out-of-sample sign consistency\n")
    for lag_key, splits in r["oos_sign_consistency"].items():
        parts = [f"{name}: slope={f(v['mean_slope'],5)} (t={f(v['t_stat'],2)}, n={v['n_days']})"
                 for name, v in splits.items()]
        L.append(f"- **{lag_key}** — " + "; ".join(parts))
    L.append("")

    L.append("## Cost-adjusted economic significance (decile L/S, 30-min holding)\n")
    L.append("| Lag | gross bps/bucket | one-way bps | L/S round-trip bps | net bps/bucket | cost-dominated |")
    L.append("|----:|-----------------:|------------:|-------------------:|---------------:|:--------------:|")
    for lag_key, e in r["economics_cost_gate"].items():
        if not e:
            continue
        L.append(f"| {e['lag']} | {f(e['gross_ls_mean_bps_per_bucket'])} | {f(e['oneway_cost_bps'],3)} | "
                 f"{f(e['ls_full_roundtrip_cost_bps'],3)} | {f(e['net_ls_mean_bps_per_bucket'])} | "
                 f"{'YES' if e['cost_dominated'] else 'no'} |")
    L.append("")

    # Interpretation
    L.append("## Interpretation\n")
    if verdict == "NULL_NON_REPLICATION":
        L.append(
            "No pre-registered lag's market-neutralized same-half-hour continuation slope exceeded "
            "the Bonferroni critical t (+2.498) in the liquid US-stock cross-section, 2023–2026. "
            "Per the preregistration this is an interpretable null, not dismissible as: underpowered "
            "(synthetic MC power ≈1.0 at literature R²; MDE ρ≈0.004 ≈8× below the literature lower "
            "bound), contaminated (negative controls clean), undisciplined (preregistered, k=4 "
            "Bonferroni), survivorship-inflated (delisted bars retained; relative demeaned "
            "estimator), or aimed at the weakest spec (L=1 — HKS's strongest documented horizon — "
            "is co-primary). It is EXPLORATORY w.r.t. HKS's original CRSP universe (fidelity "
            "Approximate; liquidity proxy, modern post-publication era). Consistent with the M127 "
            "single-instrument MIM null and with post-publication decay (McLean-Pontiff 2016)."
        )
    elif verdict == "SUSPICIOUS_STOP":
        L.append(
            "A negative control reached the Bonferroni critical t — the pipeline is flagged "
            "SUSPICIOUS_STOP. The confirmatory result must NOT be interpreted as evidence until the "
            "contamination is diagnosed and resolved. Do not advance."
        )
    else:
        L.append(
            "At least one pre-registered lag (incl. the L=5 primary or L=1 co-primary) exceeded the "
            "Bonferroni critical t with clean negative controls — the HKS same-half-hour continuation "
            "is statistically SUPPORTED in the liquid US-stock cross-section 2023–2026. This is "
            "EXPLORATORY (universe fidelity Approximate, not point-in-time CRSP). Economic viability "
            "is governed separately by the cost gate above: if the decile L/S is cost-dominated, the "
            "finding is STATISTICALLY_SIGNIFICANT_BUT_NOT_ECONOMICALLY_VIABLE."
        )
    L.append("")
    L.append("## Provenance\n")
    L.append("- Preregistration: `docs/preregistration/M128_PREREG.yaml` + `M128_PREREG_v2.yaml` "
             "(both committed before any result; results_observed=false).")
    L.append("- Power: `m128_power_report.md` / `m128_power_sim.json`. Fidelity: `m128_fidelity_report.md`.")
    L.append("- Data: `m128_data_inventory.md`; universe `universe_membership.csv`.")
    L.append("- Estimator: `src/spy_edge_research/signal_engine/cross_sectional.py`; runner `scripts/run_m128.py`.")
    L.append("- Result JSON: `docs/m128/m128_results.json`.\n")

    (OUT / "m128_results.md").write_text("\n".join(L))
    print(f"Wrote {OUT/'m128_results.md'} (verdict={verdict})")


if __name__ == "__main__":
    main()
