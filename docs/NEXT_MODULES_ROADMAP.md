# Next Modules Roadmap (Milestone 70+)

> **Status: planning only.** This document briefs all candidate next modules so a
> module boundary can be chosen. Nothing here is approved or started. Per project
> governance, **one module is approved and built at a time**; Milestone 70+ scope
> is a user decision. Governing docs: `MASTER_PROJECT_BRIEF.md`,
> `CODEX_MASTER_DESK.md`, `PROJECT_MILESTONES.md`. Snapshot: 2026-06-13,
> baseline Milestone 69 (`679 passed, 4 skipped`).

## Context

The platform has completed its core research stack through Milestone 69:
data → indicators → structure/levels → causal events → forward labels → regime →
edge measurement → validation/robustness/governance → multi-instrument → sector →
macro context. The five candidate directions below map to the long-term phases in
`MASTER_PROJECT_BRIEF.md` (Phases 6, 7, 9, 10, 11). All remain **research-only**:
no execution, broker, options, alerts, real-money sizing, or trade-readiness
claims. A "no valid trade / evidence insufficient / risk overlap too high" output
is a valid, desirable result.

Each module mirrors the proven shape of the last three (MOD 03/04/05): a typed
universe/registry where relevant, causal feature builders, conditioned event
studies, and CSV/JSON report bundles — each milestone fully tested before the
next.

## Recommended sequence & dependencies

```text
MOD 06  Portfolio / Risk Exposure Research   (Phase 6)   ← recommended first
   │      builds on multi-instrument/sector/macro context already shipped;
   │      prerequisite for any allocation or readiness reasoning
   ▼
MOD 07  Factor-ETF Allocation Research        (Phase 7)
   │      extends the instrument universe + edge studies to factor ETFs
   ▼
MOD 08  Research API / Service Layer           (Phase 9)
   │      exposes existing report bundles/registries programmatically (read-only)
   ▼
MOD 09  Dashboard Data Export                  (Phase 10)
   │      stable, versioned frontend-ready JSON contracts (depends on MOD 08)
   ▼
MOD 10  Paper-Trading Readiness Criteria       (Phase 11)
          a research-only readiness *gate/scorecard* — NOT paper trading itself;
          depends on the risk layer (MOD 06) for exposure criteria
```

Modules are reorderable, but MOD 06 is the strongest first pick: exposure/overlap
reasoning is the missing research layer that every later module (allocation,
readiness) leans on, and all its prerequisites already exist.

The milestone bands below assume this order; they shift if you reorder.

---

## MOD 06 — Portfolio / Risk Exposure Research  (Phase 6)

**Proposed milestones:** 70–74. **Status:** prerequisites met (multi-instrument,
sector, macro context + candidate registry all shipped).

**Goal / why now.** Provide causal, descriptive measures of *exposure* and *risk
overlap* across a set of candidate edges / instruments, so research can flag
concentration and redundancy before anything downstream treats a candidate as
usable. Produces the "risk overlap too high" class of outputs the master brief
calls for.

**Scope (milestone breakdown).**
- 70 — `exposure.py`: aggregate gross/net directional exposure implied by a
  candidate set across instruments/horizons (descriptive only).
- 71 — `signal_overlap.py`: rolling co-occurrence / correlation of candidate
  event masks and of instrument returns (how redundant are these edges?).
- 72 — `concentration.py`: instrument/family/regime concentration metrics
  (reuse `candidate_family_aggregation`).
- 73 — `exposure_limits.py`: config-driven limit **checks** that emit flags
  (`risk_overlap_too_high`, `concentration_exceeds_limit`) — flags, never orders.
- 74 — `risk_reports.py`: report bundle + CSV/JSON export.

**Package location:** new `src/spy_edge_research/risk/`.

**Reuses:** `candidate_family_aggregation`, `multi_instrument_event_study`,
cross-instrument features (`signal_engine.cross_instrument_features`),
`statistical_tests`, instruments registry, and the existing report-bundle
pattern (`build_*_report_bundle`, `export_report_bundle_to_csv/json`).

**Expected tests:** one focused `test_*.py` per module; synthetic candidate sets
+ small multi-symbol panels; assert flags fire at known thresholds; assert
descriptive-only column naming (no buy/sell/entry/exit/approved/live).

**Acceptance criteria:** causal & no-lookahead; flags are advisory; full suite
green; report bundles round-trip to CSV/JSON; outputs carry research caveats.

**Non-goals:** position sizing for real capital, order generation, portfolio
optimization/rebalancing, Kelly/vol-target sizing presented as actionable.

---

## MOD 07 — Factor-ETF Allocation Research  (Phase 7)

**Proposed milestones:** 75–79. **Status:** prerequisites met (sector module is a
direct template).

**Goal / why now.** Extend the instrument universe and conditioned event studies
to **factor ETFs** (momentum, value, quality, size, low-volatility), studying
*which factor regimes coincide with measured edge* — not generating allocations.

**Scope (milestone breakdown).**
- 75 — `instruments/factor_universe.py`: typed factor-ETF universe (mirror
  `sector_universe.py` / `macro_universe.py`).
- 76 — `signal_engine/factor_context_features.py`: factor relative-strength,
  leadership, dispersion (mirror `sector_context_features.py`).
- 77 — `backtesting/factor_event_study.py`: event outcomes conditioned on factor
  context (mirror `sector_event_study.py`).
- 78 — `backtesting/factor_rotation_reports.py`: factor leadership/rotation
  report bundle (mirror `sector_rotation_reports.py`).
- 79 — integration: factor context in the multi-context research workflow +
  coverage summaries.

**Package location:** extends `instruments/`, `signal_engine/`, `backtesting/`.

**Reuses:** the entire sector module as a structural template;
`cross_instrument_features`, `build_*_event_outcome_table`, instruments registry
helpers (`build_*_universe`, `default_*_universe`, `filter_*`).

**Expected tests:** mirror `test_sector_*` — universe build/validate/read/write,
feature causality, conditioned outcomes, report round-trip.

**Acceptance criteria:** causal; descriptive factor diagnostics only; full suite
green; report bundles export.

**Non-goals:** allocation weights / target portfolios for real money, factor
timing "signals," optimization results presented as actionable.

---

## MOD 08 — Research API / Service Layer  (Phase 9)

**Proposed milestones:** 80–84. **Status:** prerequisites met (report bundles,
registries, manifests, workflows all shipped).

**Goal / why now.** Provide a thin, **read-only, offline** programmatic surface
over existing research artifacts (report bundles, run registry, audit index,
package manifests) so they can be queried without re-running pipelines — the
backend the eventual local app/dashboard consumes.

**Scope (milestone breakdown).**
- 80 — `services/artifact_access.py`: load/validate committed artifacts from disk
  into typed result objects.
- 81 — `services/research_queries.py`: query functions (list runs, fetch a
  study/stability/robustness bundle, diff packages) over those artifacts.
- 82 — `services/workflow_service.py`: orchestrate `event_workflows` end-to-end
  and return structured outputs.
- 83 — *(optional)* `services/http_app.py`: a minimal local HTTP layer behind an
  **optional** dependency (FastAPI/Flask), skipped gracefully like matplotlib.
- 84 — service-level integration tests + a documented stable response contract.

**Package location:** new `src/spy_edge_research/services/`.

**Reuses:** `event_workflows` (`build_event_research_workflow_outputs`),
`event_run_registry`, `event_audit_index`, `research_package_manifest`, all
`*_report_bundle` builders/exporters.

**Expected tests:** deterministic, no network; if the HTTP layer is included, use
an in-process test client and skip when the optional dep is absent.

**Acceptance criteria:** read-only; no live/market data; offline-reproducible;
full suite green; response contracts validated.

**Non-goals:** auth, trading/order endpoints, real-time data, write endpoints
that mutate research history, anything resembling execution.

---

## MOD 09 — Dashboard Data Export  (Phase 10)

**Proposed milestones:** 85–88. **Status:** best after MOD 08.

**Goal / why now.** Produce **stable, versioned, frontend-ready JSON contracts**
from research artifacts — the data a future dashboard renders. This is the data
contract layer only, not a UI.

**Scope (milestone breakdown).**
- 85 — `dashboard/contracts.py`: versioned schema definitions for the export
  payloads (event-study summary, OOS stability, robustness, coverage).
- 86 — `dashboard/export.py`: build payloads from report bundles / visualization
  prep tables; validate against the schema.
- 87 — `dashboard/manifest.py`: an export manifest (schema version, source run
  ids, generated artifact list) for traceability.
- 88 — integration + golden-contract tests.

**Package location:** new `src/spy_edge_research/dashboard/`.

**Reuses:** `prepare_event_count_table` / `prepare_*_table` (visualization prep),
`*_report_bundle` summaries, MOD 08 services for orchestration,
`research_package_manifest` pattern for the export manifest.

**Expected tests:** schema-validation tests; golden JSON contract snapshots;
round-trip and version-bump handling.

**Acceptance criteria:** schema-versioned and validated; descriptive only;
deterministic; full suite green.

**Non-goals:** any actual frontend, buy/sell widgets, live data feeds,
trade-readiness or signal fields in the payloads.

---

## MOD 10 — Paper-Trading Readiness Criteria  (Phase 11)

**Proposed milestones:** 89–92. **Status:** gated last; depends on MOD 06 for
exposure criteria. **This is a readiness *gate/scorecard*, not paper trading.**

**Goal / why now.** Define and apply explicit, pre-registered, research-only
**kill/readiness criteria** that score whether a candidate or research package
would even be *eligible* to consider for a future (separately authorized)
paper-trading layer. The output is a verdict + reasons, e.g.
`not_ready: failed_oos_stability`, `not_ready: insufficient_sample`, or
`eligible_for_paper_consideration` — never an instruction to trade.

**Scope (milestone breakdown).**
- 89 — `paper/readiness_criteria.py`: declarative, pre-registered criteria
  (min OOS-stable splits, min sample, robustness survival, negative-control &
  multiple-testing survival, temporal stability, exposure-overlap limit).
- 90 — `paper/readiness_scoring.py`: score a candidate/package against criteria,
  emitting pass/fail per criterion + an overall gated verdict with reasons.
- 91 — `paper/readiness_reports.py`: readiness scorecard report bundle.
- 92 — integration with the candidate registry + research package comparison.

**Package location:** new `src/spy_edge_research/paper/` (criteria only).

**Reuses:** `summarize_oos_edge_stability`, `negative_controls`,
`placebo_statistics`, `multiple_testing`, `temporal_stability`,
`research_maturity` (`score_research_package_from_diagnostics`),
`robustness_reports`, and MOD 06 exposure flags.

**Expected tests:** candidates that pass/fail each criterion; verdict reasons;
descriptive-only naming.

**Acceptance criteria:** every criterion is explicit and tested; a failing
candidate yields a clear negative verdict; full suite green.

**Non-goals (critical):** no paper trades, no broker/paper-broker simulation, no
order generation, no P/L simulation, no "go live" semantics. The actual
paper-trading **simulation** layer is a separate, later, explicitly-authorized
module — this only defines whether a candidate is even worth considering.

---

## How each module will be executed

Per the established loop (and the now-active git workflow): scope the chosen
module → implement on a branch → focused tests then full suite → keep `main`
green → summarize files/APIs/tests/limitations → only then brief the next
milestone. One module at a time.
