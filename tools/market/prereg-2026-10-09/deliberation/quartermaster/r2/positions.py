#!/usr/bin/env python3
"""
positions.py — Quartermaster round 2. Calendar-only placement of dates relative
to month-end T (T = last SCHEDULED session of the month, barqc rules).
Writes T-k / T+k for: the lead's six assumed SPY ex-dates, every ex-date
located in round 1 (basis-events.csv, stooq pairs), and all 336 monthly
expirations. No prices are read.
Run: python3 -I -B positions.py <tools/market> <basis-events.csv> <opex csv> <out>
"""
import csv, datetime as dt, sys
TOOLS, EV, OPEX, OUT = sys.argv[1:5]
sys.path.insert(0, TOOLS)
import barqc
SCHED = barqc.sessions_between(dt.date(1998, 12, 1), dt.date(2027, 1, 31))
idx = {d: i for i, d in enumerate(SCHED)}
month_last = {}
for d in SCHED:
    month_last[(d.year, d.month)] = d          # last scheduled session of each month
Ts = sorted(month_last.values())

def pos(d):
    """Position of date d relative to the nearest month-end T on the scheduled
    calendar: returns (label, k) with T-k for the month that ends at or after d
    (k = sessions before T) and T+k for k sessions after the previous T."""
    if d not in idx:
        return ("not a scheduled session", None)
    i = idx[d]
    T_next = month_last[(d.year, d.month)]
    k_before = idx[T_next] - i                   # 0 means d == T
    prevs = [t for t in Ts if t < d]
    k_after = i - idx[prevs[-1]] if prevs else None
    return (f"T-{k_before}" if k_before > 0 else "T", k_before, f"T+{k_after}", k_after)

L = []
L.append("A. Lead's six assumed SPY ex-dates after the stooq cutoff (brief §2)")
for s in ["2025-06-20", "2025-09-19", "2025-12-19", "2026-03-20", "2026-06-18", "2026-09-18"]:
    p = pos(dt.date.fromisoformat(s))
    L.append(f"   {s} {dt.date.fromisoformat(s):%a}: {p[0]} (also {p[2]} of the previous month-end)")

L.append("\nB. Every ex-date located in round 1 (stooq vs nasdaq, 2016-10..cutover): position vs [T-3, T+3]")
L.append("   in-window means T-3..T (k_before <= 3) or T+1..T+3 (k_after <= 3)")
rows = [r for r in csv.DictReader(open(EV)) if r["pair"].startswith("stooq ")]
by = {}
for r in rows:
    sym = r["pair"].split()[1].replace("-1d-long.csv", "").replace("-1d.csv", "")
    by.setdefault(sym, []).append(r["event_date"])
for sym in sorted(by):
    ins, mins, maxs = [], None, None
    kb = []
    for s in by[sym]:
        p = pos(dt.date.fromisoformat(s))
        kb.append(p[1])
        if p[1] <= 3 or p[3] <= 3:
            ins.append(f"{s}({p[0] if p[1] <= 3 else p[2]})")
    L.append(f"   {sym:<4} n={len(by[sym]):>3}  T-k range for k: min {min(kb)} max {max(kb)};  in [T-3,T+3]: {len(ins)}  {' '.join(ins[:8])}{' ...' if len(ins) > 8 else ''}")
spy = [pos(dt.date.fromisoformat(s)) for s in by["SPY"]]
from collections import Counter
L.append(f"   SPY positions (T-k) histogram: {dict(sorted(Counter(p[0] for p in spy).items()))}")
qqq = [pos(dt.date.fromisoformat(s)) for s in by["QQQ"]]
L.append(f"   QQQ positions (T-k) histogram: {dict(sorted(Counter(p[0] for p in qqq).items()))}")

L.append("\nC. All monthly expirations 1999-2026 (opex-1999-2026.csv): position vs month-end T")
ks = []
for r in csv.DictReader(open(OPEX)):
    p = pos(dt.date.fromisoformat(r["expiration_trading_date"]))
    ks.append((p[1], r["expiration_trading_date"]))
ks.sort()
L.append(f"   n = {len(ks)}; smallest k (latest in month) = T-{ks[0][0]} at {', '.join(d for k, d in ks if k == ks[0][0])}")
L.append(f"   largest k (earliest) = T-{ks[-1][0]};  any in T-3..T: {sum(1 for k, d in ks if k <= 3)}")
L.append(f"   k histogram: {dict(sorted(Counter(k for k, d in ks).items()))}")
open(OUT, "w").write("\n".join(L) + "\n")
print("\n".join(L))
