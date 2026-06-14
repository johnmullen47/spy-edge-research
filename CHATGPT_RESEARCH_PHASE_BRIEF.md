# ChatGPT Research Phase Brief

## Purpose

This brief explains how the ChatGPT research phase should understand the current Codex implementation of the master project prompt.

The project is being interpreted as:

```text
SPY Directional Edge Research -> Multi-Thesis Quant + Value Research Platform
```

The active implementation is not a trading bot, not an AI stock picker, and not
an options assistant. It is a research-first platform for testing whether
observable SPY intraday conditions show repeatable short-term directional edge.
Broker sandbox/live-adapter code now exists, but it is gated, inert, and
unauthorized for use while Hard Gate A remains negative.

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

This ordering intentionally slowed down before execution-like surfaces. Later
work added paper simulation, human-in-the-loop decision support, and broker/live
adapter scaffolding under explicit staged gates. The empirical hard gate remains
negative, so those layers stay off.

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

The project currently records completed milestones through Milestone 107.

The most recently completed hardening sequence is:

```text
M101-M107 staged Trader module hardening
```

This sequence covers:

- M101: control batteries wired into the pipeline runner.
- M102: human-in-the-loop decision support records.
- M103: Alpaca paper/sandbox broker preparation.
- M104: inert live adapter behind explicit gates.
- M105: economic-significance cost-floor readiness criterion.
- M106: per-candidate permutation p-values and FDR.
- M107: slippage separated from costs in the execution model.

Latest verified test baseline:

```text
844 passed, 4 skipped
```

The skipped tests are optional matplotlib visualization tests.

Hard Gate A has run on real SPY 1-minute data. The current candidate set has:

```text
0 of 42 candidates eligible
```

Therefore there is no validated intraday edge in the current candidate set, and
broker/live layers remain off.

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
- Decision-support records authorize nothing.
- Broker/live paths must remain gated and inert while no candidate clears Hard Gate A.

Codex should now operate as the project Master Desk by default: maintain the
roadmap, generate precise implementation briefs, review outputs for drift, and
protect architecture. Codex should write code only when explicitly asked to
implement an approved milestone or module.

## Non-Negotiable Boundaries

Do not ask Codex to implement these during the current research phase:

- Options selection or options execution.
- Autonomous trading.
- Buy/sell alerts.
- Trade recommendations.
- Real-money portfolio automation.
- Any live deployment while Hard Gate A remains negative.

Broker/live scaffolding exists only under explicit gates:

- Hard Gate A must find a validated eligible edge.
- The user must authorize deployment.
- `SPY_EDGE_ALLOW_LIVE=1` must be set.
- Every order must have a matching per-order human approval token.
- Limits and kill-switch checks must pass.

Also avoid:

- Robinhood integration.
- LLM trade decision engines.
- Dashboards that imply current trade instructions.

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

Use ChatGPT to decide whether the next research move should expand the
hypothesis space, test longer horizons, explore other instruments, improve
slippage modeling, or accept the efficient-market/null interpretation for the
current intraday SPY candidate set.

Useful questions:

- Is there a richer hypothesis space worth testing after Hard Gate A rejected all 42 candidates?
- Should the project explore longer horizons or non-SPY instruments?
- What would a dynamic volatility/volume-scaled slippage model require?
- What would falsify the next candidate family?
- What evidence would justify keeping the staged broker layers at all?
- What documentation should explain the current no-edge result?

## Handoff Summary

Codex has implemented the master brief as a conservative, research-first,
evidence-governance platform with staged, gated trader scaffolding.

The project is complete through Milestone 107.

The project should now reassess whether new research hypotheses are worthwhile
given the negative Hard Gate A result, rather than automatically progressing
toward execution or productization.
