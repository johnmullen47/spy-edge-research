"""Throwaway probe to validate the MOD 11 orchestration chain end-to-end."""
from __future__ import annotations

import numpy as np
import pandas as pd

from spy_edge_research.indicators.ema import calculate_ema
from spy_edge_research.indicators.atr import calculate_atr
from spy_edge_research.indicators.adx import calculate_adx
from spy_edge_research.indicators.bollinger import calculate_bollinger_bands
from spy_edge_research.indicators.vwap import calculate_intraday_vwap
from spy_edge_research.indicators.volume import calculate_volume_features
from spy_edge_research.signal_engine.events import add_basic_event_primitives
from spy_edge_research.signal_engine.named_events import add_named_event_features
from spy_edge_research.signal_engine.event_catalog import build_named_event_catalog
from spy_edge_research.backtesting.labels import add_forward_labels
from spy_edge_research.services.workflow_service import (
    run_event_research_workflow_service,
    export_workflow_service_response,
)
from spy_edge_research.services.artifact_access import (
    load_report_bundle_csv_dir,
    discover_report_bundles,
)
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
import re
import tempfile
from pathlib import Path


def _horizon_from_label(label_col: str) -> str:
    m = re.search(r"_(\d+m)$", label_col)
    return m.group(1) if m else label_col


def study_to_candidates(study: pd.DataFrame, label_cols, total_rows: int):
    dir_map = {"long": "long", "short": "short", "bullish": "long", "bearish": "short",
               "neutral": "neutral", "unknown": "unknown"}
    rows = study[study["label_column"].isin(label_cols)].copy()
    rows = rows[rows["label_mean_on_event"].notna()]
    records = []
    for r in rows.itertuples(index=False):
        horizon = _horizon_from_label(r.label_column)
        records.append(create_candidate_edge(
            candidate_id=f"{r.event_column}__{horizon}",
            candidate_type="event",
            name=r.event_column,
            direction=dir_map.get(str(r.event_direction), "unknown"),
            horizon=horizon,
            sample_size=int(r.event_count),
            baseline_sample_size=int(total_rows),
            expectancy=float(r.label_mean_on_event),
            baseline_expectancy=float(r.overall_label_mean),
            hit_rate=float("nan"),
            baseline_hit_rate=float("nan"),
            context={"label_column": r.label_column, "event_family": r.event_family},
            caveats=["hit_rate_not_computed_in_basic_pipeline"],
        ))
    return build_candidate_edge_registry(records)


def synth(n=240, seed=7):
    rng = np.random.default_rng(seed)
    # two trading days of 1-min bars, 120 each, regular session start 09:30 ET
    start = pd.Timestamp("2024-01-02 09:30:00", tz="America/New_York")
    ts = []
    for day in range(2):
        day_start = start + pd.Timedelta(days=day)
        ts.extend([day_start + pd.Timedelta(minutes=i) for i in range(n // 2)])
    ts = pd.DatetimeIndex(ts)
    price = 100 + np.cumsum(rng.normal(0, 0.05, size=n))
    high = price + rng.uniform(0.01, 0.1, size=n)
    low = price - rng.uniform(0.01, 0.1, size=n)
    vol = rng.integers(1000, 5000, size=n)
    return pd.DataFrame(
        {
            "timestamp": ts,
            "symbol": "SPY",
            "open": price,
            "high": high,
            "low": low,
            "close": price,
            "volume": vol,
        }
    )


def main():
    df = synth()
    print("bars:", len(df))

    # Stage 2: indicators
    df = calculate_intraday_vwap(df)
    df = calculate_ema(df)
    df = calculate_atr(df)
    df = calculate_adx(df)
    df = calculate_bollinger_bands(df)
    df = calculate_volume_features(df)
    print("after indicators cols:", [c for c in df.columns if c not in ("timestamp", "symbol")][:12], "...")

    # Stage 3: events
    df = add_basic_event_primitives(df)
    df = add_named_event_features(df)
    event_cols = [c for c in df.columns if c.startswith("event_")]
    print("event cols:", len(event_cols), event_cols[:8])

    # Stage 4: labels
    df = add_forward_labels(df, horizons_minutes=(5, 15))
    label_cols = [c for c in df.columns if c.startswith("forward_return_") and not c.endswith("bps")]
    print("label cols:", label_cols)

    # Stage 5: catalog + workflow
    catalog = build_named_event_catalog(df=df)
    print("catalog rows:", len(catalog), "cols:", list(catalog.columns))
    resp = run_event_research_workflow_service(
        df, label_columns=label_cols, catalog=catalog, min_events=1
    )
    print("table_names:", resp.table_names[:6])
    study = resp.outputs["event_study_results"]
    print("event_study_results shape:", study.shape)

    run_dir = Path(tempfile.mkdtemp(prefix="probe_run_"))
    bundle_dir = run_dir / "report_bundle"
    export_workflow_service_response(resp, bundle_dir, overwrite=True)
    print("bundle written:", sorted(p.name for p in bundle_dir.glob("*")))

    # Stage 7: candidates
    registry = study_to_candidates(study, label_cols, total_rows=len(df))
    print("candidates:", len(registry))
    cand_path = write_candidate_edge_registry(
        registry, run_dir / "candidates" / "candidate_edges.json", overwrite=True
    )
    print("candidate registry:", cand_path.name)

    # Stage 8: risk overlap
    overlap = compute_event_mask_overlap(df, mask_columns=event_cols)
    overlap_summary = summarize_signal_overlap(overlap)
    print("overlap_summary cols:", list(overlap_summary.columns))
    print(overlap_summary.to_string())

    # Stage 8a: OOS stability
    splits = create_walk_forward_splits(df, initial_train_size=80, test_size=40, step_size=40)
    print("splits:", len(splits))
    outcome_by_h = {_horizon_from_label(c): c for c in label_cols}
    print("outcome_by_h:", outcome_by_h)
    oos_results = evaluate_candidate_registry_oos(
        df, registry, splits, outcome_columns_by_horizon=outcome_by_h, min_events=1
    )
    print("oos_results shape:", oos_results.shape, list(oos_results.columns))
    oos_stab = summarize_oos_edge_stability(oos_results)
    print("oos_stab cols:", list(oos_stab.columns))
    print(oos_stab.head().to_string())

    # Stage 9: dashboard
    loaded = load_report_bundle_csv_dir(bundle_dir)
    payload = build_dashboard_payload_from_bundle(loaded, payload_type="event_study")
    dash_path = export_dashboard_payload_to_json(
        payload, run_dir / "dashboard" / "event_study.json", overwrite=True
    )
    manifest = build_dashboard_manifest([payload])
    print("dashboard json:", dash_path.name, "| manifest keys:", list(manifest.keys()))

    # Stage 10: readiness (per candidate, using OOS stab row + overlap summary)
    metrics = build_readiness_metrics(
        oos_stability_row=oos_stab.iloc[[0]] if not oos_stab.empty else None,
        signal_overlap_summary=overlap_summary.iloc[[0]] if not overlap_summary.empty else None,
    )
    print("readiness metrics:", metrics)
    scorecard = score_candidate_readiness(metrics)
    verdict = summarize_readiness_verdict(scorecard)
    print(verdict.to_string())

    print("\\ndiscover_report_bundles:")
    print(discover_report_bundles(run_dir).to_string())


if __name__ == "__main__":
    main()
