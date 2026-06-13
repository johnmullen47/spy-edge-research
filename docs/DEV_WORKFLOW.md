# Developer Workflow

> Operational notes for working on this repository. For architecture see
> [`ARCHITECTURE.md`](ARCHITECTURE.md); for vision/governance/progress see the
> root `MASTER_PROJECT_BRIEF.md`, `CODEX_MASTER_DESK.md`, and
> `PROJECT_MILESTONES.md`.

## Environment

- **Python:** 3.11 (the committed baseline was verified on 3.11.15).
- **Canonical virtualenv:** `.venv/` at the project root (git-ignored).
- **Key deps:** `pandas`, `pytest` (matplotlib optional — 4 visualization tests
  skip gracefully when it is absent).

Install (editable, with dev extras):

```bash
python3 -m pip install -e ".[dev]"
```

## Running tests

Always run from the project root (pytest config lives in `pyproject.toml`):

```bash
.venv/bin/python -m pytest -q
```

**Green baseline:** `674 passed, 4 skipped` at **Milestone 69** — the state
captured by the initial git commit. The 4 skips require matplotlib.

> Note: running `pytest` from another working directory collects no tests —
> `testpaths` is resolved relative to the project root.

## Version control

- The **initial commit** captures the Milestone 69 green baseline.
- `main` should always point at a **last-known-green** state: the suite passes
  before anything lands on it.
- Generated artifacts (`data/`, `reports/`) and environments (`.venv/`,
  `*.egg-info/`, caches) are git-ignored; the archived
  `legacy_auto_trader_spy_scaffold/` keeps its *source* but not its venv/cache.

### Branch discipline (for concurrent work)

This project may be edited by more than one agent. To avoid clobbering:

- Do feature/milestone work on a **branch**, not directly on `main`.
- **Commit before and after** a working session so any concurrent edits remain a
  reviewable diff rather than a silent overwrite.
- Run the full suite before merging to `main`; keep `main` green.
- **Never force-push** shared history.

## Working conventions

Per the governing briefs, when extending the package:

- Keep all features/events **causal** — no future rows in current-row signals;
  forward-looking columns use the `outcome_` / `forward_` prefix and are
  **labels only**, never inputs.
- Every new public function gets a focused test; every new module gets a test
  file. Prefer deterministic synthetic fixtures; no network or paid-data calls
  in tests.
- Respect the research-only hard boundaries (no execution, broker, options,
  alerts, or trade-readiness claims) until a later milestone explicitly
  authorizes otherwise.
- Advance **one approved module/milestone at a time**; Milestone 70+ scope is
  decided with the user, not assumed.
