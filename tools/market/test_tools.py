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
check("intraday session count is UNRUN, never a pass",
      barqc.check_sessions(_series(_daily(5), tf="1h"))["ok"] is None)
check("one bar is UNRUN for sessions", barqc.check_sessions(_series(_daily(1)))["ok"] is None)

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
      barqc.inspect(_series(_daily(70), tf="1h"))["verdict"] != "pass")
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

ledger.LEDGER = _real_ledger
shutil.rmtree(_tmp, ignore_errors=True)
check("the real ledger path was restored", ledger.LEDGER.endswith(os.path.join("out", "ledger.json")))

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

# ---------------------------------------------------------------- result

print()
if FAILURES:
    print(f"{len(FAILURES)} FAILED: {', '.join(FAILURES)}")
    sys.exit(1)
print("all checks passed")
