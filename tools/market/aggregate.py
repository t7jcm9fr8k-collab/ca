#!/usr/bin/env python3
"""
aggregate.py — minute bars → daily bars, one per New York session.

WHY
    The free minute feed reaches back to 2020-07; the daily fetch Daniel ran
    started in 2024. Everything on daily bars — the trend filter, the null
    test, combine — was therefore scored on one regime with two bought dips,
    and the 2022 bear, the one stretch that would have tested buy-the-dip
    rules and a trend filter, was sitting unused in bars/SPY-1m.csv. A
    reviewer pointed this out. This file turns those minute bars into ~1,500
    daily sessions with nothing fetched.

WHAT A DAY IS
    Regular session only, by New York date: open = first bar's open, high =
    max, low = min, close = last bar's close, volume = sum. Half-days are real
    sessions and are kept. The bar count per session is recorded so a hole
    (a day with 47 bars) can be seen and, with --min-bars, dropped.

WHAT THESE CLOSES ARE NOT
    The last IEX print before 16:00 — not the official closing auction. For a
    200-day average that is a rounding error; for anything that trades the
    close it is a few basis points of noise. The provenance says so.

USAGE
    python3 aggregate.py --csv bars/SPY-1m.csv --symbol SPY --source alpaca
    python3 barqc.py --csv bars/SPY-1d-agg.csv --symbol SPY --source alpaca-1m-aggregated --adjusted yes
"""

import argparse
import datetime as dt
import os
import sys

import bars as B

HERE = os.path.dirname(os.path.abspath(__file__))
SESSION_OPEN, SESSION_CLOSE = dt.time(9, 30), dt.time(16, 0)


def aggregate(series, min_bars=1):
    """Series of intraday bars → (daily Series, {date: bar count}, dropped)."""
    if series.timeframe == "1d":
        raise ValueError("already daily")
    try:
        from zoneinfo import ZoneInfo
        ny = ZoneInfo("America/New_York")
    except Exception as e:
        raise RuntimeError(f"no timezone database ({type(e).__name__}); cannot "
                           f"assign bars to New York sessions")
    days = {}
    for b in sorted(series.bars, key=lambda x: x.ts):
        loc = b.ts.astimezone(ny)
        if not (SESSION_OPEN <= loc.time() < SESSION_CLOSE):
            continue
        d = loc.date()
        acc = days.get(d)
        if acc is None:
            days[d] = {"o": b.open, "h": b.high, "l": b.low, "c": b.close, "v": b.volume, "n": 1}
        else:
            acc["h"] = max(acc["h"], b.high)
            acc["l"] = min(acc["l"], b.low)
            acc["c"] = b.close
            acc["v"] += b.volume
            acc["n"] += 1
    out, counts, dropped = [], {}, 0
    for d in sorted(days):
        a = days[d]
        counts[d.isoformat()] = a["n"]
        if a["n"] < min_bars:
            dropped += 1
            continue
        out.append(B.Bar(dt.datetime(d.year, d.month, d.day, tzinfo=B.UTC),
                         a["o"], a["h"], a["l"], a["c"], a["v"]))
    prov = dict(series.provenance)
    prov.update({"source": f"{series.provenance.get('source', 'intraday')}-{series.timeframe}-aggregated",
                 "fetched_at": dt.datetime.now(B.UTC).isoformat(timespec="seconds"),
                 "aggregated_from": series.timeframe,
                 "close_is": "last regular-session print, not the official closing auction",
                 "sessions_dropped_short": dropped, "min_bars": min_bars})
    return B.Series(series.symbol, "1d", out, prov), counts, dropped


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--csv", required=True, help="the intraday CSV")
    ap.add_argument("--symbol", required=True)
    ap.add_argument("--timeframe", default="1m", choices=[t for t in B.TIMEFRAMES if t != "1d"])
    ap.add_argument("--source", help="where the minute bars came from; recorded")
    ap.add_argument("--adjusted", choices=["yes", "no"])
    ap.add_argument("--min-bars", type=int, default=1,
                    help="drop sessions with fewer bars than this (half-days are ~205 of 390)")
    ap.add_argument("--out", help="default bars/<SYMBOL>-1d-agg.csv")
    a = ap.parse_args()
    try:
        s = B.load_csv(a.csv, a.symbol, a.timeframe, a.source,
                       {"yes": True, "no": False}.get(a.adjusted))
    except (B.Unparseable, B.NoProvenance) as e:
        sys.exit(f"REFUSED: {e}")
    try:
        daily, counts, dropped = aggregate(s, a.min_bars)
    except (ValueError, RuntimeError) as e:
        sys.exit(f"REFUSED: {e}")
    path = a.out or os.path.join(HERE, "bars", f"{a.symbol.upper()}-1d-agg.csv")
    B.to_csv(daily, path)
    short = sorted((d, n) for d, n in counts.items() if n < 312)
    print(f"OK       {daily.describe()}")
    print(f"         from {len(s)} {a.timeframe} bars; {len(short)} short session(s)"
          + (f", {dropped} dropped under --min-bars {a.min_bars}" if dropped else "")
          + (": " + ", ".join(f"{d} ({n})" for d, n in short[:6]) + (" …" if len(short) > 6 else "") if short else ""))
    print(f"         closes are the last regular-session print, not the official auction")
    print(f"wrote    {path}")
    print(f"\nnext:  python3 barqc.py --csv {path} --symbol {a.symbol} --source "
          f"{daily.provenance['source']}"
          + (" --adjusted yes" if daily.provenance.get("adjusted") is True else ""))


if __name__ == "__main__":
    main()
