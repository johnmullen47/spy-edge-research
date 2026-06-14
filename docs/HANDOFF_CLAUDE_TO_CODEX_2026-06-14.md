# Handoff: Claude → Codex (2026-06-14)

Briefing for **Codex**, resuming the **SPY Directional Edge Research** project
(`~/Documents/Codex/Auto-Trader SPY`, package `src/spy_edge_research/`). You were
parked after **Milestone 100**. A Claude Code session on the afternoon of
2026-06-14 advanced the project substantially **and put it on a private git
remote**. Get up to speed before doing anything.

## FIRST — the project now lives on GitHub (private)

- Remote: `https://github.com/johnmullen47/spy-edge-research` (PRIVATE). `main`
  tracks `origin/main`.
- If you already have the local folder: `git pull --ff-only origin main`.
- Starting fresh, or to (re)bootstrap venv/credentials/data: **clone it and read
  [`CLONE_SETUP.md`](CLONE_SETUP.md)** — Python 3.11 venv (`pip install -e ".[dev]"`),
  recreating `secrets/alpaca.env` (gitignored, not in the repo), fetching SPY data,
  running the pipeline. Also read [`HANDOFF.md`](HANDOFF.md) and `PROJECT_MILESTONES.md`.
- If you can't access the private repo, ask John to add your GitHub account as a
  collaborator.

## What happened (M101–M107) — the "Trader module" build-out

John authorized crossing toward live execution, but explicitly as a **staged
roadmap with hard gates**, not a jump to live. Locked decisions: **a human
approves every order**; broker **Alpaca, equities/ETF only** (sandbox-first);
options deferred. All merged to `main`:

- **M101** — control batteries (negative-control / multiple-testing /
  temporal-stability) wired into `run_pipeline` so a candidate can finally reach
  `eligible_for_paper_consideration` (`cli/control_batteries.py`, Stage 9.5,
  default-on toggle).
- **M102** — `decision_support/` (Phase 12): descriptive, human-in-the-loop review
  records from eligible candidates. Authorizes nothing.
- **M103** — `broker/` sandbox (Phase 13): Alpaca **paper endpoint only**,
  human-approved `OrderIntent` → dry-run + JSONL audit, `TradingLimits` +
  `KillSwitch`. No real money; a live endpoint is structurally unreachable here.
- **M104** — `broker/live_adapter.py` (Phase 14): the only real-order path, **inert
  by construction** behind 3 gates — env flag `SPY_EDGE_ALLOW_LIVE=1`, a per-order
  `human_approval_token` matching the intent id, and limits/kill-switch. No
  batch/autonomous path exists.
- **M105** — economic-significance gate (`ReadinessCriteria.min_edge_bps`, default
  1.0 bp cost floor) on the OOS edge.
- **M106** — replaced the coarse multiple-testing heuristic with real
  **per-candidate permutation p-values + Benjamini-Hochberg FDR**.
- **M107** — `ExecutionModel.slippage_bps` separated from `cost_bps`.

`decision_support/` and `broker/` are intentionally kept OUT of the top-level
package re-export (like `simulation`).

## The key empirical result — Hard Gate A ran on REAL data

SPY 1-min bars were fetched from Alpaca (`scripts/fetch_spy_bars.py`) and run
through `scripts/run_hard_gate_a.py`. Across **both** IEX (189,663 bars,
2024-06..2026-06) and full-volume **SIP** (195,487 bars, 2023..2024): **0 of 42
candidates reached `eligible`** — most failing on all three independent grounds
(negative control + FDR + economic significance). **There is no validated intraday
edge in the current candidate set. The broker layers stay OFF.** This is the
designed, desirable outcome — not a bug. The first (pre-M105) run had flagged 15
"eligible," but their edges were 0.06–0.46 bps (sub-cost noise) — exactly what
M105–M107 were built to catch.

## Current state

`main` @ `249a245` (plus this memo), full suite `844 passed, 4 skipped` (4 skips
need matplotlib). Verify with `.venv/bin/python -m pytest -q` from the project root.

## Discipline (multi-writer — Claude and you both write)

- `git pull --ff-only origin main` before starting; `git push origin main` after
  merging.
- Branch per milestone; renumber against the live `git log` max (M-numbers are
  taken through M107).
- Run the full suite before merging; keep `main` green; ff-merge only.
- **Never `git add -A`** — stage explicit paths. `secrets/` and `data/` are
  gitignored; never commit credentials or market data.
- Reuse `_internal/_common` helpers; per-module forbidden-field guards stay local.
- Research-only boundaries hold: nothing places a real order without John's
  explicit per-deployment authorization (env flag + per-order approval), and only
  after an edge actually clears Hard Gate A — which it currently does not.

## Open threads (nothing required; for discussion with John)

The no-edge result is robust, so the productive direction isn't more plumbing —
it's whether a richer hypothesis space (combined / regime-conditioned signals,
longer horizons, other instruments) is worth exploring, or whether to accept the
efficient-market null for intraday SPY technicals. Also possible: a dynamic
(volatility/volume-scaled) slippage model. Do not assume the next move is toward
execution.
