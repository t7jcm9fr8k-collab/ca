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
import tlsctx

HERE = os.path.dirname(os.path.abspath(__file__))
TIMEOUT = 25
UA = "market-tools/1.0 (personal research; low volume)"
# Stooq serves its front page to anything that does not look like a browser.
# A browser UA for the one CSV request is the same courtesy rival.py extends
# to Etsy: low volume, one file, identified as a person's browser.
BROWSER_UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/122.0 Safari/537.36")

STOOQ_URL = "https://stooq.com/q/d/l/?s={sym}&i=d"
STOOQ_PAGE = "https://stooq.com/q/d/?s={sym}"
ALPACA_DATA = "https://data.alpaca.markets/v2/stocks/{sym}/bars"
ALPACA_TF = {"1d": "1Day", "1h": "1Hour", "15m": "15Min", "5m": "5Min", "1m": "1Min"}


class Unreachable(Exception):
    """Could not reach the source at all."""


Unparseable = B.Unparseable      # reached it; body is not bars. NOT zero bars.


def _get(url, headers=None):
    req = urllib.request.Request(url, headers={"User-Agent": UA, **(headers or {})})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT, context=tlsctx.context()) as r:
            if r.status != 200:
                raise Unreachable(f"HTTP {r.status}")
            return r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            raise Unreachable(f"HTTP {e.code} — credentials refused") from e
        raise Unreachable(f"HTTP {e.code}") from e
    except Exception as e:
        # A certificate failure is NETWORK — nothing was read — but it is the
        # one network failure with a fix on this machine, so say what it is.
        if tlsctx.is_cert_failure(e):
            raise Unreachable(tlsctx.explain(e)) from e
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
        raise Unreachable(_page_message(body, symbol))
    if "exceeded" in head and "limit" in head:
        raise Unreachable(f"stooq daily hit limit reached — it said: "
                          f"{body.strip()[:120]!r}. Try tomorrow, or download by hand: "
                          f"{manual_download_hint(symbol)}")
    if len(body) < 40:
        raise Unreachable(f"response too short to be a CSV ({len(body)} bytes): "
                          f"{body.strip()[:80]!r}. {manual_download_hint(symbol)}")
    return B.parse_csv(body, symbol.upper(), "1d", "stooq",
                       adjusted=None,
                       extra={"url": STOOQ_URL.format(sym=_stooq_sym(symbol)),
                              "adjustment": "not documented by source"})


def _visible_text(html, n=160):
    """The first bit of a page a person would read, so the error can quote it."""
    import re
    t = re.sub(r"<script.*?</script>|<style.*?</style>", " ", html, flags=re.S | re.I)
    t = re.sub(r"<[^>]+>", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t[:n]


def manual_download_hint(symbol):
    sym = _stooq_sym(symbol)
    return (f"Download it in a browser instead — open "
            f"{STOOQ_PAGE.format(sym=sym)} , click the CSV/download link, and save "
            f"it as bars/{symbol.upper()}-1d.csv. bars.py reads Stooq's format as is.")


def _page_message(body, symbol):
    return (f"stooq returned a web page, not a CSV. It reads: "
            f"{_visible_text(body)!r}. Usually a bot check or a rate limit. "
            f"{manual_download_hint(symbol)}")


def _stooq_sym(symbol):
    s = symbol.lower()
    return s if "." in s else f"{s}.us"


def fetch_stooq(symbol):
    body = _get(STOOQ_URL.format(sym=_stooq_sym(symbol)),
                headers={"User-Agent": BROWSER_UA,
                         "Accept": "text/csv,text/plain,*/*;q=0.8",
                         "Referer": STOOQ_PAGE.format(sym=_stooq_sym(symbol))})
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


def regular_session(bars):
    """
    Keep only bars inside 09:30–16:00 New York. Alpaca's minute bars include
    pre- and post-market (04:00–20:00), which barqc rightly refuses as
    off-calendar and which intraday.py must not see. Returns (kept, dropped).
    """
    try:
        from zoneinfo import ZoneInfo
        ny = ZoneInfo("America/New_York")
    except Exception as e:
        raise Unreachable(f"no timezone database ({type(e).__name__}); cannot "
                          f"separate the regular session from extended hours")
    lo, hi = dt.time(9, 30), dt.time(16, 0)
    kept = [b for b in bars if lo <= b.ts.astimezone(ny).time() < hi]
    return kept, len(bars) - len(kept)


def fetch_alpaca(symbol, timeframe="1d", start=None, end=None, adjustment="split",
                 feed="iex", regular_only=True, max_pages=1000):
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
        if pages % 10 == 0:
            print(f"  … {pages} pages, {len(raw)} bars so far", file=sys.stderr)
        if not token or pages >= max_pages:
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
    dropped = 0
    session = "daily"
    if timeframe != "1d":
        if regular_only:
            bars, dropped = regular_session(bars)
            session = "regular (09:30–16:00 NY)"
        else:
            session = "extended hours included"
    return B.Series(symbol.upper(), timeframe, bars, {
        "source": "alpaca", "fetched_at": dt.datetime.now(B.UTC).isoformat(timespec="seconds"),
        "adjusted": adjustment != "raw", "adjustment": adjustment, "feed": feed,
        "pages": pages, "start": start, "end": end,
        "session": session, "extended_bars_dropped": dropped})


# ---------------------------------------------------------------- merge

def merge(existing, new):
    """
    Union of two Series of the same symbol and timeframe, by timestamp; the
    new bar wins on a collision. For patching a feed hole — one missing day
    fetched on its own and folded back in — without refetching six years.
    Returns (merged Series, bars added, bars replaced).
    """
    if existing.symbol != new.symbol or existing.timeframe != new.timeframe:
        raise ValueError(f"cannot merge {existing.symbol} {existing.timeframe} with "
                         f"{new.symbol} {new.timeframe}")
    by = {b.ts: b for b in existing.bars}
    added = replaced = 0
    for b in new.bars:
        if b.ts in by:
            replaced += 1
        else:
            added += 1
        by[b.ts] = b
    prov = dict(existing.provenance)
    prov["merged"] = (prov.get("merged") or []) + [{
        "from": new.provenance.get("source"), "start": new.provenance.get("start"),
        "end": new.provenance.get("end"), "added": added, "replaced": replaced,
        "at": dt.datetime.now(B.UTC).isoformat(timespec="seconds")}]
    return B.Series(existing.symbol, existing.timeframe,
                    [by[k] for k in sorted(by)], prov), added, replaced


# ---------------------------------------------------------------- cli

def dry_run():
    """Prove, offline, that the three outcomes stay apart."""
    print("dry run — no market host is contacted\n")
    print(f"  trust    TLS verifies against: {tlsctx.source()}")
    print(f"           python: {sys.executable}\n")

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
    ap.add_argument("--include-extended", action="store_true",
                    help="alpaca intraday: keep pre/post-market bars (barqc will flag them)")
    ap.add_argument("--out", help="CSV path; default bars/<SYMBOL>-<tf>.csv")
    ap.add_argument("--merge-into", metavar="CSV",
                    help="fold the fetched bars into this existing CSV (new bars win) "
                         "instead of writing a new file — for patching a feed hole")
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
            s = fetch_alpaca(a.symbol, a.timeframe, a.start, a.end, a.adjustment,
                             regular_only=not a.include_extended)
    except Unreachable as e:
        print(f"NETWORK  {e}", file=sys.stderr)
        print("Nothing was written. No bars means no bars, not zero bars.", file=sys.stderr)
        sys.exit(6)
    except Unparseable as e:
        print(f"PARSE    {e}", file=sys.stderr)
        print("Reached the source, could not read bars. Nothing was written.", file=sys.stderr)
        sys.exit(2)

    if a.merge_into:
        try:
            base = B.load_csv(a.merge_into, a.symbol, a.timeframe, a.source)
            s, added, replaced = merge(base, s)
        except (B.Unparseable, B.NoProvenance, ValueError) as e:
            sys.exit(f"REFUSED: {e}")
        if added == 0 and replaced == 0:
            sys.exit(f"NOTHING  the fetch returned no bars for that range; {a.merge_into} untouched. "
                     f"If the source has no data for those dates, the hole is real.")
        path = a.merge_into
        B.to_csv(s, path)
        print(f"OK       {s.describe()}")
        print(f"merged   {added} bar(s) added, {replaced} replaced, into {path}")
    else:
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
