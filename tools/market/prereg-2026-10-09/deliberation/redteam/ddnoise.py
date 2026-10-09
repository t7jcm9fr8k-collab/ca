#!/usr/bin/env python3
"""
SYNTHETIC only (no market data): how far apart are the max drawdowns of the overlay
(1x + 1x in a fixed 7-of-21 window) and constant leverage 1+p when there is NO timing
effect? Two return models: i.i.d. normal, and a 2-state Markov volatility model
(calm 0.9%/day, stressed 2.5%/day, ~10% of days stressed, persistent). Both have the
same mean (4.66 bp/day). Financing 2.5%/yr on borrowed exposure, no costs.
Used only to calibrate a drawdown tolerance for G3; every parameter is an assumption.
"""
import math, random
SESS = 5413
P_W = ([0] * 14 + [1] * 7) * (SESS // 21 + 1)
P_W = P_W[:SESS]
p = sum(P_W) / SESS
MU = 4.66e-4
F = 0.025 / 252

def path(rng, model):
    if model == "iid":
        return [rng.gauss(MU, 0.0121) for _ in range(SESS)]
    out, state = [], 0
    for _ in range(SESS):
        if state == 0 and rng.random() < 0.005:
            state = 1
        elif state == 1 and rng.random() < 0.045:
            state = 0
        out.append(rng.gauss(MU, 0.025 if state else 0.009))
    return out

def maxdd(r, lev):
    eq = peak = 1.0
    worst = 0.0
    for x, L in zip(r, lev):
        eq *= 1 + L * x - (L - 1) * F
        peak = max(peak, eq)
        worst = min(worst, eq / peak - 1)
    return worst

rng = random.Random(7)
for model in ("iid", "markov"):
    diffs, dds = [], []
    for _ in range(300):
        r = path(rng, model)
        a = maxdd(r, [1 + w for w in P_W])
        b = maxdd(r, [1 + p] * SESS)
        c = maxdd(r, [1.0] * SESS)
        diffs.append((a - b) * 100)
        dds.append((a, b, c))
    diffs.sort()
    q = lambda x: diffs[int(x * (len(diffs) - 1))]
    mean = sum(diffs) / len(diffs)
    line = (f"{model:6s}: overlay DD minus constant DD (pts, negative = overlay deeper): mean {mean:+.2f}, "
            f"5th pct {q(0.05):+.2f}, 10th {q(0.10):+.2f}, median {q(0.5):+.2f}; "
            f"P(overlay worse by > 2 pts) {sum(1 for d in diffs if d < -2)/len(diffs):.2f}, "
            f"> 5 pts {sum(1 for d in diffs if d < -5)/len(diffs):.2f}; "
            f"median DDs overlay {sorted(x[0] for x in dds)[150]:.1%} constant {sorted(x[1] for x in dds)[150]:.1%} "
            f"1x {sorted(x[2] for x in dds)[150]:.1%}")
    print(line)
