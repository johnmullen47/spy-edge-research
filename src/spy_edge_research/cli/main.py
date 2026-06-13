"""Command-line entry point for the SPY edge-research pipeline (MOD 11).

Thin argparse layer: it parses arguments and dispatches to the pure pipeline
functions. All research logic lives in ``pipeline.py`` and the existing
research modules. This CLI produces descriptive research artifacts only — never
trade signals, orders, or execution.
"""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

from spy_edge_research.cli.pipeline import PipelineConfig, RunResult, run_pipeline
from spy_edge_research.services.artifact_access import (
    discover_report_bundles,
    load_report_bundle_csv_dir,
)
from spy_edge_research.dashboard.export import (
    build_dashboard_payload_from_bundle,
    export_dashboard_payload_to_json,
)


def _new_run_id() -> str:
    """Derive a sortable UTC run id (clock access kept out of pure pipeline code)."""
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")


def _parse_horizons(value: str) -> tuple[int, ...]:
    parts = [p.strip() for p in value.split(",") if p.strip()]
    if not parts:
        raise argparse.ArgumentTypeError("horizons must be a comma-separated list of minutes")
    try:
        return tuple(int(p) for p in parts)
    except ValueError as exc:  # noqa: TRY003
        raise argparse.ArgumentTypeError(f"invalid horizons: {value}") from exc


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="spy-edge",
        description="Run-only, research-only SPY edge-research pipeline (descriptive artifacts).",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run-pipeline", help="Run the full research pipeline end-to-end.")
    run.add_argument("--input", required=True, help="Path to an OHLCV CSV file.")
    run.add_argument("--output", default="reports", help="Run-output root directory.")
    run.add_argument("--run-id", default=None, help="Override the generated UTC run id.")
    run.add_argument("--horizons", type=_parse_horizons, default=None,
                     help="Comma-separated forward horizons in minutes (default: 5,15,30).")
    run.add_argument("--overwrite", action="store_true", help="Overwrite an existing run dir.")
    run.set_defaults(func=_cmd_run_pipeline)

    export = sub.add_parser("export-dashboard", help="Re-export a dashboard contract from a bundle.")
    export.add_argument("--bundle", required=True, help="Report-bundle CSV directory.")
    export.add_argument("--output", required=True, help="Output JSON path.")
    export.add_argument("--payload-type", default="event_study", help="Dashboard payload type.")
    export.add_argument("--overwrite", action="store_true")
    export.set_defaults(func=_cmd_export_dashboard)

    score = sub.add_parser("score-readiness", help="Print the readiness verdict for a run dir.")
    score.add_argument("--run", required=True, help="A run directory produced by run-pipeline.")
    score.set_defaults(func=_cmd_score_readiness)

    listing = sub.add_parser("list-runs", help="List report bundles discovered under a root.")
    listing.add_argument("--root", default="reports", help="Root directory to scan.")
    listing.set_defaults(func=_cmd_list_runs)

    return parser


def _cmd_run_pipeline(args: argparse.Namespace) -> int:
    config = PipelineConfig()
    if args.horizons is not None:
        config = PipelineConfig(horizons_minutes=args.horizons)
    run_id = args.run_id or _new_run_id()
    result: RunResult = run_pipeline(
        args.input, args.output, run_id=run_id, config=config, overwrite=args.overwrite
    )
    print(f"run_id: {result.run_id}")
    print(f"run_dir: {result.run_dir}")
    for stage in result.stages:
        extra = {k: v for k, v in stage.items() if k not in ("stage", "status")}
        print(f"  [{stage['status']:>7}] {stage['stage']}  {extra or ''}".rstrip())
    if result.readiness_verdicts is not None:
        eligible = int(
            (result.readiness_verdicts["verdict"] == "eligible_for_paper_consideration").sum()
        )
        print(f"readiness: {len(result.readiness_verdicts)} candidate(s), {eligible} eligible")
    return 0


def _cmd_export_dashboard(args: argparse.Namespace) -> int:
    bundle = load_report_bundle_csv_dir(args.bundle)
    payload = build_dashboard_payload_from_bundle(bundle, payload_type=args.payload_type)
    target = export_dashboard_payload_to_json(payload, args.output, overwrite=args.overwrite)
    print(f"wrote {target}")
    return 0


def _cmd_score_readiness(args: argparse.Namespace) -> int:
    import pandas as pd

    verdict_path = Path(args.run) / "readiness" / "verdict.csv"
    if not verdict_path.exists():
        raise FileNotFoundError(f"no readiness verdict at {verdict_path}")
    verdicts = pd.read_csv(verdict_path)
    print(verdicts.to_string(index=False))
    return 0


def _cmd_list_runs(args: argparse.Namespace) -> int:
    bundles = discover_report_bundles(args.root)
    if bundles.empty:
        print(f"no report bundles found under {args.root}")
    else:
        print(bundles.to_string(index=False))
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
