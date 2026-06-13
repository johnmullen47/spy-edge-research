# ChatGPT Research Phase Brief

## Purpose

This brief explains how the ChatGPT research phase should understand the current Codex implementation of the master project prompt.

The project is being interpreted as:

```text
SPY Directional Edge Research -> Multi-Thesis Quant + Value Research Platform
```

The active implementation is not a trading bot, not an AI stock picker, not an options assistant, and not a broker automation project. It is a research-first platform for testing whether observable SPY intraday conditions show repeatable short-term directional edge.

## Current Project Interpretation

Codex has interpreted the master brief as a mandate to build the research infrastructure before building any product or execution surface.

The implementation priority has been:

1. Causal data and feature foundations.
2. Named event detection and event catalogs.
3. Forward outcome labels strictly as evaluation targets.
4. Conditional event studies and sequence studies.
5. Statistical skepticism, multiple-testing warnings, placebo controls, and temporal stability.
6. Out-of-sample validation and robustness reporting.
7. Research-only candidate/rule objects.
8. Audit, reproducibility, lineage, maturity, manifest, and governance workflows.

This ordering intentionally slows down before trade simulation, paper trading, dashboards, broker integration, or options logic.

## Authoritative Implementation State

The unified project root is:

```text
/Users/johnmullen/Documents/Codex/Auto-Trader SPY
```

Authoritative files:

- `MASTER_PROJECT_BRIEF.md`
- `PROJECT_MILESTONES.md`
- `README.md`
- `V2_RESUME_BRIEF.md`
- `CODEX_MASTER_DESK.md`
- `src/spy_edge_research/`
- `tests/`

The project currently records completed milestones through Milestone 57.

The most recently completed module is:

```text
Research Governance Module
```

This module covers Milestones 54-57:

- Milestone 54: Research Review Artifact Integrity Checks.
- Milestone 55: Research Package Comparison Reports.
- Milestone 56: Research Evidence Traceability Matrix.
- Milestone 57: Research Governance Summary Bundle.

Latest verified test baseline:

```text
607 passed, 4 skipped
```

The skipped tests are optional matplotlib visualization tests.

## How Codex Has Applied The Master Brief

Codex has treated the master prompt as a scope-control document, not just a feature roadmap.

That means:

- Research outputs must be auditable and reproducible.
- Every new public module/function should have focused tests.
- README and milestone docs should be updated after each milestone.
- Forward-looking data is allowed only in explicitly named outcome/evaluation columns.
- Causal feature generation must not import or depend on outcome-study modules.
- Positive diagnostics must not be framed as proof of edge.
- Maturity, rank, score, and comparison language must not imply trade readiness.
- Candidate rule objects are research artifacts, not executable strategy rules.

Codex should now operate as the project Master Desk by default: maintain the
roadmap, generate precise implementation briefs, review outputs for drift, and
protect architecture. Codex should write code only when explicitly asked to
implement an approved milestone or module.

## Non-Negotiable Boundaries

Do not ask Codex to implement these during the current research phase:

- Live trading.
- Broker integration.
- Order routing.
- Robinhood integration.
- Options selection or options execution.
- Buy/sell alerts.
- LLM trade decision engines.
- Trade recommendations.
- Paper trading unless explicitly authorized by a later milestone.
- Dashboards that imply current trade instructions.
- Real-money portfolio automation.

The system should be able to conclude:

```text
No valid trade.
Evidence insufficient.
Current regime invalid.
Risk overlap too high.
Strategy failed kill criteria.
```

A no-trade or no-edge conclusion is considered a successful research outcome.

## Research Phase Guidance For ChatGPT

When using ChatGPT as the research-planning layer, frame requests around:

- What hypothesis should be tested next?
- What evidence would falsify the hypothesis?
- What causal data would be needed?
- What audit trail should exist?
- What caveats must be surfaced?
- What would make a result non-reproducible?
- What could create lookahead bias?
- What would constitute overfitting or data mining?
- What should be killed, retired, or merged?

Avoid framing requests as:

- What should I buy?
- What is the best trade?
- What option contract should I use?
- How do we automate execution?
- How do we connect to a broker?
- How do we make this live?

## Current Research Meaning Of Progress

Progress is not measured by moving closer to live trading.

Progress is measured by whether the system can more honestly answer:

```text
Does SPY show a repeatable, statistically defensible, short-term directional edge under specific observable conditions?
```

The current implementation is building toward that answer by strengthening:

- evidence integrity
- reproducibility
- traceability
- negative controls
- out-of-sample review
- robustness diagnostics
- caveat preservation
- research governance

## Recommended Next ChatGPT Research Use

Use ChatGPT to review whether the completed Research Governance Module is sufficient before any later module begins.

Useful questions:

- Are Milestones 54-57 enough to close the governance layer?
- What integrity failures should Milestone 54 catch?
- What package comparisons are useful without creating "best strategy" language?
- What should a traceability matrix include to make every research claim auditable?
- What governance bundle would make weak evidence impossible to hide?
- What should be required before the project considers trade simulation or paper trading readiness?

## Handoff Summary

Codex has implemented the master brief as a conservative, research-first, evidence-governance platform.

The Research Governance Module is now complete through Milestone 57.

The project should now reassess whether the research foundation is strong enough to justify the next module, rather than automatically progressing toward execution or productization.
