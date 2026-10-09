#!/usr/bin/env python3
"""
test_edgelab.py — checks for the bench. Run: python3 test_edgelab.py

What is pinned here is what a wrong harness would get wrong without anyone
noticing: the fill arithmetic at both auctions, the per-side cost, the
leverage model, cash across weekends and holidays, the information sets at
both auctions, the leak check, the calendar on dates whose answer is known,
the placebo's determinism and what it preserves, the benchmark's window, and
the deflated Sharpe's fixed point.

Stdlib only, same posture as test_tools.py. Offline, and enforced: every
socket connection to anything but this machine is refused. Nothing is written
outside a temporary directory, and the bar files and trials.json are checked
unchanged at the end.
"""

import contextlib
import datetime as dt
import io
import json
import math
import os
import random
import shutil
import socket
import sys
import tempfile
from fractions import Fraction

# ------------------------------------------------------------------ offline
_real_connect = socket.socket.connect
_real_connect_ex = socket.socket.connect_ex


def _host(address):
    return address[0] if isinstance(address, tuple) else address


def _offline_connect(self, address):
    if _host(address) not in ("127.0.0.1", "::1", "localhost"):
        raise OSError(f"test_edgelab is offline: refused a connection to {address}")
    return _real_connect(self, address)


def _offline_connect_ex(self, address):
    if _host(address) not in ("127.0.0.1", "::1", "localhost"):
        raise OSError(f"test_edgelab is offline: refused a connection to {address}")
    return _real_connect_ex(self, address)


socket.socket.connect = _offline_connect
socket.socket.connect_ex = _offline_connect_ex

import bars as B
import barqc
import combine
import edgelab as E
import replay

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


def _close(a, b, tol=1e-12):
    return a is not None and b is not None and abs(a - b) <= tol


def _snapshot():
    """Names, sizes and mtimes of the bar files and trials.json — must not move."""
    out = {}
    for d in (os.path.join(HERE, "bars"),):
        if os.path.isdir(d):
            for n in sorted(os.listdir(d)):
                p = os.path.join(d, n)
                st = os.stat(p)
                out[p] = (st.st_size, st.st_mtime_ns)
    p = os.path.join(HERE, "trials.json")
    if os.path.exists(p):
        out[p] = (os.stat(p).st_size, os.stat(p).st_mtime_ns)
    return out


_BEFORE = _snapshot()
PROV = {"source": "test", "fetched_at": "2026-10-09T00:00:00+00:00", "adjusted": True}


def _ts(d):
    return dt.datetime(d.year, d.month, d.day, tzinfo=B.UTC)


def _bar(d, o, c, v=1e6):
    return B.Bar(_ts(d), float(o), max(o, c) * 1.001, min(o, c) * 0.999, float(c), float(v))


def _series(rows, symbol="T"):
    """rows: [(date, open, close)] or [(date, open, close, volume)]."""
    return B.Series(symbol, "1d", [_bar(*r) for r in rows], dict(PROV))


def _walk_series(start, end, seed=1, drift=0.0002, skip=(), symbol="T", vol=1e6):
    rng = random.Random(seed)
    px, rows = 100.0, []
    for i, d in enumerate(barqc.sessions_between(start, end)):
        o = px * (1 + rng.gauss(drift / 2, 0.004))
        c = o * (1 + rng.gauss(drift / 2, 0.008))
        px = c
        if d in skip:
            continue
        rows.append((d, o, c, vol))
    return _series(rows, symbol)


def _scripted(table, warmup=0, name="scripted"):
    """A factory for a rule that returns a fixed weight per (date, auction): a pure function."""
    def decide(v):
        return table.get((v.date, v.auction), 0.0)
    return lambda: E.Rule(name, decide, warmup)


def _fn(decide, warmup=0, name="local"):
    return lambda: E.Rule(name, decide, warmup)


QUIET = dict(placebo_draws=0, boot_draws=0, leak_samples=20)

# ================================================================== registry

print("registry — empty but for the benchmark and two test-only rules")

check("the registry holds exactly buy_and_hold and the two test-only rules",
      sorted(E.RULES) == ["buy_and_hold", "test_intraday_only", "test_overnight_only"],
      str(sorted(E.RULES)))
check("the two test rules are flagged test-only and buy_and_hold is not",
      E.RULES["test_overnight_only"]().test_only and E.RULES["test_intraday_only"]().test_only
      and not E.RULES["buy_and_hold"]().test_only)
check("a name cannot be registered twice", _raises(ValueError, E.register("buy_and_hold"), lambda v: 1.0))
check("an unknown rule is refused by name", _raises(KeyError, E.get_rule, "alpha_machine"))
_s70 = _walk_series(dt.date(2026, 1, 2), dt.date(2026, 4, 30))
check("a Rule instance is refused: the leak check needs a factory",
      _raises(TypeError, E.run, _s70, E.RULES["buy_and_hold"](), 1.0, 0.0, **QUIET))
check("each factory call builds a fresh Rule", E.RULES["buy_and_hold"]() is not E.RULES["buy_and_hold"]())

# ================================================================== fill math

print("\nfill math — a hand-computed series, both auctions")

# Four sessions whose opens gap away from the previous close, so a fill at the
# wrong price (previous close for a MOO, next open for a MOC) changes the answer.
FM = [(dt.date(2026, 3, 2), 100.0, 100.0), (dt.date(2026, 3, 3), 102.0, 101.0),
      (dt.date(2026, 3, 4), 99.0, 103.0), (dt.date(2026, 3, 5), 104.0, 104.0)]
_fm = _series(FM)
D2, D3, D4, D5 = (r[0] for r in FM)
_fm_table = {(D2, "close"): 1.0,     # overnight into 03-03: in
             (D3, "open"): 0.5,      # intraday 03-03: half
             (D3, "close"): 0.0,     # overnight into 03-04: out
             (D4, "open"): 1.0,      # intraday 03-04: in
             (D4, "close"): 1.0,     # overnight into 03-05: stay
             (D5, "open"): 0.0}      # intraday 03-05: out
_fm_r = E.run(_fm, _scripted(_fm_table), 10.0, 0.0, **QUIET)

# The same walk by hand, in exact fractions.
c = Fraction(10, 10000)
Eq = Fraction(1)
paid = Fraction(0)
n = 1 * Eq; paid += n * c; Eq -= n * c            # close 03-02: 0 -> 1 at the close (100)
Eq = Eq * Fraction(102, 100)                       # overnight: 100 -> open 102, fully in
n = Fraction(1, 2) * Eq; paid += n * c; Eq -= n * c  # open 03-03: 1 -> 0.5 at the open (102)
A, C = Eq / 2, Eq / 2
A = A * Fraction(101, 102)                         # intraday 03-03: 102 -> 101 on half
Eq = A + C
h = A / Eq
n = h * Eq; paid += n * c; Eq -= n * c             # close 03-03: h -> 0 at the close (101)
#                                                  # overnight 03-04: flat, cash at 0%
n = Eq; paid += n * c; Eq -= n * c                 # open 03-04: 0 -> 1 at the open (99)
Eq = Eq * Fraction(103, 99)                        # intraday 03-04: 99 -> 103
#                                                  # close 03-04: 1 -> 1, no trade
Eq = Eq * Fraction(104, 103)                       # overnight 03-05: 103 -> 104
n = Eq; paid += n * c; Eq -= n * c                 # open 03-05: 1 -> 0 at the open (104)
check("the final equity matches the hand walk to 1e-12",
      _close(_fm_r["strategy"]["final_equity"], float(Eq)),
      f"{_fm_r['strategy']['final_equity']!r} vs {float(Eq)!r}")
check("the cost paid matches the hand walk", _close(_fm_r["strategy"]["cost_paid"], float(paid)))
check("five sides traded, two of them entries from flat",
      _fm_r["strategy"]["sides"] == 5 and _fm_r["strategy"]["round_trips"] == 2,
      f"{_fm_r['strategy']['sides']} sides, {_fm_r['strategy']['round_trips']} entries")
check("the scored window is close(03-02) → close(03-05), three sessions",
      _fm_r["window"]["start_close"] == "2026-03-02" and _fm_r["window"]["sessions"] == 3)
_fm_legs = E.build_legs(_fm.bars, 0, 3, E.CashRate(rate=0.0))
check("the overnight leg is close[t-1] → open[t] and the intraday leg open[t] → close[t]",
      _close(_fm_legs.r_on[0], 102 / 100 - 1) and _close(_fm_legs.r_id[0], 101 / 102 - 1)
      and _close(_fm_legs.r_on[1], 99 / 101 - 1) and _close(_fm_legs.r_id[2], 104 / 104 - 1))
_fm_bh = E.run(_fm, "buy_and_hold", 10.0, 0.0, **QUIET)
check("buy-and-hold buys at the first CLOSE auction and holds: (1 - c) * C_last / C_first",
      _close(_fm_bh["benchmark"]["final_equity"], (1 - 0.001) * 104 / 100))

# A fractional weight held across auctions drifts; the book is put back to the
# declared weight at every auction, and that rebalance is a trade that costs.
_dr_table = {(D2, "close"): 0.5, (D3, "open"): 0.5, (D3, "close"): 0.5,
             (D4, "open"): 0.5, (D4, "close"): 0.5, (D5, "open"): 0.5}
_dr = E.run(_fm, _scripted(_dr_table), 10.0, 0.0, **QUIET)
Eq, paid, h = Fraction(1), Fraction(0), Fraction(0)
for ret_leg in (Fraction(102, 100), Fraction(101, 102), Fraction(99, 101), Fraction(103, 99),
                Fraction(104, 103), Fraction(104, 104)):
    n = abs(Fraction(1, 2) - h) * Eq                 # back to exactly half, whatever the drift
    if n:
        paid += n * c
        Eq -= n * c
    A, C = Eq / 2, Eq / 2
    A *= ret_leg
    Eq = A + C
    h = A / Eq
check("a fractional weight is rebalanced to its declared value at every auction, at a cost",
      _close(_dr["strategy"]["final_equity"], float(Eq)) and _close(_dr["strategy"]["cost_paid"], float(paid))
      and _dr["strategy"]["sides"] == 6, f"{_dr['strategy']['final_equity']!r} vs {float(Eq)!r}")

# The information set the ENGINE hands the view, probed directly: the leak
# check re-decides on the same number of closed bars the engine used, so an
# engine that gave the view one bar too many would pass it. This would not.
_probe_log = []


def _probe(v):
    _probe_log.append((v.auction, v.date, v[-1].ts.date() if len(v) else None, len(v),
                       v.open_today if v.auction == "close" else None))
    return 0.0


_pr_s = _walk_series(dt.date(2026, 1, 2), dt.date(2026, 2, 27), seed=31)
_pr_cal = E.Calendar(_pr_s.bars[0].ts.date(), _pr_s.bars[-1].ts.date())
E.decide_all(_pr_s, E.Rule("probe", _probe), _pr_cal, 0, len(_pr_s.bars) - 1)
_pr_dates = [b.ts.date() for b in _pr_s.bars]
_pr_ok = True
for auction, today, lastd, n, op in _probe_log:
    i = _pr_dates.index(today)
    _pr_ok &= n == i and (i == 0 or lastd == _pr_dates[i - 1])
    if auction == "close":
        _pr_ok &= op == _pr_s.bars[i].open
check("at both auctions the view's last bar is the previous session's, never today's",
      _pr_ok and len(_probe_log) == 2 * (len(_pr_s.bars) - 1), str(_probe_log[:3]))
check("the decisions alternate close, open — the close auction of t-1 before the open of t",
      [a for a, *_ in _probe_log[:4]] == ["close", "open", "close", "open"]
      and _probe_log[0][1] == _pr_dates[0] and _probe_log[1][1] == _pr_dates[1])

# ================================================================== per-side cost

print("\ncost — per side, a round trip is two sides")

FLAT = [(d, 100.0, 100.0) for d in barqc.sessions_between(dt.date(2026, 3, 2), dt.date(2026, 3, 9))]
_flat = _series(FLAT)
_rt = E.run(_flat, _scripted({(FLAT[0][0], "close"): 1.0}), 1.0, 0.0, **QUIET)
check("one round trip at 1 bp a side leaves (1 - 0.0001)^2: two sides, ~2 bp",
      _close(_rt["strategy"]["final_equity"], (1 - 1e-4) ** 2, 1e-15),
      repr(_rt["strategy"]["final_equity"]))
check("the round trip is two sides and one entry",
      _rt["strategy"]["sides"] == 2 and _rt["strategy"]["round_trips"] == 1)
check("the convention is stated in the result: per side, round trip twice",
      "PER SIDE" in _rt["conventions"]["cost"] and "round trip costs 2 bp" in _rt["conventions"]["cost"]
      and _rt["settings"]["round_trip_bps"] == 2.0)
_rt_txt = E.render(_rt)
check("the rendered output opens with the cost convention and names the other one",
      "COST CONVENTION  1 bp PER SIDE" in _rt_txt and "nulltest.py charges ONCE per round trip" in _rt_txt)
_rt0 = E.run(_flat, _scripted({(FLAT[0][0], "close"): 1.0}), 0.0, 0.0, **QUIET)
check("zero cost on a flat market is exactly flat", _rt0["strategy"]["final_equity"] == 1.0)
_on = E.run(_flat, "test_overnight_only", 1.0, 0.0, **QUIET)
_S = _on["window"]["sessions"]
check("overnight-only trades twice a session: one entry and one exit each",
      _on["strategy"]["sides"] == 2 * _S and _on["strategy"]["round_trips"] == _S)
check("and on a flat market loses exactly (1 - c)^(2 * sessions)",
      _close(_on["strategy"]["final_equity"], (1 - 1e-4) ** (2 * _S), 1e-14))
check("a negative cost is refused", _raises(ValueError, E.run, _flat, "buy_and_hold", -1.0, 0.0, **QUIET))

# ================================================================== leverage model

print("\nleverage — a modelled daily-reset fund, labelled as a model")

LV = [(dt.date(2026, 3, 3), 100.0, 100.0), (dt.date(2026, 3, 4), 101.0, 98.98)]   # Tue → Wed
_lv = _series(LV)
_lv_legs = E.build_legs(_lv.bars, 0, 1, E.CashRate(rate=0.03), leverage=3, expense_ratio=0.01)
r_on, r_id = 101 / 100 - 1, 98.98 / 101 - 1
delta = (1 + 0.01 + 2 * 0.03) ** (-1 / 365)
check("overnight: (1 + 3 r_on) less one day of expense + 2 x cash",
      _close(_lv_legs.i_on[0], (1 + 3 * r_on) * delta - 1))
check("intraday: 3 r_id (1 + r_on) / (1 + 3 r_on) — the fund reset at the previous close",
      _close(_lv_legs.i_id[0], 3 * r_id * (1 + r_on) / (1 + 3 * r_on)))
check("close-to-close the two legs compound to exactly 3 x the session return, less the drag",
      _close((1 + _lv_legs.i_on[0]) * (1 + _lv_legs.i_id[0]), (1 + 3 * (98.98 / 100 - 1)) * delta))
_lv1 = E.build_legs(_lv.bars, 0, 1, E.CashRate(rate=0.03), leverage=1)
check("at 1x the instrument is the underlying, untouched",
      _lv1.i_on == _lv1.r_on and _lv1.i_id == _lv1.r_id)
LVW = [(dt.date(2026, 3, 6), 100.0, 100.0), (dt.date(2026, 3, 9), 100.0, 100.0)]  # Fri → Mon
_lvw = E.build_legs(_series(LVW).bars, 0, 1, E.CashRate(rate=0.03), 3, 0.01)
check("a weekend overnight leg carries three days of drag",
      _close(_lvw.i_on[0], (1.07) ** (-3 / 365) - 1) and _lvw.days == [3])
CRASH = [(dt.date(2026, 3, 3), 100.0, 100.0), (dt.date(2026, 3, 4), 60.0, 61.0)]
_crash = E.build_legs(_series(CRASH).bars, 0, 1, E.CashRate(rate=0.0), 3, 0.01)
check("a 40% gap wipes out a modelled 3x fund, and says so",
      _crash.i_on == [-1.0] and _crash.wiped == ["2026-03-04"])
_lv_run = E.run(_s70, "buy_and_hold", 1.0, 0.03, leverage=3, expense_ratio=0.0095, **QUIET)
_lv_txt = E.render(_lv_run)
check("a leveraged run says MODEL, NOT DATA in its output",
      "A MODEL, NOT DATA" in _lv_txt and "A MODEL, NOT DATA" in _lv_run["conventions"]["instrument"])
check("a leveraged run reports a leveraged buy-and-hold reference beside the 1x benchmark",
      _lv_run["leveraged_buy_and_hold"] is not None
      and _close(_lv_run["leveraged_buy_and_hold"]["final_equity"], _lv_run["strategy"]["final_equity"]))
check("weight 1 in the 3x fund is effective exposure 3",
      _close(_lv_run["strategy"]["mean_exposure"], 3.0))
check("a leveraged variant without a stated expense ratio is refused",
      _raises(ValueError, E.run, _s70, "buy_and_hold", 1.0, 0.03, leverage=3, **QUIET))
check("leverage above 3 is refused",
      _raises(ValueError, E.run, _s70, "buy_and_hold", 1.0, 0.03, leverage=4, expense_ratio=0.01, **QUIET))

# ================================================================== cash

print("\ncash — calendar days, on the overnight leg, across a weekend and a holiday")

CASHD = [dt.date(2026, 1, 14), dt.date(2026, 1, 15), dt.date(2026, 1, 16),   # Wed Thu Fri
         dt.date(2026, 1, 20), dt.date(2026, 1, 21), dt.date(2026, 1, 22)]   # MLK Monday 01-19 shut
_cash = _series([(d, 100.0, 100.0) for d in CASHD])
_cl = E.build_legs(_cash.bars, 0, 5, E.CashRate(rate=0.05), cal=E.Calendar(CASHD[0], CASHD[-1]))
check("overnight legs span 1, 1, 4 (weekend + holiday), 1, 1 calendar days", _cl.days == [1, 1, 4, 1, 1],
      str(_cl.days))
check("the leg across the weekend and MLK day accrues four days: 1.05^(4/365) - 1",
      _close(_cl.g_on[2], 1.05 ** (4 / 365) - 1))
check("a holiday that the calendar knows is not a gap leg", _cl.gap == [False] * 5)
_flat_rule = _fn(lambda v: 0.0, name="cash_only")
_cash_r = E.run(_cash, _flat_rule, 1.0, 0.05, **QUIET)
check("all cash from 01-14 to 01-22 earns exactly 1.05^(8/365)",
      _close(_cash_r["strategy"]["final_equity"], 1.05 ** (8 / 365)),
      repr(_cash_r["strategy"]["final_equity"]))
_cash_p = E.walk([0.0] * 5, [0.0] * 5, _cl.i_on, _cl.i_id, _cl.g_on, 0.0, detail=True)
check("intraday legs accrue nothing: each open equals that session's close for cash",
      all(o == c for o, c in zip(_cash_p["opens"], _cash_p["closes"])))
_inv = E.run(_cash, "buy_and_hold", 0.0, 0.05, **QUIET)
check("a fully invested book earns no cash yield", _inv["strategy"]["final_equity"] == 1.0)
_dated = E.CashRate(dated=[(dt.date(2026, 1, 1), 0.04), (dt.date(2026, 1, 16), 0.06)])
_dl = E.build_legs(_cash.bars, 0, 5, _dated)
check("a dated series applies the rate in force at the start of the leg",
      _close(_dl.g_on[1], 1.04 ** (1 / 365) - 1) and _close(_dl.g_on[2], 1.06 ** (4 / 365) - 1))
check("a date before the dated series starts is refused, not extrapolated",
      _raises(ValueError, E.CashRate(dated=[(dt.date(2026, 1, 15), 0.04)]).at, dt.date(2026, 1, 14)))
check("a rate that looks like a percent is refused", _raises(ValueError, E.CashRate, rate=5.0))
_tmpd = tempfile.mkdtemp(prefix="edgelab-")
_rates_p = os.path.join(_tmpd, "rates.csv")
with open(_rates_p, "w") as f:
    f.write("date,rate\n2026-01-01,0.04\n2026-01-16,0.06\n")
_parsed = E.CashRate.parse(_rates_p)
check("a dated series loads from a date,rate CSV", _parsed.at(dt.date(2026, 1, 20)) == 0.06
      and _parsed.at(dt.date(2026, 1, 15)) == 0.04)
check("a constant parses from text", E.CashRate.parse("0.03").at(dt.date(2000, 1, 3)) == 0.03)

# ================================================================== information sets

print("\ninformation sets — the view raises at both auctions")

_cal70 = E.Calendar(_s70.bars[0].ts.date(), _s70.bars[-1].ts.date())
_t = 10
_vo = E.View(_s70.bars, _t, "open", _s70.bars[_t].ts.date(), None, _cal70)
check("at the open auction the view has the closed bars only", len(_vo) == _t and _vo[-1] is _s70.bars[_t - 1])
check("at the open auction today's bar is out of reach", _raises(E.LookAhead, lambda: _vo[_t]))
check("at the open auction open_today raises — it is the price being set",
      _raises(E.LookAhead, lambda: _vo.open_today))
check("today's close, high, low and volume raise at the open auction",
      all(_raises(E.LookAhead, lambda a=a: getattr(_vo, a))
          for a in ("close_today", "high_today", "low_today", "volume_today")))
_vc = E.View(_s70.bars, _t, "close", _s70.bars[_t].ts.date(), _s70.bars[_t].open, _cal70)
check("at the close auction open_today is today's open", _vc.open_today == _s70.bars[_t].open)
check("at the close auction today's close, high, low and volume raise",
      all(_raises(E.LookAhead, lambda a=a: getattr(_vc, a))
          for a in ("close_today", "high_today", "low_today", "volume_today")))
check("at the close auction today's bar is still out of reach by index", _raises(E.LookAhead, lambda: _vc[_t]))
check("a negative index before the start raises", _raises(E.LookAhead, lambda: _vc[-_t - 1]))
check("a slice clamps to the closed bars", len(_vc[-500:]) == _t and _vc[-500:][-1] is _s70.bars[_t - 1])
check("closes(n) returns at most n closed closes", _vc.closes(3) == [b.close for b in _s70.bars[_t - 3:_t]])
check("a view cannot be given a new attribute to smuggle state",
      _raises(AttributeError, setattr, _vc, "memo", 1))
check("the view's calendar facts are today's, and next_cal the next scheduled session",
      _vc.cal.date == _s70.bars[_t].ts.date() and _vc.next_cal.date == _cal70.next_session(_vc.date))


def _cheat_open(v):
    return 1.0 if v.auction == "open" and v.open_today > v[-1].close else 0.0


def _cheat_close(v):
    return 1.0 if v.auction == "close" and v.close_today > v.open_today else 0.0


def _cheat_index(v):
    return 1.0 if v[len(v)].close > 0 else 0.0


check("a rule that reads today's open at the OPEN auction is stopped (LookAhead)",
      _raises(E.LookAhead, E.run, _s70, _fn(_cheat_open), 1.0, 0.0, **QUIET))
check("a rule that reads today's close at the CLOSE auction is stopped (LookAhead)",
      _raises(E.LookAhead, E.run, _s70, _fn(_cheat_close), 1.0, 0.0, **QUIET))
check("a rule that indexes today's bar is stopped at either auction",
      _raises(E.LookAhead, E.run, _s70, _fn(_cheat_index), 1.0, 0.0, **QUIET))


def _gap_rule(v):
    # legitimate at the close: today's open against yesterday's close is known by 15:50
    if v.auction == "close":
        return 1.0 if len(v) and v.open_today < v[-1].close else 0.0
    return 0.0


_gap_r = E.run(_s70, _fn(_gap_rule), 1.0, 0.0, **QUIET)
check("a rule that uses today's open at the close auction is allowed, and passes the leak check",
      _gap_r["leak_check"]["checked"] > 0 and _gap_r["leak_check"]["differences"] == [])
for _bad in (1.5, -0.1, float("nan"), "abc", None):
    check(f"a weight of {_bad!r} is refused, never clamped",
          _raises(ValueError, E.run, _s70, _fn(lambda v, b=_bad: b), 1.0, 0.0, **QUIET))

# ================================================================== leak check

print("\nleak check — the future physically removed, the rule rebuilt per sample")

_lk_series = _walk_series(dt.date(2025, 1, 2), dt.date(2025, 12, 31), seed=7)
for name in ("buy_and_hold", "test_overnight_only", "test_intraday_only"):
    _lr = E.run(_lk_series, name, 1.0, 0.0, **dict(QUIET, leak_samples=60))
    check(f"{name} is clean", _lr["leak_check"]["checked"] > 0 and _lr["leak_check"]["differences"] == [],
          str(_lr["leak_check"]["differences"][:2]))


def _momentum(v):
    if len(v) < 2:
        return 0.0
    return 1.0 if v[-1].close > v[-2].close else 0.0


_lr = E.run(_lk_series, _fn(_momentum), 1.0, 0.0, **dict(QUIET, leak_samples=60))
check("a legitimate price rule is clean at both auctions",
      _lr["leak_check"]["differences"] == [] and _lr["leak_check"]["open"] > 0
      and _lr["leak_check"]["close"] > 0)


def _peek_close(v):
    # through the private list: today's close, at the close auction
    if v.auction != "close":
        return 0.0
    b = v._bars[len(v)]
    return 1.0 if b.close > b.open else 0.0


def _peek_open(v):
    # through the private list: today's whole bar, at the open auction
    if v.auction != "open":
        return 0.0
    b = v._bars[len(v)]
    return 1.0 if b.close > b.open else 0.0


_pc = E.run(_lk_series, _fn(_peek_close), 1.0, 0.0, **dict(QUIET, leak_samples=60))
check("a rule that peeks at today's close at the CLOSE auction is caught",
      len(_pc["leak_check"]["differences"]) > 0
      and all(d["auction"] == "close" for d in _pc["leak_check"]["differences"]),
      str(len(_pc["leak_check"]["differences"])))
_po = E.run(_lk_series, _fn(_peek_open), 1.0, 0.0, **dict(QUIET, leak_samples=60))
check("a rule that peeks at today's bar at the OPEN auction is caught",
      len(_po["leak_check"]["differences"]) > 0
      and all(d["auction"] == "open" for d in _po["leak_check"]["differences"]))


def _peek_tomorrow(v):
    # the classic: tomorrow's close, through the private list
    n = len(v)
    if n + 1 >= len(v._bars):
        return 0.0
    return 1.0 if v._bars[n + 1].close > v._bars[n].close else 0.0


_pt = E.run(_lk_series, _fn(_peek_tomorrow), 1.0, 0.0, **dict(QUIET, leak_samples=60))
check("a rule that reads tomorrow's bar is caught", len(_pt["leak_check"]["differences"]) > 0)


class _Counter:
    calls = 0


def _stateful(v):
    _Counter.calls += 1
    return 1.0 if _Counter.calls % 5 == 0 else 0.0


_st = E.run(_lk_series, _fn(_stateful), 1.0, 0.0, **dict(QUIET, leak_samples=60))
check("a rule that keeps state between calls is caught", len(_st["leak_check"]["differences"]) > 0)


def _memo_factory():
    # memoises a table from the FULL private bar list on its first call
    memo = {}

    def decide(v):
        if "t" not in memo:
            memo["t"] = [b.close for b in v._bars]
        n = len(v)
        return 1.0 if n + 1 < len(memo["t"]) and memo["t"][n + 1] > memo["t"][n] else 0.0
    return E.Rule("memo", decide, 0)


_mm = E.run(_lk_series, _memo_factory, 1.0, 0.0, **dict(QUIET, leak_samples=60))
check("a memoised look-ahead is caught because the check rebuilds the rule per sample",
      len(_mm["leak_check"]["differences"]) > 0)
check("a leak shows in the rendered output as NOT A RESULT", "NOT A RESULT" in E.render(_mm))


def _sticky(v):
    # enters on an up close and then stays in by READING what it holds: legitimate
    if v.held > 0:
        return 1.0
    return 1.0 if len(v) >= 2 and v[-1].close > v[-2].close * 1.01 else 0.0


_sk = E.run(_lk_series, _fn(_sticky), 1.0, 0.0, **dict(QUIET, leak_samples=60))
check("a rule that reads view.held is checked with the weight the run held, and is clean",
      _sk["strategy"]["round_trips"] >= 1 and _sk["leak_check"]["differences"] == [],
      str(_sk["leak_check"]["differences"][:2]))
check("the leak check re-decides every point where the decision changed",
      _po["leak_check"]["checked"] >= 60)

# ================================================================== calendar

print("\ncalendar — the scheduled one, on dates whose answer is known")

CAL = E.Calendar(dt.date(2018, 1, 2), dt.date(2026, 12, 31))
f = CAL.facts(dt.date(2020, 3, 31))
check("the last session of 2020-03 is 2020-03-31: day -1, a quarter end",
      CAL.last_session(2020, 3) == dt.date(2020, 3, 31) and f.month_ordinal_from_end == -1
      and f.is_month_end and f.is_quarter_end and f.month_ordinal == f.month_sessions == 22)
check("2018-03's last weekday is Good Friday, so its last session is Thursday 03-29",
      CAL.last_session(2018, 3) == dt.date(2018, 3, 29)
      and CAL.facts(dt.date(2018, 3, 29)).is_quarter_end
      and CAL.facts(dt.date(2018, 3, 29)).pre_holiday_rank == 1)
check("2021-05's last weekday is Memorial Day, so its last session is Friday 05-28",
      CAL.last_session(2021, 5) == dt.date(2021, 5, 28)
      and CAL.facts(dt.date(2021, 5, 28)).month_ordinal_from_end == -1)
check("the third Friday of 2022-04 is the 15th", E.third_friday(2022, 4) == dt.date(2022, 4, 15))
check("opex 2022-04 falls on Good Friday, so it is Thursday 2022-04-14",
      CAL.opex(2022, 4) == dt.date(2022, 4, 14) and CAL.facts(dt.date(2022, 4, 14)).is_opex
      and CAL.facts(dt.date(2022, 4, 14)).opex_offset == 0
      and CAL.facts(dt.date(2022, 4, 13)).opex_offset == -1)
check("opex 2026-06 falls on Juneteenth, so it is Thursday 2026-06-18",
      CAL.opex(2026, 6) == dt.date(2026, 6, 18))
check("an ordinary opex is the third Friday: 2026-09-18", CAL.opex(2026, 9) == dt.date(2026, 9, 18)
      and CAL.facts(dt.date(2026, 9, 21)).opex_offset == 1)
check("the session before Thanksgiving 2026 is pre-holiday rank 1, the one before that rank 2",
      CAL.facts(dt.date(2026, 11, 25)).pre_holiday_rank == 1
      and CAL.facts(dt.date(2026, 11, 24)).pre_holiday_rank == 2
      and CAL.facts(dt.date(2026, 11, 25)).holiday_ahead == dt.date(2026, 11, 26))
check("the Friday after Thanksgiving is post-holiday rank 1",
      CAL.facts(dt.date(2026, 11, 27)).post_holiday_rank == 1)
check("the Friday before MLK day is pre-holiday rank 1, and its overnight leg spans 4 days",
      CAL.facts(dt.date(2026, 1, 16)).pre_holiday_rank == 1
      and CAL.facts(dt.date(2026, 1, 16)).days_to_next_session == 4)
check("an ordinary Friday is not pre-holiday when no holiday is near",
      CAL.facts(dt.date(2026, 3, 6)).pre_holiday_rank is None)
check("a weekend is not a holiday: an ordinary Monday spans 3 days and is not post-holiday",
      CAL.facts(dt.date(2026, 3, 9)).days_since_prev_session == 3
      and CAL.facts(dt.date(2026, 3, 9)).post_holiday_rank is None)
check("year end is the last session of December", CAL.facts(dt.date(2025, 12, 31)).is_year_end)
check("a non-session date is refused, not guessed", _raises(ValueError, CAL.facts, dt.date(2026, 1, 19)))

# A DATA HOLE: 2026-03-04 (the 3rd session of March) missing from the file.
_hole = _walk_series(dt.date(2026, 1, 2), dt.date(2026, 4, 30), seed=3, skip={dt.date(2026, 3, 4)})
_hr = E.calendar_report(_hole)
check("a session the file lacks is reported as a DATA HOLE",
      _hr["holes"] == ["2026-03-04"] and _hr["missing"][0]["class"] == "DATA HOLE")
check("the overnight leg across the hole is named", _hr["gap_legs"][0]["into"] == "2026-03-05"
      and _hr["gap_legs"][0]["spans"] == ["2026-03-04"])
check("bar-counted ordinals would shift in that month, and the report says why",
      _hr["ordinal_shifts"]["by_cause"].get("DATA HOLE", 0) > 0)


def _fifth_overnight(v):
    # in overnight only INTO the 5th scheduled session of a month
    return 1.0 if v.auction == "close" and v.next_cal.month_ordinal == 5 else 0.0


_hcal = E.Calendar(_hole.bars[0].ts.date(), _hole.bars[-1].ts.date())
_hs0 = 0
_hw_on, _hw_id, _ = E.decide_all(_hole, E.Rule("fifth", _fifth_overnight), _hcal, _hs0, len(_hole.bars) - 1)
_hdates = [b.ts.date() for b in _hole.bars[1:]]
_in = [d for d, w in zip(_hdates, _hw_on) if w > 0 and d.month == 3]
check("a missing bar does not shift the window: March's 5th session is still 03-06, not 03-09",
      _in == [dt.date(2026, 3, 6)], str(_in))
check("the leg across the hole is marked as a gap leg in the run",
      E.run(_hole, "buy_and_hold", 1.0, 0.0, **QUIET)["window"]["gap_legs_in_window"] == ["2026-03-05"])

_carter = _walk_series(dt.date(2025, 1, 2), dt.date(2025, 2, 28), seed=4, skip={dt.date(2025, 1, 9)})
_cr = E.calendar_report(_carter)
check("a known unscheduled closure is labelled as one, not as a hole",
      _cr["holes"] == [] and _cr["closures"] == ["2025-01-09"]
      and "Carter" in _cr["missing"][0]["class"])
_mid = _walk_series(dt.date(2026, 1, 2), dt.date(2026, 3, 18), seed=5)
_mr = E.calendar_report(_mid)
check("a file that ends mid-month: a bar-counted 'last session of the month' is flagged",
      any("ends mid-month" in k for k in _mr["ordinal_shifts"]["by_cause"]))
_part = list(_walk_series(dt.date(2026, 1, 2), dt.date(2026, 2, 27), seed=6).bars)
_part[-1] = B.Bar(_part[-1].ts, _part[-1].open, _part[-1].high, _part[-1].low, _part[-1].close, 1e5)
_pr = E.calendar_report(B.Series("T", "1d", _part, dict(PROV)))
check("a final bar with a tenth of the usual volume is flagged as a possible partial session",
      _pr["final_bar"]["suspect_partial"] and _close(_pr["final_bar"]["volume_ratio"], 0.1))
check("a normal final bar is not flagged", not _mr["final_bar"]["suspect_partial"])

_bad = list(_s70.bars)
_bad.append(B.Bar(dt.datetime(2026, 5, 2, tzinfo=B.UTC), 100.0, 101.0, 99.0, 100.0, 1e6))  # a Saturday
check("a series barqc blocks is refused before a single leg is walked",
      _raises(E.Blocked, E.run, B.Series("T", "1d", _bad, dict(PROV)), "buy_and_hold", 1.0, 0.0, **QUIET))

# ================================================================== window

print("\nwindow — strategy and benchmark from the same close, over the same legs")

_win = _walk_series(dt.date(2024, 1, 2), dt.date(2025, 6, 30), seed=8)
_bh = E.run(_win, "buy_and_hold", 5.0, 0.03, **QUIET)
keys = ("final_equity", "total_return", "cagr", "volatility", "sharpe", "sortino", "max_drawdown",
        "peak", "trough", "recovered", "cost_paid", "sides", "years")
check("buy_and_hold run as a rule equals the benchmark to the last digit",
      all(_bh["strategy"][k] == _bh["benchmark"][k] for k in keys),
      str([k for k in keys if _bh["strategy"][k] != _bh["benchmark"][k]]))
_w30 = E.run(_win, _fn(lambda v: 1.0, warmup=30, name="bh30"), 5.0, 0.03, **QUIET)
_b = _win.bars
check("a 30-bar warm-up moves BOTH starts to the close of bar 30",
      _w30["window"]["start_close"] == _b[30].ts.date().isoformat()
      and _w30["window"]["first_session"] == _b[31].ts.date().isoformat()
      and _w30["window"]["benchmark_first_leg"] == _w30["window"]["first_session"])
check("the benchmark is bought at bar 30's close, never at bar 0's",
      _close(_w30["benchmark"]["final_equity"], (1 - 5e-4) * _b[-1].close / _b[30].close))
check("and the warmed-up buy-and-hold still equals it exactly",
      _w30["strategy"]["final_equity"] == _w30["benchmark"]["final_equity"]
      and _w30["strategy"]["sharpe"] == _w30["benchmark"]["sharpe"])
_f30 = E.run(_win, _fn(lambda v: 0.0, warmup=30, name="flat30"), 5.0, 0.0, **QUIET)
check("a flat rule with a warm-up is compared with buy-and-hold from the same bar",
      _f30["benchmark"]["final_equity"] == _w30["benchmark"]["final_equity"]
      and _f30["strategy"]["final_equity"] == 1.0)
_st = E.run(_win, "buy_and_hold", 5.0, 0.0, start=dt.date(2025, 1, 2), **QUIET)
check("--start scores from the close before the first session on or after it",
      _st["window"]["start_close"] == "2024-12-31" and _st["window"]["first_session"] == "2025-01-02")
_en = E.run(_win, "buy_and_hold", 5.0, 0.0, end=dt.date(2025, 3, 31), **QUIET)
check("--end stops at the last session on or before it", _en["window"]["last_session"] == "2025-03-31")
_late = E.run(_win, _fn(lambda v: 1.0, warmup=300, name="bh300"), 5.0, 0.0, start=dt.date(2024, 2, 1), **QUIET)
check("a warm-up longer than the gap before --start pushes the start later, never earlier",
      _late["window"]["start_close"] == _b[300].ts.date().isoformat())

# ================================================================== metrics

print("\nmetrics — they add up")

_cal_rule = _fn(lambda v: (1.0 if v.next_cal.month_ordinal <= 2 else 0.0) if v.auction == "close"
                else (0.5 if v.cal.month_ordinal_from_end == -1 else 0.0), name="calendar_test")
_m = E.run(_win, _cal_rule, 2.0, 0.03, **QUIET)
_yr = _m["per_year"]
_prod = 1.0
for y in _yr:
    _prod *= 1 + y["strategy"]
check("per-year returns compound to the total", _close(_prod, _m["strategy"]["final_equity"], 1e-12))
check("per-year sides add up to the total", sum(y["sides"] for y in _yr) == _m["strategy"]["sides"])
_h = _m["halves"]
_split = (dt.date.fromisoformat(_m["window"]["start_close"])
          + dt.timedelta(days=(dt.date.fromisoformat(_m["window"]["last_session"])
                               - dt.date.fromisoformat(_m["window"]["start_close"])).days // 2))
_scored = [b.ts.date() for b in _win.bars[1:]]
_n_first = sum(1 for d in _scored if d <= _split)
check("the date midpoint and the bar midpoint differ on this window, so the next check means something",
      _n_first != len(_scored) // 2, f"{_n_first} vs {len(_scored) // 2}")
check("the halves split at the DATE midpoint: the first half is every session on or before it",
      _h["split_date"] == _split.isoformat() and _h["first"]["sessions"] == _n_first
      and _h["second"]["sessions"] == len(_scored) - _n_first)
check("the two halves compound to the whole",
      _close((1 + _h["first"]["strategy"]["return"]) * (1 + _h["second"]["strategy"]["return"]),
             _m["strategy"]["final_equity"], 1e-12)
      and _close((1 + _h["first"]["benchmark"]["return"]) * (1 + _h["second"]["benchmark"]["return"]),
                 _m["benchmark"]["final_equity"], 1e-12))
check("exposure counts legs: 0.5 intraday weights count as exposed legs, mean exposure is lower",
      _m["strategy"]["mean_exposure"] < _m["strategy"]["exposure_share"])
_mz = E.run(_win, _cal_rule, 0.0, 0.03, **QUIET)
check("at zero cost the gross and net paths are the same path",
      _mz["strategy"]["final_equity"] == _mz["strategy"]["gross_final_equity"])
check("cost makes the net path worse than the gross one",
      _m["strategy"]["final_equity"] < _m["strategy"]["gross_final_equity"])
_on_m = E.run(_win, "test_overnight_only", 1.0, 0.0, **QUIET)
check("overnight-only is exposed on every overnight leg and no intraday one",
      _on_m["strategy"]["exposure_share"] == 0.5 and _on_m["strategy"]["exposure_share_overnight"] == 1.0
      and _on_m["strategy"]["exposure_share_intraday"] == 0.0)
_marks = [(dt.date(2026, 1, 2), "close", 1.0), (dt.date(2026, 1, 5), "open", 1.2),
          (dt.date(2026, 1, 5), "close", 0.9), (dt.date(2026, 1, 6), "open", 1.0),
          (dt.date(2026, 1, 6), "close", 1.3)]
_dd = E.drawdown(_marks)
check("max drawdown is peak-to-trough with its dates and recovery",
      _close(_dd["max_drawdown"], 0.9 / 1.2 - 1) and _dd["peak"] == "2026-01-05 open"
      and _dd["trough"] == "2026-01-05 close" and _dd["recovered"] == "2026-01-06 close")
check("and agrees with replay.max_drawdown",
      _close(_dd["max_drawdown"], replay.max_drawdown([m[2] for m in _marks])))
check("the reported Sharpe is in excess of the cash rate",
      _close(_m["strategy"]["sharpe"],
             replay._stats([r - g for r, g in zip(E.session_returns(
                 E.walk(*E.decide_all(_win, _cal_rule(), E.Calendar(_win.bars[0].ts.date(), _win.bars[-1].ts.date()),
                                      0, len(_win.bars) - 1)[:2],
                        *(lambda L: (L.i_on, L.i_id, L.g_on))(E.build_legs(_win.bars, 0, len(_win.bars) - 1,
                                                                           E.CashRate(rate=0.03))),
                        2e-4)["closes"]),
                 E.build_legs(_win.bars, 0, len(_win.bars) - 1, E.CashRate(rate=0.03)).g_on)], 252)["sharpe"]))

# ================================================================== decomposition

print("\ndecomposition — the two legs multiply to the whole, through the rule path too")

_dc = E.decompose(_win)
check("overnight x intraday compounds to the close-to-close whole",
      _close((1 + _dc["whole"]["overnight"]) * (1 + _dc["whole"]["intraday"]), 1 + _dc["whole"]["whole"])
      and _close(_dc["whole"]["whole"], _dc["close_to_close_check"], 1e-12))
_z = dict(QUIET)
_on0 = E.run(_win, "test_overnight_only", 0.0, 0.0, **_z)
_id0 = E.run(_win, "test_intraday_only", 0.0, 0.0, **_z)
_bh0 = E.run(_win, "buy_and_hold", 0.0, 0.0, **_z)
check("test_overnight_only at zero cost and cash IS the overnight leg",
      _close(_on0["strategy"]["total_return"], _dc["whole"]["overnight"], 1e-12))
check("test_intraday_only at zero cost and cash IS the intraday leg",
      _close(_id0["strategy"]["total_return"], _dc["whole"]["intraday"], 1e-12))
check("buy_and_hold at zero cost IS the whole",
      _close(_bh0["strategy"]["total_return"], _dc["whole"]["whole"], 1e-12))
check("the halves of the decomposition compound to the whole",
      _close((1 + _dc["first_half"]["overnight"]) * (1 + _dc["second_half"]["overnight"]),
             1 + _dc["whole"]["overnight"], 1e-12))

# ================================================================== placebo

print("\nplacebo — seeded, and it keeps what it claims to keep")

_pl_legs = E.build_legs(_win.bars, 0, len(_win.bars) - 1, E.CashRate(rate=0.03))
_pl_cal = E.Calendar(_win.bars[0].ts.date(), _win.bars[-1].ts.date())
_pw_on, _pw_id, _ = E.decide_all(_win, _cal_rule(), _pl_cal, 0, len(_win.bars) - 1)
_years = (_pl_legs.dates[-1] - _win.bars[0].ts.date()).days / 365.25
_p1 = E.placebo(_pw_on, _pw_id, _pl_legs, 2e-4, _years, "shift", 50, seed=11)
_p2 = E.placebo(_pw_on, _pw_id, _pl_legs, 2e-4, _years, "shift", 50, seed=11)
_p3 = E.placebo(_pw_on, _pw_id, _pl_legs, 2e-4, _years, "shift", 50, seed=12)
check("the same seed gives the same placebo, draw for draw",
      _p1["null_sharpe"] == _p2["null_sharpe"] and _p1["p_sharpe"] == _p2["p_sharpe"]
      and _p1["p_cagr"] == _p2["p_cagr"])
check("a different seed gives a different placebo", _p1["null_sharpe"] != _p3["null_sharpe"])
_b1 = E.placebo(_pw_on, _pw_id, _pl_legs, 2e-4, _years, "blocks", 50, seed=11)
_b2 = E.placebo(_pw_on, _pw_id, _pl_legs, 2e-4, _years, "blocks", 50, seed=11)
check("the block placebo is deterministic under its seed too", _b1["null_cagr"] == _b2["null_cagr"])
check("the observed numbers the placebo compares are the ones reported",
      _close(_p1["observed_sharpe"], E.run(_win, _cal_rule, 2.0, 0.03, **QUIET)["strategy"]["sharpe"], 0)
      and _close(_p1["observed_cagr"], _m["strategy"]["cagr"], 0))
_states = list(zip(_pw_on, _pw_id))


def _profile(st):
    blocks, gaps, first = E._segments(st)
    return (sum(1 for s in st if s[0] > 0), sum(1 for s in st if s[1] > 0),
            sorted(len(b) for b in blocks), sorted(len(g) for g in gaps), first)


_rng = random.Random(5)
_ok_shift = _ok_blocks = True
for _ in range(25):
    sh = E.placebo_states(_states, "shift", _rng)
    bl = E.placebo_states(_states, "blocks", _rng)
    _ok_shift &= sorted(sh) == sorted(_states) and len(sh) == len(_states)
    _ok_blocks &= _profile(bl) == _profile(_states) and len(bl) == len(_states)
    _ok_blocks &= sorted(tuple(b) for b in E._segments(bl)[0]) == sorted(tuple(b) for b in E._segments(_states)[0])
check("a circular shift keeps every session state, so every exposed leg of each kind", _ok_shift)
check("the block placebo keeps the exposed legs of each kind, every block intact, every gap length",
      _ok_blocks)
check("the placebo actually moves the exposure",
      E.placebo_states(_states, "shift", random.Random(1)) != _states
      and E.placebo_states(_states, "blocks", random.Random(1)) != _states)
_bhp = E.placebo([1.0] * 20, [1.0] * 20, E.build_legs(_win.bars, 0, 20, E.CashRate(rate=0.0)),
                 0.0, 0.1, "shift", 10, 0)
check("an exposure with no timing is degenerate: no p-value, said so",
      _bhp["degenerate"] and _bhp["p_sharpe"] is None)
_full = E.run(_win, _cal_rule, 2.0, 0.03, placebo_draws=40, placebo_method="both", boot_draws=0,
              leak_samples=20)
check("with both placebos the conservative reading is the larger p",
      _full["placebo_conservative"]["p_sharpe"] == max(_full["placebo"]["shift"]["p_sharpe"],
                                                        _full["placebo"]["blocks"]["p_sharpe"]))
check("a p-value is (1 + hits) / (1 + draws), never zero",
      _full["placebo"]["shift"]["p_sharpe"] >= 1 / 41)

# ================================================================== deflated sharpe

print("\ndeflated Sharpe — against the benchmark, with the trial count as an argument")

T, N, v = 5000, 40, 1 / 4999
sr0 = combine.expected_max_sharpe(N, v)
_d = E.deflated_sharpe_vs(0.03 + sr0, 0.03, T, N)
check("observed Sharpe = benchmark + expected best-of-N under the null gives exactly 0.5",
      _close(_d["dsr"], 0.5, 1e-12) and _close(_d["sr0"], sr0, 0), str(_d))
check("a higher observed Sharpe gives a higher probability",
      E.deflated_sharpe_vs(0.05 + sr0, 0.03, T, N)["dsr"] > 0.5 > E.deflated_sharpe_vs(0.01 + sr0, 0.03, T, N)["dsr"])
check("against a zero benchmark it is combine.deflated_sharpe exactly",
      _close(E.deflated_sharpe_vs(0.04, 0.0, T, N, v, -0.3, 6.0)["dsr"],
             combine.deflated_sharpe(0.04, T, N, v, -0.3, 6.0)[0], 1e-15))
check("one trial has no selection: the threshold is the benchmark's Sharpe itself",
      E.deflated_sharpe_vs(0.03, 0.03, T, 1)["sr0"] == 0.0
      and _close(E.deflated_sharpe_vs(0.03, 0.03, T, 1)["dsr"], 0.5, 1e-12))
check("more trials raise the bar", E.deflated_sharpe_vs(0.06, 0.03, T, 100)["dsr"]
      < E.deflated_sharpe_vs(0.06, 0.03, T, 10)["dsr"])
check("a run without --trials does not invent a deflated Sharpe", _m["deflated_sharpe"] is None
      and "not computed: pass --trials" in E.render(_m))
_dsr_run = E.run(_win, _cal_rule, 2.0, 0.03, trials=40, **QUIET)
check("a run with --trials deflates against the benchmark's own Sharpe",
      _close(_dsr_run["deflated_sharpe"]["threshold_per_session"],
             _dsr_run["benchmark"]["sharpe_per_session"] + _dsr_run["deflated_sharpe"]["sr0"], 1e-15))

# ================================================================== bootstrap

print("\nbootstrap — paired, stationary, seeded")

_ra = [random.Random(1).gauss(0.0004, 0.01) for _ in range(300)]
_rng2 = random.Random(2)
_ra = [_rng2.gauss(0.0004, 0.01) for _ in range(300)]
_g0 = [0.0] * 300
_bs_same = E.bootstrap(_ra, _ra, _g0, 1.2, 200, 20, 0)
check("a rule identical to its benchmark has a zero-width CI at zero",
      _bs_same["cagr_diff_ci95"] == [0.0, 0.0] and _bs_same["p_cagr_diff_le_0"] == 1.0)
_rb = [x - 0.0004 for x in _ra]
_bs_up = E.bootstrap(_ra, _rb, _g0, 1.2, 200, 20, 0)
check("a rule that beats its benchmark every session has a CI above zero",
      _bs_up["cagr_diff_ci95"][0] > 0 and _bs_up["p_cagr_diff_le_0"] == 0.0)
check("the bootstrap is deterministic under its seed",
      E.bootstrap(_ra, _rb, _g0, 1.2, 50, 20, 3) == E.bootstrap(_ra, _rb, _g0, 1.2, 50, 20, 3))

# ================================================================== many files, cli

print("\nmany files and the command line")

_tmp = tempfile.mkdtemp(prefix="edgelab-cli-")
_pa = os.path.join(_tmp, "AAA-1d.csv")
_pb = os.path.join(_tmp, "BBB-1d.csv")
_pz = os.path.join(_tmp, "ZZZ-1d.csv")
B.to_csv(_walk_series(dt.date(2024, 1, 2), dt.date(2024, 12, 31), seed=21, symbol="AAA"), _pa)
B.to_csv(_walk_series(dt.date(2024, 1, 2), dt.date(2024, 12, 31), seed=22, symbol="BBB"), _pb)
B.to_csv(B.Series("ZZZ", "1d", _bad, dict(PROV)), _pz)
_rows = E.run_many([_pa, _pb, _pz], "buy_and_hold", cost_bps_per_side=1.0, cash=0.0, **QUIET)
check("the same rule runs on many files, symbols taken from the file names",
      [r["symbol"] for r in _rows] == ["AAA", "BBB", "ZZZ"]
      and _rows[0]["status"] == "ok" and _rows[1]["status"] == "ok")
check("a file barqc blocks is a BLOCKED row, never a silent gap", _rows[2]["status"].startswith("BLOCKED"))
_tab = E.summary_table(_rows)
check("the summary table has a row per file, the blocked one included",
      all(s in _tab for s in ("AAA", "BBB", "ZZZ")) and "BLOCKED" in _tab)


def _cli(argv):
    out, err = io.StringIO(), io.StringIO()
    try:
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = E.main(argv)
    except SystemExit as e:
        code = e.code if isinstance(e.code, int) else 1
    return code, out.getvalue(), err.getvalue()


_c, _o, _ = _cli(["--list-rules"])
check("--list-rules lists exactly the three", _c == 0 and all(n in _o for n in E.RULES))
_c, _, _ = _cli(["--rule", "buy_and_hold", "--csv", _pa, "--cash-yield", "0"])
check("no cost given is refused: there is no default cost", _c == 2)
_c, _, _ = _cli(["--rule", "buy_and_hold", "--csv", _pa, "--cost-bps-per-side", "1"])
check("no cash yield given is refused: 0 is an answer, silence is not", _c == 2)
_c, _, _ = _cli(["--rule", "test_overnight_only", "--csv", _pa, "--cost-bps-per-side", "1",
                 "--cash-yield", "0"])
check("a test-only rule is refused on a file without --allow-test-rule", _c == 2)
_c, _, _ = _cli(["--rule", "buy_and_hold", "--csv", _pa, "--cost-bps-per-side", "1",
                 "--cash-yield", "5"])
check("a cash yield that looks like a percent is refused", _c == 2)
_outp = os.path.join(_tmp, "out", "run.txt")
_c, _o, _ = _cli(["--rule", "buy_and_hold", "--csv", _pa, _pb, "--source", "test", "--adjusted", "yes",
                  "--cost-bps-per-side", "1", "--cash-yield", "0.03", "--trials", "40", "--seed", "0",
                  "--placebo-draws", "10", "--boot-draws", "10", "--out", _outp])
check("a two-file run exits 0 and writes --out", _c == 0 and os.path.exists(_outp), str(_c))
_txt = open(_outp).read() if os.path.exists(_outp) else ""
check("--out holds the summary, both reports, the cost convention, then JSON",
      "COST CONVENTION  1 bp PER SIDE" in _txt and _txt.count("EDGELAB v") == 2 and "symbol" in _txt
      and json.loads(_txt[_txt.index("\n{"):])["runs"][1]["symbol"] == "BBB")
_c, _o, _ = _cli(["--rule", "buy_and_hold", "--csv", _pa, _pz, "--cost-bps-per-side", "1",
                  "--cash-yield", "0", "--placebo-draws", "0", "--boot-draws", "0"])
check("a run with a blocked file exits 2 and still reports the good one", _c == 2 and "AAA" in _o and "BLOCKED" in _o)
_c, _o, _ = _cli(["--calendar-report", "--csv", _pa])
check("--calendar-report runs on dates alone", _c == 0 and "scheduled sessions" in _o)
_c, _o, _ = _cli(["--rule", "buy_and_hold", "--csv", _pa, "--cost-bps-per-side", "1", "--cash-yield",
                  "0.03", "--leverage", "3", "--placebo-draws", "0", "--boot-draws", "0"])
check("--leverage 3 without --expense-ratio is refused", _c == 2)

# ================================================================== cleanup

shutil.rmtree(_tmp, ignore_errors=True)
shutil.rmtree(_tmpd, ignore_errors=True)
check("no bar file and not trials.json was touched by the tests", _snapshot() == _BEFORE)
check("the suite stayed offline: a connection out is refused",
      _raises(OSError, socket.create_connection, ("192.0.2.1", 80), 0.5))

print()
if FAILURES:
    print(f"{len(FAILURES)} FAILED: {', '.join(FAILURES)}")
    sys.exit(1)
print("all checks passed")
