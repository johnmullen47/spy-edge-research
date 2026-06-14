# SPY Directional Edge Research

This project is a research-grade scaffold for testing whether specific intraday
SPY price-action events show statistically meaningful directional continuation
over the next 5, 10, 15, and 30 minutes.

Canonical workspace:

```text
/Users/johnmullen/Documents/Codex/Auto-Trader SPY
```

Private GitHub remote:

```text
https://github.com/johnmullen47/spy-edge-research
```

This folder is now the unified authoritative project root. The former flat
`Auto-Trader SPY` scaffold has been archived under
`legacy_auto_trader_spy_scaffold/`; future work should use `src/`,
`tests/`, `MASTER_PROJECT_BRIEF.md`, `PROJECT_MILESTONES.md`,
`CODEX_MASTER_DESK.md`, and this README in the current root.

For the ChatGPT-side trading theory, research philosophy, signal vocabulary,
and thesis context behind this repo, see
[`docs/CHATGPT_TRADING_THEORY_HANDOFF.md`](docs/CHATGPT_TRADING_THEORY_HANDOFF.md).
That document explains the project "why"; use the live handoff, milestones, and
code for current implementation state.

Current verified state:

- Completed through Milestone 107.
- Latest full suite: `844 passed, 4 skipped`.
- Hard Gate A ran on real SPY 1-minute data and found `0 of 42` candidates
  eligible after M105-M107 hardening.
- Broker/live layers remain off; there is no validated intraday edge in the
  current candidate set.

Milestone 1 implements the local data foundation: loading, validating,
session classification, and causal OHLCV resampling.

Milestone 2 adds causal price-action event primitives. These are reusable
building blocks for later named events, not trading signals, backtests, edge
claims, labels, or forward-return analytics. Trailing references exclude the
current bar when they represent prior levels, and no future candles are used.

Milestone 3 adds causal technical indicator foundations for VWAP, EMA,
Bollinger Bands, ATR, ADX, and volume features. These are reusable numeric
features for later research modules, not strategy signals or edge claims.

Milestone 4 adds forward labeling utilities for later statistical evaluation.
These labels are evaluation targets only and are the only module so far allowed
to look forward. They must not be used as causal features, event inputs,
indicator inputs, or trading signals.

Milestone 5 adds simple baseline benchmark predictions and minimal directional
evaluation utilities. Implemented baselines include always long, always short,
deterministic random direction, VWAP relation, EMA relation, and trailing break
event benchmarks. These are benchmark predictions, not production trading
signals. Evaluation compares baseline predictions against the forward labels
from Milestone 4. Directional return and profit-factor-equivalent metrics are
research proxies only, not real P/L. No strategy engine, confidence scoring,
portfolio accounting, execution, slippage, or edge claims are implemented.

Milestone 6 adds causal market-structure primitives: confirmed pivot highs and
lows, last confirmed pivot levels, higher-high/lower-high/higher-low/lower-low
classification, bullish and bearish structure breaks, and a primitive structure
state. Pivot candidates may require future bars internally, but causal pivot
features are emitted only on the later confirmation row. Market-structure
features are not trading signals. No support/resistance zones, market regimes,
scoring, strategy signals, advanced analytics, or edge claims are implemented.

Milestone 7 adds causal support/resistance level and zone features: prior-day
high/low/close levels, same-day premarket high/low levels, simple price zones
around levels, repeated touch counts, nearest support/resistance zone lookup,
and basic zone scoring utilities. Zones are features only, not trading signals
or edge claims. Prior-day levels use only completed prior local dates.
Premarket levels are cumulative during premarket and fixed during regular
session. Confirmed pivot levels may be zoned only after they exist. No strategy
engine, confidence scoring, backtest claims, execution, regimes, advanced
analytics, plots, or reports are implemented.

Milestone 8 adds causal market-regime context features and simple rule-based
regime classification. Directional regimes are Trending Up, Trending Down,
Range Bound, and Unknown. Volatility regimes are High Volatility, Normal
Volatility, Low Volatility, and Unknown. Regimes use only current and prior
information, are context features only, are not trading signals, and do not
claim edge. Forward labels are not used in regime classification. Regime
diagnostics summarize counts, transitions, and consecutive-run durations only;
they do not analyze returns or performance.

Milestone 9 adds causal retest and false-break event features. Implemented
features include retests of standard support/resistance zones, retests of
recently broken trailing levels, recent break context tracking, false breakout
events, false breakdown events, and trailing event counts. These are event
features only, not trading signals. False-break events are emitted only when
failure is known at the current row and are not backdated to the original break
candle. No future candles, labels, forward returns, performance analytics, or
edge claims are used. No strategy engine, confidence scoring, or execution is
implemented.

Milestone 10 adds named causal event definitions. Implemented named events
include VWAP reclaim/loss/rejection/bounce, trailing breakout/breakdown,
standard support/resistance zone breaks, structure break/context events, retest
confirmation events, failed breakout/failed breakdown, momentum/range/volume
event combinations, and trend-continuation context events. Named events are
feature columns only: they are not trading signals, are not scored, and do not
claim edge. No forward labels, future returns, performance analytics, or
execution are used. False-break named events are copied only from already-causal
Milestone 9 false-break columns and are not backdated.

Milestone 11 adds a named event catalog and event-study evaluation utilities.
The event catalog maps named event columns to research-direction hypotheses
using the metadata values long, short, neutral, and unknown. Event-study
evaluation summarizes event occurrences against existing forward-label columns,
with forward labels remaining evaluation targets only. Event direction mappings
are research hypotheses, not trading signals. Event-study outputs are separate
descriptive research summaries. No event scoring, confidence ranking,
optimization, strategy signal generation, execution, or edge claims are
implemented.

Milestone 12 adds research-only event-study diagnostics and quality controls.
Diagnostics provide sample-size flags, label coverage summaries, event coverage
summaries, and grouped descriptive summaries for existing event-study outputs.
These diagnostics are descriptive research quality controls only. They do not
rank events, optimize thresholds, create signals, or claim edge. Forward-label
columns remain evaluation-only and are not used by causal feature/event
generation.

Milestone 13 adds research-only reporting and export utilities for event-study
and diagnostic outputs. Report bundles can be exported reproducibly to CSV or
records-oriented JSON as portable research artifacts. These utilities do not
rank events, optimize thresholds, create signals, or claim edge. Forward-label
data remains evaluation-only and is not used by causal feature or event
generation.

Milestone 14 adds research-only visualization helpers for event-study,
diagnostic, and reporting artifacts. Table helpers prepare deterministic
event-count, label-coverage, event-coverage, and grouped-summary views, and
optional plotting helpers lazily use matplotlib when available. These helpers
are research review tools only: they do not rank events, optimize thresholds,
create signals, or claim edge. Forward-label data remains evaluation-only and
is not used by causal feature/event generation. No frontend app, live
dashboard, alerts, or live data integration was added.

Milestone 15 adds a research-only workflow helper that composes the event
catalog, event-study, diagnostics, reporting, and visualization-prep utilities
into reproducible artifact dictionaries. Workflow outputs are research
artifacts only. The workflow does not create strategy signals, rank events,
optimize thresholds, simulate P/L, or claim edge. Forward-label data remains
evaluation-only and is not used by causal feature/event generation.

Milestone 16 adds research-only artifact manifest and index helpers for
tracking exported workflow and report artifacts reproducibly. Manifests record
what files were produced, where they were written, what output each file
corresponds to, and what metadata describes the run. Artifact helpers do not
inspect outcomes, rank events, create signals, optimize thresholds, simulate
P/L, or claim edge. Forward-label data remains evaluation-only and is not used
by causal feature/event generation.

Milestone 17 adds research-only run registry and manifest-consumption helpers
for loading and indexing multiple artifact manifests. Registry helpers summarize
run and artifact inventory plus metadata-key consistency only. They do not read
event-study artifact contents, inspect outcomes, rank runs or events, create
signals, optimize thresholds, simulate P/L, or claim edge. Forward-label data
remains evaluation-only and is not used by causal feature/event generation.

Milestone 18 adds research-only registry audit/export helpers for reproducible
review of run-summary, artifact-summary, and metadata-consistency tables. Audit
helpers export deterministic CSV and records-oriented JSON artifacts. They do
not read artifact contents, inspect outcomes, rank runs or events, create
signals, optimize thresholds, simulate P/L, or claim edge. Forward-label data
remains evaluation-only and is not used by causal feature/event generation.

Milestone 19 adds research-only audit index helpers for locating and indexing
exported registry audit bundles. Audit index helpers read audit metadata JSON
only and track known audit table file paths. They do not read audit table
contents, inspect outcomes, rank audits/runs/events, create signals, optimize
thresholds, simulate P/L, or claim edge. Forward-label data remains
evaluation-only and is not used by causal feature/event generation.

Milestone 20 adds research-only audit-index report/export and structural
comparison helpers. Audit-index report helpers export audit summary, audit table
path summary, and structural comparison tables. They do not read audit CSV
contents, inspect outcomes, rank audits/runs/events, create signals, optimize
thresholds, simulate P/L, or claim edge. Forward-label data remains
evaluation-only and is not used by causal feature/event generation.

Milestone 21 adds research-only reproducibility checklist helpers. Checklist
helpers validate expected metadata keys, run-registry and audit-index
structure, and file existence only. They do not read audit table contents,
inspect artifact contents or outcomes, rank audits/runs/events, create signals,
optimize thresholds, simulate P/L, or claim edge. Forward-label data remains
evaluation-only and is not used by causal feature/event generation.

Milestone 22 adds research-only reproducibility report/export helpers.
Reproducibility report helpers package checklist summaries, checklist status,
registry summaries, and audit-index summaries into deterministic CSV or JSON
artifacts. They do not read audit table contents, manifest contents, artifact
contents, inspect outcomes, rank audits/runs/events, create signals, optimize
thresholds, simulate P/L, or claim edge. Forward-label data remains
evaluation-only and is not used by causal feature/event generation.

Milestone 23 adds research-only forward path outcome labels. Path outcome
helpers calculate future high/low windows, maximum favorable excursion,
maximum adverse excursion, and optional long/short direction-normalized
outcomes. These columns are evaluation targets only. They intentionally inspect
future bars, exclude the current bar from forward path windows, optionally
prevent horizon windows from crossing local trading dates, and must not be
used as causal features, event inputs, indicator inputs, or trading signals.

Milestone 24 adds research-only event forward-outcome study helpers. These
helpers summarize already-created causal event columns against existing forward
return/path outcome columns, including event sample size, full valid-outcome
baseline comparison, hit rate, expectancy, and explicit sample-size flags.
They do not rank events, test significance, optimize thresholds, create
signals, simulate P/L, or claim edge.

Milestone 25 adds research-only conditional event study helpers. Conditional
helpers evaluate event/outcome summaries inside existing causal context
buckets, such as VWAP regime, volatility regime, trend state, or session
segment. Baseline comparisons are calculated within the same context bucket so
context effects are not mixed with event effects. Ranking helpers are simple
research-review sorting utilities only; they do not claim significance or
tradability.

Milestone 26 adds causal event sequence helpers. Sequence helpers expand
existing event columns into an ordered event tape, find consecutive event-tape
patterns, encode recent event sequences over trailing/current row windows, add
recent sequence/count features, and summarize encoded sequence frequencies. A
sequence feature at row `t` uses only events observed at or before row `t`.

Milestone 27 adds research-only sequence outcome study helpers. These helpers
summarize encoded event sequences against existing forward outcomes, compare a
sequence against its component event columns, filter by support, and sort
sequence rows for research review. They do not test significance, create
signals, optimize sequence definitions, simulate P/L, or claim edge.

Milestone 28 adds research-only time-of-day helpers. Session buckets classify
bar-close timestamps into open, post-open, mid-morning, lunch, afternoon, power
hour, or outside-regular buckets. Research helpers summarize event outcomes by
bucket, compare bucket outcome distributions against overall baselines, and
flag possible time-of-day concentration for review. These are descriptive
research tools only and do not create signals or claim tradability.

Milestone 29 adds research-only volatility and range context helpers. Realized
volatility context is calculated from trailing close-to-close returns through
the current row, while range expansion context compares the current bar range
against a prior-range baseline shifted by one row. Event summaries by
volatility/range context reuse the conditional event-study machinery and
remain evaluation-only.

Milestone 30 adds a research-only candidate edge registry. Candidate records
capture event or sequence hypotheses, direction, horizon, context, sample
size, baseline comparison, expectancy, hit rate, caveats, data range, and
reproducibility metadata. Registry helpers validate, sort for review, and
persist candidate records as deterministic JSON. A candidate record is not a
strategy rule, signal, recommendation, or live-trading approval.

Milestone 31 adds statistical testing foundations for research validation.
Helpers include bootstrap mean-difference intervals, bootstrap hit-rate
difference intervals, permutation tests, confidence interval calculation, and
compact statistical-test summaries with small-sample warnings. These tools
surface uncertainty; they do not by themselves prove tradability or approve a
candidate edge.

Milestone 32 adds multiple-hypothesis risk helpers. These helpers count tested
hypotheses, apply Bonferroni and Benjamini-Hochberg false-discovery-rate
adjustments, and summarize how many apparent discoveries survive adjustment.
They are guardrails against data mining, not evidence of tradability.

Milestone 33 adds chronological time-series split helpers. Fixed-window and
walk-forward split builders produce train/test row-position records without
shuffle. Split validation enforces non-overlap and chronological order, and
summary helpers report train/test bounds and sizes for audit.

Milestone 34 adds research-only out-of-sample candidate validation helpers.
Candidate edge hypotheses can be evaluated across chronological train/test
splits with in-sample and OOS sample sizes, baseline comparisons, expectancy,
hit rate, stability summaries, and explicit caveats. OOS results are
descriptive validation diagnostics only; they do not prove edge, create
strategy rules, or approve live trading.

Milestone 35 adds research-only parameter sensitivity helpers. Parameter grids
can be built deterministically, evaluated with caller-supplied research
evaluators, summarized by metric variation, and compared with a designated
reference parameter set. These outputs are sensitivity diagnostics only; they
do not optimize settings, select strategy rules, or claim tradability.

Milestone 36 adds research-only robustness report builders. Robustness report
bundles package OOS validation results, OOS stability summaries, parameter
sensitivity summaries, reference comparisons, metadata, and caveat tables into
deterministic CSV or JSON artifacts. Reports are review artifacts only; they do
not create signals, optimize settings, or approve candidates for live use.

Milestone 37 adds research-only candidate rule object helpers. Rule objects
preserve validated candidate identity, condition specifications, evaluation
requirements, validation summaries, robustness summaries, required columns,
caveats, and reproducibility metadata as auditable research artifacts. They are
not executable strategy rules, trading signals, recommendations, or deployment
approvals.

Milestones 38-41 extend that artifact lifecycle with research-only catalog
reports, historical replay diagnostics, replay-vs-OOS sample comparisons, and
candidate rule audit bundles. These helpers check reproducibility and package
review tables; they do not create executable rules, generate signals, route
orders, optimize settings, or approve deployment.

Milestones 42-45 add research decision journaling, candidate family
aggregation, regime/context-conditioned replay review, and negative
control/placebo diagnostics. These helpers make research disposition,
clustering, context dependence, and data-mining risk more visible without
creating signals, recommending trades, optimizing deployment settings, or
claiming edge.

Milestones 46-49 expand the research-risk layer with repeated placebo
statistics, temporal stability diagnostics, data quality and coverage impact
review, and deterministic research-risk report bundles. These helpers package
skepticism checks only; they do not validate tradability or approve deployment.

Milestones 50-53 add research package maturity scoring, candidate retirement
and merge lineage, research package manifests, and an end-to-end research
review workflow. These tools organize and export research evidence; maturity
scores and manifests are not trade-readiness or deployment approvals.

Milestones 54-57 add research governance integrity checks, package comparison
reports, evidence traceability, and deterministic governance bundles. These
helpers validate and summarize research-review artifacts only; they do not rank
packages, approve deployment, or claim trade readiness.

Milestones 58-61 add multi-instrument research context. The module includes a
deterministic instrument registry, in-memory multi-symbol dataframe alignment,
causal cross-instrument confirmation/divergence features, and descriptive
event outcome studies conditioned on multi-instrument context. The module does
not download data, create trading signals, simulate P/L, route orders, or
claim edge.

## Current Scope

- Python package scaffold using a `src/` layout.
- Local CSV loading for SPY 1-minute OHLCV bars.
- Strict OHLCV schema validation.
- America/New_York session classification.
- Causal resampling into larger OHLCV candles.
- Causal event primitive detection for crossovers, trailing breaks, candles,
  single-bar patterns, momentum, range expansion, and volume expansion.
- Causal technical indicator calculations for VWAP, EMA, Bollinger Bands, ATR,
  ADX, and rolling/expanding volume features.
- Forward-looking evaluation labels: future close by horizon, forward return,
  forward return in basis points, valid label flags, and forward direction
  labels.
- Optional prevention of label horizons crossing local America/New_York trading
  dates.
- Simple benchmark prediction baselines and minimal directional evaluation
  summaries for comparing baselines against forward labels.
- Causal market-structure primitives for confirmed pivots, last confirmed pivot
  levels, pivot classification, structure breaks, and primitive structure
  state.
- Causal support/resistance primitives for prior-day levels, same-day premarket
  levels, standard level zones, repeated touch counts, nearest zones, and simple
  zone scoring utilities.
- Causal market-regime context features, rule-based directional and volatility
  regime classifications, and descriptive regime diagnostics.
- Causal retest and false-break event features for known zones and recently
  broken trailing levels, plus descriptive trailing event counts.
- Named causal event feature definitions that compose existing primitives into
  reusable research event columns.
- Named event cataloging and event-study evaluation summaries for comparing
  event occurrences against existing forward labels.
- Research-only event-study diagnostics for sample-size flags, label coverage,
  event coverage, and grouped descriptive summaries.
- Research-only event-study reporting and export helpers for deterministic CSV
  and JSON artifact generation.
- Research-only visualization table and optional plotting helpers for reviewing
  existing event-study and diagnostic artifacts.
- Research-only workflow composition helpers for reproducible event-study,
  diagnostic, reporting, and visualization-prep artifacts.
- Research-only artifact manifest and index helpers for reproducible tracking
  of exported workflow and report files.
- Research-only run registry helpers for loading multiple artifact manifests
  and summarizing run, artifact, and metadata-key inventory.
- Research-only registry audit/export helpers for reproducible run-summary,
  artifact-summary, and metadata-consistency review artifacts.
- Research-only audit index helpers for locating exported registry audit
  bundles, loading metadata JSON, and tracking known audit table paths.
- Research-only audit-index report/export and structural comparison helpers for
  audit summary tables, audit table path summaries, and deterministic
  audit-index structure comparisons.
- Research-only reproducibility checklist helpers for expected metadata keys,
  registry/audit-index structure, file existence, deterministic summaries, and
  JSON checklist persistence.
- Research-only reproducibility report/export helpers for packaging checklist
  summaries, checklist status, registry summaries, and audit-index summaries.
- Research-only forward path outcome labels for future high/low windows,
  MFE/MAE, and long/short direction-normalized event-study outcomes.
- Research-only event forward-outcome study helpers with baseline comparison,
  sample-size visibility, hit rate, and expectancy summaries.
- Research-only conditional event study helpers for causal context buckets,
  context-local baselines, support filtering, and research-review sorting.
- Causal event sequence helpers for event tapes, recent sequence encodings,
  pattern matching, and sequence-count summaries.
- Research-only sequence outcome study helpers for forward outcome summaries,
  component-event comparisons, support filtering, and research-review sorting.
- Research-only time-of-day helpers for deterministic intraday session bucket
  assignment, bucket outcome comparisons, and concentration review.
- Research-only volatility/range context helpers using causal rolling
  volatility and prior-range expansion baselines.
- Research-only candidate edge registry helpers for caveated hypothesis
  tracking and reproducible JSON persistence.
- Research-only statistical testing helpers for bootstrap intervals,
  permutation tests, deterministic seeds, and small-sample warnings.
- Multiple-hypothesis risk helpers for tested-hypothesis counts, Bonferroni
  adjustment, FDR adjustment, and data-mining warnings.
- Chronological time-series and walk-forward split helpers for out-of-sample
  research validation.
- Research-only out-of-sample candidate validation helpers for chronological
  train/test candidate review, in-sample versus OOS diagnostics, and stability
  summaries.
- Research-only parameter sensitivity helpers for explicit parameter grids,
  descriptive metric variation summaries, and reference-set comparisons.
- Research-only robustness report builders for packaging OOS and parameter
  sensitivity diagnostics into deterministic CSV/JSON review artifacts.
- Research-only candidate rule object helpers for auditable, caveated
  hypothesis specifications that remain separate from execution or deployment.
- Research-only candidate rule catalog reports, replay diagnostics,
  replay-vs-OOS comparison helpers, and candidate rule audit bundles.
- Research-only decision journals, family aggregation, context-conditioned
  replay review, and negative control/placebo diagnostics.
- Research-only placebo statistics, temporal stability diagnostics,
  data-quality impact review, and research-risk report bundles.
- Research-only maturity scoring, candidate lineage, package manifests, and
  end-to-end research review workflow helpers.
- Research-only governance artifact integrity, package comparison,
  traceability, and governance summary bundles.
- Deterministic research instrument registry helpers for symbols such as SPY,
  QQQ, DIA, and IWM.
- In-memory multi-symbol dataframe alignment helpers with explicit inner/outer
  joins, symbol-prefixed columns, timestamp coverage diagnostics, and opt-in
  forward fill.
- Causal cross-instrument confirmation, divergence, relative-return, VWAP-side,
  and trailing-volume context features for aligned panels.
- Research-only multi-instrument event outcome studies that compare existing
  event/outcome columns by cross-instrument context with sample-size and
  coverage caveats.
- Deterministic sector ETF and macro instrument universe helpers for
  descriptive research metadata without tradability, allocation, broker, or
  execution implications.
- Causal sector and macro regime context features from already-aligned panels,
  including sector breadth/leadership and macro rates, credit, commodity,
  volatility-proxy, currency-proxy, and risk-on/risk-off context.
- Research-only sector-confirmed and macro-conditioned event studies plus
  deterministic sector rotation and macro regime report bundles with
  sample-size, coverage, proxy-interpretation, and descriptive-only caveats.
- Pytest coverage for the market-data foundation.

## Intentionally Not Included

- Options trading.
- Broker integrations.
- Live execution.
- Alerts.
- Profit simulation.
- Trading edge claims.
- Complete trading signals, regimes, confidence scoring, advanced analytics,
  full strategy backtesting, portfolio accounting, execution modeling, or edge
  claims.

## CSV Schema

Input files must contain these columns:

```text
timestamp,symbol,open,high,low,close,volume
```

Column names are normalized to lowercase. Serious data problems are rejected
instead of silently repaired.

## Timestamp Convention

Timestamps are bar-close timestamps. For example:

```text
2024-01-02 09:31:00-05:00
```

represents the 1-minute candle covering `(09:30, 09:31]`.

CSV timestamps may be timezone-aware or timezone-naive. Timezone-naive
timestamps are localized to `America/New_York` by default.

## Session Assumptions

Session classification uses America/New_York time and bar-close timestamps:

- Premarket: 04:01 through 09:30 ET.
- Regular: 09:31 through 16:00 ET.
- Postmarket: 16:01 through 20:00 ET.
- Closed: everything else.

Holidays, half days, early closes, and exchange calendar rules are not handled
in this milestone.

## No-Lookahead Rules

- Rows must be sorted by timestamp.
- Duplicate timestamps are rejected.
- 5-minute candles are labeled by close time.
- A 5-minute candle is unavailable until its close timestamp.
- No completed 5-minute candle data may be used before that candle closes.
- Session classification uses only the current timestamp.
- Indicator values use only current and prior bar data available at the bar
  close timestamp.
- Forward labels are evaluation targets only and must remain isolated from
  causal feature/event generation.
- Baseline evaluators may read forward labels for evaluation only, but do not
  feed label information back into features, indicators, events, or signal
  generation.
- Pivot candidates may use right-side bars internally for confirmation, but
  confirmed pivot features and last confirmed pivot levels are delayed until the
  confirmation row.
- Market-structure breaks use only already-confirmed pivot levels.
- Prior-day support/resistance levels use only completed previous local trading
  dates; same-day highs/lows cannot affect same-day prior-day features.
- Premarket support/resistance levels are cumulative during premarket and use
  the completed same-day premarket range during regular session.
- Support/resistance zones are built only from levels already available at the
  current row, including confirmed pivot levels only after confirmation.
- Market-regime features and classifications use only current and prior
  information; volatility quantile thresholds are shifted before trailing
  rolling calculations, and forward labels are not used.
- Retest events use only current candle OHLCV and already-available current-row
  zone or broken-level context.
- Recent break context is tracked row by row, and expires without inspecting
  future candles.
- False-break events are emitted only on the row where price has returned
  through a recent broken level; they are not backdated to the original break
  row.
- Named event definitions use current-row causal inputs and prior-row crossing
  checks only; false-break named events copy already-emitted causal false-break
  columns without backdating.
- Event cataloging maps already-existing event columns to descriptive
  research-direction hypotheses without using forward labels.
- Event-study evaluation may read forward labels only to summarize
  event-conditioned outcomes, and does not feed labels back into causal
  features, events, regimes, or signal generation.
- Event-study diagnostics may read forward labels only for coverage summaries,
  and do not feed labels back into causal features, events, regimes, or signal
  generation.
- Event-study reporting/export utilities package existing evaluation and
  diagnostic outputs only, and do not feed labels back into causal features,
  events, regimes, or signal generation.
- Event-study visualization helpers prepare deterministic tables and optional
  plots from existing research artifacts only; they do not feed labels back into
  causal features, events, regimes, or signal generation.
- Event-study workflow helpers compose existing research artifacts only; they do
  not feed labels back into causal features, events, regimes, or signal
  generation, and do not create strategy signals, rankings, optimizations, P/L
  simulation, or edge claims.
- Artifact manifest and index helpers track existing exported files and
  metadata only; they do not inspect forward-label outcomes, feed labels back
  into causal feature/event generation, rank events, create signals, optimize
  thresholds, simulate P/L, or claim edge.
- Run registry and manifest-consumption helpers read manifest JSON files only
  and summarize structural inventory only; they do not read event-study
  artifact contents, inspect outcomes, feed labels back into causal
  feature/event generation, rank runs or events, create signals, optimize
  thresholds, simulate P/L, or claim edge.
- Reproducibility checklist helpers validate dictionary structures, metadata
  key presence, and path existence only; they do not read audit CSV contents,
  artifact contents, manifest contents, outcome values, or forward-label
  values, and do not rank audits/runs/events, create signals, optimize
  thresholds, simulate P/L, or claim edge.
- Out-of-sample validation helpers consume existing candidate hypotheses,
  existing forward outcome columns, and validated chronological split records.
  Training rows always precede test rows, test outcomes are summarized only as
  evaluation diagnostics, and OOS positives are explicitly not treated as edge
  proof or trading approval.
- Parameter sensitivity helpers evaluate explicit parameter combinations with
  caller-provided research evaluators only. They summarize metric variation
  without selecting optimal settings, ranking candidates for deployment, or
  creating strategy rules.
- Robustness report builders package existing diagnostics and caveats only.
  They do not create new event definitions, inspect live data, optimize
  parameters, create strategy rules, simulate P/L, or approve deployment.
- Candidate rule object helpers package candidate identity, condition specs,
  evaluation specs, validation summaries, robustness summaries, required
  columns, caveats, and metadata only. They do not evaluate live data, create
  executable strategy instructions, generate signals, route orders, or approve
  deployment.
- Candidate rule report, replay, OOS comparison, and audit helpers consume
  stored research artifacts and historical DataFrames only. Replay reconstructs
  condition masks for reproducibility checks; it does not emit predictions,
  actions, execution instructions, or deployment decisions.
- Decision journals, family aggregation, context review, and negative controls
  summarize research artifacts or historical condition masks only. They do not
  use forward outcomes as causal inputs, emit predictions/actions, optimize
  parameters, or approve candidates for use.
- Placebo statistics, temporal stability, data-quality impact, and risk report
  helpers summarize existing diagnostics and historical evaluation outputs
  only. They do not create causal features, trading signals, strategy
  instructions, or deployment approvals.
- Maturity, lineage, manifest, and review workflow helpers package existing
  research artifacts only. They do not transform candidates into strategy
  instructions, generate signals, execute orders, or approve real-money use.
- Artifact integrity, package comparison, evidence traceability, and governance
  bundle helpers validate research review structure only. They compare
  coverage, metadata, caveats, and missing evidence without selecting a best
  package, scoring trade readiness, creating recommendations, approving
  deployment, or authorizing trading.
- Multi-instrument registry, alignment, confirmation features, and event
  studies are research-context infrastructure only. They consume caller-supplied
  data, use current/prior rows for features, and treat forward outcomes as
  evaluation targets only.
- Sector ETF universe, sector context features, sector-confirmed event studies,
  and sector rotation reports are descriptive research infrastructure only.
  Sector leadership, breadth, dispersion, and confirmation outputs do not imply
  allocation guidance, portfolio construction, tradability, broker support,
  execution support, or buy/sell recommendations.
- Macro instrument universe, macro regime features, macro-conditioned event
  studies, and macro regime reports are descriptive research infrastructure
  only. Rates, credit, commodity, volatility-proxy, currency-proxy, and
  risk-on/risk-off outputs do not imply allocation guidance, portfolio
  construction, tradability, broker support, execution support, instrument
  rankings, or buy/sell recommendations.
- No strategy signals, confidence scoring, advanced analytics, or trading
  backtests are implemented yet.
- Event primitives use current and prior bar data only.
- Prior trailing highs/lows and moving averages are shifted so the current bar
  cannot influence its own threshold.
- No forward returns, labels, or future candles are used by causal market-data,
  indicator, or event modules.

## Installation

```bash
cd spy_directional_edge_research
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Running Tests

```bash
pytest
```

## Example Usage

```python
from spy_edge_research.market_data import (
    add_session_column,
    filter_regular_session,
    load_ohlcv_csv,
    resample_ohlcv,
)

df = load_ohlcv_csv("data/raw/SPY_1min.csv")
regular = filter_regular_session(df)
five_minute = resample_ohlcv(regular, rule="5min")
with_sessions = add_session_column(df)
```

## Command-line pipeline runner (MOD 11)

The `spy-edge` console script (installed with `pip install -e .`) runs the whole
research pipeline end-to-end from one OHLCV CSV, writing a timestamped run
directory of artifacts (report bundle, candidate registry, dashboard JSON
contract + manifest, and a paper-trading readiness scorecard) plus a
`run_manifest.json`:

```bash
# data -> indicators -> events -> labels -> event study -> candidates
# -> risk overlap -> walk-forward OOS stability -> dashboard -> readiness gate
spy-edge run-pipeline --input data/raw/SPY_1min.csv --output reports --horizons 5,15,30

spy-edge list-runs --root reports                 # discover prior runs
spy-edge score-readiness --run reports/run_<id>   # print the readiness verdict
spy-edge export-dashboard --bundle reports/run_<id>/report_bundle --output out.json
```

It is **research-only**: it reimplements no stage logic, produces descriptive
artifacts only, and the readiness verdict is a research gate — never a trade
authorization. The basic pipeline does not run the negative-control /
multiple-testing / temporal-stability batteries, so verdicts stay `not_ready`
until those are run (disclosed via the manifest's
`control_batteries_not_run_in_basic_pipeline` caveat).

## Research Modules (MOD 06–10) — Usage

All of the following are **research-only**: descriptive diagnostics, advisory
flags, read-only access, data contracts, and a readiness *gate*. None size
positions, allocate capital, place orders, or authorize trades.

### Portfolio / risk exposure (MOD 06)

```python
import pandas as pd
from spy_edge_research.risk import (
    ExposureLimits,
    add_exposure_columns,
    compute_event_mask_overlap,
    compute_group_concentration,
    evaluate_exposure_limits,
    summarize_concentration,
    summarize_exposure,
    summarize_signal_overlap,
)

candidates = pd.DataFrame(
    {"instrument": ["SPY", "SPY", "QQQ"], "direction": ["long", "short", "long"]}
)
exposure = summarize_exposure(candidates)
concentration = summarize_concentration(
    compute_group_concentration(add_exposure_columns(candidates), group_column="instrument")
)
overlap = summarize_signal_overlap(
    compute_event_mask_overlap(
        pd.DataFrame({"sig_a": [1, 0, 1], "sig_b": [1, 0, 1]}), ["sig_a", "sig_b"]
    )
)
limit_checks = evaluate_exposure_limits(
    limits=ExposureLimits(max_gross_exposure=2.0, max_group_share=0.7, max_pairwise_jaccard=0.8),
    exposure_summary=exposure,
    concentration_summary=concentration,
    overlap_summary=overlap,
)  # advisory flags only, e.g. risk_overlap_too_high
```

### Factor context (MOD 07)

```python
from spy_edge_research.instruments import build_factor_universe, list_factor_etfs
from spy_edge_research.signal_engine import add_factor_context_features

universe = build_factor_universe()
symbols = list_factor_etfs(universe)  # ['HDV', 'MTUM', 'QUAL', 'SIZE', 'USMV', 'VLUE']
factor_features = add_factor_context_features(
    panel_df,  # timestamp-aligned multi-symbol close panel incl. SPY + factor ETFs
    primary_symbol="SPY",
    factor_symbols=symbols,
    factor_styles={"MTUM": "momentum", "VLUE": "value", "USMV": "low_volatility"},
)
```

### Read-only research service layer (MOD 08)

```python
from spy_edge_research.services import (
    export_workflow_service_response,
    list_bundle_tables,
    load_report_bundle_csv_dir,
    run_event_research_workflow_service,
)

response = run_event_research_workflow_service(
    df, label_columns=["forward_return_5m"], catalog=catalog, min_events=10
)
export_workflow_service_response(response, "reports/run_001")
bundle = load_report_bundle_csv_dir("reports/run_001")
tables = list_bundle_tables(bundle)
```

### Dashboard data export (MOD 09)

```python
from spy_edge_research.dashboard import (
    build_dashboard_payload_from_bundle,
    export_dashboard_payload_to_json,
)

payload = build_dashboard_payload_from_bundle(bundle, payload_type="event_study")
export_dashboard_payload_to_json(payload, "reports/run_001/dashboard.json")
```

### Paper-trading readiness gate (MOD 10)

```python
from spy_edge_research.paper import (
    build_readiness_metrics,
    score_candidate_readiness,
    summarize_readiness_verdict,
)

# Assemble the gate's inputs from upstream research summaries (OOS stability,
# MOD 06 signal overlap, control-pass flags).
metrics = build_readiness_metrics(
    oos_stability_row=oos_stability_summary.iloc[0],
    signal_overlap_summary=overlap,
    negative_control_passed=True,
    multiple_testing_passed=True,
    temporal_stable_period_count=3,
)
scorecard = score_candidate_readiness(metrics)
verdict = summarize_readiness_verdict(scorecard)
# verdict -> "eligible_for_paper_consideration" or "not_ready" (+ reasons).
# Eligible means the evidence bar is met, NOT that anything is cleared to trade.
```
