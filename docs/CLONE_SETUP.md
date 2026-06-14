# Fresh-clone setup

How to bootstrap this project on a new machine / for a second writer (Codex or
another Claude Code session). Read `MASTER_PROJECT_BRIEF.md` and
[`HANDOFF.md`](HANDOFF.md) first for scope and the research-only boundaries.

Two things are **gitignored and therefore NOT in the clone** — you recreate them
locally: the Python venv (`.venv/`), credentials (`secrets/`), and market data
(`data/`). The code reads credentials from the environment or `secrets/alpaca.env`.

## 1. Clone

```bash
git clone https://github.com/johnmullen47/spy-edge-research.git
cd spy-edge-research
```

## 2. Python environment (requires Python 3.11+)

```bash
python3.11 -m venv .venv
.venv/bin/python -m pip install -U pip
.venv/bin/python -m pip install -e ".[dev]"     # package + pytest
# optional extras used by the project but not required deps:
.venv/bin/python -m pip install ruff matplotlib  # ruff = F401 cleanup; matplotlib = the 4 skipped viz tests
```

This installs the `spy_edge_research` package (editable) and the `spy-edge`
console script.

## 3. Verify the install

```bash
.venv/bin/python -m pytest -q          # expect: 844 passed, 4 skipped (4 skips need matplotlib)
```

Run tests from the project root — pytest resolves `testpaths`/`pythonpath` there.

## 4. Credentials (only needed to fetch data — never committed)

Create `secrets/alpaca.env` (the directory is gitignored). Get paper-trading keys
from the Alpaca dashboard (app.alpaca.markets → Paper Trading → API Keys → Generate):

```
APCA_API_KEY_ID=PK...your_key_id...
APCA_API_SECRET_KEY=...your_full_secret...
```

Alternatively export `APCA_API_KEY_ID` / `APCA_API_SECRET_KEY` in your shell; the
fetcher checks the environment first, then the file. **Never commit either.**

## 5. Fetch SPY 1-minute data (network; outside the package)

```bash
# Free IEX feed, ~2 years, regular hours -> data/raw/spy_1min.csv (gitignored):
.venv/bin/python scripts/fetch_spy_bars.py

# Full-volume SIP feed (if your Alpaca plan allows; note it blocks the most
# recent ~15 months, so end in the past):
.venv/bin/python scripts/fetch_spy_bars.py --feed sip --start 2023-01-01 --end 2024-12-31 \
    --output data/raw/spy_1min_sip.csv
```

The CSV schema the pipeline requires is `timestamp,symbol,open,high,low,close,volume`
(see `market_data/validators.py`); the fetcher emits it directly. IEX understates
volume (single venue); prefer SIP for any result you intend to trust.

## 6. Run the pipeline / Hard Gate A

```bash
# Reproducible driver with OOS sizes tuned for ~2yr of 1-min bars:
.venv/bin/python scripts/run_hard_gate_a.py --input data/raw/spy_1min.csv

# or the CLI directly (tiny default OOS sizes — fine for small inputs only):
.venv/bin/spy-edge run-pipeline --input data/raw/spy_1min.csv --output reports
```

Read the verdict at `reports/run_<UTC>/readiness/verdict.csv`. As of M107, the
candidate set produces **no** `eligible` candidate on real data — the broker
layers stay off. That is the designed result, not a bug.

## 7. Git workflow (multi-writer)

`origin` = this private repo; `main` tracks `origin/main`.

```bash
git pull --ff-only origin main          # before starting work
git checkout -b mNNN-short-description   # branch per milestone (renumber vs live `git log` max)
# ... edit, then ...
.venv/bin/python -m pytest -q           # full suite green before merging
git add <explicit paths>                # NEVER `git add -A`
git commit -m "..."                     # apostrophes break bash heredoc; use `git commit -F <file>` if needed
git checkout main && git merge --ff-only mNNN-... && git push origin main
```

Keep `main` green. Stage explicit paths only. Reuse `_internal/_common` helpers;
don't write local copies. Per-module forbidden-field guards stay local.
