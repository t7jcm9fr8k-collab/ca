#!/usr/bin/env python3
"""SYNTHETIC only: P(G3 passes) for the overlay vs constant leverage, by drawdown tolerance,
with and without a window effect (delta = 10 bp/day * h). Markov-volatility model as ddnoise.py."""
import math, random
SESS = 5413
W = ([0] * 14 + [1] * 7) * (SESS // 21 + 1)
W = W[:SESS]
p = sum(W) / SESS
MU = 4.66e-4
F = 0.025 / 252

def path(rng, delta):
    out, state = [], 0
    for w in W:
        if state == 0 and rng.random() < 0.005:
            state = 1
        elif state == 1 and rng.random() < 0.045:
            state = 0
        m = MU + ((1 - p) * delta if w else -p * delta)
        out.append(rng.gauss(m, 0.025 if state else 0.009))
    return out

def maxdd(r, lev):
    eq = peak = 1.0
    worst = 0.0
    for x, L in zip(r, lev):
        eq *= 1 + L * x - (L - 1) * F
        peak = max(peak, eq)
        worst = min(worst, eq / peak - 1)
    return worst

rng = random.Random(11)
for h in (0.0, 0.38, 1.0):
    diffs = []
    for _ in range(300):
        r = path(rng, 10e-4 * h)
        diffs.append((maxdd(r, [1 + w for w in W]) - maxdd(r, [1 + p] * SESS)) * 100)
    out = ", ".join(f"tol {t} pts: P(pass) {sum(1 for d in diffs if d >= -t)/len(diffs):.2f}" for t in (0.5, 2, 5, 10))
    print(f"h={h:4.2f}: mean gap {sum(diffs)/len(diffs):+.2f} pts; {out}")
