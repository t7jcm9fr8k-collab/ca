#!/usr/bin/env python3
"""
disagreements.py — Quartermaster, round 1. Single-day price disagreements
between two vendors, and suspicious rows inside one vendor. Data quality only.

For each symbol with both a stooq file and a nasdaq.com file, on common dates:
  open outlier   |(so/no) / (sc/nc) - 1| > 10 bp   (open off the day's own basis)
  close outlier  close ratio jumps >10 bp on t and jumps back >10 bp on t+1 (isolated spike)
For each outlier both rows are printed, plus whether each vendor's open lies
inside the OTHER vendor's [low, high] (after removing the close-ratio factor).

Inside every nasdaq.com file: flat bars (O=H=L=C), zero volume, placeholder
volume 9999999, OHLC-inconsistent rows, and a close equal to the previous close
with zero volume (a stale carry-forward).

Run: python3 -I -B disagreements.py <bars dir> <nasdaq dir> <out file>
"""
import csv
import os
import statistics as st
import sys

BARS, NASDAQ, OUT = sys.argv[1:4]


def load(p):
    rows = [r for r in csv.reader(open(p, newline="")) if r and not r[0].startswith("#")][1:]
    return {r[0][:10]: tuple(float(x) for x in r[1:6]) for r in rows}


L = []
NINE = ["DIA", "EEM", "EFA", "GLD", "IWM", "QQQ", "TLT", "XLE", "XLF"]
for s in ["SPY"] + NINE:
    f = "SPY-1d.csv" if s == "SPY" else f"{s}-1d-long.csv"
    A = load(os.path.join(BARS, f))
    N = load(os.path.join(NASDAQ, f"{s}-1d-nasdaq.csv"))
    common = sorted(set(A) & set(N))
    rc = [A[d][3] / N[d][3] for d in common]
    out = []
    for i, d in enumerate(common):
        a, n = A[d], N[d]
        ob = (a[0] / n[0]) / rc[i] - 1
        # an isolated one-day close spike: away from the previous day AND back the next day
        # (a dividend step moves once and stays, so it is not counted here)
        if 0 < i < len(common) - 1:
            up = rc[i] / rc[i - 1] - 1
            down = rc[i + 1] / rc[i] - 1
            cb = up if (abs(up) > 1e-3 and abs(down) > 1e-3 and up * down < 0) else 0.0
        else:
            cb = 0.0
        if abs(ob) > 1e-3 or abs(cb) > 1e-3:
            k = rc[i]
            s_open_in_n = n[2] <= a[0] / k <= n[1]
            n_open_in_s = a[2] / k <= n[0] <= a[1] / k
            out.append(f"   {d}  open-basis {ob*1e4:+8.2f} bp  close-spike {cb*1e4:+8.2f} bp | "
                       f"stooq O {a[0]:g} H {a[1]:g} L {a[2]:g} C {a[3]:g} V {a[4]:g} | "
                       f"nasdaq O {n[0]:g} H {n[1]:g} L {n[2]:g} C {n[3]:g} V {n[4]:g} | "
                       f"stooq-open in nasdaq range: {s_open_in_n}; nasdaq-open in stooq range: {n_open_in_s}")
    L.append(f"\n## {s}: stooq {f} vs nasdaq, {len(common)} common dates, {len(out)} date(s) with a >10 bp single-day disagreement")
    L.extend(out)

L.append("\n# Suspicious rows inside each nasdaq.com file")
for name in sorted(os.listdir(NASDAQ)):
    if not name.endswith("-1d-nasdaq.csv"):
        continue
    N = load(os.path.join(NASDAQ, name))
    ds = sorted(N)
    bad = []
    for i, d in enumerate(ds):
        o, h, l, c, v = N[d]
        tags = []
        if o == h == l == c:
            tags.append("flat O=H=L=C")
        if v <= 0:
            tags.append("zero volume")
        if v == 9999999:
            tags.append("volume 9999999 placeholder")
        if h < max(o, c) or l > min(o, c) or h < l:
            tags.append("OHLC inconsistent")
        if i and c == N[ds[i - 1]][3] and v <= 0:
            tags.append("close = previous close with zero volume (carry-forward)")
        if tags:
            bad.append(f"   {d}: O {o:g} H {h:g} L {l:g} C {c:g} V {v:g}  <- {'; '.join(tags)}")
    L.append(f"\n## {name}: {len(bad)} suspicious row(s)")
    L.extend(bad)

open(OUT, "w").write("\n".join(L) + "\n")
print("\n".join(L))
