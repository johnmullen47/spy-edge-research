#!/usr/bin/env python3
"""M128 — fetch 30-min RTH bars for the universe (post-freeze data pull).

Reads data/raw/m128/universe_membership.csv, takes the UNION of all symbols ever in the
universe (+ the negative-control ETFs SPY/QQQ/IWM/DIA), and fetches 30Min SIP bars over
[2016-01-01, 2026-06-13] (2016 included so the L-lag reaching back from 2017 has data).
Writes one canonical OHLCV CSV per symbol to data/raw/m128/bars30/<SYM>.csv (RTH only).

Resumable: skips symbols whose CSV already exists. Multi-symbol endpoint, paginated.
Stdlib only. Research-only.
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
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

DATA_HOST = "https://data.alpaca.markets"
EASTERN = ZoneInfo("America/New_York")
CSV_COLUMNS = ("timestamp", "symbol", "open", "high", "low", "close", "volume")
PAGE_LIMIT = 10000
CONTROL_ETFS = ["SPY", "QQQ", "IWM", "DIA"]
# NOTE: the 30Min bars endpoint hard-caps pages at ~419 bars (the `limit` param is
# ignored), and multi-symbol requests SHARE that page. So we fetch ONE symbol per
# request (full page per symbol) and parallelize across symbols via --shard/--nshards.


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


def _in_rth(moment: datetime) -> bool:
    if moment.weekday() >= 5:
        return False
    minutes = moment.hour * 60 + moment.minute
    return 9 * 60 + 30 <= minutes < 16 * 60


def fetch_batch(symbols, start, end, key, secret):
    """Return {symbol: [rows]} of RTH 30Min bars (rows are canonical CSV tuples)."""
    headers = {"APCA-API-KEY-ID": key, "APCA-API-SECRET-KEY": secret}
    out = defaultdict(list)
    seen = defaultdict(set)
    page_token = None
    base = f"{DATA_HOST}/v2/stocks/bars"
    while True:
        params = {
            "symbols": ",".join(symbols), "timeframe": "30Min", "start": start,
            "end": end, "limit": str(PAGE_LIMIT), "adjustment": "raw", "feed": "sip",
        }
        if page_token:
            params["page_token"] = page_token
        req = urllib.request.Request(base + "?" + urllib.parse.urlencode(params), headers=headers)
        payload = None
        for attempt in range(12):
            try:
                with urllib.request.urlopen(req, timeout=90) as resp:
                    payload = json.loads(resp.read().decode("utf-8"))
                break
            except urllib.error.HTTPError as e:
                if e.code == 429:
                    ra = e.headers.get("Retry-After")
                    time.sleep(float(ra) if ra and ra.isdigit() else min(2.0 * (attempt + 1), 20))
                    continue
                if e.code >= 500:
                    time.sleep(min(2.0 * (attempt + 1), 20))
                    continue
                raise SystemExit(f"HTTP {e.code}: {e.read().decode('utf-8','replace')[:200]}")
            except Exception:  # URLError, socket timeout, http.client errors, conn reset
                time.sleep(min(1.5 * (attempt + 1), 20))
        if payload is None:
            raise SystemExit("Repeated network failures.")
        for sym, bars in (payload.get("bars") or {}).items():
            for b in bars:
                utc = datetime.fromisoformat(b["t"].replace("Z", "+00:00"))
                et = utc.astimezone(EASTERN)
                if not _in_rth(et):
                    continue
                stamp = et.strftime("%Y-%m-%d %H:%M:%S")
                if stamp in seen[sym]:
                    continue
                seen[sym].add(stamp)
                out[sym].append([stamp, sym, b["o"], b["h"], b["l"], b["c"], b["v"]])
        page_token = payload.get("next_page_token")
        if not page_token:
            break
    return out


def _fetch_one(sym, start, end, key, secret, bars_dir):
    data = fetch_batch([sym], start, end, key, secret)
    rows = sorted(data.get(sym, []))
    tmp = bars_dir / f".{sym}.csv.tmp"
    with tmp.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(CSV_COLUMNS)
        w.writerows(rows)
    tmp.replace(bars_dir / f"{sym}.csv")   # atomic; partial files never look complete
    return sym, len(rows)


def main() -> None:
    import argparse
    from concurrent.futures import ThreadPoolExecutor, as_completed

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("secrets", nargs="?", default="secrets/alpaca.env")
    ap.add_argument("--workers", type=int, default=8, help="concurrent fetch threads (one process)")
    ap.add_argument("--start", default="2016-11-01T00:00:00Z",
                    help="enough lookback for L=22 reach-back from early 2017")
    ap.add_argument("--end", default="2026-06-13T23:59:59Z")
    args = ap.parse_args()

    base = Path("data/raw/m128")
    bars_dir = base / "bars30"
    bars_dir.mkdir(parents=True, exist_ok=True)
    key, secret = load_credentials(Path(args.secrets))

    import pandas as pd

    memb = pd.read_csv(base / "universe_membership.csv")
    symbols = sorted(set(memb["symbol"].tolist()) | set(CONTROL_ETFS))
    todo = [s for s in symbols if not (bars_dir / f"{s}.csv").exists()]
    print(f"{len(symbols)} symbols; {len(todo)} to fetch; {args.workers} threads.",
          file=sys.stderr, flush=True)

    t0 = time.time()
    done = 0
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(_fetch_one, s, args.start, args.end, key, secret, bars_dir): s
                for s in todo}
        for fut in as_completed(futs):
            sym, n = fut.result()
            done += 1
            if done % 10 == 0 or done == len(todo):
                el = time.time() - t0
                rate = done / el if el else 0
                eta = (len(todo) - done) / rate if rate else 0
                print(f"[{done}/{len(todo)}] {sym} ({n} bars) elapsed={el:.0f}s eta={eta:.0f}s",
                      file=sys.stderr, flush=True)
    print(f"DONE {done} symbols -> {bars_dir}", file=sys.stderr, flush=True)


if __name__ == "__main__":
    main()
