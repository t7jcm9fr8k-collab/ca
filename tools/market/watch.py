#!/usr/bin/env python3
"""
watch.py — the morning readout. The chart as numbers, for a list of symbols,
with no prediction claimed.

WHAT IT SHOWS, PER SYMBOL
    close, the 200-day trend state, EMA20, RSI14, ATR14, the last bar's
    rejection geometry, the nearest swing level and how far, the volume
    profile's point of control, and how stale the bars are. Each is a
    description of what the bars did. EVIDENCE.md says which of them, if
    any, is more than that — and for most of these the answer is "none".

WHAT IT REFUSES
    A symbol whose bars fail barqc gets its verdict printed and no readings;
    a reading off broken bars would be a number with nothing behind it. A
    symbol with no bars file says so and points at fetch.py.

USAGE
    python3 watch.py --symbols SPY AAPL MSFT
    python3 watch.py --watchlist watchlist.txt        # one symbol per line, # comments
"""

import argparse
import os
import sys

import bars as B
import barqc
import features as F
import replay

HERE = os.path.dirname(os.path.abspath(__file__))


def readout(symbol, timeframe="1d", root=None):
    path = B.bars_path(symbol, timeframe, root)
    if not os.path.exists(path):
        return {"symbol": symbol, "status": "no bars",
                "note": f"python3 fetch.py --source stooq --symbol {symbol}"}
    try:
        s = B.load_csv(path, symbol, timeframe)
    except (B.Unparseable, B.NoProvenance) as e:
        return {"symbol": symbol, "status": "unreadable", "note": str(e)}
    qc = barqc.inspect(s)
    if qc["verdict"] == "blocked":
        return {"symbol": symbol, "status": "blocked",
                "note": ", ".join(qc["failed"])}
    cur = replay.Cursor(s, len(s))
    w = cur[-260:]
    d = F.describe(w)
    sma200 = F.sma(w, 200)
    last = s.last
    return {"symbol": symbol, "status": "ok", "date": f"{last.ts:%Y-%m-%d}",
            "close": last.close,
            "trend": (None if sma200 is None else "above" if last.close > sma200 else "below"),
            "sma200": sma200, "ema20": d.get("ema"), "rsi14": F.rsi(w, 14),
            "atr14": d.get("atr"), "rejection": d.get("rejection") or "-",
            "level": d.get("nearest_level"), "level_dist": d.get("distance_to_level"),
            "poc": d.get("poc"),
            "stale": barqc.check_staleness(s)["value"],
            "unrun": qc["unrun"]}


def _f(x, fmt=".4g"):
    return format(x, fmt) if isinstance(x, (int, float)) else "-"


def render(rows):
    L = [f"{'symbol':<7}{'date':<11}{'close':>9}{'trend':>7}{'ema20':>9}{'rsi':>6}"
         f"{'atr':>7}{'reject':>7}{'level':>9}{'dist':>7}{'poc':>9}  stale"]
    L.append("-" * 100)
    for r in rows:
        if r["status"] != "ok":
            L.append(f"{r['symbol']:<7}{r['status']:<11}{r['note']}")
            continue
        L.append(f"{r['symbol']:<7}{r['date']:<11}{_f(r['close']):>9}{(r['trend'] or '-'):>7}"
                 f"{_f(r['ema20']):>9}{_f(r['rsi14'], '.0f'):>6}{_f(r['atr14'], '.3g'):>7}"
                 f"{r['rejection']:>7}{_f(r['level']):>9}"
                 f"{(format(r['level_dist'], '+.1%') if isinstance(r['level_dist'], float) else '-'):>7}"
                 f"{_f(r['poc']):>9}  {r['stale']}")
    L.append("-" * 100)
    L.append("trend = close vs 200-day SMA. Every column describes the bars; none predicts. "
             "See EVIDENCE.md.")
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--symbols", nargs="*", default=[])
    ap.add_argument("--watchlist", help="file, one symbol per line")
    ap.add_argument("--timeframe", default="1d", choices=sorted(B.TIMEFRAMES))
    a = ap.parse_args()
    syms = list(a.symbols)
    if a.watchlist:
        for line in open(a.watchlist):
            t = line.split("#")[0].strip()
            if t:
                syms.append(t)
    if not syms:
        ap.error("give --symbols or --watchlist")
    rows = [readout(s.upper(), a.timeframe) for s in syms]
    print(render(rows))
    missing = [r["symbol"] for r in rows if r["status"] == "no bars"]
    if missing:
        print(f"\nno bars for {', '.join(missing)} — on the Mac: "
              f"python3 fetch.py --source stooq --symbol {missing[0]}")


if __name__ == "__main__":
    main()
