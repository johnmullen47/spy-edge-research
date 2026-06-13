# Mod 05: Macro Regime Research

## Module Name

```text
Macro Regime Research
```

## Purpose

This is the implementation prompt for the Mod 05 chat.

Mod 05 should complete the next natural project module after the completed Sector Context Research Module.

The module extends the project from sector ETF context into macro, rates, credit, commodity, and risk-on/risk-off regime research. It should help answer whether SPY event outcomes vary under broader market regime conditions.

This is still research infrastructure. It must not create trading signals, macro allocation recommendations, broker integrations, live execution, paper trading, options logic, alerts, or trade-readiness claims.

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

- Completed through Milestone 65.
- Milestones 62-65 completed the Sector Context Research Module.
- Latest full-suite baseline: `651 passed, 4 skipped`.
- The 4 skipped tests are optional matplotlib visualization tests.
- Mod 05 is approved as Milestones 66-69.

Run tests with:

```bash
.venv/bin/python -m pytest -q
```

## Module Boundary

Implement Milestones 66-69 as one cohesive module:

```text
Milestone 66: Macro Instrument Universe
Milestone 67: Macro Regime Feature Layer
Milestone 68: Macro-Conditioned Event Studies
Milestone 69: Macro Regime Research Reports
```

Stop after Milestone 69. Do not continue to factor allocation, value research, portfolio construction, service APIs, dashboards, paper trading, broker integration, options, alerts, execution, or trade-readiness work unless explicitly instructed in a later module.

## Why This Module Is Next

The completed project already has:

- causal SPY feature/event foundations
- multi-instrument context research
- sector ETF universe/context/reports
- event, sequence, conditional, OOS, robustness, placebo, governance, and traceability infrastructure

The next natural research expansion is macro/rates/credit/commodity regime context. This follows the master architecture's macro regime layer while keeping all outputs descriptive, auditable, and non-execution.

## Milestone 66: Macro Instrument Universe

Goal:

Define a deterministic universe of macro, rates, credit, commodity, volatility, and risk proxy instruments for research metadata and grouping.

Likely module:

```text
src/spy_edge_research/instruments/macro_universe.py
```

Likely tests:

```text
tests/instruments/test_macro_universe.py
```

Expected public dataclasses/functions:

- `MacroInstrumentDefinition`
- `MacroInstrumentUniverse`
- `create_macro_instrument_definition`
- `build_macro_instrument_universe`
- `default_macro_instrument_universe`
- `validate_macro_instrument_universe`
- `get_macro_instrument_definition`
- `list_macro_instruments`
- `filter_macro_instruments`
- `write_macro_instrument_universe`
- `read_macro_instrument_universe`

Expected metadata:

- symbol
- name
- macro group, such as `rates`, `credit`, `commodity`, `volatility`, `currency`, `risk_proxy`
- role, such as `risk_on`, `risk_off`, `inflation_proxy`, `duration_proxy`, `credit_stress_proxy`
- market/session
- timezone
- optional benchmark symbol
- optional notes
- optional metadata

Requirements:

- Include deterministic defaults for common research proxies if useful, such as TLT, IEF, HYG, LQD, GLD, USO, UUP, VIXY, and VXX.
- Keep records JSON-serializable.
- Reject duplicate symbols.
- Do not require market-data downloads.
- Do not imply tradability, allocation, broker support, or execution support.

## Milestone 67: Macro Regime Feature Layer

Goal:

Create causal macro/rates/credit/commodity regime features from already-aligned macro instrument data.

Likely module:

```text
src/spy_edge_research/signal_engine/macro_regime_features.py
```

Likely tests:

```text
tests/signal_engine/test_macro_regime_features.py
```

Expected public functions:

- `add_macro_relative_return_features`
- `add_rates_regime_features`
- `add_credit_regime_features`
- `add_commodity_regime_features`
- `add_volatility_proxy_regime_features`
- `add_risk_on_risk_off_features`
- `add_macro_regime_features`

Requirements:

- Inputs are already-loaded/aligned DataFrames.
- Use only current and prior row information.
- No future returns or forward labels.
- Support configurable primary symbol, macro symbols, and lookback windows.
- Regime outputs should be descriptive, such as rates-up/down, credit-risk-on/off, commodity-up/down, volatility-proxy-up/down, risk-on/risk-off/mixed.
- Output columns must avoid buy/sell/entry/exit/signal/approval language.
- Missing macro columns should produce clear validation errors or explicit diagnostics.

Example research questions:

- Do SPY continuation events differ when credit risk proxies confirm risk-on?
- Does SPY event quality weaken when long-duration bonds rally sharply?
- Are SPY events less reliable when volatility proxies rise?
- Do commodity/inflation proxy moves change sector-confirmed SPY behavior?

## Milestone 68: Macro-Conditioned Event Studies

Goal:

Evaluate existing SPY events and forward outcome columns conditioned on macro regime features.

Likely module:

```text
src/spy_edge_research/backtesting/macro_event_study.py
```

Likely tests:

```text
tests/backtesting/test_macro_event_study.py
```

Expected public functions:

- `summarize_event_by_macro_regime`
- `compare_macro_regime_event_outcomes`
- `build_macro_event_outcome_table`
- `summarize_macro_context_coverage`
- `build_macro_event_research_report`

Requirements:

- Consume existing event columns, forward outcome columns, and macro regime context columns.
- Forward outcomes remain evaluation-only.
- Include sample sizes and low-sample caveats.
- Include macro context coverage diagnostics.
- Compare risk-on, risk-off, mixed, rates-up/down, credit-risk-on/off, commodity-up/down, and volatility-proxy-up/down groups descriptively where inputs support it.
- Do not claim edge, rank strategies for deployment, optimize thresholds, create signals, or simulate P/L.

## Milestone 69: Macro Regime Research Reports

Goal:

Package macro regime snapshots, macro-conditioned event summaries, coverage diagnostics, and caveats into deterministic research report bundles.

Likely module:

```text
src/spy_edge_research/backtesting/macro_regime_reports.py
```

Likely tests:

```text
tests/backtesting/test_macro_regime_reports.py
```

Expected public functions:

- `create_macro_regime_report_metadata`
- `build_macro_regime_snapshot`
- `summarize_macro_regime_persistence`
- `build_macro_regime_report_bundle`
- `validate_macro_regime_report_bundle`
- `summarize_macro_regime_report_bundle`
- `export_macro_regime_report_bundle_to_csv`
- `export_macro_regime_report_bundle_to_json`

Requirements:

- Treat macro regimes as descriptive research context only.
- Do not create allocation recommendations.
- Do not rank instruments as buys/sells.
- Do not imply portfolio construction.
- Preserve caveats about sample size, coverage, proxy interpretation, and descriptive-only use.
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
- macro allocation recommendations
- macro instrument buy/sell rankings
- portfolio construction
- strategy recommendations
- buy/sell/entry/exit instructions
- confidence scores
- trade-readiness claims
- P/L simulation
- factor allocation modules
- value research modules
- service API modules

## Acceptance Criteria

Mod 05 is complete when:

- Milestones 66-69 are implemented sequentially.
- Each milestone has focused tests.
- Public helpers are exported consistently.
- README is updated.
- `PROJECT_MILESTONES.md` is updated with all milestone details.
- Full suite passes from the unified root.
- Outputs stay research-only and causal.
- Macro/rates/credit/commodity language remains descriptive and non-recommendational.
- No execution, recommendation, broker, options, paper-trading, portfolio-construction, or trade-readiness behavior is introduced.
- The final response recommends the next module boundary but does not begin it.

## Copy-Paste Prompt For Mod 05 Chat

```text
You are the Mod 05 implementation chat for the SPY Directional Edge Research project.

Module name:
Macro Regime Research

Authoritative repo:
/Users/johnmullen/Documents/Codex/Auto-Trader SPY

Read first:
- CODEX_MASTER_DESK.md
- MASTER_PROJECT_BRIEF.md
- PROJECT_MILESTONES.md
- README.md

Current verified state:
- Completed through Milestone 65.
- Milestones 62-65 completed the Sector Context Research Module.
- Latest full-suite baseline: 651 passed, 4 skipped.
- The 4 skipped tests are optional matplotlib visualization tests.
- Use .venv/bin/python -m pytest -q for tests.

Implement Milestones 66-69 sequentially as one cohesive module:

Milestone 66: Macro Instrument Universe
- Add a deterministic, JSON-serializable macro/rates/credit/commodity/volatility research proxy universe.
- Likely module: src/spy_edge_research/instruments/macro_universe.py
- Likely tests: tests/instruments/test_macro_universe.py
- Include MacroInstrumentDefinition, MacroInstrumentUniverse, create/build/default/validate/get/list/filter/write/read helpers.
- Include deterministic defaults for common research proxies if useful, such as TLT, IEF, HYG, LQD, GLD, USO, UUP, VIXY, and VXX.
- Reject duplicate symbols.
- Do not download data or imply tradability, allocation, broker support, or execution.

Milestone 67: Macro Regime Feature Layer
- Add causal macro, rates, credit, commodity, volatility-proxy, and risk-on/risk-off context features.
- Likely module: src/spy_edge_research/signal_engine/macro_regime_features.py
- Likely tests: tests/signal_engine/test_macro_regime_features.py
- Inputs are already-loaded/aligned DataFrames.
- Use only current/prior row information.
- No future labels.
- No buy/sell/entry/exit/signal/approval language.

Milestone 68: Macro-Conditioned Event Studies
- Evaluate existing SPY events/outcomes conditioned on macro regime context features.
- Likely module: src/spy_edge_research/backtesting/macro_event_study.py
- Likely tests: tests/backtesting/test_macro_event_study.py
- Include event-by-macro-regime summaries, risk-on/risk-off comparisons, outcome tables, coverage summaries, and a report builder.
- Forward outcomes remain evaluation-only.
- Include sample-size and coverage caveats.
- Do not claim edge, optimize thresholds, create signals, or simulate P/L.

Milestone 69: Macro Regime Research Reports
- Package macro regime snapshots, macro-conditioned event summaries, coverage diagnostics, and caveats into deterministic research report bundles.
- Likely module: src/spy_edge_research/backtesting/macro_regime_reports.py
- Likely tests: tests/backtesting/test_macro_regime_reports.py
- Treat macro regimes as descriptive research context only.
- Do not create allocation recommendations, macro instrument buy/sell rankings, portfolio construction, or trade-readiness claims.

Package/doc updates:
- Update relevant __init__.py exports consistently with existing style.
- Update README.md.
- Update PROJECT_MILESTONES.md with complete details for Milestones 66-69.

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
- no macro allocation recommendations
- no macro instrument buy/sell rankings
- no portfolio construction
- no buy/sell/entry/exit instructions
- no confidence scores
- no trade-readiness claims
- no P/L simulation

Stop after Milestone 69. Do not start the next module. In the final response, summarize files added/modified, public APIs, tests run, exact final test result, causal-safety notes, and the recommended next module boundary.
```
