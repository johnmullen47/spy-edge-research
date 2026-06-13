# Architecture & Design — SPY Directional Edge Research

> **Scope of this document.** This is an *as-built* technical architecture map of
> the `spy_edge_research` package as it currently exists on disk. It complements,
> and does not replace, the governing documents:
>
> - [`MASTER_PROJECT_BRIEF.md`](../MASTER_PROJECT_BRIEF.md) — vision, constraints, target layers, protocol (**authoritative for governance**).
> - [`PROJECT_MILESTONES.md`](../PROJECT_MILESTONES.md) — milestone ledger (**authoritative for progress**).
> - [`CODEX_MASTER_DESK.md`](../CODEX_MASTER_DESK.md) — Codex operating posture.
> - [`README.md`](../README.md) — user-facing usage and per-milestone notes.
>
> **Snapshot date:** 2026-06-13. The repository is under active development; treat
> this as a point-in-time map and re-verify against `src/` before relying on
> specifics.

## 1. What this system is

A **research-first validation engine** for SPY intraday directional edges,
intended to grow into a multi-instrument / sector / macro quant research
platform. It is explicitly **not** a trading bot, broker automation, options
selector, or live-execution system.

The defining design property is **causal, auditable, no-lookahead research**:
the system is built to *measure whether an edge exists* and to **kill weak
hypotheses** before they could ever reach decision support. A `No valid trade.`
/ `Evidence insufficient.` output is a first-class, desirable result.

Current state: completed through **Milestone 92**, latest verified suite **750
passed, 4 skipped**. The MOD 06–10 roadmap (`docs/NEXT_MODULES_ROADMAP.md`) is
complete and all research-only — Portfolio/Risk Exposure (M70–74), Factor-ETF
Allocation (M75–79), Research Service Layer (M80–84), Dashboard Data Export
(M85–88), and Paper-Trading Readiness Criteria (M89–92), atop the earlier Sector
(M62–65) and Macro Regime (M66–69) modules.

## 2. Package layout (as-built)

```text
src/spy_edge_research/
├── market_data/          Layer 1  — ingestion, validation, sessions, resampling, multi-symbol alignment
├── indicators/           Layer 2  — causal technical indicators (ATR, ADX, EMA, Bollinger, VWAP, volume)
├── market_structure/     Layer 2/3 — pivots, structure breaks, retests, false breaks
├── support_resistance/   Layer 2/3 — prior-day & premarket levels, zones, zone scoring
├── signal_engine/        Layer 3/4 — causal events, named-event registry, sequences, cross-instrument/sector/macro/factor features
├── market_regime/        Layer 6  — volatility & directional regime classification + diagnostics
├── instruments/          Layer 11/12 — instrument / sector / macro / factor universe registries
├── backtesting/          Layers 5,7–10,15 — labels, event studies, edge measurement, validation, governance, reporting, sector/macro/factor studies
├── risk/                 Layer 14 — exposure, signal-overlap, concentration, advisory limit flags          (MOD 06)
├── services/             Layer 9  — read-only research API over committed artifacts + workflow facade      (MOD 08)
├── dashboard/            Layer 10 — versioned, frontend-ready JSON data contracts                           (MOD 09)
└── paper/                Layer 11/17 — paper-trading readiness gate (criteria → verdict); NOT paper trading  (MOD 10)
```

Mapping is to the 19-layer target model in the master brief. Layers 8–10
(trade simulation, candidate registry, walk-forward) exist today as
**research-grade measurement and candidate-tracking**, not as a live trader.

## 3. Data-flow pipeline

```text
raw OHLCV (CSV / multi-symbol)
   │  market_data: load → validate schema → classify session → resample → align symbols
   ▼
wide causal feature frame   ── indicators + market_structure + support_resistance
   │                            (each row uses only information available at that row)
   ▼
causal events               ── signal_engine.events  (nonzero/truthy/above/at_or_above/below/at_or_below)
   ▼
named event catalog + tape  ── signal_engine.event_catalog / named_events / event_sequences
   ▼
forward outcome labels      ── backtesting.labels  (outcome_* return / direction / path; LABELS ONLY)
   ▼
edge measurement            ── backtesting.event_study / event_forward_outcomes / conditional_event_study
   │                            hit rate, expectancy, sample size, by horizon / direction / regime
   ▼
validation & robustness     ── baselines, negative_controls, placebo_statistics, multiple_testing,
   │                            oos_validation, time_splits (walk-forward), parameter_sensitivity,
   │                            temporal_stability, time_of_day, volatility_range_context
   ▼
candidate registry          ── candidate_edges / candidate_rule_objects / candidate_lineage
   ▼
governance & reporting      ── event_reports, run_registry, audit_index, reproducibility,
                                research_decision_journal, research_maturity, traceability,
                                package_manifest/comparison, *_report_bundle exporters (CSV/JSON)
```

The **causal boundary** sits between *features/events* (which may only see the
current and prior rows) and *forward outcome labels* (which may look forward,
but **only as labels — never as inputs to event detection**). The `outcome_`
column prefix enforces this separation by convention throughout.

**Downstream research consumers (MOD 06–10).** Beyond reporting, the
candidate/registry and report-bundle artifacts feed four newer subpackages:
`risk/` (exposure / overlap / concentration diagnostics + advisory limit flags),
`services/` (read-only loading and querying of committed bundles, plus a
workflow facade), `dashboard/` (versioned JSON data contracts built from loaded
bundles), and `paper/` (a readiness *gate* that scores diagnostic metrics
against pre-registered criteria and emits an eligibility verdict — never a
trade).

## 4. Module reference

### `market_data` — Layer 1: ingestion & normalization
- **Load/validate:** `load_ohlcv_csv`, `validate_ohlcv_schema`, `REQUIRED_COLUMNS`.
- **Sessions:** `classify_session`, `add_session_column`, `filter_premarket`, `filter_regular_session`, `SessionLabel`.
- **Resampling:** `resample_ohlcv`.
- **Multi-symbol:** `align_symbol_frames`, `build_multi_symbol_panel`, `prefix_symbol_columns`, `filter_aligned_symbol_universe`, `summarize_symbol_alignment`, `validate_symbol_frame_map`.

### `indicators` — Layer 2: causal technical features
Standard rolling indicators computed with information available at each row:
`atr`, `adx`, `ema`, `bollinger`, `vwap`, `volume`.

### `market_structure` — Layer 2/3: price structure
`pivots`, `structure_breaks`, `retests`, `false_breaks`. Confirmed-structure
events must not be backdated unless explicitly tagged as known-late confirmation.

### `support_resistance` — Layer 2/3: levels & zones
`prior_day_levels`, `premarket_levels`, `zones`, `zone_scoring`.

### `signal_engine` — Layer 3/4: causal events & named-event registry
- **Event primitives:** `add_basic_event_primitives`, `add_momentum_events`, `add_crossover_events`, `add_range_expansion_events`, `add_trailing_break_events`, `add_volume_expansion_events`, `add_single_bar_pattern_events`, `add_candle_body_features`, `crosses_above/below`.
- **Named-event catalog:** `build_named_event_catalog`, `validate_event_catalog`, `filter_directional_event_catalog`, `infer_named_event_direction`, `infer_named_event_family`, `add_event_hypothesis_columns`.
- **Named events:** structure / retest / false-break / trend-continuation / VWAP / momentum-volume / zone-break / trailing-break event builders + `find_named_event_columns`.
- **Sequences:** `build_event_sequence`, `find_event_sequences`, `encode_recent_event_sequence`, `add_recent_event_sequence_features`, `summarize_event_sequence_counts`.
- **Cross-context features:** cross-instrument confirmation/divergence, sector context (breadth, dispersion, leadership, relative return), macro regime (rates, credit, commodity, volatility-proxy, risk-on/off), and factor context (relative-return, leadership, dispersion).

### `market_regime` — Layer 6: regime classification
- **Classifier + constants:** `classify_volatility_regime`, `classify_directional_regime`, `add_market_regime_classification/features`; labels `TRENDING_UP/DOWN`, `RANGE_BOUND`, `HIGH/NORMAL/LOW_VOLATILITY`, `UNKNOWN_*`.
- **Regime features:** EMA / VWAP / structure / volume / intraday-range feature builders.
- **Diagnostics:** `regime_value_counts`, `regime_duration_summary`, `regime_transition_counts`.

### `instruments` — Layer 11/12: research universes
Typed registries for the base instrument set, the SPDR **sector** universe, the
**macro** universe (rates/credit/commodity/vol proxies), and the **factor**
universe (momentum/value/quality/size/low-vol/yield), each with
create/build/read/write/validate/filter helpers and dataclass definitions.

### `backtesting` — Layers 5, 7–10, 15: the measurement & governance core
This is the largest subsystem. Functional groups:
- **Labels (Layer 5):** `add_forward_return_labels`, `add_forward_direction_labels`, `add_directional_forward_outcome_labels`, `add_forward_path_outcome_labels`, `add_forward_labels`, `horizon_to_bars`.
- **Edge measurement (Layer 7):** `event_study` (`evaluate_event_catalog/column`, `evaluate_named_events`, frequency/regime summaries), `event_forward_outcomes` (hit rate, expectancy, sample size, vs-baseline), `conditional_event_study`, `sequence_outcomes`, `volatility_range_context`, `time_of_day`.
- **Baselines & honesty controls:** `baselines` (always-long/short, random, EMA/VWAP-relation, trailing-break), `negative_controls`, `placebo_statistics`, `multiple_testing` (Bonferroni / FDR), `statistical_tests` (bootstrap, permutation, confidence intervals).
- **Out-of-sample / stability (Layers 9–10):** `time_splits` (walk-forward), `oos_validation`, `parameter_sensitivity`, `temporal_stability`, `data_quality_impact`.
- **Candidate tracking (Layer 9):** `candidate_edges`, `candidate_rule_objects`, `candidate_rule_replay`, `candidate_rule_oos_comparison`, `candidate_rule_audits`, `candidate_rule_reports`, `candidate_family_aggregation`, `candidate_lineage`, `rule_context_review`.
- **Cross-context studies:** `multi_instrument_event_study`, `sector_event_study` + `sector_rotation_reports`, `macro_event_study` + `macro_regime_reports`, `factor_event_study` + `factor_rotation_reports`.
- **Governance & reproducibility (Layer 15):** `event_reports`, `event_artifacts`, `event_run_registry`, `event_audit_index`(`_reports`), `event_reproducibility`(`_reports`), `research_decision_journal`, `research_artifact_integrity`, `research_risk_reports`, `research_maturity`, `research_governance_reports`, `research_package_manifest`/`_comparison`, `research_traceability`, `research_review_workflow`, `event_workflows`, `event_visualizations`, `robustness_reports`. Most report bundles export to both CSV and JSON.

### `risk` — Layer 14: portfolio/risk exposure research (MOD 06)
Descriptive exposure diagnostics over a candidate set — **not** position sizing
or allocation. `exposure` (signed/gross aggregation), `signal_overlap` (pairwise
co-occurrence / Jaccard / correlation), `concentration` (group shares +
Herfindahl), `exposure_limits` (`ExposureLimits` config → advisory flags such as
`risk_overlap_too_high`), `risk_reports` (bundle + CSV/JSON). A forbidden-field
guard rejects allocation/portfolio/order/position_size field names.

### `services` — Layer 9: read-only research service layer (MOD 08)
Offline programmatic access to committed artifacts. `artifact_access`
(`load_report_bundle_json` / `_csv_dir`, `discover_report_bundles`,
`LoadedReportBundle`), `research_queries` (list/get/filter tables, summarize
across bundles), `workflow_service` (a facade over
`build_event_research_workflow_outputs`). No live data, no mutation, no
execution. (An HTTP layer is deferred — no web framework in the environment.)

### `dashboard` — Layer 10: frontend-ready data contracts (MOD 09)
A versioned JSON contract layer (no UI). `contracts` (schema `1.0` envelope +
validation + forbidden-field guard), `export` (`LoadedReportBundle` → payload →
JSON file), `manifest` (provenance across exported payloads). Descriptive data
only — no trade-readiness fields.

### `paper` — Layer 11/17: paper-trading readiness gate (MOD 10)
A research **gate**, *not* paper trading. `readiness_criteria`
(`ReadinessCriteria` pre-registered thresholds), `readiness_scoring`
(per-criterion scorecard + gated `eligible_for_paper_consideration` / `not_ready`
verdict; missing metrics are conservatively `insufficient_evidence`),
`readiness_reports` (bundle + CSV/JSON). It never authorizes a trade, sizes a
position, or runs an order; the paper-trading simulation layer remains a
separate, unauthorized module.

### `cli` — unified pipeline runner (MOD 11)
Makes the import-only backend runnable end-to-end. `pipeline.run_pipeline` is a
pure orchestration that threads one OHLCV frame through existing stage functions
(load → indicators → causal events → forward labels → event-study workflow →
report-bundle export → candidate registry → risk signal-overlap → walk-forward
OOS stability → dashboard contract export → per-candidate readiness scorecard),
writing a deterministic timestamped run dir (`reports/run_<UTC>/...`) plus a
`run_manifest.json`. `main` is a thin argparse layer (`spy-edge` console script)
with `run-pipeline`, `export-dashboard`, `score-readiness`, `list-runs`. It
reimplements no stage logic and produces descriptive artifacts only. The basic
pipeline does not run the negative-control / multiple-testing / temporal-stability
batteries, so readiness verdicts stay `not_ready` (disclosed via the
`control_batteries_not_run_in_basic_pipeline` manifest caveat) until the full
battery is run.

### `simulation` — paper-trading simulation (MOD 14, post-gate, authorized)
The first module **past** the research-only readiness gate, built under explicit
user authorization. Simulates positions/fills/P&L on *historical* bars only — no
real broker, money, live execution, order routing, or options. `position_sim`
opens a position each time a candidate's event column fires (entry decided
causally from rows ≤ t), holds for the candidate's horizon, and closes at the
historical close that many bars later (exits reuse `labels.add_forward_return_labels`).
`execution_model` is a deterministic cost/fill model; `pnl` builds the trade
ledger, realized equity curve, and drawdown; `eligibility` applies the MOD 10
gate as a filter; `sim_reports` packages a validated JSON-safe bundle.
`contracts` holds the **own** data model + forbidden-field validator — sim
records use `entry_price`/`exit_price`/`pnl_points` (rejected by the research
guards) and must never round-trip through `candidate_rule_objects` /
`dashboard.contracts`; every report carries `sim_caveat =
"simulation_only_no_broker_no_real_money"`.

## 5. Core data contracts

| Contract | Shape | Key fields |
|---|---|---|
| **Wide causal feature frame** | one row per timestamp, one column per feature | timestamp (index or column) + feature columns |
| **Event catalog** | one row per named event definition | `feature`, `event_name`, `label`, `threshold`, `direction` (+ optional `side`, `color`, `marker`, `metadata`) |
| **Event tape** | one row per triggered event | `timestamp`, `event_name`, `label`, `feature`, `value` (+ optional display fields) |
| **Forward outcome labels** | columns joined to a research frame | `outcome_*` (return / direction / MFE / MAE / path) — **labels only** |
| **Chart annotations** | display-ready records | `x`, `id`, `text`, optional `y`, `side`, `color`, `marker`, `feature`, `value`, `metadata` |

**Trigger directions:** `nonzero`, `truthy`, `above`, `at_or_above`, `below`,
`at_or_below`. Threshold-based directions require a threshold.

## 6. Design principles (as enforced in code)

- **Causality first.** No future rows in current-row features; rolling windows
  use only past/current data; forward labels are outputs, never inputs.
- **Honesty controls are part of the product.** Baselines, negative/placebo
  controls, multiple-testing adjustment, and OOS/walk-forward are first-class —
  the system is designed to *disprove* edges, not advertise them.
- **Auditability & reproducibility.** Run registries, artifact manifests,
  reproducibility checklists, decision journals, and package manifests make
  every research output traceable and re-runnable.
- **Small composable pure functions** over monoliths; **dataclasses** for typed
  records/configs; **pandas** for research tables; correctness before speed.
- **Test discipline.** Every public function/module is tested with deterministic
  synthetic fixtures; no network or paid-data dependencies in tests; optional
  plotting deps skip gracefully.

## 7. Research-only boundaries (hard constraints)

Not to be implemented until an explicit later milestone authorizes it: options
trading/selection, broker integration, live execution or order routing,
automated trading, buy/sell alerts, trade-readiness dashboards, LLM trade
engines, screenshot trading, real-money rebalancing, real-time production
deployment, and paper trading (until historical validation is strong and
explicitly approved). See `MASTER_PROJECT_BRIEF.md` §"Non-Negotiable Constraints"
and `CODEX_MASTER_DESK.md` §"Hard Boundaries" for the governing list.

## 8. Where it's heading (next boundaries)

The MOD 06–10 roadmap (Milestones 70–92) is complete: portfolio/risk exposure,
factor-ETF allocation research, the read-only research service layer, dashboard
data export, and the paper-trading readiness gate all shipped, all research-only.
MOD 11 (Milestone 97, the `cli/` runner) then made the backend runnable
end-to-end.

**Functional-app build-out (authorized 2026-06-13).** The owner has approved a
sequenced build-out toward a usable app and has **explicitly authorized** the
paper-trading *simulation* layer as a new, clearly-bounded module:

1. **MOD 11 — CLI / pipeline runner** *(done, M97)*.
2. **MOD 14 — paper-trading simulation layer** *(done, M98)*: simulated
   positions / fills / P&L on historical bars in `simulation/`, with its own data
   model and forbidden-field validator (never round-trips through the research
   `candidate_rule_objects` / `dashboard.contracts` validators). Entries causal;
   fixed-horizon exits reuse the `labels.py` forward-price math.
3. **MOD 12 — frontend** *(done, M99)*: a zero-build static viewer
   (`frontend/index.html`) over the MOD 09 dashboard JSON contracts — offline,
   dependency-free, descriptive research only. Contract shape pinned by
   `tests/frontend/`.
4. **MOD 13 — value/quality/momentum research** (mirrors the factor module).

Still forbidden until a further explicit authorization: real broker
connectivity, real money, live/real-time execution, order routing, and options
expression. The readiness gate's `eligible_for_paper_consideration` verdict
still means only that the evidence bar is met — not that anything is cleared to
trade.

## 9. Notes & open observations

- The top-level package `__init__.py` currently only re-exports `market_data`
  (`__all__ = ["market_data"]`); subpackages are imported via their own paths.
  If a single high-level import surface is ever desired, this is the seam.
- `legacy_auto_trader_spy_scaffold/` is an **archived flat copy** of the
  original compact event-transformation scaffold (its own throwaway venv
  included). It is explicitly **non-authoritative** — kept for reference, not
  development.
- The package is installed in editable form as both `auto-trader-spy` (legacy
  dist-info) and `spy_directional_edge_research` (current egg-info); the import
  name is `spy_edge_research`.
