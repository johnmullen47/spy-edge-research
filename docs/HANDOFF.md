# Session Handoff — SPY Directional Edge Research

> For the next agent (Codex or another Claude Code session) picking up this
> project. Written 2026-06-13. **Re-verify the live state before trusting any
> specific number here** — this repo has had concurrent writers (see §1).

## 0. Verified snapshot at handoff

- **Branch:** `main`
- **HEAD:** `bdb493c` — `MOD 11 (M97): unified CLI / pipeline runner`
- **Working tree:** clean
- **Full suite:** `766 passed, 4 skipped` (`.venv/bin/python -m pytest -q` from project root; Python 3.11; the 4 skips need matplotlib)
- **Latest ledger milestone:** M97 (`PROJECT_MILESTONES.md`)
- **ruff** is installed in `.venv` (used for F401 import cleanup).

## 1. ⚠️ This is a multi-writer repo — read first

This project has been advanced by **more than one session at once**. While this
session did M94–M96, a parallel Claude Code session built and committed
**MOD 11 (M97)**. Consequences for whoever picks up:

- **Always re-check before assuming state:** `git log --oneline | head`,
  `git branch --show-current`, `git status --porcelain`, and re-run the suite.
- **Renumber milestones against the live max**, not your local memory — MOD 11
  took M97 because M96 was already used by the other session.
- **Never `git add -A`.** Stage explicit paths only. A blanket add here has
  swept in (a) another session's staged files and (b) a stray scratch probe.
  Scratch files (`scratch_*.py`, `*_probe.py`) are now gitignored.
- There is **no git remote**; `main` is the only source of truth. Keep it green.

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
  (disclosed via `control_batteries_not_run_in_basic_pipeline`).

## 3. Approved roadmap ahead (user-authorized 2026-06-13)

Sequence toward a usable app:

1. **MOD 11 runner** — done (M97).
2. **MOD 14 — paper-trading SIMULATION layer.** The user **explicitly authorized
   crossing the research-only boundary** for this. Build in a NEW `simulation/`
   module with **its own forbidden-field validator** — it must NOT round-trip
   through `candidate_rule_objects` / `dashboard.contracts`, which reject
   `pnl`/`entry`/`exit`/`order`. Entries must be **causal**; exits reuse
   `labels.py` horizon math. Simulated positions/fills/P&L only.
3. **MOD 12 — frontend** (static SPA over the MOD 09 dashboard JSON contracts).
4. **MOD 13 — value/quality/momentum research.**

**Still forbidden until a further explicit OK:** real broker/money, live
execution, order routing, options expression.

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
