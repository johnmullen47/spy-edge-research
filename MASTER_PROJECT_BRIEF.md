# Master Project Brief

## Project Identity

Auto-Trader SPY should be treated as the local continuation of the broader research program:

```text
SPY Directional Edge Research -> Multi-Thesis Quant + Value Research Platform
```

The long-term goal is to build a research-grade, causal, auditable trading research platform that begins with SPY intraday directional edge research and gradually expands into multi-instrument, sector, macro, factor, value, risk, paper-trading, and human-approved decision-support workflows.

This is not a generic AI stock picker, a live trading bot, an options gambling assistant, or a broker automation script. It is a research-first validation engine.

## Current Repository Status

This repository is now the unified authoritative project folder. The recovered
package-style milestone repository has been copied into this root:

```text
src/spy_edge_research/
tests/
PROJECT_MILESTONES.md
README.md
pyproject.toml
```

The former flat `Auto-Trader SPY` scaffold has been preserved for reference
under:

```text
legacy_auto_trader_spy_scaffold/
```

Future development should use the package in `src/spy_edge_research`, the
tests in `tests`, and the milestone ledger in `PROJECT_MILESTONES.md`.

The original compact event-transformation scaffold is no longer authoritative,
but it remains archived rather than deleted.

The project currently records completed milestones through Milestone 69.
Milestones 62-65 completed the Sector Context Research Module. Milestones
66-69 completed the Macro Regime Research Module.

## Codex Master Desk Role

Codex should operate as the project Master Desk unless the user explicitly asks
for implementation.

Default responsibilities:

- Maintain the milestone roadmap.
- Generate one implementation brief or module brief at a time.
- Include exact scope, likely files, expected tests, acceptance criteria, and non-goals.
- Review Codex outputs for drift, missing tests, weak abstractions, lookahead risk, and hidden complexity.
- Protect architecture, causality, auditability, and research-only boundaries.
- Produce the next milestone/module brief only after the prior milestone/module is summarized and verified.

Codex may still write code when explicitly asked, but governance, briefing,
review, and drift prevention are the default posture for this project.

## Long-Term Vision

The platform should eventually support:

1. SPY intraday directional edge research.
2. Multi-index ETF research.
3. Sector ETF confirmation and rotation research.
4. Macro, rates, credit, and commodity regime filtering.
5. Factor ETF allocation research.
6. Systematic value, quality, and momentum research.
7. Portfolio-level exposure and risk controls.
8. Paper-trading validation.
9. Human-approved semi-autonomous trade decision support.
10. Broker integration, live execution, and options expression layers only after prerequisite research validation exists.

## Non-Negotiable Constraints

Do not implement any of the following until explicitly allowed by a later milestone:

- Options trading or options chain selection.
- Robinhood or broker API integration.
- Live order execution or live order routing.
- Automatic trading.
- Alerts that imply trade instructions.
- Buy-now or sell-now dashboards.
- LLM-based trade decision engines.
- Screenshot-based trading.
- Discretionary chatbot stock picking.
- Portfolio auto-rebalancing with real money.
- Real-time production deployment.

The system should be comfortable producing outputs such as:

```text
No valid trade.
Evidence insufficient.
Current regime invalid.
Risk overlap too high.
Strategy failed kill criteria.
```

A no-trade result is a valid and often desirable result.

## Causal And No-Lookahead Rules

All features, events, labels, and backtests must be causal.

- Never use future rows to create current-row signals.
- Forward outcome labels may look forward only as labels or outcomes, never as features.
- Confirmed pivots, support/resistance, retests, false breaks, trend continuation events, and named events must not be backdated unless explicitly encoded as known-late confirmation metadata.
- Rolling windows must use only information available at the row being computed.
- Full-day high/low, full-session statistics, and future bars must not leak into current-row features.

## Target Architecture

The platform should evolve through these layers:

```text
Layer 1: Data ingestion and normalization
Layer 2: Feature generation
Layer 3: Causal event detection
Layer 4: Named event registry
Layer 5: Forward outcome labeling
Layer 6: Regime classification
Layer 7: Conditional edge analysis
Layer 8: Trade simulation
Layer 9: Strategy candidate registry
Layer 10: Walk-forward validation
Layer 11: Multi-instrument expansion
Layer 12: Sector / macro / factor context
Layer 13: Value / quality / momentum research
Layer 14: Portfolio exposure and risk
Layer 15: Research reports and dashboards
Layer 16: Paper trading
Layer 17: Human-approved semi-autonomous workflow
Layer 18: Broker integration
Layer 19: Options expression layer
```

Later layers should only be implemented after earlier layers are stable, tested, and documented.

## Current Core Data Contracts

### Wide Causal Feature Dataframe

One row per timestamp and one column per causal feature. The timestamp may be a dataframe index or a dedicated timestamp column.

### Event Catalog

Maps raw feature columns to named events and display metadata.

Required fields:

- `feature`
- `event_name`
- `label`
- `threshold`
- `direction`

Optional fields:

- `side`
- `color`
- `marker`
- `metadata`

### Event Tape

One row per triggered event, typically including:

- `timestamp`
- `event_name`
- `label`
- `feature`
- `value`
- `side`
- `color`
- `marker`
- `metadata`

### Chart Annotations

Display-ready records for plotting layers, typically including:

- `x`
- `id`
- `text`
- `y`, when a price lookup is supplied
- `side`
- `color`
- `marker`
- `feature`
- `value`
- `metadata`

## Trigger Semantics

Current event trigger directions:

- `nonzero`
- `truthy`
- `above`
- `at_or_above`
- `below`
- `at_or_below`

Threshold-based directions require a threshold value.

## Development Protocol

For each Codex session:

1. Inspect the repository structure.
2. Read `README.md` and this master brief.
3. Identify the latest completed milestone or current repository baseline.
4. Run the existing test suite before substantial changes.
5. Implement only the next logical milestone unless explicitly asked to continue further.
6. Preserve existing public behavior unless a milestone requires an extension.
7. Add or update focused tests for every public function and module.
8. Run relevant tests, and run the full suite when practical.
9. Update `README.md` after each milestone.
10. Summarize files touched, public APIs added, tests run, and known limitations.

Do not skip tests. Do not silently alter existing behavior. If blocked by missing data, paid services, credentials, ambiguous product decisions, or destructive actions, stop and explain the blocker.

## Testing Rules

- Every new public function requires tests.
- Every new module requires at least one focused test file.
- Prefer deterministic, lightweight synthetic fixtures.
- Avoid network calls in tests.
- Avoid requiring paid market data in tests.
- Use small synthetic OHLCV DataFrames for unit tests.
- Keep optional plotting dependencies isolated and skipped gracefully when unavailable.

## Documentation Rules

Update `README.md` after each milestone with:

- What was added.
- Why it matters.
- Public functions and classes.
- Example usage when appropriate.
- Limitations and non-goals.

Use docstrings and type hints where helpful.

## Design Rules

- Prefer small composable modules over monolithic files.
- Prefer explicit configs over hidden assumptions.
- Prefer pure functions where practical.
- Prefer dataclasses for typed records and configs.
- Prefer pandas DataFrames for research-table operations.
- Keep all research outputs auditable and reproducible.
- Optimize only after correctness.

## Preferred Package Structure Over Time

The target package layout is:

```text
src/spy_edge_research/
  data/
  indicators/
  signal_engine/
  backtesting/
  reporting/
  instruments/
  risk/
  fundamentals/
  services/
  dashboard/
  paper/
  decision_support/
  broker/
  options/
  config/
```

Keep the existing structure where possible. Do not reorganize aggressively unless necessary for the active milestone.

## Roadmap Summary

This unified folder is the current source of truth for milestone progress:

```text
/Users/johnmullen/Documents/Codex/Auto-Trader SPY
```

Verified from other project chats and `PROJECT_MILESTONES.md`:

- Milestone 22 is not the most recently accomplished milestone.
- Milestones 1-69 are recorded as completed.
- The latest verified full-suite result is `674 passed, 4 skipped`.
- Milestones 62-65 completed the Sector Context Research Module.
- Milestones 66-69 completed the Macro Regime Research Module.

Before implementing roadmap work, inspect this root folder and use
`PROJECT_MILESTONES.md` here as the progress ledger.

Next major planned phases:

- Phase 2A: Convert event engine into edge measurement engine.
- Phase 2B: Research reports and audit outputs.
- Phase 3: Multi-instrument ETF research foundation.
- Phase 4: Sector ETF confirmation and rotation.
- Phase 5: Macro / rates / credit / commodity regime layer.
- Phase 6: Portfolio-level risk and exposure controls.
- Phase 7: Factor ETF and swing allocation research.
- Phase 8: Systematic value / quality / momentum research.
- Phase 9: Research API and local app backend.
- Phase 10: Frontend-ready research dashboard.
- Phase 11: Paper trading simulation layer.
- Phase 12: Human-approved semi-autonomous workflow.
- Phase 13: Broker integration preparation.
- Phase 14: Real broker integration.
- Phase 15: Options expression layer.
- Phase 16: Production hardening.

## Immediate Research Roadmap

The immediate next implementation module is Macro Regime Research, Milestones
66-69.

This module must remain research-only. It must not imply trade readiness,
create signals, optimize thresholds, simulate P/L, or connect to brokers.

## Success Criteria

The project is successful when it can:

- Generate causal SPY features and named event rows.
- Label forward outcomes without feature leakage.
- Measure event edge by horizon, direction, and market regime.
- Simulate candidate trade rules with explicit assumptions.
- Validate candidates through time-ordered walk-forward research.
- Kill weak strategies before they reach decision support.
- Produce reproducible research reports and audit artifacts.
- Support human-approved decisions only after research evidence exists.
