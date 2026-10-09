#!/usr/bin/env python3
"""
edgelab.py — the bench. Runs ONE pre-registered once- or twice-a-day rule on
daily bars, at the only two moments it can trade (the open auction and the
close auction), and scores it against buy-and-hold over the identical window,
with a placebo, a deflated Sharpe and a bootstrap. It was built before any
candidate rule existed: the registry holds `buy_and_hold` and two TEST-ONLY
rules, nothing else. Rules are added after the pre-registration is frozen.

THE SESSION, AS TWO LEGS
    Session t has an OVERNIGHT leg, close[t-1] -> open[t], and an INTRADAY leg,
    open[t] -> close[t]. A rule declares a weight for each leg. Trades happen
    only at the auctions a retail broker takes orders for:
        close auction of t-1 (MOC)   sets the weight for the overnight leg of t
        open auction of t    (MOO)   sets the weight for the intraday leg of t
    Scoring is close-to-close: the window opens at a close auction, so every
    scored session has both of its legs and a session return is close-to-close.

INFORMATION SETS — enforced by the view, then checked by the leak check
    open auction of t    bars through close[t-1]. NOT open[t]: that is the
                         price this auction is about to set.
    close auction of t   bars through close[t-1], plus open[t]. NOT close[t],
                         high[t], low[t] or volume[t]: an MOC order is due
                         before ~15:50 ET and none of those exist yet.
    calendar             the SCHEDULED NYSE calendar (barqc.nyse_holidays),
                         for any date, because it is published in advance. An
                         unscheduled closure (a day of mourning, a hurricane)
                         is not in it, because it was not known in advance. The
                         BAR dates never feed a calendar fact a rule sees: "the
                         last session of the month" read off the bars is known
                         only once the month is over, and a missing bar would
                         silently shift every ordinal after it.

COST — PER SIDE, said loudly because the repo already has two conventions
    cost_bps_per_side is charged on the traded notional at every auction that
    trades. A full round trip (in, then out) therefore costs TWICE that.
    replay.py charges cost_bps per fill — the same convention. nulltest.py
    charges cost_bps ONCE per round trip — half this for the same number.
    Every output opens by saying which one it used.

CASH, DRAG, LEVERAGE
    Idle cash earns a constant annual rate or a dated series, accrued on
    CALENDAR days, all of it on the overnight leg: interest is paid on the
    end-of-day balance, and a weekend or a holiday is part of the overnight
    leg. Intraday legs accrue nothing.
    A labelled leveraged variant (k = 2 or 3) trades a MODELLED k-times
    daily-reset ETF built from the same bars: overnight k*r_on; intraday
    k*r_id*(1+r_on)/(1+k*r_on), because the fund reset its exposure at the
    previous close and the gap changed it; close-to-close exactly k*r_cc; less
    an annual expense ratio and financing of (k-1) at the cash rate, accrued
    like cash on the overnight leg. It is a model, not data, and every output
    that uses it says so.

WHAT IT MEASURES
    total return (ROI on all capital), CAGR, volatility, Sharpe and Sortino in
    excess of the cash rate, max drawdown with its dates, exposure (share of
    legs held; mean and capital-weighted), return per unit of exposure, round
    trips, turnover, cost paid, a per-year table, and halves split at the DATE
    midpoint. The benchmark is buy-and-hold of the underlying, bought at the
    SAME close auction the rule could first act at and scored over the
    identical legs: `buy_and_hold` run as a rule equals it to the last digit.

THE NULLS
    placebo    the rule's own exposure, moved in time. `shift`: a random
               circular shift of the session-by-session exposure — every block
               and its spacing kept, the phase moved. `blocks`: the same
               contiguous blocks of exposed sessions and the same flat gaps, in
               a random order. Both keep the number of exposed legs of each
               kind and their clustering. p = (1 + #null >= observed) /
               (1 + draws). With both, the LARGER p is the conservative reading.
               An exposure with no timing (every session alike) has no placebo
               and is reported as degenerate rather than given a p.
    deflated   Bailey & López de Prado (2014), against the BENCHMARK's Sharpe
               instead of zero (EVIDENCE.md, "One limitation in how the
               deflation was wired"); the trial count is an argument.
    bootstrap  stationary bootstrap (Politis & Romano 1994) of paired session
               returns: a CI for the CAGR difference and the Sharpe difference
               against buy-and-hold.

ADDING A RULE (after the pre-registration is frozen, never before)
    @register("name_from_the_prereg", warmup=0)
    def _name_from_the_prereg(v):
        '''What it holds and when, and the pre-registration it comes from.'''
        if v.auction == "close":           # weight for the overnight leg into v.next_cal
            return 1.0 if v.next_cal.month_ordinal_from_end == -1 else 0.0
        return 0.0                         # weight for today's intraday leg
    A rule returns a weight in [0, 1] of the instrument, is a pure function of
    the view, and keeps no state between calls: the leak check rebuilds it for
    every sample and compares.

USAGE
    python3 edgelab.py --list-rules
    python3 edgelab.py --calendar-report --csv bars/SPY-1d.csv
    python3 edgelab.py --rule buy_and_hold --csv bars/SPY-1d.csv --source stooq --adjusted yes \\
        --cost-bps-per-side 1 --cash-yield 0.03 --seed 0 --out runs/x.txt
    python3 edgelab.py --rule NAME --csv bars/DIA-1d-long.csv bars/QQQ-1d-long.csv --source stooq \\
        --cost-bps-per-side 1 --cash-yield 0.03 --trials 42 --placebo-draws 1000 --out runs/y.txt
"""

import argparse
import bisect
import csv
import datetime as dt
import hashlib
import json
import math
import os
import random
import sys
from dataclasses import dataclass
from statistics import NormalDist

import bars as B
import barqc
import combine
import replay

HERE = os.path.dirname(os.path.abspath(__file__))
EDGELAB_VERSION = 2

LookAhead = replay.LookAhead          # one exception type for the whole pipeline
Blocked = replay.Blocked

SESSIONS_PER_YEAR = 252               # annualises per-session statistics, as replay.py does
ACCRUAL_DAYS = 365.0                  # calendar-day basis for cash, expense and financing
MAX_LEVERAGE = 3
MAX_MARGIN_EXPOSURE = 2.0             # a margin-model rule holds e in [0, 2] of the underlying
EPS = 1e-12
HOLIDAY_HORIZON = 10                  # pre/post-holiday ranks are reported up to this many sessions
PARTIAL_BAR_VOLUME = 0.5              # final bar under this share of the trailing median → suspect
RATE_BOUNDS = (-0.05, 0.25)           # an annual rate outside this is a percent, or a typo

# Closures the scheduled calendar cannot know. Used ONLY to label the bar-vs-
# calendar report ("closure" vs "DATA HOLE"); never shown to a rule.
KNOWN_UNSCHEDULED_CLOSURES = {
    dt.date(1994, 4, 27): "national day of mourning (Nixon)",
    dt.date(2001, 9, 11): "September 11 attacks",
    dt.date(2001, 9, 12): "September 11 attacks",
    dt.date(2001, 9, 13): "September 11 attacks",
    dt.date(2001, 9, 14): "September 11 attacks",
    dt.date(2004, 6, 11): "national day of mourning (Reagan)",
    dt.date(2007, 1, 2): "national day of mourning (Ford)",
    dt.date(2012, 10, 29): "Hurricane Sandy",
    dt.date(2012, 10, 30): "Hurricane Sandy",
    dt.date(2018, 12, 5): "national day of mourning (G. H. W. Bush)",
    dt.date(2025, 1, 9): "national day of mourning (Carter)",
}

COST_NOTE = ("replay.py charges per fill (= per side, the same as here); nulltest.py charges "
             "ONCE per round trip (half this for the same number). Convert before comparing.")
CASH_NOTE = ("accrued on calendar days, all of it on the overnight leg (end-of-day balance; "
             "weekends and holidays fall in the overnight leg); intraday legs earn nothing")
INFO_NOTE = ("open auction of t sees bars through close[t-1]; close auction of t sees bars "
             "through close[t-1] plus open[t]; calendar = the SCHEDULED NYSE calendar (barqc), "
             "so an unscheduled closure is not known to the rule")
NOT_MODELLED = (
    "slippage beyond the stated per-side cost; the auction price versus the bar's open/close "
    "(on Alpaca IEX files the open and close are IEX prints, not the primary-market auctions "
    "MOO/MOC orders receive); auction imbalance and partial fills; order cut-offs (MOC ~15:50 ET, "
    "12:50 on half-days, which this calendar does not mark); taxes; borrow; dividends on files "
    "that are not total-return; settlement (T+1) and cash-account good-faith rules; the "
    "pattern-day-trader rule, which every same-session round trip (in at the open, out at the "
    "close) counts against")


# =================================================================== calendar

def third_friday(y, m):
    first = dt.date(y, m, 1)
    return first + dt.timedelta(days=(4 - first.weekday()) % 7 + 14)


@dataclass(frozen=True)
class Facts:
    """What the SCHEDULED calendar says about one session. Known in advance."""
    date: dt.date
    weekday: int                    # 0 = Monday
    month_ordinal: int              # 1 = first session of the month
    month_ordinal_from_end: int     # -1 = last session of the month
    month_sessions: int
    is_month_end: bool
    is_quarter_end: bool
    is_year_end: bool
    pre_holiday_rank: object        # 1 = the session right before a weekday exchange holiday; None if > horizon
    post_holiday_rank: object       # 1 = the first session after one; None if > horizon
    holiday_ahead: object           # that holiday's date (with pre_holiday_rank), else None
    is_opex: bool                   # monthly options expiration: third Friday, or the session before it when it is a holiday
    opex_offset: int                # sessions from this month's opex session (0 on it, -1 the session before)
    prev_session: object
    next_session: object
    days_since_prev_session: object  # calendar days the overnight leg INTO this session spans
    days_to_next_session: object     # calendar days the overnight leg OUT of it spans


class Calendar:
    """
    The scheduled NYSE calendar from barqc, with the facts a calendar rule
    keys on, precomputed per session. Built from DATES only — no bar touches
    it — so it is the same object in the full run and in the leak check.
    """

    def __init__(self, first, last):
        y0, y1 = first.year - 1, last.year + 1
        hol = set()
        for y in range(y0, y1 + 1):
            hol |= barqc.nyse_holidays(y)
        self.holidays = sorted(hol)
        self.sessions = barqc.sessions_between(dt.date(y0, 1, 1), dt.date(y1, 12, 31))
        self._index = {d: i for i, d in enumerate(self.sessions)}
        months = {}
        for i, d in enumerate(self.sessions):
            months.setdefault((d.year, d.month), []).append(i)
        self._months = months
        opex = {ym: bisect.bisect_right(self.sessions, third_friday(*ym)) - 1 for ym in months}
        self._opex = opex
        self._facts = {}
        S, H = self.sessions, self.holidays
        for (y, m), idxs in months.items():
            n = len(idxs)
            for k, i in enumerate(idxs):
                d = S[i]
                pre = ahead = post = None
                hi = bisect.bisect_right(H, d)
                if hi < len(H):
                    j = bisect.bisect_right(S, H[hi])       # first session after that holiday
                    if j - i <= HOLIDAY_HORIZON:
                        pre, ahead = j - i, H[hi]
                hi = bisect.bisect_left(H, d) - 1
                if hi >= 0:
                    j = bisect.bisect_right(S, H[hi])
                    if i - j + 1 <= HOLIDAY_HORIZON:
                        post = i - j + 1
                prev = S[i - 1] if i > 0 else None
                nxt = S[i + 1] if i + 1 < len(S) else None
                last = k == n - 1
                self._facts[d] = Facts(
                    date=d, weekday=d.weekday(), month_ordinal=k + 1,
                    month_ordinal_from_end=k - n, month_sessions=n,
                    is_month_end=last, is_quarter_end=last and m in (3, 6, 9, 12),
                    is_year_end=last and m == 12,
                    pre_holiday_rank=pre, post_holiday_rank=post, holiday_ahead=ahead,
                    is_opex=i == opex[(y, m)], opex_offset=i - opex[(y, m)],
                    prev_session=prev, next_session=nxt,
                    days_since_prev_session=(d - prev).days if prev else None,
                    days_to_next_session=(nxt - d).days if nxt else None)

    def is_session(self, d):
        return d in self._index

    def facts(self, d):
        try:
            return self._facts[d]
        except KeyError:
            raise ValueError(f"{d} is not a scheduled NYSE session") from None

    def next_session(self, d):
        i = bisect.bisect_right(self.sessions, d)
        return self.sessions[i] if i < len(self.sessions) else None

    def prev_session(self, d):
        i = bisect.bisect_left(self.sessions, d) - 1
        return self.sessions[i] if i >= 0 else None

    def between(self, a, b):
        """Scheduled sessions strictly between dates a and b."""
        return self.sessions[bisect.bisect_right(self.sessions, a):bisect.bisect_left(self.sessions, b)]

    def month(self, y, m):
        return [self.sessions[i] for i in self._months.get((y, m), [])]

    def opex(self, y, m):
        return self.sessions[self._opex[(y, m)]]

    def last_session(self, y, m):
        return self.sessions[self._months[(y, m)][-1]]


def calendar_report(series, cal=None):
    """
    Bar dates against the scheduled calendar. Dates only — no return is
    computed here. Says which scheduled sessions have no bar (an unscheduled
    closure, or a DATA HOLE: a session that traded and the file lacks), which
    bars sit on a closed day, which overnight legs span a missing session, how
    many bars a bar-counted month ordinal would have mislabelled and why, and
    whether the final bar looks like a partial session.
    """
    bars = series.bars
    if not bars:
        return {"bars": 0}
    dates = [b.ts.date() for b in bars]
    cal = cal or Calendar(dates[0], dates[-1])
    have = set(dates)
    sched = [d for d in cal.sessions if dates[0] <= d <= dates[-1]]
    missing = []
    for d in sched:
        if d not in have:
            why = KNOWN_UNSCHEDULED_CLOSURES.get(d)
            missing.append({"date": d.isoformat(),
                            "class": f"unscheduled closure: {why}" if why else "DATA HOLE"})
    extra = [d.isoformat() for d in dates if not cal.is_session(d)]
    gaps = []
    for a, b in zip(dates, dates[1:]):
        inside = cal.between(a, b)
        if inside:
            gaps.append({"into": b.isoformat(), "spans": [x.isoformat() for x in inside],
                         "class": "closure" if all(x in KNOWN_UNSCHEDULED_CLOSURES for x in inside)
                         else "DATA HOLE"})
    # A bar-counted ordinal, and why it disagrees with the scheduled one.
    by_month = {}
    for d in dates:
        if cal.is_session(d):
            by_month.setdefault((d.year, d.month), []).append(d)
    missing_months = {}
    for x in missing:
        d = dt.date.fromisoformat(x["date"])
        missing_months.setdefault((d.year, d.month), []).append(x["class"])
    first_m, last_m = (dates[0].year, dates[0].month), (dates[-1].year, dates[-1].month)
    shifts = {"from_start": 0, "from_end": 0, "by_cause": {}, "examples": []}
    for ym, ds in by_month.items():
        full = cal.month(*ym)
        causes = []
        if ym == first_m and ds[0] != full[0]:
            causes.append("file starts mid-month")
        if ym == last_m and ds[-1] != full[-1]:
            causes.append("file ends mid-month (a bar-counted 'last session' is not one)")
        for c in missing_months.get(ym, []):
            causes.append("DATA HOLE" if c == "DATA HOLE" else "unscheduled closure")
        cause = "; ".join(sorted(set(causes))) or "unexplained"
        n = len(ds)
        for k, d in enumerate(ds):
            f = cal.facts(d)
            bs, be = k + 1, k - n
            if bs != f.month_ordinal or be != f.month_ordinal_from_end:
                shifts["from_start"] += bs != f.month_ordinal
                shifts["from_end"] += be != f.month_ordinal_from_end
                shifts["by_cause"][cause] = shifts["by_cause"].get(cause, 0) + 1
                if len(shifts["examples"]) < 12:
                    shifts["examples"].append({
                        "date": d.isoformat(), "bar_counted": [bs, be],
                        "scheduled": [f.month_ordinal, f.month_ordinal_from_end], "cause": cause})
    flat = [b.ts.date().isoformat() for b in bars
            if b.open == b.high == b.low == b.close and b.volume <= 0]
    final = {"date": dates[-1].isoformat(), "suspect_partial": False, "volume_ratio": None}
    vols = sorted(b.volume for b in bars[-21:-1])
    if len(vols) >= 5:
        med = vols[len(vols) // 2]
        if med > 0:
            ratio = bars[-1].volume / med
            final["volume_ratio"] = ratio
            final["suspect_partial"] = ratio < PARTIAL_BAR_VOLUME
    return {"first": dates[0].isoformat(), "last": dates[-1].isoformat(), "bars": len(bars),
            "scheduled_sessions": len(sched), "missing": missing, "extra": extra,
            "gap_legs": gaps, "ordinal_shifts": shifts, "final_bar": final,
            "flat_zero_volume_bars": flat,
            "holes": [x["date"] for x in missing if x["class"] == "DATA HOLE"],
            "closures": [x["date"] for x in missing if x["class"] != "DATA HOLE"]}


def render_calendar(rep):
    L = [f"calendar: {rep['bars']} bars, {rep['scheduled_sessions']} scheduled sessions "
         f"{rep['first']} → {rep['last']}; {len(rep['missing'])} scheduled session(s) without a bar "
         f"({len(rep['closures'])} unscheduled closure(s), {len(rep['holes'])} DATA HOLE(s)); "
         f"{len(rep['extra'])} bar(s) on a closed day"]
    for x in rep["missing"]:
        L.append(f"    missing {x['date']}  {x['class']}")
    for x in rep["extra"][:10]:
        L.append(f"    bar on a closed day {x}")
    for g in rep["gap_legs"]:
        L.append(f"    overnight leg into {g['into']} spans {', '.join(g['spans'])} ({g['class']})")
    sh = rep["ordinal_shifts"]
    if sh["from_start"] or sh["from_end"]:
        L.append(f"    a BAR-COUNTED month ordinal would differ from the scheduled one on "
                 f"{sh['from_start']} bar(s) from the start and {sh['from_end']} from the end — "
                 f"this harness uses the scheduled ordinal:")
        for cause, n in sorted(sh["by_cause"].items()):
            L.append(f"      {n:>4}  {cause}")
        for e in sh["examples"][:6]:
            L.append(f"      e.g. {e['date']}: bar-counted {e['bar_counted']}, "
                     f"scheduled {e['scheduled']} ({e['cause']})")
    for d in rep.get("flat_zero_volume_bars", [])[:10]:
        L.append(f"    {d}: open = high = low = close with zero volume — a vendor placeholder, not a "
                 f"session (r1-quartermaster §1)")
    fb = rep["final_bar"]
    if fb["volume_ratio"] is not None:
        flag = ("  POSSIBLY A PARTIAL SESSION — consider --end on the previous session"
                if fb["suspect_partial"] else "")
        L.append(f"    final bar {fb['date']}: volume {fb['volume_ratio']:.0%} of the trailing "
                 f"20-bar median{flag}")
    return "\n".join(L)


# =================================================================== cash

class CashRate:
    """
    The annual rate idle cash earns: a constant, or a dated series read from a
    CSV with `date,rate` columns (annual decimals, the rate in force from that
    date). A date before the first row is refused, never extrapolated.
    """

    def __init__(self, rate=None, dated=None, label=None):
        if (rate is None) == (dated is None):
            raise ValueError("give a constant rate or a dated series, not both or neither")
        if rate is not None:
            _check_rate(rate, "cash yield")
            self.rate, self.dates, self.rates = float(rate), None, None
            self.label = label or f"{rate:.2%}/yr constant"
        else:
            self.rate = None
            self.dates = [d for d, _ in dated]
            self.rates = [r for _, r in dated]
            if any(b <= a for a, b in zip(self.dates, self.dates[1:])):
                raise ValueError("dated cash series must be strictly increasing in date")
            for d, r in dated:
                _check_rate(r, f"cash yield on {d}")
            self.label = label or (f"dated series, {len(self.dates)} rates "
                                   f"{self.dates[0]} → {self.dates[-1]}")

    def at(self, d):
        if self.rate is not None:
            return self.rate
        i = bisect.bisect_right(self.dates, d) - 1
        if i < 0:
            raise ValueError(f"no cash rate in force on {d}: the dated series starts "
                             f"{self.dates[0]}. Refused rather than extrapolated.")
        return self.rates[i]

    @classmethod
    def from_csv(cls, path):
        if not os.path.exists(path):
            raise ValueError(f"--cash-yield {path!r} is neither a number nor a file")
        rows = []
        with open(path, newline="") as f:
            rdr = csv.reader(f)
            head = [h.strip().lower() for h in next(rdr, [])]
            if "date" not in head or "rate" not in head:
                raise ValueError(f"{path}: header must have 'date' and 'rate' (annual decimals)")
            di, ri = head.index("date"), head.index("rate")
            for n, row in enumerate(rdr, start=2):
                if not row or all(not c.strip() for c in row):
                    continue
                try:
                    rows.append((dt.date.fromisoformat(row[di].strip()), float(row[ri])))
                except (ValueError, IndexError) as e:
                    raise ValueError(f"{path} row {n}: {e} — {row}")
        if not rows:
            raise ValueError(f"{path}: no rates")
        return cls(dated=rows, label=f"dated series {os.path.basename(path)}, {len(rows)} rates "
                                     f"{rows[0][0]} → {rows[-1][0]}")

    @classmethod
    def parse(cls, text):
        try:
            return cls(rate=float(text))
        except ValueError as e:
            if os.path.exists(str(text)):
                return cls.from_csv(text)
            raise ValueError(f"--cash-yield {text!r}: {e}") from None


def _check_rate(r, what):
    if not isinstance(r, (int, float)) or not math.isfinite(r) or not (RATE_BOUNDS[0] <= r <= RATE_BOUNDS[1]):
        raise ValueError(f"{what} {r!r} is outside {RATE_BOUNDS}: rates are annual decimals "
                         f"(0.05 is 5%)")


# =================================================================== legs

@dataclass
class Legs:
    """Per scored session j: the bar index, the dates, the underlying's two leg
    returns, the instrument's two leg returns, the cash growth of the overnight
    leg, its calendar days, and whether it spans a scheduled session with no bar."""
    t: list
    dates: list
    prev_dates: list
    r_on: list
    r_id: list
    i_on: list
    i_id: list
    g_on: list
    days: list
    gap: list
    leverage: int
    wiped: list


def accrual_years(D, accrual):
    """The year fraction one overnight leg accrues: D calendar days / 365 ('calendar', the
    round-1 end-of-day convention), or one session = 1/252 of a year whatever D is ('session')."""
    if accrual == "calendar":
        return D / ACCRUAL_DAYS
    if accrual == "session":
        return 1.0 / SESSIONS_PER_YEAR
    raise ValueError("accrual is 'calendar' (days/365) or 'session' (1/252 per session)")


def build_legs(bars, s0, last, cash, leverage=1, expense_ratio=0.0, cal=None, accrual="calendar",
               distributions=None, closes_only=False):
    """`distributions` = {ex-date: amount per share}, added back to make a price-only stretch
    total-return: on the ex-date's overnight leg, r_on = (open + amount) / close[t-1] - 1 (the
    holder of record at the open earns it). closes_only: each session is one close-to-close step,
    r_on = 0 and r_id = (close + amount) / close[t-1] - 1, so no open is ever read; only for books
    that never trade at an open auction."""
    k = int(leverage)
    dist = distributions or {}
    out = Legs([], [], [], [], [], [], [], [], [], [], k, [])
    for t in range(s0 + 1, last + 1):
        p, b = bars[t - 1], bars[t]
        d0, d1 = p.ts.date(), b.ts.date()
        D = (d1 - d0).days
        if closes_only:
            r_on, r_id = 0.0, (b.close + dist.get(d1, 0.0)) / p.close - 1.0
        else:
            r_on = (b.open + dist.get(d1, 0.0)) / p.close - 1.0
            r_id = b.close / b.open - 1.0
        y = cash.at(d0)
        yf = accrual_years(D, accrual)
        g = (1.0 + y) ** yf - 1.0
        if k == 1:
            i_on, i_id = r_on, r_id
        else:
            a = expense_ratio + (k - 1) * y
            delta = (1.0 + a) ** (-yf)
            base = 1.0 + k * r_on
            if base <= 0.0:                     # the modelled fund is wiped out at the open
                i_on, i_id = -1.0, 0.0
                out.wiped.append(d1.isoformat())
            else:
                i_on = base * delta - 1.0
                i_id = k * r_id * (1.0 + r_on) / base
        out.t.append(t)
        out.dates.append(d1)
        out.prev_dates.append(d0)
        out.r_on.append(r_on)
        out.r_id.append(r_id)
        out.i_on.append(i_on)
        out.i_id.append(i_id)
        out.g_on.append(g)
        out.days.append(D)
        out.gap.append(bool(cal.between(d0, d1)) if cal is not None else False)
    return out


# =================================================================== rules

class Rule:
    """
    A named decision function, the closed bars it needs before it can act, and
    the exposure model its numbers mean:

      model "weight"  a weight in [0, 1] of the instrument (round 1): the file
                      as traded, or a modelled k-times fund with --leverage k.
      model "margin"  an exposure e in [0, max_exposure <= 2] on the underlying
                      itself, held as shares between declared changes; the
                      borrowed (e-1)+ pays cash + spread, idle (1-e)+ earns cash.

    `baseline` is the exposure the rule holds when it is not doing anything —
    0 for a long/flat rule, 1 for an overlay. The placebos move departures from
    it. `anchor(facts) -> bool` marks the scheduled sessions whose CLOSE starts
    a new cycle for the within-cycle placebo (default: the last session of
    each month).
    """

    def __init__(self, name, decide, warmup=0, doc="", test_only=False, model="weight",
                 baseline=0.0, max_exposure=None, anchor=None):
        self.name = name
        self.decide = decide
        self.warmup = int(warmup)
        self.doc = doc
        self.test_only = bool(test_only)
        if self.warmup < 0:
            raise ValueError("warmup is a count of closed bars, >= 0")
        if model not in ("weight", "margin"):
            raise ValueError(f"model {model!r} is 'weight' or 'margin'")
        self.model = model
        mx = (1.0 if model == "weight" else MAX_MARGIN_EXPOSURE) if max_exposure is None \
            else float(max_exposure)
        if model == "weight" and mx != 1.0:
            raise ValueError("a weight-model rule's maximum is 1: leverage belongs to --leverage")
        if model == "margin" and not 0.0 < mx <= MAX_MARGIN_EXPOSURE:
            raise ValueError(f"a margin rule's maximum exposure is in (0, {MAX_MARGIN_EXPOSURE:g}]")
        self.max_exposure = mx
        self.baseline = float(baseline)
        if not 0.0 <= self.baseline <= mx:
            raise ValueError(f"baseline {baseline} is outside [0, {mx:g}]")
        self.anchor = anchor


RULES = {}


def register(name, warmup=0, test_only=False, model="weight", baseline=0.0, max_exposure=None,
             anchor=None):
    """@register("name", warmup=N, model=...) over decide(view) -> exposure (see Rule)."""
    def deco(fn):
        if name in RULES:
            raise ValueError(f"rule {name!r} is registered twice")
        doc = (fn.__doc__ or "").strip()
        RULES[name] = lambda: Rule(name, fn, warmup, doc, test_only, model, baseline,
                                   max_exposure, anchor)
        return fn
    return deco


def register_factory(name, factory):
    """For a rule with parameters or closures: factory() must return a FRESH Rule."""
    if name in RULES:
        raise ValueError(f"rule {name!r} is registered twice")
    RULES[name] = factory


def get_rule(name):
    if name not in RULES:
        raise KeyError(f"no rule named {name!r}; registered: {', '.join(sorted(RULES))}")
    return RULES[name]


@register("buy_and_hold", warmup=0)
def _buy_and_hold(v):
    """Fully invested in every leg from the first auction. The benchmark, as a rule."""
    return 1.0


@register("test_overnight_only", warmup=0, test_only=True)
def _test_overnight_only(v):
    """Not a candidate. In for every overnight leg: buys each close, sells each open."""
    return 1.0 if v.auction == "close" else 0.0


@register("test_intraday_only", warmup=0, test_only=True)
def _test_intraday_only(v):
    """Not a candidate. In for every intraday leg: buys each open, sells each close."""
    return 1.0 if v.auction == "open" else 0.0


# ------------------------------------------------------------------ PRE-REGISTERED RULES
# Add them below this line after the pre-registration is frozen, one @register
# each, citing the pre-registration file in the docstring. Nothing goes here
# before the freeze: a rule that exists is a rule somebody will run.


# =================================================================== the view

class View:
    """
    A rule's whole world at one auction: the bars that have CLOSED, plus — at
    the close auction only — today's open, and the scheduled calendar.

    Integer indexing past the closed bars raises LookAhead, exactly as
    replay.Cursor does; slices clamp. `open_today` raises at the open auction,
    where the open is the price being set. Today's close, high, low and volume
    raise at both auctions. `held` is the weight of the leg that just ended,
    so a rule that needs to know whether it is in reads it here instead of
    keeping state.
    """
    __slots__ = ("_bars", "_n", "_open", "auction", "date", "cal", "next_cal", "calendar",
                 "held", "symbol", "leverage")

    def __init__(self, bars, n, auction, date, today_open, calendar, held=0.0, symbol="",
                 leverage=1):
        if auction not in ("open", "close"):
            raise ValueError(f"auction must be 'open' or 'close', not {auction!r}")
        if n < 0 or n > len(bars):
            raise ValueError(f"view n={n} outside 0..{len(bars)}")
        self._bars = bars
        self._n = n
        self._open = today_open if auction == "close" else None
        self.auction = auction
        self.date = date
        self.calendar = calendar
        self.cal = calendar.facts(date)
        nxt = calendar.next_session(date)
        self.next_cal = calendar.facts(nxt) if nxt is not None else None
        self.held = float(held)
        self.symbol = symbol
        self.leverage = leverage

    def __len__(self):
        return self._n

    def __getitem__(self, k):
        if isinstance(k, slice):
            a, b, s = k.indices(self._n)
            return self._bars[a:b:s]
        if k < 0:
            k += self._n
        if k < 0 or k >= self._n:
            raise LookAhead(f"bar {k} requested at the {self.auction} auction of {self.date} with "
                            f"{self._n} bar(s) closed — it has not closed yet")
        return self._bars[k]

    def __iter__(self):
        return iter(self._bars[:self._n])

    @property
    def last(self):
        if self._n == 0:
            raise LookAhead("no bar has closed yet")
        return self._bars[self._n - 1]

    def closes(self, n=None):
        lo = 0 if n is None else max(0, self._n - n)
        return [b.close for b in self._bars[lo:self._n]]

    @property
    def open_today(self):
        if self.auction != "close":
            raise LookAhead(f"open_today at the OPEN auction of {self.date}: the open is the price "
                            f"this auction sets, not something an order placed before it can know")
        return self._open

    def _never(self, what):
        raise LookAhead(f"today's {what} at the {self.auction} auction of {self.date}: it does not "
                        f"exist until the close, after the MOC deadline")

    close_today = property(lambda self: self._never("close"))
    high_today = property(lambda self: self._never("high"))
    low_today = property(lambda self: self._never("low"))
    volume_today = property(lambda self: self._never("volume"))


def _weight(x, rule, date, auction):
    mx = getattr(rule, "max_exposure", 1.0)
    try:
        w = float(x)
    except (TypeError, ValueError):
        raise ValueError(f"rule {rule.name} returned {x!r} at the {auction} auction of {date}; "
                         f"a weight is a number") from None
    if not math.isfinite(w) or w < -EPS or w > mx + EPS:
        if getattr(rule, "model", "weight") == "weight":
            raise ValueError(f"rule {rule.name} returned {x!r} at the {auction} auction of {date}: "
                             f"a weight must be a finite number in [0, 1] of the instrument "
                             f"(leverage belongs to the instrument, --leverage, not to the weight)")
        raise ValueError(f"rule {rule.name} returned {x!r} at the {auction} auction of {date}: a "
                         f"margin exposure must be a finite number in [0, {mx:g}]")
    return min(mx, max(0.0, w))


def decide_all(series, rule, cal, s0, last, leverage=1):
    """
    Call the rule at every auction of the window, in time order. Returns the
    weights per scored session and the decision log the leak check samples:
    (today's bar index, auction, closed bars, held, weight).
    """
    bars = series.bars
    w_on, w_id, log = [], [], []
    held = 0.0
    for t in range(s0 + 1, last + 1):
        u = t - 1                                  # the close auction of u sets the overnight leg of t
        d = bars[u].ts.date()
        w = _weight(rule.decide(View(bars, u, "close", d, bars[u].open, cal, held, series.symbol,
                                     leverage)), rule, d, "close")
        log.append((u, "close", u, held, w))
        w_on.append(w)
        held = w
        d = bars[t].ts.date()                      # the open auction of t sets its intraday leg
        w = _weight(rule.decide(View(bars, t, "open", d, None, cal, held, series.symbol,
                                     leverage)), rule, d, "open")
        log.append((t, "open", t, held, w))
        w_id.append(w)
        held = w
    return w_on, w_id, log


# =================================================================== the walk

def walk(w_on, w_id, i_on, i_id, g_on, cost, detail=False):
    """
    The one accounting path — the rule, the benchmark, the zero-cost path and
    every placebo draw all go through it, so a null never differs from the
    real run by anything but the weights.

    Equity starts at 1.0, all cash, at the close auction of the start
    session. At each auction the book is set to exactly the declared weight;
    the traded notional is |target - current weight| x equity before the
    trade, and cost = cost_per_side x notional comes out of equity. A 0/1 rule
    never trades on drift; a fractional one is rebalanced back to its weight at
    every auction and pays for it. Cash grows only on the overnight leg.
    """
    S = len(w_on)
    E, h = 1.0, 0.0
    closes = [0.0] * S
    sides = entries = 0
    notional = paid = paid_frac = 0.0
    if detail:
        opens = [0.0] * S
        start_on, start_id = [0.0] * S, [0.0] * S
        auctions = []                   # (session j, "close"|"open", notional, cost)
    ruined_at = None
    for j in range(S):
        w = w_on[j]
        dw = w - h
        if dw > EPS or dw < -EPS:
            n = (dw if dw > 0 else -dw) * E
            c = n * cost
            if h <= EPS:
                entries += 1
            sides += 1
            notional += n
            paid += c
            paid_frac += c / E
            E -= c
            if detail:
                auctions.append((j, "close", n, c))
        A = w * E
        C = E - A
        if detail:
            start_on[j] = E
        A *= 1.0 + i_on[j]
        C *= 1.0 + g_on[j]
        E = A + C
        if E <= 0.0:
            ruined_at = j
            break
        h = A / E
        if detail:
            opens[j] = E
        w = w_id[j]
        dw = w - h
        if dw > EPS or dw < -EPS:
            n = (dw if dw > 0 else -dw) * E
            c = n * cost
            if h <= EPS:
                entries += 1
            sides += 1
            notional += n
            paid += c
            paid_frac += c / E
            E -= c
            if detail:
                auctions.append((j, "open", n, c))
        A = w * E
        C = E - A
        if detail:
            start_id[j] = E
        A *= 1.0 + i_id[j]
        E = A + C
        if E <= 0.0:
            ruined_at = j
            break
        h = A / E
        closes[j] = E
    if ruined_at is not None:
        for j in range(ruined_at, S):
            closes[j] = 0.0
            if detail:
                opens[j] = 0.0
    out = {"closes": closes, "sides": sides, "entries": entries, "notional": notional,
           "cost_paid": paid, "cost_frac": paid_frac, "ruined_at": ruined_at,
           "open_at_end": h > EPS and ruined_at is None}
    if detail:
        out.update(opens=opens, start_on=start_on, start_id=start_id, auctions=auctions)
    return out


def session_returns(closes):
    out, prev = [], 1.0
    for c in closes:
        out.append(c / prev - 1.0 if prev > 0 else 0.0)
        prev = c
    return out


def cagr_of(final, years):
    if years <= 0:
        return None
    if final <= 0:
        return -1.0
    return final ** (1.0 / years) - 1.0


def cagr_sharpe(closes, g_on, years):
    """The two numbers the placebo compares — the SAME function scores the observed run."""
    rets = session_returns(closes)
    ex = [r - g for r, g in zip(rets, g_on)]
    st = replay._stats(ex, SESSIONS_PER_YEAR)
    return cagr_of(closes[-1], years), st["sharpe"]


def drawdown(marks):
    """marks: [(date, 'open'|'close', equity)] in time order → worst peak-to-trough, with dates."""
    peak_i, worst, wp, wt = 0, 0.0, 0, 0
    for i, m in enumerate(marks):
        if m[2] > marks[peak_i][2]:
            peak_i = i
        elif marks[peak_i][2] > 0:
            dd = m[2] / marks[peak_i][2] - 1.0
            if dd < worst:
                worst, wp, wt = dd, peak_i, i
    rec = None
    if worst < 0:
        for m in marks[wt + 1:]:
            if m[2] >= marks[wp][2]:
                rec = m
                break

    def lab(m):
        return f"{m[0].isoformat()} {m[1]}"
    return {"max_drawdown": worst,
            "peak": lab(marks[wp]) if worst < 0 else None,
            "trough": lab(marks[wt]) if worst < 0 else None,
            "recovered": lab(rec) if rec else (None if worst == 0 else "not recovered")}


def _marks(start_date, legs, path):
    m = [(start_date, "close", 1.0)]
    for j, d in enumerate(legs.dates):
        m.append((d, "open", path["opens"][j]))
        m.append((d, "close", path["closes"][j]))
    return m


def score(path, legs, start_date, w_on, w_id, k):
    """Every headline number for one path over the scored legs."""
    closes = path["closes"]
    S = len(closes)
    rets = session_returns(closes)
    ex = [r - g for r, g in zip(rets, legs.g_on)]
    years = (legs.dates[-1] - start_date).days / 365.25
    st = replay._stats(rets, SESSIONS_PER_YEAR)
    sx = replay._stats(ex, SESSIONS_PER_YEAR)
    down = math.sqrt(sum(x * x for x in ex if x < 0) / S) if S else 0.0
    mean_ex = sum(ex) / S if S else 0.0
    dd = drawdown(_marks(start_date, legs, path))
    on_x = sum(1 for w in w_on if w > EPS)
    id_x = sum(1 for w in w_id if w > EPS)
    wsum = sum(w_on) + sum(w_id)
    eq_sum = sum(path["start_on"]) + sum(path["start_id"])
    cap_w = (sum(w * e for w, e in zip(w_on, path["start_on"]))
             + sum(w * e for w, e in zip(w_id, path["start_id"])))
    gross_legs = (sum(w * r for w, r in zip(w_on, legs.i_on))
                  + sum(w * r for w, r in zip(w_id, legs.i_id)))
    mean_eq = sum(closes) / S if S else 0.0
    return {
        "final_equity": closes[-1], "total_return": closes[-1] - 1.0,
        "cagr": cagr_of(closes[-1], years), "years": years,
        "volatility": st["volatility"], "sharpe": sx["sharpe"],
        "sharpe_per_session": sx["sharpe_per_bar"], "skew": sx["skew"], "kurt": sx["kurt"],
        "sortino": (mean_ex / down * math.sqrt(SESSIONS_PER_YEAR)) if down > 0 else None,
        **dd,
        "legs": 2 * S, "legs_exposed": on_x + id_x,
        "exposure_share": (on_x + id_x) / (2 * S),
        "exposure_share_overnight": on_x / S, "exposure_share_intraday": id_x / S,
        "mean_exposure": k * wsum / (2 * S),
        "capital_weighted_exposure": (k * cap_w / eq_sum) if eq_sum > 0 else 0.0,
        "gross_bp_per_unit_exposure": (1e4 * gross_legs / (k * wsum)) if wsum > 0 else None,
        "net_bp_per_unit_exposure": (1e4 * (gross_legs - path["cost_frac"]) / (k * wsum))
                                    if wsum > 0 else None,
        "sides": path["sides"], "round_trips": path["entries"], "open_at_end": path["open_at_end"],
        "turnover_per_year": (path["notional"] / mean_eq / years) if mean_eq > 0 and years > 0 else None,
        "cost_paid": path["cost_paid"], "ruined_at": path["ruined_at"],
    }


def per_year(legs, s_path, b_path, w_on, w_id):
    rows, j0 = [], 0
    S = len(legs.dates)
    ps, pb = 1.0, 1.0
    close_dates = legs.prev_dates            # the close auction before session j happens on prev_dates[j]
    while j0 < S:
        y = legs.dates[j0].year
        j1 = j0
        while j1 + 1 < S and legs.dates[j1 + 1].year == y:
            j1 += 1
        cs, cb = s_path["closes"][j1], b_path["closes"][j1]
        sides = cost = 0
        for (j, kind, n, c) in s_path["auctions"]:
            d = close_dates[j] if kind == "close" else legs.dates[j]
            if d.year == y:
                sides += 1
                cost += c
        exp = sum(1 for j in range(j0, j1 + 1) for w in (w_on[j], w_id[j]) if w > EPS)
        rows.append({"year": y, "sessions": j1 - j0 + 1,
                     "strategy": cs / ps - 1.0 if ps > 0 else None,
                     "benchmark": cb / pb - 1.0 if pb > 0 else None,
                     "exposure_share": exp / (2 * (j1 - j0 + 1)),
                     "sides": sides, "cost_pct_of_start_equity": cost / ps if ps > 0 else None})
        ps, pb = cs, cb
        j0 = j1 + 1
    return rows


def halves(legs, start_date, s_path, b_path, mode="date"):
    """Split at the DATE midpoint of the scored window (round 1), or at the midpoint SESSION
    index (mode 'session', r1-redteam D5) — never the bar midpoint by accident."""
    cut, split = split_halves(legs.dates, start_date, mode)  # sessions [0, cut) are the first half
    out = {"split_date": split.isoformat(), "mode": mode, "cut": cut}
    for name, a, b in (("first", 0, cut), ("second", cut, len(legs.dates))):
        if b - a < 2:
            out[name] = None
            continue
        d0 = start_date if a == 0 else legs.dates[a - 1]
        years = (legs.dates[b - 1] - d0).days / 365.25
        row = {"from": d0.isoformat(), "to": legs.dates[b - 1].isoformat(), "sessions": b - a}
        for who, p in (("strategy", s_path), ("benchmark", b_path)):
            base = 1.0 if a == 0 else p["closes"][a - 1]
            seg = p["closes"][a:b]
            if base <= 0:
                row[who] = None
                continue
            rets = session_returns([c / base for c in seg])
            ex = [r - g for r, g in zip(rets, legs.g_on[a:b])]
            row[who] = {"return": seg[-1] / base - 1.0, "cagr": cagr_of(seg[-1] / base, years),
                        "sharpe": replay._stats(ex, SESSIONS_PER_YEAR)["sharpe"],
                        "max_drawdown": replay.max_drawdown([base] + seg)}
        out[name] = row
    return out


# =================================================================== the nulls

def _segments(states):
    runs = []
    for s in states:
        exposed = s[0] > EPS or s[1] > EPS
        if runs and runs[-1][0] == exposed:
            runs[-1][1].append(s)
        else:
            runs.append((exposed, [s]))
    blocks = [r for e, r in runs if e]
    gaps = [r for e, r in runs if not e]
    return blocks, gaps, (runs[0][0] if runs else True)


def placebo_states(states, method, rng):
    """One placebo arrangement of the session states (w_on, w_id)."""
    S = len(states)
    if method == "shift":
        if S < 2:
            return list(states)
        u = rng.randrange(1, S)
        return states[-u:] + states[:-u]
    if method == "blocks":
        blocks, gaps, first_block = _segments(states)
        b, g = blocks[:], gaps[:]
        rng.shuffle(b)
        rng.shuffle(g)
        a, c = (b, g) if first_block else (g, b)
        out = []
        for i in range(max(len(a), len(c))):
            if i < len(a):
                out.extend(a[i])
            if i < len(c):
                out.extend(c[i])
        return out
    raise ValueError(f"placebo method {method!r} is not shift or blocks")


def placebo(w_on, w_id, legs, cost, years, method, draws, seed):
    """p-values of the observed CAGR and Sharpe against the rule's own exposure, moved in time."""
    states = list(zip(w_on, w_id))
    obs_cagr, obs_sharpe = cagr_sharpe(
        walk(w_on, w_id, legs.i_on, legs.i_id, legs.g_on, cost)["closes"], legs.g_on, years)
    rng = random.Random(f"edgelab/{seed}/{method}")
    cagrs, sharpes, seen = [], [], set()
    for _ in range(draws):
        st = placebo_states(states, method, rng)
        seen.add(hash(tuple(st)))
        p = walk([s[0] for s in st], [s[1] for s in st], legs.i_on, legs.i_id, legs.g_on, cost)
        c, s = cagr_sharpe(p["closes"], legs.g_on, years)
        cagrs.append(c)
        sharpes.append(s)
    degenerate = len(seen) <= 1 and (not seen or hash(tuple(states)) in seen)
    out = {"method": method, "draws": draws, "seed": seed, "unique_arrangements": len(seen),
           "degenerate": degenerate, "observed_cagr": obs_cagr, "observed_sharpe": obs_sharpe,
           "null_cagr": cagrs, "null_sharpe": sharpes}
    if degenerate or not draws:
        out.update(p_cagr=None, p_sharpe=None)
        return out
    out["p_cagr"] = (1 + sum(1 for x in cagrs if x >= obs_cagr - EPS)) / (1 + draws)
    out["p_sharpe"] = (1 + sum(1 for x in sharpes if x >= obs_sharpe - EPS)) / (1 + draws)
    for key, xs in (("cagr", cagrs), ("sharpe", sharpes)):
        srt = sorted(xs)
        out[f"null_{key}_q"] = {q: _quantile(srt, q) for q in (0.05, 0.5, 0.95)}
    return out


def _quantile(srt, q):
    if not srt:
        return None
    x = q * (len(srt) - 1)
    lo = int(math.floor(x))
    hi = min(lo + 1, len(srt) - 1)
    return srt[lo] + (srt[hi] - srt[lo]) * (x - lo)


def deflated_sharpe_vs(sr, sr_bench, T, n_trials, var_sr=None, skew=0.0, kurt=3.0):
    """
    P(true Sharpe > the benchmark's | the observed per-session Sharpe sr over T
    sessions, after n_trials tries) — Bailey & López de Prado 2014 with the
    null moved from zero to the benchmark: the threshold is sr_bench plus the
    expected maximum of n_trials zero-edge Sharpe estimates. Per-session Sharpes,
    not annualised. var_sr defaults to the sampling variance of one Sharpe
    estimate under the null, 1/(T-1): the number N independent nothings scatter
    by. The benchmark's Sharpe is treated as known; its own sampling error is
    not in this number (the bootstrap carries it).
    """
    if T < 3:
        return {"dsr": None, "sr0": None, "z": None, "var_sr": None}
    v = (1.0 / (T - 1)) if var_sr is None else float(var_sr)
    sr0 = combine.expected_max_sharpe(n_trials, v)
    denom = math.sqrt(max(1e-12, 1.0 - skew * sr + (kurt - 1.0) / 4.0 * sr * sr))
    z = (sr - sr_bench - sr0) * math.sqrt(T - 1) / denom
    return {"dsr": NormalDist().cdf(z), "sr0": sr0, "z": z, "var_sr": v,
            "threshold_per_session": sr_bench + sr0}


def bootstrap(a, b, g, years, draws, block_len, seed):
    """
    Stationary bootstrap of PAIRED session returns: the same resampled sessions
    for the rule and for buy-and-hold, so their correlation is kept. Returns
    the 95% CI of the CAGR difference and the Sharpe difference, and the share
    of resamples in which the rule did not beat the benchmark.
    """
    n = len(a)
    if draws <= 0 or n < 2:
        return None
    p = 1.0 / block_len
    rng = random.Random(f"edgelab/{seed}/bootstrap")
    rr, rand = rng.randrange, rng.random
    ann = math.sqrt(SESSIONS_PER_YEAR)
    dc, ds = [], []
    for _ in range(draws):
        i = rr(n)
        pa = pb = 1.0
        sa = sb = qa = qb = 0.0
        for _k in range(n):
            x, y, z = a[i], b[i], g[i]
            pa *= 1.0 + x
            pb *= 1.0 + y
            ea, eb = x - z, y - z
            sa += ea
            sb += eb
            qa += ea * ea
            qb += eb * eb
            i = rr(n) if rand() < p else (i + 1) % n
        ca, cb = cagr_of(pa, years), cagr_of(pb, years)
        dc.append(ca - cb)
        va = (qa - sa * sa / n) / (n - 1)
        vb = (qb - sb * sb / n) / (n - 1)
        sha = (sa / n) / math.sqrt(va) * ann if va > 0 else 0.0
        shb = (sb / n) / math.sqrt(vb) * ann if vb > 0 else 0.0
        ds.append(sha - shb)
    dc.sort()
    ds.sort()
    return {"draws": draws, "block_len": block_len, "seed": seed,
            "cagr_diff_ci95": [_quantile(dc, 0.025), _quantile(dc, 0.975)],
            "cagr_diff_median": _quantile(dc, 0.5),
            "p_cagr_diff_le_0": sum(1 for x in dc if x <= 0) / draws,
            "sharpe_diff_ci95": [_quantile(ds, 0.025), _quantile(ds, 0.975)],
            "sharpe_diff_median": _quantile(ds, 0.5),
            "p_sharpe_diff_le_0": sum(1 for x in ds if x <= 0) / draws}


# =================================================================== leak check

def _partial(bar):
    """Today's bar as a close-auction order sees it: the open, and nothing else."""
    nan = float("nan")
    return B.Bar(bar.ts, bar.open, nan, nan, nan, nan)


def leak_check(series, factory, log, cal, samples=100, changes=200, seed=0, leverage=1):
    """
    replay.leak_check's idea at both auctions: re-decide a sample of the run's
    decisions on bars TRUNCATED at that auction's information set — at an open
    auction the bars through close[t-1]; at a close auction those plus a bar
    for today holding only its open (high, low, close and volume are NaN) — with
    a FRESH rule from the factory and the held weight the run had, and compare.
    The view already raises on public access past the information set; this
    catches the rest: a peek through private attributes, a feature computed
    once over the whole series, state kept between calls. Every point where the
    decision changed is checked (up to `changes`), plus `samples` at random.
    """
    bars = series.bars
    rng = random.Random(f"edgelab/{seed}/leak")
    idx = list(range(len(log)))
    pick = set(rng.sample(idx, min(samples, len(idx))))
    flips = [i for i in idx if i > 0 and abs(log[i][4] - log[i - 1][4]) > EPS]
    if len(flips) > changes:
        step = len(flips) / changes
        flips = [flips[int(k * step)] for k in range(changes)]
    pick |= set(flips)
    diffs, by = [], {"open": 0, "close": 0}
    for i in sorted(pick):
        today, auction, n, held, w = log[i]
        by[auction] += 1
        if auction == "close":
            trunc = tuple(bars[:n]) + (_partial(bars[today]),)
            v = View(trunc, n, "close", bars[today].ts.date(), bars[today].open, cal, held,
                     series.symbol, leverage)
        else:
            trunc = tuple(bars[:n])
            v = View(trunc, n, "open", bars[today].ts.date(), None, cal, held, series.symbol,
                     leverage)
        rule = factory()
        try:
            got = _weight(rule.decide(v), rule, v.date, auction)
        except Exception as e:                      # a peek that now finds nothing
            diffs.append({"date": v.date.isoformat(), "auction": auction, "run": w,
                          "check": f"raised {type(e).__name__}: {e}"})
            continue
        if abs(got - w) > EPS:
            diffs.append({"date": v.date.isoformat(), "auction": auction, "run": w, "check": got})
    return {"checked": len(pick), "open": by["open"], "close": by["close"], "differences": diffs}


# =================================================================== the run

def load(path, symbol=None, source=None, adjusted=None, total_return_through=None):
    """Load a daily file. `total_return_through` declares a basis cutoff: total-return up to that
    date, price-only after (r1-quartermaster §Conclusions-2); recorded, never measured."""
    sym = symbol or symbol_from_path(path)
    s = B.load_csv(path, sym, "1d", source, adjusted)
    if total_return_through is not None:
        s.provenance["total_return_through"] = str(total_return_through)
    with open(path, "rb") as f:
        s.provenance["sha256"] = hashlib.sha256(f.read()).hexdigest()
    return s


def symbol_from_path(path):
    return os.path.basename(path).split("-")[0].split(".")[0].upper()


def gate(series):
    """barqc decides whether these bars may be used at all — exactly as everywhere else."""
    if series.timeframe != "1d":
        raise Blocked(f"edgelab runs on daily bars; {series.describe()} is {series.timeframe}")
    qc = barqc.inspect(series)
    if qc["verdict"] == "blocked":
        raise Blocked(f"barqc blocked {series.describe()}: {', '.join(qc['failed'])}. "
                      f"Fix the data first.")
    return qc


def _as_factory(rule):
    if isinstance(rule, str):
        return get_rule(rule)
    if isinstance(rule, Rule):
        raise TypeError("pass a FACTORY (a callable returning a fresh Rule), not a Rule: the "
                        "leak check rebuilds the rule for every sample")
    return rule


def run(series, rule, cost_bps_per_side, cash, leverage=1, expense_ratio=None, start=None,
        end=None, trials=None, sr_var=None, seed=0, placebo_draws=1000, placebo_method="both",
        boot_draws=1000, block_len=20, leak_samples=100, leak_changes=200, keep_curves=False,
        halves_mode="date", trials_sensitivity=100, dsr_draws=5000, dsr_block=10, prereg=None):
    """
    One rule, one file. `rule` is a registry name or a factory returning a
    fresh Rule. Raises Blocked (data), ValueError (arguments, or a weight out
    of range) and LookAhead (a rule that reached past its information set).
    With `trials`, the deflated Sharpe is the paired one (dsr_paired, against
    buy-and-hold, on returns in excess of cash); round 1's single-Sharpe form is
    kept beside it as `deflated_sharpe_round1`, for comparison only.
    """
    factory = _as_factory(rule)
    if not isinstance(cash, CashRate):
        cash = CashRate(rate=float(cash))
    cost_bps_per_side = float(cost_bps_per_side)
    if not math.isfinite(cost_bps_per_side) or not 0 <= cost_bps_per_side < 1000:
        raise ValueError(f"cost {cost_bps_per_side} bp per side is not a cost")
    k = int(leverage)
    if k != leverage or not 1 <= k <= MAX_LEVERAGE:
        raise ValueError(f"leverage {leverage}: the modelled instrument is 1x, 2x or 3x")
    if k > 1:
        if expense_ratio is None:
            raise ValueError(f"a {k}x variant needs a stated annual expense ratio (--expense-ratio)")
        if not math.isfinite(expense_ratio) or not 0 <= expense_ratio < 0.2:
            raise ValueError(f"expense ratio {expense_ratio} is not an annual decimal")
    else:
        expense_ratio = 0.0
    if placebo_method not in ("shift", "blocks", "both"):
        raise ValueError("placebo is shift, blocks or both")
    if trials is not None and int(trials) < 1:
        raise ValueError("trials counts every specification tried, >= 1")
    if block_len < 1:
        raise ValueError("block length is >= 1 session")
    if trials is not None and dsr_draws < 2:
        raise ValueError("the paired deflated Sharpe needs at least 2 bootstrap draws")

    qc = gate(series)
    bars = series.bars
    r0 = factory()
    dates = [b.ts.date() for b in bars]
    cal = Calendar(dates[0], dates[-1])
    first = 0 if start is None else bisect.bisect_left(dates, start)
    s0 = max(r0.warmup, first - 1, 0)
    last = len(bars) - 1 if end is None else bisect.bisect_right(dates, end) - 1
    if last - s0 < 3:
        raise Blocked(f"{series.describe()}: {last - s0} scored session(s) after a warm-up of "
                      f"{r0.warmup} bar(s) and the requested window — nothing to measure")
    legs = build_legs(bars, s0, last, cash, k, expense_ratio, cal)
    w_on, w_id, log = decide_all(series, r0, cal, s0, last, k)
    cost = cost_bps_per_side / 1e4
    S = len(w_on)
    start_date = dates[s0]
    years = (legs.dates[-1] - start_date).days / 365.25

    s_path = walk(w_on, w_id, legs.i_on, legs.i_id, legs.g_on, cost, detail=True)
    g_path = walk(w_on, w_id, legs.i_on, legs.i_id, legs.g_on, 0.0)
    ones = [1.0] * S
    b_path = walk(ones, ones, legs.r_on, legs.r_id, legs.g_on, cost, detail=True)
    strategy = score(s_path, legs, start_date, w_on, w_id, k)
    strategy["gross_final_equity"] = g_path["closes"][-1]
    strategy["gross_cagr"] = cagr_of(g_path["closes"][-1], years)
    bl = Legs(legs.t, legs.dates, legs.prev_dates, legs.r_on, legs.r_id, legs.r_on, legs.r_id,
              legs.g_on, legs.days, legs.gap, 1, [])
    benchmark = score(b_path, bl, start_date, ones, ones, 1)
    lev_bh = None
    if k > 1:
        lp = walk(ones, ones, legs.i_on, legs.i_id, legs.g_on, cost, detail=True)
        lev_bh = score(lp, legs, start_date, ones, ones, k)

    res = {
        "edgelab_version": EDGELAB_VERSION,
        "rule": r0.name, "rule_doc": r0.doc, "test_only_rule": r0.test_only, "warmup": r0.warmup,
        "symbol": series.symbol, "path": series.provenance.get("path"),
        "source": series.provenance.get("source"), "adjusted": series.provenance.get("adjusted"),
        "qc_verdict": qc["verdict"], "qc_unrun": qc["unrun"],
        "settings": {"cost_bps_per_side": cost_bps_per_side,
                     "round_trip_bps": 2 * cost_bps_per_side,
                     "cash": cash.label, "leverage": k,
                     "expense_ratio": expense_ratio if k > 1 else None,
                     "start": start.isoformat() if start else None,
                     "end": end.isoformat() if end else None,
                     "trials": trials, "seed": seed, "placebo_draws": placebo_draws,
                     "placebo_method": placebo_method, "boot_draws": boot_draws,
                     "block_len": block_len},
        "conventions": {"cost": f"{cost_bps_per_side:g} bp PER SIDE on traded notional; a round "
                                f"trip costs {2 * cost_bps_per_side:g} bp. {COST_NOTE}",
                        "cash": CASH_NOTE, "information": INFO_NOTE,
                        "annualisation": f"{SESSIONS_PER_YEAR} sessions/yr for volatility and "
                                         f"Sharpe; calendar years (days/365.25) for CAGR",
                        "instrument": instrument_note(series.symbol, k, expense_ratio),
                        "dividends": dividend_note(series.provenance.get("adjusted"))},
        "calendar": calendar_report(series, cal),
        "window": {"start_close": start_date.isoformat(), "first_session": legs.dates[0].isoformat(),
                   "last_session": legs.dates[-1].isoformat(), "sessions": S, "legs": 2 * S,
                   "years": years, "warmup_bars": r0.warmup,
                   "gap_legs_in_window": [d.isoformat() for d, gp in zip(legs.dates, legs.gap) if gp],
                   "benchmark_first_leg": legs.dates[0].isoformat(),
                   "benchmark_entry": f"close auction of {start_date.isoformat()}"},
        "strategy": strategy, "benchmark": benchmark, "leveraged_buy_and_hold": lev_bh,
        "instrument_wiped_out": legs.wiped,
        "per_year": per_year(legs, s_path, b_path, w_on, w_id),
        "halves": halves(legs, start_date, s_path, b_path, halves_mode),
        "not_modelled": NOT_MODELLED,
    }
    res["leak_check"] = leak_check(series, factory, log, cal, leak_samples, leak_changes, seed, k)
    res["integrity"] = integrity_check(series, qc, res["leak_check"], log, prereg)

    res["placebo"] = {}
    if placebo_draws:
        for m in (("shift", "blocks") if placebo_method == "both" else (placebo_method,)):
            p = placebo(w_on, w_id, legs, cost, years, m, placebo_draws, seed)
            p.pop("null_cagr")
            p.pop("null_sharpe")
            res["placebo"][m] = p
        ps = [p["p_sharpe"] for p in res["placebo"].values() if p["p_sharpe"] is not None]
        pc = [p["p_cagr"] for p in res["placebo"].values() if p["p_cagr"] is not None]
        res["placebo_conservative"] = {"p_cagr": max(pc) if pc else None,
                                       "p_sharpe": max(ps) if ps else None}

    s_rets = session_returns(s_path["closes"])
    b_rets = session_returns(b_path["closes"])
    if trials is not None:
        ex_s = [x - g for x, g in zip(s_rets, legs.g_on)]
        ex_b = [x - g for x, g in zip(b_rets, legs.g_on)]
        res["deflated_sharpe"] = dsr_paired(ex_s, ex_b, int(trials), trials_sensitivity, dsr_block,
                                            dsr_draws, seed)
        res["deflated_sharpe"]["benchmark"] = "buy_and_hold"
        res["deflated_sharpe_round1"] = deflated_sharpe_vs(
            strategy["sharpe_per_session"], benchmark["sharpe_per_session"], S, int(trials),
            sr_var, strategy["skew"], strategy["kurt"])
        res["deflated_sharpe_round1"]["trials"] = int(trials)
    else:
        res["deflated_sharpe"] = res["deflated_sharpe_round1"] = None
    res["bootstrap"] = bootstrap(s_rets, b_rets, legs.g_on, years, boot_draws, block_len, seed)
    if keep_curves:
        res["_curves"] = [
            {"date": legs.dates[j].isoformat(), "close_auction_on": legs.prev_dates[j].isoformat(),
             "gap_leg": legs.gap[j], "w_overnight": w_on[j], "w_intraday": w_id[j],
             "r_overnight": legs.r_on[j], "r_intraday": legs.r_id[j],
             "instr_overnight": legs.i_on[j], "instr_intraday": legs.i_id[j],
             "cash_overnight": legs.g_on[j],
             "strategy_open": s_path["opens"][j], "strategy_close": s_path["closes"][j],
             "benchmark_open": b_path["opens"][j], "benchmark_close": b_path["closes"][j]}
            for j in range(S)]
    return res


def write_curves(res, path):
    """The per-session path of one run, as CSV: what was held in each leg and what it earned."""
    rows = res["_curves"]
    d = os.path.dirname(os.path.abspath(path))
    os.makedirs(d, exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        for r in rows:
            w.writerow({k: (repr(v) if isinstance(v, float) else v) for k, v in r.items()})
    os.replace(tmp, path)
    return path


# =================================================================== round 2 — the margin overlay

DEFAULT_CRISES = (("2008-09-01", "2009-06-30"), ("2020-02-15", "2020-04-30"))
EPISODE_MERGE_GAP = 5              # runs separated by fewer than 5 baseline sessions are one episode (r1-redteam D6)
TOP_EPISODES = 5
STOP_LEVEL = 0.15                  # the autopilot's drawdown STOP (r1-redteam L4): crossings reported, never gated
DRIFT_NOTE = ("shares are held between declared changes, as a margin account behaves: an auction trades "
              "only when the declared exposure changes, and the exposure drifts with the price in "
              "between. Bar (A) holds shares the same way and is reset to its target at every auction "
              "where the rule trades, so both books trade on the same days")
MARGIN_NOTE = ("exposure e on the underlying itself; the borrowed (e-1)+ pays cash + spread and idle "
               "(1-e)+ earns cash, both on the overnight leg. A model of a frictionless margin loan: no "
               "maintenance calls, no whole-share rounding, no expense ratio")


def month_offset(f):
    """A session's offset from its own month's last scheduled session T: T -> 0, T-1 -> -1."""
    return f.month_ordinal_from_end + 1


def in_month_window(f, first, last):
    """
    True when the session is T+first .. T+last of some month, where T is the
    month's last SCHEDULED session: offsets <= 0 count back from T inside the
    session's own month, offsets >= 1 count into the next month (T+1 is the
    next month's first session).
    """
    if first > last:
        raise ValueError("the first offset must not exceed the last")
    o = f.month_ordinal_from_end + 1
    if first <= o <= min(last, 0):
        return True
    return last >= 1 and max(first, 1) <= f.month_ordinal <= last


def month_window_anchor(first):
    """The cycle anchor of a month window starting at T+first: the close just before its first session."""
    if first <= 0:
        return lambda f: f.month_ordinal_from_end + 1 == first - 1
    if first == 1:
        return lambda f: f.month_ordinal_from_end == -1
    return lambda f: f.month_ordinal == first - 1


def month_window_rule(first, last, inside=2.0, outside=1.0, name=None, model="margin"):
    """
    GENERIC — registers nothing and is not a candidate. A factory for "exposure
    `inside` over sessions T+first .. T+last of every month, `outside`
    otherwise", MOC only: each change is made at a close auction, decided by
    whether the next SCHEDULED session is in the window, and an open auction
    keeps what is held. A scheduled entry or exit that falls on an unscheduled
    closure therefore happens at the next actual close. Freezing a rule means
    registering one of these under a pre-registered name.
    """
    def decide(v):
        if v.auction == "open":
            return v.held
        nxt = v.next_cal
        return inside if nxt is not None and in_month_window(nxt, first, last) else outside
    nm = name or f"month_window[{first:+d},{last:+d}] {inside:g}x in / {outside:g}x out"
    doc = (f"GENERIC month window, MOC only: {inside:g}x over T{first:+d}..T{last:+d}, "
           f"{outside:g}x otherwise")
    return lambda: Rule(nm, decide, 0, doc, False, model, baseline=outside,
                        anchor=month_window_anchor(first))


@dataclass
class MarginLegs:
    """Per scored session j: dates, the underlying's two leg returns, what idle cash earns and
    what borrowed money costs over the overnight leg, and prefix products over the 2S legs
    (leg 2j = session j's overnight leg, 2j+1 = its intraday leg)."""
    t: list
    dates: list
    prev_dates: list
    r_on: list
    r_id: list
    days: list
    gap: list
    g_cash: list
    g_fin: list
    P_r: list
    P_cash: list
    P_fin: list


def margin_legs(bars, s0, last, cash, spread, cal=None, accrual="calendar", distributions=None,
                closes_only=False):
    """Idle cash grows by (1+y)^a - 1 and borrowed money by (1+y+spread)^a - 1 on each overnight
    leg, a = accrual_years(D, accrual). `distributions` and `closes_only` as in build_legs."""
    if spread is None:
        raise ValueError("a margin run needs a stated financing spread over cash (--spread)")
    spread = float(spread)
    if not math.isfinite(spread) or not 0.0 <= spread <= 0.20:
        raise ValueError(f"spread {spread} is not an annual decimal in [0, 0.20]")
    dist = distributions or {}
    ML = MarginLegs([], [], [], [], [], [], [], [], [], [1.0], [1.0], [1.0])
    for t in range(s0 + 1, last + 1):
        p, b = bars[t - 1], bars[t]
        d0, d1 = p.ts.date(), b.ts.date()
        D = (d1 - d0).days
        if closes_only:
            r_on, r_id = 0.0, (b.close + dist.get(d1, 0.0)) / p.close - 1.0
        else:
            r_on = (b.open + dist.get(d1, 0.0)) / p.close - 1.0
            r_id = b.close / b.open - 1.0
        y = cash.at(d0)
        yf = accrual_years(D, accrual)
        g = (1.0 + y) ** yf - 1.0
        gf = (1.0 + y + spread) ** yf - 1.0
        ML.t.append(t)
        ML.dates.append(d1)
        ML.prev_dates.append(d0)
        ML.r_on.append(r_on)
        ML.r_id.append(r_id)
        ML.days.append(D)
        ML.gap.append(bool(cal.between(d0, d1)) if cal is not None else False)
        ML.g_cash.append(g)
        ML.g_fin.append(gf)
        ML.P_r.append(ML.P_r[-1] * (1.0 + r_on))
        ML.P_r.append(ML.P_r[-1] * (1.0 + r_id))
        ML.P_cash.append(ML.P_cash[-1] * (1.0 + g))
        ML.P_cash.append(ML.P_cash[-1])
        ML.P_fin.append(ML.P_fin[-1] * (1.0 + gf))
        ML.P_fin.append(ML.P_fin[-1])
    return ML


def interleave(w_on, w_id):
    """Per-session (overnight, intraday) exposures -> one exposure per leg."""
    out = []
    for a, b in zip(w_on, w_id):
        out.append(a)
        out.append(b)
    return out


def _push(out, leg, level, force=False):
    """Append a change, keeping legs strictly increasing and dropping no-ops."""
    if out and out[-1][0] == leg:
        out.pop()
    if not force and out and abs(out[-1][1] - level) <= EPS:
        return
    out.append((leg, level, force))


def levels_to_changes(levels):
    out = []
    for leg, e in enumerate(levels):
        if not out or abs(e - out[-1][1]) > EPS:
            out.append((leg, e, False))
    return out


def constant_changes(level, reset_legs):
    """Bar (A): one constant exposure, reset to target at the given legs (where the rule trades)."""
    out = [(0, level, False)]
    for leg in sorted(set(reset_legs)):
        if leg > 0:
            out.append((leg, level, True))
    return out


def margin_walk(changes, ML, cost, probes=(), detail=False):
    """
    THE margin engine. The rule, bar (A), buy-and-hold, the descriptive books and
    every placebo draw go through it, so a null differs from the run only in
    its exposures.

    `changes` = [(leg, exposure, force)], legs strictly increasing and the first
    at leg 0: the declared exposure from that leg's auction on (leg 2j is
    session j's overnight leg, set at the close auction before it; leg 2j+1 is
    its intraday leg, set at its open auction). Shares are held between
    entries. An auction trades only when the declared exposure changes, or when
    `force` is set (a benchmark reset), and takes the book from its DRIFTED
    exposure to the declared one: notional = |e - drifted| x equity before the
    trade; cost = cost x notional, out of equity. Positive cash earns g_cash,
    negative cash pays g_fin (cash + spread), both on the overnight leg.

    Between trades the book is A in shares plus C in cash, so its value at any
    later leg boundary b is exactly A*P_r[b]/P_r[l] + C*P[b]/P[l]: a placebo
    draw costs O(changes), not O(sessions). `probes` are ascending boundaries
    b in [0, 2S] whose equity — before any trade at b — is wanted.
    """
    n = 2 * len(ML.dates)
    Pr, Pc, Pf = ML.P_r, ML.P_cash, ML.P_fin
    A, C, decl = 0.0, 1.0, 0.0
    sides = entries = 0
    notional = paid = paid_frac = fin_paid = interest = 0.0
    pv = [None] * len(probes)
    pi = 0
    while pi < len(probes) and probes[pi] <= 0:
        pv[pi] = 1.0
        pi += 1
    marks = auctions = None
    if detail:
        marks = [0.0] * (n + 1)
        marks[0] = 1.0
        auctions = []
    if not changes or changes[0][0] != 0:
        raise ValueError("changes must start at leg 0")
    ruined = None
    K = len(changes)
    prev = -1
    for k in range(K):
        leg, e, force = changes[k]
        if leg <= prev:
            raise ValueError("changes must be strictly increasing in leg")
        prev = leg
        m = changes[k + 1][0] if k + 1 < K else n
        E = A + C
        if E <= 0.0:
            ruined = leg
            break
        if force or e - decl > EPS or decl - e > EPS:
            h = A / E
            dh = e - h
            nn = (dh if dh > 0.0 else -dh) * E
            if nn > EPS * E:
                c = nn * cost
                if h <= EPS and e > EPS:
                    entries += 1
                sides += 1
                notional += nn
                paid += c
                paid_frac += c / E
                E -= c
                if detail:
                    auctions.append((leg, nn, c))
            A = e * E
            C = E - A
            decl = e
        Q = Pc if C >= 0.0 else Pf
        ar = A / Pr[leg]
        cr = C / Q[leg]
        while pi < len(probes) and probes[pi] <= m:
            b = probes[pi]
            pv[pi] = ar * Pr[b] + cr * Q[b]
            pi += 1
        if detail:
            for b in range(leg + 1, m + 1):
                marks[b] = ar * Pr[b] + cr * Q[b]
        A2, C2 = ar * Pr[m], cr * Q[m]
        if C < 0.0:
            fin_paid += C - C2
        else:
            interest += C2 - C
        A, C = A2, C2
    if detail:
        for b in range(n + 1):
            if marks[b] <= 0.0:
                ruined = b if ruined is None else min(ruined, b)
                for bb in range(b, n + 1):
                    marks[bb] = 0.0
                break
    final = 0.0 if ruined is not None else A + C
    out = {"final": final, "probes": [0.0 if v is None else v for v in pv], "sides": sides,
           "entries": entries, "notional": notional, "cost_paid": paid, "cost_frac": paid_frac,
           "financing_paid": fin_paid, "interest_earned": interest, "ruined_at": ruined,
           "open_at_end": ruined is None and A > EPS * max(A + C, EPS)}
    if detail:
        out.update(marks=marks, auctions=auctions)
    return out


def stop_episodes(closes, level=STOP_LEVEL):
    """How many separate times equity falls `level` below its running peak (an episode ends at a new peak)."""
    peak, n, inside = 1.0, 0, False
    for c in closes:
        if c > peak:
            peak, inside = c, False
        elif not inside and peak > 0 and c / peak - 1.0 <= -level:
            n += 1
            inside = True
    return n


def score_margin(path, ML, start_date, levels, marks_mode="close"):
    """Every headline number for one margin path over the scored legs."""
    mk = path["marks"]
    closes, opens = mk[2::2], mk[1::2]
    S = len(closes)
    rets = session_returns(closes)
    ex = [r - g for r, g in zip(rets, ML.g_cash)]
    years = (ML.dates[-1] - start_date).days / 365.25
    st = replay._stats(rets, SESSIONS_PER_YEAR)
    sx = replay._stats(ex, SESSIONS_PER_YEAR)
    down = math.sqrt(sum(x * x for x in ex if x < 0) / S) if S else 0.0
    mean_ex = sum(ex) / S if S else 0.0
    mlist = [(start_date, "close", 1.0)]
    for j, d in enumerate(ML.dates):
        if marks_mode == "both":
            mlist.append((d, "open", opens[j]))
        mlist.append((d, "close", closes[j]))
    dd = drawdown(mlist)
    shares = {}
    for e in levels:
        key = round(e, 6)
        shares[key] = shares.get(key, 0) + 1
    mean_eq = sum(closes) / S if S else 0.0
    return {
        "final_equity": closes[-1], "total_return": closes[-1] - 1.0,
        "cagr": cagr_of(closes[-1], years), "years": years,
        "volatility": st["volatility"], "sharpe": sx["sharpe"],
        "sharpe_per_session": sx["sharpe_per_bar"], "skew": sx["skew"], "kurt": sx["kurt"],
        "sortino": (mean_ex / down * math.sqrt(SESSIONS_PER_YEAR)) if down > 0 else None,
        **dd, "marks": marks_mode,
        "stop_episodes": stop_episodes(closes), "legs": 2 * S,
        "mean_exposure": sum(levels) / len(levels),
        "leg_share_by_exposure": {k: v / len(levels) for k, v in sorted(shares.items())},
        "sides": path["sides"], "round_trips": path["entries"], "open_at_end": path["open_at_end"],
        "turnover_per_year": (path["notional"] / mean_eq / years) if mean_eq > 0 and years > 0 else None,
        "cost_paid": path["cost_paid"], "financing_paid": path["financing_paid"],
        "interest_earned": path["interest_earned"], "ruined_at": path["ruined_at"],
    }


def split_halves(dates, start_date, mode):
    """(cut, split): sessions [0, cut) are the first half. mode 'session' = the midpoint session
    index (r1-redteam D5); 'date' = the calendar midpoint of the window (round 1)."""
    S = len(dates)
    if mode == "session":
        cut = (S + 1) // 2
        return cut, dates[cut - 1]
    if mode != "date":
        raise ValueError("halves are split by 'session' or 'date'")
    split = start_date + dt.timedelta(days=(dates[-1] - start_date).days // 2)
    return bisect.bisect_right(dates, split), split


def halves_books(dates, start_date, books, g_cash, mode):
    cut, split = split_halves(dates, start_date, mode)
    out = {"mode": mode, "split": split.isoformat(), "cut": cut}
    for name, a, b in (("first", 0, cut), ("second", cut, len(dates))):
        if b - a < 2:
            out[name] = None
            continue
        d0 = start_date if a == 0 else dates[a - 1]
        years = (dates[b - 1] - d0).days / 365.25
        row = {"from": d0.isoformat(), "to": dates[b - 1].isoformat(), "sessions": b - a}
        for who, closes in books.items():
            base = 1.0 if a == 0 else closes[a - 1]
            seg = closes[a:b]
            if base <= 0:
                row[who] = None
                continue
            rets = session_returns([c / base for c in seg])
            ex = [r - g for r, g in zip(rets, g_cash[a:b])]
            row[who] = {"return": seg[-1] / base - 1.0, "cagr": cagr_of(seg[-1] / base, years),
                        "sharpe": replay._stats(ex, SESSIONS_PER_YEAR)["sharpe"],
                        "max_drawdown": replay.max_drawdown([base] + seg)}
        out[name] = row
    return out


def per_year_books(dates, books, auctions=None, prev_dates=None):
    rows, j0, S = [], 0, len(dates)
    base = {k: 1.0 for k in books}
    while j0 < S:
        y = dates[j0].year
        j1 = j0
        while j1 + 1 < S and dates[j1 + 1].year == y:
            j1 += 1
        row = {"year": y, "sessions": j1 - j0 + 1}
        for k, closes in books.items():
            row[k] = closes[j1] / base[k] - 1.0 if base[k] > 0 else None
            base[k] = closes[j1]
        if auctions is not None:
            row["sides"] = sum(1 for (leg, nn, c) in auctions
                               if (prev_dates[leg // 2] if leg % 2 == 0 else dates[leg // 2]).year == y)
        rows.append(row)
        j0 = j1 + 1
    return rows


def session_cycles(dates, cal, anchor):
    """Session-index ranges [j0, j1): a new cycle begins after the close of every scheduled session
    `anchor` marks. Unscheduled closures change nothing: cycles are cut by date."""
    anchors = [d for d in cal.sessions if d <= dates[-1] and anchor(cal.facts(d))]
    ids = [bisect.bisect_left(anchors, d) for d in dates]
    out, j0 = [], 0
    for j in range(1, len(dates) + 1):
        if j == len(dates) or ids[j] != ids[j0]:
            out.append((j0, j))
            j0 = j
    return out, anchors


def _internal(pat):
    """A leg-level pattern as its change points: [(leg offset, level)], the first at offset 0."""
    out = []
    for off, e in enumerate(pat):
        if not out or abs(e - out[-1][1]) > EPS:
            out.append((off, e))
    return out


class WithinCycle:
    """
    r1-redteam D7 for an overlay. In each cycle, the departure from the rule's
    BASELINE exposure — from the first departing session to the last, as one
    composite block — is moved intact to a random start inside its own cycle. A
    cycle with no departure is left alone. Leverage, legs, costs, cash and
    fills are the rule's own.

    wrap=False ('linear'): the start is uniform over the positions where the
    block fits without crossing the cycle's end. NOT an exact randomization
    test when the real block sits at an edge of its cycle (as a month-window
    rule's does): edge sessions are covered by fewer placements than interior
    ones, so the real placement's statistic is more dispersed around the null
    centre than a random placement's, and the p-value is U-shaped
    (r2-bench Build §B4).
    wrap=True ('circular'): the start is uniform over EVERY session of the cycle
    and the block wraps from the cycle's end to its start. Every session is
    covered equally often, the real placement is one of the cycle's rotations,
    and the test is exact for returns exchangeable under rotation within cycles.
    Offsets are relative to the cycle's first session; `observed` is the rule's.
    """

    def __init__(self, levels, cycles, baseline, wrap=False):
        self.n = len(levels)
        self.baseline = baseline
        self.wrap = bool(wrap)
        self.plan, self.observed = [], []
        for j0, j1 in cycles:
            dev = [j for j in range(j0, j1)
                   if abs(levels[2 * j] - baseline) > EPS or abs(levels[2 * j + 1] - baseline) > EPS]
            if not dev:
                continue
            f, l = dev[0], dev[-1]
            L = l - f + 1
            self.plan.append((j0, j1 - j0, _internal(levels[2 * f:2 * (l + 1)]), L))
            self.observed.append(f - j0)
        self.observed = tuple(self.observed)
        self.movable = sum(1 for (j0, Lc, internal, L) in self.plan if Lc > L)

    def arrange(self, offsets):
        out = []
        _push(out, 0, self.baseline)
        for (j0, Lc, internal, L), r in zip(self.plan, offsets):
            if r + L <= Lc:                                   # the block fits: no wrap
                for off, e in internal:
                    _push(out, 2 * (j0 + r) + off, e)
                if 2 * (j0 + r + L) < self.n:
                    _push(out, 2 * (j0 + r + L), self.baseline)
                continue
            w = 2 * (Lc - r)                                  # pattern legs before the cycle's end
            lvl_w = [e for off, e in internal if off <= w][-1]
            _push(out, 2 * j0, lvl_w)                         # the tail, at the cycle's start
            for off, e in internal:
                if off > w:
                    _push(out, 2 * j0 + off - w, e)
            _push(out, 2 * j0 + 2 * L - w, self.baseline)
            for off, e in internal:                           # the head, up to the cycle's end
                if off < w:
                    _push(out, 2 * (j0 + r) + off, e)
            if 2 * (j0 + Lc) < self.n:
                _push(out, 2 * (j0 + Lc), self.baseline)
        return out

    def draw(self, rng):
        if self.wrap:
            offs = tuple(rng.randrange(Lc) for (j0, Lc, internal, L) in self.plan)
        else:
            offs = tuple(rng.randrange(Lc - L + 1) for (j0, Lc, internal, L) in self.plan)
        return self.arrange(offs), offs


def _level_runs(levels):
    runs, s = [], 0
    for i in range(1, len(levels) + 1):
        if i == len(levels) or abs(levels[i] - levels[s]) > EPS:
            runs.append((s, i, levels[s]))
            s = i
    return runs


class ShiftPlacebo:
    """A circular shift of the whole exposure path by a whole number of sessions u (2u legs),
    u uniform in [1, S/2); arrange(0) is the rule's own path."""

    def __init__(self, levels):
        self.n = len(levels)
        self.runs = _level_runs(levels)

    def arrange(self, u):
        k, n = 2 * u, self.n
        pieces = []
        for s, e, lvl in self.runs:
            a, b = s + k, e + k
            if b <= n:
                pieces.append((a, lvl))
            elif a >= n:
                pieces.append((a - n, lvl))
            else:
                pieces.append((a, lvl))
                pieces.append((0, lvl))
        pieces.sort()
        out = []
        for a, lvl in pieces:
            _push(out, a, lvl)
        return out

    def draw(self, rng):
        u = rng.randrange(1, self.n // 2)
        return self.arrange(u), u


class BlocksPlacebo:
    """The same departures from baseline and the same baseline gaps (in sessions), each list
    shuffled; arrange(identity orders) is the rule's own path."""

    def __init__(self, levels, baseline):
        S = len(levels) // 2
        self.n, self.baseline = len(levels), baseline
        dev = [abs(levels[2 * j] - baseline) > EPS or abs(levels[2 * j + 1] - baseline) > EPS
               for j in range(S)]
        self.blocks, self.gaps = [], []
        self.first_is_block = dev[0] if S else True
        j0 = 0
        for j in range(1, S + 1):
            if j == S or dev[j] != dev[j0]:
                if dev[j0]:
                    self.blocks.append((_internal(levels[2 * j0:2 * j]), j - j0))
                else:
                    self.gaps.append(j - j0)
                j0 = j

    def identity(self):
        return tuple(range(len(self.blocks))), tuple(range(len(self.gaps)))

    def arrange(self, border, gorder):
        b = [self.blocks[i] for i in border]
        g = [self.gaps[i] for i in gorder]
        a1, a2 = (b, g) if self.first_is_block else (g, b)
        seq = []
        for i in range(max(len(a1), len(a2))):
            if i < len(a1):
                seq.append(a1[i])
            if i < len(a2):
                seq.append(a2[i])
        out, pos = [], 0
        _push(out, 0, self.baseline)
        for item in seq:
            if isinstance(item, int):
                _push(out, 2 * pos, self.baseline)
                pos += item
            else:
                internal, L = item
                for off, e in internal:
                    _push(out, 2 * pos + off, e)
                pos += L
        return out

    def draw(self, rng):
        border, gorder = list(range(len(self.blocks))), list(range(len(self.gaps)))
        rng.shuffle(border)
        rng.shuffle(gorder)
        out = self.arrange(border, gorder)
        return out, tuple(out)


class ProbeSet:
    """The leg boundaries a placebo draw is read at, and the statistics read from them:
    full-window CAGR, each half's CAGR, and CAGR with the crisis spans removed."""

    def __init__(self, dates, start_date, cut, spans):
        S = len(dates)
        self.n, self.cut, self.spans = 2 * S, cut, spans
        pts = {self.n, 2 * cut}
        for a, b in spans:
            pts.add(2 * a)
            pts.add(2 * (b + 1))
        self.points = sorted(pts)
        self.index = {p: i for i, p in enumerate(self.points)}
        self.years = (dates[-1] - start_date).days / 365.25
        d_cut = dates[cut - 1]
        self.y1 = (d_cut - start_date).days / 365.25
        self.y2 = (dates[-1] - d_cut).days / 365.25
        removed = sum(b - a + 1 for a, b in spans)
        self.y_excl = self.years * (S - removed) / S if S else 0.0

    def stats(self, pv):
        v = lambda b: pv[self.index[b]]
        En, Ec = v(self.n), v(2 * self.cut)
        g = En
        for a, b in self.spans:
            lo, hi = v(2 * a), v(2 * (b + 1))
            g = g * lo / hi if hi > 0 else 0.0
        return (cagr_of(En, self.years), cagr_of(Ec, self.y1),
                cagr_of(En / Ec, self.y2) if Ec > 0 else -1.0, cagr_of(g, self.y_excl))


def crisis_spans(dates, crises):
    """Session-index spans [a, b] (inclusive) of the scored sessions inside each crisis period."""
    out = []
    for lo, hi in crises:
        lo, hi = dt.date.fromisoformat(str(lo)), dt.date.fromisoformat(str(hi))
        a, b = bisect.bisect_left(dates, lo), bisect.bisect_right(dates, hi) - 1
        if a <= b:
            out.append((a, b))
    return out


def run_placebo(method, gen, observed_changes, observed_key, ML, cost, probes, draws, seed):
    """p-value of the rule's CAGR against `draws` arrangements from `gen`, plus the medians the gates
    read: each half's CAGR (G4) and CAGR with the crisis spans removed (G6), and a z for G7."""
    obs = probes.stats(margin_walk(observed_changes, ML, cost, probes.points)["probes"])
    rng = random.Random(f"edgelab/{seed}/{method}")
    cols = ([], [], [], [])
    seen = set()
    for _ in range(draws):
        ch, key = gen(rng)
        seen.add(key)
        s = probes.stats(margin_walk(ch, ML, cost, probes.points)["probes"])
        for c, x in zip(cols, s):
            c.append(x)
    degenerate = len(seen) <= 1 and (not seen or observed_key in seen)
    res = {"method": method, "draws": draws, "seed": seed, "unique_arrangements": len(seen),
           "degenerate": degenerate, "observed_cagr": obs[0], "observed_cagr_first_half": obs[1],
           "observed_cagr_second_half": obs[2], "observed_cagr_ex_crises": obs[3]}
    if degenerate or not draws:
        res.update(p_cagr=None)
        return res
    cg = cols[0]
    res["p_cagr"] = (1 + sum(1 for x in cg if x >= obs[0] - EPS)) / (1 + draws)
    for name, c in zip(("cagr", "cagr_first_half", "cagr_second_half", "cagr_ex_crises"), cols):
        srt = sorted(c)
        res[f"null_{name}_median"] = _quantile(srt, 0.5)
        res[f"null_{name}_q05"] = _quantile(srt, 0.05)
        res[f"null_{name}_q95"] = _quantile(srt, 0.95)
    mean = sum(cg) / len(cg)
    sd = math.sqrt(sum((x - mean) ** 2 for x in cg) / (len(cg) - 1)) if len(cg) > 1 else 0.0
    res["z_cagr"] = (obs[0] - mean) / sd if sd > 0 else None
    res["percentile_cagr"] = sum(1 for x in cg if x < obs[0]) / len(cg)
    res["above_median"] = obs[0] > res["null_cagr_median"]
    res["beats_median_each_half"] = (obs[1] > res["null_cagr_first_half_median"]
                                     and obs[2] > res["null_cagr_second_half_median"])
    res["ex_crises_minus_median"] = obs[3] - res["null_cagr_ex_crises_median"]
    return res


def _sharpe(xs):
    n = len(xs)
    m = sum(xs) / n
    v = sum((x - m) ** 2 for x in xs) / (n - 1)
    return m / math.sqrt(v) * math.sqrt(SESSIONS_PER_YEAR) if v > 0 else 0.0


def paired_block_se(a, b, block=10, draws=5000, seed=0):
    """
    The paired circular-block bootstrap standard error of dSR = SR(a) - SR(b),
    annualised: resample blocks of `block` consecutive sessions (wrapping at the
    end) at uniform random starts, the SAME blocks for both series, recompute
    both Sharpe ratios, and take the standard deviation of their difference.
    Block sums come from prefix sums, so a resample costs O(blocks), not
    O(sessions).
    """
    n = len(a)
    if n != len(b) or n < 3:
        raise ValueError("paired series of equal length >= 3")
    block = int(block)
    if block < 1:
        raise ValueError("block length >= 1")
    Pa, Qa, Pb, Qb = [0.0], [0.0], [0.0], [0.0]
    for x, y in zip(a, b):
        Pa.append(Pa[-1] + x)
        Qa.append(Qa[-1] + x * x)
        Pb.append(Pb[-1] + y)
        Qb.append(Qb[-1] + y * y)
    full, rem = divmod(n, block)
    lengths = [block] * full + ([rem] if rem else [])
    rng = random.Random(f"edgelab/{seed}/dsr-paired")
    rr = rng.randrange
    ann = math.sqrt(SESSIONS_PER_YEAR)
    out = []
    for _ in range(draws):
        sa = qa = sb = qb = 0.0
        for L in lengths:
            s = rr(n)
            e = s + L
            if e <= n:
                sa += Pa[e] - Pa[s]
                qa += Qa[e] - Qa[s]
                sb += Pb[e] - Pb[s]
                qb += Qb[e] - Qb[s]
            else:
                e -= n
                sa += Pa[n] - Pa[s] + Pa[e]
                qa += Qa[n] - Qa[s] + Qa[e]
                sb += Pb[n] - Pb[s] + Pb[e]
                qb += Qb[n] - Qb[s] + Qb[e]
        va = (qa - sa * sa / n) / (n - 1)
        vb = (qb - sb * sb / n) / (n - 1)
        out.append(((sa / n) / math.sqrt(va) if va > 0 else 0.0) * ann
                   - ((sb / n) / math.sqrt(vb) if vb > 0 else 0.0) * ann)
    m = sum(out) / draws
    return math.sqrt(sum((x - m) ** 2 for x in out) / (draws - 1)), out


def dsr_paired(a, b, n_trials, n_sensitivity=100, block=10, draws=5000, seed=0):
    """
    The deflated Sharpe against a benchmark (r1-redteam §3.5): DSR =
    Phi(dSR / SE - E[max Z_N]), dSR = SR(a) - SR(b) on returns in excess of
    cash, annualised; SE = the paired circular-block bootstrap SE of dSR;
    E[max Z_N] = the expected maximum of N independent standard normals
    (combine.expected_max_sharpe(N, 1)). Replaces round 1's single-Sharpe SE,
    which is right only when the two books correlate at ~0.5 (r2-bench §1b).
    """
    d_sr = _sharpe(a) - _sharpe(b)
    se, _ = paired_block_se(a, b, block, draws, seed)
    ma, mb = sum(a) / len(a), sum(b) / len(b)
    sab = sum((x - ma) * (y - mb) for x, y in zip(a, b))
    saa = sum((x - ma) ** 2 for x in a)
    sbb = sum((y - mb) ** 2 for y in b)
    out = {"dSR": d_sr, "se": se, "block": block, "draws": draws, "seed": seed,
           "sr_rule": _sharpe(a), "sr_benchmark": _sharpe(b),
           "corr": sab / math.sqrt(saa * sbb) if saa > 0 and sbb > 0 else None,
           "se_single_sharpe": math.sqrt(SESSIONS_PER_YEAR / (len(a) - 1))}
    for key, N in (("primary", int(n_trials)), ("sensitivity", int(n_sensitivity))):
        emz = combine.expected_max_sharpe(N, 1.0)
        z = d_sr / se - emz if se > 0 else None
        out[key] = {"trials": N, "E_max_Z": emz, "z": z,
                    "dsr": NormalDist().cdf(z) if z is not None else None,
                    "dSR_for_dsr_0.5": se * emz, "dSR_for_dsr_0.8": se * (emz + 0.8416212335729143)}
    return out


def episodes_of(levels, baseline, merge_gap=EPISODE_MERGE_GAP):
    """Maximal runs of sessions departing from baseline; runs separated by fewer than `merge_gap`
    baseline sessions are one episode (r1-redteam D6). [(first, last)] session indices."""
    S = len(levels) // 2
    runs, j = [], 0
    while j < S:
        if abs(levels[2 * j] - baseline) > EPS or abs(levels[2 * j + 1] - baseline) > EPS:
            k = j
            while k + 1 < S and (abs(levels[2 * k + 2] - baseline) > EPS
                                 or abs(levels[2 * k + 3] - baseline) > EPS):
                k += 1
            if runs and j - runs[-1][1] - 1 < merge_gap:
                runs[-1] = (runs[-1][0], k)
            else:
                runs.append((j, k))
            j = k + 1
        else:
            j += 1
    return runs


def _drop_top(values, top):
    """(total, the `top` largest POSITIVE values summed, total without them)."""
    pos = sorted((v for v in values if v > 0), reverse=True)[:top]
    total = sum(values)
    return total, sum(pos), total - sum(pos)


def g6_inputs(levels, baseline, rets, ML, cycles, cut, bar_rets=None, top=TOP_EPISODES):
    """
    G6's inputs in every form proposed, until the gate text is settled:
    - redteam_r1: per episode (merged runs of departure from baseline), the
      rule's log return minus cash; the 5 largest positive episodes as a share
      of the sum (r1-redteam §3.2: pass if <= 0.50);
    - flow_formula: per cycle, the sum of D_t = (e_t - mean e)(r_t - f_t), f =
      cash + spread, e_t the session's mean declared exposure, no costs; the
      sum without the 5 largest positive cycles (r2-flow G6': pass if >= 0);
    - book_simple / book_log: the same per-cycle test on the walked books'
      session excess over bar (A), R_rule - R_A or ln(1+R_rule) - ln(1+R_A)
      (costs, financing and drift included; r2-redteam's amendment is the log).
    Cycles are counted per half by the half they start in.
    """
    eps = episodes_of(levels, baseline)
    vals = []
    for a, b in eps:
        vals.append(sum(math.log1p(rets[j]) - math.log1p(ML.g_cash[j]) for j in range(a, b + 1)))
    total, top_sum, _ = _drop_top(vals, top)
    share = top_sum / total if total > 0 else None
    S = len(ML.dates)
    e_s = [(levels[2 * j] + levels[2 * j + 1]) / 2.0 for j in range(S)]
    ebar = sum(levels) / len(levels)
    series = {"flow_formula": [(e_s[j] - ebar) * ((1.0 + ML.r_on[j]) * (1.0 + ML.r_id[j]) - 1.0
                                                   - ML.g_fin[j]) for j in range(S)]}
    if bar_rets is not None:
        series["book_simple"] = [x - y for x, y in zip(rets, bar_rets)]
        series["book_log"] = [math.log1p(x) - math.log1p(y) for x, y in zip(rets, bar_rets)]
    out = {
        "episodes": len(eps), "episodes_first_half": sum(1 for a, b in eps if a < cut),
        "episodes_second_half": sum(1 for a, b in eps if a >= cut), "merge_gap": EPISODE_MERGE_GAP,
        "cycles": len(cycles), "cycles_first_half": sum(1 for j0, j1 in cycles if j0 < cut),
        "cycles_second_half": sum(1 for j0, j1 in cycles if j0 >= cut),
        "redteam_r1": {"definition": "per episode: the rule's log return minus cash over its sessions; "
                                     "the 5 largest positive episodes as a share of the sum over all "
                                     "episodes (r1 gate: <= 0.50)",
                       "sum": total, "top5": top_sum, "share": share,
                       "pass": share is not None and share <= 0.5},
    }
    defs = {"flow_formula": "per cycle: sum of D_t = (e_t - mean e)(r_t - f_t), f = cash + spread, no "
                            "costs; the sum without the 5 largest positive cycles (gate: >= 0)",
            "book_simple": "per cycle: sum of R_rule - R_A from the walked books (costs, financing and "
                           "drift included); without the 5 largest positive cycles (gate: >= 0)",
            "book_log": "per cycle: sum of ln(1+R_rule) - ln(1+R_A) from the walked books; without "
                        "the 5 largest positive cycles (gate: >= 0)"}
    for name, x in series.items():
        per_cycle = [sum(x[j0:j1]) for j0, j1 in cycles]
        tot, tops, rest = _drop_top(per_cycle, top)
        out[name] = {"definition": defs[name], "sum": tot, "top5": tops, "sum_without_top5": rest,
                     "pass": rest >= 0}
    return out


def timing_book(r_rule, r_bar, n_trials=None, n_sensitivity=100, block=10, draws=5000, seed=0):
    """
    The rule's session excess over bar (A) as a series of its own, in two forms:
    'log', d_t = ln(1+R_rule) - ln(1+R_A), which sums to the log wealth ratio and
    so charges the variance drag (r2-redteam G5'); 'simple', D_t = R_rule - R_A
    (r2-flow G5'). For each: mean and SD per session; z on i.i.d. sessions; the
    annualised Sharpe of the series with its circular-block bootstrap SE (the
    paired bootstrap of (series, 0), i.e. the same blocks of both books); the
    analytic z = SR sqrt(T-1) / sqrt(1 - skew SR + (kurt-1)/4 SR^2) (Bailey &
    Lopez de Prado, per-session SR); and, with n_trials, the deflated value
    Phi(min(z_boot, z_analytic) - E[max Z_N]) at N and at the sensitivity N.
    """
    out = {}
    for form in ("log", "simple"):
        if form == "log":
            x = [math.log1p(a) - math.log1p(b) for a, b in zip(r_rule, r_bar)]
        else:
            x = [a - b for a, b in zip(r_rule, r_bar)]
        n = len(x)
        st = replay._stats(x, SESSIONS_PER_YEAR)
        m = sum(x) / n
        sd = st["volatility"] / math.sqrt(SESSIONS_PER_YEAR)
        sr = st["sharpe_per_bar"]
        denom = math.sqrt(max(1e-12, 1.0 - st["skew"] * sr + (st["kurt"] - 1.0) / 4.0 * sr * sr))
        z_an = sr * math.sqrt(n - 1) / denom
        se = paired_block_se(x, [0.0] * n, block, draws, seed)[0] if draws and draws >= 2 else None
        z_boot = st["sharpe"] / se if se else None
        z_used = z_an if z_boot is None else min(z_boot, z_an)
        row = {"sessions": n, "mean_per_session": m, "mean_annual": m * SESSIONS_PER_YEAR,
               "sd_per_session": sd, "tracking_error": st["volatility"], "sum": sum(x),
               "z_iid": sr * math.sqrt(n), "sharpe": st["sharpe"], "se_boot": se, "z_boot": z_boot,
               "skew": st["skew"], "kurt": st["kurt"], "z_analytic": z_an, "z_used": z_used,
               "block": block, "draws": draws, "seed": seed}
        if n_trials is not None and se:
            for key, N in (("primary", int(n_trials)), ("sensitivity", int(n_sensitivity))):
                emz = combine.expected_max_sharpe(N, 1.0)
                row[key] = {"trials": N, "E_max_Z": emz, "dsr": NormalDist().cdf(z_used - emz),
                            "z_for_dsr_0.8": emz + 0.8416212335729143}
        out[form] = row
    return out


def g7_inputs(placebo_res, tb):
    """G7's veto statistic in each proposed form, with both proposed thresholds: r1-redteam's
    'same sign' (veto when the rule is on the wrong side of its null) and r2-flow's G7' (veto only
    when z < -1). The freeze picks the statistic and the threshold."""
    out = {}
    if placebo_res and not placebo_res.get("degenerate") and placebo_res.get("p_cagr") is not None:
        z = placebo_res["z_cagr"]
        out["placebo_cagr"] = {"z": z, "percentile": placebo_res["percentile_cagr"],
                               "veto_same_sign": not placebo_res["above_median"],
                               "veto_z_below_minus_1": z is not None and z < -1.0}
    for form in ("log", "simple"):
        if tb and form in tb:
            t = tb[form]
            out[f"timing_{form}"] = {"z": t["z_used"], "z_boot": t["z_boot"], "z_analytic": t["z_analytic"],
                                     "z_iid": t["z_iid"], "veto_same_sign": t["mean_per_session"] <= 0,
                                     "veto_z_below_minus_1": t["z_used"] < -1.0}
    return out


def sso_switch_path(levels, series, s0, last, cash, cal, k=2, expense_ratio=0.0095,
                    cost_under=0.0, cost_fund=0.0, accrual="calendar", distributions=None,
                    closes_only=False):
    """
    DESCRIPTIVE, never a gate: a cash-account way to hold a 1x / kx overlay —
    the underlying at 1x, switched into a MODELLED k-times daily-reset fund at
    each entry and back at each exit (4 sides a window). The fund is build_legs'
    LETF model: expense + (k-1) x cash, accrued on the overnight leg. None when
    the exposures are not all 1 or k.
    """
    if any(abs(e - 1.0) > EPS and abs(e - k) > EPS for e in levels):
        return None
    bars = series.bars
    U = build_legs(bars, s0, last, CashRate(rate=0.0), 1, distributions=distributions,
                   closes_only=closes_only)
    F = build_legs(bars, s0, last, cash, k, expense_ratio, cal, accrual, distributions, closes_only)
    E, held, sides, paid = 1.0, None, 0, 0.0
    closes = []
    for leg, e in enumerate(levels):
        want = "fund" if abs(e - k) <= EPS else "under"
        if want != held:
            c = (cost_under if want == "under" else cost_fund) * E
            if held is not None:
                c += (cost_under if held == "under" else cost_fund) * E
                sides += 1
            sides += 1
            paid += c
            E -= c
            held = want
        j = leg // 2
        if leg % 2 == 0:
            E *= 1.0 + (F.i_on[j] if held == "fund" else U.r_on[j])
        else:
            E *= 1.0 + (F.i_id[j] if held == "fund" else U.r_id[j])
            closes.append(E)
    return {"closes": closes, "sides": sides, "cost_paid": paid, "k": k, "expense_ratio": expense_ratio,
            "cost_bps_per_side_under": cost_under * 1e4, "cost_bps_per_side_fund": cost_fund * 1e4}


def load_distributions(path):
    """
    Cash distributions to add back, from a CSV with a date column ('ex_date' or
    'date') and an amount column ('amount_usd' or 'amount'), in the file's price
    units per share. Returns {"path", "sha256", "rows": {date: amount}}.
    """
    with open(path, "rb") as f:
        raw = f.read()
    rows = {}
    rdr = csv.reader(raw.decode("utf-8").splitlines())
    head = [h.strip().lower() for h in next(rdr, [])]
    di = next((head.index(c) for c in ("ex_date", "date") if c in head), None)
    ai = next((head.index(c) for c in ("amount_usd", "amount") if c in head), None)
    if di is None or ai is None:
        raise ValueError(f"{path}: header needs an 'ex_date' (or 'date') and an 'amount_usd' "
                         f"(or 'amount') column")
    for n, row in enumerate(rdr, start=2):
        if not row or all(not c.strip() for c in row):
            continue
        try:
            d, a = dt.date.fromisoformat(row[di].strip()), float(row[ai])
        except (ValueError, IndexError) as e:
            raise ValueError(f"{path} row {n}: {e}")
        if not math.isfinite(a) or a <= 0:
            raise ValueError(f"{path} row {n}: amount {a} is not a payout")
        if d in rows:
            raise ValueError(f"{path} row {n}: {d} appears twice")
        rows[d] = a
    if not rows:
        raise ValueError(f"{path}: no distributions")
    return {"path": path, "sha256": hashlib.sha256(raw).hexdigest(), "rows": rows}


def place_distributions(dist, series, first, last):
    """
    Which add-backs apply to the scored sessions first..last (dates). A payout
    on or before the file's declared total-return cutoff is already in its
    prices and is skipped, never added twice; a file declared adjusted with no
    cutoff takes none (integrity fails). An ex-date inside the window with no
    bar cannot be placed (integrity fails).
    """
    prov = series.provenance
    adj, thru = prov.get("adjusted"), prov.get("total_return_through")
    thru = dt.date.fromisoformat(str(thru)) if thru else None
    bar_dates = {b.ts.date() for b in series.bars}
    out = {"path": dist["path"], "sha256": dist["sha256"], "applied": {}, "already_adjusted": [],
           "outside_window": [], "unplaceable": [], "ok": True, "problem": None}
    for d in sorted(dist["rows"]):
        a = dist["rows"][d]
        if adj is True and thru is None:
            out["ok"] = False
            out["problem"] = ("the file is declared adjusted with no total-return cutoff, so an add-back "
                              "would count a payout twice (declare --total-return-through)")
            return out
        if thru is not None and d <= thru:
            out["already_adjusted"].append(d)
        elif d < first or d > last:
            out["outside_window"].append(d)
        elif d not in bar_dates:
            out["unplaceable"].append(d)
        else:
            out["applied"][d] = a
    if out["unplaceable"]:
        out["ok"] = False
        out["problem"] = "ex-date(s) inside the window with no bar: " + ", ".join(
            x.isoformat() for x in out["unplaceable"])
    return out


def declared_windows(levels, baseline, dates, start_date):
    """Each run of sessions whose declared exposure departs from baseline, as executed:
    (entry close, exit close, sessions held). The entry close is the close before the run's first
    session; the exit close is its last session's close; a run still open at the end says so."""
    S = len(levels) // 2
    dep = [abs(levels[2 * j] - baseline) > EPS or abs(levels[2 * j + 1] - baseline) > EPS
           for j in range(S)]
    out, j = [], 0
    while j < S:
        if dep[j]:
            k = j
            while k + 1 < S and dep[k + 1]:
                k += 1
            out.append({"entry_close": (start_date if j == 0 else dates[j - 1]).isoformat(),
                        "exit_close": dates[k].isoformat(), "sessions": k - j + 1,
                        "open_at_end": k == S - 1})
            j = k + 1
        else:
            j += 1
    return out


def check_window_list(path, declared):
    """G0: the declared exposure path against a frozen window list (CSV with entry_exec,
    exit_exec, sessions_held_with_bars and complete columns; its complete rows are compared)."""
    with open(path, "rb") as f:
        raw = f.read()
    sha = hashlib.sha256(raw).hexdigest()
    rows = list(csv.DictReader(raw.decode("utf-8").splitlines()))
    need = {"entry_exec", "exit_exec", "sessions_held_with_bars", "complete"}
    if not rows or not need <= set(rows[0]):
        return False, f"{path}: needs columns {', '.join(sorted(need))}", sha
    want = [(r["entry_exec"], r["exit_exec"], int(r["sessions_held_with_bars"]))
            for r in rows if r["complete"].strip().lower() == "true"]
    got = [(w["entry_close"], w["exit_close"], w["sessions"]) for w in declared]
    if any(w["open_at_end"] for w in declared):
        return False, f"the declared path is still away from baseline at the last scored close", sha
    if got == want:
        return True, f"{len(got)} windows reproduced exactly ({os.path.basename(path)} sha256 {sha})", sha
    diff = next((i for i, (a, b) in enumerate(zip(got, want)) if a != b), min(len(got), len(want)))
    return False, (f"{len(got)} declared vs {len(want)} listed; first difference at #{diff + 1}: "
                   f"declared {got[diff] if diff < len(got) else None} vs listed "
                   f"{want[diff] if diff < len(want) else None}"), sha


def total_return_status(prov, last_date, applied):
    """r1-redteam G0: the benchmark is total return over the scored window."""
    adj, thru = prov.get("adjusted"), prov.get("total_return_through")
    if adj is not True:
        if applied:
            return True, (f"declared adjusted={adj}; {len(applied)} payout(s) added back (completeness "
                          f"is the add-back file's claim)")
        return False, f"the file is not declared total-return (adjusted={adj})"
    if not thru:
        return True, "declared total-return throughout"
    thru = dt.date.fromisoformat(str(thru))
    if thru >= last_date:
        return True, f"total-return through {thru}, after the last scored session"
    if applied:
        return True, f"total-return through {thru}; {len(applied)} later payout(s) added back"
    return False, (f"price-only after {thru}, inside the scored window, and nothing added back "
                   f"(--distributions)")


def integrity_check(series, qc, leak, log, prereg=None, placed=None, extra=()):
    """G0 (r1-redteam §3.2): the items that make a run VOID. No performance number is printed
    unless every item passes."""
    items = [("barqc", qc["verdict"] == "pass", f"verdict {qc['verdict']}"),
             ("leak check", leak["checked"] > 0 and not leak["differences"],
              f"{leak['checked']} decisions re-run on truncated bars, {len(leak['differences'])} "
              f"difference(s)"),
             ("information sets", all(n == today for (today, auction, n, held, w) in log),
              "every decision saw exactly the bars closed before its session (open auction: through "
              "close[t-1]; close auction: the same plus open[t])"),
             ("calendar", True, "scheduled NYSE rules only (barqc.nyse_holidays); no bar date enters "
                                "a rule's calendar facts (by construction; tested)"),
             ("dividend basis declared", series.provenance.get("adjusted") is not None,
              f"adjusted={series.provenance.get('adjusted')}, total-return through "
              f"{series.provenance.get('total_return_through') or 'not stated'}")]
    items.extend(extra)
    if placed is not None:
        items.append(("distributions added back", placed["ok"],
                      placed["problem"] or (
                          f"{len(placed['applied'])} applied ("
                          + ", ".join(f"{d.isoformat()} {a:g}" for d, a in sorted(placed["applied"].items()))
                          + f"); {len(placed['already_adjusted'])} already in the prices, "
                          f"{len(placed['outside_window'])} outside the window; {placed['path']} "
                          f"sha256 {placed['sha256']}")))
    sha = None
    if prereg:
        try:
            with open(prereg, "rb") as f:
                sha = hashlib.sha256(f.read()).hexdigest()
            items.append(("pre-registration", True, f"{prereg} sha256 {sha}"))
        except OSError as e:
            items.append(("pre-registration", False, f"{prereg} unreadable: {e}"))
    return {"pass": all(ok for _, ok, _ in items), "items": items, "prereg_sha256": sha}


def _window(dates, warmup, start=None, end=None, start_close=None):
    """(s0, last): scoring starts at the close auction of bar s0 and ends at the close of bar last.
    `start_close` names that first close exactly (it must be a bar); `start` instead names the first
    scored SESSION (scoring then starts at the close before it)."""
    if start_close is not None:
        if start_close not in set(dates):
            raise ValueError(f"start close {start_close} is not a bar in this file")
        s0 = dates.index(start_close)
        if s0 < warmup:
            raise ValueError(f"start close {start_close} leaves {s0} bars for a warm-up of {warmup}")
    else:
        first = 0 if start is None else bisect.bisect_left(dates, start)
        s0 = max(warmup, first - 1, 0)
    last = len(dates) - 1 if end is None else bisect.bisect_right(dates, end) - 1
    return s0, last


def synthetic_like(dates, seed=0, sigma=0.0121, mu=4.6e-4, extra=None, symbol="SYN"):
    """SYNTHETIC bars on the given dates (dates only are taken from any real file): i.i.d.
    normal session returns, mean `mu`, sd `sigma`, split 0.358 / 0.642 of the variance between the
    overnight and intraday legs; `extra[j]` is added to session j's return."""
    rng = random.Random(f"edgelab/synthetic/{seed}")
    px, out = 100.0, []
    for j, d in enumerate(dates):
        ro = rng.gauss(mu * 0.67, sigma * math.sqrt(0.358))
        ri = rng.gauss(mu * 0.33, sigma * math.sqrt(0.642)) + (extra[j] if extra else 0.0)
        o = px * (1.0 + ro)
        c = o * (1.0 + ri)
        out.append(B.Bar(dt.datetime(d.year, d.month, d.day, tzinfo=B.UTC), o, max(o, c), min(o, c), c, 1e6))
        px = c
    return B.Series(symbol, "1d", out, {"source": "synthetic (edgelab.synthetic_like)",
                                        "fetched_at": "1970-01-01T00:00:00+00:00", "adjusted": True})


def harness_selfcheck(dates, rule, cells, start_close=None, end=None, seed=0, block=10, draws=5000,
                      closes_only=False, accrual="calendar"):
    """
    The pre-registration's synthetic harness checks 1-4, on SYNTHETIC prices laid
    on the real file's bar DATES (no price of the file is read), with the frozen
    rule and the gated (cash, spread) cells. Returns G0 items (name, ok, note).
    1. Across the cells, the log timing book's annual mean moves by no more than
       the calendar-day accrual residuals printed for them: for every cell,
       |m(cell) - m(first)| <= |resid(cell)| + |resid(first)| + 0.1 bp/yr.
    2. Its tracking error is within 5% of sqrt(p(1-p)) sigma (p = mean exposure
       above baseline; sigma = the synthetic underlying's session sd, annualised).
    3. With a known timing effect (20 bp a session added inside the windows), the
       G5' z (min of bootstrap and analytic) is within 5% of mean sqrt(years) / TE.
    4. The Sharpe difference vs bar (A) is a paired one: corr in [0.90, 0.97], its
       paired bootstrap SE in [0.05, 0.10], and under half the single-Sharpe SE.
    """
    items = []
    kw = dict(placebo_methods=(), placebo_draws=0, start_close=start_close, end=end, seed=seed,
              leak_samples=10, leak_changes=10, closes_only=closes_only, accrual=accrual)
    base = synthetic_like(dates, seed)
    r1 = run_margin(base, rule, cells, dsr_draws=0, **kw)
    if not r1["cells"]:
        return [("harness self-check", False, "the synthetic run itself failed integrity")]
    c0 = r1["cells"][0]
    m0 = c0["timing_book"]["log"]["mean_annual"]
    rs0 = c0["accrual_residual"]["residual"]
    worst = max((abs(c["timing_book"]["log"]["mean_annual"] - m0)
                 - abs(c["accrual_residual"]["residual"]) - abs(rs0)) for c in r1["cells"])
    items.append(("self-check 1: cash/spread", worst <= 1e-5,
                  f"largest |move of d's annual mean| minus the two residuals = {worst * 1e4:+.3f} bp/yr "
                  f"(limit +0.1) over {len(r1['cells'])} cells"))
    p = r1["p_hat"] - r1["baseline"]
    bd = [b.ts.date() for b in base.bars]
    a0 = bd.index(dt.date.fromisoformat(r1["window"]["start_close"]))
    a1 = bd.index(dt.date.fromisoformat(r1["window"]["last_session"]))
    cl = [b.close for b in base.bars[a0:a1 + 1]]
    sig = replay._stats([y / x - 1.0 for x, y in zip(cl, cl[1:])], SESSIONS_PER_YEAR)["volatility"]
    te = c0["timing_book"]["log"]["tracking_error"]
    want = math.sqrt(p * (1 - p)) * sig
    items.append(("self-check 2: tracking error", abs(te / want - 1) <= 0.05,
                  f"TE(d) {te:.4%} vs sqrt(p(1-p)) sigma {want:.4%} (p {p:.4f}, sigma {sig:.2%}): "
                  f"ratio {te / want:.4f}"))
    inside = set()
    for w in r1["declared_windows"]:
        a = bd.index(dt.date.fromisoformat(w["entry_close"]))
        for j in range(a + 1, a + 1 + w["sessions"]):
            inside.add(j)
    extra = [20e-4 if j in inside else 0.0 for j in range(len(bd))]
    eff = synthetic_like(dates, seed, extra=extra)
    r3 = run_margin(eff, rule, cells[:1], dsr_draws=draws, dsr_block=block, **kw)
    t = r3["cells"][0]["timing_book"]["log"]
    zt = t["mean_annual"] * math.sqrt(t["sessions"] / SESSIONS_PER_YEAR) / t["tracking_error"]
    items.append(("self-check 3: G5' z", abs(t["z_used"] / zt - 1) <= 0.05,
                  f"z used {t['z_used']:.3f} (boot {t['z_boot']:.3f}, analytic {t['z_analytic']:.3f}) vs "
                  f"mean sqrt(years)/TE {zt:.3f}: ratio {t['z_used'] / zt:.4f}"))
    r4 = run_margin(base, rule, cells[:1], dsr_draws=draws, dsr_block=block, trials=1, **kw)
    c4 = r4["cells"][0]
    ds = c4["dsr"]
    single = math.sqrt(SESSIONS_PER_YEAR / (r4["window"]["sessions"] - 1))
    rho = ds["corr"]
    ok = 0.90 <= rho <= 0.97 and 0.05 <= ds["se"] <= 0.10 and ds["se"] < 0.5 * single
    items.append(("self-check 4: paired SE", ok,
                  f"corr {rho:.3f}; paired SE of dSR {ds['se']:.4f} vs single-Sharpe {single:.4f}"))
    return items


PLACEBO_METHODS = ("within_cycle", "within_cycle_circular", "shift", "blocks")
CLOSES_ONLY_NOTE = ("closes only: each session is one close-to-close step and no open is read; a "
                    "payout added back makes the ex-date's return (close + D) / close[t-1] - 1")
ACCRUAL_NOTE = {
    "calendar": "accrued by calendar days, (1+y)^(D/365) - 1 on each overnight leg (D = days since the "
                "previous close; the round-1 end-of-day convention)",
    "session": "accrued per session, (1+y)^(1/252) - 1 on each overnight leg whatever its calendar "
               "days (r2-redteam R4)"}


def run_margin(series, rule, cells, trials=None, trials_sensitivity=100, seed=0, start=None,
               end=None, placebo_methods=("within_cycle",), placebo_draws=1000,
               dsr_benchmark="constant", dsr_draws=5000, dsr_block=10, halves_mode="session",
               marks_mode="close", crises=DEFAULT_CRISES, leak_samples=100, leak_changes=200,
               prereg=None, sso=None, start_close=None, accrual="calendar", distributions=None,
               closes_only=False, expect_sha256=None, window_list=None, expect_addbacks=None,
               extra_integrity=(), integrity_only=False):
    """
    One margin-model rule, one file, every stress cell in one invocation.
    `cells` = [(cost_bps_per_side, CashRate, spread)]; the FIRST is primary. The
    rule's decisions, the leak check and the integrity block do not depend on
    costs or rates, so they are computed once; every cell re-walks the books.
    `distributions` is load_distributions()'s result: payouts added back on
    their ex-date's overnight leg for every book alike. Nothing that depends on
    a price is computed when integrity (G0) fails.
    """
    factory = _as_factory(rule)
    r0 = factory()
    if r0.model != "margin":
        raise ValueError(f"{r0.name} is a weight-model rule: use run()")
    if not cells:
        raise ValueError("at least one (cost, cash, spread) cell")
    cells = [(float(c), cr if isinstance(cr, CashRate) else CashRate(rate=float(cr)), sp)
             for c, cr, sp in cells]
    for c, _, sp in cells:
        if not math.isfinite(c) or not 0 <= c < 1000:
            raise ValueError(f"cost {c} bp per side is not a cost")
        if sp is None:
            raise ValueError("a margin run needs a stated financing spread over cash (--spread)")
    for m in placebo_methods:
        if m not in PLACEBO_METHODS:
            raise ValueError(f"placebo {m!r} is one of {', '.join(PLACEBO_METHODS)}")
    if dsr_benchmark not in ("constant", "buy_and_hold"):
        raise ValueError("the deflated Sharpe is computed against 'constant' (bar A) or 'buy_and_hold'")
    if closes_only and marks_mode != "close":
        raise ValueError("a closes-only run marks closes only (--marks close)")
    if trials is not None and int(trials) < 1:
        raise ValueError("trials counts every specification tried, >= 1")
    if marks_mode not in ("close", "both"):
        raise ValueError("marks are 'close' or 'both'")
    if dsr_draws == 1 or dsr_draws < 0 or (trials is not None and not dsr_draws):
        raise ValueError("the bootstrap SE needs at least 2 draws (0 skips it, and then --trials too)")
    accrual_years(1, accrual)
    other_accrual = "session" if accrual == "calendar" else "calendar"

    qc = gate(series)
    bars = series.bars
    dates_all = [b.ts.date() for b in bars]
    cal = Calendar(dates_all[0], dates_all[-1])
    s0, last = _window(dates_all, r0.warmup, start, end, start_close)
    if last - s0 < 3:
        raise Blocked(f"{series.describe()}: {last - s0} scored session(s) — nothing to measure")
    w_on, w_id, log = decide_all(series, r0, cal, s0, last, 1)
    levels = interleave(w_on, w_id)
    if closes_only and any(abs(levels[i] - levels[i - 1]) > EPS for i in range(1, len(levels), 2)):
        raise ValueError(f"{r0.name} changes exposure at an open auction: a closes-only run cannot "
                         f"price that (drop --closes-only)")
    leak = leak_check(series, factory, log, cal, leak_samples, leak_changes, seed, 1)
    start_date = dates_all[s0]
    dates = dates_all[s0 + 1:last + 1]
    placed = place_distributions(distributions, series, dates[0], dates[-1]) if distributions else None
    applied = placed["applied"] if placed else None
    prov = series.provenance
    extra = list(extra_integrity)
    sha = prov.get("sha256")
    if expect_sha256:
        ok = sha == str(expect_sha256).strip().lower()
        extra.append(("file sha256", ok, f"{os.path.basename(prov.get('path') or '')} {sha}"
                      + ("" if ok else f" — expected {expect_sha256}")))
    else:
        extra.append(("file sha256", True, f"{sha} (no expected hash given)"))
    declared = declared_windows(levels, r0.baseline, dates, start_date)
    if window_list:
        ok, note, _ = check_window_list(window_list, declared)
        extra.append(("window list", ok, note))
    if expect_addbacks is not None:
        got = sorted(applied or {})
        want = sorted(dt.date.fromisoformat(str(x)) for x in expect_addbacks)
        extra.append(("add-backs as frozen", got == want,
                      f"applied {', '.join(d.isoformat() for d in got) or 'none'}"
                      + ("" if got == want else f" — expected {', '.join(d.isoformat() for d in want)}")))
    extra.append(("total-return benchmark",) + total_return_status(prov, dates[-1], applied))
    integ = integrity_check(series, qc, leak, log, prereg, placed, extra)
    cycles, anchors = session_cycles(dates, cal, r0.anchor or (lambda f: f.is_month_end))
    cut, split = split_halves(dates, start_date, halves_mode)
    spans = crisis_spans(dates, crises)
    probes = ProbeSet(dates, start_date, cut, spans)
    rule_changes = levels_to_changes(levels)
    trade_legs = [leg for leg, e, f in rule_changes if leg > 0]
    p_hat = sum(levels) / len(levels)
    days = [(d1 - d0).days for d0, d1 in zip([start_date] + dates[:-1], dates)]
    p_hat_days = sum(levels[2 * j] * D for j, D in enumerate(days)) / sum(days)
    lf_levels = [1.0 if e > r0.baseline + EPS else 0.0 for e in levels]
    gens = {}
    if "within_cycle" in placebo_methods:
        wc = WithinCycle(levels, cycles, r0.baseline)
        gens["within_cycle"] = (wc.draw, wc.observed)
    if "within_cycle_circular" in placebo_methods:
        wcc = WithinCycle(levels, cycles, r0.baseline, wrap=True)
        gens["within_cycle_circular"] = (wcc.draw, wcc.observed)
    if "shift" in placebo_methods:
        sp_ = ShiftPlacebo(levels)
        gens["shift"] = (sp_.draw, 0)
    if "blocks" in placebo_methods:
        bp = BlocksPlacebo(levels, r0.baseline)
        gens["blocks"] = (bp.draw, tuple(rule_changes))
    aset = set(anchors)
    complete = start_date in aset and dates[-1] in aset
    tail_note = None
    if prov.get("total_return_through") and not applied:
        tail_note = (f"the file is price-only after {prov['total_return_through']} and no distribution "
                     f"was added back: every book is charged each later payout as a loss on its "
                     f"ex-date, in proportion to its exposure that night")
    out = {
        "edgelab_version": EDGELAB_VERSION, "model": "margin",
        "rule": r0.name, "rule_doc": r0.doc, "baseline": r0.baseline,
        "max_exposure": r0.max_exposure, "warmup": r0.warmup,
        "symbol": series.symbol, "path": prov.get("path"),
        "source": prov.get("source"), "adjusted": prov.get("adjusted"),
        "total_return_through": prov.get("total_return_through"),
        "integrity": integ, "leak_check": leak, "qc_verdict": qc["verdict"],
        "distributions": ({k_: v for k_, v in placed.items() if k_ != "applied"}
                          | {"applied": {d.isoformat(): x for d, x in placed["applied"].items()}}
                          if placed else None),
        "window": {"start_close": start_date.isoformat(), "first_session": dates[0].isoformat(),
                   "last_session": dates[-1].isoformat(), "sessions": len(dates),
                   "legs": len(levels), "cycles": len(cycles),
                   "window_starts_and_ends_on_anchors": bool(complete),
                   "halves": {"mode": halves_mode, "split": split.isoformat(), "cut": cut},
                   "crisis_spans": [(dates[a].isoformat(), dates[b].isoformat()) for a, b in spans]},
        "settings": {"trials": trials, "trials_sensitivity": trials_sensitivity, "seed": seed,
                     "placebo_methods": list(placebo_methods), "placebo_draws": placebo_draws,
                     "dsr_benchmark": dsr_benchmark, "dsr_draws": dsr_draws, "dsr_block": dsr_block,
                     "marks": marks_mode, "crises": [list(c) for c in crises], "sso": sso,
                     "accrual": accrual, "closes_only": bool(closes_only)},
        "conventions": {"drift": DRIFT_NOTE, "instrument": MARGIN_NOTE,
                        "prices": (CLOSES_ONLY_NOTE if closes_only else
                                   "two legs per session: overnight close[t-1]->open[t] and intraday "
                                   "open[t]->close[t]; a payout added back is credited on the overnight "
                                   "leg, (open + D) / close[t-1] - 1"),
                        "cash": f"idle cash and borrowed money {ACCRUAL_NOTE[accrual]}",
                        "information": INFO_NOTE,
                        "dividends": dividend_note(prov.get("adjusted"), prov.get("total_return_through")),
                        "price_only_tail": tail_note,
                        "bar_A": f"constant exposure {p_hat:.6f} = the rule's mean declared "
                                 f"exposure over its {len(levels)} scored legs; reset at the "
                                 f"{len(trade_legs)} auctions where the rule trades"},
        "p_hat": p_hat, "p_hat_calendar_days": p_hat_days, "declared_windows": declared,
        "cells": [],
    }
    if not integ["pass"] or integrity_only:
        return out                      # VOID (or asked for integrity only): no performance number
    for cost_bps, cash, spread in cells:
        cost = cost_bps / 1e4
        ML = margin_legs(bars, s0, last, cash, spread, cal, accrual, applied, closes_only)
        rp = margin_walk(rule_changes, ML, cost, detail=True)
        a_changes = constant_changes(p_hat, trade_legs)
        ap = margin_walk(a_changes, ML, cost, detail=True)
        bp_ = margin_walk([(0, 1.0, False)], ML, cost, detail=True)
        lp = margin_walk(levels_to_changes(lf_levels), ML, cost, detail=True)
        S_rule = score_margin(rp, ML, start_date, levels, marks_mode)
        S_A = score_margin(ap, ML, start_date, [p_hat] * len(levels), marks_mode)
        S_B = score_margin(bp_, ML, start_date, [1.0] * len(levels), marks_mode)
        S_L = score_margin(lp, ML, start_date, lf_levels, marks_mode)
        books = {"rule": rp["marks"][2::2], "bar_A": ap["marks"][2::2], "buy_and_hold": bp_["marks"][2::2]}
        r_rets = session_returns(books["rule"])
        a_rets = session_returns(books["bar_A"])
        ML2 = margin_legs(bars, s0, last, cash, spread, cal, other_accrual, applied, closes_only)
        yrs = S_rule["years"]
        d_this = S_rule["cagr"] - S_A["cagr"]
        d_other = (cagr_of(margin_walk(rule_changes, ML2, cost)["final"], yrs)
                   - cagr_of(margin_walk(a_changes, ML2, cost)["final"], yrs))
        cell = {"cost_bps_per_side": cost_bps, "round_trip_bps": 2 * cost_bps, "cash": cash.label,
                "spread": spread, "rule": S_rule, "bar_A": S_A, "buy_and_hold": S_B,
                "long_flat_1x": S_L, "per_year": per_year_books(dates, books, rp["auctions"],
                                                                ML.prev_dates),
                "halves": halves_books(dates, start_date, books, ML.g_cash, halves_mode),
                "accrual_residual": {"accrual": accrual, "other": other_accrual,
                                     "rule_minus_A_cagr": d_this, "rule_minus_A_cagr_other": d_other,
                                     "residual": d_this - d_other}}
        if sso:
            sw = sso_switch_path(levels, series, s0, last, cash, cal, sso.get("k", 2),
                                 sso["expense_ratio"], cost, sso.get("cost_bps_per_side_fund",
                                                                     cost_bps) / 1e4,
                                 accrual, applied, closes_only)
            if sw is not None:
                cl = sw["closes"]
                cell["sso_switch"] = {**{k_: v for k_, v in sw.items() if k_ != "closes"},
                                      "cagr": cagr_of(cl[-1], S_rule["years"]),
                                      "total_return": cl[-1] - 1.0,
                                      "max_drawdown": replay.max_drawdown([1.0] + cl)}
            else:
                cell["sso_switch"] = "not applicable: exposures are not all 1x or kx"
        cell["placebo"] = {}
        for m, (gen, okey) in gens.items():
            cell["placebo"][m] = run_placebo(m, gen, rule_changes, okey, ML, cost, probes,
                                             placebo_draws, seed)
        bench = books["bar_A"] if dsr_benchmark == "constant" else books["buy_and_hold"]
        b_rets = session_returns(bench)
        ex_r = [x - g for x, g in zip(r_rets, ML.g_cash)]
        ex_b = [x - g for x, g in zip(b_rets, ML.g_cash)]
        cell["dsr"] = (dsr_paired(ex_r, ex_b, trials, trials_sensitivity, dsr_block, dsr_draws, seed)
                       if trials is not None else None)
        if cell["dsr"] is not None:
            cell["dsr"]["benchmark"] = dsr_benchmark
        cell["timing_book"] = timing_book(r_rets, a_rets, trials, trials_sensitivity, dsr_block,
                                          dsr_draws, seed)
        cell["g6"] = g6_inputs(levels, r0.baseline, r_rets, ML, cycles, cut, a_rets)
        wc_res = cell["placebo"].get(placebo_methods[0]) if placebo_methods else None
        cell["g6"]["drop_crises_minus_placebo_median"] = (wc_res or {}).get("ex_crises_minus_median")
        cell["g7"] = g7_inputs(wc_res, cell["timing_book"])
        out["cells"].append(cell)
    return out


def decompose(series, start=None, end=None):
    """
    Buy-and-hold split into its overnight and intraday legs: DESCRIPTIVE — no
    rule, no cost, no cash. It exists to reproduce EVIDENCE.md "Day run" §C on
    SPY-1d.csv as a check of the leg arithmetic. On any other file it is NEW
    information about the overnight leg, which is a test, and it waits for a
    frozen pre-registration like any other.
    """
    gate(series)
    bars = series.bars
    dates = [b.ts.date() for b in bars]
    cal = Calendar(dates[0], dates[-1])
    first = 0 if start is None else bisect.bisect_left(dates, start)
    s0 = max(first - 1, 0)
    last = len(bars) - 1 if end is None else bisect.bisect_right(dates, end) - 1
    legs = build_legs(bars, s0, last, CashRate(rate=0.0), 1, 0.0, cal)

    def part(lo, hi):
        on, idr = legs.r_on[lo:hi], legs.r_id[lo:hi]
        p_on = p_id = 1.0
        for x in on:
            p_on *= 1.0 + x
        for x in idr:
            p_id *= 1.0 + x
        a, b = replay._stats(on, SESSIONS_PER_YEAR), replay._stats(idr, SESSIONS_PER_YEAR)
        return {"from_close": (dates[s0] if lo == 0 else legs.dates[lo - 1]).isoformat(),
                "to_close": legs.dates[hi - 1].isoformat(), "sessions": hi - lo,
                "overnight": p_on - 1.0, "intraday": p_id - 1.0, "whole": p_on * p_id - 1.0,
                "mean_bp_overnight": 1e4 * sum(on) / len(on),
                "mean_bp_intraday": 1e4 * sum(idr) / len(idr),
                "sharpe_overnight": a["sharpe"], "sharpe_intraday": b["sharpe"]}
    S = len(legs.dates)
    split = dates[s0] + dt.timedelta(days=(legs.dates[-1] - dates[s0]).days // 2)
    cut = bisect.bisect_right(legs.dates, split)
    return {"symbol": series.symbol, "path": series.provenance.get("path"),
            "whole": part(0, S), "split_date": split.isoformat(),
            "first_half": part(0, cut), "second_half": part(cut, S),
            "close_to_close_check": bars[last].close / bars[s0].close - 1.0,
            "gap_legs": [d.isoformat() for d, g in zip(legs.dates, legs.gap) if g],
            "calendar": calendar_report(series, cal)}


def dividend_note(adjusted, total_return_through=None):
    """Where a dividend lands in the leg split — the bias that matters most for a two-leg rule."""
    if total_return_through:
        return (f"total-return THROUGH {total_return_through} (each ex-date's dividend added back on "
                f"that day's OVERNIGHT leg), price-only AFTER it: a later ex-date's drop lands in an "
                f"overnight leg with no dividend credited, and a book holding more exposure that night "
                f"is charged more of it (r1-quartermaster §5; r2-bench §1a)")
    if adjusted is True:
        return ("in the prices as stated (total-return): each ex-date's dividend is added back in "
                "that day's OVERNIGHT leg, which is where a holder of record earns it")
    return ("NOT in the prices as stated (or not stated): each ex-date's price drop lands in an "
            "OVERNIGHT leg with no dividend credited, so overnight exposure — and buy-and-hold — "
            "is understated by about the distribution yield, and a rule that is flat overnight "
            "into ex-dates is flattered. Use a total-return file for any rule that holds overnight")


def instrument_note(symbol, k, expense_ratio):
    if k == 1:
        return f"{symbol} as traded (1x)"
    return (f"LEVERAGED VARIANT — A MODEL, NOT DATA: a {k}x daily-reset fund built from {symbol}'s "
            f"bars. Overnight {k}*r_on; intraday {k}*r_id*(1+r_on)/(1+{k}*r_on) (reset at the "
            f"previous close); close-to-close {k}*r_cc; less {expense_ratio:.2%}/yr expense and "
            f"financing of {k - 1} x the cash rate, accrued on calendar days on the overnight "
            f"leg. No tracking error, no swap spread, the ETF's own bars not used.")


# =================================================================== rendering

def _p(x, nd=1):
    return "n/a" if x is None else f"{x * 100:+.{nd}f}%"


def _f(x, fmt="{:.2f}"):
    return "n/a" if x is None else fmt.format(x)


def render(r):
    s, b = r["strategy"], r["benchmark"]
    st, w = r["settings"], r["window"]
    L = ["=" * 100,
         f"EDGELAB v{r['edgelab_version']} · rule {r['rule']} on {r['symbol']} · "
         f"{os.path.basename(r['path'] or '')}",
         "=" * 100]
    integ = r.get("integrity")
    if integ and not integ["pass"]:
        lk = r["leak_check"]
        L += [render_integrity(integ),
              f"LEAK CHECK       {lk['checked']} decisions re-run: {len(lk['differences'])} difference(s) "
              f"— NOT A RESULT until this is zero"]
        return "\n".join(L)
    if r["test_only_rule"]:
        L.append("TEST-ONLY RULE — exists for the test suite; its numbers are not a candidate's")
    L += [f"COST CONVENTION  {st['cost_bps_per_side']:g} bp PER SIDE on traded notional — a round "
          f"trip (in and out) costs {st['round_trip_bps']:g} bp.",
          f"                 {COST_NOTE}",
          f"CASH             {st['cash']}, {CASH_NOTE}",
          f"INSTRUMENT       {r['conventions']['instrument']}",
          f"INFORMATION      {INFO_NOTE}",
          f"DATA             {r['path']} · source {r['source']} · adjusted "
          f"{ {True: 'yes', False: 'no', None: 'NOT STATED'}[r['adjusted']] } (as stated, not "
          f"measured) · barqc {r['qc_verdict'].upper()}",
          f"DIVIDENDS        {r['conventions']['dividends']}",
          "                 " + render_calendar(r["calendar"]).replace("\n", "\n                 "),
          f"WINDOW           scored from the close auction of {w['start_close']} (warm-up "
          f"{w['warmup_bars']} bar(s)) to the close of {w['last_session']}: {w['sessions']} "
          f"sessions, {w['legs']} legs, {w['years']:.2f} years.",
          f"                 The benchmark buys at that same close auction and is scored over the "
          f"identical legs."]
    if w["gap_legs_in_window"]:
        L.append(f"                 {len(w['gap_legs_in_window'])} scored overnight leg(s) span a "
                 f"scheduled session with no bar: {', '.join(w['gap_legs_in_window'][:8])}")
    lk = r["leak_check"]
    L.append(f"LEAK CHECK       {lk['checked']} decisions re-run on truncated bars with a fresh rule "
             f"({lk['open']} open, {lk['close']} close): {len(lk['differences'])} difference(s)"
             + ("" if not lk["differences"] else "  ← NOT A RESULT until this is zero"))
    for d in lk["differences"][:5]:
        L.append(f"                   {d['date']} {d['auction']}: run {d['run']} vs check {d['check']}")
    if r["instrument_wiped_out"]:
        L.append(f"WIPED OUT        the modelled fund lost everything at the open on "
                 f"{', '.join(r['instrument_wiped_out'])}")
    lev = r["leveraged_buy_and_hold"]
    head = f"{'':34}{'strategy':>16}{'buy & hold':>16}" + (f"{'lev. b&h (model)':>18}" if lev else "")
    L += ["-" * 100, head]

    def row(label, key, fmt):
        cells = [fmt(x.get(key)) for x in (s, b) + ((lev,) if lev else ())]
        return f"{label:<34}" + "".join(f"{c:>16}" for c in cells[:2]) + \
            (f"{cells[2]:>18}" if lev else "")
    L += [row("total return (ROI on capital)", "total_return", _p),
          row("CAGR", "cagr", lambda x: _p(x, 2)),
          row("volatility (annualised)", "volatility", lambda x: _p(x, 1).lstrip("+")),
          row("Sharpe (excess of cash)", "sharpe", _f),
          row("Sortino (excess of cash)", "sortino", _f),
          row("max drawdown", "max_drawdown", _p),
          row("legs exposed", "exposure_share", lambda x: _p(x, 1).lstrip("+")),
          row("  overnight legs exposed", "exposure_share_overnight", lambda x: _p(x, 1).lstrip("+")),
          row("  intraday legs exposed", "exposure_share_intraday", lambda x: _p(x, 1).lstrip("+")),
          row("mean effective exposure", "mean_exposure", lambda x: _f(x, "{:.3f}")),
          row("capital-weighted exposure", "capital_weighted_exposure", lambda x: _f(x, "{:.3f}")),
          row("gross bp per leg per unit exposure", "gross_bp_per_unit_exposure", lambda x: _f(x, "{:+.2f}")),
          row("net bp per leg per unit exposure", "net_bp_per_unit_exposure", lambda x: _f(x, "{:+.2f}")),
          row("trades (sides)", "sides", lambda x: _f(x, "{:d}")),
          row("round trips (entries)", "round_trips", lambda x: _f(x, "{:d}")),
          row("turnover (x equity per year)", "turnover_per_year", lambda x: _f(x, "{:.1f}")),
          row("cost paid (x initial capital)", "cost_paid", lambda x: _f(x, "{:.4f}"))]
    L.append(f"{'max drawdown dates (strategy)':<34}peak {s['peak']} → trough {s['trough']} → "
             f"recovered {s['recovered']}")
    L.append(f"{'max drawdown dates (benchmark)':<34}peak {b['peak']} → trough {b['trough']} → "
             f"recovered {b['recovered']}")
    L.append(f"{'gross of cost (strategy)':<34}final {s['gross_final_equity']:.4f} vs net "
             f"{s['final_equity']:.4f}; CAGR {_p(s['gross_cagr'], 2)} gross")
    L += ["-" * 100, "PER YEAR (strategy, benchmark, difference; legs exposed; sides; cost as % of "
                     "equity at the year's start)"]
    for y in r["per_year"]:
        L.append(f"  {y['year']}  {y['sessions']:>3} sess  {_p(y['strategy']):>8}  "
                 f"{_p(y['benchmark']):>8}  {_p((y['strategy'] or 0) - (y['benchmark'] or 0)):>8}  "
                 f"{y['exposure_share']:>6.1%}  {y['sides']:>4}  "
                 f"{_f(y['cost_pct_of_start_equity'] and 100 * y['cost_pct_of_start_equity'], '{:.3f}')}%")
    h = r["halves"]
    L += ["-" * 100, f"HALVES (split by {h.get('mode', 'date')} at {h['split_date']})"]
    for name in ("first", "second"):
        x = h.get(name)
        if not x:
            L.append(f"  {name}: too short")
            continue
        L.append(f"  {name:<6} {x['from']} → {x['to']} ({x['sessions']} sess)  strategy CAGR "
                 f"{_p(x['strategy']['cagr'], 2)} Sharpe {_f(x['strategy']['sharpe'])} DD "
                 f"{_p(x['strategy']['max_drawdown'])}  |  buy&hold CAGR "
                 f"{_p(x['benchmark']['cagr'], 2)} Sharpe {_f(x['benchmark']['sharpe'])} DD "
                 f"{_p(x['benchmark']['max_drawdown'])}")
    L.append("-" * 100)
    if r["placebo"]:
        for m, p in r["placebo"].items():
            if p["degenerate"]:
                L.append(f"PLACEBO {m:<7} degenerate: every arrangement of this exposure is the "
                         f"same ({p['unique_arrangements']} unique in {p['draws']} draws) — it has "
                         f"no timing to test")
                continue
            L.append(f"PLACEBO {m:<7} {p['draws']} draws, seed {p['seed']}, "
                     f"{p['unique_arrangements']} unique arrangements: p(CAGR) = "
                     f"{p['p_cagr']:.4f}, p(Sharpe) = {p['p_sharpe']:.4f}; null CAGR median "
                     f"{_p(p['null_cagr_q'][0.5], 2)} [5% {_p(p['null_cagr_q'][0.05], 2)}, 95% "
                     f"{_p(p['null_cagr_q'][0.95], 2)}], null Sharpe median "
                     f"{_f(p['null_sharpe_q'][0.5])} [95% {_f(p['null_sharpe_q'][0.95])}]"
                     + (f"  — only {p['unique_arrangements']} distinct arrangements: this p is coarse"
                        if p["unique_arrangements"] < min(100, p["draws"]) else ""))
        pc = r.get("placebo_conservative") or {}
        if len(r["placebo"]) > 1 and pc.get("p_sharpe") is not None:
            L.append(f"PLACEBO reading  the larger p of the two is the conservative one: p(CAGR) = "
                     f"{pc['p_cagr']:.4f}, p(Sharpe) = {pc['p_sharpe']:.4f}")
    else:
        L.append("PLACEBO          not run (--placebo-draws 0)")
    ds = r["deflated_sharpe"]
    if ds:
        L.append(f"DEFLATED SHARPE  paired circular-block bootstrap vs buy & hold (excess of cash): dSR "
                 f"{ds['dSR']:+.4f}, SE {ds['se']:.4f} (corr {_f(ds['corr'], '{:.3f}')}; block {ds['block']}, "
                 f"{ds['draws']} resamples); N={ds['primary']['trials']}: z {ds['primary']['z']:+.3f}, DSR "
                 f"{ds['primary']['dsr']:.4f}; N={ds['sensitivity']['trials']}: DSR "
                 f"{ds['sensitivity']['dsr']:.4f}")
        d1 = r.get("deflated_sharpe_round1")
        if d1 and d1["dsr"] is not None:
            L.append(f"                 (round 1's single-Sharpe form, for comparison only, never a gate: "
                     f"{d1['dsr']:.4f})")
    else:
        L.append(f"DEFLATED SHARPE  not computed: pass --trials N (every specification ever tried; "
                 f"{_prior_trials_note()})")
    bs = r["bootstrap"]
    if bs:
        L.append(f"BOOTSTRAP        stationary, mean block {bs['block_len']} sessions, {bs['draws']} "
                 f"draws, seed {bs['seed']}: CAGR difference 95% CI "
                 f"[{_p(bs['cagr_diff_ci95'][0], 2)}, {_p(bs['cagr_diff_ci95'][1], 2)}], "
                 f"P(diff <= 0) = {bs['p_cagr_diff_le_0']:.3f}; Sharpe difference 95% CI "
                 f"[{bs['sharpe_diff_ci95'][0]:+.3f}, {bs['sharpe_diff_ci95'][1]:+.3f}]")
    else:
        L.append("BOOTSTRAP        not run (--boot-draws 0)")
    L += ["-" * 100, f"NOT MODELLED     {NOT_MODELLED}",
          "RECORD           nothing is written to the ledger; a run that is a trial needs a row in "
          "trials.json citing its saved output"]
    return "\n".join(L)


def render_integrity(integ):
    L = [f"INTEGRITY (G0)   {'PASS' if integ['pass'] else 'FAIL — VOID'}"]
    for name, ok, note in integ["items"]:
        L.append(f"   {'ok  ' if ok else 'FAIL'} {name:<26}{note}")
    if not integ["pass"]:
        L.append("VOID — no performance number is printed when an integrity item fails (r1-redteam G0)")
    return "\n".join(L)


def _cell_label(c):
    return f"{c['cost_bps_per_side']:g} bp/side · cash {c['cash']} · spread {c['spread']:.2%}"


def render_margin(r):
    """The report of one margin-model run: integrity first; nothing else when it fails."""
    w = r["window"]
    L = ["=" * 112,
         f"EDGELAB v{r['edgelab_version']} · MARGIN OVERLAY · rule {r['rule']} on {r['symbol']} · "
         f"{os.path.basename(r['path'] or '')}", "=" * 112, render_integrity(r["integrity"])]
    if not r["integrity"]["pass"]:
        return "\n".join(L)
    c0 = r["cells"][0]
    cv = r["conventions"]
    L += [f"COST CONVENTION  {c0['cost_bps_per_side']:g} bp PER SIDE on traded notional (primary) — a round "
          f"trip costs {c0['round_trip_bps']:g} bp. {COST_NOTE}",
          f"CASH, FINANCING  {c0['cash']}; borrowed money pays cash + {c0['spread']:.2%}/yr; {cv['cash']}",
          f"INSTRUMENT       {cv['instrument']}",
          f"DRIFT            {cv['drift']}",
          f"DIVIDENDS        {cv['dividends']}"]
    if cv.get("price_only_tail"):
        L.append(f"                 WARNING: {cv['price_only_tail']}")
    if r.get("distributions"):
        d = r["distributions"]
        L.append(f"                 added back on the ex-date's overnight leg, every book alike: "
                 + (", ".join(f"{k} {v:g}" for k, v in d["applied"].items()) or "none in the window")
                 + f" (from {os.path.basename(d['path'])}, sha256 {d['sha256'][:16]}…)")
    L += [f"INFORMATION      {INFO_NOTE}",
          f"WINDOW           from the close of {w['start_close']} to the close of {w['last_session']}: "
          f"{w['sessions']} sessions, {w['legs']} legs, {w['cycles']} cycles"
          + ("" if w["window_starts_and_ends_on_anchors"] else
             " — NOTE: the window does not start and end on cycle anchors, so its first or last "
             "cycle is partial"),
          f"                 halves split by {w['halves']['mode']} at {w['halves']['split']} "
          f"(first half = {w['halves']['cut']} sessions); crisis spans removed for G6: "
          + (", ".join(f"{a}..{b}" for a, b in w["crisis_spans"]) or "none in the window"),
          f"BAR (A)          {cv['bar_A']}; weighted by the calendar days of each overnight leg the "
          f"mean exposure would be {r['p_hat_calendar_days']:.6f}",
          f"BASELINE         {r['baseline']:g}x — placebos move departures from it",
          "-" * 112]
    cols = [("rule", c0["rule"]), ("bar (A)", c0["bar_A"]), ("buy & hold 1x", c0["buy_and_hold"]),
            ("1x long/flat*", c0["long_flat_1x"])]
    sw = c0.get("sso_switch")
    L.append(f"{'':32}" + "".join(f"{n:>17}" for n, _ in cols)
             + (f"{'SSO switch*':>17}" if isinstance(sw, dict) else ""))

    def row(label, key, fmt):
        cells = [fmt(x.get(key)) for _, x in cols]
        extra = ""
        if isinstance(sw, dict):
            extra = f"{fmt(sw.get(key)) if key in sw else '':>17}"
        return f"{label:<32}" + "".join(f"{c:>17}" for c in cells) + extra
    L += [row("total return (ROI on capital)", "total_return", _p),
          row("CAGR", "cagr", lambda x: _p(x, 2)),
          row("volatility (annualised)", "volatility", lambda x: _p(x, 1).lstrip("+")),
          row("Sharpe (excess of cash)", "sharpe", _f),
          row("Sortino (excess of cash)", "sortino", _f),
          row(f"max drawdown (marks: {c0['rule']['marks']})", "max_drawdown", _p),
          row("-15% STOP episodes", "stop_episodes", lambda x: _f(x, "{:d}")),
          row("mean exposure", "mean_exposure", lambda x: _f(x, "{:.4f}")),
          row("trades (sides)", "sides", lambda x: _f(x, "{:d}")),
          row("cost paid (x initial capital)", "cost_paid", lambda x: _f(x, "{:.4f}")),
          row("financing paid (x initial)", "financing_paid", lambda x: _f(x, "{:.4f}")),
          row("cash interest (x initial)", "interest_earned", lambda x: _f(x, "{:.4f}"))]
    L.append(f"{'max drawdown dates (rule)':<32}peak {c0['rule']['peak']} → trough {c0['rule']['trough']} "
             f"→ recovered {c0['rule']['recovered']}")
    L.append("* declared descriptive lines, never gates: the window alone at 1x (cash outside), and the "
             "cash-account switch into a modelled kx fund")
    ar = c0["accrual_residual"]
    L.append(f"ACCRUAL RESIDUAL CAGR(rule) − CAGR(A) is {_p(ar['rule_minus_A_cagr'], 3)} with financing "
             f"accrued by {ar['accrual']}, {_p(ar['rule_minus_A_cagr_other'], 3)} by {ar['other']}: "
             f"residual {_p(ar['residual'], 3)}")
    L += ["-" * 112, "PER YEAR (rule, bar A, buy & hold; rule sides)"]
    for y in c0["per_year"]:
        L.append(f"  {y['year']}  {y['sessions']:>3} sess  {_p(y['rule']):>8}  {_p(y['bar_A']):>8}  "
                 f"{_p(y['buy_and_hold']):>8}  {y.get('sides', 0):>4}")
    h = c0["halves"]
    L += ["-" * 112, f"HALVES (split by {h['mode']} at {h['split']})"]
    for name in ("first", "second"):
        x = h.get(name)
        if not x:
            L.append(f"  {name}: too short")
            continue
        L.append(f"  {name:<6} {x['from']} → {x['to']} ({x['sessions']} sess)  CAGR rule "
                 f"{_p(x['rule']['cagr'], 2)} · bar A {_p(x['bar_A']['cagr'], 2)} · B&H "
                 f"{_p(x['buy_and_hold']['cagr'], 2)}; Sharpe rule {_f(x['rule']['sharpe'])} · A "
                 f"{_f(x['bar_A']['sharpe'])} · B&H {_f(x['buy_and_hold']['sharpe'])}")
    L.append("-" * 112)
    for m, p in c0["placebo"].items():
        if p["degenerate"] or p.get("p_cagr") is None:
            why = (f"degenerate ({p['unique_arrangements']} arrangement(s)): no timing to test"
                   if p["degenerate"] else "not run (0 draws)")
            L.append(f"PLACEBO {m:<13}{why}")
            continue
        L.append(f"PLACEBO {m:<13}{p['draws']} draws, seed {p['seed']}, {p['unique_arrangements']} unique: "
                 f"p(CAGR) = {p['p_cagr']:.4f}; rule CAGR {_p(p['observed_cagr'], 2)} vs null median "
                 f"{_p(p['null_cagr_median'], 2)} [5% {_p(p['null_cagr_q05'], 2)}, 95% "
                 f"{_p(p['null_cagr_q95'], 2)}]; z {_f(p['z_cagr'])}; beats the median in each half: "
                 f"{'yes' if p['beats_median_each_half'] else 'no'}")
    ds = c0["dsr"]
    if ds:
        L.append(f"DEFLATED SHARPE  paired circular-block bootstrap vs {ds['benchmark']}: dSR "
                 f"{ds['dSR']:+.4f} (rule {ds['sr_rule']:.4f} − {ds['sr_benchmark']:.4f}), SE {ds['se']:.4f} "
                 f"(block {ds['block']}, {ds['draws']} resamples); N={ds['primary']['trials']}: z "
                 f"{ds['primary']['z']:+.3f}, DSR {ds['primary']['dsr']:.4f}; N={ds['sensitivity']['trials']}: "
                 f"DSR {ds['sensitivity']['dsr']:.4f}; dSR needed for DSR 0.5 / 0.8 at N="
                 f"{ds['primary']['trials']}: {ds['primary']['dSR_for_dsr_0.5']:.3f} / "
                 f"{ds['primary']['dSR_for_dsr_0.8']:.3f}")
    else:
        L.append(f"DEFLATED SHARPE  not computed: pass --trials N ({_prior_trials_note()})")
    tb = c0.get("timing_book")
    if tb:
        for form in ("log", "simple"):
            t = tb[form]
            dsr_txt = ""
            if "primary" in t:
                dsr_txt = (f"; deflated at N={t['primary']['trials']}: {t['primary']['dsr']:.4f} (needs z ≥ "
                           f"{t['primary']['z_for_dsr_0.8']:.2f} for 0.8), N={t['sensitivity']['trials']}: "
                           f"{t['sensitivity']['dsr']:.4f} (z ≥ {t['sensitivity']['z_for_dsr_0.8']:.2f})")
            L.append(f"TIMING BOOK {form:<7}rule − bar A per session ({'ln(1+R) − ln(1+R_A)' if form == 'log' else 'R − R_A'}): "
                     f"mean {_p(t['mean_annual'], 3)}/yr, tracking error {_p(t['tracking_error'], 2).lstrip('+')}; "
                     f"z boot {_f(t['z_boot'], '{:+.3f}')} (SE {t['se_boot']:.4f}), z analytic "
                     f"{t['z_analytic']:+.3f}, z i.i.d. {t['z_iid']:+.3f}; used {t['z_used']:+.3f}{dsr_txt}")
    g = c0["g6"]
    L += ["-" * 112,
          f"G6 INPUTS        episodes {g['episodes']} ({g['episodes_first_half']} / {g['episodes_second_half']} "
          f"by half; runs < {g['merge_gap']} sessions apart merge); cycles {g['cycles']} "
          f"({g['cycles_first_half']} / {g['cycles_second_half']} by the half they start in)",
          f"   redteam_r1    top-5 positive episodes' share of the summed log excess over cash: "
          f"{_f(g['redteam_r1']['share'], '{:.3f}')} (sum {g['redteam_r1']['sum']:+.4f}; r1 gate ≤ 0.50)"]
    for name in ("flow_formula", "book_simple", "book_log"):
        if name in g:
            x = g[name]
            L.append(f"   {name:<13} per-cycle sum {x['sum']:+.5f}; 5 largest positive cycles {x['top5']:+.5f}; "
                     f"without them {x['sum_without_top5']:+.5f} (gate ≥ 0: {'pass' if x['pass'] else 'fail'})")
    L.append(f"   drop-crises   CAGR(rule) − within-cycle placebo median, crisis spans removed from both: "
             f"{_p(g['drop_crises_minus_placebo_median'], 3)}")
    g7 = c0.get("g7") or {}
    if g7:
        L.append("G7 INPUTS        (read on the replication file; veto forms: r1 'same sign' | r2 'z < −1')")
        for name, x in g7.items():
            L.append(f"   {name:<13} z {_f(x['z'], '{:+.3f}')}"
                     + (f", percentile {x['percentile']:.3f}" if "percentile" in x else
                        f" (i.i.d. {x['z_iid']:+.3f})")
                     + f"; veto same-sign: {'YES' if x['veto_same_sign'] else 'no'}; veto z < −1: "
                       f"{'YES' if x['veto_z_below_minus_1'] else 'no'}")
    if len(r["cells"]) > 1:
        L += ["-" * 112, "STRESS GRID (every cell of the invocation; the first row is primary)",
              f"{'cost':>5}{'cash':>7}{'spread':>8}{'CAGR rule':>11}{'bar A':>8}{'B&H':>8}{'rule−A':>8}"
              f"{'rule−B&H':>9}{'MDD rule':>9}{'MDD A':>8}{'p WC':>7}{'DSR':>7}{'DSR100':>7}"
              f"{'z log':>7}{'DSRlog':>7}{'top5':>6}{'log-5':>8}{'crisis':>9}{'accr':>8}"]
        for c in r["cells"]:
            p = (c["placebo"].get("within_cycle") or {})
            ds = c["dsr"] or {}
            tl = (c.get("timing_book") or {}).get("log") or {}
            gl = c["g6"].get("book_log") or {}
            cash_v = c["cash"].split("%")[0] if "%" in c["cash"] else c["cash"][:6]
            L.append(f"{c['cost_bps_per_side']:>5g}{cash_v:>7}{c['spread']:>8.2%}"
                     f"{_p(c['rule']['cagr'], 2):>11}{_p(c['bar_A']['cagr'], 2):>8}"
                     f"{_p(c['buy_and_hold']['cagr'], 2):>8}"
                     f"{_p(c['rule']['cagr'] - c['bar_A']['cagr'], 2):>8}"
                     f"{_p(c['rule']['cagr'] - c['buy_and_hold']['cagr'], 2):>9}"
                     f"{_p(c['rule']['max_drawdown']):>9}{_p(c['bar_A']['max_drawdown']):>8}"
                     f"{_f(p.get('p_cagr'), '{:.4f}'):>7}"
                     f"{_f((ds.get('primary') or {}).get('dsr'), '{:.3f}'):>7}"
                     f"{_f((ds.get('sensitivity') or {}).get('dsr'), '{:.3f}'):>7}"
                     f"{_f(tl.get('z_used'), '{:+.2f}'):>7}"
                     f"{_f((tl.get('primary') or {}).get('dsr'), '{:.3f}'):>7}"
                     f"{_f(c['g6']['redteam_r1']['share'], '{:.2f}'):>6}"
                     f"{_f(gl.get('sum_without_top5'), '{:+.3f}'):>8}"
                     f"{_p(c['g6']['drop_crises_minus_placebo_median'], 2):>9}"
                     f"{_p(c['accrual_residual']['residual'], 3):>8}")
    L += ["-" * 112, f"NOT MODELLED     {NOT_MODELLED}; margin calls; whole-share rounding",
          "RECORD           nothing is written to the ledger; a run that is a trial needs a row in "
          "trials.json citing its saved output"]
    return "\n".join(L)


def offset_profile(series, offsets, labels, breaks, exclude=(), contrast=None, start=None, end=None):
    """
    DESCRIPTIVE — declared in advance; it cannot confirm or refute anything.
    The mean close-to-close return of the session at each offset from its
    month's last SCHEDULED session T (T+o for o in `offsets`; o <= 0 counts back
    inside the month, o >= 1 into the next), per group of months, with count
    and standard error. A month's group is decided by T's date: labels[0]
    before breaks[0], labels[i] from breaks[i-1]. Sessions whose overnight leg
    spans a missing scheduled session are left out, and so is every date in
    `exclude`. `contrast` = (offset, groups_a, groups_b) prints
    mean(offset | a) − mean(offset | b) with its SE (independent groups).
    """
    gate(series)
    if len(labels) != len(breaks) + 1:
        raise ValueError("one more label than break dates")
    breaks = [dt.date.fromisoformat(str(x)) for x in breaks]
    if breaks != sorted(breaks):
        raise ValueError("break dates must be increasing")
    bars = series.bars
    dates = [b.ts.date() for b in bars]
    cal = Calendar(dates[0], dates[-1])
    offs = sorted(set(int(o) for o in offsets))
    excl = {dt.date.fromisoformat(str(x)) for x in exclude}
    label_of = lambda T: labels[bisect.bisect_right(breaks, T)]
    cells = {(o, lab): [] for o in offs for lab in labels}
    skipped = {"gap legs": 0, "excluded dates": 0}
    for j in range(1, len(bars)):
        d = dates[j]
        if (start and d < start) or (end and d > end):
            continue
        if cal.between(dates[j - 1], d):
            skipped["gap legs"] += 1
            continue
        if d in excl:
            skipped["excluded dates"] += 1
            continue
        f = cal.facts(d)
        r = bars[j].close / bars[j - 1].close - 1.0
        o_own = f.month_ordinal_from_end + 1
        if o_own in offs:
            cells[(o_own, label_of(cal.last_session(d.year, d.month)))].append(r)
        if f.month_ordinal in offs:
            py, pm = (d.year, d.month - 1) if d.month > 1 else (d.year - 1, 12)
            cells[(f.month_ordinal, label_of(cal.last_session(py, pm)))].append(r)

    def st(xs):
        n = len(xs)
        if n == 0:
            return {"n": 0, "mean": None, "se": None}
        m = sum(xs) / n
        sd = math.sqrt(sum((x - m) ** 2 for x in xs) / (n - 1)) if n > 1 else None
        return {"n": n, "mean": m, "se": sd / math.sqrt(n) if sd is not None else None, "sd": sd}
    table = {f"{o:+d}|{lab}": st(cells[(o, lab)]) for o in offs for lab in labels}
    out = {"label": "DESCRIPTIVE — declared in advance; cannot confirm or refute",
           "symbol": series.symbol, "offsets": offs, "labels": list(labels),
           "breaks": [b.isoformat() for b in breaks], "excluded": sorted(x.isoformat() for x in excl),
           "skipped": skipped, "table": table}
    if contrast:
        o, ga, gb = contrast
        xa = [x for lab in ga for x in cells[(int(o), lab)]]
        xb = [x for lab in gb for x in cells[(int(o), lab)]]
        sa, sb = st(xa), st(xb)
        if sa["n"] > 1 and sb["n"] > 1:
            se = math.sqrt(sa["se"] ** 2 + sb["se"] ** 2)
            out["contrast"] = {"offset": int(o), "groups_a": list(ga), "groups_b": list(gb),
                               "mean_a": sa["mean"], "n_a": sa["n"], "mean_b": sb["mean"],
                               "n_b": sb["n"], "delta": sa["mean"] - sb["mean"], "se": se,
                               "t": (sa["mean"] - sb["mean"]) / se if se > 0 else None}
        else:
            out["contrast"] = {"offset": int(o), "error": "a group has fewer than 2 sessions"}
    return out


def render_offset_profile(p):
    L = [f"OFFSET PROFILE · {p['symbol']} · {p['label']}",
         f"mean close-to-close return by session offset from T (the month's last scheduled session), "
         f"bp, by group (breaks {', '.join(p['breaks'])}); skipped {p['skipped']}",
         f"{'offset':>7}" + "".join(f"{('group ' + str(lab)):>24}" for lab in p["labels"])]
    for o in p["offsets"]:
        cells = []
        for lab in p["labels"]:
            x = p["table"][f"{o:+d}|{lab}"]
            cells.append("n/a" if x["mean"] is None else
                         f"{1e4 * x['mean']:+7.1f} ±{1e4 * (x['se'] or 0):5.1f} (n {x['n']})")
        L.append(f"{('T' + format(o, '+d')) if o else 'T':>7}" + "".join(f"{c:>24}" for c in cells))
    c = p.get("contrast")
    if c and "delta" in c:
        L.append(f"declared contrast: mean r(T{c['offset']:+d} | {','.join(map(str, c['groups_a']))}) − "
                 f"mean r(T{c['offset']:+d} | {','.join(map(str, c['groups_b']))}) = "
                 f"{1e4 * c['delta']:+.1f} bp ± {1e4 * c['se']:.1f} (n {c['n_a']} vs {c['n_b']}) — "
                 f"descriptive; it cannot confirm or refute")
    elif c:
        L.append(f"declared contrast: {c['error']}")
    return "\n".join(L)


def _prior_trials_note():
    try:
        import ledger
        n, where = ledger.prior_trials()
        return f"ledger.prior_trials() says {n} before this run ({where})"
    except Exception as e:                          # a corrupt ledger must not hide the advice
        return f"ledger.prior_trials() unreadable: {type(e).__name__}"


def summary_table(rows):
    L = [f"{'symbol':<7}{'span':<25}{'sess':>6}{'CAGR s':>9}{'CAGR b':>9}{'Shp s':>7}{'Shp b':>7}"
         f"{'DD s':>8}{'DD b':>8}{'exp':>6}{'sides':>7}{'leak':>5}{'p plc':>7}{'DSR':>7}"
         f"   CAGR diff 95% CI", "-" * 132]
    for x in rows:
        if x.get("status") != "ok":
            L.append(f"{x['symbol']:<7}{x['status']}")
            continue
        r = x["result"]
        s, b, w = r["strategy"], r["benchmark"], r["window"]
        pc = (r.get("placebo_conservative") or {}).get("p_sharpe")
        ds = ((r.get("deflated_sharpe") or {}).get("primary") or {}).get("dsr")
        bs = r.get("bootstrap")
        ci = (f"[{_p(bs['cagr_diff_ci95'][0], 2)}, {_p(bs['cagr_diff_ci95'][1], 2)}]" if bs else "n/a")
        L.append(f"{r['symbol']:<7}{w['start_close'] + ' → ' + w['last_session']:<25}{w['sessions']:>6}"
                 f"{_p(s['cagr'], 2):>9}{_p(b['cagr'], 2):>9}{_f(s['sharpe']):>7}{_f(b['sharpe']):>7}"
                 f"{_p(s['max_drawdown']):>8}{_p(b['max_drawdown']):>8}{s['exposure_share']:>6.0%}"
                 f"{s['sides']:>7}{len(r['leak_check']['differences']):>5}"
                 f"{_f(pc, '{:.3f}'):>7}{_f(ds, '{:.3f}'):>7}   {ci}")
    return "\n".join(L)


def run_many(paths, rule, symbols=None, sources=None, adjusted=None, **kw):
    """The same rule on many files. A file barqc blocks is a row that says so, never a gap."""
    rows = []
    for i, p in enumerate(paths):
        sym = (symbols[i] if symbols else None) or symbol_from_path(p)
        src = sources[i] if sources else None
        adj = adjusted[i] if adjusted else None
        try:
            s = load(p, sym, src, adj)
            rows.append({"symbol": sym, "status": "ok", "result": run(s, rule, **kw)})
        except Blocked as e:
            rows.append({"symbol": sym, "status": f"BLOCKED: {e}"})
        except (B.Unparseable, B.NoProvenance) as e:
            rows.append({"symbol": sym, "status": f"REFUSED: {e}"})
    return rows


def _json_safe(r):
    def conv(o):
        if isinstance(o, dict):
            return {str(k): conv(v) for k, v in o.items()}
        if isinstance(o, (list, tuple)):
            return [conv(v) for v in o]
        if isinstance(o, float) and not math.isfinite(o):
            return str(o)
        if isinstance(o, (dt.date, dt.datetime)):
            return o.isoformat()
        return o
    return conv(r)


# =================================================================== cli

def _per_file(values, n, what, ap):
    if not values:
        return None
    if len(values) == 1:
        return values * n
    if len(values) != n:
        ap.error(f"give one {what} for all files or one per file ({n})")
    return values


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--rule", help="a registered rule (see --list-rules)")
    ap.add_argument("--csv", nargs="+", help="one or more daily bar files")
    ap.add_argument("--symbol", nargs="+", help="one per file; default: the file name up to its first '-'")
    ap.add_argument("--source", nargs="+", help="one for all files or one per file; recorded")
    ap.add_argument("--adjusted", nargs="+", choices=["yes", "no"], help="as stated, never measured")
    ap.add_argument("--cost-bps-per-side", type=float,
                    help="REQUIRED. Charged on the traded notional at every auction that trades; "
                         "a round trip costs twice this")
    ap.add_argument("--cash-yield", help="REQUIRED. An annual decimal (0.03), or a CSV of date,rate")
    ap.add_argument("--leverage", type=int, default=1, choices=[1, 2, 3],
                    help="the instrument: 1 = the file as traded; 2 or 3 = a MODELLED daily-reset fund")
    ap.add_argument("--expense-ratio", type=float, help="annual, required with --leverage 2 or 3")
    ap.add_argument("--start", type=dt.date.fromisoformat, help="first session to score (YYYY-MM-DD)")
    ap.add_argument("--end", type=dt.date.fromisoformat, help="last session to score (YYYY-MM-DD)")
    ap.add_argument("--trials", type=int, help="every specification ever tried, for the deflated Sharpe")
    ap.add_argument("--sr-var", type=float, help="override the Sharpe variance used for deflation")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--placebo-draws", type=int, default=1000)
    ap.add_argument("--placebo", choices=["shift", "blocks", "both"], default="both")
    ap.add_argument("--boot-draws", type=int, default=1000)
    ap.add_argument("--block-len", type=float, default=20.0, help="mean block length, sessions")
    ap.add_argument("--leak-samples", type=int, default=100)
    ap.add_argument("--out", help="write the full output (text, then JSON) here")
    ap.add_argument("--curves", metavar="DIR",
                    help="also write DIR/<symbol>-<rule>-curves.csv: per session, the weight held in "
                         "each leg, each leg's return, and both equity paths")
    ap.add_argument("--allow-test-rule", action="store_true",
                    help="let a TEST-ONLY rule run on a file (the test suite uses this)")
    ap.add_argument("--list-rules", action="store_true")
    ap.add_argument("--calendar-report", action="store_true",
                    help="bar dates against the scheduled calendar; computes no return")
    a = ap.parse_args(argv)

    if a.list_rules:
        for name in sorted(RULES):
            r = RULES[name]()
            print(f"{name:<24} warmup {r.warmup:<4} {'TEST ONLY  ' if r.test_only else ''}{r.doc}")
        return 0
    if not a.csv:
        ap.error("--csv is required")
    n = len(a.csv)
    if a.symbol and len(a.symbol) != n:
        ap.error("give one --symbol per --csv file")
    sources = _per_file(a.source, n, "--source", ap)
    adj = _per_file(a.adjusted, n, "--adjusted", ap)
    adj = [{"yes": True, "no": False}[x] for x in adj] if adj else None

    if a.calendar_report:
        text = []
        for i, p in enumerate(a.csv):
            try:
                s = load(p, a.symbol[i] if a.symbol else None, sources[i] if sources else None,
                         adj[i] if adj else None)
            except (B.Unparseable, B.NoProvenance) as e:
                text.append(f"{p}: REFUSED: {e}")
                continue
            qc = barqc.inspect(s)
            text.append(f"{p} · barqc {qc['verdict'].upper()}\n  "
                        + render_calendar(calendar_report(s)).replace("\n", "\n  "))
        out = "\n".join(text)
        print(out)
        if a.out:
            _write(a.out, out)
        return 0

    if not a.rule:
        ap.error("--rule is required (or --list-rules / --calendar-report)")
    if a.cost_bps_per_side is None:
        ap.error("--cost-bps-per-side is required: no default cost, because the repo has two "
                 "conventions and a silent one is how they get mixed")
    if a.cash_yield is None:
        ap.error("--cash-yield is required (0 is an answer; silence is not)")
    try:
        factory = get_rule(a.rule)
        if factory().test_only and not a.allow_test_rule:
            ap.error(f"{a.rule} is a TEST-ONLY rule; it exists for test_edgelab.py "
                     f"(--allow-test-rule to run it anyway)")
        cash = CashRate.parse(a.cash_yield)
    except (KeyError, ValueError) as e:
        print(f"REFUSED: {e}", file=sys.stderr)
        return 2
    kw = dict(cost_bps_per_side=a.cost_bps_per_side, cash=cash, leverage=a.leverage,
              expense_ratio=a.expense_ratio, start=a.start, end=a.end, trials=a.trials,
              sr_var=a.sr_var, seed=a.seed, placebo_draws=a.placebo_draws,
              placebo_method=a.placebo, boot_draws=a.boot_draws, block_len=a.block_len,
              leak_samples=a.leak_samples, keep_curves=bool(a.curves))
    try:
        rows = run_many(a.csv, factory, a.symbol, sources, adj, **kw)
    except (ValueError, LookAhead) as e:
        print(f"REFUSED: {type(e).__name__}: {e}", file=sys.stderr)
        return 2
    blocks = []
    if n > 1:
        blocks.append(f"EDGELAB · rule {a.rule} on {n} files · {a.cost_bps_per_side:g} bp PER SIDE "
                      f"(a round trip costs {2 * a.cost_bps_per_side:g} bp) · cash {cash.label}\n"
                      + summary_table(rows))
    for x in rows:
        blocks.append(render(x["result"]) if x["status"] == "ok" else f"{x['symbol']}: {x['status']}")
    if a.curves:
        for x in rows:
            if x["status"] == "ok":
                p = write_curves(x["result"], os.path.join(
                    a.curves, f"{x['symbol']}-{a.rule}-{os.path.basename(x['result']['path'] or 'x').rsplit('.', 1)[0]}-curves.csv"))
                print(f"wrote {p}", file=sys.stderr)
    text = "\n\n".join(blocks)
    print(text)
    if a.out:
        payload = [{"symbol": x["symbol"], "status": x["status"],
                    "result": _json_safe({k: v for k, v in (x.get("result") or {}).items()
                                          if k != "_curves"}) if x.get("result") else None}
                   for x in rows]
        _write(a.out, text + "\n\n" + json.dumps({"argv": sys.argv if argv is None else argv,
                                                  "runs": payload}, indent=1, default=str) + "\n")
        print(f"\nwrote {a.out}", file=sys.stderr)
    if any(x["status"] != "ok" for x in rows):
        return 2
    if any(x["result"]["leak_check"]["differences"] for x in rows):
        return 3
    return 0


def _write(path, text):
    d = os.path.dirname(os.path.abspath(path))
    os.makedirs(d, exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        f.write(text)
    os.replace(tmp, path)


if __name__ == "__main__":
    sys.exit(main())
