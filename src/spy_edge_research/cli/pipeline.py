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
from collections.abc import Mapping, Sequence
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
from spy_edge_research.signal_engine.end_of_day_reversal_features import (
    add_end_of_day_reversal_features,
)
from spy_edge_research.signal_engine.intraday_momentum_features import (
    add_intraday_momentum_parameter_iteration_features,
    add_intraday_momentum_features,
)
from spy_edge_research.signal_engine.mim_baltussen_features import (
    add_mim_baltussen_features,
    mim_baltussen_to_close_horizons,
)
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
from spy_edge_research.backtesting.deflated_sharpe import (
    portfolio_pbo_from_oos,
    summarize_candidate_deflated_sharpe,
)
from spy_edge_research.backtesting.effective_n import (
    candidate_p_values_from_oos,
    compute_effective_n,
    within_cluster_holm,
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
from spy_edge_research.cli.control_batteries import (
    ControlBatteryResults,
    run_control_batteries,
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
    # When True (default) the pipeline runs the negative-control,
    # multiple-testing, and temporal-stability batteries and feeds their
    # outcomes into the readiness gate, so a candidate can reach
    # ``eligible_for_paper_consideration``. When False the batteries are skipped
    # and the run discloses ``control_batteries_not_run_in_basic_pipeline``.
    run_control_batteries: bool = True
    # When True the regime-conditioned intraday-momentum (MIM) family (Build 4
    # Path 2) is added as additional causal ``event_mim_*`` candidates, so the new
    # signal family flows through the SAME candidate / Hard-Gate-A pipeline — a new
    # set of candidates through the same gate, not a new gate. Default off so
    # existing chart-pattern runs are byte-for-byte unchanged.
    include_intraday_momentum: bool = False
    mim_session_open: str = "09:30"
    mim_momentum_window_end: str = "10:00"
    mim_session_close: str = "16:00"
    mim_realized_vol_lookback_days: int = 20
    mim_high_vol_quantile: float = 0.66
    # M117: add the frozen two-spec MIM parameter-iteration cells when MIM is
    # enabled. This adds four event columns, or 12 candidates across 5/15/30m,
    # and every emitted variant flows into the registry and DSR trial count.
    mim_include_parameter_iteration: bool = True
    # When True the end-of-day reversal (F2) family is added as additional causal
    # ``event_eod_reversal_*`` candidates flowing through the SAME gate (PREREG_F2).
    # The to-close hold horizon (``eod_hold_minutes``) is appended to the label
    # horizons so the signal resolves at the close, as the pre-registration requires.
    # Default off so existing runs are byte-for-byte unchanged.
    include_end_of_day_reversal: bool = False
    eod_pre_window_start: str = "14:00"
    eod_pre_window_end: str = "15:00"
    eod_session_close: str = "16:00"
    eod_vol_lookback_days: int = 20
    eod_conviction_z: float = 1.0
    eod_hold_minutes: int = 60
    # When True the MIM-Baltussen rest-of-day momentum family (M121,
    # PREREG_MIM_BALTUSSEN) is added as additional causal ``event_mimb_*``
    # candidates flowing through the SAME gate. The frozen 4-threshold x 4-gate x
    # 2-config grid is emitted as long/short event columns; the per-config to-close
    # forward horizons (29m / 59m, resolving at the 16:00 print) are appended so the
    # outcome resolves at the close. The two VIX gates are inactive unless a daily
    # VIX series is supplied (none in the SPY-only pipeline). Default off so
    # existing runs are byte-for-byte unchanged.
    include_mim_baltussen: bool = False
    mimb_session_open: str = "09:30"
    mimb_session_close: str = "16:00"
    mimb_vix_threshold: float = 20.0
    mimb_regime_lookback_days: int = 60
    mimb_garch_burnin_days: int = 60


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
    if cfg.include_intraday_momentum:
        df = add_intraday_momentum_features(
            df,
            timezone=cfg.timezone,
            session_open=cfg.mim_session_open,
            momentum_window_end=cfg.mim_momentum_window_end,
            session_close=cfg.mim_session_close,
            realized_vol_lookback_days=cfg.mim_realized_vol_lookback_days,
            high_vol_quantile=cfg.mim_high_vol_quantile,
        )
        if cfg.mim_include_parameter_iteration:
            df = add_intraday_momentum_parameter_iteration_features(
                df,
                timezone=cfg.timezone,
                session_open=cfg.mim_session_open,
                session_close=cfg.mim_session_close,
                realized_vol_lookback_days=cfg.mim_realized_vol_lookback_days,
            )
    if cfg.include_end_of_day_reversal:
        df = add_end_of_day_reversal_features(
            df,
            timezone=cfg.timezone,
            pre_window_start=cfg.eod_pre_window_start,
            pre_window_end=cfg.eod_pre_window_end,
            session_close=cfg.eod_session_close,
            vol_lookback_days=cfg.eod_vol_lookback_days,
            conviction_z=cfg.eod_conviction_z,
        )
    if cfg.include_mim_baltussen:
        df = add_mim_baltussen_features(
            df,
            timezone=cfg.timezone,
            session_open=cfg.mimb_session_open,
            session_close=cfg.mimb_session_close,
            vix_threshold=cfg.mimb_vix_threshold,
            regime_lookback_days=cfg.mimb_regime_lookback_days,
            garch_burnin_days=cfg.mimb_garch_burnin_days,
        )
    event_columns = [c for c in df.columns if c.startswith("event_")]
    record("events", "ok", event_column_count=len(event_columns))

    # Stage 4: forward evaluation labels (labels only — never event inputs).
    # F2 resolves at the close, so its to-close hold horizon is appended when the
    # family is enabled (one extra horizon → honest additional cells in N).
    horizons = tuple(cfg.horizons_minutes)
    if cfg.include_end_of_day_reversal and cfg.eod_hold_minutes not in horizons:
        horizons = horizons + (cfg.eod_hold_minutes,)
    if cfg.include_mim_baltussen:
        # Append each config's to-close horizon (29m / 59m) so the rest-of-day
        # momentum outcome resolves at the 16:00 print, not an intraday proxy.
        for h in mim_baltussen_to_close_horizons():
            if h not in horizons:
                horizons = horizons + (h,)
    df = add_forward_labels(df, horizons_minutes=horizons, timezone=cfg.timezone)
    label_columns = [f"forward_return_{h}m" for h in horizons]
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
    oos_results = _safe_oos_results(df, registry, label_columns, cfg)
    oos_stability = (
        summarize_oos_edge_stability(oos_results) if oos_results is not None else None
    )
    if oos_stability is not None and not oos_stability.empty:
        record("oos_stability", "ok", candidate_rows=int(len(oos_stability)))
    else:
        record("oos_stability", "skipped", reason="insufficient_bars_for_walk_forward")

    # Stage 9.25: deflation stack (Deflated Sharpe per candidate + portfolio PBO).
    # The OOS per-split expectancy-difference panel IS the input the López de
    # Prado deflation stack needs (rows = splits, columns = candidates), so this
    # reuses the numbers from Stage 9 rather than re-fitting. Descriptive research
    # diagnostics only — never trade authorization.
    deflated_sharpe_by_candidate: dict[str, float] = {}
    portfolio_pbo: float | None = None
    if oos_results is not None and not oos_results.empty:
        # N for the Deflated Sharpe is the EFFECTIVE number of independent trials
        # (RESEARCH_H / M119): ONC clustering of the candidate return streams,
        # bounded [family_count=2, total]. This supersedes the "N = every cell"
        # (len(registry)) clause of RESEARCH_C §4.3 for the cross-trial DSR input
        # ONLY; sigma_SR is measured over the cluster representatives. Every other
        # control/threshold is unchanged.
        effective_n_result = compute_effective_n(oos_results, family_floor=2)
        dsr_summary = summarize_candidate_deflated_sharpe(
            oos_results,
            effective_n=effective_n_result.n_eff,
            sharpe_sample=effective_n_result.representative_sharpes,
        )
        # Within-cluster Holm candidacy screen (RESEARCH_H §5): a cluster is carried
        # forward only if its best-Sharpe member survives the Holm threshold.
        sharpes_by_candidate = {
            str(r.candidate_id): float(r.observed_sharpe_ratio)
            for r in dsr_summary.itertuples(index=False)
        }
        holm = within_cluster_holm(
            effective_n_result.labels,
            candidate_p_values_from_oos(oos_results),
            sharpes_by_candidate,
        )
        result.metrics["effective_n"] = int(effective_n_result.n_eff)
        result.metrics["effective_n_clusters"] = int(effective_n_result.k_clusters)
        deflated_sharpe_by_candidate = {
            str(r.candidate_id): float(r.deflated_sharpe_ratio)
            for r in dsr_summary.itertuples(index=False)
            if pd.notna(r.deflated_sharpe_ratio)
        }
        pbo_result = portfolio_pbo_from_oos(oos_results)
        pbo_value = pbo_result.get("pbo")
        if pbo_value is not None and pd.notna(pbo_value):
            portfolio_pbo = float(pbo_value)
            result.metrics["portfolio_pbo"] = portfolio_pbo
        record(
            "deflation",
            "ok",
            candidate_rows=int(len(dsr_summary)),
            portfolio_pbo=portfolio_pbo,
            effective_n=int(effective_n_result.n_eff),
            effective_n_clusters=int(effective_n_result.k_clusters),
            total_candidates=int(effective_n_result.total_candidates),
            within_cluster_holm_survivors=int(
                sum(1 for v in holm.values() if v["survived"])
            ),
        )
    else:
        record("deflation", "skipped", reason="insufficient_oos_results")

    # Stage 9.5: control batteries (negative controls, multiple-testing family
    # size, temporal stability). Reduced to the scalars the readiness gate
    # consumes so a validated candidate can reach eligibility. Descriptive
    # research diagnostics only — never trade authorization.
    control_results: ControlBatteryResults | None = None
    if cfg.run_control_batteries and not registry.empty:
        control_results = run_control_batteries(df, registry)
        _write_control_artifacts(paths, control_results, overwrite=overwrite)
        record(
            "control_batteries",
            "ok",
            tested_hypotheses=control_results.tested_hypotheses,
            multiple_testing_warning=control_results.multiple_testing_warning,
        )
    else:
        reason = "disabled" if not cfg.run_control_batteries else "empty_registry"
        record("control_batteries", "skipped", reason=reason)

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
    scorecard, verdicts = _score_readiness(
        oos_stability,
        result.metrics,
        control_results,
        deflated_sharpe_by_candidate=deflated_sharpe_by_candidate,
        portfolio_pbo=portfolio_pbo,
    )
    paths.readiness_scorecard_path.parent.mkdir(parents=True, exist_ok=True)
    scorecard.to_csv(paths.readiness_scorecard_path, index=False)
    verdicts.to_csv(paths.readiness_verdict_path, index=False)
    result.readiness_verdicts = verdicts
    eligible = int((verdicts["verdict"] == "eligible_for_paper_consideration").sum())
    record("readiness", "ok", verdict_rows=int(len(verdicts)), eligible_count=eligible)

    # Run manifest. When the control batteries ran, disclose their (advisory)
    # caveats; otherwise disclose that they were not run.
    if control_results is not None:
        extra_caveats = list(control_results.caveats)
    else:
        extra_caveats = [_CONTROLS_NOT_RUN_CAVEAT]
    write_run_manifest(
        paths,
        run_id=run_id,
        input_path=input_csv,
        stages=result.stages,
        metrics=result.metrics,
        extra_caveats=extra_caveats,
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
                # Hit rate is not computed in the basic pipeline. Recorded as a
                # caveated 0.0 placeholder rather than NaN so the registry JSON
                # round-trips (the candidate schema requires a numeric hit_rate,
                # and NaN serializes to null which the reader rejects). The gate
                # does not use this field; the caveat marks it as not meaningful.
                hit_rate=0.0,
                baseline_hit_rate=0.0,
                context={
                    "label_column": str(r.label_column),
                    "event_family": str(r.event_family),
                },
                caveats=["hit_rate_not_computed_in_basic_pipeline_recorded_as_zero"],
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


def _safe_oos_results(
    df: pd.DataFrame,
    registry: pd.DataFrame,
    label_columns: Sequence[str],
    cfg: PipelineConfig,
) -> pd.DataFrame | None:
    """Return the raw per-candidate per-split OOS results, or None.

    A single source for both the stability summary (Stage 9) and the deflation
    stack (Stage 9.25), so the walk-forward evaluation runs only once.
    """
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
    return oos_results


def _score_readiness(
    oos_stability: pd.DataFrame | None,
    shared_metrics: Mapping[str, Any],
    control_results: ControlBatteryResults | None = None,
    *,
    deflated_sharpe_by_candidate: Mapping[str, float] | None = None,
    portfolio_pbo: float | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Score each candidate's readiness; return (scorecard, verdicts) tables.

    Each candidate's OOS-stability row is combined with the shared portfolio
    overlap metric and (when available) the control-battery outcomes: per-candidate
    negative-control and temporal-stability results plus the portfolio-level
    multiple-testing pass. The deflation stack adds a per-candidate Deflated Sharpe
    Ratio and the portfolio Probability of Backtest Overfitting. Missing metrics are
    treated conservatively by the gate as insufficient evidence.
    """
    deflated_sharpe_by_candidate = deflated_sharpe_by_candidate or {}
    overlap = shared_metrics.get("max_pairwise_jaccard")
    # Per-candidate FDR-adjusted multiple-testing is preferred; the portfolio
    # family-size pass is only a coarse fallback for the no-OOS branch.
    portfolio_multiple_testing = (
        control_results.multiple_testing_passed if control_results is not None else None
    )
    scorecards: list[pd.DataFrame] = []
    verdicts: list[pd.DataFrame] = []

    if oos_stability is None or oos_stability.empty:
        metrics = build_readiness_metrics(
            signal_overlap_summary=(
                pd.Series({"max_jaccard": overlap}) if overlap is not None else None
            ),
            multiple_testing_passed=portfolio_multiple_testing,
        )
        scorecard = score_candidate_readiness(metrics)
        verdict = summarize_readiness_verdict(scorecard)
        scorecard.insert(0, "candidate_id", "portfolio")
        verdict.insert(0, "candidate_id", "portfolio")
        return scorecard, verdict

    for row in oos_stability.itertuples(index=False):
        candidate_id = str(getattr(row, "candidate_id", "candidate"))
        negative_control_passed = None
        temporal_stable_period_count = None
        multiple_testing_passed = portfolio_multiple_testing
        if control_results is not None:
            per = control_results.per_candidate.get(candidate_id, {})
            negative_control_passed = per.get("negative_control_passed")
            temporal_stable_period_count = per.get("temporal_stable_period_count")
            # Prefer the per-candidate FDR-adjusted result when available.
            multiple_testing_passed = per.get(
                "multiple_testing_passed", portfolio_multiple_testing
            )
        metrics = build_readiness_metrics(
            oos_stability_row=pd.Series(row._asdict()),
            signal_overlap_summary=(
                pd.Series({"max_jaccard": overlap}) if overlap is not None else None
            ),
            negative_control_passed=negative_control_passed,
            multiple_testing_passed=multiple_testing_passed,
            temporal_stable_period_count=temporal_stable_period_count,
            pbo=portfolio_pbo,
            deflated_sharpe=deflated_sharpe_by_candidate.get(candidate_id),
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


def _write_control_artifacts(
    paths: RunPaths, results: ControlBatteryResults, *, overwrite: bool
) -> None:
    """Write the three control-battery summary CSVs under ``run_<id>/controls/``."""
    targets = [
        (paths.negative_control_path, results.negative_control_table),
        (paths.temporal_stability_path, results.temporal_stability_table),
        (paths.multiple_testing_path, results.multiple_testing_table),
    ]
    for path, table in targets:
        if path.exists() and not overwrite:
            raise FileExistsError(f"{path} already exists")
        path.parent.mkdir(parents=True, exist_ok=True)
        table.to_csv(path, index=False)


def _horizon_from_label(label_col: str) -> str:
    match = re.search(r"_(\d+m)$", label_col)
    return match.group(1) if match else label_col


def _json_dumps(payload: Mapping[str, Any]) -> str:
    import json

    return json.dumps(payload, indent=2, sort_keys=True, default=str)
