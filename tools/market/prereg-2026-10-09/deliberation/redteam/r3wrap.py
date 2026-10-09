#!/usr/bin/env python3
"""Red Team r3: expected trading sides per cycle of S1 vs placebo designs (combinatorics, no data).
Cycle of L sessions, 2x block of 7; S1's block sits at offset 0 of every cycle. Sides = exposure
changes between consecutive sessions, counting the boundary into the next cycle (shared)."""
import math, random
from statistics import NormalDist
def path_cycle(L, s, circular):
    x = [0]*L
    for i in range(7):
        j = s + i
        if j >= L:
            if not circular: raise ValueError
            j -= L
        x[j] = 1
    return x
def sides(cycles):
    flat = [v for c in cycles for v in c]
    return sum(abs(a-b) for a, b in zip(flat, flat[1:]))
rng = random.Random(20261009)
for L in (19, 21, 23):
    n = 20000
    s1 = sides([path_cycle(L, 0, False) for _ in range(n)]) / n
    d7 = sides([path_cycle(L, rng.randint(0, L-7), False) for _ in range(n)]) / n
    ci = sides([path_cycle(L, rng.randrange(L), True) for _ in range(n)]) / n
    exact_ci = (2*1 + (L-8)*2 + 6*2)/L + 2*(7/L)*(1-7/L)
    print(f"L={L}: sides/cycle S1 {s1:.3f}; D7 (no wrap) {d7:.3f}; circular {ci:.3f} (exact {exact_ci:.3f}); "
          f"circular extra {ci-s1:+.3f} -> {12*(ci-s1)*2:.1f} bp/yr at 2 bp, {12*(ci-s1)*5:.1f} bp/yr at 5 bp")
# effect on G4 size if extra placebo cost shifts the placebo CAGR down by c (SD of placebo CAGR ~ TE/sqrt(Y))
SIG=0.192; P=1/3; Y=5387/252; sd = math.sqrt(P*(1-P))*SIG/math.sqrt(Y)
for bp in (8.4, 14.0):
    shift = bp/1e4/sd
    print(f"placebo cost bias {bp:.1f} bp/yr = {shift:.3f} SD -> size at nominal 0.05: {1-NormalDist().cdf(1.6449-shift):.4f}")
