#!/usr/bin/env python3
"""
test_tools.py — checks for the market pipeline. Run: python3 test_tools.py

These pin the parts that CAN be checked numerically: that a strategy cannot see
the future, that a decision fills one bar later, that the session count uses
the real calendar, that a fetch which failed never becomes an empty series, and
that the gate refuses what it should refuse and records what it should record.

No test framework — stdlib only, same posture as the tools. Everything runs
offline: the one network call is to a port on localhost that nothing listens
on, to prove that unreachable is reported as unreachable.
"""

import contextlib
import datetime as dt
import io
import json
import os
import random
import shutil
import subprocess
import sys
import tempfile

import bars as B
import barqc
import broker
import fetch
import ledger
import replay
import run
import strategies

HERE = os.path.dirname(os.path.abspath(__file__))
FAILURES = []


def check(name, cond, detail=""):
    if cond:
        print(f"  ok   {name}")
    else:
        print(f"  FAIL {name} {detail}")
        FAILURES.append(name)


def _raises(exc, fn, *args, **kw):
    try:
        fn(*args, **kw)
    except exc:
        return True
    except Exception:
        return False
    return False


def _d(y, m, d):
    return dt.datetime(y, m, d, tzinfo=B.UTC)


def _bar(ts, o=100, h=None, l=None, c=None, v=1000):
    c = o if c is None else c
    h = max(o, c) + 1 if h is None else h
    l = min(o, c) - 1 if l is None else l
    return B.Bar(ts, float(o), float(h), float(l), float(c), float(v))


PROV = {"source": "test", "fetched_at": "2026-09-02T00:00:00+00:00", "adjusted": True}


def _series(bars_, symbol="T", tf="1d", prov=None):
    return B.Series(symbol, tf, bars_, dict(PROV if prov is None else prov))


def _daily(n, start=dt.date(2026, 1, 5), closes=None, base=100.0):
    """n consecutive SESSIONS from start, with a gentle drift unless closes given."""
    days = barqc.sessions_between(start, start + dt.timedelta(days=n * 2 + 20))[:n]
    out, p = [], base
    for i, d in enumerate(days):
        c = closes[i] if closes else p * 1.002
        o = p
        out.append(_bar(_d(d.year, d.month, d.day), o, max(o, c) + 0.5, min(o, c) - 0.5, c))
        p = c
    return out


# ---------------------------------------------------------------- bars

print("bars — the type and the one rule")

check("a naive timestamp is refused",
      _raises(ValueError, B.Bar, dt.datetime(2026, 1, 5), 1, 2, 0.5, 1.5, 1))
check("a series without a source is refused",
      _raises(B.NoProvenance, B.Series, "T", "1d", [], {"fetched_at": "x"}))
check("a series without fetched_at is refused",
      _raises(B.NoProvenance, B.Series, "T", "1d", [], {"source": "x"}))
check("an unknown timeframe is refused",
      _raises(ValueError, B.Series, "T", "2h", [], PROV))
check("a bar is immutable",
      _raises(Exception, setattr, _bar(_d(2026, 1, 5)), "close", 1.0))

b = B.Bar(_d(2026, 1, 5), 10, 14, 8, 12, 1)
check("candle geometry is computed, not drawn",
      b.body == 2 and b.upper_wick == 2 and b.lower_wick == 2 and b.range == 6 and b.bullish)

STOOQ = "Date,Open,High,Low,Close,Volume\n2026-01-05,1,2,0.5,1.5,100\n2026-01-06,1.5,2,1,1.8,120\n"
s = B.parse_csv(STOOQ, "T", "1d", "stooq")
check("stooq header parses", len(s) == 2 and s[0].open == 1.0 and s[1].close == 1.8)
check("daily bars are pinned to 00:00Z", s[0].ts == _d(2026, 1, 5))
check("a missing column is Unparseable, not a guess",
      _raises(B.Unparseable, B.parse_csv, "Date,Open,High,Close,Volume\n2026-01-05,1,2,1.5,1\n", "T", "1d", "x"))
check("a bad row is Unparseable, not skipped",
      _raises(B.Unparseable, B.parse_csv, STOOQ + "2026-01-07,oops,2,1,1,1\n", "T", "1d", "x"))
check("an empty file is Unparseable",
      _raises(B.Unparseable, B.parse_csv, "", "T", "1d", "x"))
check("a header with no rows is a true empty series",
      len(B.parse_csv("Date,Open,High,Low,Close,Volume\n", "T", "1d", "x")) == 0)
check("alpaca single-letter columns parse",
      len(B.parse_csv("t,o,h,l,c,v\n2026-01-05,1,2,0.5,1.5,1\n", "T", "1d", "x")) == 1)
check("a naive intraday timestamp is refused",
      _raises(B.Unparseable, B.parse_csv, "t,o,h,l,c,v\n2026-01-05T09:30:00,1,2,0.5,1.5,1\n", "T", "1h", "x"))
si = B.parse_csv("t,o,h,l,c,v\n2026-01-05T14:30:00Z,1,2,0.5,1.5,1\n", "T", "1h", "x")
check("a zoned intraday timestamp is kept as UTC",
      si[0].ts == dt.datetime(2026, 1, 5, 14, 30, tzinfo=B.UTC))
check("adj close is NOT taken as close",
      B.parse_csv("Date,Open,High,Low,Close,Adj Close,Volume\n2026-01-05,1,2,0.5,1.5,9,1\n",
                  "T", "1d", "x")[0].close == 1.5)

_tmp = tempfile.mkdtemp(prefix="market-")
_p = os.path.join(_tmp, "rt.csv")
B.to_csv(s, _p)
rt = B.load_csv(_p, "T", "1d", "stooq")
check("csv round-trips", [x.close for x in rt] == [x.close for x in s]
      and rt.provenance["source"] == "stooq" and rt.provenance["fetched_at"])
check("load_csv records the path", rt.provenance.get("path", "").endswith("rt.csv"))
check("a missing file is Unparseable",
      _raises(B.Unparseable, B.load_csv, "/nonexistent.csv", "T"))

# ---------------------------------------------------------------- calendar

print("\ncalendar — the real one")

H26 = barqc.nyse_holidays(2026)
for name, d in [("New Year", dt.date(2026, 1, 1)), ("MLK", dt.date(2026, 1, 19)),
                ("Presidents", dt.date(2026, 2, 16)), ("Good Friday", dt.date(2026, 4, 3)),
                ("Memorial", dt.date(2026, 5, 25)), ("Juneteenth", dt.date(2026, 6, 19)),
                ("Independence observed Fri", dt.date(2026, 7, 3)),
                ("Labor", dt.date(2026, 9, 7)), ("Thanksgiving", dt.date(2026, 11, 26)),
                ("Christmas", dt.date(2026, 12, 25))]:
    check(f"2026 {name} is a holiday", d in H26, d.isoformat())
check("2026 has exactly ten scheduled closures", len(H26) == 10, str(len(H26)))
check("New Year's on a Saturday is NOT observed on the Friday (2022)",
      dt.date(2021, 12, 31) not in barqc.nyse_holidays(2021)
      and dt.date(2022, 1, 1) not in barqc.nyse_holidays(2022))
check("Easter 2026 is April 5", barqc._easter(2026) == dt.date(2026, 4, 5))
check("Easter 2025 is April 20", barqc._easter(2025) == dt.date(2025, 4, 20))
check("sessions skip weekends and holidays",
      [d.day for d in barqc.sessions_between(dt.date(2026, 1, 1), dt.date(2026, 1, 9))]
      == [2, 5, 6, 7, 8, 9])
check("Juneteenth is not a holiday before 2022",
      dt.date(2021, 6, 18) not in barqc.nyse_holidays(2021))

# ---------------------------------------------------------------- barqc

print("\nbarqc — checks")

good = _series(_daily(70))
r = barqc.inspect(good)
check("a clean daily series passes", r["verdict"] == "pass", r["verdict"] + " " + str(r["failed"]))

bad = _daily(10)
bad[3] = B.Bar(bad[3].ts, 100, 99, 101, 100, 1)        # high < low
check("high < low fails ohlc", barqc.check_ohlc(_series(bad))["ok"] is False)
bad = _daily(10)
bad[3] = B.Bar(bad[3].ts, 100, 101, 99, 105, 1)        # close above high
check("close outside [low, high] fails ohlc", barqc.check_ohlc(_series(bad))["ok"] is False)
bad = _daily(10)
bad[3] = B.Bar(bad[3].ts, 100, 101, -1, 100, 1)
check("a non-positive price fails ohlc", barqc.check_ohlc(_series(bad))["ok"] is False)

dup = _daily(10)
dup[5] = B.Bar(dup[4].ts, 100, 101, 99, 100, 1)
check("a duplicate timestamp fails order",
      barqc.check_order(_series(dup))["value"].startswith("1 duplicate"))
back = _daily(10)
back[5], back[6] = back[6], back[5]
check("a backwards timestamp fails order",
      "1 backwards" in barqc.check_order(_series(back))["value"])

full = _daily(40)
two_gone = full[:10] + full[12:]
three_gone = full[:10] + full[13:]
check("two missing sessions are tolerated (special closures happen)",
      barqc.check_sessions(_series(two_gone))["ok"] is True)
c3 = barqc.check_sessions(_series(three_gone))
check("three missing sessions BLOCK", c3["ok"] is False, c3["value"])
check("the missing dates are named", full[10].ts.strftime("%Y-%m-%d") in c3["note"])
check("session count reads bars vs sessions", "40 bars" not in c3["value"] and "37 bars" in c3["value"])
check("a series that is merely SHORT is caught",
      barqc.check_sessions(_series(full[:5] + full[30:]))["ok"] is False)
check("one bar is UNRUN for sessions", barqc.check_sessions(_series(_daily(1)))["ok"] is None)


def _mins(day, n, start_h=9, start_m=30):
    """n one-minute bars on `day` from 09:30 New York, as UTC bars."""
    from zoneinfo import ZoneInfo
    ny = ZoneInfo("America/New_York")
    t0 = dt.datetime(day.year, day.month, day.day, start_h, start_m, tzinfo=ny)
    return [B.Bar((t0 + dt.timedelta(minutes=k)).astimezone(B.UTC), 100, 101, 99, 100, 10)
            for k in range(n)]


_days = barqc.sessions_between(dt.date(2026, 1, 5), dt.date(2026, 1, 20))[:5]
_full = [b for d in _days for b in _mins(d, 390)]
_cs = barqc.check_sessions(_series(_full, tf="1m"))
check("intraday sessions are counted by New York day", _cs["ok"] is True and _cs["value"].startswith("5 session days, 5 sessions, 0 missing"))
_gap = [b for d in (_days[0], _days[1], _days[3], _days[4]) for b in _mins(d, 390)]
_cg = barqc.check_sessions(_series(_gap, tf="1m"))
check("a missing intraday day is named and tolerated", _cg["ok"] is True and "1 missing" in _cg["value"] and _days[2].isoformat() in _cg["note"])
_half = [b for d in _days[:4] for b in _mins(d, 390)] + _mins(_days[4], 210)
_ch = barqc.check_sessions(_series(_half, tf="1m"))
check("a half-day is reported as short, not missing", _ch["ok"] is True and "1 short session" in _ch["note"] and "0 missing" in _ch["value"])
_hole = [b for d in _days[:4] for b in _mins(d, 390)] + _mins(_days[4], 47)
check("a 47-bar day is reported as short too", "1 short session" in barqc.check_sessions(_series(_hole, tf="1m"))["note"])
_mixed = [b for d in _days[:3] for b in _mins(d, 390)] + _mins(_days[3], 205) + _mins(_days[4], 47)
_note = barqc.check_sessions(_series(_mixed, tf="1m"))["note"]
check("short sessions are listed shortest first, so the hole comes before the half-day",
      _note.index(f"{_days[4].isoformat()} (47)") < _note.index(f"{_days[3].isoformat()} (205)"))

wk = _daily(5) + [_bar(_d(2026, 1, 10), 100)]          # a Saturday
check("a weekend bar fails calendar", barqc.check_calendar(_series(wk))["ok"] is False)
hol = _daily(5) + [_bar(_d(2026, 1, 19), 100)]         # MLK day
check("a holiday bar fails calendar", barqc.check_calendar(_series(hol))["ok"] is False)
intra_ok = [B.Bar(dt.datetime(2026, 1, 5, 15, 30, tzinfo=B.UTC), 1, 2, 0.5, 1.5, 1)]   # 10:30 NY
intra_off = [B.Bar(dt.datetime(2026, 1, 5, 13, 0, tzinfo=B.UTC), 1, 2, 0.5, 1.5, 1)]   # 08:00 NY
ci = barqc.check_calendar(_series(intra_ok, tf="1h"))
if ci["ok"] is None:
    check("intraday calendar is UNRUN without tzdata (honest)", True)
else:
    check("an in-session intraday bar passes calendar", ci["ok"] is True, ci["value"])
    check("a pre-market intraday bar fails calendar",
          barqc.check_calendar(_series(intra_off, tf="1h"))["ok"] is False)

zv = _daily(5)
zv[2] = B.Bar(zv[2].ts, 100, 101, 99, 100, 0)
cv = barqc.check_volume(_series(zv))
check("zero volume is reported, never blocking", cv["ok"] is True and cv["reported_only"]
      and cv["value"].startswith("1 zero"))

sp = _daily(6, closes=[100, 101, 102, 51, 52, 53])
ca = barqc.check_adjustment(_series(sp))
check("a split-sized gap is reported with its date",
      ca["reported_only"] and "1 split-sized" in ca["value"] and sp[3].ts.strftime("%Y-%m-%d") in ca["note"])
check("adjustment not stated is said aloud",
      "NOT stated" in barqc.check_adjustment(_series(_daily(3), prov={"source": "x", "fetched_at": "y"}))["note"])
check("an adjusted series says adjusted", barqc.check_adjustment(good)["note"].startswith("adjusted"))

st = barqc.check_staleness(good, now=good.last.ts + dt.timedelta(days=30))
check("staleness is reported, never blocking", st["ok"] is True and st["reported_only"]
      and "trading the past" in st["note"])
check("a fresh series has no staleness note",
      barqc.check_staleness(good, now=good.last.ts + dt.timedelta(days=1))["note"] == "")
check("a short span is reported, never blocking",
      barqc.check_span(_series(_daily(10)))["reported_only"]
      and "anecdote" in barqc.check_span(_series(_daily(10)))["note"])
check("provenance check passes a traced series", barqc.check_provenance(good)["ok"] is True)
check("an unrun check never yields a bare pass verdict",
      barqc.inspect(_series(_daily(1)))["verdict"] == "pass-with-unrun")
check("a failed check yields blocked",
      barqc.inspect(_series(three_gone))["verdict"] == "blocked")

# ---------------------------------------------------------------- replay

print("\nreplay — no look-ahead, by shape")

s70 = _series(_daily(70))
c = replay.Cursor(s70, 10)
check("cursor length is the closed count", len(c) == 10)
check("cursor[-1] is the last CLOSED bar", c[-1] is s70.bars[9])
check("reaching one past the window raises LookAhead", _raises(replay.LookAhead, lambda: c[10]))
check("reaching far past the window raises LookAhead", _raises(replay.LookAhead, lambda: c[69]))
check("a negative index before the start raises LookAhead", _raises(replay.LookAhead, lambda: c[-11]))
check("a slice clamps to the window, never leaks", len(c[-30:]) == 10 and c[-30:][-1] is s70.bars[9])
check("closes(n) returns at most n visible closes", c.closes(3) == [x.close for x in s70.bars[7:10]])
check("iterating a cursor stops at the window", sum(1 for _ in c) == 10)
check("an empty cursor's .last raises", _raises(replay.LookAhead, lambda: replay.Cursor(s70, 0).last))
check("a cursor past the series is refused", _raises(ValueError, replay.Cursor, s70, 71))

K = 30
def at_k(cur):
    return 1.0 if len(cur) >= K else 0.0
r = replay.replay(s70, at_k, cost_bps=0)
f0 = r["fill_list"][0]
check("a decision with K bars closed fills at bar K's OPEN, not bar K-1's close",
      f0["ts"] == s70.bars[K].ts.isoformat() and f0["price"] == s70.bars[K].open,
      f"{f0['ts']} @ {f0['price']} vs bar {K} {s70.bars[K].ts} open {s70.bars[K].open}")
check("an unchanged target is not a fill", r["fills"] == 1)

bh = replay.replay(s70, strategies.buy_and_hold, cost_bps=0)
check("buy_and_hold equals the benchmark exactly at zero cost",
      abs(bh["return"] - bh["benchmark"]) < 1e-12, f"{bh['return']} vs {bh['benchmark']}")
check("the benchmark buys at the first open a strategy could have",
      abs(bh["benchmark"] - (s70.bars[-1].close / s70.bars[2].open - 1)) < 1e-12)
bh5 = replay.replay(s70, strategies.buy_and_hold, cost_bps=5)
check("cost reduces the return", bh5["return"] < bh["return"])
check("exposure is 100% for buy and hold once entered",
      bh["exposure"] > 0.95, str(bh["exposure"]))
check("a flat strategy has zero fills, zero exposure, zero return",
      (lambda z: z["fills"] == 0 and z["exposure"] == 0 and z["return"] == 0)(
          replay.replay(s70, lambda cur: 0.0)))
check("the record says what was not modelled", "dividends" in r["not_modelled"])
check("a blocked series cannot be replayed",
      _raises(replay.Blocked, replay.replay, _series(three_gone), strategies.buy_and_hold))
check("too few bars cannot be replayed",
      _raises(replay.Blocked, replay.replay, _series(_daily(2)), strategies.buy_and_hold))
check("a strategy that peeks is caught",
      _raises(replay.LookAhead, replay.replay, s70, lambda cur: cur[len(cur)].close))
check("max drawdown of a monotone rise is zero", replay.max_drawdown([1, 2, 3]) == 0)
check("max drawdown measures peak to trough", abs(replay.max_drawdown([1, 2, 1, 3]) + 0.5) < 1e-12)

down = _series(_daily(70, closes=[100 - i * 0.5 for i in range(70)]))
sc = replay.replay(down, strategies.sma_cross(5, 20), cost_bps=0)
check("sma_cross stays flat in a monotone decline", sc["fills"] == 0 and sc["return"] == 0)

# ---------------------------------------------------------------- strategies

print("\nstrategies — the contract")

check("an unknown strategy is refused", _raises(KeyError, strategies.make, "alpha_machine"))
check("spec parses parameters", strategies.make("sma_cross:10,30").__name__ == "sma_cross_10_30")
check("bad sma parameters are refused", _raises(ValueError, strategies.make, "sma_cross:30,10"))
check("buy_and_hold is registered", strategies.make("buy_and_hold") is strategies.buy_and_hold)
check("breakout names itself", strategies.make("breakout:20").__name__ == "breakout_20")
check("a strategy short of history returns flat, not an error",
      strategies.make("sma_cross:10,30")(replay.Cursor(s70, 5)) == 0.0)

# ---------------------------------------------------------------- ledger

print("\nledger — append-only")

H_before = ledger.load()
_real_ledger = ledger.LEDGER
ledger.LEDGER = os.path.join(_tmp, "ledger.json")
ledger.record("backtest", strategy="a", symbol="X", **{"return": 0.1, "bars": 70})
ledger.record("backtest", strategy="a", symbol="X", **{"return": 0.2, "bars": 70})
check("record appends, never replaces", len(ledger.events("backtest")) == 2)
check("latest is the most recent", ledger.latest("backtest", strategy="a", symbol="X")["return"] == 0.2)
check("no record is None", ledger.latest("backtest", strategy="b", symbol="X") is None)
ledger.record("paper", strategy="a", symbol="X", filled_qty=0, status="accepted")
check("an unfilled paper run is NOT live evidence", ledger.filled_paper_runs("a", "X") == [])
ledger.record("paper", strategy="a", symbol="X", filled_qty=5, status="filled")
check("a filled paper run is", len(ledger.filled_paper_runs("a", "X")) == 1)
ledger.record("bypass", mode="live", strategy="a", symbol="X",
              missing="a paper run that filled", reason="the test reason")
html = open(ledger.build_report(ledger.load(), _tmp)).read()
check("the report marks a bypass", "Gate bypassed" in html and "the test reason" in html)
check("the report uses the red bypass style", 'class="bypass"' in html)
check("the report lists backtests", html.count("<tr>") >= 3)
check("an empty ledger renders", "Ledger is empty" in open(ledger.build_report({"events": []}, _tmp)).read())

# ---------------------------------------------------------------- fetch

print("\nfetch — NETWORK / PARSE / OK kept apart")

check("stooq 'No data' is PARSE, never an empty series",
      _raises(B.Unparseable, fetch.parse_stooq, "No data", "ZZZZ"))
check("an html page from stooq is NETWORK", _raises(fetch.Unreachable, fetch.parse_stooq, "<html><body>slow down</body></html>", "AAPL"))
try:
    fetch.parse_stooq("<html><head><script>x()</script></head><body><h1>Too many requests</h1></body></html>", "SPY")
    _pm = ""
except fetch.Unreachable as e:
    _pm = str(e)
check("the page error quotes what the page said", "Too many requests" in _pm and "x()" not in _pm)
check("the page error gives the browser fallback with the right file name",
      "stooq.com/q/d/?s=spy.us" in _pm and "bars/SPY-1d.csv" in _pm)
try:
    fetch.parse_stooq("Exceeded the daily hits limit", "SPY")
    _hm = ""
except fetch.Unreachable as e:
    _hm = str(e)
check("the hit-limit reply is named and given the fallback", "hit limit" in _hm and "bars/SPY-1d.csv" in _hm)
check("stooq is asked with a browser user agent", fetch.BROWSER_UA.startswith("Mozilla/5.0"))
check("visible text strips tags and scripts", fetch._visible_text("<p>a <b>b</b></p><script>z</script>") == "a b")
check("a short body is NETWORK", _raises(fetch.Unreachable, fetch.parse_stooq, "x", "AAPL"))
ok = fetch.parse_stooq(STOOQ, "aapl")
check("a real stooq body is OK with provenance",
      len(ok) == 2 and ok.symbol == "AAPL" and ok.provenance["source"] == "stooq"
      and ok.provenance["adjusted"] is None)
check("stooq symbols get .us", fetch._stooq_sym("AAPL") == "aapl.us" and fetch._stooq_sym("spy.us") == "spy.us")
check("alpaca error JSON is PARSE", _raises(B.Unparseable, fetch.parse_alpaca_page, '{"message":"forbidden"}'))
check("alpaca non-JSON is PARSE", _raises(B.Unparseable, fetch.parse_alpaca_page, "<html>"))
page, tok = fetch.parse_alpaca_page('{"bars":[{"t":"2026-01-05T05:00:00Z","o":1,"h":2,"l":0.5,"c":1.5,"v":9}],"next_page_token":"abc"}')
check("alpaca page parses with its token", len(page) == 1 and tok == "abc")
check("alpaca empty bars is OK-with-zero, a true statement about the range",
      fetch.parse_alpaca_page('{"bars":[],"next_page_token":null}') == ([], None))
check("an unreachable host is NETWORK", _raises(fetch.Unreachable, fetch._get, "https://127.0.0.1:9/x"))
for k in ("ALPACA_KEY_ID", "ALPACA_SECRET_KEY"):
    os.environ.pop(k, None)
check("alpaca without keys refuses before any request", _raises(fetch.Unreachable, fetch.fetch_alpaca, "AAPL"))
_yj = json.dumps({"chart": {"result": [{"timestamp": [1704207600, 1704294000, 1704380400],
    "indicators": {"quote": [{"open": [1, 2, None], "high": [2, 3, 4], "low": [0.5, 1.5, 2.5],
                              "close": [1.5, 2.5, 3.5], "volume": [10, 20, 30]}],
                   "adjclose": [{"adjclose": [1.2, 2.0, 2.8]}]}}], "error": None}})
_ys = fetch.parse_yahoo(_yj, "spy")
check("yahoo JSON parses, null rows skipped, dates pinned", len(_ys) == 2 and _ys.symbol == "SPY"
      and _ys[0].ts == dt.datetime(2024, 1, 2, tzinfo=B.UTC) and _ys.provenance["rows_skipped_null"] == 1)
check("yahoo raw close is the official close, dividends not folded in",
      _ys[0].close == 1.5 and _ys.provenance["adjusted"] is False and "official" in _ys.provenance["close_is"])
_ya = fetch.parse_yahoo(_yj, "spy", adjusted_close=True)
check("yahoo --adjusted-close back-adjusts the whole bar by the same factor",
      _ya[0].close == 1.2 and abs(_ya[0].open - 1 * 1.2 / 1.5) < 1e-12 and _ya.provenance["adjusted"] is True)
check("yahoo error JSON is PARSE", _raises(B.Unparseable, fetch.parse_yahoo, json.dumps({"chart": {"result": None, "error": {"code": "Not Found"}}}), "ZZZZ"))
check("yahoo html is NETWORK", _raises(fetch.Unreachable, fetch.parse_yahoo, "<html>blocked</html>", "SPY"))
check("yahoo all-null rows are PARSE, never zero bars",
      _raises(B.Unparseable, fetch.parse_yahoo, json.dumps({"chart": {"result": [{"timestamp": [1], "indicators": {"quote": [{"open": [None], "high": [None], "low": [None], "close": [None], "volume": [None]}]}}], "error": None}}), "SPY"))
_m_old = _series(_daily(6))
_m_new = _series([B.Bar(_m_old.bars[2].ts, 1, 2, 0.5, 1.5, 9)] + list(_daily(9)[6:8]), prov={"source": "patch", "fetched_at": "x", "start": "s", "end": "e"})
_mrg, _added, _repl = fetch.merge(_m_old, _m_new)
check("merge is a union by timestamp, sorted", len(_mrg) == 8 and [b.ts for b in _mrg] == sorted(b.ts for b in _mrg))
check("the new bar wins on a collision", _repl == 1 and _added == 2 and _mrg.bars[2].close == 1.5)
check("the merge is recorded in provenance", _mrg.provenance["merged"][0]["added"] == 2 and _mrg.provenance["merged"][0]["from"] == "patch")
check("a different symbol or timeframe is refused", _raises(ValueError, fetch.merge, _m_old, _series(_daily(2), symbol="OTHER")))
_out = io.StringIO()
with contextlib.redirect_stdout(_out):
    fetch.dry_run()
check("dry run proves all three outcomes offline",
      _out.getvalue().count("  ok   ") == 4 and "??" not in _out.getvalue())

# ---------------------------------------------------------------- tls

print("\ntls — verifying, always")

import ssl
import urllib.error
import tlsctx

_ctx = tlsctx.context()
check("the context checks hostnames", _ctx.check_hostname is True)
check("the context REQUIRES a valid certificate", _ctx.verify_mode == ssl.CERT_REQUIRED)
check("the context is a real SSLContext", isinstance(_ctx, ssl.SSLContext))
check("source() names a trust store", any(k in tlsctx.source() for k in ("truststore", "certifi", "OpenSSL")))
_cve = ssl.SSLCertVerificationError(1, "[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: self-signed certificate in certificate chain")
check("a bare cert error is recognised", tlsctx.is_cert_failure(_cve))
check("a cert error wrapped in URLError is recognised", tlsctx.is_cert_failure(urllib.error.URLError(_cve)))
check("a plain connection refusal is NOT a cert error",
      not tlsctx.is_cert_failure(urllib.error.URLError(ConnectionRefusedError(61, "refused"))))
_ex = tlsctx.explain(urllib.error.URLError(_cve))
check("the explanation names the fix", "pip install truststore" in _ex and "Install Certificates.command" in _ex)
check("the explanation says verification was not disabled", "NOT disabled" in _ex)
check("the explanation names this python", sys.executable in _ex)
check("the explanation gives a way to tell the cases apart", "curl -sI https://stooq.com" in _ex)
check("fetch reports a cert failure as NETWORK with the fix",
      _raises(fetch.Unreachable, fetch._get, "https://127.0.0.1:9/x"))   # refused, not cert — still NETWORK
# Looks for the loosening as CODE — a call, an assignment — not as a word in
# a docstring that explains why it is never done.
_loosen = ("_create_unverified_context(", "CERT_NONE", "check_hostname = False",
           "check_hostname=False")
check("nothing in the tree loosens TLS",
      not any(any(p in open(os.path.join(HERE, f)).read() for p in _loosen)
              for f in os.listdir(HERE) if f.endswith(".py") and f != "test_tools.py"))

# ---------------------------------------------------------------- broker

print("\nbroker — refuses before it sends")

check("no credentials is NoCredentials", _raises(broker.NoCredentials, broker.credentials))
check("a bad side is refused before any request",
      _raises(ValueError, broker.place_order, broker.PAPER, {}, "AAPL", "short", 1))
check("a zero qty is refused before any request",
      _raises(ValueError, broker.place_order, broker.PAPER, {}, "AAPL", "buy", 0))
check("an unreachable base is Unreachable",
      _raises(broker.Unreachable, broker.account, "https://127.0.0.1:9", {}))
sm = broker.summarise({"id": "o1", "status": "accepted", "side": "buy", "qty": "5"})
check("an unfilled order summarises with filled_qty 0 and no price",
      sm["filled_qty"] == 0 and sm["filled_avg_price"] is None and sm["order_id"] == "o1")
check("paper and live endpoints are different hosts", broker.PAPER != broker.LIVE and "paper" in broker.PAPER)

# ---------------------------------------------------------------- the gate

print("\nthe gate — signal → backtest → paper → live")

_fix = os.path.join(_tmp, "SYN-1d.csv")
B.to_csv(_series(_daily(80)), _fix)
strategies.REGISTRY["flat"] = lambda: (lambda cur: 0.0)


def _run(argv):
    real = sys.argv
    sys.argv = ["run.py"] + argv
    try:
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            run.main()
        return 0
    except SystemExit as e:
        return e.code if isinstance(e.code, int) else 1
    finally:
        sys.argv = real


BASE = ["--csv", _fix, "--symbol", "SYN", "--source", "test", "--adjusted", "yes"]
SMA = ["--strategy", "sma_cross:10,30"]
BRK = ["--strategy", "breakout:20"]

check("signal runs with no gate", _run(["--mode", "signal"] + SMA + BASE) == 0)
_sig = subprocess.run([sys.executable, "run.py", "--mode", "signal"] + SMA + BASE,
                      cwd=HERE, capture_output=True, text=True).stdout
check("signal mode prints the readings — ema, vwap, rejection, level, poc",
      all(k in _sig for k in ("ema20", "vwap", "rejection", "level", "poc")))
check("signal mode labels the order-flow proxy as a proxy", "PROXY" in _sig)
check("an unknown strategy is refused (2)", _run(["--mode", "signal", "--strategy", "nope"] + BASE) == 2)
check("paper is refused with no backtest (3)", _run(["--mode", "paper", "--qty", "5", "--dry-run"] + SMA + BASE) == 3)
check("refusal wrote nothing", ledger.events(strategy="sma_cross_10_30") == [])
check("backtest runs and records", _run(["--mode", "backtest"] + SMA + BASE) == 0
      and ledger.latest("backtest", strategy="sma_cross_10_30", symbol="SYN") is not None)
check("the backtest record carries the not-modelled list",
      "dividends" in ledger.latest("backtest", strategy="sma_cross_10_30", symbol="SYN")["not_modelled"])
check("the backtest record does not carry the equity curve",
      "equity" not in ledger.latest("backtest", strategy="sma_cross_10_30", symbol="SYN"))
check("paper dry-run passes the gate once a backtest exists (0)",
      _run(["--mode", "paper", "--qty", "5", "--dry-run"] + SMA + BASE) == 0)
check("a dry run records no paper run", ledger.events("paper", strategy="sma_cross_10_30") == [])
check("paper on a DIFFERENT strategy is still refused (3)",
      _run(["--mode", "paper", "--qty", "5", "--dry-run"] + BRK + BASE) == 3)
check("live is refused without a filled paper run (3)",
      _run(["--mode", "live", "--qty", "1", "--dry-run", "--confirm-live"] + SMA + BASE) == 3)
check("live is refused without --confirm-live (3)",
      _run(["--mode", "live", "--qty", "1", "--dry-run"] + SMA + BASE) == 3)
n_bypass = len(ledger.events("bypass"))
check("live without --confirm-live records NO bypass even when forced",
      _run(["--mode", "live", "--qty", "1", "--dry-run", "--force", "--force-reason", "x"] + SMA + BASE) == 3
      and len(ledger.events("bypass")) == n_bypass)
check("--force without a reason is refused (4)",
      _run(["--mode", "paper", "--qty", "5", "--dry-run", "--force"] + BRK + BASE) == 4)
check("--force with a blank reason is refused (4)",
      _run(["--mode", "paper", "--qty", "5", "--dry-run", "--force", "--force-reason", "  "] + BRK + BASE) == 4)
check("a refused force writes nothing", len(ledger.events("bypass")) == n_bypass)
check("--force with a reason passes the gate (0)",
      _run(["--mode", "paper", "--qty", "5", "--dry-run", "--force", "--force-reason", "test bypass"] + BRK + BASE) == 0)
bp = ledger.latest("bypass", strategy="breakout_20", symbol="SYN")
check("the bypass is recorded with its reason and what was missing",
      bp is not None and bp["reason"] == "test bypass" and "backtest" in bp["missing"])
check("a flat signal has nothing to buy (3)",
      _run(["--mode", "backtest", "--strategy", "flat"] + BASE) == 0
      and _run(["--mode", "paper", "--strategy", "flat", "--qty", "5", "--dry-run"] + BASE) == 3)
check("paper without --qty is refused (3)", _run(["--mode", "paper", "--dry-run"] + SMA + BASE) == 3)
check("a REAL paper run with no keys is refused (5) and records nothing",
      _run(["--mode", "paper", "--qty", "5"] + SMA + BASE) == 5 and ledger.events("paper", strategy="sma_cross_10_30") == [])
_bad = os.path.join(_tmp, "BAD-1d.csv")
B.to_csv(_series(three_gone), _bad)
check("a blocked series is refused before any mode runs (2)",
      _run(["--mode", "signal"] + SMA + ["--csv", _bad, "--symbol", "SYN", "--source", "t", "--adjusted", "yes"]) == 2)
help_ = subprocess.run([sys.executable, "run.py", "--help"], cwd=HERE, capture_output=True, text=True).stdout
check("--force is documented in --help", "--force" in help_ and "--force-reason" in help_)
check("--confirm-live is documented in --help", "--confirm-live" in help_)


# ---------------------------------------------------------------- features

print("\nfeatures — the chart, as numbers")

import features as F


def _b(o, h, l, c, v=100, d=1):
    return B.Bar(dt.datetime(2026, 1, d, tzinfo=B.UTC), float(o), float(h), float(l), float(c), float(v))


check("sma", F.sma([1, 2, 3, 4], 2) == 3.5)
check("sma short of data is None", F.sma([1, 2], 3) is None)
check("ema seeds with the SMA then smooths (alpha 0.5 for n=3)", F.ema([1, 2, 3, 4, 5], 3) == 4.0)
check("ema_series is None before n values", F.ema_series([1, 2, 3, 4, 5], 3) == [None, None, 2.0, 3.0, 4.0])
check("ema accepts bars or numbers", F.ema([_b(10, 11, 9, 1), _b(10, 11, 9, 2), _b(10, 11, 9, 3)], 2) == 2.5)
_bs = [_b(10, 12, 9, 11, d=1), _b(11, 13, 10, 12, d=2), _b(12, 12.5, 11, 11.5, d=3)]
check("true range uses the previous close", F.true_range(_bs[2], _bs[1].close) == 1.5)
check("atr is the mean of the last n true ranges", F.atr(_bs, 2) == 2.25)
check("atr short of data is None", F.atr(_bs, 3) is None)
check("vwap weights typical price by volume", abs(F.vwap(_bs[:2]) - (10.6667 * 100 + 11.6667 * 100) / 200) < 1e-3)
check("vwap with no volume is None", F.vwap([_b(10, 11, 9, 10, 0)]) is None)

check("a hammer is a bull rejection", F.rejection(_b(10, 10.6, 8, 10.5)) == "bull")
check("a shooting star is a bear rejection", F.rejection(_b(10, 12, 9.9, 9.5)) == "bear")
check("a full-body bar is no rejection", F.rejection(_b(10, 11, 10, 11)) is None)
check("a long-wick doji still counts (body floored at 5%)", F.rejection(_b(10, 10.1, 8, 10)) == "bull")
check("a long lower wick that closed weak is NOT a bull rejection", F.rejection(_b(10, 10.2, 8, 8.5)) is None)
check("a zero-range bar is no rejection", F.rejection(_b(10, 10, 10, 10)) is None)
check("rejections indexes the sequence", F.rejections([_b(10, 11, 10, 11), _b(10, 10.6, 8, 10.5)]) == [(1, "bull")])

_sw = [_b(10, 11, 9, 10, d=i + 1) for i in range(9)]
_sw[4] = _b(10, 14, 9, 10, d=5)
_sw[7] = _b(10, 11, 6, 10, d=8)
check("a swing high needs higher than left AND right neighbours", F.swings(_sw, 2, 1)["highs"] == [(4, 14.0)])
check("a swing low mirrors", F.swings(_sw, 2, 1)["lows"] == [(7, 6.0)])
# A new highest high at the very end is not a swing yet — nothing has printed
# after it. Placed past index 4's right-window so that swing survives.
check("the last `right` bars can never be swings yet",
      F.swings(_sw[:8] + [_b(10, 20, 9, 10, d=9)], 2, 2)["highs"] == [(4, 14.0)])
check("a higher high inside the right-window cancels the earlier swing",
      F.swings(_sw[:6] + [_b(10, 20, 9, 10, d=7)], 2, 2)["highs"] == [])
check("levels are sorted with touch counts",
      F.levels(_sw, 2, 1) == [{"price": 6.0, "touches": 1}, {"price": 14.0, "touches": 1}])
_touch = _sw + [_b(10, 11, 9, 10, d=10), _b(10, 14.01, 9, 10, d=11), _b(10, 11, 9, 10, d=12), _b(10, 11, 9, 10, d=13)]
check("swings within tolerance merge into one level with 2 touches",
      any(l["touches"] == 2 and abs(l["price"] - 14.005) < 1e-9 for l in F.levels(_touch, 2, 1)))
_n, _dist = F.nearest_level(13.5, F.levels(_sw, 2, 1))
check("nearest level and signed distance", _n["price"] == 14.0 and abs(_dist - (13.5 - 14) / 13.5) < 1e-12)
check("no levels gives (None, None)", F.nearest_level(1, []) == (None, None))

_vp = [_b(10, 12, 10, 12, 100, d=1), _b(11, 13, 11, 13, 100, d=2), _b(10, 11, 10, 11, 60, d=3)]
_p = F.volume_profile(_vp, bins=3)
check("volume spreads evenly across each bar's range",
      [round(v) for _, _, v in _p["bins"]] == [110, 100, 50])
check("point of control is the heaviest bin's midpoint", _p["poc"] == 10.5)
check("value area grows toward the heavier side", _p["va_low"] == 10.0 and _p["va_high"] == 12.0)
check("value area holds at least the requested share", _p["value_area_share"] >= 0.70)
check("a zero-range bar's volume lands in one bin",
      F.volume_profile([_b(10, 10, 10, 10, 5), _b(9, 11, 9, 11, 0)], bins=2)["bins"][1][2] == 5)
check("an empty profile is None", F.volume_profile([], 3) is None)

check("bar delta proxy signs volume by close vs open",
      (F.bar_delta_proxy(_b(10, 11, 9, 11)), F.bar_delta_proxy(_b(11, 11, 9, 10)), F.bar_delta_proxy(_b(10, 11, 9, 10))) == (100, -100, 0))
check("cvd proxy cumulates", F.cvd_proxy([_b(10, 11, 9, 11), _b(11, 11, 9, 10, 40)]) == [100, 60])
check("the proxy says so in its name", "proxy" in F.bar_delta_proxy.__name__ and "PROXY" in F.bar_delta_proxy.__doc__)

_intra = [B.Bar(dt.datetime(2026, 1, 5, 14, 30, tzinfo=B.UTC), 1, 2, 0.5, 1.5, 10),
          B.Bar(dt.datetime(2026, 1, 5, 15, 30, tzinfo=B.UTC), 1, 2, 0.5, 1.5, 10),
          B.Bar(dt.datetime(2026, 1, 6, 14, 30, tzinfo=B.UTC), 1, 2, 0.5, 1.5, 10)]
check("session_bars keeps only the last trading date", len(F.session_bars(_intra)) == 1)
check("session vwap is over that session", F.session_vwap(_intra) == F.vwap(_intra[-1:]))

check("features read a cursor slice, never the series",
      F.ema(replay.Cursor(s70, 30)[-30:], 10) is not None
      and F.ema(replay.Cursor(s70, 30)[-30:], 10) == F.ema(s70.bars[:30], 10))
_dsc = F.describe(s70.bars)
check("describe reports the readings at the last close",
      _dsc["close"] == s70.bars[-1].close and _dsc["ema"] is not None and _dsc["poc"] is not None)

print("\nstrategies — the discretionary setups, made testable")

for spec, name in (("ema_pullback:20,50", "ema_pullback_20_50_5"), ("vwap_reclaim:20", "vwap_reclaim_20"),
                   ("value_area:40", "value_area_40")):
    st = strategies.make(spec)
    check(f"{spec} names itself", st.__name__ == name)
    rr = replay.replay(s70, st, cost_bps=5)
    check(f"{spec} replays without peeking", rr["bars"] == 70 and rr["qc_verdict"] != "blocked")
check("ema_pullback refuses fast >= slow", _raises(ValueError, strategies.make, "ema_pullback:50,20"))
check("a feature strategy short of history is flat, not an error",
      strategies.make("ema_pullback:20,50")(replay.Cursor(s70, 10)) == 0.0)
_synth = os.path.join(HERE, "bars", "SYN-1d.csv")
if os.path.exists(_synth):
    _syn = B.load_csv(_synth, "SYN", "1d", "synthetic", True)
    _res = {sp: replay.replay(_syn, strategies.make(sp), cost_bps=5) for sp in ("ema_pullback:20,50", "vwap_reclaim:20", "value_area:40")}
    check("on a drifting random walk every setup lags buy-and-hold after costs — the machinery says so",
          all(r["return"] < r["benchmark"] for r in _res.values()),
          str({k: round(v["return"], 3) for k, v in _res.items()}))

# ---------------------------------------------------------------- features, round 2

print("\nfeatures — rsi, doji, engulfing, round numbers")

check("rsi of a monotone rise is 100", F.rsi([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16], 14) == 100.0)
check("rsi of a monotone fall is 0", F.rsi(list(range(16, 0, -1)), 14) == 0.0)
check("rsi of equal up and down steps is 50 at the seed", abs(F.rsi([10 + (i % 2) for i in range(15)], 14) - 50.0) < 1e-9)
check("rsi short of data is None", F.rsi([1, 2, 3], 14) is None)
_v = [100 + ((i * 7) % 5) - 2 + i * 0.1 for i in range(40)]
check("rsi_series agrees with rsi at the end", abs(F.rsi_series(_v, 14)[-1] - F.rsi(_v, 14)) < 1e-12)
check("rsi_series is None before n+1 values", F.rsi_series(_v, 14)[13] is None and F.rsi_series(_v, 14)[14] is not None)
check("doji is a tiny body", F.doji(_b(10, 11, 9, 10.05)) and not F.doji(_b(10, 11, 9, 10.8)))
check("bull engulfing covers the previous down body", F.engulfing(_b(10, 10.2, 9.5, 9.7), _b(9.6, 10.5, 9.5, 10.3)) == "bull")
check("bear engulfing mirrors", F.engulfing(_b(9.7, 10.2, 9.5, 10), _b(10.1, 10.2, 9.4, 9.6)) == "bear")
check("two up bars are not engulfing", F.engulfing(_b(9, 10, 9, 10), _b(10, 11, 10, 11)) is None)
check("round step is a tenth of the leading decade", (F.round_step(450), F.round_step(45), F.round_step(4.5)) == (10.0, 1.0, 0.1))
_rd, _near = F.round_distance(449.0)
check("round distance is signed and names the number", _near == 450.0 and abs(_rd - (449 - 450) / 449) < 1e-12)
check("drawdown from the k-bar high", abs(F.drawdown_from_high([10, 12, 11, 9], 4) - (9 / 12 - 1)) < 1e-12)

# ---------------------------------------------------------------- replay, round 2

print("\nreplay — stats, cash yield, windows")

_r = replay.replay(s70, strategies.buy_and_hold, cost_bps=0)
check("replay reports sharpe, cagr, volatility, skew, kurt",
      all(k in _r for k in ("sharpe", "cagr", "volatility", "skew", "kurt", "sharpe_per_bar")))
check("targets and equity_ts align with equity", len(_r["targets"]) == len(_r["equity"]) == len(_r["equity_ts"]))
check("bar_returns is one shorter than equity", len(_r["bar_returns"]) == len(_r["equity"]) - 1)
check("ledger exclusions name every per-bar series",
      set(("equity", "equity_ts", "targets", "bar_returns", "fill_list")) <= set(replay.LEDGER_EXCLUDE))
_ry = replay.replay(s70, strategies.buy_and_hold, cost_bps=0, cash_yield=0.05)
check("buy and hold earns yield only on the one warm-up bar before it fills",
      abs((1 + _ry["return"]) / (1 + _r["return"]) - 1.05 ** (1 / 252)) < 1e-12)
_flat = replay.replay(s70, lambda c: 0.0, cash_yield=0.04)
check("a flat strategy earns the cash yield on every scored bar", abs(_flat["return"] - ((1.04) ** (69 / 252) - 1)) < 1e-9, str(_flat["return"]))
check("zero cash yield earns nothing flat", replay.replay(s70, lambda c: 0.0)["return"] == 0.0)
_all = replay.window_stats(_r)
check("the full window reproduces the overall return", abs(_all["return"] - _r["return"]) < 1e-12)
_cut = _r["equity_ts"][40]
_a, _b_ = replay.window_stats(_r, end=_cut), replay.window_stats(_r, start=_cut)
check("in-sample and holdout partition the bars", _a["bars_used"] + _b_["bars_used"] == len(_r["equity"]))
check("an empty window has no return", replay.window_stats(_r, start="2099-01-01")["return"] is None)
check("window fills are counted inside the window", replay.window_stats(_r, end=_cut)["fills"] == 1)

check("trend_filter names itself", strategies.make("trend_filter:20").__name__ == "trend_filter_20")
check("trend_filter is long in a rise", strategies.make("trend_filter:20")(replay.Cursor(s70, 70)) == 1.0)
check("trend_filter is flat in a fall", strategies.make("trend_filter:20")(replay.Cursor(down, 70)) == 0.0)
check("every strategy declares a warm-up",
      all(hasattr(strategies.make(sp), "warmup") for sp in ("buy_and_hold", "sma_cross:10,30", "breakout:20", "trend_filter:200", "ema_pullback:20,50", "vwap_reclaim:20", "value_area:40")))
_tf = replay.replay(s70, strategies.make("trend_filter:20"), cost_bps=0)
check("replay scores from the strategy's warm-up, not from bar 2",
      _tf["warmup"] == 20 and _tf["live_bars"] == 50 and _tf["scored_from"] == s70.bars[20].ts.isoformat())
check("the benchmark is measured from the same bar",
      abs(_tf["benchmark"] - (s70.bars[-1].close / s70.bars[21].open - 1)) < 1e-12)
check("a rising series: trend filter equals buy-and-hold from its warm-up, less nothing at zero cost",
      abs(_tf["return"] - _tf["benchmark"]) < 1e-12, f"{_tf['return']} vs {_tf['benchmark']}")
check("an explicit warm-up longer than the strategy's wins", replay.replay(s70, strategies.buy_and_hold, warmup=30)["warmup"] == 30)
_nd = replay.replay(s70, strategies.buy_and_hold, cost_bps=0)
_wd = replay.replay(s70, strategies.buy_and_hold, cost_bps=0, dividend_yield=0.02)
check("a dividend yield raises buy-and-hold's return", _wd["return"] > _nd["return"])
check("the benchmark gets the same credit, so buy-and-hold still equals it",
      abs(_wd["return"] - _wd["benchmark"]) < 1e-9, f"{_wd['return']} vs {_wd['benchmark']}")
check("a flat strategy collects no dividend", replay.replay(s70, lambda c: 0.0, dividend_yield=0.02)["return"] == 0.0)
check("the record carries the dividend assumption", _wd["dividend_yield"] == 0.02)
# a series with real variation — s70 rises exactly 0.2% a bar, so its return
# variance is zero and floating point decides the Sharpe
_wob = _series(_daily(70, closes=[100 + ((i * 7) % 5) * 1.5 + i * 0.3 for i in range(70)]))
_bh0 = replay.replay(_wob, strategies.buy_and_hold, cost_bps=0)
check("buy-and-hold's own drawdown and sharpe equal the benchmark's over the same bars",
      abs(_bh0["max_drawdown"] - _bh0["benchmark_max_drawdown"]) < 1e-12
      and abs(_bh0["sharpe"] - _bh0["benchmark_sharpe"]) < 1e-9
      and _bh0["max_drawdown"] < 0, f"{_bh0['max_drawdown']} {_bh0['sharpe']} {_bh0['benchmark_sharpe']}")
check("a filter is reported beside buy-and-hold's drawdown over the SAME scored bars",
      "benchmark_max_drawdown" in _tf and _tf["benchmark_max_drawdown"] <= 0)
check("run.py accepts --cash-yield and records it",
      _run(["--mode", "backtest", "--strategy", "trend_filter:20", "--cash-yield", "0.04"] + BASE) == 0
      and ledger.latest("backtest", strategy="trend_filter_20", symbol="SYN")["cash_yield"] == 0.04)
_rec = ledger.latest("backtest", strategy="trend_filter_20", symbol="SYN") or {}
check("the record carries sharpe and no per-bar series", "sharpe" in _rec and "targets" not in _rec and "equity_ts" not in _rec)

# ---------------------------------------------------------------- intraday

print("\nintraday — pre-registered, with its own null")

import intraday

_syn = intraday.synth(40, effect=0.0)
check("synth makes 390 regular-session bars per session", len(_syn) == 40 * 390)
_ss = intraday.sessions(_syn)
check("sessions groups by New York date", len(_ss) == 40 and all(len(p) == 390 for _, p in _ss))
_m, _why = intraday.measure(_ss[0][1])
check("measure reads a full session", _m is not None and set(_m) >= {"r_first30", "r_open_to_1530", "r_last30"})
_pts = _ss[0][1]
_c10 = [b for loc, b in _pts if loc.time() < dt.time(10, 0)][-1].close
check("r_first30 is the close before 10:00 over the 09:30 open", abs(_m["r_first30"] - (_c10 / _pts[0][1].open - 1)) < 1e-12)
_b1530 = [b for loc, b in _pts if loc.time() >= dt.time(15, 30)][0]
check("the fill is the 15:30 bar's OPEN, never the 15:29 close",
      abs(_m["r_last30"] - (_pts[-1][1].close / _b1530.open - 1)) < 1e-12)
# Synthetic bars open exactly at the prior close, so the line above cannot tell
# the two apart — a mutation proved it. Put a GAP on the 15:30 bar and pin it.
_gap = []
for loc, b in _pts:
    if loc.time() == dt.time(15, 30):
        prev_close = _gap[-1][1].close
        b = B.Bar(b.ts, prev_close * 1.001, max(b.high, prev_close * 1.001), b.low, b.close, b.volume)
    _gap.append((loc, b))
_mg, _ = intraday.measure(_gap)
_g1530 = [b for loc, b in _gap if loc.time() == dt.time(15, 30)][0]
_c1529 = [b for loc, b in _gap if loc.time() < dt.time(15, 30)][-1].close
check("with a gap, the fill is the gapped OPEN and not the prior close",
      abs(_mg["r_last30"] - (_gap[-1][1].close / _g1530.open - 1)) < 1e-12
      and abs(_mg["r_last30"] - (_gap[-1][1].close / _c1529 - 1)) > 1e-6)
check("a short session is skipped with its bar count", intraday.measure(_pts[:100]) == (None, "100 bars"))
check("a session without its 09:30 bar is skipped", intraday.measure(_pts[5:] + _pts[:5][:0])[1] == "no 09:30 bar"
      if len(_pts[5:]) >= intraday.MIN_BARS else True)
check("a session ending early is skipped", intraday.measure(_pts[:370])[1].startswith("ends"))
_rows = [{"date": "2024-01-02", "r_first30": 0.001, "r_open_to_1530": 0.0, "r_last30": 0.002},
         {"date": "2024-01-03", "r_first30": -0.001, "r_open_to_1530": 0.0, "r_last30": 0.002},
         {"date": "2024-01-04", "r_first30": 0.0, "r_open_to_1530": 0.0, "r_last30": 0.002}]
_tr = intraday.trades(_rows, "first30", 2.0)
check("a positive morning goes long the last half hour, net of cost", _tr[0]["side"] == 1 and abs(_tr[0]["ret"] - (0.002 - 0.0002)) < 1e-12)
check("a negative morning goes short", _tr[1]["side"] == -1 and abs(_tr[1]["ret"] - (-0.002 - 0.0002)) < 1e-12)
check("a flat morning is no trade", len(_tr) == 2)
check("open_to_1530 rule uses the other predictor", intraday.trades(_rows, "open_to_1530", 0) == [])
_st = intraday.stats([{"ret": 0.001}, {"ret": -0.001}, {"ret": 0.003}])
check("stats: mean in bp, hit rates labelled net and gross, t",
      abs(_st["mean_bp"] - 10.0) < 1e-9 and abs(_st["hit_net"] - 2 / 3) < 1e-12 and _st["t"] > 0
      and "gross_bp" in _st and "se_bp" in _st and len(_st["ci95_bp"]) == 2)
_strong = intraday.run(intraday.synth(300, effect=2.0), "first30", 2.0, "2025-01-01", 200)
check("a strong planted effect is found: positive mean, low p", _strong["all"]["mean_bp"] > 0 and _strong["p_all"] < 0.05,
      f"mean {_strong['all']['mean_bp']:.2f} p {_strong['p_all']}")
_null = intraday.run(intraday.synth(300, effect=0.0), "first30", 2.0, "2025-01-01", 200)
check("no effect: p is not small", _null["p_all"] > 0.1, str(_null["p_all"]))
check("the run says it searched nothing", _strong["pre_registered"] and _strong["parameters_searched"] == 0)
check("the power statement names the published effect and whether the CI excludes it",
      "published_excluded" in _strong and "bp/session" in _strong["power_note"])
_slip = [(loc, b) for loc, b in _pts if loc.time() != dt.time(15, 30)]
check("a session missing its 15:30 minute fills at the next bar and is counted as slipped",
      intraday.measure(_slip)[0]["fill_slipped"] is True and intraday.measure(_pts)[0]["fill_slipped"] is False)
check("an IEX-sourced run names the closing auction as unmodelled",
      "AUCTION" in intraday.run(B.Series("X", "1m", _syn.bars, {**PROV, "source": "alpaca", "feed": "iex"}), "first30", 2.0, "2025-01-01", 5)["not_modelled"])
check("a short session is skipped at barqc's 80% line", intraday.MIN_BARS == 312)
# trial 3: the official close as the exit, joined by date
_syn3 = intraday.synth(30, effect=0.0, seed=11)
_agg3, _, _ = __import__("aggregate").aggregate(_syn3)
_cm = intraday.official_closes(_agg3)
check("official_closes maps dates to closes", len(_cm) == 30 and all(len(k) == 10 for k in _cm))
_r3 = intraday.run(_syn3, "first30", 2.0, "2024-02-01", 5, close_map=_cm, close_source="test-daily")
check("trial 3 is named, numbered and says where its exits came from",
      _r3["strategy"] == "intraday_first30_official_close" and _r3["trial"] == 3
      and "official close from test-daily" in _r3["exit_price"])
check("with the same closes the result equals the feed-close run",
      abs(_r3["all"]["gross_bp"] - intraday.run(_syn3, "first30", 2.0, "2024-02-01", 5)["all"]["gross_bp"]) < 1e-9)
_cm_up = {k: v * 1.001 for k, v in _cm.items()}
_r3u = intraday.run(_syn3, "first30", 2.0, "2024-02-01", 5, close_map=_cm_up, close_source="t")
check("a higher official close moves the last-half-hour return", _r3u["all"]["gross_bp"] != _r3["all"]["gross_bp"])
_cm_part = dict(list(_cm.items())[:20])
_r3p = intraday.run(_syn3, "first30", 2.0, "2024-02-01", 5, close_map=_cm_part, close_source="t")
check("sessions without an official close are skipped and counted",
      _r3p["sessions"] == 20 and _r3p["skipped"].get("no official close for the date") == 10)
check("trial 3 names the cross-feed basis, not the auction", "cent" in _r3p["not_modelled"] and "AUCTION" not in _r3p["not_modelled"])
check("the report shows the exit source", "exit: official close" in intraday.render(_r3))
_cm_adj = {k: v * 0.95 for k, v in _cm.items()}          # what a dividend-adjusted file looks like
check("a close file on a different price basis is REFUSED, not joined",
      _raises(SystemExit, intraday.run, _syn3, "first30", 2.0, "2024-02-01", 5, close_map=_cm_adj, close_source="adj"))
check("cents of basis are accepted", intraday.run(_syn3, "first30", 2.0, "2024-02-01", 5,
      close_map={k: v * 1.0003 for k, v in _cm.items()}, close_source="t")["trial"] == 3)
check("the run records the data span", _strong["data_start"].startswith("2024") and _strong["data_end"] > _strong["data_start"])
check("a feed that begins after 2019 cannot reproduce the papers, and says so",
      _strong["reproduction_possible"] is False and "NOT a reproduction" in intraday.render(_strong))
_old = intraday.run(intraday.synth(120, effect=0.0, start=dt.date(2018, 1, 2)), "first30", 2.0, "2018-04-01", 20)
check("a feed that begins before 2019 could, and the note is absent",
      _old["reproduction_possible"] is True and "NOT a reproduction" not in intraday.render(_old))
check("in-sample and holdout are split at the date",
      _strong["in_sample"]["n"] + _strong["holdout"]["n"] == _strong["all"]["n"] and _strong["holdout"]["n"] > 0)
check("by-year table exists", "2024" in _strong["by_year"] or "2025" in _strong["by_year"])
_early = B.Series("X", "1m", [B.Bar(dt.datetime(2026, 1, 5, 8, 0, tzinfo=B.UTC), 1, 2, 0.5, 1.5, 1)] * 1, PROV)
check("bars outside the session are refused by barqc before anything runs",
      _raises(SystemExit, intraday.run, _early, "first30", 2.0, "2025-01-01", 10))

# ---------------------------------------------------------------- combine

print("\ncombine — confluence, both ways, with the trial count")

import combine

check("expected max sharpe of one trial is zero", combine.expected_max_sharpe(1, 0.01) == 0.0)
check("expected max sharpe grows with trials",
      combine.expected_max_sharpe(100, 0.01) > combine.expected_max_sharpe(10, 0.01) > 0)
check("expected max sharpe grows with dispersion", combine.expected_max_sharpe(10, 0.04) > combine.expected_max_sharpe(10, 0.01))
_p1, _ = combine.deflated_sharpe(0.05, 500, 1, 0.0)
_p50, _sr0 = combine.deflated_sharpe(0.05, 500, 50, 0.0004)
check("deflated sharpe is high for one trial", _p1 > 0.8, str(_p1))
check("the same sharpe after 50 trials is deflated", _p50 < _p1 and _sr0 > 0, f"{_p50} vs {_p1}")
check("zero sharpe, one trial is a coin flip", abs(combine.deflated_sharpe(0.0, 500, 1, 0.0)[0] - 0.5) < 1e-9)
check("pearson of identical series is 1", abs(combine.pearson([1, 0, 1, 0], [1, 0, 1, 0]) - 1) < 1e-12)
check("pearson of opposite series is -1", abs(combine.pearson([1, 0, 1, 0], [0, 1, 0, 1]) + 1) < 1e-12)
check("pearson of a constant is None", combine.pearson([1, 1, 1], [1, 0, 1]) is None)
_one, _zero = (lambda c: 1.0), (lambda c: 0.0)
_one.__name__, _zero.__name__ = "one", "zero"
check("and-gate needs every signal", combine.and_gate([_one, _zero])(None) == 0.0 and combine.and_gate([_one, _one])(None) == 1.0)
check("average is the mean", combine.average_of([_one, _zero])(None) == 0.5)
_cr = combine.run(s70, ["sma_cross:5,20", "breakout:10"], 5.0, s70.bars[50].ts.isoformat())
check("run scores each signal plus average plus and-gate", len(_cr["trials"]) == 4)
check("correlation matrix has unit diagonal", all(_cr["corr"][i][i] == 1.0 for i in range(2)))
check("all-on never exceeds any-on", _cr["all_on"] <= _cr["any_on"])
check("every trial has in-sample and holdout windows", all("in_sample" in t and "holdout" in t for t in _cr["trials"]))
check("the trial count is what was run", _cr["n_trials"] == 4)
check("the best is named and deflated", _cr["best"] and 0.0 <= _cr["best_dsr"] <= 1.0)
check("buy and hold is scored in both windows as the reference",
      _cr["benchmark"]["in_sample"]["return"] is not None and _cr["benchmark"]["holdout"]["return"] is not None)
check("the reference is not counted as a trial", _cr["n_trials"] == 4)
check("the report shows the reference row", "buy_and_hold (reference)" in combine.render(_cr))
check("every line and the reference are scored from the longest warm-up",
      _cr["warmup"] == 20 and all(t["warmup"] == 20 for t in _cr["trials"]) and _cr["benchmark"]["warmup"] == 20)
check("the trial count says how many were this run", _cr["trials_in_run"] == 4 and _cr["trials_prior"] == 0)
check("the report shows where scoring began", "scored from" in combine.render(_cr))
check("an unknown signal is refused", _raises(KeyError, combine.run, s70, ["nope"], 5.0, "2026-01-01"))

# ---------------------------------------------------------------- nulltest

print("\nnulltest — the pattern against shuffled bars")

import nulltest

_decl = [_b(100 - i, 101 - i, 98 - i, 99.5 - i, d=i + 1) for i in range(12)]      # falling
_decl.append(_b(88, 88.6, 85, 88.5, d=13))                                        # hammer, low 85
_decl += [_b(88.5, 89, 88, 88.8, d=14), _b(88.8, 89.5, 88.5, 89.2, d=15)]
_rules = nulltest.rules(_decl)
check("hammer after a decline fires at the hammer", 12 in _rules["hammer_after_decline"][1])
check("v2 round-number rule is named for what it is", "pin_near_round" in _rules and "pin_at_round" not in _rules)
check("no shooting star in a decline", _rules["star_after_rise"][1] == [])
check("short rules are marked short", _rules["star_after_rise"][0] == -1 and _rules["hammer_after_decline"][0] == 1)
check("forward return is next open to close at the horizon",
      abs(nulltest.forward(_decl, [12], 1, 1, 0.0)[0] - (_decl[13].close / _decl[13].open - 1)) < 1e-12)
check("a short rule negates", nulltest.forward(_decl, [12], -1, 1, 0.0)[0] == -nulltest.forward(_decl, [12], 1, 1, 0.0)[0])
check("an event too close to the end is dropped", nulltest.forward(_decl, [14], 1, 1, 0.0) == [])
check("cost is charged", nulltest.forward(_decl, [12], 1, 1, 0.001)[0] == nulltest.forward(_decl, [12], 1, 1, 0.0)[0] - 0.001)
check("the block shuffle is gone — it kept the pattern→next-bar pair intact",
      not hasattr(nulltest, "block_shuffle"))
_tv = nulltest.trailing_vol(list(s70.bars))
check("trailing vol is None until the window fills and positive after",
      _tv[19] is None and _tv[20] is not None and _tv[20] >= 0)
_elig = list(range(nulltest.LOOKBACK, len(s70.bars) - 1))
_dec = nulltest.vol_deciles(_tv, _elig)
check("vol deciles cover the eligible bars", set(_dec) == set(_elig) and all(v is None or 0 <= v < 10 for v in _dec.values()))
# a planted edge: the event days are followed by big up bars; days like them are not
_pl = _daily(120, closes=[100 + 0.05 * i for i in range(120)])
for _k in (30, 60, 90):
    _pl[_k] = B.Bar(_pl[_k].ts, _pl[_k].open, _pl[_k].open * 1.03, _pl[_k].open, _pl[_k].open * 1.03, 1000)
_pp, _nm = nulltest.date_permutation_p(_pl, [29, 59, 89], 1, 1, 0.0, 200, random.Random(0), vol_match=False)
check("a real link between event and next bar gives a small p", _pp is not None and _pp < 0.05, str(_pp))
_pn, _ = nulltest.date_permutation_p(_pl, [10, 40, 70], 1, 1, 0.0, 200, random.Random(0), vol_match=False)
check("ordinary days give an ordinary p", _pn is not None and _pn > 0.2, str(_pn))
check("no events gives no p", nulltest.date_permutation_p(_pl, [], 1, 1, 0.0, 50, random.Random(0)) == (None, None))
_nt = nulltest.run(s70, 1, 5.0, 20)
check("every pre-registered rule is reported", len(_nt["rules"]) == 8)
check("p is a probability or None", all(r["p"] is None or 0 <= r["p"] <= 1 for r in _nt["rules"].values()))
check("the unconditional baseline is reported", "mean_bp" in _nt["unconditional"])
check("the run says it searched nothing", _nt["pre_registered"] and _nt["parameters_searched"] == 0)
check("the run names its null and rule version", "permutation" in _nt["null"] and _nt["rule_version"] == 2)
check("every fired rule lists its events with dates and returns",
      all(("events" in v and all("date" in e and "ret_bp" in e for e in v["events"])) for v in _nt["rules"].values()))
check("the largest event and its share are reported for fired rules",
      all(("largest_event" in v) == (v["n"] > 0) for v in _nt["rules"].values()))
check("the report says t first and warns about eight tries",
      "t = mean against zero" in nulltest.render(_nt) and "eight tries" in nulltest.render(_nt))
check("events can be rendered", "event(s)" in nulltest.render_events(_nt, "doji") or "no events" in nulltest.render_events(_nt, "doji"))

# ---------------------------------------------------------------- watch

print("\nwatch — the readout")

import watch

_wroot = tempfile.mkdtemp(prefix="watch-")
B.to_csv(_series(_daily(260)), os.path.join(_wroot, "TST-1d.csv"))
_ro = watch.readout("TST", "1d", _wroot)
check("a symbol with bars reads out", _ro["status"] == "ok" and _ro["trend"] == "above" and _ro["rsi14"] is not None)
check("a symbol without bars says so", watch.readout("NOPE", "1d", _wroot)["status"] == "no bars")
B.to_csv(_series(three_gone), os.path.join(_wroot, "BAD-1d.csv"))
check("a blocked symbol gets its verdict, not readings", watch.readout("BAD", "1d", _wroot)["status"] == "blocked")
check("render says nothing predicts", "none predicts" in watch.render([_ro]))
shutil.rmtree(_wroot, ignore_errors=True)

# ---------------------------------------------------------------- aggregate

print("\naggregate — minute bars to sessions")

import aggregate

_ag_src = intraday.synth(6, effect=0.0)
_ag, _counts, _dropped = aggregate.aggregate(_ag_src)
check("one daily bar per session", len(_ag) == 6 and _ag.timeframe == "1d")
_first = [b for b in _ag_src.bars][:390]
check("open is the first bar's open and close the last bar's close",
      _ag[0].open == _first[0].open and _ag[0].close == _first[-1].close)
check("high and low span the session", _ag[0].high == max(b.high for b in _first) and _ag[0].low == min(b.low for b in _first))
check("volume is summed", _ag[0].volume == sum(b.volume for b in _first))
check("bar counts per session are recorded", all(v == 390 for v in _counts.values()))
check("provenance says what the closes are", "auction" in _ag["close_is"] if False else "auction" in _ag.provenance["close_is"])
check("the aggregated source is named", _ag.provenance["source"].endswith("-1m-aggregated"))
_half = B.Series("X", "1m", list(_ag_src.bars[:390 * 5]) + list(_ag_src.bars[390 * 5:390 * 5 + 200]), dict(PROV))
_ah, _c2, _d2 = aggregate.aggregate(_half, min_bars=312)
check("a short session is dropped only under --min-bars", len(_ah) == 5 and _d2 == 1 and len(aggregate.aggregate(_half)[0]) == 6)
check("a daily series is refused", _raises(ValueError, aggregate.aggregate, s70))
check("the aggregate passes barqc", barqc.inspect(_ag)["verdict"] != "blocked")

# ---------------------------------------------------------------- fetch, round 2

print("\nfetch — regular session")

_ext = [B.Bar(dt.datetime(2026, 1, 5, 8, 0, tzinfo=B.UTC), 1, 2, 0.5, 1.5, 1),    # 03:00 NY
        B.Bar(dt.datetime(2026, 1, 5, 15, 0, tzinfo=B.UTC), 1, 2, 0.5, 1.5, 1),   # 10:00 NY
        B.Bar(dt.datetime(2026, 1, 5, 21, 0, tzinfo=B.UTC), 1, 2, 0.5, 1.5, 1)]   # 16:00 NY — closed
_kept, _dropped = fetch.regular_session(_ext)
check("regular_session keeps 09:30-16:00 New York only", len(_kept) == 1 and _dropped == 2)
check("barqc passes the kept bar", barqc.check_calendar(_series(_kept, tf="1m"))["ok"] is not False)

# ---------------------------------------------------------------- cleanup

ledger.LEDGER = _real_ledger
shutil.rmtree(_tmp, ignore_errors=True)
check("the real ledger path was restored", ledger.LEDGER.endswith(os.path.join("out", "ledger.json")))
check("the real ledger was never written by the tests", H_before == ledger.load())

# ---------------------------------------------------------------- result

print()
if FAILURES:
    print(f"{len(FAILURES)} FAILED: {', '.join(FAILURES)}")
    sys.exit(1)
print("all checks passed")
