# Session Handoff — SPY Directional Edge Research

> For the next agent (Codex or another Claude Code session) picking up this
> project. Last updated 2026-06-13 (after M100). **Re-verify the live state before
> trusting any specific number here** — this repo has had concurrent writers (see §1).

## 0. Verified snapshot at handoff

- **Branch:** `main`
- **HEAD:** `e30d675` — `M107: slippage in the execution model`
- **Working tree:** clean
- **Full suite:** `844 passed, 4 skipped` (`.venv/bin/python -m pytest -q` from project root; Python 3.11; the 4 skips need matplotlib)
- **Latest ledger milestone:** M107 (`PROJECT_MILESTONES.md`)
- **ruff** is installed in `.venv` (used for F401 import cleanup).

### Hard Gate A — RAN, definitive negative result (no validated edge)

Real SPY 1-min data was fetched via `scripts/fetch_spy_bars.py` (Alpaca; creds in
gitignored `secrets/alpaca.env`) and run through `scripts/run_hard_gate_a.py`.
Across **both** the IEX feed (2024-06..2026-06, 189,663 bars) and the full-volume
**SIP** feed (2023..2024, 195,487 bars), **0 of 42 candidates reached
`eligible`.** After the M105–M107 hardening, candidates fail on up to three
independent grounds at once (negative control, FDR multiple-testing, economic
significance). **There is no validated intraday edge in this candidate set — the
broker layers stay OFF.** That is the designed, desirable outcome. Robustness
milestones added after the first run:
- **M105** — economic-significance gate (`ReadinessCriteria.min_edge_bps`, default
  1.0 bp cost floor) on the OOS mean edge. The first run's "eligible" 15 were all
  0.06–0.46 bps — sub-cost noise.
- **M106** — per-candidate permutation p-value + Benjamini-Hochberg FDR replaces
  the family-size heuristic for multiple-testing.
- **M107** — `ExecutionModel.slippage_bps` separated from `cost_bps`.

Note on data: Alpaca free `--feed sip` works for **older** history but blocks the
most recent ~15 months ("subscription does not permit querying recent SIP data");
IEX carried only ~1–2% of real volume. Data CSVs are gitignored.

## 1. ⚠️ This is a multi-writer repo — read first

This project has been advanced by **more than one session at once**. One session
did M94–M96 (hardening + the `_internal/_common` DRY migration); a parallel
Claude Code session built **MOD 11 (M97)** and then the whole functional-app
build-out **MOD 14 (M98), MOD 12 (M99), MOD 13 (M100)** plus a MOD 11 round-trip
fix. Consequences for whoever picks up:

- **Always re-check before assuming state:** `git log --oneline | head`,
  `git branch --show-current`, `git status --porcelain`, and re-run the suite.
- **Renumber milestones against the live max**, not your local memory — MOD 11
  took M97 because M96 was already used by the other session.
- **Never `git add -A`.** Stage explicit paths only. A blanket add here has
  swept in (a) another session's staged files and (b) a stray scratch probe.
  Scratch files (`scratch_*.py`, `*_probe.py`) are now gitignored.
- **Git remote (2026-06-14):** `origin` = **`https://github.com/johnmullen47/spy-edge-research`**
  (PRIVATE). `main` tracks `origin/main`. **`pull` before starting work and `push`
  after merging** so the multiple writers stay in sync. `secrets/` and `data/` are
  gitignored and are NOT on the remote — keep credentials/market data local-only.

## 2. Where the project is

A **research-only**, causal, auditable SPY edge-validation platform (NOT a live
trader / broker / options selector). Package: `src/spy_edge_research/`.
Architecture map: [`ARCHITECTURE.md`](ARCHITECTURE.md). Governance/constraints:
`../MASTER_PROJECT_BRIEF.md`, `../CODEX_MASTER_DESK.md`. Progress ledger:
`../PROJECT_MILESTONES.md`.

Completed and on `main`:

- **Core stack** (M1–69): data → indicators → structure/levels → causal events →
  forward labels → regime → edge measurement → validation/robustness/governance →
  multi-instrument → sector → macro.
- **MOD 06–10** (M70–92): `risk/` (exposure/overlap/concentration + advisory
  limit flags), factor-ETF research, `services/` (read-only research API),
  `dashboard/` (versioned JSON contracts), `paper/` (readiness **gate** — NOT
  paper trading).
- **M93**: `paper/readiness_inputs.build_readiness_metrics` bridges MOD 06
  overlap / OOS-stability summaries into the readiness gate.
- **M94**: review-driven hardening + the `_internal/_common.py` DRY foundation;
  top-level `__init__` re-exports all subpackages; `tests/conftest.py` added.
- **M95/M96**: migrated all `backtesting/*_reports.py` (batch 1) and the 41
  non-report `backtesting/*.py` (batch 2) onto `_internal/_common` (−881 LOC).
- **M97 (other session)**: `cli/` package + `spy-edge` console script;
  `run_pipeline` threads one OHLCV frame through the whole backend into
  `reports/run_<UTC>/`. Note: it does not run the negative-control /
  multiple-testing / temporal batteries, so readiness stays `not_ready`
  (disclosed via `control_batteries_not_run_in_basic_pipeline`). A follow-up fix
  (`d829fba`) makes its candidate registry round-trippable (was writing
  `hit_rate=NaN` → JSON `null` → unreadable; now a caveated `0.0`).
- **M98 — MOD 14 paper-trading SIMULATION layer** (the authorized boundary
  crossing): new `simulation/` package. Simulates positions/fills/P&L on
  *historical* bars only; own data model + forbidden-field validator
  (`validate_sim_report`, `sim_caveat`); causal entries, `labels.py` exits. Reads
  the **featured** frame (with `event_*` columns) + a candidate list — not raw bars.
- **M99 — MOD 12 frontend**: `frontend/index.html` — a zero-build,
  dependency-free, offline static viewer for the MOD 09 dashboard JSON contracts
  (no Node toolchain here; a single static file, not React/Vite). `tests/frontend/`
  pins the contract shape in CI.
- **M100 — MOD 13 value/quality/momentum research**:
  `signal_engine/value_quality_momentum_features.py` (causal cross-sectional
  price-factor scores + ranks) + `backtesting/vqm_event_study.py` (bucketed
  factor→forward-outcome study). OHLCV-only; distinct from MOD 07 (factor ETFs).

## 3. Roadmap status (user-authorized 2026-06-13)

The functional-app build-out is **COMPLETE** — all merged to `main`:

1. **MOD 11 runner** — done (M97).
2. **MOD 14 paper-trading SIMULATION layer** — done (M98). The authorized
   research-only boundary crossing.
3. **MOD 12 frontend** — done (M99).
4. **MOD 13 value/quality/momentum research** — done (M100).

**Staged "Trader module" build-out (user-authorized 2026-06-13) — CODE COMPLETE
(M101–M104), live path INERT.** The user explicitly authorized crossing toward
live execution, but as a **staged plan with hard gates**, not a jump to live.
Locked decisions: **a human approves every order**; broker **Alpaca, equities/ETF
only** (sandbox-first); **options deferred** (Phase 15). Plan file:
`~/.claude/plans/binary-crunching-cascade.md`. Stages, all merged to `main`:

- **M101 — control batteries → readiness.** `cli/control_batteries.py` + Stage 9.5
  in `run_pipeline` (toggle `PipelineConfig.run_control_batteries`, default on).
  Negative-control / multiple-testing(family-size heuristic) / temporal-stability
  now feed the gate, so a candidate **can** reach `eligible`. Drops the
  `control_batteries_not_run_in_basic_pipeline` caveat when batteries run.
- **M102 — `decision_support/` (Phase 12).** Human-in-the-loop review records from
  eligible candidates + risk flags; descriptive only, `requires_human_review`.
- **M103 — `broker/` sandbox (Phase 13).** Alpaca **paper endpoint only**;
  human-approved `OrderIntent` → dry-run order + JSONL audit; `TradingLimits` +
  `KillSwitch`; `alpaca-py` optional. Reaching a live endpoint is structurally
  impossible from here.
- **M104 — `broker/live_adapter.py` (Phase 14).** The only real-order path, behind
  three gates: env flag `SPY_EDGE_ALLOW_LIVE=1` (else `BrokerLiveDisabledError`),
  per-order `human_approval_token` matching the intent id (no batch/autonomous
  path), and limits + kill-switch. No dry-run/live mode; needs a configured client.
  **Inert by construction.**

`decision_support/` and `broker/` are post-gate packages kept OUT of the top-level
re-export (like `simulation`).

**What remains is operational, NOT code — and is the real gate:**
1. **Hard Gate A** — run the pipeline on a real multi-month SPY 1-minute CSV and
   confirm ≥1 candidate reaches `eligible_for_paper_consideration`. No real SPY data
   is in the repo (`data/raw` empty by design). **If nothing reaches `eligible`,
   there is no validated edge — do not enable the broker layers.**
2. After a clean Alpaca **paper-sandbox** run on that real edge, an explicit
   per-deployment decision to set `SPY_EDGE_ALLOW_LIVE=1` and start at minimal size.

Still forbidden without that explicit per-deployment OK: enabling live execution,
and options expression (Phase 15) / production hardening (Phase 16).

Other follow-ups needing no new authorization: finishing the `_internal/_common`
DRY migration for the non-`backtesting` subpackages (see §4).

## 4. Staged maintenance follow-up (safe, mechanical)

The DRY migration to `_internal/_common` is done for `backtesting/`; the rest of
the package still defines local copies. Post-M96 counts (re-verify):
`_require_columns` ~30 modules, `_validate_positive_int` ~17, plus a few
`_normalize_columns`/`_json_safe_value`/etc. — now mostly in `signal_engine/`,
`market_*`, `instruments/`, `support_resistance/`, and the non-report files of
`risk/services/dashboard/paper`.

**Recipe that worked (do it per-subpackage, suite-verified):**

1. AST script: for each module, remove module-level `def`s whose name is in the
   `_common` set **only if the signature matches** (guard against variants —
   e.g. `event_reports._require_columns` is a 3-arg `KeyError` variant and must
   stay local). Insert `from spy_edge_research._internal._common import (... as _x)`.
2. `.venv/bin/python -m ruff check --select F401 --fix <paths>` to drop now-unused imports.
3. `py_compile` + full suite. **The suite catches *body* variants the signature
   guard can't** — e.g. several modules' `_json_safe_value` serialized
   `pathlib.Path`; the fix was to make `_common.json_safe_value` a superset
   (`Path -> str`), which it now is. If you find another superset behavior,
   widen `_common` rather than keeping a local copy.
4. Commit with **explicit paths**; ff-merge to `main`.

Optional bigger item: a spec-driven `report_bundle` base
(`{caveat, table_files, forbidden_fields}`) to collapse the duplicated
metadata/validate/summarize/export plumbing across the report modules.

## 5. Conventions / gotchas

- **Causal invariant:** features/events use only current+prior rows; forward
  columns (`outcome_`/`forward_`/`future_`) are labels only; trailing-quantile
  thresholds use `.shift(1)` so a bar never sets its own threshold.
- **Per-module forbidden-field guards stay local** (each report type has its own
  set). Only the *generic* helpers live in `_internal/_common`.
- **Suite count grows as modules are added** — `tests/backtesting/test_event_study.py`
  parametrizes over source files. Don't be alarmed by the number changing.
- Branch → tests → ff-merge → keep `main` green. Run tests from the project root
  (pytest config resolves `testpaths` there).
- Statistical notes already documented in code: permutation p-value uses the
  conservative `>=`; tiny-sample bootstrap CIs are unreliable; finite-resample
  p-values can floor at 0; `directional_profit_factor_equivalent` is a research
  proxy (no costs/slippage).

## 6. If you are the other (MOD 11/14) session

This session's lane was hardening + DRY + the MOD 06–10 research modules. To
avoid collisions: coordinate which subpackage each session edits, commit often
with explicit paths, and treat `main` as shared. When in doubt, ask the user
who else is writing.
