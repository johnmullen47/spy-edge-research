# Mod 03: Multi-Instrument Research

## Module Name

```text
Multi-Instrument Research
```

## Purpose

This is the implementation prompt for the Mod 03 chat.

Mod 03 should complete the next natural project module after the completed Research Governance Module.

The module extends the project from single-instrument SPY research into causal, auditable, multi-instrument ETF context without creating trading signals, broker integrations, live execution, paper trading, options logic, or trade-readiness claims.

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

- Completed through Milestone 57.
- Milestones 54-57 completed the Research Governance Module.
- Latest full-suite baseline: `607 passed, 4 skipped`.
- The 4 skipped tests are optional matplotlib visualization tests.
- No Milestone 58+ module has been implemented yet.

Run tests with:

```bash
.venv/bin/python -m pytest -q
```

## Module Boundary

Implement Milestones 58-61 as one cohesive module:

```text
Milestone 58: Instrument Registry Foundation
Milestone 59: Multi-Symbol Data Alignment
Milestone 60: Cross-Instrument Confirmation Features
Milestone 61: Multi-Instrument Event Outcome Studies
```

Stop after Milestone 61. Do not continue to sector rotation, macro regimes, factor allocation, value research, service APIs, dashboards, paper trading, broker integration, options, or execution unless explicitly instructed in a later module.

## Why This Module Is Next

The completed project already has:

- causal SPY feature/event foundations
- named event catalogs
- forward outcome labels
- event/sequence/conditional studies
- OOS validation
- robustness and placebo diagnostics
- research rule objects
- governance, traceability, manifest, and artifact integrity infrastructure

The next natural research expansion is to add multi-instrument context so SPY hypotheses can be studied alongside index ETF confirmation and divergence conditions.

This corresponds to the master architecture's multi-instrument expansion layer while staying firmly research-only.

## Milestone 58: Instrument Registry Foundation

Goal:

Define a typed, deterministic registry for research instruments.

Likely module:

```text
src/spy_edge_research/instruments/instrument_registry.py
```

Likely tests:

```text
tests/instruments/test_instrument_registry.py
```

Expected public dataclasses/functions:

- `InstrumentDefinition`
- `InstrumentRegistry`
- `create_instrument_definition`
- `build_instrument_registry`
- `validate_instrument_registry`
- `get_instrument_definition`
- `list_instruments`
- `filter_instruments_by_role`
- `write_instrument_registry`
- `read_instrument_registry`

Expected instrument metadata:

- symbol
- name
- asset class
- role, such as `primary`, `index_confirmation`, `sector_context`, `macro_context`, `factor_context`
- market/session
- timezone
- optional notes
- optional metadata

Requirements:

- Include default examples for SPY, QQQ, DIA, IWM if useful.
- Keep registry deterministic and JSON-serializable.
- Reject duplicate symbols.
- Do not require market-data downloads.
- Do not imply tradability or execution support.

## Milestone 59: Multi-Symbol Data Alignment

Goal:

Align already-loaded OHLCV/feature DataFrames across symbols on timestamp/session keys.

Likely module:

```text
src/spy_edge_research/market_data/multi_symbol_alignment.py
```

Likely tests:

```text
tests/market_data/test_multi_symbol_alignment.py
```

Expected public functions:

- `validate_symbol_frame_map`
- `prefix_symbol_columns`
- `align_symbol_frames`
- `build_multi_symbol_panel`
- `summarize_symbol_alignment`
- `filter_aligned_symbol_universe`

Requirements:

- Inputs are in-memory DataFrames supplied by the caller.
- No network calls.
- No paid data dependencies.
- Preserve causal row ordering.
- Support inner and outer timestamp joins.
- Prefix non-key columns by symbol to avoid collisions.
- Surface missing symbol/timestamp coverage as diagnostics.
- Do not forward-fill by default.
- If fill behavior is supported, make it explicit and caveated.

## Milestone 60: Cross-Instrument Confirmation Features

Goal:

Create causal cross-instrument confirmation/divergence features from aligned multi-symbol data.

Likely module:

```text
src/spy_edge_research/signal_engine/cross_instrument_features.py
```

Likely tests:

```text
tests/signal_engine/test_cross_instrument_features.py
```

Expected public functions:

- `add_relative_return_features`
- `add_cross_symbol_trend_confirmation`
- `add_cross_symbol_vwap_confirmation`
- `add_cross_symbol_volume_confirmation`
- `add_cross_symbol_divergence_flags`
- `add_cross_instrument_confirmation_features`

Requirements:

- All features must be causal at the current row.
- Use current and prior values only.
- No future returns or forward labels.
- Avoid hard-coded SPY-only assumptions where possible.
- Support configurable primary symbol and confirmation symbols.
- Output columns must avoid buy/sell/signal/approval language.
- Missing comparison columns should produce clear errors or explicit diagnostics.

Example research questions:

- Is SPY continuation stronger when QQQ and IWM confirm direction?
- Does SPY event performance weaken when IWM diverges?
- Does index confirmation matter more during high-volume windows?

## Milestone 61: Multi-Instrument Event Outcome Studies

Goal:

Evaluate existing SPY events/outcomes conditioned on cross-instrument context features.

Likely module:

```text
src/spy_edge_research/backtesting/multi_instrument_event_study.py
```

Likely tests:

```text
tests/backtesting/test_multi_instrument_event_study.py
```

Expected public functions:

- `summarize_event_by_instrument_context`
- `compare_confirmed_vs_divergent_event_outcomes`
- `build_multi_instrument_event_outcome_table`
- `summarize_multi_instrument_context_coverage`
- `build_multi_instrument_research_report`

Requirements:

- Consume existing event columns, outcome columns, and cross-instrument context columns.
- Forward outcomes remain evaluation-only.
- Include sample sizes and low-sample caveats.
- Include context coverage diagnostics.
- Compare confirmed/divergent/neutral groups descriptively.
- Do not claim edge, rank strategies for deployment, optimize thresholds, create signals, or simulate P/L.

## Required Package Updates

Add package exports only where consistent with existing style:

- `src/spy_edge_research/instruments/__init__.py`
- `src/spy_edge_research/market_data/__init__.py`
- `src/spy_edge_research/signal_engine/__init__.py`
- `src/spy_edge_research/backtesting/__init__.py`

If `src/spy_edge_research/instruments/` does not exist, create it with an `__init__.py`.

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
- strategy recommendations
- buy/sell/entry/exit instructions
- confidence scores
- trade-readiness claims
- P/L simulation
- portfolio construction
- sector rotation
- macro regime modules
- factor allocation modules
- value research modules

## Acceptance Criteria

Mod 03 is complete when:

- Milestones 58-61 are implemented sequentially.
- Each milestone has focused tests.
- Public helpers are exported consistently.
- README is updated.
- `PROJECT_MILESTONES.md` is updated with all milestone details.
- Full suite passes from the unified root.
- Outputs stay research-only and causal.
- No execution, recommendation, broker, options, paper-trading, or trade-readiness behavior is introduced.
- The final response recommends the next module boundary but does not begin it.

## Copy-Paste Prompt For Mod 03 Chat

```text
You are the Mod 03 implementation chat for the SPY Directional Edge Research project.

Module name:
Multi-Instrument Research

Authoritative repo:
/Users/johnmullen/Documents/Codex/Auto-Trader SPY

Read first:
- CODEX_MASTER_DESK.md
- MASTER_PROJECT_BRIEF.md
- PROJECT_MILESTONES.md
- README.md

Current verified state:
- Completed through Milestone 57.
- Milestones 54-57 completed the Research Governance Module.
- Latest full-suite baseline: 607 passed, 4 skipped.
- The 4 skipped tests are optional matplotlib visualization tests.
- Use .venv/bin/python -m pytest -q for tests.

Implement Milestones 58-61 sequentially as one cohesive module:

Milestone 58: Instrument Registry Foundation
- Add a deterministic, JSON-serializable instrument registry.
- Likely module: src/spy_edge_research/instruments/instrument_registry.py
- Likely tests: tests/instruments/test_instrument_registry.py
- Include InstrumentDefinition, InstrumentRegistry, registry build/validate/list/filter/get/write/read helpers.
- Reject duplicate symbols.
- Do not download data or imply tradability.

Milestone 59: Multi-Symbol Data Alignment
- Align already-loaded symbol DataFrames on timestamp/session keys.
- Likely module: src/spy_edge_research/market_data/multi_symbol_alignment.py
- Likely tests: tests/market_data/test_multi_symbol_alignment.py
- Include validation, column prefixing, aligned panel construction, coverage summaries, and universe filtering.
- No network calls, no paid data dependencies, no default forward-fill.

Milestone 60: Cross-Instrument Confirmation Features
- Add causal cross-symbol confirmation/divergence features from aligned data.
- Likely module: src/spy_edge_research/signal_engine/cross_instrument_features.py
- Likely tests: tests/signal_engine/test_cross_instrument_features.py
- Include relative returns, trend confirmation, VWAP confirmation, volume confirmation, divergence flags, and combined helper.
- Use only current/prior data. No future labels. No buy/sell/signal/approval language.

Milestone 61: Multi-Instrument Event Outcome Studies
- Evaluate existing SPY events/outcomes conditioned on cross-instrument context.
- Likely module: src/spy_edge_research/backtesting/multi_instrument_event_study.py
- Likely tests: tests/backtesting/test_multi_instrument_event_study.py
- Include event-by-context summaries, confirmed-vs-divergent comparisons, outcome tables, coverage summaries, and a report builder.
- Forward outcomes remain evaluation-only. Include sample-size and coverage caveats. Do not claim edge.

Package/doc updates:
- Create src/spy_edge_research/instruments/__init__.py if needed.
- Update relevant __init__.py exports consistently with existing style.
- Update README.md.
- Update PROJECT_MILESTONES.md after each milestone or at the end with complete details.

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
- no buy/sell/entry/exit instructions
- no confidence scores
- no trade-readiness claims
- no P/L simulation
- no portfolio construction

Stop after Milestone 61. Do not start the next module. In the final response, summarize files added/modified, public APIs, tests run, exact final test result, causal-safety notes, and the recommended next module boundary.
```
