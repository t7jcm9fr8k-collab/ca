#!/usr/bin/env python3
"""
window_spec.py — Quartermaster round 2. The frozen window calendar for the
pre-registration, from the SCHEDULED NYSE calendar (barqc) plus each file's
own dates. Dates only: no price is read.

For every month m:
  S1 / G7 (Etula [T-3, T+3], MOC->MOC): entry = close of scheduled T-4,
          exit = close of scheduled T+3; if that session is an unscheduled
          closure, the order executes at the close of the next session with a
          bar (what edgelab does: no bar, no auction).
  S2 (TLT last three sessions): entry = close of scheduled T-3, exit = close of T.
Flags: a boundary on an unscheduled closure, on a rule-derived half-day (13:00
close; verified only 2020-07-27..2026-09-01 by the minute feed), windows that
contain a closure or a data hole, and windows the file cannot complete.

Run: python3 -I -B window_spec.py <tools/market> <sessions csv> <out dir>
"""
import csv, datetime as dt, hashlib, os, sys
TOOLS, SESS, OUT = sys.argv[1:4]
sys.path.insert(0, TOOLS)
import barqc
BARS = os.path.join(TOOLS, "bars")

cal = {r["date"]: r for r in csv.DictReader(open(SESS))}
SCHED = sorted(dt.date.fromisoformat(d) for d in cal)
pos = {d: i for i, d in enumerate(SCHED)}
CLOSED = {dt.date.fromisoformat(d) for d, r in cal.items() if r["closed_unscheduled"]}
months = {}
for d in SCHED:
    months.setdefault((d.year, d.month), []).append(d)


def T(y, m):
    return months[(y, m)][-1]


def off(d, k):
    return SCHED[pos[d] + k]


def file_dates(name):
    rows = list(csv.reader(open(os.path.join(BARS, name))))[1:]
    return sorted(dt.date.fromisoformat(r[0][:10]) for r in rows)


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        h.update(f.read())
    return h.hexdigest()


def roll(d, have):
    """The session the order executes at: d itself if the file has a bar, else
    the next date with a bar (an unscheduled closure or a data hole)."""
    while d not in have and d <= have[-1]:
        d = SCHED[pos[d] + 1]
    return d


def halfday(d):
    r = cal[d.isoformat()]
    tag = r["early_close_rule_unverified"]
    if not tag:
        return ""
    obs = r["short_session_observed_alpaca_1m"]
    return f"{tag} ({'observed short in minute feed' if obs == '1' else 'rule only, unverified' if obs == '' else 'NOT short in feed'})"


def build(name, label, entry_k, exit_k, first_month, last_month, have):
    rows, notes = [], []
    y, m = first_month
    while (y, m) <= last_month:
        Tm = T(y, m)
        e_s, x_s = off(Tm, entry_k), off(Tm, exit_k)
        e, x = roll(e_s, have), roll(x_s, have)
        inside = [d for d in SCHED[pos[e_s] + 1: pos[x_s] + 1]]
        clos = [d for d in inside if d in CLOSED]
        holes = [d for d in inside if d not in have and d not in CLOSED]
        complete = e_s >= have[0] and x <= have[-1]
        rows.append({"month": f"{y}-{m:02d}", "T": Tm, "entry_sched": e_s, "entry_exec": e,
                     "exit_sched": x_s, "exit_exec": x, "sessions_held_with_bars": sum(1 for d in inside if d in have) + (0 if x == x_s else sum(1 for d in SCHED[pos[x_s] + 1: pos[x] + 1] if d in have)),
                     "closures_inside": ";".join(map(str, clos)), "holes_inside": ";".join(map(str, holes)),
                     "entry_halfday": halfday(e), "exit_halfday": halfday(x), "complete": complete})
        m += 1
        if m == 13:
            y, m = y + 1, 1
    with open(os.path.join(OUT, f"windows-{label}.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        for r in rows:
            w.writerow({k: (v.isoformat() if isinstance(v, dt.date) else v) for k, v in r.items()})
    return rows


L = []
spy = file_dates("SPY-1d.csv"); spy_set = set(spy)
qqq = file_dates("QQQ-1d-long.csv"); qqq_set = set(qqq)
tlt = file_dates("TLT-1d-long.csv"); tlt_set = set(tlt)
for nm in ["SPY-1d.csv", "QQQ-1d-long.csv", "TLT-1d-long.csv"]:
    L.append(f"sha256 bars/{nm} = {sha(os.path.join(BARS, nm))}")


class Have(list):
    def __contains__(self, d):
        return d in self._s


def have_of(dates, last=None):
    h = Have(d for d in dates if last is None or d <= last)
    h._s = set(h)
    return h


specs = [
    ("SPY-1d.csv", "S1-SPY", -4, 3, (2005, 2), (2026, 8), have_of(spy, dt.date(2026, 9, 1))),
    ("QQQ-1d-long.csv", "G7-QQQ", -4, 3, (1999, 2), (2005, 2), have_of(qqq, dt.date(2005, 2, 24))),
    ("TLT-1d-long.csv", "S2-TLT", -3, 0, (2005, 2), (2026, 9), have_of(tlt)),
]
for name, label, ek, xk, fm, lm, have in specs:
    rows = build(name, label, ek, xk, fm, lm, have)
    comp = [r for r in rows if r["complete"]]
    L.append(f"\n## {label} ({name}, bars used {have[0]}..{have[-1]}): entry = close of T{ek:+d}, exit = close of T{xk:+d}")
    L.append(f"   complete windows: {len(comp)}, first {comp[0]['month']} (entry {comp[0]['entry_exec']}, exit {comp[0]['exit_exec']}), "
             f"last {comp[-1]['month']} (entry {comp[-1]['entry_exec']}, exit {comp[-1]['exit_exec']})")
    inc = [r["month"] for r in rows if not r["complete"]]
    L.append(f"   incomplete windows (excluded): {inc}")
    for r in comp:
        flags = []
        if r["entry_exec"] != r["entry_sched"]:
            flags.append(f"entry rolled {r['entry_sched']} -> {r['entry_exec']}")
        if r["exit_exec"] != r["exit_sched"]:
            flags.append(f"exit rolled {r['exit_sched']} -> {r['exit_exec']} (closure)")
        if r["closures_inside"]:
            flags.append(f"closure(s) inside: {r['closures_inside']}")
        if r["holes_inside"]:
            flags.append(f"DATA HOLE inside: {r['holes_inside']}")
        if flags:
            L.append(f"   {r['month']}: " + "; ".join(flags) + f"; sessions held with bars {r['sessions_held_with_bars']}")
    hd = [(r["month"], "entry", r["entry_exec"], r["entry_halfday"]) for r in comp if r["entry_halfday"]] + \
         [(r["month"], "exit", r["exit_exec"], r["exit_halfday"]) for r in comp if r["exit_halfday"]]
    hd.sort(key=lambda x: str(x[2]))
    L.append(f"   boundary sessions that are rule-derived half-days: {len(hd)}")
    for mth, which, d, tag in hd:
        L.append(f"      {d} {d:%a}  {which} of {mth} window  {tag}")
open(os.path.join(OUT, "window-spec.txt"), "w").write("\n".join(L) + "\n")
print("\n".join(L))
