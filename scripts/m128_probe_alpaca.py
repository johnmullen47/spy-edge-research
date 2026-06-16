#!/usr/bin/env python3
"""M128 Gate 0.5 probe — can Alpaca support a survivorship-bias-free stock universe?

Standalone, stdlib-only (mirrors fetch_spy_bars.py). Answers three decision-critical
questions BEFORE any M128 data spend or implementation:

  Q1. Does Alpaca SIP serve 30-min bars for arbitrary individual stocks back to 2016?
  Q2. Does Alpaca RETAIN historical bars for DELISTED symbols (the survivorship crux)?
  Q3. Does the /v2/assets endpoint expose inactive/delisted names (for membership)?

Prints a JSON summary. Credentials are never printed. Research-only.
"""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

DATA_HOST = "https://data.alpaca.markets"
TRADING_HOST = "https://paper-api.alpaca.markets"


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
            name = name.strip()
            value = value.strip().strip('"').strip("'")
            if name == "APCA_API_KEY_ID" and not key:
                key = value
            elif name == "APCA_API_SECRET_KEY" and not secret:
                secret = value
    if not key or not secret:
        sys.exit(f"Missing Alpaca credentials in env or {secrets_path}.")
    return key, secret


def _get(url: str, key: str, secret: str) -> tuple[int, dict]:
    headers = {"APCA-API-KEY-ID": key, "APCA-API-SECRET-KEY": secret}
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return e.code, {"error": e.read().decode("utf-8", "replace")[:300]}
    except urllib.error.URLError as e:
        return -1, {"error": str(e)}


def probe_bars(symbol: str, start: str, end: str, key: str, secret: str) -> dict:
    params = {
        "timeframe": "30Min",
        "start": f"{start}T00:00:00Z",
        "end": f"{end}T23:59:59Z",
        "limit": "100",
        "adjustment": "raw",
        "feed": "sip",
    }
    url = f"{DATA_HOST}/v2/stocks/{urllib.parse.quote(symbol)}/bars?" + urllib.parse.urlencode(params)
    status, payload = _get(url, key, secret)
    bars = payload.get("bars") or [] if isinstance(payload, dict) else []
    out = {
        "symbol": symbol,
        "window": f"{start}..{end}",
        "http": status,
        "n_bars": len(bars),
    }
    if bars:
        out["first_t"] = bars[0].get("t")
        out["last_t"] = bars[-1].get("t")
    if status != 200:
        out["error"] = payload.get("error") if isinstance(payload, dict) else str(payload)
    return out


def probe_assets(key: str, secret: str) -> dict:
    out = {}
    for status_filter in ("active", "inactive"):
        url = f"{TRADING_HOST}/v2/assets?" + urllib.parse.urlencode(
            {"status": status_filter, "asset_class": "us_equity"}
        )
        http, payload = _get(url, key, secret)
        if http != 200:
            out[status_filter] = {"http": http, "error": payload.get("error")}
            continue
        assets = payload if isinstance(payload, list) else []
        symbols = {a.get("symbol") for a in assets}
        out[status_filter] = {
            "http": http,
            "count": len(assets),
            "tradable_count": sum(1 for a in assets if a.get("tradable")),
        }
        # Did known delisted names land in this bucket?
        for probe in ("TWTR", "ATVI", "XLNX", "CELG", "WORK", "DISCA"):
            out[status_filter].setdefault("known_delisted_present", {})[probe] = probe in symbols
    return out


def main() -> None:
    secrets = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("secrets/alpaca.env")
    key, secret = load_credentials(secrets)

    result = {"q1_arbitrary_stock_2016": [], "q2_delisted_bars": [], "q3_assets": {}}

    # Q1: arbitrary liquid stocks, early-2016 depth + recent
    for sym in ("AAPL", "MSFT", "JPM"):
        result["q1_arbitrary_stock_2016"].append(
            probe_bars(sym, "2016-01-04", "2016-01-08", key, secret)
        )
    result["q1_arbitrary_stock_2016"].append(
        probe_bars("AAPL", "2026-05-01", "2026-05-05", key, secret)
    )

    # Q2: delisted symbols, probed DURING their active life
    delisted = [
        ("TWTR", "2022-09-01", "2022-09-09"),   # Twitter, delisted ~2022-11 (acquired)
        ("ATVI", "2023-08-01", "2023-08-09"),   # Activision, delisted ~2023-10 (MSFT)
        ("XLNX", "2021-11-01", "2021-11-09"),   # Xilinx, delisted ~2022-02 (AMD)
        ("CELG", "2019-08-01", "2019-08-09"),   # Celgene, delisted ~2019-11 (BMS)
        ("WORK", "2021-05-03", "2021-05-11"),   # Slack, delisted ~2021-07 (CRM)
        ("DISCA", "2022-02-01", "2022-02-09"),  # Discovery, merged ~2022-04 (WBD)
    ]
    for sym, s, e in delisted:
        result["q2_delisted_bars"].append(probe_bars(sym, s, e, key, secret))

    # Q3: assets endpoint coverage
    result["q3_assets"] = probe_assets(key, secret)

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
