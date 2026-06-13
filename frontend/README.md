# SPY Edge Research — Dashboard frontend (MOD 12)

A **zero-build, dependency-free, offline** viewer for the MOD 09 versioned
dashboard JSON contracts (schema `1.0`) emitted by
`spy_edge_research.dashboard.export` and written by the MOD 11 `spy-edge`
pipeline runner. It is a single static file (`index.html`) — no Node, no npm, no
build step, no runtime server required.

It is a pure consumer of committed JSON files: it never fetches live data and
displays **descriptive research data only — never trade instructions**. The
mandatory `dashboard_caveat` is rendered prominently, an unknown
`schema_version` is flagged, and any field that should not appear in a research
dashboard (e.g. `buy`/`sell`/`pnl`/`order`/`readiness`) is surfaced as a
warning.

> Note: the original roadmap named a Vite/React SPA. This environment has no Node
> toolchain, and a single static file is the most robust, offline-pure fit for
> the contract-as-boundary design. The integration contract is identical; if a
> richer SPA is wanted later it can read the same JSON.

## Usage

Produce a contract with the pipeline, then view it:

```bash
# 1. generate a run (writes reports/run_<id>/dashboard/event_study.json + manifest.json)
spy-edge run-pipeline --input data/raw/SPY_1min.csv --output reports

# 2a. simplest: open frontend/index.html in a browser and use “Open file…”
#     (or drag the event_study.json onto the page). Works fully offline.

# 2b. or serve and auto-load via ?src= (fetch needs a server, not file://):
cd reports/run_<id>/dashboard
python -m http.server 8000
# then open:  http://localhost:8000/../../../frontend/index.html?src=./event_study.json
#   (or copy frontend/index.html next to the JSON and open ?src=event_study.json)
```

Three ways to load a contract:

- **Open file…** — a local file picker (no server needed).
- **Drag & drop** a `.json` file anywhere on the page.
- **`?src=URL`** or the URL box — fetches a contract when the page is served
  (browsers block `fetch()` of `file://`, so use a file pick when opening
  directly).

## What it renders

- The provenance header (`payload_type`, `schema_version`, `generated_at_utc`,
  `source.source_path`, `source.milestone`).
- The `dashboard_caveat` banner.
- Each table in `tables` as a sortable-width, scrollable HTML table.

The exact contract shape the UI depends on is pinned by
`tests/frontend/test_dashboard_contract_compatibility.py`, so backend schema
drift is caught in CI.
