#!/usr/bin/env python3
"""
calendar_build.py — Quartermaster, round 1. Deterministic calendar artifacts.

NO RETURNS ARE COMPUTED HERE. The only inputs are barqc's rule-based NYSE
calendar and the DATES (column 1) of bar files. Prices are never read.

Writes (into the edge/data/calendar folder):
  nyse-sessions-1999-2026.csv   one row per scheduled NYSE session (barqc rules),
                                with ordinals, holiday adjacency, opex, quarter
                                end, and a closure flag for days the market did
                                not open although the rule calendar says it would
  holidays-1999-2026.csv        every scheduled holiday from barqc.nyse_holidays,
                                named, with the session before / after it
  calendar-vs-files.txt         every disagreement between the rule calendar and
                                each bar file's own dates

Run:  python3 -I -B calendar_build.py <repo tools/market dir> <bars dir> <nasdaq dir> <out dir>
"""
import csv
import datetime as dt
import os
import sys

TOOLS, BARS, NASDAQ, OUT = sys.argv[1:5]
sys.path.insert(0, TOOLS)
import barqc  # noqa: E402  (the repo's own calendar)

START, END = dt.date(1999, 1, 1), dt.date(2026, 12, 31)

# ---------------------------------------------------------------- holidays, named
def named_holidays(y):
    """Re-derive barqc.nyse_holidays(y) with names, and assert equality with barqc."""
    out = {}
    ny = dt.date(y, 1, 1)
    if ny.weekday() != 5:
        out[barqc._observed(ny)] = "New Year's Day"
    out[barqc._nth_weekday(y, 1, 0, 3)] = "Martin Luther King Jr. Day"
    out[barqc._nth_weekday(y, 2, 0, 3)] = "Washington's Birthday"
    out[barqc._easter(y) - dt.timedelta(days=2)] = "Good Friday"
    out[barqc._last_weekday(y, 5, 0)] = "Memorial Day"
    if y >= 2022:
        out[barqc._observed(dt.date(y, 6, 19))] = "Juneteenth"
    out[barqc._observed(dt.date(y, 7, 4))] = "Independence Day"
    out[barqc._nth_weekday(y, 9, 0, 1)] = "Labor Day"
    out[barqc._nth_weekday(y, 11, 3, 4)] = "Thanksgiving Day"
    out[barqc._observed(dt.date(y, 12, 25))] = "Christmas Day"
    assert set(out) == barqc.nyse_holidays(y), (y, sorted(set(out) ^ barqc.nyse_holidays(y)))
    return out

HOL = {}
for y in range(START.year - 1, END.year + 2):
    HOL.update(named_holidays(y))

SCHED = barqc.sessions_between(START, END)          # the rule calendar, 1999-2026
SCHED_SET = set(SCHED)

# ---------------------------------------------------------------- bar-file dates
def file_dates(path):
    with open(path, newline="") as f:
        rows = list(csv.reader(f))
    # skip comment lines and the header
    rows = [r for r in rows if r and not r[0].startswith("#")]
    return [dt.date.fromisoformat(r[0][:10]) for r in rows[1:]]

files = {}
for name in sorted(os.listdir(BARS)):
    if name.endswith(".csv") and name != "SPY-sessions.csv":
        files[f"bars/{name}"] = file_dates(os.path.join(BARS, name))
files["bars/SPY-sessions.csv (minute-derived complete sessions)"] = file_dates(
    os.path.join(BARS, "SPY-sessions.csv"))
for name in sorted(os.listdir(NASDAQ)):
    if name.endswith("-1d-nasdaq.csv"):
        files[f"edge/data/nasdaq/{name}"] = file_dates(os.path.join(NASDAQ, name))

# A scheduled session is a CLOSURE only if every bar file that spans the date
# lacks it AND at least two independent vendors span it; with one vendor it is
# reported as "absent, single source" and NOT treated as a closure by this
# script (see the KNOWN list below for what the record says).
def vendor_of(k):
    if "nasdaq" in k or k.endswith("SPY-1d-raw.csv"):
        return "nasdaq"
    if "agg" in k or "sessions" in k or (k.endswith("-1d.csv") and not k.endswith("SPY-1d.csv")):
        return "alpaca"
    return "stooq"
absent_by_date = {}
spanning = {}
for k, ds in files.items():
    if "sessions" in k:      # complete-sessions file omits half-days by design; not a calendar witness
        continue
    s = set(ds)
    lo, hi = min(ds), max(ds)
    for d in SCHED:
        if lo <= d <= hi:
            spanning.setdefault(d, []).append(k)
            if d not in s:
                absent_by_date.setdefault(d, []).append(k)

closure_candidates = []
for d, ks in sorted(absent_by_date.items()):
    span = spanning[d]
    if len(ks) == len(span):
        vendors = {vendor_of(k) for k in span}
        closure_candidates.append((d, len(span), sorted(vendors)))

# The record (EVIDENCE.md §E-15, DATA.md) names these unscheduled closures; each
# is checked against the files below rather than trusted.
KNOWN_CLOSURES = {
    dt.date(2001, 9, 11): "September 11 attacks",
    dt.date(2001, 9, 12): "September 11 attacks",
    dt.date(2001, 9, 13): "September 11 attacks",
    dt.date(2001, 9, 14): "September 11 attacks",
    dt.date(2004, 6, 11): "National day of mourning, President Reagan",
    dt.date(2007, 1, 2): "National day of mourning, President Ford",
    dt.date(2012, 10, 29): "Hurricane Sandy",
    dt.date(2012, 10, 30): "Hurricane Sandy",
    dt.date(2018, 12, 5): "National day of mourning, President G.H.W. Bush",
    dt.date(2025, 1, 9): "National day of mourning, President Carter",
}
ACTUAL = [d for d in SCHED if d not in KNOWN_CLOSURES]

# ---------------------------------------------------------------- ordinals
def ordinals(sessions):
    by_month = {}
    for d in sessions:
        by_month.setdefault((d.year, d.month), []).append(d)
    first, last, n = {}, {}, {}
    for key, ds in by_month.items():
        for i, d in enumerate(ds):
            first[d] = i + 1
            last[d] = i - len(ds)          # -1 is the last session of the month
            n[d] = len(ds)
    return first, last, n

s_first, s_last, s_n = ordinals(SCHED)
a_first, a_last, a_n = ordinals(ACTUAL)

# ---------------------------------------------------------------- opex
def third_friday(y, m):
    return barqc._nth_weekday(y, m, 4, 3)

opex = {}            # trading date -> (nominal third Friday, moved?)
for y in range(START.year, END.year + 1):
    for m in range(1, 13):
        f = third_friday(y, m)
        d = f
        moved = ""
        while d not in SCHED_SET or d in KNOWN_CLOSURES:
            d -= dt.timedelta(days=1)
            moved = f"third Friday {f.isoformat()} is {'holiday: ' + HOL[f] if f in HOL else 'a closure'}"
        opex[d] = (f, moved)

# ---------------------------------------------------------------- holiday adjacency (on ACTUAL sessions)
# adjacency needs sessions just outside 1999-2026 (e.g. the session before 1999-01-01)
act_set = set(d for d in barqc.sessions_between(dt.date(1998, 12, 1), dt.date(2027, 1, 31))
              if d not in KNOWN_CLOSURES)
def prev_session(d, cal):
    d -= dt.timedelta(days=1)
    while d not in cal:
        d -= dt.timedelta(days=1)
    return d

def next_session(d, cal):
    d += dt.timedelta(days=1)
    while d not in cal:
        d += dt.timedelta(days=1)
    return d

pre_holiday, post_holiday = {}, {}
hol_rows = []
for h in sorted(x for x in HOL if START <= x <= END):
    if h.weekday() >= 5:
        continue   # cannot happen with barqc rules; guard anyway
    pb = prev_session(h, act_set)
    na = next_session(h, act_set)
    pre_holiday.setdefault(pb, []).append(HOL[h])
    post_holiday.setdefault(na, []).append(HOL[h])
    hol_rows.append([h.isoformat(), h.strftime("%a"), HOL[h], pb.isoformat(), na.isoformat(),
                     (h - pb).days, (na - h).days])

# ---------------------------------------------------------------- early closes, RULE-DERIVED, UNVERIFIED
def early_close_rule(d):
    """
    NYSE's customary 13:00 closes, by rule. UNVERIFIED against exchange notices
    for every year; the data-observed column is the check where minute data exist.
      - the day after Thanksgiving
      - December 24 when it is a weekday session
      - July 3 when it is a weekday session and July 4 is a weekday holiday
    """
    th = barqc._nth_weekday(d.year, 11, 3, 4)
    if d == th + dt.timedelta(days=1):
        return "day after Thanksgiving"
    if d.month == 12 and d.day == 24 and d in SCHED_SET:
        return "Christmas Eve"
    if d.month == 7 and d.day == 3 and d in SCHED_SET and dt.date(d.year, 7, 4).weekday() < 5:
        return "July 3"
    return ""

# data-observed short sessions: in the minute-aggregated daily file but absent
# from the complete-sessions export (intraday.py skips sessions < 80% of 390 bars)
agg = set(files["bars/SPY-1d-agg.csv"])
sess = set(files["bars/SPY-sessions.csv (minute-derived complete sessions)"])
short_observed = sorted(agg - sess)

# ---------------------------------------------------------------- quarter ends (ACTUAL calendar)
quarter_end = {d for d in ACTUAL if d.month in (3, 6, 9, 12) and a_last[d] == -1}
year_end = {d for d in ACTUAL if d.month == 12 and a_last[d] == -1}

# ---------------------------------------------------------------- write the session table
os.makedirs(OUT, exist_ok=True)
cols = ["date", "weekday", "year", "month", "scheduled_session", "closed_unscheduled",
        "ord_from_start_sched", "ord_from_end_sched", "sessions_in_month_sched",
        "ord_from_start_actual", "ord_from_end_actual", "sessions_in_month_actual",
        "last_session_before_holiday", "first_session_after_holiday",
        "monthly_opex", "opex_note", "triple_witching", "quarter_end", "year_end",
        "early_close_rule_unverified", "short_session_observed_alpaca_1m"]
with open(os.path.join(OUT, "nyse-sessions-1999-2026.csv"), "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(cols)
    for d in SCHED:
        closed = d in KNOWN_CLOSURES
        ox = opex.get(d)
        w.writerow([
            d.isoformat(), d.strftime("%a"), d.year, d.month, 1,
            KNOWN_CLOSURES.get(d, ""),
            s_first[d], s_last[d], s_n[d],
            "" if closed else a_first[d], "" if closed else a_last[d], "" if closed else a_n[d],
            "; ".join(pre_holiday.get(d, [])), "; ".join(post_holiday.get(d, [])),
            1 if ox else 0, ox[1] if ox else "",
            1 if (ox and d.month in (3, 6, 9, 12)) else 0,
            1 if d in quarter_end else 0, 1 if d in year_end else 0,
            early_close_rule(d),
            ("" if not (dt.date(2020, 7, 27) <= d <= dt.date(2026, 9, 1)) else
             (1 if d in short_observed else 0)),
        ])

with open(os.path.join(OUT, "holidays-1999-2026.csv"), "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["holiday_date", "weekday", "holiday", "last_session_before", "first_session_after",
                "calendar_days_since_prev_session", "calendar_days_to_next_session"])
    w.writerows(hol_rows)

with open(os.path.join(OUT, "opex-1999-2026.csv"), "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["expiration_trading_date", "weekday", "nominal_third_friday", "moved_reason", "quarterly"])
    for d in sorted(opex):
        f3, why = opex[d]
        w.writerow([d.isoformat(), d.strftime("%a"), f3.isoformat(), why, 1 if d.month in (3, 6, 9, 12) else 0])

# ---------------------------------------------------------------- the cross-check report
L = []
L.append("calendar-vs-files — barqc rule calendar against every bar file's own dates")
L.append(f"generated {dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')} by calendar_build.py")
L.append(f"rule calendar 1999-01-01..2026-12-31: {len(SCHED)} scheduled sessions; "
         f"{len(KNOWN_CLOSURES)} known unscheduled closures; {len(ACTUAL)} actual sessions")
L.append("")
L.append("A. Scheduled sessions absent from EVERY file that spans them (closure candidates):")
for d, nspan, vendors in closure_candidates:
    tag = KNOWN_CLOSURES.get(d, "NOT in the known-closure list")
    L.append(f"   {d} {d:%a}  absent from all {nspan} spanning file(s); vendors {','.join(vendors)}  -> {tag}")
L.append("")
L.append("B. Known closures and how many vendors witness each:")
for d, why in sorted(KNOWN_CLOSURES.items()):
    span = spanning.get(d, [])
    ab = absent_by_date.get(d, [])
    vendors = sorted({vendor_of(k) for k in span})
    L.append(f"   {d}  {why}: spanned by {len(span)} file(s) [{','.join(vendors) or 'none'}], absent from {len(ab)}")
L.append("")
L.append("C. Per file: scheduled sessions inside the file's span that it lacks, and bars on non-sessions:")
for k, ds in files.items():
    s = set(ds)
    lo, hi = min(ds), max(ds)
    exp = [d for d in barqc.sessions_between(lo, hi)]
    miss = [d for d in exp if d not in s]
    off = [d for d in ds if not barqc.is_session_day(d)]
    dup = len(ds) - len(s)
    miss_known = [d for d in miss if d in KNOWN_CLOSURES]
    miss_other = [d for d in miss if d not in KNOWN_CLOSURES]
    L.append(f"   {k}: {len(ds)} rows {lo}..{hi}; scheduled {len(exp)}; missing {len(miss)} "
             f"(known closures {len(miss_known)}; OTHER {len(miss_other)}: "
             f"{', '.join(x.isoformat() for x in miss_other[:40])}{' ...' if len(miss_other) > 40 else ''}); "
             f"off-calendar {len(off)}{(': ' + ', '.join(x.isoformat() for x in off[:10])) if off else ''}; dup {dup}")
L.append("")
L.append("D. Short sessions observed in the Alpaca minute feed (dates in SPY-1d-agg.csv absent from")
L.append("   SPY-sessions.csv, i.e. sessions under 80% of 390 minute bars), against the early-close rule:")
for d in short_observed:
    L.append(f"   {d} {d:%a}  rule says: {early_close_rule(d) or '(no early close by rule -> a feed hole?)'}")
rule_days = [d for d in ACTUAL if dt.date(2020, 7, 27) <= d <= dt.date(2026, 9, 1) and early_close_rule(d)]
L.append("   rule-derived early closes in the same window that the feed did NOT mark short: "
         + (", ".join(d.isoformat() for d in rule_days if d not in short_observed) or "none"))
L.append("")
L.append("E. Monthly expirations moved off the third Friday (holiday on the Friday):")
for d in sorted(opex):
    if opex[d][1]:
        L.append(f"   {d} {d:%a}  ({opex[d][1]})")
L.append("")
n_q = len(quarter_end)
L.append(f"F. Counts: monthly expirations {len(opex)}; quarter ends {n_q}; year ends {len(year_end)}; "
         f"holidays {len(hol_rows)}; sessions before a holiday {len(pre_holiday)}")
with open(os.path.join(OUT, "calendar-vs-files.txt"), "w") as f:
    f.write("\n".join(L) + "\n")
print("\n".join(L))
