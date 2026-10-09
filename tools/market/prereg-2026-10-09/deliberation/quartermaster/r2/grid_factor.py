#!/usr/bin/env python3
"""
grid_factor.py — Quartermaster round 2. Locate a back-adjusted file's
adjustment events WITHOUT an unadjusted reference.

Idea. After US decimalization, official prices are whole cents. A back-adjusted
price is p = raw x F, where F (the cumulative adjustment factor) is constant
between adjustment events and stooq rounds p to 4 decimals. So within a span
of constant F, every p/F lies on the 0.01 grid (within rounding). For each
block of B sessions we search the F that puts the most O/H/L/C values on the
grid; where the best F changes from one block to the next, an adjustment event
lies between them, and the event day is the first session whose CLOSE fits the
new F. On that day we also check which grid the OPEN fits: the new one means
the adjustment sits on the ex-date open (as measured in round 1 for 2016+).

This reads prices only to recover the file's own adjustment factor. It computes
no return and conditions on no rule, window or event.

Run: python3 -I -B grid_factor.py <csv> <start YYYY-MM-DD> <end> <grid> <out>
     grid = 0.01 (decimal era) or a fraction like 0.015625 (1/64)
"""
import csv, sys

PATH, START, END, GRID, OUT = sys.argv[1], sys.argv[2], sys.argv[3], float(sys.argv[4]), sys.argv[5]
B = 15                 # sessions per block
TOL = None             # per-value: half a unit in the 6th significant digit, over F
FMIN, FMAX = 0.30, 1.05

rows = [r for r in csv.reader(open(PATH, newline=""))][1:]
rows = [(r[0][:10], [float(x) for x in r[1:5]]) for r in rows if START <= r[0][:10] <= END]


import math


def on_grid(v, F):
    """stooq stores 6 significant figures, so a value's own rounding is half a
    unit in its 6th digit; divided by F that is the tolerance on the raw grid."""
    x = v / F / GRID
    tol = 0.5 * 10 ** (math.floor(math.log10(abs(v))) - 5) / F * 1.05 + 1e-9
    return abs(x - round(x)) * GRID <= tol


def hits(vals, F):
    return sum(1 for v in vals if on_grid(v, F))


def best_factor(block, near=None, width=0.015):
    """Search F so that the most O/H/L/C values sit on the grid. With `near`,
    only factors within +/-width of it are tried (factors move slowly: a
    distribution is well under 1.5% per event); without it, the full range,
    using the first 5 sessions only to keep the search cheap."""
    vals = [v for _, ohlc in block for v in ohlc]
    probe = vals if near else [v for _, ohlc in block[:5] for v in ohlc]
    c0 = block[0][1][3]
    fmin, fmax = (near * (1 - width), near * (1 + width)) if near else (FMIN, FMAX)
    lo, hi = int(c0 / (GRID * fmax)), int(c0 / (GRID * fmin)) + 1
    best = (-1, None)
    for n in range(max(lo, 1), hi + 1):
        F = c0 / (n * GRID)
        h = hits(probe, F)
        if h > best[0]:
            best = (h, F)
    F = best[1]
    return F, hits(vals, F), len(vals)


blocks = [rows[i:i + B] for i in range(0, len(rows), B)]
res = []
near = None
for b in blocks:
    F, h, n = best_factor(b, near)
    if h < 0.9 * n and near is not None:          # lost the grid: widen once
        F, h, n = best_factor(b, None)
    res.append((b[0][0], b[-1][0], F, h, n))
    if h >= 0.9 * n:
        near = F

L = [f"grid_factor {PATH} {START}..{END} grid {GRID} block {B} tol 6-sig-fig rounding/F",
     "block first..last  best F  hits/values"]
for a, z, F, h, n in res:
    L.append(f"  {a}..{z}  F={F:.6f}  {h}/{n}")

# events: consecutive blocks whose best F differs by more than 2e-4 relative
L.append("\nEvents (factor steps between blocks), located to the day:")
events = []
for (a1, z1, F1, h1, n1), (a2, z2, F2, h2, n2), b1, b2 in zip(res, res[1:], blocks, blocks[1:]):
    if h1 < 0.9 * n1 or h2 < 0.9 * n2:
        continue
    if abs(F2 / F1 - 1) > 2e-4:
        span = b1 + b2
        day = None
        for i, (d, ohlc) in enumerate(span):
            if on_grid(ohlc[3], F2) and not on_grid(ohlc[3], F1):
                # first close on the new grid that stays there
                if all(on_grid(o[3], F2) for _, o in span[i:i + 3]):
                    day = (d, ohlc, span[i - 1][0] if i else None)
                    break
        if day:
            d, ohlc, prev = day
            o_new, o_old = on_grid(ohlc[0], F2), on_grid(ohlc[0], F1)
            where = "open on NEW grid (adjustment on ex-date open)" if o_new and not o_old else \
                    "open on OLD grid (adjustment after the open)" if o_old and not o_new else \
                    "open fits both/neither (undetermined)"
            step_bp = (F2 / F1 - 1) * 1e4
            events.append((d, step_bp, where))
            L.append(f"  {d}  step {step_bp:+8.2f} bp (F {F1:.6f} -> {F2:.6f})  {where}")
        else:
            L.append(f"  between {z1} and {a2}: step {(F2 / F1 - 1) * 1e4:+.2f} bp, day not located")
open(OUT, "w").write("\n".join(L) + "\n")
print("\n".join(L[-(len(events) + 3):]))
print(f"blocks: {len(res)}; blocks with >=90% grid hits: {sum(1 for r in res if r[3] >= 0.9 * r[4])}; events located: {len(events)}")
