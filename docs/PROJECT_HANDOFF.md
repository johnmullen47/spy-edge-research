# PROJECT HANDOFF — Auto-Trader SPY Edge Research

> **Single authoritative onboarding document.** A brand-new agent or human
> collaborator with zero prior context can read this file plus the existing
> code and be fully oriented to continue the project.
>
> **Last updated:** 2026-06-16 · **Maintainer role:** "Build Master" (Claude Code).
> **Repo:** `https://github.com/johnmullen47/spy-edge-research` (PRIVATE).
> **Canonical workspace:** `/Users/johnmullen/Documents/Codex/Auto-Trader SPY`.
>
> ⚠️ **Re-verify live state before trusting any number here.** This repo has had
> concurrent writers (Codex + Claude Code + Cowork). Always run `git fetch`,
> `git log --oneline -10 origin/main`, `git branch -a`, and the test suite before
> relying on specifics. See §3 (Architecture / collaboration model) and the
> "Documentation-vs-code gap" warning in §2.

---

## 1. Mission

This is a **rigorous, research-only quantitative project searching for a
statistically validated intraday directional trading edge in US equity
instruments** — primarily SPY. The defining property is **causal, auditable,
no-lookahead research designed to *kill* weak hypotheses before they could ever
reach live trading.** A "no edge found / evidence insufficient" output is a
first-class, *desirable* result, not a failure. The system measures whether an
edge exists under a hostile anti-overfitting harness (Deflated Sharpe, Probability
of Backtest Overfitting, permutation/FDR multiple-testing, negative/placebo
controls, walk-forward OOS, regime-aware costs); only if a candidate survives all
of it does anything downstream (paper simulation, then — far later, and only with
explicit per-deployment human authorization — live execution) become reachable.

As of this handoff the search has spanned **all five durable mechanism buckets**
(risk premia, behavioral under/over-reaction, microstructure/rebalancing,
structural forced-flow, macro/calendar) and the answer is consistently **NO
validated edge**. The broker/live layers remain structurally OFF. That is the
designed outcome.

---

## 2. Current state (as of 2026-06-16)

| Item | Status |
|---|---|
| **Hard Gate A** | **NEGATIVE.** 0 of 672 candidates eligible in M126 (full F1–F10 set). No validated edge. |
| **`origin/main` HEAD** | `3a72087` — "docs: update HANDOFF and PROJECT_MILESTONES to M126" (i.e. main contains through **M126**). |
| **M127 (MIM confirmatory replication)** | **`NULL_NON_REPLICATION`** — well-powered, preregistered, control-clean non-replication of canonical Market Intraday Momentum in SPY 2016–2026. On branch `milestone/M127` (and `origin/milestone/M127`); **not yet merged to main**. |
| **M128 (cross-sectional HKS-2010)** | **In progress / scaffold only.** Interfaces + TODOs; all stubs raise `NotImplementedError`. On branch `milestone/M128`. **No experiments run.** Blocked on stock-universe intraday data. |
| **Active branch / worktree** | M127→M128 work was done by Build Master in a private worktree on `milestone/M128` (HEAD `b71b000`, the M127 result commit). The shared main checkout sits on Codex's `codex/mim-iteration` (M117). |
| **Broker / live execution** | **OFF and structurally inert.** Three independent gates (env flag + per-order human token + limits/kill-switch) all required; none satisfiable. |
| **Test suite (last verified)** | ~`1042 passed, 4 skipped` at M125 (4 skips need matplotlib); re-verify per milestone with `.venv/bin/python -m pytest -q`. |

### ⚠️ Documentation-vs-code gap (read this)

The **mainline progress ledger lags the actual work.** Two of the repo's "ledger"
documents — root `PROJECT_MILESTONES.md` and `docs/HANDOFF.md` — were last fully
reconciled around M117, while the real experimental work has advanced to
**M126/M127** (on `main`/milestone branches) and M128 (scaffold). Concretely:

- The committed `main` history goes **through M126**. `milestone/M127` and
  `milestone/M128` carry M127's result and M128's scaffold on top of it.
- The durable result records for the latest milestones live in **dedicated docs on
  the milestone branches**, not in the root ledger:
  `docs/RESULTS_M126_HARD_GATE_A.md`, `docs/m127/` (results JSON + reports),
  `docs/m128/M128_SCAFFOLD.md`, `docs/preregistration/M127_PREREG.yaml`.
- Earlier research memos (`docs/RESEARCH_J_Adversarial_Null_Challenge.md`) were
  written against an **M117 working copy** and reason about M126 numbers John
  supplied verbatim; they explicitly flag that the M126 run artifacts were not
  readable in that copy. Treat those memos as analysis, and the
  `RESULTS_M126_HARD_GATE_A.md` file as the artifact of record.

**Action for a new agent:** to see M127/M128, `git fetch origin` then inspect
`origin/milestone/M127` and `milestone/M128` (e.g.
`git show milestone/M128:docs/RESULTS_M126_HARD_GATE_A.md`). Do not assume the root
`PROJECT_MILESTONES.md` reflects current state — it is behind.

---

## 3. Architecture

### 3.1 What the system is

A **research-first validation engine** for SPY intraday directional edges,
implemented as the Python package `src/spy_edge_research/` (import name
`spy_edge_research`; installed editable as `spy_directional_edge_research`). It is
explicitly **not** a trading bot, broker automation, options selector, or
live-execution system. Full as-built map: [`docs/ARCHITECTURE.md`](ARCHITECTURE.md).

### 3.2 Package layout (`src/spy_edge_research/`)

```
market_data/          ingestion, OHLCV schema validation, NY session classification,
                      causal resampling, multi-symbol alignment, vix_loader
indicators/           causal technical features (ATR, ADX, EMA, Bollinger, VWAP, volume)
market_structure/     pivots, structure breaks, retests, false breaks
support_resistance/   prior-day & premarket levels, zones, zone scoring
signal_engine/        causal events, named-event catalog, sequences, cross-instrument/
                      sector/macro/factor features, and the SIGNAL FAMILIES:
                        intraday_momentum_features (MIM, Path 2), mim_baltussen_features,
                        end_of_day_reversal_features (F2), f3_vix_gated / f4_overnight_gap /
                        f5_fomc_calendar, vrp_features (F6), vol_managed_features (F7),
                        orb_features (F8), intraday_periodicity_features (F9),
                        fomc_cycle_features (F10), value_quality_momentum_features (VQM),
                        cross_sectional_scaffold (M128 stubs)
market_regime/        volatility & directional regime classification + diagnostics
instruments/          instrument / sector / macro / factor universe registries
backtesting/          THE MEASUREMENT & GOVERNANCE CORE — forward labels, event studies,
                      edge measurement, baselines, negative_controls, placebo_statistics,
                      multiple_testing (Bonferroni/FDR), statistical_tests (bootstrap/perm),
                      oos_validation, time_splits (walk-forward), parameter_sensitivity,
                      temporal_stability, deflated_sharpe (DSR + PBO), effective_n (ONC),
                      mim_regression, candidate registry/lineage, reproducibility/governance
risk/                 MOD 06 — exposure / overlap / concentration + advisory limit flags
services/             MOD 08 — read-only research API over committed artifacts
dashboard/            MOD 09 — versioned frontend-ready JSON data contracts
paper/                MOD 10 — paper-trading READINESS GATE (criteria → verdict); NOT trading
cli/                  MOD 11 — `spy-edge` console script; run_pipeline orchestration;
                      control_batteries
simulation/           MOD 14 — paper-trading SIMULATION on historical bars only (post-gate,
                      authorized boundary crossing); own data model + forbidden-field guard
decision_support/     Phase 12 — human-in-the-loop review records (post-gate; descriptive)
broker/               Phases 13–14 — Alpaca sandbox + INERT live adapter (kept OUT of the
                      top-level re-export; see §6 security)
```

**The causal boundary** is the central invariant: features/events may use only the
current and prior rows; forward-outcome columns (prefixed `outcome_`/`forward_`/
`future_`) are *labels only* and never feed back into event detection. Trailing
quantile thresholds use `.shift(1)` so a bar can never set its own threshold.

### 3.3 Data-flow pipeline

```
raw OHLCV CSV → load/validate/session/resample/align
  → causal feature frame (indicators + structure + S/R + regime)
  → causal events (signal_engine; the signal families fire here)
  → forward outcome labels (backtesting.labels — LABELS ONLY)
  → edge measurement (event_study / forward_outcomes / conditional)
  → validation & robustness (baselines, neg/placebo controls, multiple_testing,
     oos_validation/walk-forward, temporal_stability, effective_n, deflated_sharpe/PBO)
  → candidate registry → readiness gate (paper/) → verdict
```

### 3.4 How the AI agents collaborate

Three cooperating "wings", one human operator (**John**):

- **Codex** — works in the **main checkout** at the canonical workspace path,
  typically on branch `codex/mim-iteration`. **Build Master never edits the main
  checkout directly.**
- **Claude Code "Build Master"** — owns **all git commits** (single-committer
  rule). Implements milestones inside **private git worktrees** (see §4.3), reviews
  research drops, commits with explicit paths, and is responsible for keeping
  `HANDOFF.md` current per milestone.
- **Cowork / Dispatch research wing** — produces research memos and
  pre-registrations as **files** (dropped into the main checkout `docs/` or the
  untracked `Auto-Trader Build/` research-drop folder). Cowork **does not commit**;
  Build Master reviews and commits each drop.

**Single-committer rule:** Build Master is the only committer. Cowork/Research
writes files; Build Master reviews and commits. One committer → clean,
auditable history.

**Research-doc immutability:** decision and pre-registration docs land in
`docs/RESEARCH_*.md` / `docs/PREREG_*` / `docs/preregistration/*.yaml`, are reviewed
and committed by Build Master, and are then **immutable** — revisions ship as
amendment files (e.g. `RESEARCH_E_AMENDMENT_1.md`), never by editing the original.

---

## 4. How to run

### 4.1 Environment setup

```bash
cd "/Users/johnmullen/Documents/Codex/Auto-Trader SPY"
python -m venv .venv               # Python 3.11
source .venv/bin/activate
pip install -e ".[dev]"            # installs the package editable + dev deps
pytest                             # full suite (run from project root; ~1042 passed, 4 skipped)
```

`ruff` is installed in `.venv` (used for F401 import cleanup). The 4 skipped tests
need matplotlib. Fresh-clone bootstrap (venv + credentials + data fetch) is in
[`docs/CLONE_SETUP.md`](CLONE_SETUP.md).

### 4.2 Key scripts (`scripts/`)

| Script | Purpose |
|---|---|
| `scripts/fetch_spy_bars.py` | Fetch real SPY 1-min OHLCV from Alpaca. `--feed iex` (recent, ~1–2% of true volume) or `--feed sip` (full consolidated volume; **older** history only on the free plan — recent ~15 months blocked). Writes gitignored CSV under `data/raw/`. |
| `scripts/fetch_vix.py` | Pull CBOE **free daily** VIX/VIX9D/VIX3M CSVs → `data/raw/vix_daily.csv` (Polygon free tier is **not** entitled to `I:VIX`). |
| `scripts/run_hard_gate_a.py` | The Hard Gate A driver. Runs the full pipeline on a real multi-month SPY CSV with the signal families enabled (MIM, F2, MIM-Baltussen, F3/F4/F5, F6–F10) and reports the eligibility verdict. |
| `scripts/run_m127.py` | M127 preregistered MIM replication harness (confirmatory regressions + negative controls), driven by `docs/preregistration/M127_PREREG.yaml`. |
| `spy-edge` (console script) | `run-pipeline`, `export-dashboard`, `score-readiness`, `list-runs`. The basic pipeline does NOT run the control batteries, so its verdicts stay `not_ready` (disclosed via the `control_batteries_not_run_in_basic_pipeline` manifest caveat). |

Run artifacts land in `reports/run_<UTC>/` (gitignored — durable records are
captured in committed `docs/RESULTS_*.md` files instead).

### 4.3 Worktree protocol (MANDATORY — exact commands)

Effective 2026-06-15: at the start of **every** implementation task, Build Master
creates a private git worktree and works entirely inside it. **Never work in the
main checkout** (Codex lives there). This exists because two sessions sharing one
working tree caused a real collision — Codex checked out its branch mid-session and
Build Master's commits silently landed on the wrong branch while `git push origin
main` was a no-op "success".

```bash
# from the main checkout:
git worktree add ../auto-trader-build-$(date +%Y%m%d-%H%M) milestone/M<n>
#   (add -b milestone/M<n> origin/main to create the branch off main if new)
cd ../auto-trader-build-<timestamp>
git fetch origin && git merge --ff-only origin/main   # pull any research-doc drops
# ...implement, commit with EXPLICIT paths, push from the worktree...
git worktree remove ../auto-trader-build-<timestamp> --force   # on completion
```

**Gotcha — driver PYTHONPATH.** The package is installed editable into `.venv`,
which lives only in the main checkout and resolves to the **main checkout's**
`src/` (usually on Codex's lagging branch). Running a standalone driver like
`scripts/run_hard_gate_a.py` from a worktree imports the *stale main-checkout
code* → `TypeError: unexpected keyword argument` on new `PipelineConfig` fields.
(pytest is unaffected — it prepends the worktree `src/`.) **Fix:** set
`PYTHONPATH="$WT/src"` when running a driver from a worktree, using the main
checkout's venv python:
`PYTHONPATH="$WT/src" "/Users/johnmullen/Documents/Codex/Auto-Trader SPY/.venv/bin/python" scripts/run_hard_gate_a.py ...`

### 4.4 How to add a new milestone

1. Create a private worktree off `origin/main` on a `milestone/M<n>` branch (§4.3).
2. If a new signal family: implement causal features in `signal_engine/`, add a
   pre-registration first if it's a frozen hypothesis (§5), wire it through the
   SAME Hard Gate A pipeline (a new *family*, never a new or softened *gate*).
3. Add deterministic synthetic-fixture tests; keep the suite green.
4. Run Hard Gate A on real data; record the result in a committed
   `docs/RESULTS_M<n>_*.md` (run dirs are gitignored).
5. Update `docs/HANDOFF.md` (mandatory at every milestone) and
   `PROJECT_MILESTONES.md`.
6. Commit with explicit paths and the conventions in §7; ff-merge / PR to `main`;
   push; remove the worktree.

---

## 5. The Hard Gate A system

**Hard Gate A is the central empirical go/no-go decision:** run the full pipeline
on real multi-month SPY 1-minute data and confirm whether *any* candidate reaches
the verdict `eligible_for_paper_consideration`. **If nothing reaches `eligible`,
there is no validated edge and the broker layers stay OFF.** It has never been
turned off, softened, or bypassed, and it must not be — **not until it returns a
positive result on a fair test.**

The readiness gate is a **9-criterion** scorecard (a candidate is `eligible` only
if ALL pass; any missing metric is conservatively `insufficient_evidence` →
`not_ready`):

1. Minimum OOS-positive splits.
2. Minimum OOS sample size.
3. **Negative-control pass** (shifted + random controls must not match the edge).
4. **Multiple-testing pass** — per-candidate permutation p-value + Benjamini-Hochberg
   FDR across the family (M106), replacing the old family-size heuristic.
5. Minimum temporal-stable periods.
6. Maximum pairwise signal overlap (Jaccard).
7. **Economic significance** — OOS mean edge ≥ `min_edge_bps` (default **1.0 bp**, a
   round-trip cost floor). Added in M105 after the first real run produced 15
   "eligible" candidates whose edges were all 0.06–0.46 bp — sub-cost noise.
8. **PBO** — Probability of Backtest Overfitting ≤ `max_pbo` (default **0.50**), via
   CSCV over the OOS panel (M108–M109).
9. **Deflated Sharpe** — DSR ≥ `min_deflated_sharpe` (default **0.50**; the gate
   threshold used operationally is DSR ≥ 0.95), deflating the in-sample Sharpe
   against the expected best-of-N Sharpe (M108–M109).

**Why DSR + PBO + IS-Sharpe matter (the anti-overfitting trio):**

- **IS-Sharpe (in-sample Sharpe ratio)** is the raw backtest performance — by itself
  meaningless under a search, because the *best of many* trials is high by chance.
- **DSR (Deflated Sharpe Ratio, Bailey & López de Prado)** answers "is the observed
  Sharpe better than the *expected maximum* Sharpe you'd get from this many trials
  under the null?" It is THE BINDING CONTROL. Critically, it deflates against the
  **full pre-OOS trial budget** (every cell evaluated), not the surviving subset —
  shrinking N to survivors is the canonical false-discovery move and is forbidden
  (M112). At M119+ the trial count N is the **effective number of independent
  trials** from ONC clustering of candidate return streams (`backtesting/effective_n.py`),
  bounded `[family_count, total]`, so correlated within-family variants don't each
  cost a full trial.
- **PBO (Probability of Backtest Overfitting)** answers "how often does the
  in-sample-best configuration underperform out-of-sample?" via combinatorially
  symmetric cross-validation. PBO ≥ 0.5 means the selection procedure is no better
  than chance.

Together they make it structurally hard for a broadly-discovered chart pattern to
survive: the M126 run failed candidates on up to three independent grounds at once
(economic significance, FDR multiple-testing, and the two overfitting gates).

**A documented tension (RESEARCH_J / RESEARCH_E):** breadth is paid for in
deflation. At effective-N = 318 the False-Strategy-Theorem noise ceiling is
≈ 2.9 × σ_SR, which can put the minimum IS Sharpe needed to clear DSR around ~2.0+
annualized — a bar a *modest* honest single-instrument edge (Sharpe ~0.5–1.0)
cannot reach. The correct response is **not** to loosen the gate but to run a
**narrower, higher-prior search** (fewer families → lower N → reachable bar). The
gate is doing its job; the search design over-paid for breadth.

---

## 6. Preregistration protocol

**Why it exists:** to make data-snooping structurally impossible. The hypothesis,
the full candidate grid, the controls, and the honest expected probability of
success are **frozen in writing before any predictor→target relationship is
computed on real data.** Git history is the audit trail — the prereg commit
provably precedes the result commit.

**Structure of a pre-registration** (see `docs/PREREG_MIM_BALTUSSEN.md`,
`docs/PREREG_F3.md`…`F10.md`, and the YAML form `docs/preregistration/M127_PREREG.yaml`):

- **Hypothesis + mechanism + citations**, and the *family* it belongs to (per
  RESEARCH_H), which determines its effective-N contribution.
- **The frozen configuration grid** — every threshold/window/regime cell, with the
  total candidate count booked into the trial budget. No cell may be added after the
  freeze; no tuning after the freeze.
- **Anti-snooping controls**, with the binding one named (DSR with effective-N).
- **Negative / placebo controls** that must make the apparent edge vanish.
- **A binding, regime-aware cost model.**
- **Acceptance criteria** (all must hold for `eligible`) and **falsification
  criteria** (what routes the family to null — and the rule "on failure, do NOT
  re-slice into finer cells; drop the family").
- **An honest, often-low pre-registered probability of clearing the gate.**

The YAML form (M127) adds machine-checkable fields:
`results_observed_before_freeze: false`, frozen UTC timestamp, co-primary
hypotheses, the exact predictor/target formulas, the universe with explicit
exclusions and reasons, and the negative-control pass rule. Any change requires a
new versioned file (`M127_PREREG_v2.yaml`) with an explicit statement of whether
results were already observed.

**The v2 rules / RESEARCH_H "N-count correction":** the Deflated Sharpe must deflate
against the *effective* number of independent trials, computed by ONC clustering of
candidate return streams (not the raw candidate count and not the survivor count).
New, genuinely decorrelated families each add ~1 effective trial and *raise* the
DSR bar for everything — breadth is honestly paid for in a higher Type-I hurdle
rather than by loosening gates (the Type-I/Type-II trade of RESEARCH_E). This
superseded the earlier "N = every cell ever evaluated" clause **for the cross-trial
DSR input only**; all thresholds (DSR ≥ 0.95, PBO ≤ 0.50, cost floor) are unchanged.

---

## 7. Security constraints (verbatim, immutable)

These are non-negotiable. Do not weaken, route around, or "temporarily" disable any
of them.

- **Paper API keys only in `secrets/alpaca.env` — NEVER committed.**
- **Hard Gate A must remain NEGATIVE before any live trading.**
- **Broker/live layers stay OFF.**
- **`SPY_EDGE_ALLOW_LIVE=1` flag required for any live execution path.**
- **Human-approval-token required per order.**
- **`secrets/polygon.env` gitignored, NEVER committed.**
- **R/W (`04_`) never reads Life Strategy (`06_`) — membrane is one-directional.**
- **Theory layer: no living persons or named ministries (archetypal roles and
  historical cases only).**
- **Do-not-modify gate on promoted core-corpus documents.**
- **INTERNAL tier classification = mask-off, not for public distribution.**

**How these are enforced in code:**
- `secrets/` and `data/` are gitignored (see `.gitignore`) and are **not** on the
  remote — credentials and market data stay local-only. The repo is PRIVATE.
- The live order path (`broker/live_adapter.py`, `AlpacaLiveAdapter`) is **inert by
  construction**: it raises `BrokerLiveDisabledError` unless `SPY_EDGE_ALLOW_LIVE=1`
  is in the process env, requires a per-order `human_approval_token` matching the
  intent id (no batch / autonomous path), and enforces `TradingLimits` + a
  `KillSwitch`. The sandbox adapter is hard-pinned to Alpaca's **paper** endpoint
  and refuses any non-sandbox mode. `broker/` and `decision_support/` are kept OUT
  of the top-level package re-export.

---

## 8. Commit conventions

- **Branching:** research hypotheses on `research/<signal-name>`; milestone
  implementation on `milestone/M<n>` (off `origin/main`); Codex on
  `codex/<topic>`. Merge to `main` at completion (ff-merge or PR). **Stage explicit
  paths only — never `git add -A`** (a blanket add here has historically swept in
  another session's staged files and stray scratch probes).
- **Commit message formats:**
  - Milestones: `M<number>: <summary>`
  - HANDOFF updates: `docs: update HANDOFF to M<number>`
  - Research docs: `RESEARCH_<letter>: <summary>`
  - Cowork file drops: `research: add <filename> from Cowork Master Agent`
- **Single committer:** Build Master owns all commits.
- **Where things go:** durable milestone *results* → committed `docs/RESULTS_M<n>_*.md`
  (run dirs under `reports/` are gitignored); frozen specs → `docs/PREREG_*` /
  `docs/preregistration/*.yaml`; permanent research records → `docs/RESEARCH_*.md`
  (immutable post-commit). Scratch files (`scratch_*.py`, `*_probe.py`) are
  gitignored — never commit them.

---

## 9. What has been tested, and the results

### 9.1 M1–M99 — the research infrastructure (core stack + MOD 06–14)

Built the entire causal measurement platform: data → indicators → market
structure/levels → causal events → forward labels → regime → edge measurement →
validation/robustness/governance → multi-instrument → sector → macro (M1–M69);
then MOD 06–10 (risk exposure, factor-ETF research, read-only service layer,
dashboard contracts, the readiness gate) (M70–M92); hardening + the
`_internal/_common` DRY foundation (M93–M96); the `spy-edge` CLI runner (M97); the
paper-trading **simulation** layer on historical bars (M98); the static frontend
viewer (M99). All research-only.

### 9.2 M100–M104 — VQM research + the staged (inert) trader scaffold

- **M100** — cross-sectional value/quality/momentum factor research (OHLCV-only).
- **M101** — control batteries wired into the pipeline so a candidate *can* reach
  `eligible`.
- **M102–M104** — `decision_support/` (human-in-the-loop review records), `broker/`
  Alpaca **paper** sandbox, and the **inert** live adapter behind three gates. Code
  complete, live path structurally impossible to reach (see §7).

### 9.3 The Hard Gate A sweep — M105 onward (the empirical core)

**First real-data run (2026-06-14):** 189,663 real SPY 1-min bars (Alpaca IEX,
2024-06…2026-06), 42 candidates → 15 initially "eligible", but every edge was
0.06–0.46 bp (sub-cost). This exposed a missing economic-significance criterion and
triggered the hardening below:

- **M105** — economic-significance floor (`min_edge_bps`, default 1.0 bp) → **0 of
  42 eligible.**
- **M106** — per-candidate permutation p-value + BH-FDR multiple-testing.
- **M107** — slippage separated from cost in the execution model.
- **M108–M109** — Deflated Sharpe + PBO added and wired into the gate (7 → 9
  criteria). Pure-numpy implementation (no SciPy).
- **M112** — DSR deflates against the **full** pre-OOS trial budget, not OOS
  survivors (RESEARCH_C §4.3 binding control).
- **M114** — regime-aware cost model
  (`cost = half_spread(t) + k·σ_intraday(t) + impact_sqrt(Q/ADV)`, time-of-day &
  VIX-regime aware, charged at point-of-fill). Built but not yet wired into the
  economic gate (open follow-up).

**Five mechanism buckets and the families tested (RESEARCH_I taxonomy):**

1. **Behavioral continuation/reversal** — MIM (intraday momentum, Path 2; M110–M111),
   MIM-Baltussen rest-of-day (M121), F2 EOD reversal (M116/M118), F3 VIX gate /
   F4 overnight gap / F5 pre-FOMC placebo (M122).
2. **Risk premia** — F6 variance risk premium (M125).
3. **Microstructure/rebalancing** — F9 intraday periodicity (M125).
4. **Structural/forced-flow** — opening-range breakout F8 (M125); the gamma-hedging
   F1 path (data-blocked, see §11).
5. **Macro/calendar** — F10 FOMC cycle (M125).

Plus risk-management overlays: F7 vol-managed (M125, a likely-fail adjudication).

Key intermediate runs (all `0 eligible`, broker layers OFF):
- **M115 / M117** — MIM (+ parameter iteration): 54 → 66 candidates, PBO 0.1065.
- **M118** — F2 enabled: 100 candidates, PBO 0.3303.
- **M119** — effective-N via ONC clustering (RESEARCH_H): effective-N fell from 100
  to its principled floor (2) and **still 0/100** — the null is robust to the
  N-count correction.
- **M121** — MIM-Baltussen (32 strategy cells): 280 candidates, effective-N 143,
  PBO 0.0971.
- **M122** — VIX pipeline + F3/F4/F5: 600 candidates, effective-N 600 (ceiling at the
  time), PBO 0.1016. **F5 placebo confirmed null** (post-2015 pre-FOMC decay), so no
  candidate leaned on the FOMC gate.
- **M124** — fixed an ONC degenerate-effective-N bug (a single sparse candidate +
  `dropna(how="any")` collapsed the panel, forcing `n_eff = total`). Fix keeps NaN
  gaps + pairwise-complete correlation; N=600 now runs in ~18 s and clusters
  properly.

### 9.4 M126 — Hard Gate A on the full F1–F10 set (the headline null)

Source of record: `docs/RESULTS_M126_HARD_GATE_A.md` (run `reports/run_20260616T040858Z`,
gitignored; IEX SPY 1-min, 189,663 bars + CBOE daily VIX).

**0 of 672 candidates reached `eligible_for_paper_consideration`. No validated
edge.** A valid, honestly-recorded null across every pre-registered family in all
five mechanism buckets.

| Metric | Value |
|---|---|
| Event columns | 214 (154 from M122 + 60 from F6–F10) |
| Candidate registry | 672 |
| **Effective-N (clusters)** | **318** (M124 fix validated on real data — non-degenerate) |
| Within-cluster Holm survivors | **38** (none cleared the full gate) |
| Portfolio PBO | **0.0959** (≤ 0.50) |
| Eligible | **0 / 672** |

Per-family (all `not_ready`): MIM-Baltussen 256, chart/named 84, F4 72, F3 72,
MIM 48, F5 48, F9 20, F2 20, F8 18, F10 12, F6 12, F7 10 — **0 eligible each.**
Even the stronger-prior F10 (FOMC cycle) and F6 (VRP) were null; the ~2-year IEX
sample is power-limited for the daily/weekly families. Thresholds unchanged
(DSR ≥ 0.95, PBO ≤ 0.50, cost floor). SPA/Hansen remains deferred (report-only).

### 9.5 M127 — MIM confirmatory replication → `NULL_NON_REPLICATION`

Source of record: `docs/m127/m127_results.md` + `m127_results.json`; design frozen
in `docs/preregistration/M127_PREREG.yaml` (committed **before** the result). Data:
**Alpaca SIP** (full consolidated volume), SPY 2016-01-04…2026-06-12, N_full = 2,625
daily obs, N_highvol = 875; HAC t critical = 2.498 (k=4 Bonferroni).

Canonical Market Intraday Momentum does **not** replicate in SPY 2016–2026 at its
published magnitude. Co-primary tests (Gao H_a: prior close→10:00; Baltussen H_b:
prior close→15:30; target 15:30→16:00):

| Test | n | β | HAC t | corr | Pass? |
|---|---|---|---|---|---|
| H_b full (PRIMARY) | 2,625 | +0.0178 | +1.23 | +0.063 | fail |
| H_a full (PRIMARY) | 2,625 | +0.0182 | +0.73 | +0.045 | fail |
| H_b high-vol | 875 | +0.0210 | +0.98 | +0.070 | fail |
| H_a high-vol | 875 | +0.0251 | +0.73 | +0.059 | fail |

All βs are the correct (momentum) sign but far below significance; correlations
+0.045–0.070 are ~half the canonical 0.13; high-vol conditioning did not rescue the
effect. **Negative controls all insignificant** (max |t| = 1.94 < 2.498) → harness
not contaminated, null trustworthy. This is a **well-powered** (power > 0.999 at
canonical corr 0.13; MDE ~0.07 full), **preregistered, control-clean**
non-replication. Most likely explanations: publication decay (McLean–Pontiff ~58%;
our window is post-publication) and instrument (H_b is documented on **futures**;
this is the SPY ETF — a null here is *not* a rejection of the futures finding).
A documented post-result driver fix corrected a loose `suspicious` heuristic to the
frozen prereg criterion; the binding confirmatory verdict (0/4) was unchanged.

### 9.6 M128 — cross-sectional HKS-2010 (IN PROGRESS, scaffold only)

Source of record: `docs/m128/M128_SCAFFOLD.md`; code
`signal_engine/cross_sectional_scaffold.py` (all stubs raise `NotImplementedError`).

**Rationale:** the periodicity/continuation effect (Heston-Korajczyk-Sadka 2010,
RESEARCH_I bucket 3) is **cross-sectional** — defined *across many stocks*, not
within one diversified ETF. M127's SPY-ETF null is the *expected control outcome*
for a cross-sectional effect, not a test of it. M128 would test it where it lives:
the stock cross-section.

**Planned design (to be frozen at M128 via the same Gate-0.5 discipline as M127):**
stocks-first universe with point-in-time membership (no survivorship bias);
same-clock-time (e.g. 30-min bucket) per-stock return continuation; **mandatory
controls** — market/beta neutralization, a point-in-time liquidity screen, and
ETFs (SPY/QQQ/…) as **negative controls** (a true cross-sectional effect should be
weak/absent on a diversified ETF, anchored by the M127 SPY null). Same harness:
preregistration freeze → power/MDE → fidelity ≥ Close → negative controls →
auditable artifacts. Intended methods include **Fama-MacBeth** cross-sectional
regressions on **Alpaca SIP** stock minute bars.

**Blockers (must resolve before any M128 experiment):** (1) stock-universe intraday
data with survivorship-correct point-in-time membership + liquidity history — not in
the repo (Alpaca can fetch individual stock minute bars, IEX-thin or SIP, but
membership/liquidity must be sourced); (2) a cross-sectional power analysis
(N = stocks × days). **Until then: scaffold only. No M128 experiments.**

### 9.7 RESEARCH_I & RESEARCH_J (the framing memos)

- **`RESEARCH_I_Retail_Quant_Method_Sweep.md`** — the 5-bucket taxonomy of durable
  return patterns and the basis for the F6–F10 pre-registrations. Bottom line: the
  retail-quant space is a fragmented application of a small number of durable
  patterns; the gap between *claimed* and *evidenced* is enormous (most technical
  rules don't survive data-snooping + costs; <1% of day traders are predictably
  profitable; ~58% post-publication decay). The project was concentrated in one
  bucket and under-exploring the other four; F6–F10 deliberately spread across them,
  each runnable on existing data, each pre-registered with an honest (often low)
  expected success probability.
- **`RESEARCH_J_Adversarial_Null_Challenge.md`** — a commissioned devil's-advocate
  challenge to the 0/672 null ("if there's nothing here, why do retail quants claim
  profit?"). Verdict: **the null partially stands.** It validly rejects "a
  high-Sharpe, broadly-discoverable directional edge on SPY," but does **not** earn
  "there is nothing here," because (H1) the intraday-native families may have been
  tested outside their native 1-min resolution, and (H3) effective-N = 318 set the
  DSR bar near ~2+ Sharpe, blind to a *modest* real edge. The claimed retail profits
  are explained without rescuing any edge by **selection/survivorship bias (H2)** +
  **decay (H5)**. Recommended response: run *different, narrower* tests (re-test the
  four intraday families at 1-min; pull the 38 survivors' family/Sharpe breakdown;
  probe 1–2 high-prior families at low N) — **not** lower the gate. (Note: this memo
  was written against an M117 working copy and could not read the M126 artifacts; it
  reasons from the summary numbers John supplied.)

---

## 10. Open decisions (require John's input)

1. **Merge `milestone/M127` to `main`?** The M127 NULL_NON_REPLICATION result is
   clean and auditable (preregistered, control-clean, git-provable freeze). Whether
   to merge it (and the M128 scaffold) into `main` is John's call. `main` currently
   sits at M126.
2. **ES/MES futures for H_b?** The decisive remaining test for the Baltussen
   canonical instrument is a futures run — H_b is documented on futures, and the SPY
   ETF null is not a rejection of the futures finding. Requires **new paid data**
   (Databento / IQFeed); no source is configured.
3. **The 38 Holm within-cluster survivors from M126 — profile them?** They passed
   within-cluster multiple-testing but failed the full breadth-inflated gate.
   RESEARCH_J flags pulling their family + IS-Sharpe distribution (and the DSR's
   σ_SR and T) as the single highest-information follow-up — it adjudicates H3/H4
   together. Currently deferred.

---

## 11. Next steps (priority order)

1. **M128 (in progress)** — cross-sectional HKS-2010 continuation/reversal on
   individual stocks via Alpaca SIP, with Fama-MacBeth and ETFs as negative
   controls. Resolve the data/power blockers (§9.6), pass Gate 0.5, then freeze and
   run. **No experiments until the blockers clear.**
2. **ES/MES futures for H_b** — the only remaining decisive test for the Baltussen
   canonical instrument. **Blocked on data** (paid: Databento/IQFeed).
3. **F1 gamma-gated MIM** — highest-prior structural candidate, **data-blocked** on
   historical option open-interest / options-chain data (Polygon confirmed no
   historical OI; the documented fix is DeltaNeutral ALLSPX ~$805). Per RESEARCH_J,
   scope it as a **volatility-regime** input, not a directional savior — recent
   evidence says dealer gamma (GEX) predicts next-day *volatility*, not *direction*.
4. **38 Holm survivors** — profiling deferred (§10.3).

Other non-authorization-needed follow-up: wire the M114 regime-aware cost model into
the economic-significance gate; finish the `_internal/_common` DRY migration for the
non-`backtesting` subpackages.

---

## 12. Data sources available (no new spend)

| Source | Coverage | Notes |
|---|---|---|
| **Alpaca SIP** | Stocks + ETFs, full consolidated volume, back to ~2016 | **Already paid.** Free plan blocks the most recent ~15 months of SIP; older history is fine. Primary source for M127 and planned M128. |
| **Alpaca IEX** | Recent intraday | Free, but only ~1–2% of true volume (thin single-venue); used for many Hard Gate A runs. |
| **Polygon.io free tier** | ~2 years intraday | **Not** entitled to `I:VIX`; no historical option OI. |
| **yfinance** | Daily | Unreliable intraday; daily only. |
| **CBOE free CSVs** | Daily VIX / VIX9D / VIX3M | `scripts/fetch_vix.py` → `data/raw/vix_daily.csv`. The working VIX source. |
| **FRED** | Macro / rates | Macro regime context. |
| Free Fed calendar | FOMC dates | Embedded 2024–2026 calendar for F5/F10. |

**Data NOT available without new spend:** ES/MES/NQ futures (Databento/IQFeed),
historical SPX option open-interest (DeltaNeutral ALLSPX ~$805), VIX *futures*
term-structure.

---

## 13. Key literature references

- **Gao, Han, Li & Zhou (2018), JFE** — "Market Intraday Momentum" (the H_a
  formulation; first-30-min → last-30-min).
- **Baltussen, Da, Lammers & Martens (2021), JFE** — "Hedging Demand and Market
  Intraday Momentum" (the H_b rest-of-day predictor + gamma-hedging mechanism;
  documented on futures).
- **Heston, Korajczyk & Sadka (2010), JF** — "Intraday Patterns in the Cross-section
  of Stock Returns" (the cross-sectional periodicity effect; basis for M128).
- **McLean & Pontiff (2016), JF** — "Does Academic Research Destroy Stock Return
  Predictability?" (~58% post-publication decay).
- **Harvey, Liu & Zhu (2016)** and **Bailey & López de Prado** — the DSR / Deflated
  Sharpe / PBO / False Strategy Theorem methodology that underpins the gate.
- Supporting: Barber, Lee, Liu & Odean (Taiwan day-trader base rates); Bollerslev,
  Tauchen & Zhou 2009 (VRP); Cieslak, Morse & Vissing-Jorgensen 2019 (FOMC cycle);
  Moreira & Muir 2017 vs. Cederburg et al. 2020 (vol-managed); Sullivan-Timmermann-White
  1999 & Bajgrowicz-Scaillet 2012 (technical rules vs. data-snooping); Zarattini &
  Aziz 2023 (ORB). Full citations live in `docs/RESEARCH_I_*.md`, `RESEARCH_J_*.md`,
  and the `PREREG_*` files.

---

## 14. Repo / contact

- **GitHub (PRIVATE):** `https://github.com/johnmullen47/spy-edge-research`
- **Canonical workspace:** `/Users/johnmullen/Documents/Codex/Auto-Trader SPY`
- **Human operator:** John (stepping back; this document enables cold-start
  handoff).
- **`origin`** = the GitHub remote above; `main` tracks `origin/main`. `secrets/`
  and `data/` are gitignored and NOT on the remote — keep credentials and market
  data local-only. **Pull before starting work, push after merging** so concurrent
  writers stay in sync.

---

### Document provenance / honesty notes

- This handoff was assembled on 2026-06-16 from: `README.md`, `docs/ARCHITECTURE.md`,
  `docs/HANDOFF.md` (main and `milestone/M128` versions), `PROJECT_MILESTONES.md`
  (through M117), and the milestone-branch result records
  (`docs/RESULTS_M126_HARD_GATE_A.md`, `docs/m127/*`, `docs/m128/M128_SCAFFOLD.md`,
  `docs/preregistration/M127_PREREG.yaml`), plus `RESEARCH_I`/`RESEARCH_J` and the
  `PREREG_*` specs.
- **Known uncertainty, stated rather than guessed:** the root `PROJECT_MILESTONES.md`
  ledger and root `docs/HANDOFF.md` lag the milestone branches (§2). M127/M128 are on
  `milestone/M127`/`milestone/M128` and **not yet merged to `main`** (M126). The 38
  Holm survivors' per-family Sharpe breakdown and the DSR σ_SR/T are referenced but
  were not re-derived here. Numbers from gitignored run dirs are quoted from the
  committed `RESULTS_*`/`m127` records, which are the artifacts of record. **Re-verify
  against live state before acting.**
