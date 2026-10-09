#!/usr/bin/env python3
"""
close_grid.py — Quartermaster round 2. Recover a back-adjusted file's
adjustment events from its CLOSES alone, without an unadjusted reference.

Official closes after decimalization are whole cents. A back-adjusted close is
c = raw x F, rounded by stooq to 6 significant figures, with F constant
between adjustment events. Walk the closes day by day: while c/F stays on the
0.01 grid (within the 6-significant-figure rounding, divided by F) nothing
happened; at the first close that leaves the grid, search a new F' within
+/-2% that puts that close and the next four on the grid, and record an event
(date, step F'/F). Ambiguity is flagged when the previous close also fits F'.

Basis data only: recovers the file's own factor path; no return, no rule.
Run: python3 -I -B close_grid.py <csv> <start> <end> <out> [first-F-hint]
"""
import csv, math, sys
PATH, START, END, OUT = sys.argv[1:5]
HINT = float(sys.argv[5]) if len(sys.argv) > 5 else None
G = 0.01
rows = [r for r in csv.reader(open(PATH, newline=""))][1:]
cl = [(r[0][:10], float(r[4])) for r in rows if START <= r[0][:10] <= END]


def fits(c, F):
    x = c / F / G
    tol = 0.5 * 10 ** (math.floor(math.log10(abs(c))) - 5) / F * 1.05 + 1e-9
    return abs(x - round(x)) * G <= tol


def search(vals, lo_f, hi_f):
    """Largest F in [lo_f, hi_f] with every value on the grid, else None."""
    c0 = vals[0]
    for n in range(max(1, int(c0 / (G * hi_f))), int(c0 / (G * lo_f)) + 2):
        F = c0 / (n * G)            # n ascending -> F descending: the largest F wins
        if lo_f <= F <= hi_f and all(fits(v, F) for v in vals):
            return F
    return None


L = [f"close_grid {PATH} {START}..{END}"]
if HINT:
    F = search([c for _, c in cl[:10]], HINT * 0.98, HINT * 1.02)
else:
    F = search([c for _, c in cl[:10]], 0.30, 1.05)
L.append(f"initial F = {F}")
events, unexplained = [], []
i = 1
while F and i < len(cl):
    d, c = cl[i]
    if fits(c, F):
        i += 1
        continue
    window = [v for _, v in cl[i:i + 5]]
    F2 = search(window, F * 0.98, F * 1.02)
    if F2 is None:
        unexplained.append(d)
        i += 1
        continue
    amb = fits(cl[i - 1][1], F2)
    events.append((d, (F2 / F - 1) * 1e4, amb))
    F = F2
    i += 1
L.append(f"events found: {len(events)}; closes on no nearby grid (data errors or sub-cent prints): {len(unexplained)} {unexplained[:12]}")
for d, step, amb in events:
    L.append(f"  {d}  step {step:+8.2f} bp{'  (ambiguous: previous close also fits the new grid)' if amb else ''}")
open(OUT, "w").write("\n".join(L) + "\n")
print("\n".join(L[:3]))
print(f"... {len(events)} events written to {OUT}")
