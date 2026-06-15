# Project Milestones

## Verified Project Status

Repository audited at:

```text
/Users/johnmullen/Documents/Codex/Auto-Trader SPY
```

This directory is now the unified authoritative project folder. The recovered
`src/spy_edge_research` repository was copied into this root, and the former
flat `Auto-Trader SPY` scaffold was archived under:

```text
legacy_auto_trader_spy_scaffold/
```

Future work should use this root folder, its `src/spy_edge_research` package,
its `tests/` suite, and this `PROJECT_MILESTONES.md` ledger as authoritative.

This project now lives on a private GitHub remote:

```text
https://github.com/johnmullen47/spy-edge-research
```

`main` tracks `origin/main`. Pull with `git pull --ff-only origin main` before
starting work and push after merging authorized changes.

## Completed Milestones Inferred From Repo

- Milestone 1: local data loading, OHLCV validation, sessions, causal resampling.
- Milestone 2: causal price-action event primitives.
- Milestone 3: causal indicator foundations.
- Milestone 4: forward close-to-close labels.
- Milestone 5: benchmark baselines and minimal directional evaluation.
- Milestone 6: causal market-structure primitives.
- Milestone 7: support/resistance level and zone features.
- Milestone 8: market-regime context features and diagnostics.
- Milestone 9: retest and false-break event features.
- Milestone 10: named causal event definitions.
- Milestone 11: named event catalog and event-study utilities.
- Milestone 12: event-study diagnostics and quality controls.
- Milestone 13: event-study reporting and export utilities.
- Milestone 14: visualization helpers.
- Milestone 15: event-study workflow helper.
- Milestone 16: artifact manifest and index helpers.
- Milestone 17: run registry and manifest-consumption helpers.
- Milestone 18: registry audit/export helpers.
- Milestone 19: audit index helpers.
- Milestone 20: audit-index report/export and structural comparison helpers.
- Milestone 21: reproducibility checklist helpers.
- Milestone 22: reproducibility report/export helpers.
- Milestone 23: forward path outcome labels.
- Milestone 24: event forward outcome study helpers.
- Milestone 25: conditional event study helpers.
- Milestone 26: causal event sequence foundation.
- Milestone 27: event sequence outcome study helpers.
- Milestone 28: time-of-day research helpers.
- Milestone 29: volatility/range context study helpers.
- Milestone 30: research candidate edge registry.
- Milestone 31: statistical testing foundation.
- Milestone 32: multiple hypothesis risk helpers.
- Milestone 33: walk-forward split foundation.
- Milestone 34: out-of-sample event validation.
- Milestone 35: parameter sensitivity study.
- Milestone 36: robustness report builder.
- Milestone 37: candidate rule object research boundary.
- Milestone 38: candidate rule catalog reporting.
- Milestone 39: rule object evaluation replay.
- Milestone 40: rule object OOS replay comparison.
- Milestone 41: rule object robustness audit.
- Milestone 42: research decision journal.
- Milestone 43: candidate family aggregation.
- Milestone 44: regime-conditioned rule review.
- Milestone 45: negative control and placebo tests.
- Milestone 46: expanded statistical placebo suite.
- Milestone 47: temporal stability diagnostics.
- Milestone 48: data quality and coverage impact review.
- Milestone 49: research risk dashboard bundle.
- Milestone 50: research package maturity scoring.
- Milestone 51: candidate retirement and merge workflow.
- Milestone 52: research package export manifest.
- Milestone 53: end-to-end research review workflow.
- Milestone 54: research review artifact integrity checks.
- Milestone 55: research package comparison reports.
- Milestone 56: research evidence traceability matrix.
- Milestone 57: research governance summary bundle.
- Milestone 58: deterministic research instrument registry foundation.
- Milestone 59: in-memory multi-symbol dataframe alignment helpers.
- Milestone 60: causal cross-instrument confirmation/divergence features.
- Milestone 61: multi-instrument event outcome study helpers.
- Milestone 62: deterministic sector ETF universe foundation.
- Milestone 63: causal sector context feature layer.
- Milestone 64: sector-confirmed event study helpers.
- Milestone 65: descriptive sector rotation research reports.
- Milestone 66: deterministic macro instrument universe foundation.
- Milestone 67: causal macro regime feature layer.
- Milestone 68: macro-conditioned event study helpers.
- Milestone 69: descriptive macro regime research reports.
- Milestone 70: candidate directional exposure.
- Milestone 71: candidate signal-overlap diagnostics.
- Milestone 72: candidate exposure concentration.
- Milestone 73: advisory exposure-limit checks.
- Milestone 74: risk exposure research reports.
- Milestone 75: factor ETF universe foundation.
- Milestone 76: factor context feature layer.
- Milestone 77: factor-conditioned event studies.
- Milestone 78: factor rotation research reports.
- Milestone 79: factor module integration.
- Milestone 80: research artifact access.
- Milestone 81: research query helpers.
- Milestone 82: workflow service facade.
- Milestone 83: optional HTTP layer deferred.
- Milestone 84: service layer integration.
- Milestone 85: dashboard contract schema.
- Milestone 86: dashboard payload export.
- Milestone 87: dashboard export manifest.
- Milestone 88: dashboard module integration.
- Milestone 89: readiness criteria definition.
- Milestone 90: readiness scoring and verdict.
- Milestone 91: readiness scorecard reports.
- Milestone 92: readiness module integration.
- Milestone 93: readiness input assembler.
- Milestone 94: architecture review hardening and DRY foundation.
- Milestone 95: helper migration batch 1.
- Milestone 96: helper migration batch 2.
- Milestone 97: unified CLI / pipeline runner.
- Milestone 98: paper-trading simulation layer.
- Milestone 99: dashboard frontend.
- Milestone 100: value/quality/momentum cross-sectional factor research.
- Milestone 101: control batteries wired into the pipeline runner.
- Milestone 102: decision_support package.
- Milestone 103: broker preparation sandbox.
- Milestone 104: live execution adapter inert unless explicitly enabled.
- Milestone 105: economic-significance readiness criterion.
- Milestone 106: rigorous per-candidate multiple-testing.
- Milestone 107: slippage in the execution model.

## Milestone 23 - Forward Path Outcome Labels

Goal:
Add evaluation-only forward path outcomes for studying what happened after
events beyond close-to-close returns.

Files modified:

- `src/spy_edge_research/backtesting/labels.py`
- `src/spy_edge_research/backtesting/__init__.py`
- `tests/backtesting/test_labels.py`
- `README.md`
- `PROJECT_MILESTONES.md`

Public functions added:

- `add_forward_path_outcome_labels`
- `add_directional_forward_outcome_labels`

Tests added:

- Current bar is excluded from forward high/low path windows.
- Original input frames are not mutated.
- Forward path labels can be prevented from crossing local trading dates.
- Direction-normalized outcomes support long and short event hypotheses.
- Required input columns, horizons, and direction values are validated.

Causal-safety notes:

- These helpers intentionally look forward and therefore produce outcome
  labels only.
- Forward path windows use bars after the current row; the current row is not
  included in MFE/MAE windows.
- Direction-normalized outputs are still labels and must not be used by causal
  feature, event, indicator, or signal generation.

Commands run:

```bash
python3 -m pytest tests/backtesting/test_labels.py -q
'/Users/johnmullen/Documents/Codex/Auto-Trader SPY/.venv/bin/python' -m pytest tests/backtesting/test_labels.py -q
'/Users/johnmullen/Documents/Codex/Auto-Trader SPY/.venv/bin/python' -c '...direct labels smoke test...'
'/Users/johnmullen/Documents/Codex/Auto-Trader SPY/.venv/bin/python' -c '...pytest with datetime.UTC shim...'
'/Users/johnmullen/Documents/Codex/Auto-Trader SPY/.venv/bin/python' -c '...pytest with datetime.UTC and enum.StrEnum shims...'
```

Result:

- `python3` could not run tests because `pytest` is not installed.
- The available `.venv` uses Python 3.9 and cannot import this Python 3.11+
  project directly because package imports use `datetime.UTC` and
  `enum.StrEnum`.
- Direct label-module smoke test passed.
- Focused `tests/backtesting/test_labels.py` passed under a temporary
  `datetime.UTC` compatibility shim: 15 passed.
- Full test suite passed under temporary `datetime.UTC` and `enum.StrEnum`
  compatibility shims: 446 passed, 4 skipped. The skipped tests require
  matplotlib.
- Pytest emitted a cache warning because the recovered repo snapshot was
  outside the writable workspace root before unification.

## Test Command

Use a Python 3.11+ environment with dev dependencies installed:

```bash
python -m pytest -q
```

Local Python 3.11 environment now installed:

```bash
/usr/local/bin/python3.11 --version
.venv/bin/python --version
.venv/bin/python -m pytest -q
```

Verified result after installing the repo-local Python 3.11 venv:

```text
Python 3.11.15
511 passed, 4 skipped
```

Focused Milestone 23 tests:

```bash
python -m pytest tests/backtesting/test_labels.py -q
```

## Milestone 24 - Event Forward Outcome Study

Goal:
Evaluate already-created causal event columns against existing forward
return/path outcome labels with baseline comparison and visible sample-size
warnings.

Files added:

- `src/spy_edge_research/backtesting/event_forward_outcomes.py`
- `tests/backtesting/test_event_forward_outcomes.py`

Files modified:

- `src/spy_edge_research/backtesting/__init__.py`
- `README.md`
- `PROJECT_MILESTONES.md`

Public functions added:

- `calculate_event_sample_size`
- `calculate_event_hit_rate`
- `calculate_event_expectancy`
- `summarize_event_forward_returns`
- `build_event_forward_return_table`
- `compare_event_vs_baseline_forward_returns`

Tests added:

- Event sample size counts event rows with optional valid-outcome filtering.
- Hit rate and expectancy handle missing and empty outcome samples.
- Event outcome summaries include event count, baseline count, event rate,
  expectancy, baseline expectancy, differences, hit rates, and sample flags.
- Small samples and zero-event cases produce explicit `small_sample` or
  `no_events` flags and suppress event-derived summary claims.
- Catalog-driven tables preserve event family and direction metadata.
- Helpers validate missing columns, invalid `min_events`, and invalid hit-rate
  thresholds.
- Output columns do not create trading signal/confidence language.

Causal-safety notes:

- Helpers only read existing event columns and existing outcome columns.
- Outcome columns may be forward-looking because this module is evaluation
  only.
- No event generation, threshold optimization, ranking, significance testing,
  strategy signal creation, P/L simulation, or edge claim is performed.

Commands run:

```bash
'/Users/johnmullen/Documents/Codex/Auto-Trader SPY/.venv/bin/python' -c '...pytest tests/backtesting/test_event_forward_outcomes.py with datetime.UTC and enum.StrEnum shims...'
'/Users/johnmullen/Documents/Codex/Auto-Trader SPY/.venv/bin/python' -c '...pytest tests/backtesting/test_event_study.py tests/backtesting/test_event_forward_outcomes.py with shims...'
'/Users/johnmullen/Documents/Codex/Auto-Trader SPY/.venv/bin/python' -c '...full pytest suite with datetime.UTC and enum.StrEnum shims...'
```

Result:

- Focused Milestone 24 tests passed under temporary Python 3.11 stdlib
  compatibility shims: 8 passed.
- Related event-study tests passed under the same shims: 18 passed.
- Full suite passed under the same shims: 454 passed, 4 skipped. The skipped
  tests require matplotlib.
- Pytest emitted a cache warning because this recovered repo snapshot is
  outside the writable workspace root.

## Milestone 25 - Conditional Event Study

Goal:
Evaluate event/outcome summaries inside existing causal context buckets, using
context-local baselines so context effects and event effects are easier to
separate during research review.

Files added:

- `src/spy_edge_research/backtesting/conditional_event_study.py`
- `tests/backtesting/test_conditional_event_study.py`

Files modified:

- `src/spy_edge_research/backtesting/__init__.py`
- `README.md`
- `PROJECT_MILESTONES.md`

Public functions added:

- `group_event_outcomes_by_context`
- `summarize_conditional_event_edge`
- `filter_event_contexts_by_sample_size`
- `rank_conditional_event_edges`

Tests added:

- Single-context event outcome grouping uses context-local baselines.
- Multi-context summaries preserve context key/value columns plus catalog
  event family and direction metadata.
- Sample-size filtering keeps only supported context rows.
- Research-review ranking sorts stably and can apply sample-size filters.
- Missing event, outcome, and context columns are validated.
- Outputs avoid trading signal/confidence column language.

Causal-safety notes:

- Context columns must already exist and should be causal context features.
- Helpers only read existing event, context, and outcome columns.
- Forward outcomes remain evaluation-only.
- Ranking is deterministic sorting for review, not significance testing,
  optimization, signal generation, or an edge claim.

Commands run:

```bash
'/Users/johnmullen/Documents/Codex/Auto-Trader SPY/.venv/bin/python' -c '...pytest tests/backtesting/test_conditional_event_study.py with datetime.UTC and enum.StrEnum shims...'
'/Users/johnmullen/Documents/Codex/Auto-Trader SPY/.venv/bin/python' -c '...pytest tests/backtesting/test_event_forward_outcomes.py tests/backtesting/test_conditional_event_study.py with shims...'
'/Users/johnmullen/Documents/Codex/Auto-Trader SPY/.venv/bin/python' -c '...full pytest suite with datetime.UTC and enum.StrEnum shims...'
```

Result:

- Initial focused run found a test expectation mistake: two events times two
  outcomes times four context buckets produces 16 rows, not 8.
- After correcting the test, focused Milestone 25 tests passed under temporary
  Python 3.11 stdlib compatibility shims: 6 passed.
- Related event-forward-outcome plus conditional tests passed under the same
  shims: 14 passed.
- Full suite passed under the same shims: 460 passed, 4 skipped. The skipped
  tests require matplotlib.
- Pytest emitted a cache warning because this recovered repo snapshot is
  outside the writable workspace root.

## Milestone 26 - Causal Event Sequence Foundation

Goal:
Represent sequences of already-created named/causal events over ordered rows
and trailing windows without lookahead.

Files added:

- `src/spy_edge_research/signal_engine/event_sequences.py`
- `tests/signal_engine/test_event_sequences.py`

Files modified:

- `src/spy_edge_research/signal_engine/__init__.py`
- `README.md`
- `PROJECT_MILESTONES.md`

Public functions added:

- `build_event_sequence`
- `find_event_sequences`
- `encode_recent_event_sequence`
- `add_recent_event_sequence_features`
- `summarize_event_sequence_counts`

Tests added:

- Event tapes preserve row order and configured event-column order.
- Consecutive event-tape pattern matching returns deterministic spans.
- `max_span_rows=0` is supported for same-row pattern matches.
- Recent sequence encoding uses only past/current rows.
- Changing a future row does not alter prior sequence encodings.
- Missing event values are treated as false.
- Recent sequence/count features do not mutate inputs.
- Sequence-count summaries produce counts and rates.
- Helpers validate missing columns and invalid parameters.
- Outputs avoid trading signal/confidence column language.

Causal-safety notes:

- Sequence features are built from existing event columns only.
- A row-level recent sequence at row `t` includes rows from
  `t - lookback_bars + 1` through `t`, never rows after `t`.
- No forward outcomes, labels, P/L, optimization, or edge claims are read or
  produced by the sequence feature helpers.

Commands run:

```bash
'/Users/johnmullen/Documents/Codex/Auto-Trader SPY/.venv/bin/python' -c '...pytest tests/signal_engine/test_event_sequences.py with datetime.UTC and enum.StrEnum shims...'
'/Users/johnmullen/Documents/Codex/Auto-Trader SPY/.venv/bin/python' -c '...pytest tests/signal_engine with datetime.UTC and enum.StrEnum shims...'
'/Users/johnmullen/Documents/Codex/Auto-Trader SPY/.venv/bin/python' -c '...full pytest suite with datetime.UTC and enum.StrEnum shims...'
```

Result:

- Initial focused run showed `max_span_rows=0` should be valid for same-row
  pattern matches; implementation was adjusted to allow non-negative span
  limits.
- Focused Milestone 26 tests passed under temporary Python 3.11 stdlib
  compatibility shims: 7 passed.
- Related signal-engine tests passed under the same shims: 41 passed.
- Full suite passed under the same shims: 467 passed, 4 skipped. The skipped
  tests require matplotlib.
- Pytest emitted a cache warning because this recovered repo snapshot is
  outside the writable workspace root.

## Milestone 27 - Event Sequence Outcome Study

Goal:
Evaluate encoded event sequences against existing forward outcomes and compare
sequence summaries against their component event summaries.

Files added:

- `src/spy_edge_research/backtesting/sequence_outcomes.py`
- `tests/backtesting/test_sequence_outcomes.py`

Files modified:

- `src/spy_edge_research/backtesting/__init__.py`
- `README.md`
- `PROJECT_MILESTONES.md`

Public functions added:

- `summarize_sequence_forward_returns`
- `compare_sequence_vs_component_events`
- `filter_sequences_by_support`
- `rank_event_sequences_by_expectancy`

Tests added:

- Sequence outcome summaries include sequence counts, baseline counts, rates,
  expectancy, hit rate, differences, and sample-size flags.
- Small and zero-occurrence sequences are explicitly flagged and suppress
  sequence-derived summary claims.
- Sequence-vs-component comparison returns one sequence row plus component
  event rows.
- Support filtering keeps only sufficiently observed sequences.
- Research-review ranking sorts deterministically.
- Helpers validate missing columns, empty sequence values, and invalid
  `min_occurrences`.
- Outputs avoid trading signal/confidence column language.

Causal-safety notes:

- These helpers evaluate already-encoded sequence features against existing
  outcome columns.
- Outcome columns may be forward-looking because this module is evaluation
  only.
- No sequence feature generation, parameter optimization, statistical testing,
  signal creation, P/L simulation, or edge claim is performed.

Commands run:

```bash
'/Users/johnmullen/Documents/Codex/Auto-Trader SPY/.venv/bin/python' -c '...pytest tests/backtesting/test_sequence_outcomes.py with datetime.UTC and enum.StrEnum shims...'
'/Users/johnmullen/Documents/Codex/Auto-Trader SPY/.venv/bin/python' -c '...pytest tests/signal_engine/test_event_sequences.py tests/backtesting/test_sequence_outcomes.py with shims...'
'/Users/johnmullen/Documents/Codex/Auto-Trader SPY/.venv/bin/python' -c '...full pytest suite with datetime.UTC and enum.StrEnum shims...'
```

Result:

- Focused Milestone 27 tests passed under temporary Python 3.11 stdlib
  compatibility shims: 6 passed.
- Related sequence feature and sequence outcome tests passed under the same
  shims: 13 passed.
- Full suite passed under the same shims: 473 passed, 4 skipped. The skipped
  tests require matplotlib.
- Pytest emitted a cache warning because this recovered repo snapshot is
  outside the writable workspace root.

## Milestone 28 - Time-of-Day Research Helpers

Goal:
Add deterministic intraday session bucket assignment and research-only helpers
for reviewing event/outcome behavior by time of day.

Files added:

- `src/spy_edge_research/backtesting/time_of_day.py`
- `tests/backtesting/test_time_of_day.py`

Files modified:

- `src/spy_edge_research/backtesting/__init__.py`
- `README.md`
- `PROJECT_MILESTONES.md`

Public functions added:

- `assign_intraday_session_bucket`
- `summarize_event_by_session_bucket`
- `compare_session_bucket_outcomes`
- `detect_time_of_day_edge_concentration`

Tests added:

- Exact bar-close bucket boundaries are pinned for open, post-open,
  mid-morning, lunch, afternoon, power hour, and outside-regular timestamps.
- Event summaries by session bucket use context-local baselines and do not
  mutate input data.
- Bucket outcome comparisons use overall valid-outcome baselines.
- Time-of-day concentration helper adds event-count share and concentration
  flags.
- Helpers validate missing columns, invalid `min_events`, and invalid
  concentration thresholds.
- Outputs avoid trading signal/confidence column language.

Causal-safety notes:

- Session bucket assignment uses timestamp metadata only.
- Event-by-bucket summaries delegate to conditional event study helpers, so
  each bucket uses its own local baseline.
- Forward outcomes remain evaluation-only.
- Concentration flags are descriptive review aids, not significance tests,
  strategy signals, or edge claims.

Commands run:

```bash
'/Users/johnmullen/Documents/Codex/Auto-Trader SPY/.venv/bin/python' -c '...pytest tests/backtesting/test_time_of_day.py with datetime.UTC and enum.StrEnum shims...'
'/Users/johnmullen/Documents/Codex/Auto-Trader SPY/.venv/bin/python' -c '...pytest tests/backtesting/test_conditional_event_study.py tests/backtesting/test_time_of_day.py with shims...'
'/Users/johnmullen/Documents/Codex/Auto-Trader SPY/.venv/bin/python' -c '...full pytest suite with datetime.UTC and enum.StrEnum shims...'
```

Result:

- Focused Milestone 28 tests passed under temporary Python 3.11 stdlib
  compatibility shims: 6 passed.
- Related conditional event and time-of-day tests passed under the same shims:
  12 passed.
- Full suite passed under the same shims: 479 passed, 4 skipped. The skipped
  tests require matplotlib.
- Pytest emitted a cache warning because this recovered repo snapshot is
  outside the writable workspace root.

## Milestone 29 - Volatility/Range Context Study Helpers

Goal:
Add causal volatility and range context features plus event outcome summaries
by those contexts.

Files added:

- `src/spy_edge_research/backtesting/volatility_range_context.py`
- `tests/backtesting/test_volatility_range_context.py`

Files modified:

- `src/spy_edge_research/backtesting/__init__.py`
- `README.md`
- `PROJECT_MILESTONES.md`

Public functions added:

- `calculate_intraday_realized_volatility`
- `calculate_range_expansion_features`
- `summarize_event_by_volatility_context`
- `summarize_event_by_range_context`

Tests added:

- Realized volatility features are causal under future price changes and do
  not mutate inputs.
- Range expansion features use a prior-range baseline shifted by one row.
- Volatility context summaries use existing context columns when provided or
  generate causal context features when needed.
- Range context summaries generate context features and summarize events.
- Helpers validate missing columns and invalid windows.
- Outputs avoid trading signal/confidence column language.

Causal-safety notes:

- Realized volatility uses close-to-close returns through the current row only.
- Volatility baselines use prior realized-volatility values.
- Range expansion ratios compare the current range to a prior rolling range
  mean, excluding the current bar from the baseline.
- Event summaries remain evaluation-only because they read forward outcomes.

Commands run:

```bash
'/Users/johnmullen/Documents/Codex/Auto-Trader SPY/.venv/bin/python' -c '...pytest tests/backtesting/test_volatility_range_context.py with datetime.UTC and enum.StrEnum shims...'
'/Users/johnmullen/Documents/Codex/Auto-Trader SPY/.venv/bin/python' -c '...pytest tests/backtesting/test_conditional_event_study.py tests/backtesting/test_volatility_range_context.py with shims...'
'/Users/johnmullen/Documents/Codex/Auto-Trader SPY/.venv/bin/python' -c '...full pytest suite with datetime.UTC and enum.StrEnum shims...'
```

Result:

- Focused Milestone 29 tests passed under temporary Python 3.11 stdlib
  compatibility shims: 6 passed.
- Related conditional event plus volatility/range tests passed under the same
  shims: 12 passed.
- Full suite passed under the same shims: 485 passed, 4 skipped. The skipped
  tests require matplotlib.
- Pytest emitted a cache warning because this recovered repo snapshot is
  outside the writable workspace root.

## Milestone 30 - Research Candidate Edge Registry

Goal:
Create a reproducible registry for caveated candidate edge hypotheses discovered
from event, sequence, conditional, or context studies.

Files added:

- `src/spy_edge_research/backtesting/candidate_edges.py`
- `tests/backtesting/test_candidate_edges.py`

Files modified:

- `src/spy_edge_research/backtesting/__init__.py`
- `README.md`
- `PROJECT_MILESTONES.md`

Public functions added:

- `create_candidate_edge`
- `validate_candidate_edge`
- `build_candidate_edge_registry`
- `rank_candidate_edges`
- `write_candidate_edge_registry`
- `read_candidate_edge_registry`

Tests added:

- Candidate creation records type, name, direction, horizon, context, sample
  size, baseline comparison, expectancy, hit rate, caveats, data range, and
  reproducibility metadata.
- Validation rejects missing required fields, invalid candidate types,
  invalid directions, and malformed caveats.
- Registry builder sorts deterministically and rejects duplicate candidate IDs.
- Ranking filters by sample size and sorts for research review.
- JSON write/read round trips records and metadata.
- Persistence respects `overwrite=False`.
- Registry columns avoid live/trading approval language.

Causal-safety notes:

- Candidate records are post-study research artifacts, not causal features.
- Registry sorting is research review only, not statistical validation.
- Records must carry caveats and reproducibility metadata so weak or
  unvalidated candidates remain visibly unproven.
- No strategy rules, signals, broker integration, execution, or live-trading
  readiness status is created.

Commands run:

```bash
'/Users/johnmullen/Documents/Codex/Auto-Trader SPY/.venv/bin/python' -c '...pytest tests/backtesting/test_candidate_edges.py with datetime.UTC and enum.StrEnum shims...'
'/Users/johnmullen/Documents/Codex/Auto-Trader SPY/.venv/bin/python' -c '...pytest tests/backtesting with datetime.UTC and enum.StrEnum shims...'
'/Users/johnmullen/Documents/Codex/Auto-Trader SPY/.venv/bin/python' -c '...full pytest suite with datetime.UTC and enum.StrEnum shims...'
```

Result:

- Focused Milestone 30 tests passed under temporary Python 3.11 stdlib
  compatibility shims: 7 passed.
- Backtesting test suite passed under the same shims: 344 passed, 4 skipped.
- Full suite passed under the same shims: 492 passed, 4 skipped. The skipped
  tests require matplotlib.
- Pytest emitted a cache warning because this recovered repo snapshot is
  outside the writable workspace root.

## Milestone 31 - Statistical Testing Foundation

Goal:
Add deterministic statistical-test helpers for event/candidate validation while
making uncertainty and sample-size limits explicit.

Files added:

- `src/spy_edge_research/backtesting/statistical_tests.py`
- `tests/backtesting/test_statistical_tests.py`

Files modified:

- `src/spy_edge_research/backtesting/__init__.py`
- `README.md`
- `PROJECT_MILESTONES.md`

Public functions added:

- `bootstrap_mean_difference`
- `bootstrap_hit_rate_difference`
- `permutation_test_event_vs_baseline`
- `calculate_confidence_interval`
- `summarize_statistical_test_result`

Tests added:

- Confidence intervals use percentile bounds and handle empty samples.
- Bootstrap mean-difference results are deterministic with a seed.
- Bootstrap hit-rate difference results are deterministic with a seed.
- Permutation tests support mean and hit-rate statistics.
- Statistical summaries include sample sizes and small-sample/no-p-value
  warnings.
- Helpers validate invalid confidence levels, empty samples, invalid resample
  counts, unsupported statistics, and incomplete result records.
- Summary columns avoid overclaiming edge/profitability/trading language.

Causal-safety notes:

- Statistical helpers consume already-separated outcome samples only.
- They do not generate causal features, signals, candidates, strategy rules, or
  execution instructions.
- Bootstrap intervals and permutation p-values are research diagnostics, not
  standalone proof of tradability.

Commands run:

```bash
'/Users/johnmullen/Documents/Codex/Auto-Trader SPY/.venv/bin/python' -c '...pytest tests/backtesting/test_statistical_tests.py with datetime.UTC and enum.StrEnum shims...'
'/Users/johnmullen/Documents/Codex/Auto-Trader SPY/.venv/bin/python' -c '...pytest tests/backtesting with datetime.UTC and enum.StrEnum shims...'
'/Users/johnmullen/Documents/Codex/Auto-Trader SPY/.venv/bin/python' -c '...full pytest suite with datetime.UTC and enum.StrEnum shims...'
```

Result:

- Focused Milestone 31 tests passed under temporary Python 3.11 stdlib
  compatibility shims: 7 passed.
- Backtesting test suite passed under the same shims: 351 passed, 4 skipped.
- Full suite passed under the same shims: 499 passed, 4 skipped. The skipped
  tests require matplotlib.
- Pytest emitted a cache warning because this recovered repo snapshot is
  outside the writable workspace root.

## Milestone 32 - Multiple Hypothesis Risk Helpers

Goal:
Make data-mining risk visible when many event, sequence, horizon, and context
hypotheses are tested.

Files added:

- `src/spy_edge_research/backtesting/multiple_testing.py`
- `tests/backtesting/test_multiple_testing.py`

Files modified:

- `src/spy_edge_research/backtesting/__init__.py`
- `README.md`
- `PROJECT_MILESTONES.md`

Public functions added:

- `count_tested_hypotheses`
- `apply_bonferroni_adjustment`
- `apply_false_discovery_rate_adjustment`
- `summarize_multiple_testing_risk`

Tests added:

- Hypotheses can be counted overall or by grouping columns.
- Bonferroni adjustment multiplies by the number of non-missing p-values and
  caps adjusted p-values at 1.
- Benjamini-Hochberg FDR adjustment is monotonic and preserves missing
  p-values.
- Multiple-testing summaries count unadjusted, Bonferroni-adjusted, and FDR
  discoveries below alpha.
- Helpers validate missing p-value columns, invalid groups, and invalid alpha.
- Outputs avoid overclaiming edge/profitability/trading language.

Causal-safety notes:

- These helpers consume statistical test result tables only.
- They do not generate features, events, labels, signals, candidates, strategy
  rules, or execution instructions.
- Adjusted p-values and warnings are research risk controls, not edge claims.

Commands run:

```bash
'/Users/johnmullen/Documents/Codex/Auto-Trader SPY/.venv/bin/python' -c '...pytest tests/backtesting/test_multiple_testing.py with datetime.UTC and enum.StrEnum shims...'
'/Users/johnmullen/Documents/Codex/Auto-Trader SPY/.venv/bin/python' -c '...pytest tests/backtesting/test_statistical_tests.py tests/backtesting/test_multiple_testing.py with shims...'
'/Users/johnmullen/Documents/Codex/Auto-Trader SPY/.venv/bin/python' -c '...full pytest suite with datetime.UTC and enum.StrEnum shims...'
```

Result:

- Focused Milestone 32 tests passed under temporary Python 3.11 stdlib
  compatibility shims: 6 passed.
- Related statistical and multiple-testing tests passed under the same shims:
  13 passed.
- Full suite passed under the same shims: 505 passed, 4 skipped. The skipped
  tests require matplotlib.
- Pytest emitted a cache warning because this recovered repo snapshot is
  outside the writable workspace root.

## Milestone 33 - Walk-Forward Split Foundation

Goal:
Create chronological train/test split helpers for out-of-sample validation
without random shuffle or leakage across split boundaries.

Files added:

- `src/spy_edge_research/backtesting/time_splits.py`
- `tests/backtesting/test_time_splits.py`

Files modified:

- `src/spy_edge_research/backtesting/__init__.py`
- `README.md`
- `PROJECT_MILESTONES.md`

Public functions added:

- `create_time_series_splits`
- `create_walk_forward_splits`
- `validate_time_series_split`
- `summarize_walk_forward_splits`

Tests added:

- Fixed-width time-series splits use chronological row-position windows.
- Walk-forward splits support expanding and rolling train windows.
- `max_train_size` limits expanding windows to the most recent training rows.
- Split validation rejects overlaps, non-chronological splits, and missing
  required fields.
- Split summaries report train/test bounds and sizes.
- Helpers validate invalid split-size parameters.

Causal-safety notes:

- Split records are row-position based and preserve chronological order.
- Training indices must end before test indices begin.
- No random shuffle or label/outcome inspection is performed by split builders.

Commands run:

```bash
'/Users/johnmullen/Documents/Codex/Auto-Trader SPY/.venv/bin/python' -c '...pytest tests/backtesting/test_time_splits.py with datetime.UTC and enum.StrEnum shims...'
'/Users/johnmullen/Documents/Codex/Auto-Trader SPY/.venv/bin/python' -c '...pytest tests/backtesting/test_time_splits.py tests/backtesting/test_statistical_tests.py with shims...'
'/Users/johnmullen/Documents/Codex/Auto-Trader SPY/.venv/bin/python' -c '...full pytest suite with datetime.UTC and enum.StrEnum shims...'
```

Result:

- Initial focused run found a test expectation mistake for the final
  `max_train_size` split; the implementation correctly used the last five
  training rows before the final test window.
- After correcting the test, focused Milestone 33 tests passed under temporary
  Python 3.11 stdlib compatibility shims: 6 passed.
- Related split and statistical tests passed under the same shims: 13 passed.
- Full suite passed under the same shims: 511 passed, 4 skipped. The skipped
  tests require matplotlib.
- Pytest emitted a cache warning because this recovered repo snapshot is
  outside the writable workspace root.

## Known Constraints Recorded At Milestone 33

These constraints describe the project state at Milestone 33 and are retained
for historical continuity; current live/broker boundaries are governed by the
front matter, `MASTER_PROJECT_BRIEF.md`, and `CODEX_MASTER_DESK.md`.

- Research, validation, and backtesting only at that stage.
- No broker integrations at that stage.
- No live execution at that stage.
- No order routing at that stage.
- No options trading.
- No profitability assumptions.
- Forward-looking columns are labels/outcomes only, never causal inputs.
- The recovered filesystem snapshot was not yet wired to Git at that stage.

## Known Open Questions

- Resolved: the recovered milestone repo has been copied into the active
  `Auto-Trader SPY` workspace, making this folder authoritative.
- Resolved: the former flat scaffold has been archived under
  `legacy_auto_trader_spy_scaffold/`.
- Resolved: this workspace now has a local Python 3.11 `.venv` for ongoing
  test execution.

## Milestone 34 - Out-of-Sample Event Validation

Goal:
Evaluate candidate edge hypotheses on unseen chronological periods using the
candidate registry and walk-forward split foundation.

Files added:

- `src/spy_edge_research/backtesting/oos_validation.py`
- `tests/backtesting/test_oos_validation.py`

Files modified:

- `src/spy_edge_research/backtesting/__init__.py`
- `README.md`
- `PROJECT_MILESTONES.md`

Public functions added:

- `evaluate_candidate_edge_in_split`
- `evaluate_candidate_registry_oos`
- `summarize_oos_edge_stability`
- `compare_in_sample_vs_oos_results`

Tests added:

- One candidate hypothesis is evaluated with separate chronological train and
  OOS windows.
- Registry evaluation supports event, sequence, and conditional-event
  candidate types.
- In-sample versus OOS comparisons add descriptive diagnostic differences and
  sign-consistency flags.
- OOS stability summaries aggregate split-level OOS diagnostics by candidate.
- Helpers reject missing outcome mappings and invalid split records.
- Output columns avoid live-trading/readiness language.

Causal-safety notes:

- Candidate records remain hypotheses, not strategy rules.
- Split validation requires non-overlap and train rows before test rows.
- Forward-looking values are read only from explicitly configured outcome
  columns for evaluation.
- OOS results are caveated as descriptive diagnostics and not proof of edge or
  tradability.
- No broker integration, live execution, order routing, options logic, or
  trading approval state was added.

Commands run:

```bash
.venv/bin/python -m pytest tests/backtesting/test_oos_validation.py -q
.venv/bin/python -m pytest tests/backtesting/test_oos_validation.py tests/backtesting/test_candidate_edges.py tests/backtesting/test_time_splits.py -q
.venv/bin/python -m pytest tests/backtesting -q
.venv/bin/python -m pytest -q
```

Result:

- Initial focused Milestone 34 test run found a registry DataFrame round-trip
  issue where optional `None` fields could become `NaN`; OOS registry
  evaluation now normalizes those optional fields before validation.
- Focused Milestone 34 tests passed: 6 passed.
- Related OOS, candidate-registry, and time-split tests passed: 19 passed.
- Backtesting suite passed: 369 passed, 4 skipped.
- Full suite passed: 517 passed, 4 skipped. The skipped tests require
  matplotlib.
- Pytest emitted a cache warning because this recovered repo snapshot is
  outside the writable workspace root.

## Milestone 35 - Parameter Sensitivity Study

Goal:
Make parameter-dependence visible for research candidates without optimizing,
selecting deployment settings, or implying tradability.

Files added:

- `src/spy_edge_research/backtesting/parameter_sensitivity.py`
- `tests/backtesting/test_parameter_sensitivity.py`

Files modified:

- `src/spy_edge_research/backtesting/__init__.py`
- `README.md`
- `PROJECT_MILESTONES.md`

Public functions added:

- `build_parameter_grid`
- `evaluate_parameter_grid`
- `summarize_parameter_sensitivity`
- `compare_parameter_sensitivity_to_reference`

Tests added:

- Parameter grids produce deterministic cartesian products and parameter-set
  IDs.
- Caller-supplied research evaluators run once per parameter-set row.
- Sensitivity summaries report metric range, mean, standard deviation,
  relative range, and descriptive variation flags.
- Reference comparisons add metric differences from a designated parameter set.
- Helpers validate empty grids, invalid evaluators, missing metrics, missing
  reference rows, and invalid sensitivity thresholds.
- Output columns avoid optimization, live-trading, and trading-readiness
  language.

Causal-safety notes:

- Parameter helpers do not inspect data unless a caller-supplied evaluator does
  so explicitly.
- The module does not generate events, labels, signals, strategy rules,
  rankings, execution instructions, or deployment approvals.
- Sensitivity flags describe metric variation only and are not evidence of a
  repeatable edge.

Commands run:

```bash
.venv/bin/python -m pytest tests/backtesting/test_parameter_sensitivity.py -q
.venv/bin/python -m pytest tests/backtesting/test_parameter_sensitivity.py tests/backtesting/test_oos_validation.py tests/backtesting/test_candidate_edges.py tests/backtesting/test_time_splits.py -q
.venv/bin/python -m pytest -q
```

Result:

- Focused Milestone 35 tests passed: 6 passed.
- Related parameter-sensitivity, OOS, candidate-registry, and time-split tests
  passed: 25 passed.
- Full suite passed: 523 passed, 4 skipped. The skipped tests require
  matplotlib.
- Pytest emitted a cache warning because this recovered repo snapshot is
  outside the writable workspace root.

## Milestone 36 - Robustness Report Builder

Goal:
Package out-of-sample validation and parameter-sensitivity diagnostics into
deterministic research review artifacts without creating strategy rules or
deployment approvals.

Files added:

- `src/spy_edge_research/backtesting/robustness_reports.py`
- `tests/backtesting/test_robustness_reports.py`

Files modified:

- `src/spy_edge_research/backtesting/__init__.py`
- `README.md`
- `PROJECT_MILESTONES.md`

Public functions added:

- `validate_robustness_report_bundle`
- `create_robustness_report_metadata`
- `build_robustness_report_bundle`
- `summarize_robustness_report_bundle`
- `export_robustness_report_bundle_to_csv`
- `export_robustness_report_bundle_to_json`
- `build_and_export_robustness_report`

Tests added:

- Metadata includes a timestamp, milestone, package name, and descriptive
  report caveat.
- Report bundles copy inputs, include provided OOS and parameter-sensitivity
  tables, automatically build OOS stability when needed, and aggregate caveats.
- Bundle summaries report deterministic table names, row counts, column counts,
  and column lists.
- CSV and JSON exports write deterministic table and metadata artifacts.
- Combined build/export returns the report bundle, written paths, and summary.
- Helpers validate malformed bundles, non-DataFrame tables, forbidden metadata
  fields, and overwrite policy.
- Output columns avoid optimization, live-trading, and trading-readiness
  language.

Causal-safety notes:

- Robustness reports package existing diagnostics only.
- Reports do not generate events, labels, signals, strategy rules, rankings,
  parameter selections, execution instructions, or deployment approvals.
- Caveat tables explicitly state that positive diagnostics are not proof of a
  repeatable edge.

Commands run:

```bash
.venv/bin/python -m pytest tests/backtesting/test_robustness_reports.py -q
.venv/bin/python -m pytest tests/backtesting/test_robustness_reports.py tests/backtesting/test_oos_validation.py tests/backtesting/test_parameter_sensitivity.py tests/backtesting/test_event_reports.py -q
.venv/bin/python -m pytest -q
```

Result:

- Initial focused Milestone 36 test run found a caveat-table row-count
  expectation mismatch; the implementation correctly aggregates caveats from
  multiple diagnostic tables.
- Focused Milestone 36 tests passed: 7 passed.
- Related robustness, OOS, parameter-sensitivity, and event-report tests
  passed: 39 passed.
- Full suite passed: 530 passed, 4 skipped. The skipped tests require
  matplotlib.
- Pytest emitted a cache warning because this recovered repo snapshot is
  outside the writable workspace root.

## Milestone 37 - Candidate Rule Object Research Boundary

Goal:
Represent validated candidate hypotheses as auditable research-only rule
objects without creating executable strategy rules, recommendations, execution
instructions, or deployment approvals.

Files added:

- `src/spy_edge_research/backtesting/candidate_rule_objects.py`
- `tests/backtesting/test_candidate_rule_objects.py`

Files modified:

- `src/spy_edge_research/backtesting/__init__.py`
- `README.md`
- `PROJECT_MILESTONES.md`

Public functions added:

- `create_candidate_rule_object`
- `validate_candidate_rule_object`
- `build_candidate_rule_catalog`
- `summarize_candidate_rule_catalog`
- `write_candidate_rule_catalog`
- `read_candidate_rule_catalog`

Tests added:

- Rule objects preserve candidate identity, condition specs, evaluation specs,
  required columns, caveats, validation summaries, robustness summaries, and
  reproducibility metadata.
- Validation rejects incomplete records, invalid research states, non-mapping
  specs, invalid required columns, and forbidden execution/deployment fields.
- Catalog construction sorts deterministically and rejects duplicate rule IDs.
- Catalog summaries report inventory counts and required-column counts without
  rankings or approvals.
- JSON write/read helpers round-trip validated rule catalogs.
- Output columns avoid broker, order-routing, execution, live-trading, and
  trading-readiness language.

Causal-safety notes:

- Rule objects are structured research artifacts only.
- The module does not inspect live data, generate events, generate labels,
  produce signals, optimize settings, simulate P/L, route orders, or approve
  deployment.
- Candidate rule objects carry explicit caveats including
  `research_only_rule_object`, `not_a_trading_signal`, and
  `not_deployment_approval`.

Commands run:

```bash
.venv/bin/python -m pytest tests/backtesting/test_candidate_rule_objects.py -q
.venv/bin/python -m pytest tests/backtesting/test_candidate_rule_objects.py tests/backtesting/test_candidate_edges.py tests/backtesting/test_oos_validation.py tests/backtesting/test_robustness_reports.py -q
.venv/bin/python -m pytest -q
```

Result:

- Focused Milestone 37 tests passed: 7 passed.
- Related candidate-rule, candidate-registry, OOS, and robustness-report tests
  passed: 27 passed.
- Full suite passed: 537 passed, 4 skipped. The skipped tests require
  matplotlib.
- Pytest emitted a cache warning because this recovered repo snapshot is
  outside the writable workspace root.

## Milestone 38 - Candidate Rule Catalog Reporting

Goal:
Package candidate rule catalogs into deterministic research reports without
ranking, optimization, deployment status, or trading-readiness language.

Files added:

- `src/spy_edge_research/backtesting/candidate_rule_reports.py`
- `tests/backtesting/test_candidate_rule_reports.py`

Files modified:

- `src/spy_edge_research/backtesting/__init__.py`
- `README.md`
- `PROJECT_MILESTONES.md`

Public functions added:

- `create_candidate_rule_report_metadata`
- `summarize_candidate_rule_research_states`
- `build_candidate_rule_required_column_inventory`
- `summarize_candidate_rule_caveats`
- `build_candidate_rule_report_bundle`
- `validate_candidate_rule_report_bundle`
- `summarize_candidate_rule_report_bundle`
- `export_candidate_rule_report_bundle_to_csv`
- `export_candidate_rule_report_bundle_to_json`

Tests added:

- Research-state, required-column, and caveat summaries.
- Report bundle construction and structural summaries.
- Deterministic CSV and JSON exports with overwrite protection.
- Bundle validation for malformed inputs.

Causal-safety notes:

- Reports summarize existing candidate rule artifacts only.
- No replay, signal generation, optimization, execution, or approval state is
  created.

## Milestone 39 - Rule Object Evaluation Replay

Goal:
Replay stored rule-object condition specs against historical DataFrames for
reproducibility checks only.

Files added:

- `src/spy_edge_research/backtesting/candidate_rule_replay.py`
- `tests/backtesting/test_candidate_rule_replay.py`

Files modified:

- `src/spy_edge_research/backtesting/__init__.py`
- `README.md`
- `PROJECT_MILESTONES.md`

Public functions added:

- `replay_candidate_rule_object`
- `replay_candidate_rule_catalog`
- `summarize_candidate_rule_replay`

Tests added:

- Replay applies event-column, sequence, and context-filter conditions.
- Catalog replay and replay summary aggregation.
- Missing required columns are reported without evaluation.
- Invalid sequence specs are rejected.

Causal-safety notes:

- Replay reconstructs historical condition masks for audit only.
- Replay outputs sample counts and caveats, not predictions, actions, signals,
  orders, or performance claims.

## Milestone 40 - Rule Object OOS Replay Comparison

Goal:
Compare replay sample sizes with OOS validation samples to detect
reproducibility drift or missing OOS references.

Files added:

- `src/spy_edge_research/backtesting/candidate_rule_oos_comparison.py`
- `tests/backtesting/test_candidate_rule_oos_comparison.py`

Files modified:

- `src/spy_edge_research/backtesting/__init__.py`
- `README.md`
- `PROJECT_MILESTONES.md`

Public functions added:

- `compare_rule_replay_to_oos_results`
- `summarize_rule_oos_comparison`

Tests added:

- Comparison flags ok, sample-size mismatch, and missing OOS reference states.
- Comparison summaries count rule objects by diagnostic status.
- Helpers validate threshold and required-column inputs.

Causal-safety notes:

- Comparison is a reproducibility diagnostic only.
- It does not evaluate profitability, select candidates, create signals, or
  approve deployment.

## Milestone 41 - Rule Object Robustness Audit

Goal:
Bundle catalog reports, replay diagnostics, OOS comparisons, and caveats into
deterministic research audit artifacts.

Files added:

- `src/spy_edge_research/backtesting/candidate_rule_audits.py`
- `tests/backtesting/test_candidate_rule_audits.py`

Files modified:

- `src/spy_edge_research/backtesting/__init__.py`
- `README.md`
- `PROJECT_MILESTONES.md`

Public functions added:

- `create_candidate_rule_audit_metadata`
- `build_candidate_rule_audit_bundle`
- `validate_candidate_rule_audit_bundle`
- `summarize_candidate_rule_audit_bundle`
- `export_candidate_rule_audit_bundle_to_csv`
- `export_candidate_rule_audit_bundle_to_json`

Tests added:

- Audit metadata creation.
- Audit bundle table copying and default caveat table creation.
- Structural audit bundle summaries.
- Deterministic CSV and JSON exports with overwrite protection.
- Bundle validation for malformed inputs.

Causal-safety notes:

- Audit bundles package existing research diagnostics only.
- Audit findings do not imply deployment approval, execution readiness, or
  tradability.

Commands run:

```bash
.venv/bin/python -m pytest tests/backtesting/test_candidate_rule_reports.py tests/backtesting/test_candidate_rule_replay.py tests/backtesting/test_candidate_rule_oos_comparison.py tests/backtesting/test_candidate_rule_audits.py -q
.venv/bin/python -m pytest tests/backtesting/test_candidate_rule_objects.py tests/backtesting/test_candidate_rule_reports.py tests/backtesting/test_candidate_rule_replay.py tests/backtesting/test_candidate_rule_oos_comparison.py tests/backtesting/test_candidate_rule_audits.py tests/backtesting/test_candidate_edges.py tests/backtesting/test_oos_validation.py tests/backtesting/test_robustness_reports.py -q
.venv/bin/python -m pytest -q
```

Result:

- Focused Milestone 38-41 tests passed: 17 passed.
- Related candidate-rule, candidate-registry, OOS, and robustness-report tests
  passed: 44 passed.
- Full suite passed: 554 passed, 4 skipped. The skipped tests require
  matplotlib.
- Pytest emitted a cache warning because this recovered repo snapshot is
  outside the writable workspace root.

## Milestone 42 - Research Decision Journal

Goal:
Track research dispositions for candidates and rule objects without approval,
deployment, or trading-readiness language.

Files added:

- `src/spy_edge_research/backtesting/research_decision_journal.py`
- `tests/backtesting/test_research_decision_journal.py`

Public functions added:

- `create_research_decision_record`
- `validate_research_decision_record`
- `build_research_decision_journal`
- `summarize_research_decision_journal`
- `write_research_decision_journal`
- `read_research_decision_journal`

Causal-safety notes:

- Decision records are research dispositions only.
- Valid decisions are limited to continue study, needs more data, merge with
  related hypothesis, or retire from review.

## Milestone 43 - Candidate Family Aggregation

Goal:
Group related candidates and rule objects by descriptive family attributes to
surface clustering without ranking or claiming edge.

Files added:

- `src/spy_edge_research/backtesting/candidate_family_aggregation.py`
- `tests/backtesting/test_candidate_family_aggregation.py`

Public functions added:

- `add_candidate_family_columns`
- `aggregate_candidate_families`
- `summarize_candidate_family_concentration`

Causal-safety notes:

- Family aggregation summarizes existing metadata and condition specs only.
- Concentration summaries are descriptive and not edge evidence.

## Milestone 44 - Regime-Conditioned Rule Review

Goal:
Review rule-object replay sample distribution across context buckets such as
session, regime, volatility, or range context.

Files added:

- `src/spy_edge_research/backtesting/rule_context_review.py`
- `tests/backtesting/test_rule_context_review.py`

Public functions added:

- `review_rule_replay_by_context`
- `review_rule_catalog_by_context`
- `summarize_rule_context_review`

Causal-safety notes:

- Context review reuses historical replay masks for descriptive concentration
  checks only.
- It does not create predictions, actions, strategy instructions, or
  deployment decisions.

## Milestone 45 - Negative Control And Placebo Tests

Goal:
Make data-mining risk more visible with shifted and randomized control
conditions.

Files added:

- `src/spy_edge_research/backtesting/negative_controls.py`
- `tests/backtesting/test_negative_controls.py`

Public functions added:

- `build_shifted_condition_control`
- `build_random_condition_control`
- `evaluate_negative_control_outcomes`
- `summarize_negative_control_risk`

Causal-safety notes:

- Negative controls are placebo diagnostics only.
- They do not validate an edge, optimize parameters, create signals, or approve
  deployment.

Files modified for Milestones 42-45:

- `src/spy_edge_research/backtesting/__init__.py`
- `README.md`
- `PROJECT_MILESTONES.md`

Commands run:

```bash
.venv/bin/python -m pytest tests/backtesting/test_research_decision_journal.py tests/backtesting/test_candidate_family_aggregation.py tests/backtesting/test_rule_context_review.py tests/backtesting/test_negative_controls.py -q
.venv/bin/python -m pytest tests/backtesting/test_research_decision_journal.py tests/backtesting/test_candidate_family_aggregation.py tests/backtesting/test_rule_context_review.py tests/backtesting/test_negative_controls.py tests/backtesting/test_candidate_rule_objects.py tests/backtesting/test_candidate_rule_replay.py tests/backtesting/test_candidate_rule_oos_comparison.py tests/backtesting/test_candidate_rule_audits.py -q
.venv/bin/python -m pytest -q
```

Result:

- Initial focused run found a test setup issue in the negative-control
  validation test; the test now supplies required metric columns before
  checking the missing-observed-condition path.
- Focused Milestone 42-45 tests passed: 15 passed.
- Related decision-journal, family, context-review, negative-control, and
  candidate-rule tests passed: 35 passed.
- Full suite passed: 569 passed, 4 skipped. The skipped tests require
  matplotlib.
- Pytest emitted a cache warning because this recovered repo snapshot is
  outside the writable workspace root.

## Milestone 46 - Expanded Statistical Placebo Suite

Goal:
Extend placebo diagnostics with shifted-control grids, repeated random
controls, percentile ranks, and control exceedance rates.

Files added:

- `src/spy_edge_research/backtesting/placebo_statistics.py`
- `tests/backtesting/test_placebo_statistics.py`

Public functions added:

- `build_shifted_control_grid`
- `build_repeated_random_controls`
- `evaluate_placebo_control_suite`
- `summarize_placebo_percentile_ranks`

## Milestone 47 - Temporal Stability Diagnostics

Goal:
Review whether diagnostics are stable across calendar periods or concentrated
in a few windows.

Files added:

- `src/spy_edge_research/backtesting/temporal_stability.py`
- `tests/backtesting/test_temporal_stability.py`

Public functions added:

- `assign_temporal_period`
- `summarize_metric_by_period`
- `summarize_temporal_stability`
- `flag_temporal_concentration`

## Milestone 48 - Data Quality And Coverage Impact Review

Goal:
Quantify missingness, context completeness, session coverage, and quality-mask
impact on research diagnostics.

Files added:

- `src/spy_edge_research/backtesting/data_quality_impact.py`
- `tests/backtesting/test_data_quality_impact.py`

Public functions added:

- `summarize_column_coverage`
- `summarize_session_coverage`
- `evaluate_quality_filter_impact`
- `summarize_required_context_coverage`

## Milestone 49 - Research Risk Dashboard Bundle

Goal:
Package multiple-testing, placebo, temporal, data-quality, and decision
summary tables into deterministic research-risk report artifacts.

Files added:

- `src/spy_edge_research/backtesting/research_risk_reports.py`
- `tests/backtesting/test_research_risk_reports.py`

Public functions added:

- `create_research_risk_report_metadata`
- `build_research_risk_report_bundle`
- `validate_research_risk_report_bundle`
- `summarize_research_risk_report_bundle`
- `export_research_risk_report_bundle_to_csv`
- `export_research_risk_report_bundle_to_json`

Files modified for Milestones 46-49:

- `src/spy_edge_research/backtesting/__init__.py`
- `README.md`
- `PROJECT_MILESTONES.md`

Causal-safety notes:

- Milestones 46-49 package and summarize skepticism diagnostics only.
- They do not create causal features, trading signals, strategy instructions,
  deployment approvals, broker integrations, or live execution behavior.

Commands run:

```bash
.venv/bin/python -m pytest tests/backtesting/test_placebo_statistics.py tests/backtesting/test_temporal_stability.py tests/backtesting/test_data_quality_impact.py tests/backtesting/test_research_risk_reports.py -q
.venv/bin/python -m pytest tests/backtesting/test_placebo_statistics.py tests/backtesting/test_temporal_stability.py tests/backtesting/test_data_quality_impact.py tests/backtesting/test_research_risk_reports.py tests/backtesting/test_negative_controls.py tests/backtesting/test_research_decision_journal.py tests/backtesting/test_multiple_testing.py -q
.venv/bin/python -m pytest -q
```

Result:

- Focused Milestone 46-49 tests passed: 16 passed.
- Related placebo, temporal, data-quality, risk-report, negative-control,
  decision-journal, and multiple-testing tests passed: 30 passed.
- Full suite passed: 585 passed, 4 skipped. The skipped tests require
  matplotlib.
- Pytest emitted a cache warning because this recovered repo snapshot is
  outside the writable workspace root.

## Milestone 50 - Research Package Maturity Scoring

Goal:
Score research packages by evidence completeness, OOS coverage, placebo risk,
temporal stability, data quality, caveat control, and decision status without
implying trade readiness.

Files added:

- `src/spy_edge_research/backtesting/research_maturity.py`
- `tests/backtesting/test_research_maturity.py`

Public functions added:

- `create_research_maturity_record`
- `build_research_maturity_table`
- `summarize_research_maturity`
- `score_research_package_from_diagnostics`

## Milestone 51 - Candidate Retirement And Merge Workflow

Goal:
Preserve candidate retirement and merge lineage without deleting research
history.

Files added:

- `src/spy_edge_research/backtesting/candidate_lineage.py`
- `tests/backtesting/test_candidate_lineage.py`

Public functions added:

- `create_candidate_lineage_record`
- `validate_candidate_lineage_record`
- `build_candidate_lineage_table`
- `summarize_candidate_lineage`
- `write_candidate_lineage_table`
- `read_candidate_lineage_table`

## Milestone 52 - Research Package Export Manifest

Goal:
Index research package artifacts such as catalogs, OOS results, journals, risk
reports, and audit outputs in a deterministic manifest.

Files added:

- `src/spy_edge_research/backtesting/research_package_manifest.py`
- `tests/backtesting/test_research_package_manifest.py`

Public functions added:

- `create_research_package_manifest_record`
- `build_research_package_manifest`
- `validate_research_package_manifest`
- `summarize_research_package_manifest`
- `write_research_package_manifest`
- `read_research_package_manifest`

## Milestone 53 - End-to-End Research Review Workflow

Goal:
Compose research review tables and package manifests into deterministic
workflow outputs and exports.

Files added:

- `src/spy_edge_research/backtesting/research_review_workflow.py`
- `tests/backtesting/test_research_review_workflow.py`

Public functions added:

- `create_research_review_metadata`
- `build_research_review_workflow_outputs`
- `summarize_research_review_workflow_outputs`
- `export_research_review_workflow_outputs`

Files modified for Milestones 50-53:

- `src/spy_edge_research/backtesting/__init__.py`
- `README.md`
- `PROJECT_MILESTONES.md`

Causal-safety notes:

- Milestones 50-53 organize existing research evidence only.
- Maturity scores, lineage records, manifests, and workflow outputs do not
  imply trade readiness, deployment approval, signals, execution, broker
  integration, or real-money use.

Commands run:

```bash
.venv/bin/python -m pytest tests/backtesting/test_research_maturity.py tests/backtesting/test_candidate_lineage.py tests/backtesting/test_research_package_manifest.py tests/backtesting/test_research_review_workflow.py -q
.venv/bin/python -m pytest tests/backtesting/test_research_maturity.py tests/backtesting/test_candidate_lineage.py tests/backtesting/test_research_package_manifest.py tests/backtesting/test_research_review_workflow.py tests/backtesting/test_research_risk_reports.py tests/backtesting/test_research_decision_journal.py tests/backtesting/test_candidate_rule_audits.py -q
.venv/bin/python -m pytest -q
```

Result:

- Focused Milestone 50-53 tests passed: 13 passed.
- Related maturity, lineage, manifest, workflow, risk-report,
  decision-journal, and candidate-rule audit tests passed: 26 passed.
- Full suite passed: 598 passed, 4 skipped. The skipped tests require
  matplotlib.
- Pytest emitted a cache warning because this recovered repo snapshot is
  outside the writable workspace root.

## Milestone 54 - Research Review Artifact Integrity Checks

Goal:
Validate research package manifests for artifact path presence, required
metadata keys, expected artifact names, and deterministic integrity summaries.

Files added:

- `src/spy_edge_research/backtesting/research_artifact_integrity.py`
- `tests/backtesting/test_research_artifact_integrity.py`

Public functions added:

- `check_manifest_artifact_paths`
- `check_manifest_required_metadata`
- `check_expected_artifacts`
- `build_artifact_integrity_report`
- `summarize_artifact_integrity`

## Milestone 55 - Research Package Comparison Reports

Goal:
Compare research package artifact coverage, maturity distributions, risk
summary structure, decision distributions, lineage counts, and caveat inventory
without selecting a best package.

Files added:

- `src/spy_edge_research/backtesting/research_package_comparison.py`
- `tests/backtesting/test_research_package_comparison.py`

Public functions added:

- `compare_research_package_artifacts`
- `compare_research_package_maturity`
- `compare_research_package_risks`
- `compare_research_package_decisions`
- `compare_research_package_lineage`
- `build_research_package_comparison_bundle`
- `validate_research_package_comparison_bundle`
- `summarize_research_package_comparison_bundle`
- `export_research_package_comparison_bundle_to_csv`
- `export_research_package_comparison_bundle_to_json`

## Milestone 56 - Research Evidence Traceability Matrix

Goal:
Link research candidates and rule objects to available candidate records, OOS
results, robustness reports, risk reports, decision records, lineage records,
and package manifest artifacts while surfacing missing evidence as caveats.

Files added:

- `src/spy_edge_research/backtesting/research_traceability.py`
- `tests/backtesting/test_research_traceability.py`

Public functions added:

- `build_research_traceability_matrix`
- `summarize_research_traceability`

## Milestone 57 - Research Governance Summary Bundle

Goal:
Package artifact integrity summaries, package comparison summaries,
traceability summaries, and governance caveats into deterministic CSV/JSON
research review bundles.

Files added:

- `src/spy_edge_research/backtesting/research_governance_reports.py`
- `tests/backtesting/test_research_governance_reports.py`

Public functions added:

- `create_research_governance_metadata`
- `build_research_governance_bundle`
- `validate_research_governance_bundle`
- `summarize_research_governance_bundle`
- `export_research_governance_bundle_to_csv`
- `export_research_governance_bundle_to_json`

Files modified for Milestones 54-57:

- `src/spy_edge_research/backtesting/__init__.py`
- `README.md`
- `PROJECT_MILESTONES.md`

Causal-safety notes:

- Milestones 54-57 validate and summarize research-review artifacts only.
- Integrity checks inspect file existence and metadata structure; they do not
  read research outcome contents or evaluate tradability.
- Package comparisons are descriptive coverage/distribution reports only and do
  not rank packages, choose a best package, optimize thresholds, or create
  recommendations.
- Traceability matrices surface missing evidence as caveats only; they are not
  approval states, deployment gates, or trade-readiness scores.
- Governance bundles package existing review summaries and caveats only. They
  do not create broker integrations, live execution, order routing, trading
  approval states, recommendations, or real-money use claims.

Commands run:

```bash
.venv/bin/python -m pytest tests/backtesting/test_research_artifact_integrity.py -q
.venv/bin/python -m pytest tests/backtesting/test_research_package_comparison.py -q
.venv/bin/python -m pytest tests/backtesting/test_research_traceability.py -q
.venv/bin/python -m pytest tests/backtesting/test_research_governance_reports.py -q
.venv/bin/python -m pytest tests/backtesting/test_research_artifact_integrity.py tests/backtesting/test_research_package_comparison.py tests/backtesting/test_research_traceability.py tests/backtesting/test_research_governance_reports.py -q
.venv/bin/python -m pytest -q
```

Result:

- Focused Milestone 54 tests passed after tightening summary recursion:
  2 passed.
- Focused Milestone 55 tests passed: 2 passed.
- Focused Milestone 56 tests passed: 2 passed.
- Focused Milestone 57 tests passed: 3 passed.
- Combined focused Milestone 54-57 tests passed: 9 passed.
- Full suite passed: 607 passed, 4 skipped. The skipped tests require
  matplotlib.

## Milestone 58 - Instrument Registry Foundation

Goal:
Define a typed, deterministic, JSON-serializable registry for research
instruments without implying tradability, broker support, or execution support.

Files added:

- `src/spy_edge_research/instruments/instrument_registry.py`
- `src/spy_edge_research/instruments/__init__.py`
- `tests/instruments/test_instrument_registry.py`

Public classes and functions added:

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

## Milestone 59 - Multi-Symbol Data Alignment

Goal:
Align already-loaded in-memory symbol DataFrames on timestamp/session keys,
prefix non-key columns by symbol, and surface timestamp coverage diagnostics.

Files added:

- `src/spy_edge_research/market_data/multi_symbol_alignment.py`
- `tests/market_data/test_multi_symbol_alignment.py`

Files modified:

- `src/spy_edge_research/market_data/__init__.py`

Public functions added:

- `validate_symbol_frame_map`
- `prefix_symbol_columns`
- `align_symbol_frames`
- `build_multi_symbol_panel`
- `summarize_symbol_alignment`
- `filter_aligned_symbol_universe`

## Milestone 60 - Cross-Instrument Confirmation Features

Goal:
Create causal cross-instrument confirmation, divergence, relative-return,
VWAP-side, and trailing-volume context features from aligned multi-symbol data.

Files added:

- `src/spy_edge_research/signal_engine/cross_instrument_features.py`
- `tests/signal_engine/test_cross_instrument_features.py`

Files modified:

- `src/spy_edge_research/signal_engine/__init__.py`

Public functions added:

- `add_relative_return_features`
- `add_cross_symbol_trend_confirmation`
- `add_cross_symbol_vwap_confirmation`
- `add_cross_symbol_volume_confirmation`
- `add_cross_symbol_divergence_flags`
- `add_cross_instrument_confirmation_features`

## Milestone 61 - Multi-Instrument Event Outcome Studies

Goal:
Evaluate existing events and forward outcome columns conditioned on
cross-instrument context features with sample-size and coverage caveats.

Files added:

- `src/spy_edge_research/backtesting/multi_instrument_event_study.py`
- `tests/backtesting/test_multi_instrument_event_study.py`

Files modified:

- `src/spy_edge_research/backtesting/__init__.py`
- `README.md`
- `PROJECT_MILESTONES.md`

Public functions added:

- `summarize_event_by_instrument_context`
- `compare_confirmed_vs_divergent_event_outcomes`
- `build_multi_instrument_event_outcome_table`
- `summarize_multi_instrument_context_coverage`
- `build_multi_instrument_research_report`

Causal-safety notes:

- Milestone 58 records research instrument metadata only and does not imply
  market-data availability, tradability, routing, broker support, or execution.
- Milestone 59 accepts caller-supplied in-memory DataFrames only. It performs
  deterministic joins and diagnostics without downloads or paid data
  dependencies. Forward fill is disabled by default and explicitly caveated
  when requested.
- Milestone 60 creates features from current and prior rows only. Return
  features use current-vs-prior prices, volume baselines are shifted trailing
  baselines, and outputs avoid buy/sell/entry/exit/approval language.
- Milestone 61 reads forward outcomes only as evaluation targets. It produces
  descriptive context comparisons, sample-size flags, and coverage diagnostics
  without ranking strategies, optimizing thresholds, simulating P/L, claiming
  edge, or approving deployment.

Commands run:

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m pytest tests/instruments/test_instrument_registry.py -q
.venv/bin/python -m pytest tests/market_data/test_multi_symbol_alignment.py -q
.venv/bin/python -m pytest tests/signal_engine/test_cross_instrument_features.py -q
.venv/bin/python -m pytest tests/backtesting/test_multi_instrument_event_study.py -q
.venv/bin/python -m pytest tests/instruments/test_instrument_registry.py tests/market_data/test_multi_symbol_alignment.py tests/signal_engine/test_cross_instrument_features.py tests/backtesting/test_multi_instrument_event_study.py -q
.venv/bin/python -m pytest -q
```

Result:

- Pre-change full suite baseline passed: 607 passed, 4 skipped.
- Focused Milestone 58 tests passed: 5 passed.
- Focused Milestone 59 tests passed: 5 passed.
- Focused Milestone 60 tests passed: 5 passed.
- Focused Milestone 61 tests passed after correcting a synthetic test
  expectation: 6 passed.
- Combined focused Milestone 58-61 tests passed: 21 passed.
- Final full suite passed: 628 passed, 4 skipped. The skipped tests require
  matplotlib.

Next recommended module boundary:

- Stop after Milestone 61 as planned. The next natural module should remain
  research-only, likely sector ETF context expansion or data-quality hardening
  for multi-instrument panels, and should not begin sector rotation, macro
  regimes, factor allocation, dashboards, paper trading, broker integration,
  options, alerts, execution, or trade-readiness work without a new approved
  module brief.

## Milestone 62 - Sector ETF Universe Foundation

Goal:
Define a deterministic, JSON-serializable sector ETF universe for research
metadata and grouping without implying tradability, allocation, broker support,
or execution support.

Files added:

- `src/spy_edge_research/instruments/sector_universe.py`
- `tests/instruments/test_sector_universe.py`

Files modified:

- `src/spy_edge_research/instruments/__init__.py`

Public classes and functions added:

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

## Milestone 63 - Sector Context Feature Layer

Goal:
Create causal sector breadth, leadership, dispersion, relative-return, and
primary-sector confirmation features from already-aligned sector ETF data.

Files added:

- `src/spy_edge_research/signal_engine/sector_context_features.py`
- `tests/signal_engine/test_sector_context_features.py`

Files modified:

- `src/spy_edge_research/signal_engine/__init__.py`

Public functions added:

- `add_sector_relative_return_features`
- `add_sector_breadth_features`
- `add_sector_leadership_flags`
- `add_sector_dispersion_features`
- `add_primary_sector_confirmation_features`
- `add_sector_context_features`

## Milestone 64 - Sector-Confirmed Event Studies

Goal:
Evaluate existing SPY events and forward outcome columns conditioned on sector
context features with sample-size and coverage caveats.

Files added:

- `src/spy_edge_research/backtesting/sector_event_study.py`
- `tests/backtesting/test_sector_event_study.py`

Files modified:

- `src/spy_edge_research/backtesting/__init__.py`

Public functions added:

- `summarize_event_by_sector_context`
- `compare_sector_confirmed_event_outcomes`
- `build_sector_event_outcome_table`
- `summarize_sector_context_coverage`
- `build_sector_event_research_report`

## Milestone 65 - Sector Rotation Research Reports

Goal:
Package sector leadership, breadth, dispersion, sector-event study summaries,
and caveats into deterministic descriptive research report bundles.

Files added:

- `src/spy_edge_research/backtesting/sector_rotation_reports.py`
- `tests/backtesting/test_sector_rotation_reports.py`

Files modified:

- `src/spy_edge_research/backtesting/__init__.py`
- `README.md`
- `PROJECT_MILESTONES.md`

Public functions added:

- `create_sector_rotation_report_metadata`
- `build_sector_rotation_snapshot`
- `summarize_sector_leadership_persistence`
- `build_sector_rotation_report_bundle`
- `validate_sector_rotation_report_bundle`
- `summarize_sector_rotation_report_bundle`
- `export_sector_rotation_report_bundle_to_csv`
- `export_sector_rotation_report_bundle_to_json`

Causal-safety notes:

- Milestone 62 records sector ETF metadata only and does not imply
  market-data availability, tradability, sector allocation, broker support,
  portfolio construction, or execution.
- Milestone 63 accepts caller-supplied, already-aligned DataFrames only.
  Return features use current-vs-prior prices, breadth/leadership/dispersion
  use current row sector returns, and high-dispersion context uses trailing
  rolling information available at the row.
- Milestone 64 reads forward outcomes only as evaluation targets. It produces
  descriptive sector-context comparisons, sample-size flags, and coverage
  diagnostics without ranking strategies, optimizing thresholds, simulating
  P/L, claiming edge, or approving deployment.
- Milestone 65 packages existing sector context and sector-event research
  summaries only. Rotation is descriptive sector-leadership research, not
  allocation guidance, portfolio construction, sector buy/sell ranking, paper
  trading, broker integration, execution, or trade-readiness support.

Commands run:

```bash
.venv/bin/python -m pytest tests/instruments/test_sector_universe.py -q
.venv/bin/python -m pytest tests/signal_engine/test_sector_context_features.py -q
.venv/bin/python -m pytest tests/backtesting/test_sector_event_study.py -q
.venv/bin/python -m pytest tests/backtesting/test_sector_rotation_reports.py -q
.venv/bin/python -m pytest tests/instruments/test_instrument_registry.py tests/instruments/test_sector_universe.py -q
.venv/bin/python -m pytest tests/signal_engine/test_cross_instrument_features.py tests/signal_engine/test_sector_context_features.py -q
.venv/bin/python -m pytest tests/backtesting/test_multi_instrument_event_study.py tests/backtesting/test_sector_event_study.py tests/backtesting/test_sector_rotation_reports.py -q
.venv/bin/python -m pytest -q
```

Result:

- Focused Milestone 62 tests passed: 5 passed.
- Focused Milestone 63 tests passed: 6 passed.
- Focused Milestone 64 tests passed: 6 passed.
- Focused Milestone 65 tests passed: 6 passed.
- Related instrument tests passed: 10 passed.
- Related signal-engine tests passed: 11 passed.
- Related backtesting context/report tests passed: 18 passed.
- Final full suite passed: 651 passed, 4 skipped. The skipped tests require
  matplotlib.

Next recommended module boundary:

- Stop after Milestone 65 as planned. The next module should remain
  research-only and should be separately approved before beginning macro,
  rates, credit, commodity, factor, portfolio/risk, dashboard, service API,
  paper-trading, broker integration, options, alerting, execution, or
  trade-readiness work.

## Milestone 66 - Macro Instrument Universe

Goal:
Define a deterministic, JSON-serializable macro, rates, credit, commodity,
volatility, currency, and risk-proxy universe for research metadata and
grouping without implying tradability, allocation, broker support, or execution
support.

Files added:

- `src/spy_edge_research/instruments/macro_universe.py`
- `tests/instruments/test_macro_universe.py`

Files modified:

- `src/spy_edge_research/instruments/__init__.py`

Public classes and functions added:

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

## Milestone 67 - Macro Regime Feature Layer

Goal:
Create causal macro, rates, credit, commodity, volatility-proxy, and
risk-on/risk-off context features from already-aligned macro instrument data.

Files added:

- `src/spy_edge_research/signal_engine/macro_regime_features.py`
- `tests/signal_engine/test_macro_regime_features.py`

Files modified:

- `src/spy_edge_research/signal_engine/__init__.py`

Public functions added:

- `add_macro_relative_return_features`
- `add_rates_regime_features`
- `add_credit_regime_features`
- `add_commodity_regime_features`
- `add_volatility_proxy_regime_features`
- `add_risk_on_risk_off_features`
- `add_macro_regime_features`

## Milestone 68 - Macro-Conditioned Event Studies

Goal:
Evaluate existing SPY events and forward outcome columns conditioned on macro
regime context features with sample-size and coverage caveats.

Files added:

- `src/spy_edge_research/backtesting/macro_event_study.py`
- `tests/backtesting/test_macro_event_study.py`

Files modified:

- `src/spy_edge_research/backtesting/__init__.py`

Public functions added:

- `summarize_event_by_macro_regime`
- `compare_macro_regime_event_outcomes`
- `build_macro_event_outcome_table`
- `summarize_macro_context_coverage`
- `build_macro_event_research_report`

## Milestone 69 - Macro Regime Research Reports

Goal:
Package macro regime snapshots, macro-conditioned event summaries, coverage
diagnostics, persistence summaries, and caveats into deterministic descriptive
research report bundles.

Files added:

- `src/spy_edge_research/backtesting/macro_regime_reports.py`
- `tests/backtesting/test_macro_regime_reports.py`

Files modified:

- `src/spy_edge_research/backtesting/__init__.py`
- `README.md`
- `PROJECT_MILESTONES.md`

Public functions added:

- `create_macro_regime_report_metadata`
- `build_macro_regime_snapshot`
- `summarize_macro_regime_persistence`
- `build_macro_regime_report_bundle`
- `validate_macro_regime_report_bundle`
- `summarize_macro_regime_report_bundle`
- `export_macro_regime_report_bundle_to_csv`
- `export_macro_regime_report_bundle_to_json`

Causal-safety notes:

- Milestone 66 records macro proxy metadata only and does not imply
  market-data availability, tradability, macro allocation, broker support,
  portfolio construction, or execution.
- Milestone 67 accepts caller-supplied, already-aligned DataFrames only.
  Return features use current-vs-prior prices. Rates, credit, commodity,
  volatility-proxy, and risk-on/risk-off context columns use current and prior
  row information only.
- Milestone 68 reads forward outcomes only as evaluation targets. It produces
  descriptive macro-regime comparisons, sample-size flags, and coverage
  diagnostics without ranking strategies, optimizing thresholds, simulating
  P/L, claiming edge, or approving deployment.
- Milestone 69 packages existing macro context and macro-event research
  summaries only. Macro regimes are descriptive context, not allocation
  guidance, portfolio construction, instrument buy/sell ranking, paper
  trading, broker integration, execution, or trade-readiness support.

Focused test commands:

```bash
.venv/bin/python -m pytest tests/instruments/test_macro_universe.py -q
.venv/bin/python -m pytest tests/signal_engine/test_macro_regime_features.py -q
.venv/bin/python -m pytest tests/backtesting/test_macro_event_study.py -q
.venv/bin/python -m pytest tests/backtesting/test_macro_regime_reports.py -q
.venv/bin/python -m pytest tests/instruments/test_macro_universe.py tests/signal_engine/test_macro_regime_features.py tests/backtesting/test_macro_event_study.py tests/backtesting/test_macro_regime_reports.py -q
```

Full-suite command:

```bash
.venv/bin/python -m pytest -q
```

Result:

- Focused Milestone 66 tests passed after correcting the expected alphabetical
  deterministic symbol order: 5 passed.
- Focused Milestone 67 tests passed: 6 passed.
- Focused Milestone 68 tests passed: 6 passed.
- Focused Milestone 69 tests passed: 6 passed.
- Combined focused Milestone 66-69 tests passed: 23 passed.
- Related instrument tests passed: 15 passed.
- Related signal-engine tests passed: 17 passed.
- Related backtesting context/report tests passed: 30 passed.
- Final full suite passed: 674 passed, 4 skipped. The skipped tests require
  matplotlib.

Next recommended module boundary (as recorded at Milestone 69):

- Stop after Milestone 69 as planned. The next module should remain
  research-only and should be separately approved before beginning factor ETF
  allocation research, value research, portfolio/risk construction, dashboard,
  service API, paper-trading readiness, broker integration, options, alerting,
  execution, or trade-readiness work.

> Superseded 2026-06-13: the user reviewed `docs/NEXT_MODULES_ROADMAP.md` and
> approved building the full Milestone 70+ roadmap (MOD 06-10), one module at a
> time, all research-only. MOD 06 (Portfolio/Risk Exposure Research) follows.

## Milestone 70 - Candidate Directional Exposure

Added the `spy_edge_research.risk` package with `exposure.py`: descriptive
directional-exposure aggregation for a candidate edge set. `add_exposure_columns`
maps direction (long/short/neutral, with synonyms) to a signed exposure and a
gross exposure (default weight 1.0, optional non-negative weight column);
`summarize_exposure` reports candidate/long/short/neutral counts and gross/net
exposure, overall or grouped. Exposure is descriptive research only and is not a
position size. Tests: `tests/risk/test_exposure.py` (6 passed).

## Milestone 71 - Candidate Signal-Overlap Diagnostics

Added `risk/signal_overlap.py`: `compute_event_mask_overlap` produces pairwise
co-occurrence/Jaccard/correlation across candidate event masks, and
`summarize_signal_overlap` counts redundant pairs above a Jaccard threshold and
reports max/mean Jaccard. Descriptive redundancy research only; not features,
signals, or sizes. Tests: `tests/risk/test_signal_overlap.py` (4 passed).

## Milestone 72 - Candidate Exposure Concentration

Added `risk/concentration.py`: `compute_group_concentration` aggregates gross
exposure by group (instrument/family/regime) with each group's share, and
`summarize_concentration` reports largest share, Herfindahl index, and effective
group count. Descriptive only; not allocation guidance. Tests:
`tests/risk/test_concentration.py` (3 passed).

## Milestone 73 - Advisory Exposure-Limit Checks

Added `risk/exposure_limits.py`: the `ExposureLimits` config dataclass and
`evaluate_exposure_limits`, which compares exposure/concentration/overlap
summaries against configured limits and emits advisory rows with `ok`,
`exceeds_limit`, or `not_evaluated` statuses and flags such as
`risk_overlap_too_high` and `concentration_exceeds_limit`. Flags are advisory
research signals for a human reviewer, never orders or position sizes. Tests:
`tests/risk/test_exposure_limits.py` (4 passed).

## Milestone 74 - Risk Exposure Research Reports

Added `risk/risk_reports.py`: a descriptive risk-exposure report bundle
(exposure, concentration, signal-overlap, limit-check, and caveat tables) with
metadata, structural summary, deterministic CSV/JSON export, and a
forbidden-field guard (rejecting allocation/portfolio/order/position_size/
trade-action field names). Tests: `tests/risk/test_risk_reports.py` (3 passed).

Full-suite command:

```bash
.venv/bin/python -m pytest -q
```

Result:

- Focused MOD 06 tests passed: 20 passed (`tests/risk`).
- Final full suite passed: 699 passed, 4 skipped. The skipped tests require
  matplotlib.

## Milestone 75 - Factor ETF Universe Foundation

Added `instruments/factor_universe.py`: a deterministic single-factor ETF
universe (`FactorDefinition`/`FactorUniverse`) covering momentum, value,
quality, size, low-volatility, and yield styles, mirroring the sector-universe
helpers (create/build/validate/get/list/filter/read/write +
`default_factor_etf_universe`). Research metadata only; not a tradability,
allocation, or execution registry. Tests: `tests/instruments/test_factor_universe.py`.

## Milestone 76 - Factor Context Feature Layer

Added `signal_engine/factor_context_features.py`: causal factor relative-return,
leadership (top/bottom factor + factor-style), and dispersion features, plus a
composing `add_factor_context_features`. Uses only current/prior rows; features
are descriptive context, not allocation or execution instructions. Tests:
`tests/signal_engine/test_factor_context_features.py`.

## Milestone 77 - Factor-Conditioned Event Studies

Added `backtesting/factor_event_study.py`: factor-context conditioned event
outcome summaries, an outcome table built from a validated event catalog, a
context comparison, and context-coverage diagnostics (reusing
`summarize_event_forward_returns`). Descriptive research only. Tests:
`tests/backtesting/test_factor_event_study.py`.

## Milestone 78 - Factor Rotation Research Reports

Added `backtesting/factor_rotation_reports.py`: a descriptive factor-leadership
report bundle (rotation snapshot, leadership persistence, event outcomes,
context coverage, caveats) with metadata, structural summary, deterministic
CSV/JSON export, and a forbidden-field guard. Tests:
`tests/backtesting/test_factor_rotation_reports.py`.

## Milestone 79 - Factor Module Integration

Wired the factor universe, features, event study, and rotation reports into the
`instruments`, `signal_engine`, and `backtesting` package exports. The factor
module mirrors the sector module so factor context can flow through the same
research workflow.

Full-suite command:

```bash
.venv/bin/python -m pytest -q
```

Result:

- Focused MOD 07 tests passed: 20 passed (factor universe, features, event
  study, rotation reports).
- Final full suite passed: 719 passed, 4 skipped. The skipped tests require
  matplotlib.

## Milestone 80 - Research Artifact Access

Added the `spy_edge_research.services` package with `artifact_access.py`:
read-only loading of committed report bundles into a typed `LoadedReportBundle`
(records-oriented JSON via `load_report_bundle_json`, CSV directory via
`load_report_bundle_csv_dir`) plus `discover_report_bundles` to enumerate
bundles under a root. Offline and read-only; no live data or mutation. Tests:
`tests/services/test_artifact_access.py`.

## Milestone 81 - Research Query Helpers

Added `services/research_queries.py`: `list_bundle_tables`, `get_bundle_table`,
`filter_bundle_table`, and `summarize_bundles` answer structural questions over
loaded bundles. Read-only. Tests: `tests/services/test_research_queries.py`.

## Milestone 82 - Workflow Service Facade

Added `services/workflow_service.py`: `run_event_research_workflow_service`
wraps `build_event_research_workflow_outputs` and returns a structured
`WorkflowServiceResponse` (outputs, table names, report summary);
`export_workflow_service_response` writes the report bundle to CSV. Research
orchestration only; reads an in-memory DataFrame, no live data or execution.
Tests: `tests/services/test_workflow_service.py`.

## Milestone 83 - Optional HTTP Layer (deferred)

The optional thin HTTP layer is intentionally deferred: no web framework is in
the project environment, and adding one is out of scope for a research-only,
offline service layer. The function-based service surface (M80-82) is the
supported interface. Revisit only if a local app backend is explicitly approved.

## Milestone 84 - Service Layer Integration

Verified the read-only service surface end to end: a workflow response exports
to a CSV bundle that `load_report_bundle_csv_dir` reloads and the query helpers
inspect. The `services` package is importable as `spy_edge_research.services`.

Full-suite command:

```bash
.venv/bin/python -m pytest -q
```

Result:

- Focused MOD 08 tests passed: 11 passed (`tests/services`).
- Final full suite passed: 730 passed, 4 skipped. The skipped tests require
  matplotlib.

Next recommended module boundary:

- MOD 09 (Dashboard Data Export), per `docs/NEXT_MODULES_ROADMAP.md`.
  Stable, versioned, frontend-ready JSON contracts built from research
  artifacts; a data-contract layer only, descriptive, no UI, no live data, no
  trade-readiness fields.

## Milestone 85 - Dashboard Contract Schema

Added the `spy_edge_research.dashboard` package with `contracts.py`: a versioned
JSON envelope (`DASHBOARD_SCHEMA_VERSION = "1.0"`) via `build_dashboard_contract`
and `validate_dashboard_contract`. Each envelope carries `schema_version`,
`payload_type`, `generated_at_utc`, JSON-safe `tables`, `source` provenance, and
a caveat, with a forbidden-field guard on payload type, table names, and record
keys. Tests: `tests/dashboard/test_contracts.py`.

## Milestone 86 - Dashboard Payload Export

Added `dashboard/export.py`: `build_dashboard_payload_from_bundle` turns a
`LoadedReportBundle` (from the services layer) into a contract payload with
source provenance, and `export_dashboard_payload_to_json` validates and writes
it. Tests: `tests/dashboard/test_export.py`.

## Milestone 87 - Dashboard Export Manifest

Added `dashboard/manifest.py`: `build_dashboard_manifest` records schema version,
payload types, and tables across a set of payloads for traceability, with
`summarize_dashboard_manifest`. Tests: `tests/dashboard/test_manifest.py`.

## Milestone 88 - Dashboard Module Integration

The `dashboard` package composes on top of the services layer: services load a
committed bundle, dashboard builds a versioned contract payload and a manifest.
All contracts are descriptive data only; no UI, live data, or trade-readiness
fields.

Full-suite command:

```bash
.venv/bin/python -m pytest -q
```

Result:

- Focused MOD 09 tests passed: 10 passed (`tests/dashboard`).
- Final full suite passed: 740 passed, 4 skipped. The skipped tests require
  matplotlib.

Next recommended module boundary:

- MOD 10 (Paper-Trading Readiness Criteria), per `docs/NEXT_MODULES_ROADMAP.md`.
  A research-only readiness scorecard/gate (criteria + verdict + reasons), NOT
  paper trading; the paper-trading simulation layer remains separate and
  unauthorized.

## Milestone 89 - Readiness Criteria Definition

Added the `spy_edge_research.paper` package with `readiness_criteria.py`: the
pre-registered `ReadinessCriteria` dataclass (min OOS-positive splits, min OOS
sample size, negative-control pass, multiple-testing pass, min temporal-stable
periods, max pairwise overlap) and `default_readiness_criteria`. Research gates
only; nothing authorizes a trade. Tests: `tests/paper/test_readiness_scoring.py`.

## Milestone 90 - Readiness Scoring & Verdict

Added `readiness_scoring.py`: `score_candidate_readiness` scores a candidate's
research metrics against the criteria (one row per criterion, with a missing
metric treated conservatively as `insufficient_evidence`), and
`summarize_readiness_verdict` reduces it to a gated verdict
(`eligible_for_paper_consideration` / `not_ready`) with failing reasons. A
verdict is a research gate, never trade authorization.

## Milestone 91 - Readiness Scorecard Reports

Added `readiness_reports.py`: a readiness report bundle (scorecard, verdict,
caveats) with metadata, structural summary, deterministic CSV/JSON export, and a
forbidden-field guard (rejecting trade-action / order / sizing / allocation
field names). Tests: `tests/paper/test_readiness_reports.py`.

## Milestone 92 - Readiness Module Integration

The `paper` package consumes diagnostics-style metrics (e.g. OOS stability,
control survival, temporal stability, exposure overlap from earlier modules) and
emits an auditable readiness gate. It performs no paper trading; the
paper-trading simulation layer remains a separate, explicitly-unauthorized
module.

Full-suite command:

```bash
.venv/bin/python -m pytest -q
```

Result:

- Focused MOD 10 tests passed: 10 passed (`tests/paper`).
- Final full suite passed: 750 passed, 4 skipped. The skipped tests require
  matplotlib.

Roadmap status:

- MOD 06-10 (Milestones 70-92) from `docs/NEXT_MODULES_ROADMAP.md` are complete.
  All remain research-only. Any move toward an actual paper-trading simulation
  layer, broker integration, options expression, or live execution requires a
  separate, explicit authorization and a new module boundary.

## Milestone 93 - Readiness Input Assembler (MOD 06 -> MOD 10 bridge)

Added `paper/readiness_inputs.py`: `build_readiness_metrics` assembles the
readiness metrics mapping consumed by `score_candidate_readiness` directly from
upstream research summaries — an OOS stability row (`summarize_oos_edge_stability`),
the MOD 06 risk signal-overlap summary or exposure-limit checks (for
`max_pairwise_jaccard`), and control-pass flags. Read-only reshaping only; it
makes no trade decision. This wires the risk module's overlap output into the
readiness gate instead of relying on a hand-built metrics dict. Tests:
`tests/paper/test_readiness_inputs.py` (4 passed). Full suite: 754 passed,
4 skipped.

Documentation:

- `README.md` now has a "Research Modules (MOD 06-10) — Usage" section with
  runnable examples for the risk, factor, services, dashboard, and paper
  modules. `docs/ARCHITECTURE.md` was refreshed to the Milestone 92+ as-built
  state.

## Milestone 94 - Architecture review hardening & DRY foundation

A code-review-driven hardening pass (research-only). Verified findings only —
several "critical" review claims were checked against source and rejected (the
permutation `>=` convention is correct; the rolling realized-vol "leak" is
causal; bootstrap NaN handling was already clean).

Correctness / clarity:

- `signal_engine/factor_context_features.py` and `sector_context_features.py`:
  the high-dispersion trailing-quantile threshold now uses `.shift(1)` so the
  current bar is compared against strictly prior history and never contributes
  to its own threshold (consistency with the `events`/`regime` convention).
- `backtesting/multiple_testing.py`: `apply_bonferroni_adjustment` gains an
  optional `n_tests` to set the multiplicity family explicitly (default still
  counts p-value-bearing rows); documented the warning thresholds.
- `backtesting/statistical_tests.py`: documented tiny-sample CI unreliability
  and finite-resample p-value flooring (no formula change).
- `backtesting/directional_backtester.py`: documented the zero/NaN-return
  exclusion convention and that it is a research proxy, not a tradable factor.

Maintainability foundation:

- Added `spy_edge_research/_internal/_common.py` with generic, behavior-
  preserving helpers (require_columns, validate_positive_int, normalize_columns,
  created_at_utc, json_safe_value/mapping, dataframe_to_records, raise_if_exists)
  consolidating helpers copy-defined across 60+ modules. Migrated
  `risk/risk_reports.py` to it as a verified proof-of-pattern.
- Top-level `spy_edge_research/__init__.py` now re-exports all 12 subpackages
  (was `market_data` only) for discoverability.
- Added `tests/conftest.py` with shared event-frame/catalog fixtures.

Full suite: 754 passed, 4 skipped.

Staged follow-up (mechanical, to run in tested batches):

- Migrate the remaining report modules and the ~50 modules that still define
  local `_require_columns` / `_validate_positive_int` to `_internal/_common`.
  Best done with an import-cleanup linter (e.g. ruff) to drop now-unused imports.
- Optional: a spec-driven `report_bundle` base to collapse the duplicated
  metadata/validate/summarize/export plumbing across report modules.

## Milestone 95 - Helper migration batch 1 (report modules)

Migrated all 11 `backtesting/*_reports.py` modules to source their generic
helpers (`json_safe_value`/`mapping`, `dataframe_to_records`, `raise_if_exists`,
`normalize_columns`, `created_at_utc`, `require_columns`, `validate_positive_int`)
from `spy_edge_research/_internal/_common.py`, then stripped the now-unused
imports with ruff (F401). Net −424 LOC, behavior unchanged. `event_reports.py`
keeps its own 3-arg `_require_columns` (a `KeyError`-raising signature variant
that differs from the shared 2-arg helper — surfaced by tests during migration).
Full suite: 754 passed, 4 skipped.

Remaining: the ~50 non-report modules that still define local `_require_columns`
/ `_validate_positive_int` / `_normalize_columns` can be migrated the same way
(AST-remove + ruff F401) in further batches, watching for signature variants.

## Milestone 96 - Helper migration batch 2 (non-report backtesting modules)

Migrated 41 non-report `backtesting/*.py` modules to `_internal/_common`, using a
hardened script with a **signature-match guard** that auto-skips call-incompatible
variants (it correctly skipped `candidate_rule_objects._normalize_columns`).
Unused imports stripped with ruff (F401). Net −457 LOC.

One behavioral variant was caught by the full suite, not the signature guard:
`event_run_registry` (and `event_artifacts`, `event_audit_index`,
`event_reproducibility`) had a `_json_safe_value` that serialized `pathlib.Path`
to ``str``. The shared helper didn't, so the fix made the canonical
`_common.json_safe_value` a proper superset by adding `Path -> str` (benefits
every module). `event_reports`'s 3-arg `_require_columns` remains local.

Verified baseline: the full suite is **766 passed, 4 skipped** on both `main`
and this branch (identical results → behavior-preserving). Note: earlier session
entries (M93–M95) quoted "754 passed" from a stale local reading; the suite
count grows as modules are added because `tests/backtesting/test_event_study.py`
parametrizes over source files. 766/4 is the current verified number.

## Milestone 97 - MOD 11: Unified CLI / pipeline runner

Added a new `cli/` package (`spy_edge_research.cli`) that makes the previously
import-only research backend runnable end-to-end from one command. This is the
first module of the post-readiness-gate "functional app" build-out (remaining
roadmap: MOD 11 runner -> MOD 14 paper-sim -> MOD 12 frontend -> MOD 13
value/quality/momentum).

New files:

- `cli/pipeline.py` - `run_pipeline(input_csv, output_root, *, run_id, config,
  overwrite)`: a pure, importable orchestration that threads one OHLCV frame
  through existing stage functions only (no stage logic is reimplemented):
  load -> indicators -> causal events -> forward labels -> event-study workflow
  service -> report-bundle export -> candidate-edge registry -> risk
  signal-overlap -> walk-forward OOS stability -> dashboard contract export ->
  per-candidate paper-trading readiness scorecard. A small glue adapter maps
  event-study result rows into validated `create_candidate_edge` records.
- `cli/run_artifacts.py` - deterministic timestamped run layout
  (`reports/run_<UTC>/...`) and a `run_manifest.json` writer that records
  per-stage status, provenance, metrics, and research caveats (reuses
  `create_research_run_metadata`).
- `cli/main.py` + `cli/__init__.py` - argparse entry point (no new
  dependencies) with subcommands `run-pipeline`, `export-dashboard`,
  `score-readiness`, `list-runs`. Registered as the `spy-edge` console script
  via `[project.scripts]` in `pyproject.toml`.

Scope note (deliberate): the basic pipeline wires OOS stability and risk overlap
into the readiness gate but does NOT run the negative-control, multiple-testing,
or temporal-stability batteries. Those readiness metrics are left unprovided, so
the gate honestly reports them as insufficient evidence and verdicts remain
`not_ready` until the full battery is run. The run manifest discloses this with
the `control_batteries_not_run_in_basic_pipeline` caveat. Everything remains
research-only and descriptive: no trade signals, orders, sizing, or execution;
the readiness verdict is a research gate, not a trade authorization. The causal
invariant is unchanged (`forward_*` columns are evaluation labels only).

Tests: `tests/cli/` (`test_pipeline.py`, `test_cli_main.py`, `test_list_runs.py`
+ a `conftest.py` synthetic-OHLCV fixture) - 12 passed. End-to-end verified via
the installed `spy-edge` console script. Full suite: 766 passed, 4 skipped (the
4 skips require matplotlib).

## Milestone 98 - MOD 14: Paper-trading SIMULATION layer (authorized boundary crossing)

The project's **first module past the research-only readiness gate**, built under
**explicit user authorization (2026-06-13)**. It simulates positions, fills, and
P&L on *historical* bars only — it is NOT live trading and NOT a broker. Still
forbidden until a further explicit OK: real broker/money, live/real-time
execution, order routing, accounts, options.

New package `src/spy_edge_research/simulation/`:

- `contracts.py` - sim data model (`SimFill`, `SimPosition`, `SimTrade`,
  `EquityPoint`) + the layer's **own** forbidden-field validator. Sim records
  intentionally use `entry_price` / `exit_price` / `pnl_points` (which the
  research guards `candidate_rule_objects.FORBIDDEN_RULE_OBJECT_FIELDS` and
  `dashboard.contracts.FORBIDDEN_DASHBOARD_FIELDS` reject) — so sim records must
  never be round-tripped through those. `validate_sim_report` requires the
  mandatory `sim_caveat = "simulation_only_no_broker_no_real_money"` and rejects
  the *next* boundary out (whole-token `broker`/`live`/`route`/`account`/`order`/
  `option`/`margin`/`money`/...).
- `execution_model.py` - deterministic `ExecutionModel` (round-trip `cost_bps`
  charged against gross return; fixed unit `quantity`; no randomness, no broker).
- `position_sim.py` - `simulate_candidate_positions`: walks bars, opens a
  position each time a candidate's event column fires (entry decided **causally**
  from rows <= t), holds for the candidate's fixed horizon, and closes at the
  historical close that many bars later. Exits reuse
  `backtesting.labels.add_forward_return_labels` (a forward column is the right
  tool to *close* a position opened at t, never to *trigger* one). Positions whose
  horizon can't resolve same-day are not opened (counted, not silently dropped);
  non-directional candidates are skipped and counted.
- `pnl.py` - per-trade ledger, realized equity curve (P&L booked at each exit
  bar), max drawdown, descriptive summary (win rate, gross/net mean bps, total
  P&L, drawdown).
- `eligibility.py` - `select_eligible_candidates`: applies the MOD 10 readiness
  gate as a filter (verdict == `eligible_for_paper_consideration`). The simulator
  accepts any candidate list for research; callers wanting the gated subset filter
  first. Simulating a not-yet-eligible candidate is research-descriptive only and
  never an authorization.
- `sim_reports.py` - assembles a validated, JSON-safe report bundle (reusing
  `_internal/_common`) and writes it to disk.

Invariants held: causal entries; deterministic (no RNG); reuses existing
label/`_common` code rather than reimplementing. Newly allowed (the authorized
crossing): persisted position state, P&L, equity curve, drawdown, simulated fills
with explicit cost assumptions.

Tests: `tests/simulation/` (`test_position_sim.py`, `test_pnl.py`,
`test_sim_contracts.py`, `test_sim_reports_and_eligibility.py` + a `conftest.py`
rising-market fixture) - 25 passed. P&L cross-checked against the forward-return
labels by hand. Full suite: 791 passed, 4 skipped.

## Milestone 99 - MOD 12: Dashboard frontend (zero-build static viewer)

A research-only frontend that consumes the MOD 09 versioned dashboard JSON
contracts (schema 1.0) emitted by `dashboard/export.py` and written by the MOD 11
runner. Lives **outside** the Python package in `frontend/` so packaging/pytest
are unaffected.

- `frontend/index.html` - a single self-contained file (HTML + CSS + vanilla JS,
  no dependencies, no build step, fully offline). Loads a dashboard contract via
  a local file picker, drag-and-drop, or `?src=URL` / URL box (fetch when
  served). Validates `schema_version == "1.0"`, renders the `dashboard_caveat`
  banner prominently and the provenance header, and renders each `tables` entry
  as a scrollable HTML table. Surfaces (as warnings) any forbidden research-
  dashboard field and any unknown schema version. It is a pure consumer of
  committed JSON — no live data, descriptive research only, no trade
  instructions.
- `frontend/README.md` - usage (file pick / drag-drop / `python -m http.server`
  + `?src=`).

Deviation (recorded): the roadmap named a Vite/React SPA, but this environment
has no Node toolchain and a single static file is the more robust, offline-pure
fit for the contract-as-boundary design; the integration contract is identical
and a richer SPA could read the same JSON later.

Tests: `tests/frontend/test_dashboard_contract_compatibility.py` pins the exact
contract envelope keys, schema version, table shape, caveat, and forbidden-field
absence the UI depends on, so backend schema drift fails in CI (4 passed).
Verified live by serving `frontend/` and rendering a real `spy-edge` run's
`event_study.json` through the page's own `render()` (4 tables, 72 rows, caveat
shown, no false warnings). Full suite: 796 passed, 4 skipped.

## Milestone 100 - MOD 13: Value/Quality/Momentum cross-sectional factor research

Phase-8 systematic factor research, built only from OHLCV price data (the platform
ingests no fundamentals). Distinct from MOD 07 (which studies factor *ETFs* as
instruments): this scores **any** symbol universe cross-sectionally from price
alone. Mirrors the factor-module trio (`*_features` -> `*_event_study`).

- `signal_engine/value_quality_momentum_features.py` - causal per-symbol factor
  scores on a timestamp-aligned multi-symbol frame (`{SYMBOL}_close` columns):
  **momentum** (trailing return), **quality** (negative trailing realized
  volatility - steadier = higher), **value** (negative recent return - recently
  cheaper = higher). `add_cross_sectional_factor_ranks` ranks each score across
  symbols per row as a [0,1] pct rank (same-row only - no look-ahead);
  `add_value_quality_momentum_features` composes all three + ranks + a composite
  VQM rank + a caveat column. All scores use current/prior rows only.
- `backtesting/vqm_event_study.py` - buckets rows by a factor score (rank-based
  quantiles, robust to ties), summarizes the forward outcome label per bucket,
  the descriptive top-minus-bottom `outcome_mean_spread`, and coverage; plus a
  report bundle and a CSV exporter. Causality preserved: the score is a feature,
  the outcome is a `forward_*` label; the spread is a descriptive statistic, not
  an edge claim, allocation, or trade signal.

Both reuse `_internal/_common` helpers and are exported from the `signal_engine`
and `backtesting` package `__init__`s.

Tests: `tests/signal_engine/test_value_quality_momentum_features.py` (incl. a
truncation-based no-look-ahead check and exact cross-sectional rank math) and
`tests/backtesting/test_vqm_event_study.py` (bucketing, spread sign, coverage,
CSV round-trip, overwrite guard) - 12 passed. Full suite: 808 passed, 4 skipped.

This completes the user-approved functional-app build-out: MOD 11 runner (M97),
MOD 14 paper-sim (M98), MOD 12 frontend (M99), MOD 13 VQM research (M100).

## Milestone 101 - Control batteries wired into the pipeline runner

First step of the user-approved staged "Trader module" build-out (destination:
human-approved live execution, reached only through hard validation gates). This
step needs no new authorization and is the empirical go/no-go gate for the rest.

The MOD 11 runner previously skipped the negative-control / multiple-testing /
temporal-stability batteries, so every candidate was permanently stamped
`not_ready` (`control_batteries_not_run_in_basic_pipeline`) and nothing could
ever reach `eligible_for_paper_consideration`. M101 wires the batteries in:

- `cli/control_batteries.py` - `run_control_batteries(df, registry)` reduces the
  three batteries to the scalars the readiness gate consumes. **Negative control**
  (per candidate): builds shifted + random controls on the event column, compares
  the candidate's forward-return expectancy difference, passes iff the observed
  edge is finite and no control matches/exceeds it. **Multiple testing**
  (portfolio): no per-candidate p-values exist in the basic pipeline, so it
  applies the module's own family-size heuristic - pass iff `< 100` tested
  hypotheses (warning != "high"); caveated as a heuristic. **Temporal stability**
  (per candidate): counts distinct calendar periods (months) in which the event
  produced an outcome -> `temporal_stable_period_count`. Reuses the committed
  `backtesting/` battery functions; reimplements no statistics.
- `cli/pipeline.py` - new Stage 9.5 runs the batteries (new `PipelineConfig.
  run_control_batteries`, default **on**), writes `run_<id>/controls/*.csv`, and
  threads per-candidate negative-control + temporal counts and the portfolio
  multiple-testing pass into `_score_readiness`. When batteries run the not-run
  caveat is dropped and the (advisory) battery caveats are disclosed; batteries-off
  restores the prior disclosure.
- `cli/run_artifacts.py` - three new `RunPaths` artifact paths under `controls/`.

Tests: `tests/cli/test_control_batteries.py` (batteries fire on a real edge vs a
wrong-direction null; multiple-testing high-family flag; and the readiness verdict
**flips to `eligible` only when every criterion passes**) plus updated
`tests/cli/test_pipeline.py`. Full suite: 816 passed, 4 skipped.

Causal / no-lookahead invariant unchanged: forward-return columns are read as
outcome labels only. Outputs remain descriptive research diagnostics - never a
trade signal, order, or authorization.

**Hard Gate A (pending real data):** run the pipeline on a real multi-month SPY
1-minute CSV and inspect `run_<id>/readiness/verdict.csv`. If no candidate reaches
`eligible_for_paper_consideration`, there is no validated edge and Stages 2-4
(decision_support, broker-prep, live execution) do not proceed - a valid result.

## Milestone 102 - decision_support package (Phase 12, human-in-the-loop)

Stage 2 of the staged Trader build-out. New `src/spy_edge_research/decision_support/`
takes candidates that cleared the research readiness gate and assembles a
*descriptive* per-candidate review surface for a human to consider. It authorizes
nothing, sizes nothing, and routes no orders.

- `decision_support/contracts.py` - `DECISION_SUPPORT_REPORT_CAVEAT`
  (`decision_support_analysis_is_research_only_requires_human_review`),
  `FORBIDDEN_DECISION_SUPPORT_FIELDS` (a superset of the upstream research/sim
  forbidden tokens - adds broker/route/execution/money/account/...), and the
  bundle validator.
- `decision_support/recommendation.py` - `build_decision_support_records`
  reuses `simulation.select_eligible_candidates` to keep only
  `eligible_for_paper_consideration` candidates, emitting one review record each
  (direction, horizon, sample_size, expectancy_difference, verdict, portfolio
  `risk_flags`, `requires_human_review=True`, caveat). `summarize_decision_support`
  counts by direction / risk-flag presence.
- `decision_support/reports.py` - standard `{metadata, tables}` bundle with
  `build_*`, `summarize_*`, and deterministic `export_*_to_csv/json`; reuses
  `_internal/_common` helpers.

Like `simulation`, this post-gate package is intentionally kept OUT of the
top-level package re-export. Tests: `tests/decision_support/test_decision_support.py`
(eligible-only filtering, empty set, risk-flag surfacing, forbidden-field
rejection, CSV/JSON round-trip, clobber guard). Full suite: 822 passed, 4 skipped.

Still gated: a decision support record is not an instruction; broker preparation
and live execution remain separate modules and require the real-data Hard Gate A
plus an explicit per-deployment authorization before anything can run live.

## Milestone 103 - broker preparation sandbox (Phase 13, Alpaca paper, no real money)

Stage 3 of the staged Trader build-out. New `src/spy_edge_research/broker/` turns
a human-approved order intent into a dry-run order against Alpaca's PAPER endpoint
with a full audit trail. **No real money; reaching a live endpoint is structurally
impossible from this module.**

- `broker/order_intent.py` - frozen `OrderIntent`; `build_order_intent_from_review`
  builds one ONLY from a decision-support review record with `human_approved=True`
  (refuses otherwise) and maps direction long/short -> side buy/sell.
- `broker/safety.py` - `TradingLimits` (tiny fail-closed defaults), `KillSwitch`,
  and `check_order_against_limits` (kill-switch, missing-approval, non-positive
  qty, per-order and open-position quantity caps, daily-loss cap) -> violation
  codes; `BrokerSafetyError`.
- `broker/audit.py` - append-only JSONL log (`append_audit_event` / `read_audit_log`);
  no secrets ever written.
- `broker/alpaca_adapter.py` - `AlpacaSandboxAdapter` hard-pinned to the paper
  endpoint (constructor refuses any non-sandbox mode or non-paper endpoint);
  `dry_run=True` default needs no network/credentials; `alpaca-py` is an optional
  dependency. Every submission audits intent_received -> (rejected | result).

The order/side vocabulary lives inside this authorized boundary, so the research
forbidden-field guards do not apply here. Credentials are env-only, never in the
repo. Tests: `tests/broker/test_broker_sandbox.py` (approval requirement,
direction->side, sandbox/endpoint refusal, dry-run accept+audit, limit/kill-switch
rejection, injected-client paper submit). Full suite: 830 passed, 4 skipped.

Still gated: live execution is a separate module; nothing here can place a real
order. Real runs additionally require Hard Gate A (an eligible edge on real data).

## Milestone 104 - live execution adapter (Phase 14, INERT unless explicitly enabled)

Stage 4 (final code stage) of the staged Trader build-out. `broker/live_adapter.py`
adds the only code path that can place a real-money order - designed to be
impossible to trigger by accident behind three independent gates:

1. **Env flag** - the constructor raises `BrokerLiveDisabledError` unless
   `SPY_EDGE_ALLOW_LIVE=1` is set in the process env (fail closed).
2. **Per-order human approval** - every `submit_intent` requires a
   `human_approval_token` that equals that specific intent's id. There is no
   batch path and no autonomous path; a human confirms each order by id.
3. **Limits + kill-switch** - the same `TradingLimits` / `KillSwitch` checks as
   the sandbox, applied before any submit.

There is deliberately no dry-run/live mode (a live submit needs a configured
client) and credentials are env-only. `AlpacaLiveAdapter` is hard-pinned to the
live endpoint and refuses any other; the sandbox adapter remains hard-pinned to
paper. Tests (`tests/broker/test_broker_live.py`) inject a fake client and pass
the env flag as an explicit dict - **no test places a real order**: they verify
the adapter is disabled without the flag, rejects a non-matching approval token
(placing no order), enforces limits and the kill-switch, refuses to run without a
client, and only submits + audits when every gate holds. Full suite: 837 passed,
4 skipped.

**This completes the staged Trader build-out code (M101-M104).** What remains is
NOT code: **Hard Gate A** - run the pipeline on real multi-month SPY 1-minute data
and confirm >=1 candidate reaches `eligible_for_paper_consideration` - and, only
after a clean Alpaca paper-sandbox run on that real edge, an explicit
per-deployment decision to set `SPY_EDGE_ALLOW_LIVE=1`. Until then the live path
is inert by construction.

## Hard Gate A — first real-data run (2026-06-14) and what it exposed

Fetched 189,663 real SPY 1-min bars (2024-06..2026-06, Alpaca IEX feed, regular
hours) via `scripts/fetch_spy_bars.py` and ran the pipeline (`scripts/
run_hard_gate_a.py`, OOS train=30000 / test=7500). 42 candidates, and **15
initially reached `eligible`** — but inspecting magnitudes showed every "edge" was
**0.06–0.46 basis points**: statistically detectable only because of huge samples
(4k–43k events), and far below SPY round-trip cost (~1 bp). Statistical
detectability at large N is not a tradeable edge. The gate had a real gap: no
economic-significance criterion.

## Milestone 105 - economic-significance (cost-floor) readiness criterion

Closes that gap. `ReadinessCriteria` gains `min_edge_bps` (default **1.0 bps**, a
conservative round-trip cost-floor proxy; configurable; `None` disables).
`build_readiness_metrics` now derives `edge_bps` from the OOS summary's
`oos_mean_expectancy_difference` (out-of-sample, x1e4), and `score_candidate_
readiness` adds an `economic_edge_bps` criterion (`edge_bps >= min_edge_bps`).
A candidate that is statistically clean but sub-cost now fails with
`economic_edge_bps_below_min`.

Re-running Hard Gate A with the floor: **0 of 42 eligible** — all rejected on
`economic_edge_bps_below_min`. The honest result: **no validated edge on this
data; the broker layers stay OFF.** Tests: new `test_sub_cost_edge_is_not_ready`
plus updates to the readiness/control-battery suites for the 7th criterion. Full
suite: 838 passed, 4 skipped.

Caveats on the run itself: IEX is a thin single-venue feed (volume understated —
volume-based candidates especially suspect); 42 hypotheses tested carries
multiple-testing risk only coarsely guarded by the family-size heuristic; no
slippage model. Even an above-floor result here would warrant SIP-quality data
and a stricter multiple-testing correction before any sandbox/live consideration.

## Milestone 106 - rigorous per-candidate multiple-testing (permutation + FDR)

First of the post-Hard-Gate-A robustness improvements. Replaces the coarse
family-size heuristic with real statistics: for each candidate the control
battery runs `permutation_test_event_vs_baseline` (event vs non-event forward
outcome, n_permutations=500 default, baseline/event subsampled to <=20000 for
speed), then applies a Benjamini-Hochberg FDR correction across the whole
candidate family. A candidate's `multiple_testing_passed` is now True only if its
FDR-adjusted p-value is below alpha (default 0.05).

- `cli/control_batteries.py`: per-candidate permutation p-value + family-wide FDR
  (`_permutation_pvalue_for`, `_build_multiple_testing_table`); new config
  (`n_permutations`, `multiple_testing_alpha`, `permutation_seed`,
  `max_permutation_sample`). The portfolio family-size warning is retained only as
  a coarse summary / no-OOS fallback. `controls/multiple_testing.csv` is now a
  per-candidate table (candidate_id, n_event, p_value, p_value_fdr_bh, alpha,
  passed).
- `cli/pipeline.py`: `_score_readiness` prefers the per-candidate FDR result,
  falling back to the portfolio pass only when no per-candidate value exists.

Tests: per-candidate pass for a real edge, fail for a null; existing suites green.
Full suite: 840 passed, 4 skipped.

## Milestone 107 - slippage in the execution model

Second robustness improvement. `simulation/ExecutionModel` now separates
`cost_bps` (commissions/fees) from a new `slippage_bps` (market-impact/spread:
the gap between the bar-close fill the simulator assumes and the price a real
order would achieve). `net_return_bps` subtracts both (`total_cost_bps` property);
`slippage_bps` defaults to 0.0 so existing behaviour and tests are unchanged. It
is a flat, conservative round-trip charge (no per-fill distribution yet) - the
honest floor; a volatility/volume-scaled model could extend it later. Tests:
`tests/simulation/test_execution_model.py`. Full suite: 844 passed, 4 skipped.

## Milestone 108 - Deflated Sharpe Ratio + Probability of Backtest Overfitting

Build 4, Amendment 1 (constitutional upgrade of the anti-overfitting stack to the
López de Prado deflation framework; see `Auto-Trader Build/RESEARCH_C_DECISION.md`
§4.3, which names the Deflated Sharpe Ratio "THE BINDING CONTROL" and PBO < 0.5 as
a pass gate). New pure module `backtesting/deflated_sharpe.py`:

- `probabilistic_sharpe_ratio` / `..._from_moments` - Bailey & López de Prado
  (2012): P(true SR > benchmark), correcting for sample length, skewness, and
  (Pearson) kurtosis.
- `expected_maximum_sharpe_ratio` - the Sharpe a researcher should expect purely
  from selecting the best of N trials (0.0 for a single trial / non-positive
  variance).
- `deflated_sharpe_ratio` - DSR (Bailey & López de Prado 2014): the PSR with the
  benchmark set to that expected maximum, so the luckiest-of-many deflates toward
  and below 0.5.
- `probability_of_backtest_overfitting` - PBO via Combinatorially Symmetric
  Cross-Validation (Bailey-Borwein-LdP-Zhu 2017) over a (T observations x N
  configs) panel.
- OOS adapters `summarize_candidate_deflated_sharpe` / `portfolio_pbo_from_oos`:
  the candidate OOS per-split expectancy-difference results ARE the panel the
  deflation stack needs (rows = splits, columns = candidates), so DSR/PBO are
  derived from already-computed research numbers, not a re-fit.

No SciPy in the venv, so the standard-normal CDF uses `math.erf` and the inverse
CDF uses Acklam's rational approximation (~1e-9). Research-only measurement: no
trade authorization, no I/O, pure functions. Exported from `backtesting`.
Tests: `tests/backtesting/test_deflated_sharpe.py` (20). Full suite: 864 passed,
4 skipped. Wiring into the readiness gate is M109.

## Milestone 109 - wire the deflation stack into the readiness gate

Build 4, Amendment 1 (completion). The M108 Deflated Sharpe / PBO measurements
now bind as readiness criteria, supplementing — not replacing — the M106 BH/FDR
multiple-testing gate, exactly as the constitutional amendment specifies.

- `ReadinessCriteria` gains `max_pbo` (default **0.5**: PBO >= 0.5 means selection
  is no better than chance) and `min_deflated_sharpe` (default **0.5**: at-even
  odds the edge beats the expected best-of-N-trials benchmark). `None` disables.
- `readiness_scoring` adds two criteria — `backtest_overfit_probability`
  (`pbo <= max_pbo`) and `deflated_sharpe` (`deflated_sharpe >= min_deflated_sharpe`)
  — taking the gate from 7 to 9 criteria. Missing metrics stay conservatively
  `insufficient_evidence` (not ready).
- `build_readiness_metrics` accepts `pbo` / `deflated_sharpe` pass-throughs.
- `cli/pipeline.py`: a single `_safe_oos_results` now sources both the Stage 9
  stability summary and a new **Stage 9.25 deflation** stage, which derives the
  per-candidate Deflated Sharpe (`summarize_candidate_deflated_sharpe`) and the
  portfolio PBO (`portfolio_pbo_from_oos`) from the same OOS per-split panel and
  feeds them into `_score_readiness`. No edge is re-fit.

Effect on Hard Gate A: the chart-pattern candidates already failed on economic
significance; they now face two additional overfitting gates. The gate stays
closed (the designed NEGATIVE result) and is strictly harder to pass — a true
edge must now also survive deflation. Tests: 3 new readiness-scoring cases (high
PBO, low deflated Sharpe, missing-metric) + a control-battery deflation-fail case;
updated eligible-path fixtures. Full suite: 868 passed, 4 skipped.

## Milestone 110 - regime-conditioned intraday-momentum signal family (Path 2)

Build 4, Amendment 2 (scaffold). The first signal family deliberately *disjoint*
from the killed 42 chart-pattern candidates: it conditions on the sign of a
realized clock-window return, not on price geometry. This is Path 2 from
`Auto-Trader Build/RESEARCH_C_DECISION.md` — the most-replicated short-horizon
equity effect (Gao-Han-Li-Zhou 2018; Bogousslavsky 2016; Heston-Korajczyk-Sadka
2010), evaluated under the project's full honesty harness.

New module `signal_engine/intraday_momentum_features.py`
(`add_intraday_momentum_features`, `find_intraday_momentum_event_columns`):

- **Signal.** Over a fixed early-session window (default 09:30-10:00 ET), the
  open-to-window-end return `r_open`; directional hypothesis `sign(r_open)`,
  emitted on the *decision bar* (first bar at/after the window end), using only
  bars up to and including it.
- **Regime gate.** Realized volatility of 1-min returns over the same window vs a
  trailing high-vol threshold = rolling quantile (default 66th pct, 20-day
  lookback) of *prior* sessions' window vol, `.shift(1)` so a session never sets
  its own threshold (same trailing-quantile discipline as `market_regime`).
- **Events.** Boolean `event_mim_long` / `event_mim_short` (gated to the high-vol
  regime) plus ungated `event_mim_long_all` / `event_mim_short_all` baselines, so
  the family flows through the same candidate / Hard-Gate-A pipeline — a new set
  of candidates through the same gate, not a new gate.

Strictly causal: forward returns are added separately as labels; nothing here
looks forward. Research-only feature engineering — no trade signal/order/sizing.
Exported from `signal_engine`. Tests:
`tests/signal_engine/test_intraday_momentum_features.py` (7). Full suite: 875
passed, 4 skipped. Pipeline + study wiring is M111.
