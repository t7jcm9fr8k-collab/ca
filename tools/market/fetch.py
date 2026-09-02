#!/usr/bin/env python3
"""
fetch.py — get bars from a source, and refuse to hand over an empty series.

Runs on the Mac. It cannot run from a cloud session; every market-data host is
unreachable from there (yahoo, polygon, alpaca, binance, coingecko, stooq,
alphavantage all refused at the proxy, 2026-09-02), which is exactly why the
failure path below matters more than the success path.

THE FAILURE MODE THIS FILE IS BUILT AROUND
    A fetch that cannot reach the host, or reaches it and cannot read the body,
    must NEVER return an empty Series. An empty series and a flat market are the
    same array, and the next tool along would backtest it and report a number.

    So three outcomes are kept strictly separate, as rival.py keeps them:
        NETWORK     could not reach the source at all
        PARSE       reached it, got a body that is not bars
        OK          N bars, with provenance attached
    Only OK ever produces a Series. The other two raise, loudly.

SOURCES
    stooq    daily bars, CSV, NO KEY. Symbols are `aapl.us` style; this file adds
             the `.us` for you. Stooq does not document its adjustment policy —
             the series is recorded as adjustment-not-stated and barqc reports
             any split-sized gap so you can check against a known split.
    alpaca   daily and intraday, JSON, needs a key pair in the environment:
                 ALPACA_KEY_ID, ALPACA_SECRET_KEY
             Never passed as arguments — arguments land in shell history. The
             free tier serves the IEX feed. Adjustment is requested explicitly
             and recorded.

USAGE
    python3 fetch.py --dry-run                            # prove the failure path, offline
    python3 fetch.py --source stooq  --symbol AAPL
    python3 fetch.py --source alpaca --symbol AAPL --timeframe 1d --start 2024-01-01
"""

import argparse
import datetime as dt
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

import bars as B

HERE = os.path.dirname(os.path.abspath(__file__))
TIMEOUT = 25
UA = "market-tools/1.0 (personal research; low volume)"

STOOQ_URL = "https://stooq.com/q/d/l/?s={sym}&i=d"
ALPACA_DATA = "https://data.alpaca.markets/v2/stocks/{sym}/bars"
ALPACA_TF = {"1d": "1Day", "1h": "1Hour", "15m": "15Min", "5m": "5Min", "1m": "1Min"}


class Unreachable(Exception):
    """Could not reach the source at all."""


Unparseable = B.Unparseable      # reached it; body is not bars. NOT zero bars.


def _get(url, headers=None):
    req = urllib.request.Request(url, headers={"User-Agent": UA, **(headers or {})})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            if r.status != 200:
                raise Unreachable(f"HTTP {r.status}")
            return r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            raise Unreachable(f"HTTP {e.code} — credentials refused") from e
        raise Unreachable(f"HTTP {e.code}") from e
    except Exception as e:
        raise Unreachable(f"{type(e).__name__}: {e}") from e


# ---------------------------------------------------------------- stooq

def parse_stooq(body, symbol):
    """
    Stooq's CSV, or its two ways of saying nothing.

    An unknown symbol returns the literal text `No data`. A blocked or throttled
    request returns a short HTML page. Neither is a header + rows, and neither
    may become an empty Series.
    """
    head = body.strip()[:200].lower()
    if head.startswith("no data"):
        raise Unparseable(f"stooq has no data for {symbol!r} — check the symbol "
                          f"(US tickers are `aapl.us`)")
    if "<html" in head or "<!doctype" in head:
        raise Unreachable("stooq returned a page, not a file — throttled or blocked")
    if len(body) < 40:
        raise Unreachable(f"response too short to be a CSV ({len(body)} bytes)")
    return B.parse_csv(body, symbol.upper(), "1d", "stooq",
                       adjusted=None,
                       extra={"url": STOOQ_URL.format(sym=_stooq_sym(symbol)),
                              "adjustment": "not documented by source"})


def _stooq_sym(symbol):
    s = symbol.lower()
    return s if "." in s else f"{s}.us"


def fetch_stooq(symbol):
    body = _get(STOOQ_URL.format(sym=_stooq_sym(symbol)))
    return parse_stooq(body, symbol)


# ---------------------------------------------------------------- alpaca

def credentials():
    key = os.environ.get("ALPACA_KEY_ID", "").strip()
    sec = os.environ.get("ALPACA_SECRET_KEY", "").strip()
    if not key or not sec:
        raise Unreachable("ALPACA_KEY_ID / ALPACA_SECRET_KEY not set in the "
                          "environment; export them, never pass them as arguments")
    return {"APCA-API-KEY-ID": key, "APCA-API-SECRET-KEY": sec}


def parse_alpaca_page(body):
    try:
        j = json.loads(body)
    except json.JSONDecodeError as e:
        raise Unparseable(f"alpaca body is not JSON: {e}")
    if "bars" not in j:
        raise Unparseable(f"alpaca JSON has no `bars` key: {list(j)[:6]}")
    return j.get("bars") or [], j.get("next_page_token")


def fetch_alpaca(symbol, timeframe="1d", start=None, end=None, adjustment="split",
                 feed="iex"):
    if timeframe not in ALPACA_TF:
        raise ValueError(f"alpaca timeframe must be one of {', '.join(ALPACA_TF)}")
    hdr = credentials()
    q = {"timeframe": ALPACA_TF[timeframe], "limit": 10000,
         "adjustment": adjustment, "feed": feed}
    if start:
        q["start"] = start
    if end:
        q["end"] = end
    raw, token, pages = [], None, 0
    while True:
        if token:
            q["page_token"] = token
        url = ALPACA_DATA.format(sym=symbol.upper()) + "?" + urllib.parse.urlencode(q)
        page, token = parse_alpaca_page(_get(url, hdr))
        raw.extend(page)
        pages += 1
        if not token or pages > 50:
            break

    bars = []
    for r in raw:
        try:
            ts = dt.datetime.fromisoformat(r["t"].replace("Z", "+00:00"))
            if timeframe == "1d":
                d = ts.astimezone(B.UTC).date()      # alpaca daily t is 05:00Z; pin to the date
                ts = dt.datetime(d.year, d.month, d.day, tzinfo=B.UTC)
            bars.append(B.Bar(ts, float(r["o"]), float(r["h"]), float(r["l"]),
                              float(r["c"]), float(r.get("v", 0))))
        except (KeyError, ValueError, TypeError) as e:
            raise Unparseable(f"alpaca bar {r} unreadable: {e}")
    return B.Series(symbol.upper(), timeframe, bars, {
        "source": "alpaca", "fetched_at": dt.datetime.now(B.UTC).isoformat(timespec="seconds"),
        "adjusted": adjustment != "raw", "adjustment": adjustment, "feed": feed,
        "pages": pages, "start": start, "end": end})


# ---------------------------------------------------------------- cli

def dry_run():
    """Prove, offline, that the three outcomes stay apart."""
    print("dry run — no market host is contacted\n")

    try:
        _get("https://127.0.0.1:9/nothing")
        print("  ??   unreachable host returned something — this should not happen")
    except Unreachable as e:
        print(f"  ok   NETWORK  unreachable host raised Unreachable: {e}")

    try:
        parse_stooq("No data", "ZZZZ")
        print("  ??   'No data' produced a series — THIS IS THE BUG THIS FILE PREVENTS")
    except Unparseable as e:
        print(f"  ok   PARSE    stooq 'No data' raised Unparseable, not an empty series")

    try:
        parse_alpaca_page('{"message": "forbidden"}')
        print("  ??   a JSON error body produced bars")
    except Unparseable as e:
        print(f"  ok   PARSE    alpaca error JSON raised Unparseable: {e}")

    s = parse_stooq("Date,Open,High,Low,Close,Volume\n2024-01-02,1,2,0.5,1.5,100\n"
                    "2024-01-03,1.5,2,1,1.8,120\n", "TEST")
    print(f"  ok   OK       a real body gives {len(s)} bars with source "
          f"{s.provenance['source']!r}")
    print("\nOnly OK produced bars. Run for real on the Mac.")


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--source", choices=["stooq", "alpaca"], default="stooq")
    ap.add_argument("--symbol")
    ap.add_argument("--timeframe", default="1d", choices=sorted(B.TIMEFRAMES))
    ap.add_argument("--start", help="alpaca: RFC3339 or YYYY-MM-DD")
    ap.add_argument("--end")
    ap.add_argument("--adjustment", default="split", choices=["raw", "split", "dividend", "all"])
    ap.add_argument("--out", help="CSV path; default bars/<SYMBOL>-<tf>.csv")
    a = ap.parse_args()

    if a.dry_run:
        dry_run()
        return
    if not a.symbol:
        ap.error("--symbol is required (or use --dry-run)")

    try:
        if a.source == "stooq":
            if a.timeframe != "1d":
                sys.exit("stooq serves daily bars only; use --source alpaca for intraday")
            s = fetch_stooq(a.symbol)
        else:
            s = fetch_alpaca(a.symbol, a.timeframe, a.start, a.end, a.adjustment)
    except Unreachable as e:
        print(f"NETWORK  {e}", file=sys.stderr)
        print("Nothing was written. No bars means no bars, not zero bars.", file=sys.stderr)
        sys.exit(6)
    except Unparseable as e:
        print(f"PARSE    {e}", file=sys.stderr)
        print("Reached the source, could not read bars. Nothing was written.", file=sys.stderr)
        sys.exit(2)

    path = a.out or B.bars_path(a.symbol, a.timeframe)
    B.to_csv(s, path)
    print(f"OK       {s.describe()}")
    print(f"wrote    {path}")
    print(f"\nnext:  python3 barqc.py --csv {path} --symbol {a.symbol} "
          f"--timeframe {a.timeframe} --source {a.source}"
          + (" --adjusted yes" if s.provenance.get("adjusted") is True else
             " --adjusted no" if s.provenance.get("adjusted") is False else ""))


if __name__ == "__main__":
    main()
