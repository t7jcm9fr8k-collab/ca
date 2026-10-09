#!/usr/bin/env python3
"""r4_split.py — split of the S1 log timing book (primary cell) between sessions held at 2x (inside the
window) and at 1x (outside), for the top-5 positive cycles and for the whole span. Verification only.
Usage: python3 -I -B r4_split.py <tools/market> <out>"""
import datetime as dt, math, os, sys
TOOLS, OUT = sys.argv[1:3]
sys.path.insert(0, TOOLS); os.chdir(TOOLS)
import edgelab as E
series = E.load("bars/SPY-1d.csv", None, "stooq", True, "2025-03-21")
r0 = E._as_factory("month_end_overlay")()
bars = series.bars; da = [b.ts.date() for b in bars]; cal = E.Calendar(da[0], da[-1])
s0, last = E._window(da, r0.warmup, None, dt.date(2026, 8, 25), dt.date(2005, 3, 24))
w_on, w_id, _ = E.decide_all(series, r0, cal, s0, last, 1)
levels = E.interleave(w_on, w_id); dates = da[s0 + 1:last + 1]
applied = E.place_distributions(E.load_distributions("prereg-2026-10-09/spy-distributions-2025-2026.csv"),
                                series, dates[0], dates[-1])["applied"]
ML = E.margin_legs(bars, s0, last, E.CashRate(rate=0.015), 0.015, cal, "calendar", applied, True)
ch = E.levels_to_changes(levels); trade = [leg for leg, e, f in ch if leg > 0]; p_hat = sum(levels) / len(levels)
r = E.session_returns(E.margin_walk(ch, ML, 0.0002, detail=True)["marks"][2::2])
a = E.session_returns(E.margin_walk(E.constant_changes(p_hat, trade), ML, 0.0002, detail=True)["marks"][2::2])
d = [math.log1p(x) - math.log1p(y) for x, y in zip(r, a)]
e = [(levels[2 * j] + levels[2 * j + 1]) / 2 for j in range(len(dates))]
cyc, _ = E.session_cycles(dates, cal, r0.anchor or (lambda f: f.is_month_end))
per = [sum(d[j0:j1]) for j0, j1 in cyc]
L = [f"sum d {sum(d):+.5f}: at 2x {sum(x for x, y in zip(d, e) if y > 1.5):+.5f} ({sum(1 for y in e if y > 1.5)} sessions), "
     f"at 1x {sum(x for x, y in zip(d, e) if y < 1.5):+.5f} ({sum(1 for y in e if y < 1.5)} sessions)"]
for n, k in enumerate(sorted(range(len(cyc)), key=lambda k: -per[k])[:5], 1):
    j0, j1 = cyc[k]
    i2 = sum(d[j] for j in range(j0, j1) if e[j] > 1.5); i1 = sum(d[j] for j in range(j0, j1) if e[j] < 1.5)
    L.append(f"#{n} {dates[j0]}..{dates[j1-1]}: sum d {per[k]:+.4f} = at 2x {i2:+.4f} + at 1x {i1:+.4f}")
top = sorted(range(len(cyc)), key=lambda k: -per[k])[:5]
L.append(f"top-5 together: at 2x {sum(sum(d[j] for j in range(*cyc[k]) if e[j] > 1.5) for k in top):+.4f}, "
         f"at 1x {sum(sum(d[j] for j in range(*cyc[k]) if e[j] < 1.5) for k in top):+.4f}")
open(OUT, "w").write("\n".join(L) + "\n"); print("\n".join(L))
