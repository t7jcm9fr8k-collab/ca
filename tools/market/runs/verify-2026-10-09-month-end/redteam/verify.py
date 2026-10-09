#!/usr/bin/env python3
"""Red Team r4: an independent re-implementation of S1 and bar (A) at the primary cell, written
without edgelab, to check the run's printed numbers (verification only; the trial is spent).
Closes only; shares held between changes; borrowed money accrues (1+c+s)^(D/365)-1 per leg;
2 bp per side on traded notional; the five frozen add-backs; window list as frozen."""
import csv, math, datetime as dt, sys
M = "/home/user/ca/tools/market/"
C, S, BP = 0.015, 0.015, 2e-4
L_A = 1.333395
START, END = dt.date(2005, 3, 24), dt.date(2026, 8, 25)
ADD = {dt.date(2025,6,20):1.7611, dt.date(2025,9,19):1.8311, dt.date(2025,12,19):1.9934,
       dt.date(2026,3,20):1.797, dt.date(2026,6,18):1.90352}
bars = []
with open(M + "bars/SPY-1d.csv") as fh:
    for row in csv.DictReader(fh):
        d = dt.date.fromisoformat(row["Date"])
        if START <= d <= END:
            bars.append((d, float(row["Close"])))
entries, exits = set(), set()
wins = []
with open(M + "prereg-2026-10-09/windows-S1-SPY.csv") as fh:
    for row in csv.DictReader(fh):
        if row["complete"] == "True":
            e, x = dt.date.fromisoformat(row["entry_exec"]), dt.date.fromisoformat(row["exit_exec"])
            if START <= e and x <= END:
                entries.add(e); exits.add(x); wins.append((row["month"], e, x))
# returns per leg (close-to-close), with add-backs
dates = [b[0] for b in bars]
ret = [None] + [((bars[i][1] + ADD.get(bars[i][0], 0.0)) / bars[i-1][1] - 1.0) for i in range(1, len(bars))]
days = [None] + [(bars[i][0] - bars[i-1][0]).days for i in range(1, len(bars))]
def run(target_fn, resets):
    """Generic shares-held margin book. target_fn(date) -> exposure decided at that close.
    resets: set of dates at whose close the book trades to its target."""
    E = 1.0
    pos = target_fn(dates[0]) * E           # notional in SPY
    loan = pos - E
    cost = BP * pos
    E -= cost; loan += cost                 # pay the entry cost from borrowing (tiny)
    eq = [E]
    for i in range(1, len(bars)):
        f = (1 + C + S) ** (days[i] / 365.0) - 1.0
        pos *= (1 + ret[i])
        loan *= (1 + f) if loan > 0 else (1 + ((1 + C) ** (days[i] / 365.0) - 1.0))
        E = pos - loan
        if dates[i] in resets:
            tgt = target_fn(dates[i]) * E
            tc = BP * abs(tgt - pos)
            loan += (tgt - pos) + tc
            pos = tgt
            E = pos - loan
        eq.append(E)
    return eq
inwin = set()
for _, e, x in wins:
    for d in dates:
        if e < d <= x:
            inwin.add(d)
def s1_target(d):
    # exposure decided at the close of d for the next leg: 2 from an entry close up to the exit close
    if d in entries: return 2.0
    if d in exits: return 1.0
    return None
# S1: track state explicitly
state = {"x": 2.0}
def s1_fn(d):
    t = s1_target(d)
    if t is not None: state["x"] = t
    return state["x"]
eq1 = run(s1_fn, entries | exits)
eqA = run(lambda d: L_A, entries | exits)
eqB = run(lambda d: 1.0, set())
years = (END - START).days / 365.25
def cagr(eq): return eq[-1] ** (1 / years) - 1
def mdd(eq):
    pk, pkd, worst, w = -1, None, 0.0, None
    for d, e in zip(dates, eq):
        if e > pk: pk, pkd = e, d
        dd = e / pk - 1
        if dd < worst: worst, w = dd, (pkd, d)
    return worst, w
dser = [math.log(eq1[i] / eq1[i-1]) - math.log(eqA[i] / eqA[i-1]) for i in range(1, len(bars))]
n = len(dser); m = sum(dser) / n; sd = math.sqrt(sum((x - m) ** 2 for x in dser) / (n - 1))
print(f"sessions {n}; years {years:.3f}; window sessions {len(inwin)}")
print(f"CAGR S1 {cagr(eq1):+.2%}  A {cagr(eqA):+.2%}  B&H {cagr(eqB):+.2%}")
for nm, eq in (("S1", eq1), ("A", eqA), ("B&H", eqB)):
    w, (p, t) = mdd(eq)
    print(f"maxDD {nm} {w:+.1%} peak {p} trough {t}")
print(f"d: mean {m*252:+.3%}/yr  TE {sd*math.sqrt(252):.2%}  z_iid {m/sd*math.sqrt(n):+.3f}  sum {sum(dser):+.4f}")
# per-cycle sums of d: cycle = sessions after an entry close up to and including the next entry close
ent = sorted(entries)
cyc = []
for k, e in enumerate(ent):
    nxt = ent[k+1] if k + 1 < len(ent) else END
    s = sum(dser[i-1] for i in range(1, len(bars)) if e < dates[i] <= nxt)
    cyc.append((s, e))
cyc.sort(reverse=True)
tot = sum(c[0] for c in cyc)
top5 = sum(c[0] for c in cyc[:5])
print(f"cycles {len(cyc)}; sum {tot:+.4f}; top-5 {top5:+.4f} ({top5/tot:.0%} of the sum); without them {tot-top5:+.4f}")
print("top-5 cycles (entry close, sum d):", ", ".join(f"{e} {s:+.4f}" for s, e in cyc[:5]))
print("bottom-5 cycles:", ", ".join(f"{e} {s:+.4f}" for s, e in cyc[-5:]))
def span_sum(a, b):
    return sum(dser[i-1] for i in range(1, len(bars)) if a <= dates[i] <= b)
for a, b in ((dt.date(2008,9,1), dt.date(2009,6,30)), (dt.date(2020,2,15), dt.date(2020,4,30))):
    print(f"sum d {a}..{b}: {span_sum(a, b):+.4f}")
crisis = span_sum(dt.date(2008,9,1), dt.date(2009,6,30)) + span_sum(dt.date(2020,2,15), dt.date(2020,4,30))
kept_n = sum(1 for i in range(1, len(bars)) if not (dt.date(2008,9,1) <= dates[i] <= dt.date(2009,6,30) or dt.date(2020,2,15) <= dates[i] <= dt.date(2020,4,30)))
print(f"without the two crisis spans: sum d {tot - crisis:+.4f} over {kept_n} sessions -> {(tot-crisis)/kept_n*252:+.2%}/yr")
# inside vs outside the window: d contribution
din = sum(dser[i-1] for i in range(1, len(bars)) if dates[i] in inwin)
print(f"d summed over window sessions {din:+.4f}; over other sessions {tot - din:+.4f}")
# largest single-session d
big = sorted(((dser[i-1], dates[i], ret[i]) for i in range(1, len(bars))), reverse=True)
print("largest d sessions:", ", ".join(f"{d} d {x:+.4f} (r {r:+.2%})" for x, d, r in big[:6]))
print("smallest d sessions:", ", ".join(f"{d} d {x:+.4f} (r {r:+.2%})" for x, d, r in big[-6:]))
# --- robustness of the fail (verification only, never a gate) ---
from statistics import NormalDist
N01 = NormalDist(); G = 0.5772156649015329
def emax(k): return (1-G)*N01.inv_cdf(1-1/k) + G*N01.inv_cdf(1-1/(k*math.e)) if k > 1 else 0.0
cs = [c[0] for c in cyc]; mc = sum(cs)/len(cs); sc = math.sqrt(sum((x-mc)**2 for x in cs)/(len(cs)-1))
print(f"per-cycle z (257 cycle sums of d): {mc/sc*math.sqrt(len(cs)):+.3f}")
keep = [dser[i-1] for i in range(1, len(bars)) if not (dt.date(2008,9,1) <= dates[i] <= dt.date(2009,6,30) or dt.date(2020,2,15) <= dates[i] <= dt.date(2020,4,30))]
mk = sum(keep)/len(keep); sk = math.sqrt(sum((x-mk)**2 for x in keep)/(len(keep)-1))
print(f"outside the two crisis spans: {len(keep)} sessions, mean {mk*252:+.2%}/yr, TE {sk*math.sqrt(252):.2%}, z_iid {mk/sk*math.sqrt(len(keep)):+.2f}")
crisis_n = len(bars) - 1 - len(keep)
print(f"crisis spans: {crisis_n} sessions ({crisis_n/(len(bars)-1):.1%}) carry {crisis/tot:.0%} of sum d")
for k in (1, 2, 3, 5, 10, 40, 100):
    print(f"N={k:3d}: z needed {emax(k)+N01.inv_cdf(0.8):.3f}; DSR at z 1.688 = {N01.cdf(1.688-emax(k)):.3f}")
# the scale needed: SE shrink or mean growth to reach 3.0311 from z_boot 1.812 / z_used 1.688
for z in (1.688, 1.812, 1.930):
    print(f"from z {z}: mean x{3.0311/z:.2f} or SE x{z/3.0311:.2f}")
# where does G3's 14-point margin come from: each book's drawdown at the other's trough
def dd_at(eq, d):
    i = dates.index(d); pk = max(eq[:i+1]); return eq[i]/pk - 1
for d in (dt.date(2008,10,27), dt.date(2008,11,20), dt.date(2009,3,9)):
    print(f"{d}: drawdown S1 {dd_at(eq1, d):+.1%}, A {dd_at(eqA, d):+.1%}, B&H {dd_at(eqB, d):+.1%}")
# S1 with the 2008-10-27 entry close 0.8% higher (index-consistent move; unverified), G3 sensitivity
print(f"per-cycle sum of d: mean {mc*1e4:+.1f} bp, SD {sc*1e4:.1f} bp; FOMC split (printed +68.8 vs +20.2 bp, 46 vs 114 cycles): "
      f"difference {(68.8-20.2):.1f} bp, SE ~{math.sqrt((sc*1e4)**2/46 + (sc*1e4)**2/114):.1f} bp")
yr = {}
for i in range(1, len(bars)):
    yr.setdefault(dates[i].year, 0.0); yr[dates[i].year] += dser[i-1]
print("sum d by calendar year:", ", ".join(f"{y} {v:+.3f}" for y, v in sorted(yr.items())))
