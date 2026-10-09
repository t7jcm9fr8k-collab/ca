#!/usr/bin/env python3
"""
SYNTHETIC only (no market data). G6 concentration criteria on the per-cycle timing book
D_c = sum over a 21-session cycle of (1_W - p)(r - f), 258 cycles, 7-session window.
Return model: 2-state Markov volatility (calm 0.9%/day, stressed 2.5%/day, as ddnoise.py),
mean 4.66 bp/day, window-minus-outside effect delta = 10 bp/day * h. f cancels (constant).
  (A) r2-redteam draft: top-5 positive cycles supply <= 50% of the total (total must be > 0)
  (B) Flow G6': total minus the 5 largest positive cycles >= 0
Also: P(total > 0), the plain sign of the timing book.
"""
import random
CYC, WIN = 21, 7
NC = 258
p = WIN / CYC
MU = 4.66e-4

def run(h, reps=2000, seed=5):
    rng = random.Random(seed)
    a = b = s = 0
    for _ in range(reps):
        state = 0
        cyc = []
        for c in range(NC):
            tot = 0.0
            for i in range(CYC):
                if state == 0 and rng.random() < 0.005:
                    state = 1
                elif state == 1 and rng.random() < 0.045:
                    state = 0
                w = 1 if i >= CYC - WIN else 0
                d = 10e-4 * h
                m = MU + ((1 - p) * d if w else -p * d)
                r = rng.gauss(m, 0.025 if state else 0.009)
                tot += (w - p) * r
            cyc.append(tot)
        total = sum(cyc)
        top5 = sum(sorted([x for x in cyc if x > 0], reverse=True)[:5])
        s += total > 0
        a += total > 0 and top5 <= 0.5 * total
        b += (total - top5) >= 0
    return s / reps, a / reps, b / reps

for h in (0.0, 0.38, 0.69, 1.0):
    s, a, b = run(h)
    print(f"h={h:4.2f}: P(timing book > 0) {s:.3f} | (A) top-5 <= 50% of total: {a:.3f} | (B) total minus top-5 >= 0: {b:.3f}")
