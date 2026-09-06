#!/usr/bin/env python3
"""
nasdaq_json.py — the nasdaq.com historical JSON, converted to the plain CSV.

Trial 3 needs the price the tape printed: the official consolidated close,
unadjusted. Yahoo serves it keyless but answers 429 to anonymous clients more
often than not (2026-09-04, again 2026-09-06). The nasdaq.com site has a JSON
endpoint behind its "Download historical data" button that answers a plain
GET with a browser User-Agent and `Accept: application/json`:

    https://api.nasdaq.com/api/quote/SPY/historical?assetclass=etf
        &fromdate=2020-07-01&limit=9999&todate=2026-09-06

The body is `data.tradesTable.rows`, one object per session with the fields
date, close, volume, open, high, low — newest first, and the prices sometimes
carry dollar signs (the CSV download always does; the JSON did not on
2026-09-06). This tool turns that into the file every other tool reads, with
the SAME semantics as `bars.parse_nasdaq` gives the CSV download:

    oldest first · dollar signs and thousands separators stripped ·
    source "nasdaq" · adjusted False · close_is the official consolidated close

Three outcomes, kept strictly apart as fetch.py keeps them:

    NETWORK   could not reach the host, or it refused          exit 6
    PARSE     reached it; the body is not the table above       exit 2
    OK        N bars written, provenance attached               exit 0

A row it cannot read is never skipped: a row with no close is Unparseable,
because a silently dropped session is an off-by-one that ruins the join in
`intraday.py --close-from`.

USAGE
    python3 nasdaq_json.py --symbol SPY --out bars/SPY-1d-raw.csv
    python3 nasdaq_json.py --symbol SPY --from 2020-07-01 --out bars/SPY-1d-raw.csv
    python3 nasdaq_json.py --json saved.json --symbol SPY --out bars/SPY-1d-raw.csv
        (a body saved earlier — the offline door; the tests use it)

    then:   python3 barqc.py --csv bars/SPY-1d-raw.csv --symbol SPY --source nasdaq
            python3 intraday.py --sessions-from bars/SPY-sessions.csv --rule first30 \\
                --close-from bars/SPY-1d-raw.csv --close-source nasdaq
"""

import argparse
import datetime as dt
import json
import os
import sys

import bars as B
import fetch as F

UTC = dt.timezone.utc

NASDAQ_JSON_URL = ("https://api.nasdaq.com/api/quote/{sym}/historical"
                   "?assetclass={cls}&fromdate={start}&limit=9999&todate={end}")

# The row keys nasdaq.com uses, and the Bar field each one feeds.
_ROW_KEYS = {"close": "close", "open": "open", "high": "high", "low": "low",
             "volume": "volume", "date": "date"}


def parse_nasdaq_json(body, symbol, fetched_at=None, url=None):
    """
    nasdaq.com historical JSON (text or already-decoded dict) → daily Series,
    oldest first, source "nasdaq", adjusted False. Raises B.Unparseable for
    anything that is not the table; never skips a row it cannot read.
    """
    if isinstance(body, (bytes, bytearray)):
        body = body.decode("utf-8", "replace")
    if isinstance(body, str):
        try:
            j = json.loads(body.lstrip("﻿"))
        except json.JSONDecodeError as e:
            raise B.Unparseable(f"nasdaq body is not JSON: {e} — starts {body[:80]!r}")
    else:
        j = body
    if not isinstance(j, dict):
        raise B.Unparseable(f"nasdaq JSON is a {type(j).__name__}, not an object")

    data = j.get("data")
    if not isinstance(data, dict):
        status = j.get("status") or {}
        raise B.Unparseable(
            f"nasdaq JSON has no `data` object (status {status.get('rCode')!r}, "
            f"message {status.get('bCodeMessage') or j.get('message')!r})")
    table = data.get("tradesTable")
    if not isinstance(table, dict) or not isinstance(table.get("rows"), list):
        raise B.Unparseable(
            f"nasdaq JSON `data` has no `tradesTable.rows` list: keys {list(data)[:8]}")
    rows = table["rows"]
    if not rows:
        raise B.Unparseable("nasdaq JSON `tradesTable.rows` is empty — no bars means "
                            "no bars, not zero bars")

    bars = []
    for n, row in enumerate(rows, start=1):
        if not isinstance(row, dict):
            raise B.Unparseable(f"row {n}: not an object — {row!r}")
        missing = [k for k in _ROW_KEYS if k not in row]
        if missing:
            raise B.Unparseable(f"row {n}: missing {', '.join(missing)} — {row}")
        try:
            d = dt.datetime.strptime(str(row["date"]).strip(), "%m/%d/%Y")
            vol = str(row["volume"]).strip().replace(",", "")
            bars.append(B.Bar(
                ts=dt.datetime(d.year, d.month, d.day, tzinfo=UTC),
                open=B._money(str(row["open"])), high=B._money(str(row["high"])),
                low=B._money(str(row["low"])), close=B._money(str(row["close"])),
                volume=float(vol) if vol not in ("", "--", "N/A", "n/a") else 0.0))
        except (ValueError, TypeError) as e:
            raise B.Unparseable(f"row {n}: {e} — {row}")

    newest_first = len(bars) >= 2 and bars[0].ts > bars[-1].ts
    if newest_first:
        bars.reverse()
    prov = {"source": "nasdaq",
            "fetched_at": fetched_at or dt.datetime.now(UTC).isoformat(timespec="seconds"),
            "adjusted": False,
            "close_is": "official consolidated close (nasdaq.com historical JSON)",
            "order": ("export was newest-first; reversed to oldest-first" if newest_first
                      else "export was already oldest-first"),
            "as_of": table.get("asOf"),
            "total_records": data.get("totalRecords")}
    if url:
        prov["url"] = url
    return B.Series(symbol.upper(), "1d", bars, prov)


def fetch_nasdaq_json(symbol, start, end, assetclass="etf"):
    """GET the endpoint with the two headers it wants; NETWORK on anything else."""
    url = NASDAQ_JSON_URL.format(sym=symbol.upper(), cls=assetclass, start=start, end=end)
    body = F._get(url, headers={"User-Agent": F.BROWSER_UA, "Accept": "application/json"})
    return parse_nasdaq_json(body, symbol, url=url)


def load_nasdaq_json(path, symbol):
    """The offline door: a body saved earlier."""
    if not os.path.exists(path):
        raise B.Unparseable(f"no such file: {path}")
    fetched = dt.datetime.fromtimestamp(os.path.getmtime(path), UTC)
    with open(path, encoding="utf-8-sig") as f:
        s = parse_nasdaq_json(f.read(), symbol, fetched.isoformat(timespec="seconds"))
    s.provenance["path"] = os.path.abspath(path)
    return s


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--symbol", required=True)
    ap.add_argument("--out", required=True, help="the plain CSV to write")
    ap.add_argument("--json", metavar="PATH", help="a saved body instead of a fetch")
    ap.add_argument("--from", dest="start", default="2020-07-01",
                    help="fromdate for the fetch (default 2020-07-01, where the "
                         "minute feed starts)")
    ap.add_argument("--to", dest="end", default=dt.date.today().isoformat(),
                    help="todate for the fetch (default today)")
    ap.add_argument("--assetclass", default="etf", choices=["etf", "stocks"],
                    help="nasdaq.com's assetclass for the symbol (default etf)")
    a = ap.parse_args()

    try:
        if a.json:
            s = load_nasdaq_json(a.json, a.symbol)
        else:
            s = fetch_nasdaq_json(a.symbol, a.start, a.end, a.assetclass)
    except F.Unreachable as e:
        print(f"NETWORK  {e}", file=sys.stderr)
        print("Nothing was written. No bars means no bars, not zero bars.", file=sys.stderr)
        sys.exit(6)
    except (B.Unparseable, B.NoProvenance) as e:
        print(f"PARSE    {e}", file=sys.stderr)
        print("Reached the source, could not read bars. Nothing was written.", file=sys.stderr)
        sys.exit(2)

    B.to_csv(s, a.out)
    print(s.describe())
    print(f"provenance: {s.provenance}")
    print(f"wrote {a.out}: {len(s)} bars, oldest first, unadjusted official closes")
    print(f"\nnext:  python3 barqc.py --csv {a.out} --symbol {a.symbol} --source nasdaq")
    print(f"       python3 intraday.py --sessions-from bars/{a.symbol.upper()}-sessions.csv "
          f"--rule first30 --close-from {a.out} --close-source nasdaq")


if __name__ == "__main__":
    main()
