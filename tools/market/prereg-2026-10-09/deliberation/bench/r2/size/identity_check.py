"""
SYNTHETIC. The coordinator's decisive test: each placebo design's IDENTITY arrangement
(within-cycle at the observed offsets, linear and circular; shift by 0; blocks in their
original order), fed through exactly the placebo evaluator (margin_walk + ProbeSet.stats),
must reproduce the observed CAGR and the observed change list, in every cell.
"""
import datetime as dt, itertools, random, sys
sys.path.insert(0, "/home/user/ca/tools/market")
sys.path.insert(0, "/tmp/claude-0/-home-user-ca/2758dbcb-e96c-587b-81c2-e59b0c402304/scratchpad/edge/bench/r2/size")
import edgelab as E
import size_study as Z

wc = E.WithinCycle(Z.LEVELS, Z.CYCLES, 1.0)
wcc = E.WithinCycle(Z.LEVELS, Z.CYCLES, 1.0, wrap=True)
sp = E.ShiftPlacebo(Z.LEVELS)
bp = E.BlocksPlacebo(Z.LEVELS, 1.0)
ids = {"within_cycle": wc.arrange(wc.observed), "within_cycle_circular": wcc.arrange(wcc.observed),
       "shift": sp.arrange(0), "blocks": bp.arrange(*bp.identity())}
print("observed offsets all zero:", set(wc.observed) == {0}, "| plan blocks", len(wc.plan),
      "| change lists identical to the rule's:",
      {k: v == Z.CHANGES for k, v in ids.items()})
r_on, r_id = Z.gen_returns("garch", random.Random(5), len(Z.DATES))
bars = Z.bars_from(r_on, r_id)
dist = {Z.SC[100]: 0.5, Z.SC[4000]: 0.7}               # two synthetic add-backs inside the window
worst = 0.0
n = 0
for cost, cash, spread, accrual, co, dd in itertools.product(
        (0.0, 2e-4, 5e-4), (0.0, 0.015, 0.03), (0.015, 0.04), ("calendar", "session"), (False, True),
        (None, dist)):
    ML = E.margin_legs(bars, Z.S0, Z.LAST, E.CashRate(rate=cash), spread, Z.CAL, accrual, dd, co)
    obs = Z.PROBES.stats(E.margin_walk(Z.CHANGES, ML, cost, Z.PROBES.points)["probes"])
    full = E.margin_walk(Z.CHANGES, ML, cost, detail=True)
    sc = E.score_margin(full, ML, Z.START, Z.LEVELS)
    worst = max(worst, abs(sc["cagr"] - obs[0]))
    for k, ch in ids.items():
        st = Z.PROBES.stats(E.margin_walk(ch, ML, cost, Z.PROBES.points)["probes"])
        worst = max(worst, max(abs(a - b) for a, b in zip(st, obs)))
    n += 1
print(f"{n} cells (cost x cash x spread x accrual x closes-only x add-backs): largest |identity - observed| "
      f"over CAGR, both halves and ex-crises = {worst:.3e}")
