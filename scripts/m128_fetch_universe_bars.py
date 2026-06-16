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
BATCH = 40
PAGE_LIMIT = 10000
CONTROL_ETFS = ["SPY", "QQQ", "IWM", "DIA"]


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
        for attempt in range(5):
            try:
                with urllib.request.urlopen(req, timeout=120) as resp:
                    payload = json.loads(resp.read().decode("utf-8"))
                break
            except urllib.error.HTTPError as e:
                if e.code == 429:
                    time.sleep(2.0 * (attempt + 1))
                    continue
                raise SystemExit(f"HTTP {e.code}: {e.read().decode('utf-8','replace')[:200]}")
            except urllib.error.URLError:
                time.sleep(1.5 * (attempt + 1))
        else:
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
        time.sleep(0.3)
    return out


def main() -> None:
    secrets = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("secrets/alpaca.env")
    base = Path("data/raw/m128")
    bars_dir = base / "bars30"
    bars_dir.mkdir(parents=True, exist_ok=True)
    key, secret = load_credentials(secrets)

    import pandas as pd

    memb = pd.read_csv(base / "universe_membership.csv")
    symbols = sorted(set(memb["symbol"].tolist()) | set(CONTROL_ETFS))
    todo = [s for s in symbols if not (bars_dir / f"{s}.csv").exists()]
    print(f"{len(symbols)} symbols total ({len(CONTROL_ETFS)} control ETFs); {len(todo)} to fetch.",
          file=sys.stderr)

    start, end = "2016-01-01T00:00:00Z", "2026-06-13T23:59:59Z"
    batches = [todo[i : i + BATCH] for i in range(0, len(todo), BATCH)]
    t0 = time.time()
    for bi, batch in enumerate(batches):
        data = fetch_batch(batch, start, end, key, secret)
        for sym in batch:
            rows = sorted(data.get(sym, []))
            path = bars_dir / f"{sym}.csv"
            with path.open("w", encoding="utf-8", newline="") as fh:
                w = csv.writer(fh)
                w.writerow(CSV_COLUMNS)
                w.writerows(rows)
        el = time.time() - t0
        print(f"[{bi+1}/{len(batches)}] {batch[0]}..{batch[-1]} "
              f"({sum(len(data.get(s, [])) for s in batch)} bars) elapsed={el:.0f}s",
              file=sys.stderr, flush=True)
    print(f"DONE -> {bars_dir}", file=sys.stderr)


if __name__ == "__main__":
    main()
