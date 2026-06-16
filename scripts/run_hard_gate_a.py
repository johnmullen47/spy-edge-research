#!/usr/bin/env python3
"""Run the research pipeline on real SPY 1-min data and report Hard Gate A.

Standalone driver (outside the package) that calls ``run_pipeline`` with
walk-forward / OOS sizes appropriate for ~2 years of 1-minute bars — the CLI only
exposes ``--horizons``, and its tiny defaults (train=80/test=40) would produce
thousands of degenerate splits on a dataset this size. Prints the readiness
verdict breakdown: that breakdown IS Hard Gate A.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path

from spy_edge_research.cli.pipeline import PipelineConfig, run_pipeline


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default="data/raw/spy_1min.csv")
    parser.add_argument("--output", default="reports")
    parser.add_argument("--vix", default="data/raw/vix_daily.csv",
                        help="daily VIX term-structure CSV (scripts/fetch_vix.py)")
    parser.add_argument("--train", type=int, default=30000, help="OOS initial train bars")
    parser.add_argument("--test", type=int, default=7500, help="OOS test bars per fold")
    args = parser.parse_args()

    cfg = PipelineConfig(
        horizons_minutes=(5, 15, 30),
        oos_initial_train_size=args.train,
        oos_test_size=args.test,
        oos_step_size=args.test,
        include_intraday_momentum=True,
        include_end_of_day_reversal=True,
        include_mim_baltussen=True,
        vix_csv=args.vix,
        include_f3_vix_gate=True,
        include_f4_overnight_gap=True,
        include_f5_fomc_calendar=True,
        include_f6_vrp=True,
        include_f7_vol_managed=True,
        include_f8_orb=True,
        include_f9_periodicity=True,
        include_f10_fomc_cycle=True,
    )
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    result = run_pipeline(
        args.input, args.output, run_id=run_id, config=cfg, overwrite=True
    )

    print(f"run_dir: {result.run_dir}")
    for stage in result.stages:
        print("  stage:", stage)

    verdicts = result.readiness_verdicts
    print("\n=== READINESS VERDICTS (Hard Gate A) ===")
    if verdicts is None or verdicts.empty:
        print("no verdicts produced")
        return
    counts = verdicts["verdict"].value_counts().to_dict()
    print("verdict counts:", counts)
    eligible = verdicts[verdicts["verdict"] == "eligible_for_paper_consideration"]
    if eligible.empty:
        print("\nNO candidate reached eligible_for_paper_consideration.")
        print("=> No validated edge on this data. Broker layers stay OFF. (Valid result.)")
        # Show why the closest candidates failed.
        if "failing_reasons" in verdicts.columns:
            print("\nsample failing_reasons:")
            for _, row in verdicts.head(8).iterrows():
                print(f"  {row.get('candidate_id', '?')}: {row['failing_reasons']}")
    else:
        print(f"\n{len(eligible)} candidate(s) reached ELIGIBLE:")
        print(eligible.to_string(index=False))


if __name__ == "__main__":
    main()
