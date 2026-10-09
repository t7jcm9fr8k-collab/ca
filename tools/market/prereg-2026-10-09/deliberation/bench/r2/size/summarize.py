"""Aggregate the size/power study outputs (synthetic). Writes the table to argv[1] (default size-power.txt)."""
import glob, json, math, sys
rows = {}
for p in sorted(glob.glob("out-*.jsonl") + glob.glob("outc-*.jsonl")):
    for line in open(p):
        o = json.loads(line)
        rows.setdefault((o["gen"], o["delta_bp"]), {}).setdefault(o["rep"], {}).update(o)
methods = ("within_cycle", "within_cycle_circular", "shift", "blocks")
short = {"within_cycle": "WC linear", "within_cycle_circular": "WC circular", "shift": "shift", "blocks": "blocks"}
L = ["SYNTHETIC size/power of the placebo designs, run through edgelab's own code (size_study.py).",
     "S1-shaped overlay (2x T-3..T+3, 1x otherwise, MOC), real scheduled calendar, scored close 2005-03-24 ..",
     "close 2026-08-25 (5,387 sessions, 257 cycles), 2 bp/side, cash 1.5%, spread 1.5%, B = 200 draws per",
     "replication. Each cell: rejection rate at one-sided p < 0.05 (± its binomial SE), at p < 0.025, and 'G4' =",
     "p < 0.05 AND the rule beats the null median CAGR in each half. R = replications. delta = bp per window",
     "added to the window sessions' mean (delta/7 a session). Generators: see size_study.py's docstring.",
     "Size holds when the delta=0 rate is <= 0.05 + 2 binomial SE (0.064 at R = 1000).", ""]
hdr = f"{'gen':<7}{'delta':>6}" + "".join(f"{short[m]:>32}" for m in methods)
sub = f"{'':13}" + "".join(f"{'R':>6}{'a.05':>6}{'(±SE)':>8}{'a.025':>6}{'G4':>6}" for m in methods)
L += [hdr, sub]
order = {"iid": 0, "garch": 1, "regime": 2}
for (g, d) in sorted(rows, key=lambda k: (k[1], order.get(k[0], 9))):
    reps = list(rows[(g, d)].values())
    cells = []
    for m in methods:
        rr = [r for r in reps if m in r and r[m]["p"] is not None]
        n = len(rr)
        if not n:
            cells.append(f"{'—':>32}")
            continue
        r05 = sum(1 for r in rr if r[m]["p"] < 0.05) / n
        r025 = sum(1 for r in rr if r[m]["p"] < 0.025) / n
        g4 = sum(1 for r in rr if r[m]["p"] < 0.05 and r[m]["halves"]) / n
        se = math.sqrt(max(r05 * (1 - r05), 1e-12) / n)
        cells.append(f"{n:>6}{r05:>6.3f}{'(' + format(se, '.3f') + ')':>8}{r025:>6.3f}{g4:>6.3f}")
    L.append(f"{g:<7}{d:>6g}" + "".join(cells))
L.append("")
L.append("Dispersion of the observed statistic against its own null, delta = 0 (an exact test gives sd(z) ~ 1, "
         "uniform p):")
for g in ("iid", "garch", "regime"):
    reps = list(rows.get((g, 0.0), {}).values())
    for m in methods:
        zs = [r[m]["z"] for r in reps if m in r and r[m]["z"] is not None]
        ps = [r[m]["p"] for r in reps if m in r and r[m]["p"] is not None]
        if len(zs) > 2:
            mz = sum(zs) / len(zs)
            sz = math.sqrt(sum((z - mz) ** 2 for z in zs) / (len(zs) - 1))
            dec = [sum(1 for p in ps if k / 10 <= p < (k + 1) / 10) for k in range(10)]
            L.append(f"  {g:<7}{short[m]:<12} sd(z) {sz:.3f}  mean z {mz:+.3f}  p deciles {dec}")
text = "\n".join(L)
print(text)
open(sys.argv[1] if len(sys.argv) > 1 else "size-power.txt", "w").write(text + "\n")
