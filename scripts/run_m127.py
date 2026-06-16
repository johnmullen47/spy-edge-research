#!/usr/bin/env python3
"""Run the preregistered M127 MIM replication (post-freeze; see M127_PREREG.yaml).

Confirmatory tests (k=4, SPY, Bonferroni alpha=0.0125, two-sided crit |t|=2.498):
  1. H_b full sample        3. H_b high-volatility subsample
  2. H_a full sample        4. H_a high-volatility subsample
Plus the 4 seeded negative controls per co-primary predictor (full sample).

Predictive HAC (Newey-West) regression of the last-30-min return on each predictor. The
preregistration (committed before this script produces any result) is the binding design;
this driver only executes it and writes an auditable results artifact.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone

from spy_edge_research.market_data.loaders import load_ohlcv_csv
from spy_edge_research.backtesting.mim_regression import (
    build_mim_daily_frame,
    high_volatility_mask,
    negative_controls,
    run_mim_regression,
)

CRIT = 2.498  # Bonferroni two-sided crit z at alpha_per_test = 0.0125 (k=4)
TESTS = [
    ("H_b full sample", "r_hb", None),
    ("H_a full sample", "r_ha", None),
    ("H_b high-volatility subsample", "r_hb", "highvol"),
    ("H_a high-volatility subsample", "r_ha", "highvol"),
]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", default="data/raw/spy_sip_2016_2026.csv")
    ap.add_argument("--output", default="docs/m127/m127_results.json")
    args = ap.parse_args()

    df = load_ohlcv_csv(args.input)
    frame = build_mim_daily_frame(df)
    hv = high_volatility_mask(frame)

    results = {"run_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
               "input": args.input, "N_full": int(len(frame)), "N_highvol": int(hv.sum()),
               "crit_t": CRIT, "confirmatory": [], "negative_controls": {}}

    print(f"M127 run | N_full={len(frame)} N_highvol={int(hv.sum())} crit|t|={CRIT}\n")
    for label, pred, cond in TESTS:
        mask = hv if cond == "highvol" else None
        r = run_mim_regression(frame, predictor=pred, label=label, mask=mask)
        passed = (r.t_stat is not None and r.t_stat > CRIT)  # positive (momentum) & significant
        rec = {**r.as_dict(), "passed_confirmatory": bool(passed)}
        results["confirmatory"].append(rec)
        print(f"  {label:34s} n={r.n:4d} beta={r.beta:+.4f} t={r.t_stat:+.3f} "
              f"R2={r.r_squared:.4%} corr={r.corr:+.3f} -> {'PASS' if passed else 'fail'}")

    print("\nNegative controls (full sample; should all be insignificant):")
    suspicious = False
    for pred in ("r_hb", "r_ha"):
        real = run_mim_regression(frame, predictor=pred, label=f"real:{pred}")
        ctrls = negative_controls(frame, predictor=pred, seed=20260616)
        results["negative_controls"][pred] = {
            "real_t": real.t_stat,
            "controls": {k: c.as_dict() for k, c in ctrls.items()},
        }
        print(f"  [{pred}] real t={real.t_stat:+.3f}")
        for name, c in ctrls.items():
            # PREREG criterion (M127_PREREG.yaml negative_controls.pass): a control is
            # problematic iff it is itself SIGNIFICANT at alpha_per_test (|t| > crit). A
            # control being comparable to a *null* real signal is expected, not contamination.
            flag = abs(c.t_stat) > CRIT if c.t_stat is not None else False
            suspicious = suspicious or flag
            print(f"      {name:22s} t={c.t_stat:+.3f}{'  <-- SIGNIFICANT (suspicious)' if flag else ''}")
    results["suspicious"] = bool(suspicious)

    n_pass = sum(1 for c in results["confirmatory"] if c["passed_confirmatory"])
    results["summary"] = {
        "confirmatory_passed": n_pass, "confirmatory_total": len(TESTS),
        "verdict": ("SUSPICIOUS_STOP" if suspicious else
                    "REPLICATED" if n_pass > 0 else "NULL_NON_REPLICATION"),
    }
    with open(args.output, "w") as fh:
        json.dump(results, fh, indent=2)
    print(f"\nVERDICT: {results['summary']['verdict']}  "
          f"({n_pass}/{len(TESTS)} confirmatory passed; suspicious={suspicious})")
    print(f"artifact: {args.output}")


if __name__ == "__main__":
    main()
