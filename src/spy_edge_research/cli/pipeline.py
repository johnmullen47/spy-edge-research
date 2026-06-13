"""Pure, importable end-to-end research pipeline (MOD 11).

``run_pipeline`` threads a single OHLCV DataFrame through the project's existing,
already-committed research stages and writes a timestamped run directory of
artifacts:

    load -> indicators -> events -> forward labels -> event-study workflow
    -> candidate registry -> risk signal-overlap -> walk-forward OOS stability
    -> dashboard contract export -> paper-trading readiness scorecard

It REIMPLEMENTS NO stage logic; every stage calls an existing function. It
produces descriptive research artifacts only — no trade signals, orders,
sizing, or execution. The readiness verdict it writes is a research gate, never
a trade authorization. The causal / no-lookahead invariant is unchanged:
forward_* columns are used as evaluation labels only, never as event inputs.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd

from spy_edge_research.market_data.loaders import load_ohlcv_csv
from spy_edge_research.indicators.vwap import calculate_intraday_vwap
from spy_edge_research.indicators.ema import calculate_ema
from spy_edge_research.indicators.atr import calculate_atr
from spy_edge_research.indicators.adx import calculate_adx
from spy_edge_research.indicators.bollinger import calculate_bollinger_bands
from spy_edge_research.indicators.volume import calculate_volume_features
from spy_edge_research.signal_engine.events import add_basic_event_primitives
from spy_edge_research.signal_engine.named_events import add_named_event_features
from spy_edge_research.signal_engine.event_catalog import build_named_event_catalog
from spy_edge_research.backtesting.labels import add_forward_labels
from spy_edge_research.backtesting.candidate_edges import (
    create_candidate_edge,
    build_candidate_edge_registry,
    write_candidate_edge_registry,
)
from spy_edge_research.backtesting.time_splits import create_walk_forward_splits
from spy_edge_research.backtesting.oos_validation import (
    evaluate_candidate_registry_oos,
    summarize_oos_edge_stability,
)
from spy_edge_research.risk.signal_overlap import (
    compute_event_mask_overlap,
    summarize_signal_overlap,
)
from spy_edge_research.services.workflow_service import (
    run_event_research_workflow_service,
    export_workflow_service_response,
)
from spy_edge_research.services.artifact_access import load_report_bundle_csv_dir
from spy_edge_research.dashboard.export import (
    build_dashboard_payload_from_bundle,
    export_dashboard_payload_to_json,
)
from spy_edge_research.dashboard.manifest import build_dashboard_manifest
from spy_edge_research.paper.readiness_inputs import build_readiness_metrics
from spy_edge_research.paper.readiness_scoring import (
    score_candidate_readiness,
    summarize_readiness_verdict,
)

from spy_edge_research.cli.run_artifacts import (
    RunPaths,
    build_run_paths,
    prepare_run_dir,
    write_run_manifest,
)

_DIRECTION_MAP = {
    "long": "long",
    "short": "short",
    "bullish": "long",
    "bearish": "short",
    "neutral": "neutral",
    "unknown": "unknown",
}

# Control batteries (negative controls, multiple-testing, temporal stability)
# are intentionally NOT run by the basic pipeline. Their readiness metrics are
# left unprovided, so the gate reports them as insufficient evidence. Wiring the
# full validation battery is a separate, larger step.
_CONTROLS_NOT_RUN_CAVEAT = "control_batteries_not_run_in_basic_pipeline"


@dataclass(frozen=True)
class PipelineConfig:
    """Tunable inputs for a pipeline run. Defaults suit 1-minute intraday bars."""

    horizons_minutes: tuple[int, ...] = (5, 15, 30)
    min_events: int = 1
    oos_initial_train_size: int = 80
    oos_test_size: int = 40
    oos_step_size: int | None = 40
    dashboard_payload_type: str = "event_study"
    timezone: str = "America/New_York"


@dataclass
class RunResult:
    """Outcome of a pipeline run: resolved paths, per-stage status, and counts."""

    run_id: str
    paths: RunPaths
    stages: list[dict[str, Any]] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)
    readiness_verdicts: pd.DataFrame | None = None

    @property
    def run_dir(self) -> Path:
        return self.paths.run_dir


def run_pipeline(
    input_csv: str | Path,
    output_root: str | Path,
    *,
    run_id: str,
    config: PipelineConfig | None = None,
    overwrite: bool = False,
) -> RunResult:
    """Run the full research pipeline and write a timestamped run directory.

    ``run_id`` is supplied by the caller (the CLI derives it from a UTC clock)
    so runs are reproducible and tests are deterministic.
    """
    cfg = config or PipelineConfig()
    paths = build_run_paths(output_root, run_id)
    prepare_run_dir(paths, overwrite=overwrite)
    result = RunResult(run_id=run_id, paths=paths)

    def record(name: str, status: str, **detail: Any) -> None:
        result.stages.append({"stage": name, "status": status, **detail})

    # Stage 1: load
    df = load_ohlcv_csv(input_csv)
    record("load", "ok", bar_count=int(len(df)))

    # Stage 2: indicators
    df = calculate_intraday_vwap(df)
    df = calculate_ema(df)
    df = calculate_atr(df)
    df = calculate_adx(df)
    df = calculate_bollinger_bands(df)
    df = calculate_volume_features(df)
    record("indicators", "ok")

    # Stage 3: causal events
    df = add_basic_event_primitives(df)
    df = add_named_event_features(df)
    event_columns = [c for c in df.columns if c.startswith("event_")]
    record("events", "ok", event_column_count=len(event_columns))

    # Stage 4: forward evaluation labels (labels only — never event inputs)
    df = add_forward_labels(df, horizons_minutes=cfg.horizons_minutes, timezone=cfg.timezone)
    label_columns = [f"forward_return_{h}m" for h in cfg.horizons_minutes]
    record("labels", "ok", label_columns=label_columns)

    # Stage 5: event-study workflow
    catalog = build_named_event_catalog(df=df)
    response = run_event_research_workflow_service(
        df, label_columns=label_columns, catalog=catalog, min_events=cfg.min_events
    )
    study = response.outputs["event_study_results"]
    record("event_study", "ok", result_rows=int(len(study)))

    # Stage 6: export report bundle
    export_workflow_service_response(response, paths.report_bundle_dir, overwrite=overwrite)
    record("report_bundle", "ok", path=str(paths.report_bundle_dir))

    # Stage 7: candidate edge registry
    registry = _study_to_candidate_registry(study, label_columns, total_rows=int(len(df)))
    write_candidate_edge_registry(registry, paths.candidates_path, overwrite=overwrite)
    record("candidates", "ok", candidate_count=int(len(registry)))

    # Stage 8: risk signal-overlap (descriptive redundancy only)
    overlap_summary = _safe_overlap_summary(df, event_columns)
    if overlap_summary is not None and not overlap_summary.empty:
        result.metrics["max_pairwise_jaccard"] = float(overlap_summary.iloc[0]["max_jaccard"])
        record("risk_overlap", "ok", max_jaccard=result.metrics["max_pairwise_jaccard"])
    else:
        record("risk_overlap", "skipped", reason="insufficient_event_masks")

    # Stage 9: walk-forward OOS stability (per-candidate)
    oos_stability = _safe_oos_stability(df, registry, label_columns, cfg)
    if oos_stability is not None and not oos_stability.empty:
        record("oos_stability", "ok", candidate_rows=int(len(oos_stability)))
    else:
        record("oos_stability", "skipped", reason="insufficient_bars_for_walk_forward")

    # Stage 10: dashboard contract export
    loaded = load_report_bundle_csv_dir(paths.report_bundle_dir)
    payload = build_dashboard_payload_from_bundle(
        loaded, payload_type=cfg.dashboard_payload_type
    )
    export_dashboard_payload_to_json(payload, paths.dashboard_path, overwrite=overwrite)
    manifest = build_dashboard_manifest([payload])
    paths.dashboard_manifest_path.write_text(
        _json_dumps(manifest), encoding="utf-8"
    )
    record("dashboard", "ok", path=str(paths.dashboard_path))

    # Stage 11: paper-trading readiness scorecard (research gate, not authorization)
    scorecard, verdicts = _score_readiness(oos_stability, result.metrics)
    paths.readiness_scorecard_path.parent.mkdir(parents=True, exist_ok=True)
    scorecard.to_csv(paths.readiness_scorecard_path, index=False)
    verdicts.to_csv(paths.readiness_verdict_path, index=False)
    result.readiness_verdicts = verdicts
    eligible = int((verdicts["verdict"] == "eligible_for_paper_consideration").sum())
    record("readiness", "ok", verdict_rows=int(len(verdicts)), eligible_count=eligible)

    # Run manifest
    write_run_manifest(
        paths,
        run_id=run_id,
        input_path=input_csv,
        stages=result.stages,
        metrics=result.metrics,
        extra_caveats=[_CONTROLS_NOT_RUN_CAVEAT],
        overwrite=overwrite,
    )
    return result


def _study_to_candidate_registry(
    study: pd.DataFrame, label_columns: Sequence[str], *, total_rows: int
) -> pd.DataFrame:
    """Adapt event-study result rows into a validated candidate edge registry.

    Glue only: maps each (event, label) row with a finite event mean into a
    candidate record. Hit rate is not computed in the basic pipeline and is
    recorded as NaN with an explicit caveat.
    """
    rows = study[study["label_column"].isin(list(label_columns))].copy()
    rows = rows[rows["label_mean_on_event"].notna()]
    records = []
    for r in rows.itertuples(index=False):
        horizon = _horizon_from_label(r.label_column)
        records.append(
            create_candidate_edge(
                candidate_id=f"{r.event_column}__{horizon}",
                candidate_type="event",
                name=str(r.event_column),
                direction=_DIRECTION_MAP.get(str(r.event_direction), "unknown"),
                horizon=horizon,
                sample_size=int(r.event_count),
                baseline_sample_size=int(total_rows),
                expectancy=float(r.label_mean_on_event),
                baseline_expectancy=float(r.overall_label_mean),
                hit_rate=float("nan"),
                baseline_hit_rate=float("nan"),
                context={
                    "label_column": str(r.label_column),
                    "event_family": str(r.event_family),
                },
                caveats=["hit_rate_not_computed_in_basic_pipeline"],
            )
        )
    return build_candidate_edge_registry(records)


def _safe_overlap_summary(
    df: pd.DataFrame, event_columns: Sequence[str]
) -> pd.DataFrame | None:
    if len(event_columns) < 2:
        return None
    overlap = compute_event_mask_overlap(df, mask_columns=list(event_columns))
    if overlap.empty:
        return None
    return summarize_signal_overlap(overlap)


def _safe_oos_stability(
    df: pd.DataFrame,
    registry: pd.DataFrame,
    label_columns: Sequence[str],
    cfg: PipelineConfig,
) -> pd.DataFrame | None:
    if registry.empty:
        return None
    if len(df) < cfg.oos_initial_train_size + cfg.oos_test_size:
        return None
    splits = create_walk_forward_splits(
        df,
        initial_train_size=cfg.oos_initial_train_size,
        test_size=cfg.oos_test_size,
        step_size=cfg.oos_step_size,
    )
    if not splits:
        return None
    outcome_by_horizon = {_horizon_from_label(c): c for c in label_columns}
    oos_results = evaluate_candidate_registry_oos(
        df,
        registry,
        splits,
        outcome_columns_by_horizon=outcome_by_horizon,
        min_events=cfg.min_events,
    )
    if oos_results.empty:
        return None
    return summarize_oos_edge_stability(oos_results)


def _score_readiness(
    oos_stability: pd.DataFrame | None, shared_metrics: Mapping[str, Any]
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Score each candidate's readiness; return (scorecard, verdicts) tables.

    Each candidate's OOS-stability row is combined with the shared portfolio
    overlap metric. Missing metrics (e.g. the unrun control batteries) are
    treated conservatively by the gate as insufficient evidence.
    """
    overlap = shared_metrics.get("max_pairwise_jaccard")
    scorecards: list[pd.DataFrame] = []
    verdicts: list[pd.DataFrame] = []

    if oos_stability is None or oos_stability.empty:
        metrics = build_readiness_metrics(
            signal_overlap_summary=(
                pd.Series({"max_jaccard": overlap}) if overlap is not None else None
            ),
        )
        scorecard = score_candidate_readiness(metrics)
        verdict = summarize_readiness_verdict(scorecard)
        scorecard.insert(0, "candidate_id", "portfolio")
        verdict.insert(0, "candidate_id", "portfolio")
        return scorecard, verdict

    for row in oos_stability.itertuples(index=False):
        candidate_id = str(getattr(row, "candidate_id", "candidate"))
        metrics = build_readiness_metrics(
            oos_stability_row=pd.Series(row._asdict()),
            signal_overlap_summary=(
                pd.Series({"max_jaccard": overlap}) if overlap is not None else None
            ),
        )
        scorecard = score_candidate_readiness(metrics)
        verdict = summarize_readiness_verdict(scorecard)
        scorecard.insert(0, "candidate_id", candidate_id)
        verdict.insert(0, "candidate_id", candidate_id)
        scorecards.append(scorecard)
        verdicts.append(verdict)

    return (
        pd.concat(scorecards, ignore_index=True),
        pd.concat(verdicts, ignore_index=True),
    )


def _horizon_from_label(label_col: str) -> str:
    match = re.search(r"_(\d+m)$", label_col)
    return match.group(1) if match else label_col


def _json_dumps(payload: Mapping[str, Any]) -> str:
    import json

    return json.dumps(payload, indent=2, sort_keys=True, default=str)
