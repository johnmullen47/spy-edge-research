#!/usr/bin/env python3
"""M128 step 1A.2 — scan daily dollar-volume for the full candidate roster.

Reads data/raw/m128/assets_roster.json, fetches DAILY bars (multi-symbol endpoint,
SIP, raw) for every candidate over [start, end], and streams a compact monthly
aggregate to data/raw/m128/daily_dollar_volume.csv:

    symbol, ym (YYYY-MM), sum_dv (sum of close*volume that month), n_days

This is the no-lookahead liquidity primitive. Trailing-12m ADV at each rebalance is
computed downstream from this file (m128_build_universe.py). NOT a cross-sectional
result; this is data inventory / universe construction (allowed pre-freeze).

Resumable: appends per-batch and records completed batches in a checkpoint file so a
re-run skips finished batches. Stdlib only. Research-only.
"""
from __future__ import annotations

import csv
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

DATA_HOST = "https://data.alpaca.markets"
EASTERN = ZoneInfo("America/New_York")
BATCH = 400            # symbols per multi-symbol request
PAGE_LIMIT = 10000


def load_credentials(secrets_path: Path) -> tuple[str, str]:
    import os

    key = os.environ.get("APCA_API_KEY_ID")
    secret = os.environ.get("APCA_API_SECRET_KEY")
    if (not key or not secret) and secrets_path.exists():
        for line in secrets_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            name, value = line.split("=", 1)
            name, value = name.strip(), value.strip().strip('"').strip("'")
            if name == "APCA_API_KEY_ID" and not key:
                key = value
            elif name == "APCA_API_SECRET_KEY" and not secret:
                secret = value
    if not key or not secret:
        sys.exit("Missing Alpaca credentials.")
    return key, secret


def fetch_batch_monthly(symbols, start, end, key, secret):
    """Yield (symbol, ym, sum_dv, n_days) monthly aggregates for a batch."""
    headers = {"APCA-API-KEY-ID": key, "APCA-API-SECRET-KEY": secret}
    # agg[symbol][ym] = [sum_dv, n_days]
    agg = defaultdict(lambda: defaultdict(lambda: [0.0, 0]))
    page_token = None
    base = f"{DATA_HOST}/v2/stocks/bars"
    while True:
        params = {
            "symbols": ",".join(symbols),
            "timeframe": "1Day",
            "start": start,
            "end": end,
            "limit": str(PAGE_LIMIT),
            "adjustment": "raw",
            "feed": "sip",
        }
        if page_token:
            params["page_token"] = page_token
        req = urllib.request.Request(base + "?" + urllib.parse.urlencode(params), headers=headers)
        for attempt in range(4):
            try:
                with urllib.request.urlopen(req, timeout=120) as resp:
                    payload = json.loads(resp.read().decode("utf-8"))
                break
            except urllib.error.HTTPError as e:
                if e.code == 429:
                    time.sleep(2.0 * (attempt + 1))
                    continue
                body = e.read().decode("utf-8", "replace")[:200]
                raise SystemExit(f"HTTP {e.code}: {body}")
            except urllib.error.URLError:
                time.sleep(1.5 * (attempt + 1))
        else:
            raise SystemExit("Repeated network failures.")
        bars_by_sym = payload.get("bars") or {}
        for sym, bars in bars_by_sym.items():
            for b in bars:
                # b['t'] like '2016-01-04T05:00:00Z'; daily bar date in ET
                ym = b["t"][:7]  # YYYY-MM (UTC date ~ trade date for daily bars)
                dv = float(b["c"]) * float(b["v"])
                cell = agg[sym][ym]
                cell[0] += dv
                cell[1] += 1
        page_token = payload.get("next_page_token")
        if not page_token:
            break
        time.sleep(0.3)
    for sym, months in agg.items():
        for ym, (sum_dv, n_days) in months.items():
            yield sym, ym, sum_dv, n_days


def main() -> None:
    secrets = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("secrets/alpaca.env")
    roster_path = Path("data/raw/m128/assets_roster.json")
    out_path = Path("data/raw/m128/daily_dollar_volume.csv")
    ckpt_path = Path("data/raw/m128/scan_checkpoint.json")
    start = "2016-01-01T00:00:00Z"
    end = "2026-06-13T23:59:59Z"

    key, secret = load_credentials(secrets)
    roster = json.loads(roster_path.read_text())["roster"]
    symbols = sorted(roster.keys())
    batches = [symbols[i : i + BATCH] for i in range(0, len(symbols), BATCH)]

    done = set()
    if ckpt_path.exists():
        done = set(json.loads(ckpt_path.read_text()).get("done", []))

    out_path.parent.mkdir(parents=True, exist_ok=True)
    new_file = not out_path.exists()
    fh = out_path.open("a", encoding="utf-8", newline="")
    writer = csv.writer(fh)
    if new_file:
        writer.writerow(["symbol", "ym", "sum_dv", "n_days"])

    t0 = time.time()
    for bi, batch in enumerate(batches):
        if bi in done:
            continue
        rows = 0
        for sym, ym, sum_dv, n_days in fetch_batch_monthly(batch, start, end, key, secret):
            writer.writerow([sym, ym, f"{sum_dv:.2f}", n_days])
            rows += 1
        fh.flush()
        done.add(bi)
        ckpt_path.write_text(json.dumps({"done": sorted(done), "n_batches": len(batches)}))
        el = time.time() - t0
        print(
            f"[{bi+1}/{len(batches)}] {batch[0]}..{batch[-1]} rows={rows} elapsed={el:.0f}s",
            file=sys.stderr,
            flush=True,
        )
    fh.close()
    print(f"DONE {len(batches)} batches -> {out_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
