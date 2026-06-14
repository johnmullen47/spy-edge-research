#!/usr/bin/env python3
"""Fetch historical SPY 1-minute bars from Alpaca into a canonical OHLCV CSV.

This is a STANDALONE network utility. It is intentionally NOT part of the
``spy_edge_research`` package (which stays offline and network-free, with no
network in its tests). It uses only the Python standard library — no third-party
dependency — so it runs in the project venv as-is.

It reads Alpaca credentials from the environment (``APCA_API_KEY_ID`` /
``APCA_API_SECRET_KEY``) or, failing that, from a gitignored secrets file
(default ``secrets/alpaca.env``). It pulls 1-minute bars from the Alpaca Market
Data v2 historical endpoint (paginated via ``next_page_token``), optionally
filters to the regular U.S. equity session, and writes a CSV that
``load_ohlcv_csv`` / ``validate_ohlcv_schema`` accept verbatim:

    timestamp,symbol,open,high,low,close,volume

Credentials are never printed. Free Alpaca data is the IEX feed (single venue,
thin/understated volume); pass ``--feed sip`` if you have the paid plan.

Example:
    .venv/bin/python scripts/fetch_spy_bars.py --start 2023-01-01 --end 2024-12-31
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

DATA_HOST = "https://data.alpaca.markets"
EASTERN = ZoneInfo("America/New_York")
CSV_COLUMNS = ("timestamp", "symbol", "open", "high", "low", "close", "volume")
REGULAR_OPEN = (9, 30)   # 09:30 ET inclusive
REGULAR_CLOSE = (16, 0)  # 16:00 ET exclusive


def load_credentials(secrets_path: Path) -> tuple[str, str]:
    """Return (key_id, secret) from env, falling back to the secrets file."""
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
    if not key or not secret or secret == "PASTE_YOUR_FULL_SECRET_HERE":
        sys.exit(
            "Missing Alpaca credentials. Set APCA_API_KEY_ID / APCA_API_SECRET_KEY "
            f"in the environment or in {secrets_path}."
        )
    return key, secret


def iter_bars(
    symbol: str,
    start: str,
    end: str,
    *,
    key: str,
    secret: str,
    feed: str,
    adjustment: str,
    timeframe: str,
    limit: int = 10000,
):
    """Yield raw Alpaca bar dicts across all pages for the date range."""
    headers = {"APCA-API-KEY-ID": key, "APCA-API-SECRET-KEY": secret}
    base = f"{DATA_HOST}/v2/stocks/{urllib.parse.quote(symbol)}/bars"
    page_token: str | None = None
    while True:
        params = {
            "timeframe": timeframe,
            "start": start,
            "end": end,
            "limit": str(limit),
            "adjustment": adjustment,
            "feed": feed,
        }
        if page_token:
            params["page_token"] = page_token
        request = urllib.request.Request(
            base + "?" + urllib.parse.urlencode(params), headers=headers
        )
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            body = error.read().decode("utf-8", "replace")
            sys.exit(f"Alpaca API error {error.code}: {body}")
        except urllib.error.URLError as error:
            sys.exit(f"Network error reaching Alpaca: {error}")
        for bar in payload.get("bars") or []:
            yield bar
        page_token = payload.get("next_page_token")
        if not page_token:
            return
        time.sleep(0.3)  # gentle on the free-tier rate limit


def _to_eastern(bar_time: str) -> datetime:
    """Parse an Alpaca RFC3339 UTC bar timestamp into an aware ET datetime."""
    utc = datetime.fromisoformat(bar_time.replace("Z", "+00:00"))
    return utc.astimezone(EASTERN)


def _in_regular_session(moment: datetime) -> bool:
    if moment.weekday() >= 5:  # Saturday/Sunday
        return False
    minutes = moment.hour * 60 + moment.minute
    return (
        REGULAR_OPEN[0] * 60 + REGULAR_OPEN[1]
        <= minutes
        < REGULAR_CLOSE[0] * 60 + REGULAR_CLOSE[1]
    )


def write_csv(
    rows,
    output_path: Path,
    *,
    symbol: str,
    regular_hours_only: bool,
) -> int:
    """Write canonical OHLCV rows; dedupe + keep ascending; return row count."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    seen: set[str] = set()
    written = 0
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(CSV_COLUMNS)
        for bar in rows:
            moment = _to_eastern(bar["t"])
            if regular_hours_only and not _in_regular_session(moment):
                continue
            stamp = moment.strftime("%Y-%m-%d %H:%M:%S")
            if stamp in seen:
                continue
            seen.add(stamp)
            writer.writerow(
                [stamp, symbol, bar["o"], bar["h"], bar["l"], bar["c"], bar["v"]]
            )
            written += 1
    return written


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    default_end = datetime.now(timezone.utc) - timedelta(minutes=20)
    default_start = default_end - timedelta(days=730)
    parser.add_argument("--symbol", default="SPY")
    parser.add_argument(
        "--start",
        default=default_start.strftime("%Y-%m-%d"),
        help="UTC start date YYYY-MM-DD (default: ~2 years ago).",
    )
    parser.add_argument(
        "--end",
        default=default_end.strftime("%Y-%m-%d"),
        help="UTC end date YYYY-MM-DD (default: ~yesterday).",
    )
    parser.add_argument("--timeframe", default="1Min")
    parser.add_argument("--feed", default="iex", choices=["iex", "sip"])
    parser.add_argument("--adjustment", default="raw", choices=["raw", "split", "all"])
    parser.add_argument("--output", default="data/raw/spy_1min.csv")
    parser.add_argument("--secrets", default="secrets/alpaca.env")
    parser.add_argument(
        "--all-hours",
        action="store_true",
        help="Keep pre/post-market bars (default: regular 09:30-16:00 ET only).",
    )
    args = parser.parse_args()

    key, secret = load_credentials(Path(args.secrets))
    start = f"{args.start}T00:00:00Z"
    end = f"{args.end}T23:59:59Z"

    print(
        f"Fetching {args.symbol} {args.timeframe} bars {args.start}..{args.end} "
        f"(feed={args.feed}, adjustment={args.adjustment})...",
        file=sys.stderr,
    )
    bars = iter_bars(
        args.symbol,
        start,
        end,
        key=key,
        secret=secret,
        feed=args.feed,
        adjustment=args.adjustment,
        timeframe=args.timeframe,
    )
    output_path = Path(args.output)
    written = write_csv(
        bars,
        output_path,
        symbol=args.symbol,
        regular_hours_only=not args.all_hours,
    )
    if written == 0:
        sys.exit(
            "No bars written. Check the date range, the feed (free tier = iex), "
            "and that your credentials are valid."
        )
    print(f"Wrote {written} bars -> {output_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
