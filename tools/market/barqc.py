#!/usr/bin/env python3
"""
barqc.py — integrity checks on a bar series. The gate before any backtest.

This is the only tool here whose job is to say NO to data.

A backtest on bad bars is worse than no backtest, because it converts an
unchecked series into a result everyone believes was measured. So every check
reports a NUMBER rather than a verdict — "247 bars, 251 sessions, 4 missing"
tells you what to fetch; "fails coverage" does not — and a check that could not
run is reported as UNRUN, never as passed.

THE CHECKS, AND THE FAILURE EACH ONE PREVENTS

    ohlc sanity      high < max(o,c), low > min(o,c), non-positive price
                                                  a corrupt or misparsed row
    order            duplicate or backwards timestamps
                                                  a bar counted twice, or a
                                                  series silently reordered
    sessions         bars vs the exchange calendar (daily only)
                                                  THE KILLER: a short series
                                                  that looks complete
    calendar         bars on days/hours the market was shut
                                                  off-by-one-session, which is
                                                  invisible and ruins everything
    provenance       no source / fetched_at       the SOURCES rule, for prices
    volume           zero or negative             reported: halts are real
    adjustment       split-sized gaps, or the adjusted flag never stated
                                                  reported: an unadjusted split
                                                  reads as a −50% crash
    staleness        age of the last bar          reported: irrelevant to a
                                                  backtest, fatal to a live run
    span             too few bars to mean much    reported

THE PRINCIPLE THIS FILE IS BUILT AROUND
    `rival.py` keeps NETWORK failure, PARSE failure and a genuine count strictly
    apart, because a scraper that cannot read the page returns zero results and
    zero results looks exactly like an empty niche. For market data that stops
    being a nicety: an empty bar series and a flat market are the same array.
    So the session-count check compares against a real calendar, and a series
    that is merely SHORT is blocked as loudly as one that is wrong.

USAGE
    python3 barqc.py --csv bars/AAPL-1d.csv --symbol AAPL
    python3 barqc.py --csv x.csv --symbol AAPL --json
"""

import argparse
import datetime as dt
import json
import os
import sys

import bars as B

HERE = os.path.dirname(os.path.abspath(__file__))

MISSING_ALLOWED = 2         # sessions; special closures happen (Carter, 2025-01-09)
MISSING_ALLOWED_FRAC = 0.01
SPLIT_GAP = 0.40            # a 40% close-to-close move is a split until proven otherwise
MIN_BARS_REPORTED = 60      # below this a backtest is an anecdote
STALE_PERIODS = 3           # last bar older than this many periods → reported

# US regular session, for intraday calendar checks.
SESSION_OPEN = dt.time(9, 30)
SESSION_CLOSE = dt.time(16, 0)


# ---------------------------------------------------------------- NYSE calendar

def _easter(y):
    """Anonymous Gregorian algorithm (Meeus). Good Friday is two days before."""
    a, b, c = y % 19, y // 100, y % 100
    d, e = b // 4, b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = c // 4, c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = ((h + l - 7 * m + 114) % 31) + 1
    return dt.date(y, month, day)


def _nth_weekday(y, m, weekday, n):
    first = dt.date(y, m, 1)
    return first + dt.timedelta(days=(weekday - first.weekday()) % 7 + 7 * (n - 1))


def _last_weekday(y, m, weekday):
    nxt = dt.date(y + (m == 12), m % 12 + 1, 1)
    last = nxt - dt.timedelta(days=1)
    return last - dt.timedelta(days=(last.weekday() - weekday) % 7)


def _observed(d):
    if d.weekday() == 5:
        return d - dt.timedelta(days=1)
    if d.weekday() == 6:
        return d + dt.timedelta(days=1)
    return d


def nyse_holidays(y):
    """
    Scheduled NYSE closures for one year. Special closures — days of mourning,
    weather — are not knowable in advance and show up as MISSING sessions with
    their dates listed, which is the honest outcome.
    """
    h = set()
    ny = dt.date(y, 1, 1)
    # NYSE rule: New Year's on a Saturday is NOT observed on the Friday.
    if ny.weekday() != 5:
        h.add(_observed(ny))
    h.add(_nth_weekday(y, 1, 0, 3))                   # MLK
    h.add(_nth_weekday(y, 2, 0, 3))                   # Presidents
    h.add(_easter(y) - dt.timedelta(days=2))          # Good Friday
    h.add(_last_weekday(y, 5, 0))                     # Memorial
    if y >= 2022:
        h.add(_observed(dt.date(y, 6, 19)))           # Juneteenth
    h.add(_observed(dt.date(y, 7, 4)))                # Independence
    h.add(_nth_weekday(y, 9, 0, 1))                   # Labor
    h.add(_nth_weekday(y, 11, 3, 4))                  # Thanksgiving
    h.add(_observed(dt.date(y, 12, 25)))              # Christmas
    return h


def sessions_between(start, end):
    """Trading dates in [start, end], inclusive."""
    hol = set()
    for y in range(start.year, end.year + 1):
        hol |= nyse_holidays(y)
    out, d = [], start
    while d <= end:
        if d.weekday() < 5 and d not in hol:
            out.append(d)
        d += dt.timedelta(days=1)
    return out


def is_session_day(d):
    return d.weekday() < 5 and d not in nyse_holidays(d.year)


# ---------------------------------------------------------------- checks

def check_ohlc(s):
    bad = []
    for i, b in enumerate(s.bars):
        if (b.high < max(b.open, b.close) or b.low > min(b.open, b.close)
                or b.low <= 0 or b.high <= 0 or b.open <= 0 or b.close <= 0
                or b.high < b.low):
            bad.append(i)
    note = ""
    if bad:
        b = s.bars[bad[0]]
        note = (f"first at row {bad[0]} ({b.ts:%Y-%m-%d}): "
                f"O {b.open:g} H {b.high:g} L {b.low:g} C {b.close:g}")
    return {"ok": not bad, "value": f"{len(bad)} bad row(s)", "want": "0",
            "note": note}


def check_order(s):
    dupes = backwards = 0
    for a, b in zip(s.bars, s.bars[1:]):
        if b.ts == a.ts:
            dupes += 1
        elif b.ts < a.ts:
            backwards += 1
    ok = dupes == 0 and backwards == 0
    return {"ok": ok, "value": f"{dupes} duplicate, {backwards} backwards",
            "want": "0, 0",
            "note": "" if ok else "a duplicate is a bar counted twice; "
                                  "backwards means the source reordered it"}


FULL_SESSION_BARS = {"1m": 390, "5m": 78, "15m": 26, "1h": 7}
SHORT_SESSION_FRAC = 0.8    # under this share of a full session's bars → counted as short


def check_sessions(s):
    """
    Bars against the exchange calendar.

    Daily: one bar per session, so bars vs sessions is the whole check.
    Intraday: the DAYS present vs the calendar, plus how many of those days
    are short — half-days (~205 of 390 minute bars) are real, a session with
    47 bars is a hole. Both are reported by count; the intraday tools skip
    short sessions themselves and say so.
    """
    if len(s) < 2:
        return {"ok": None, "value": "unrun", "want": "0 missing",
                "note": f"{len(s)} bar(s) — nothing to count between"}
    if s.timeframe == "1d":
        have = {b.ts.date() for b in s.bars}
        first, last = s.first.ts.date(), s.last.ts.date()
        per_day = None
    else:
        try:
            from zoneinfo import ZoneInfo
            ny = ZoneInfo("America/New_York")
        except Exception as e:
            return {"ok": None, "value": "unrun", "want": "0 missing",
                    "note": f"no timezone database ({type(e).__name__}); cannot "
                            f"assign intraday bars to session days"}
        per_day = {}
        for b in s.bars:
            d = b.ts.astimezone(ny).date()
            per_day[d] = per_day.get(d, 0) + 1
        have = set(per_day)
        first, last = min(have), max(have)
    expected = sessions_between(first, last)
    missing = [d for d in expected if d not in have]
    allowed = max(MISSING_ALLOWED, int(MISSING_ALLOWED_FRAC * len(expected)))
    ok = len(missing) <= allowed
    notes = []
    if missing:
        notes.append("missing " + ", ".join(d.isoformat() for d in missing[:5])
                     + (" …" if len(missing) > 5 else "")
                     + f"; up to {allowed} tolerated for special closures")
    if per_day is not None:
        full = FULL_SESSION_BARS.get(s.timeframe)
        if full:
            # shortest first: a hole shows before the half-days
            short = sorted(((d, n) for d, n in per_day.items() if n < SHORT_SESSION_FRAC * full),
                           key=lambda x: (x[1], x[0]))
            if short:
                notes.append(f"{len(short)} short session(s) (< {SHORT_SESSION_FRAC:.0%} of "
                             f"{full} bars), shortest first: "
                             + ", ".join(f"{d.isoformat()} ({n})" for d, n in short[:5])
                             + (" …" if len(short) > 5 else "")
                             + " — half-days are real; a day with a handful of bars is a hole")
        value = (f"{len(have)} session days, {len(expected)} sessions, "
                 f"{len(missing)} missing")
    else:
        value = f"{len(s)} bars, {len(expected)} sessions, {len(missing)} missing"
    return {"ok": ok, "value": value, "want": f"<= {allowed} missing",
            "note": "; ".join(notes)}


def check_calendar(s):
    if s.timeframe == "1d":
        off = [b for b in s.bars if not is_session_day(b.ts.date())]
        note = ""
        if off:
            note = ("first: " + off[0].ts.strftime("%Y-%m-%d %a")
                    + " — a bar on a closed day means the dates are shifted "
                      "or the source is not this exchange")
        return {"ok": not off, "value": f"{len(off)} off-calendar bar(s)",
                "want": "0", "note": note}
    try:
        from zoneinfo import ZoneInfo
        ny = ZoneInfo("America/New_York")
    except Exception as e:
        return {"ok": None, "value": "unrun", "want": "0 outside session",
                "note": f"no timezone database ({type(e).__name__}); "
                        f"cannot place intraday bars in the New York session"}
    off = []
    for b in s.bars:
        local = b.ts.astimezone(ny)
        t = local.time()
        if (not is_session_day(local.date()) or t < SESSION_OPEN
                or t >= SESSION_CLOSE):
            off.append(b)
    note = ""
    if off:
        note = (f"first: {off[0].ts.astimezone(ny):%Y-%m-%d %H:%M %Z} — "
                f"outside 09:30–16:00 New York; extended hours or wrong zone")
    return {"ok": not off, "value": f"{len(off)} outside session", "want": "0",
            "note": note}


def check_provenance(s):
    p = s.provenance or {}
    missing = [k for k in ("source", "fetched_at") if not str(p.get(k, "")).strip()]
    return {"ok": not missing, "value": f"{len(missing)} missing", "want": "0",
            "note": ("no " + " / ".join(missing)) if missing else
                    f"{p.get('source')} @ {p.get('fetched_at')}"}


def check_volume(s):
    zero = sum(1 for b in s.bars if b.volume <= 0)
    return {"ok": True, "value": f"{zero} zero/negative", "want": "0",
            "reported_only": True,
            "note": "" if not zero else
                    "halts and thin names produce real zero-volume bars; look, "
                    "do not assume"}


def check_adjustment(s):
    gaps = []
    for a, b in zip(s.bars, s.bars[1:]):
        if a.close > 0 and abs(b.close / a.close - 1) >= SPLIT_GAP:
            gaps.append((b.ts, b.close / a.close - 1))
    adj = s.provenance.get("adjusted") if s.provenance else None
    stated = "adjusted" if adj is True else "unadjusted" if adj is False \
        else "adjustment NOT stated"
    note = stated
    if gaps:
        ts, g = gaps[0]
        note += f"; first split-sized gap {ts:%Y-%m-%d} ({g:+.0%})"
        if adj is not True:
            note += " — if that is a split, every return across it is wrong"
    return {"ok": True, "value": f"{len(gaps)} split-sized gap(s)", "want": "0",
            "reported_only": True, "note": note}


def check_staleness(s, now=None):
    if not s.bars:
        return {"ok": None, "value": "unrun", "want": "", "note": "no bars"}
    now = now or dt.datetime.now(B.UTC)
    age = now - s.last.ts
    periods = age / s.period
    note = ""
    if periods > STALE_PERIODS:
        note = ("fine for a backtest; a live decision on this would be trading "
                "the past")
    return {"ok": True, "value": f"last bar {periods:.1f} period(s) old",
            "want": f"<= {STALE_PERIODS} for live", "reported_only": True,
            "note": note}


def check_span(s):
    n = len(s)
    return {"ok": True, "value": f"{n} bars", "want": f">= {MIN_BARS_REPORTED}",
            "reported_only": True,
            "note": "" if n >= MIN_BARS_REPORTED else
                    "a backtest on this few bars is an anecdote, not evidence"}


def inspect(series, now=None):
    checks = {
        "ohlc sanity": check_ohlc(series),
        "order": check_order(series),
        "sessions": check_sessions(series),
        "calendar": check_calendar(series),
        "provenance": check_provenance(series),
        "volume": check_volume(series),
        "adjustment": check_adjustment(series),
        "staleness": check_staleness(series, now),
        "span": check_span(series),
    }
    failed = [k for k, v in checks.items() if v["ok"] is False]
    unrun = [k for k, v in checks.items() if v["ok"] is None]
    verdict = "blocked" if failed else ("pass" if not unrun else "pass-with-unrun")
    return {"verdict": verdict, "checks": checks, "failed": failed,
            "unrun": unrun, "series": series.describe()}


def render(result):
    L = [f"\n{'='*72}", f"BAR INSPECTION — {result.get('series', '')}", "=" * 72]
    if result.get("error"):
        L.append(f"\nUNRUN: {result['error']}")
        return "\n".join(L)
    L.append(f"\n{'check':<16}{'value':<40}{'want':<16}")
    L.append("-" * 72)
    for name, c in result["checks"].items():
        mark = "unrun" if c["ok"] is None else ("ok   " if c["ok"] else "FAIL ")
        tail = "  (reported, not blocking)" if c.get("reported_only") else ""
        L.append(f"{mark} {name:<15}{str(c['value']):<40}{str(c['want']):<16}{tail}")
        if c.get("note"):
            L.append(f"       └─ {c['note']}")
    L.append("-" * 72)
    L.append(f"VERDICT: {result['verdict'].upper()}")
    if result.get("failed"):
        L.append(f"blocked by: {', '.join(result['failed'])}")
    if result.get("unrun"):
        L.append(f"could not run: {', '.join(result['unrun'])} "
                 f"— these are NOT passes")
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--csv", required=True)
    ap.add_argument("--symbol", required=True)
    ap.add_argument("--timeframe", default="1d", choices=sorted(B.TIMEFRAMES))
    ap.add_argument("--source")
    ap.add_argument("--adjusted", choices=["yes", "no"])
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    try:
        s = B.load_csv(a.csv, a.symbol, a.timeframe, a.source,
                       {"yes": True, "no": False}.get(a.adjusted))
    except (B.Unparseable, B.NoProvenance) as e:
        result = {"verdict": "unrun", "checks": {}, "error": str(e)}
        print(json.dumps(result, indent=2) if a.json else render(result))
        sys.exit(2)

    result = inspect(s)
    if a.json:
        print(json.dumps(result, indent=2, default=str))
    else:
        print(render(result))
        if result["verdict"] != "blocked":
            print(f"\nnext:  python3 run.py --mode backtest --strategy sma_cross:10,30 "
                  f"--csv {a.csv} --symbol {a.symbol}")
    sys.exit(2 if result["verdict"] == "blocked" else 0)


if __name__ == "__main__":
    main()
