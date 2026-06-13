# Mod 04: Sector Context Research

## Module Name

```text
Sector Context Research
```

## Purpose

This is the implementation prompt for the Mod 04 chat.

Mod 04 should complete the next natural project module after the completed Multi-Instrument Research Module.

The module extends the project from broad multi-index confirmation into sector ETF context research. It should help answer whether SPY event outcomes vary when sector leadership, breadth, dispersion, or sector confirmation conditions are present.

This is still research infrastructure. It must not create trading signals, sector rotation allocation recommendations, broker integrations, live execution, paper trading, options logic, or trade-readiness claims.

## Authoritative Project State

Use this repo:

```text
/Users/johnmullen/Documents/Codex/Auto-Trader SPY
```

Read before coding:

- `CODEX_MASTER_DESK.md`
- `MASTER_PROJECT_BRIEF.md`
- `PROJECT_MILESTONES.md`
- `README.md`

Current verified state:

- Completed through Milestone 61.
- Milestones 58-61 completed the Multi-Instrument Research Module.
- Latest full-suite baseline: `628 passed, 4 skipped`.
- The 4 skipped tests are optional matplotlib visualization tests.
- Mod 04 is approved as Milestones 62-65.

Run tests with:

```bash
.venv/bin/python -m pytest -q
```

## Module Boundary

Implement Milestones 62-65 as one cohesive module:

```text
Milestone 62: Sector ETF Universe Foundation
Milestone 63: Sector Context Feature Layer
Milestone 64: Sector-Confirmed Event Studies
Milestone 65: Sector Rotation Research Reports
```

Stop after Milestone 65. Do not continue to macro/rates/credit/commodity regimes, factor allocation, value research, service APIs, dashboards, paper trading, broker integration, options, alerts, execution, or trade-readiness work unless explicitly instructed in a later module.

## Why This Module Is Next

The completed project already has:

- causal SPY feature/event foundations
- multi-instrument instrument registry
- multi-symbol alignment
- cross-instrument confirmation features
- multi-instrument event outcome studies
- OOS, robustness, placebo, governance, traceability, and package review infrastructure

The next natural research expansion is sector ETF context. This follows the master architecture's sector ETF confirmation and rotation research layer while keeping all outputs descriptive, auditable, and non-execution.

## Milestone 62: Sector ETF Universe Foundation

Goal:

Define a deterministic sector ETF universe for research metadata and grouping.

Likely module:

```text
src/spy_edge_research/instruments/sector_universe.py
```

Likely tests:

```text
tests/instruments/test_sector_universe.py
```

Expected public dataclasses/functions:

- `SectorDefinition`
- `SectorUniverse`
- `create_sector_definition`
- `build_sector_universe`
- `default_spdr_sector_universe`
- `validate_sector_universe`
- `get_sector_definition`
- `list_sector_etfs`
- `filter_sector_universe`
- `write_sector_universe`
- `read_sector_universe`

Expected sector metadata:

- sector name
- ETF symbol
- sector group
- market/session
- timezone
- optional benchmark symbol
- optional notes
- optional metadata

Requirements:

- Include deterministic defaults for common SPDR sector ETFs if useful, such as XLB, XLC, XLE, XLF, XLI, XLK, XLP, XLRE, XLU, XLV, and XLY.
- Keep records JSON-serializable.
- Reject duplicate sector names or ETF symbols.
- Do not require market-data downloads.
- Do not imply tradability, allocation, broker support, or execution support.

## Milestone 63: Sector Context Feature Layer

Goal:

Create causal sector context features from already-aligned sector ETF data.

Likely module:

```text
src/spy_edge_research/signal_engine/sector_context_features.py
```

Likely tests:

```text
tests/signal_engine/test_sector_context_features.py
```

Expected public functions:

- `add_sector_relative_return_features`
- `add_sector_breadth_features`
- `add_sector_leadership_flags`
- `add_sector_dispersion_features`
- `add_primary_sector_confirmation_features`
- `add_sector_context_features`

Requirements:

- Inputs are already-loaded/aligned DataFrames.
- Use only current and prior row information.
- No future returns or forward labels.
- Support configurable primary symbol, sector symbols, and lookback windows.
- Breadth should be descriptive, such as count/fraction of sectors positive or above a benchmark.
- Leadership/laggard flags must be descriptive context, not recommendations.
- Output columns must avoid buy/sell/entry/exit/signal/approval language.
- Missing sector columns should produce clear validation errors or explicit diagnostics.

Example research questions:

- Does SPY continuation differ when cyclical sectors confirm?
- Does SPY event quality change when defensive sectors lead?
- Are SPY events weaker during high sector dispersion?
- Does broad sector participation matter more than single-index confirmation?

## Milestone 64: Sector-Confirmed Event Studies

Goal:

Evaluate existing SPY events and forward outcome columns conditioned on sector context features.

Likely module:

```text
src/spy_edge_research/backtesting/sector_event_study.py
```

Likely tests:

```text
tests/backtesting/test_sector_event_study.py
```

Expected public functions:

- `summarize_event_by_sector_context`
- `compare_sector_confirmed_event_outcomes`
- `build_sector_event_outcome_table`
- `summarize_sector_context_coverage`
- `build_sector_event_research_report`

Requirements:

- Consume existing event columns, forward outcome columns, and sector context columns.
- Forward outcomes remain evaluation-only.
- Include sample sizes and low-sample caveats.
- Include context coverage diagnostics.
- Compare sector-confirmed, sector-divergent, defensive-led, cyclical-led, high-dispersion, and neutral groups descriptively where inputs support it.
- Do not claim edge, rank strategies for deployment, optimize thresholds, create signals, or simulate P/L.

## Milestone 65: Sector Rotation Research Reports

Goal:

Package sector leadership, breadth, dispersion, sector-event study summaries, and caveats into deterministic research report bundles.

Likely module:

```text
src/spy_edge_research/backtesting/sector_rotation_reports.py
```

Likely tests:

```text
tests/backtesting/test_sector_rotation_reports.py
```

Expected public functions:

- `create_sector_rotation_report_metadata`
- `build_sector_rotation_snapshot`
- `summarize_sector_leadership_persistence`
- `build_sector_rotation_report_bundle`
- `validate_sector_rotation_report_bundle`
- `summarize_sector_rotation_report_bundle`
- `export_sector_rotation_report_bundle_to_csv`
- `export_sector_rotation_report_bundle_to_json`

Requirements:

- Treat "rotation" as descriptive sector-leadership research only.
- Do not create allocation recommendations.
- Do not rank sectors as buys/sells.
- Do not imply portfolio construction.
- Preserve caveats about sample size, coverage, and descriptive-only interpretation.
- Export deterministic CSV/JSON artifacts.

## Required Package Updates

Add package exports only where consistent with existing style:

- `src/spy_edge_research/instruments/__init__.py`
- `src/spy_edge_research/signal_engine/__init__.py`
- `src/spy_edge_research/backtesting/__init__.py`

Update:

- `README.md`
- `PROJECT_MILESTONES.md`

The milestone tracker must record:

- milestone goals
- files added
- files modified
- public functions/classes
- causal-safety notes
- focused test commands
- full-suite command
- exact final test result
- next recommended module boundary

## Testing Requirements

For each milestone:

- Add a focused test file.
- Run that focused test file before moving on.
- Run related tests where appropriate.

At the end:

```bash
.venv/bin/python -m pytest -q
```

Expected result should be the previous baseline plus new tests, with the same optional matplotlib skips unless plotting dependencies change.

## Non-Goals

Do not implement:

- live data ingestion
- network/API downloads
- broker integration
- order routing
- live execution
- paper trading
- options logic
- alerts
- dashboard UI
- sector allocation recommendations
- sector buy/sell rankings
- portfolio construction
- strategy recommendations
- buy/sell/entry/exit instructions
- confidence scores
- trade-readiness claims
- P/L simulation
- macro/rates/credit/commodity regime modules
- factor allocation modules
- value research modules

## Acceptance Criteria

Mod 04 is complete when:

- Milestones 62-65 are implemented sequentially.
- Each milestone has focused tests.
- Public helpers are exported consistently.
- README is updated.
- `PROJECT_MILESTONES.md` is updated with all milestone details.
- Full suite passes from the unified root.
- Outputs stay research-only and causal.
- Sector rotation language remains descriptive and non-recommendational.
- No execution, recommendation, broker, options, paper-trading, portfolio-construction, or trade-readiness behavior is introduced.
- The final response recommends the next module boundary but does not begin it.

## Copy-Paste Prompt For Mod 04 Chat

```text
You are the Mod 04 implementation chat for the SPY Directional Edge Research project.

Module name:
Sector Context Research

Authoritative repo:
/Users/johnmullen/Documents/Codex/Auto-Trader SPY

Read first:
- CODEX_MASTER_DESK.md
- MASTER_PROJECT_BRIEF.md
- PROJECT_MILESTONES.md
- README.md

Current verified state:
- Completed through Milestone 61.
- Milestones 58-61 completed the Multi-Instrument Research Module.
- Latest full-suite baseline: 628 passed, 4 skipped.
- The 4 skipped tests are optional matplotlib visualization tests.
- Use .venv/bin/python -m pytest -q for tests.

Implement Milestones 62-65 sequentially as one cohesive module:

Milestone 62: Sector ETF Universe Foundation
- Add a deterministic, JSON-serializable sector ETF universe.
- Likely module: src/spy_edge_research/instruments/sector_universe.py
- Likely tests: tests/instruments/test_sector_universe.py
- Include SectorDefinition, SectorUniverse, create/build/validate/get/list/filter/write/read helpers.
- Include deterministic defaults for common SPDR sector ETFs if useful.
- Reject duplicate sector names or ETF symbols.
- Do not download data or imply tradability, allocation, broker support, or execution.

Milestone 63: Sector Context Feature Layer
- Add causal sector breadth, leadership, dispersion, relative-return, and primary-sector confirmation features.
- Likely module: src/spy_edge_research/signal_engine/sector_context_features.py
- Likely tests: tests/signal_engine/test_sector_context_features.py
- Inputs are already-loaded/aligned DataFrames.
- Use only current/prior row information.
- No future labels.
- No buy/sell/entry/exit/signal/approval language.

Milestone 64: Sector-Confirmed Event Studies
- Evaluate existing SPY events/outcomes conditioned on sector context features.
- Likely module: src/spy_edge_research/backtesting/sector_event_study.py
- Likely tests: tests/backtesting/test_sector_event_study.py
- Include event-by-sector-context summaries, sector-confirmed comparisons, outcome tables, coverage summaries, and a report builder.
- Forward outcomes remain evaluation-only.
- Include sample-size and coverage caveats.
- Do not claim edge, optimize thresholds, create signals, or simulate P/L.

Milestone 65: Sector Rotation Research Reports
- Package sector leadership, breadth, dispersion, sector-event summaries, and caveats into deterministic research report bundles.
- Likely module: src/spy_edge_research/backtesting/sector_rotation_reports.py
- Likely tests: tests/backtesting/test_sector_rotation_reports.py
- Treat rotation as descriptive sector-leadership research only.
- Do not create allocation recommendations, sector buy/sell rankings, portfolio construction, or trade-readiness claims.

Package/doc updates:
- Update relevant __init__.py exports consistently with existing style.
- Update README.md.
- Update PROJECT_MILESTONES.md with complete details for Milestones 62-65.

Testing:
- Run each focused test file after implementing its milestone.
- Run related tests where appropriate.
- End with .venv/bin/python -m pytest -q.
- Record exact commands and results in PROJECT_MILESTONES.md.

Hard boundaries:
- research and validation only
- no live data ingestion
- no network/API downloads
- no broker integration
- no live execution
- no order routing
- no paper trading
- no options logic
- no alerts
- no dashboard UI
- no sector allocation recommendations
- no sector buy/sell rankings
- no portfolio construction
- no buy/sell/entry/exit instructions
- no confidence scores
- no trade-readiness claims
- no P/L simulation

Stop after Milestone 65. Do not start the next module. In the final response, summarize files added/modified, public APIs, tests run, exact final test result, causal-safety notes, and the recommended next module boundary.
```
