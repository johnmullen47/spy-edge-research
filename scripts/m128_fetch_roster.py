#!/usr/bin/env python3
"""M128 step 1A.1 — fetch the no-lookahead candidate roster from Alpaca assets.

Roster = (active ∪ inactive) us_equity. This is Alpaca's own complete record of
every US equity it has ever carried, so using it (rather than active-only) is the
survivorship-control step: delisted names are included where Alpaca retained them.

Applies a MECHANICAL, documented common-stock symbol filter (no discretion): keep
plain tickers ^[A-Z]{1,5}$ plus dual-class BRK.A/BRK.B style ^[A-Z]{1,4}\\.[A-Z]$.
Drops warrants/units/preferreds/rights (suffixes .WS .U .PR .RT etc.).

Writes data/raw/m128/assets_roster.json (symbol -> {status, name, exchange}).
Stdlib only. Research-only.
"""
from __future__ import annotations

import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

TRADING_HOST = "https://paper-api.alpaca.markets"
COMMON_RE = re.compile(r"^[A-Z]{1,5}$|^[A-Z]{1,4}\.[A-Z]$")


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


def fetch_assets(status: str, key: str, secret: str) -> list[dict]:
    url = f"{TRADING_HOST}/v2/assets?" + urllib.parse.urlencode(
        {"status": status, "asset_class": "us_equity"}
    )
    req = urllib.request.Request(
        url, headers={"APCA-API-KEY-ID": key, "APCA-API-SECRET-KEY": secret}
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main() -> None:
    secrets = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("secrets/alpaca.env")
    out_path = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("data/raw/m128/assets_roster.json")
    key, secret = load_credentials(secrets)

    roster: dict[str, dict] = {}
    counts = {"active_raw": 0, "inactive_raw": 0, "kept_common": 0, "dropped_nonstd": 0}
    for status in ("active", "inactive"):
        assets = fetch_assets(status, key, secret)
        counts[f"{status}_raw"] = len(assets)
        for a in assets:
            sym = a.get("symbol", "")
            if not COMMON_RE.match(sym):
                counts["dropped_nonstd"] += 1
                continue
            # First occurrence wins; prefer 'active' record if a symbol appears in both.
            if sym not in roster:
                roster[sym] = {
                    "status": status,
                    "name": a.get("name"),
                    "exchange": a.get("exchange"),
                }
    counts["kept_common"] = len(roster)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps({"counts": counts, "roster": roster}, indent=2))
    print(json.dumps(counts, indent=2))
    print(f"Wrote {len(roster)} common-stock symbols -> {out_path}")


if __name__ == "__main__":
    main()
