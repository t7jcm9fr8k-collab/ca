"""
SYNTHETIC, harness-free check of WHY uniform within-cycle placement over-rejects:
257 cycles of 21 sessions, a 7-session block at offset 0 of each (the observed
placement). Statistic = sum of i.i.d. N(0,1) returns inside the blocks.
Null A ('linear'): each block starts uniformly in [0, 14], never crossing the cycle end.
Null B ('circular'): each block starts uniformly in [0, 20] and wraps inside its cycle.
Under H0 the p-value must be uniform; reports the rejection rate at 0.05 and the
p-value deciles over R replications with B draws each.
"""
import random, sys
C, L, BL = 257, 21, 7
R, B = int(sys.argv[1]) if len(sys.argv) > 1 else 2000, 200
rng = random.Random(20261009)
for mode in ("linear", "circular"):
    rej, dec = 0, [0] * 10
    for _ in range(R):
        x = [[rng.gauss(0, 1) for _ in range(L)] for _ in range(C)]
        pre = []
        for row in x:
            ext = row + row                     # circular access
            if mode == "linear":
                pre.append([sum(row[u:u + BL]) for u in range(L - BL + 1)])
            else:
                pre.append([sum(ext[u:u + BL]) for u in range(L)])
        obs = sum(p[0] for p in pre)
        k = 0
        for _ in range(B):
            s = sum(p[rng.randrange(len(p))] for p in pre)
            k += s >= obs
        pv = (1 + k) / (1 + B)
        rej += pv < 0.05
        dec[min(9, int(pv * 10))] += 1
    print(f"{mode:<9} R={R} B={B}: rejection at 0.05 = {rej / R:.3f}; p-value deciles {dec}")
