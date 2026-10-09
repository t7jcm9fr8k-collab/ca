#!/usr/bin/env python3
"""r4_verify3.py — QQQ veto book: z_used (edgelab.timing_book, block 10, 5,000 draws, seed 20261009) at the
six 2 bp pairs without each subset of its three gap legs (1999-11-16 data hole; 2001-09-11..14 closures;
2004-06-11 closure). Usage: python3 -I -B r4_verify3.py <tools/market> <out>"""
import datetime as dt, itertools, math, os, sys
TOOLS, OUT = sys.argv[1:3]
sys.path.insert(0, TOOLS); os.chdir(TOOLS)
import edgelab as E
PAIRS = [(0.015, 0.015), (0.015, 0.04), (0.0, 0.015), (0.0, 0.04), (0.03, 0.015), (0.03, 0.04)]
series = E.load("bars/QQQ-1d-long.csv", None, "stooq", True, "2025-03-24")
r0 = E._as_factory("month_end_overlay")()
bars = series.bars; da = [b.ts.date() for b in bars]; cal = E.Calendar(da[0], da[-1])
s0, last = E._window(da, r0.warmup, None, dt.date(2005, 2, 22), dt.date(1999, 3, 25))
w_on, w_id, _ = E.decide_all(series, r0, cal, s0, last, 1)
levels = E.interleave(w_on, w_id); ch = E.levels_to_changes(levels)
trade = [leg for leg, e, f in ch if leg > 0]; p_hat = sum(levels) / len(levels)
L = []
worst = None
for cash, spread in PAIRS:
    ML = E.margin_legs(bars, s0, last, E.CashRate(rate=cash), spread, cal, "calendar", None, True)
    r = E.session_returns(E.margin_walk(ch, ML, 0.0002, detail=True)["marks"][2::2])
    a = E.session_returns(E.margin_walk(E.constant_changes(p_hat, trade), ML, 0.0002, detail=True)["marks"][2::2])
    g = [j for j in range(len(r)) if ML.gap[j]]
    row = []
    for k in range(0, len(g) + 1):
        for sub in itertools.combinations(g, k):
            keep = [j for j in range(len(r)) if j not in sub]
            z = E.timing_book([r[j] for j in keep], [a[j] for j in keep], None, 100, 10, 5000, 20261009)["log"]["z_used"]
            lab = "+".join(str(ML.dates[j]) for j in sub) or "none"
            row.append(f"without {lab}: {z:+.4f}")
            if worst is None or z < worst[0]:
                worst = (z, cash, spread, lab)
    L.append(f"cash {cash:.2%} spread {spread:.2%} | " + "; ".join(row))
L.append(f"smallest z_used over the six pairs and all {2 ** 3} subsets: {worst[0]:+.4f} (cash {worst[1]:.2%}, spread "
         f"{worst[2]:.2%}, without {worst[3]}); veto needs < -1")
open(OUT, "w").write("\n".join(L) + "\n"); print("\n".join(L))
