"""
Bench validation on SPY-1d.csv — the ONLY real-data computations beyond
buy-and-hold on each file: the buy-and-hold overnight/intraday decomposition
EVIDENCE.md "Day run" §C already published, the same totals through the rule
path, and two data checks that explain differences. No calendar-, event- or
signal-conditioned statistic is computed. No per-year leg split is computed.
Run from tools/market:  python3 -B <this file> <out.txt>
"""
import datetime as dt
import json
import os
import sys

sys.path.insert(0, os.getcwd())
import bars as B
import edgelab as E
import replay

out_path = sys.argv[1]
L, J = [], {}
spy = E.load("bars/SPY-1d.csv", "SPY", "stooq", True)

# --- 1. the decomposition, the harness's own convention (start at the first close, date-midpoint halves)
d = E.decompose(spy)
J["decompose"] = {k: v for k, v in d.items() if k != "calendar"}
w, h1, h2 = d["whole"], d["first_half"], d["second_half"]
L.append("SPY-1d.csv buy-and-hold, split into legs (edgelab.decompose; no cost, no cash)")
L.append(f"  window: close {w['from_close']} -> close {w['to_close']}, {w['sessions']} sessions")
L.append(f"  overnight (close->open) compounds {w['overnight']:+.4%}   published +367%")
L.append(f"  intraday  (open->close) compounds {w['intraday']:+.4%}   published +75%")
L.append(f"  whole                   compounds {w['whole']:+.4%}   published +717%")
L.append(f"  close-to-close check (C_last / C_first - 1): {d['close_to_close_check']:+.6%}")
L.append(f"  mean per night {w['mean_bp_overnight']:+.3f} bp, per day {w['mean_bp_intraday']:+.3f} bp"
         f"   published +3.1 / +1.5")
L.append(f"  Sharpe (per-leg, sqrt 252, no cash) overnight {w['sharpe_overnight']:.3f}, intraday "
         f"{w['sharpe_intraday']:.3f}   published 0.69 / 0.25")
L.append(f"  halves at the DATE midpoint {d['split_date']}: overnight {h1['overnight']:+.2%} then "
         f"{h2['overnight']:+.2%}; intraday {h1['intraday']:+.2%} then {h2['intraday']:+.2%}"
         f"   published +82%/+157%, +2%/+71%")

# --- 2. halves at the BAR midpoint, to see which convention §C used
bars = spy.bars
legs = E.build_legs(bars, 0, len(bars) - 1, E.CashRate(rate=0.0))
S = len(legs.r_on)


def comp(xs):
    p = 1.0
    for x in xs:
        p *= 1 + x
    return p - 1


cut = S // 2
J["bar_midpoint_halves"] = {"cut_session": legs.dates[cut - 1].isoformat(),
                            "overnight": [comp(legs.r_on[:cut]), comp(legs.r_on[cut:])],
                            "intraday": [comp(legs.r_id[:cut]), comp(legs.r_id[cut:])]}
b = J["bar_midpoint_halves"]
L.append(f"  halves at the BAR midpoint (after {b['cut_session']}): overnight {b['overnight'][0]:+.2%} then "
         f"{b['overnight'][1]:+.2%}; intraday {b['intraday'][0]:+.2%} then {b['intraday'][1]:+.2%}")

# --- 3. the same totals through the RULE path (decide_all + walk), zero cost, zero cash.
#        Only the final equity is computed: no per-year table, no halves, no placebo.
cal = E.Calendar(bars[0].ts.date(), bars[-1].ts.date())
J["rule_path"] = {}
L.append("")
L.append("the same totals through the rule path (edgelab.decide_all + edgelab.walk, cost 0, cash 0)")
for name, ref in (("test_overnight_only", w["overnight"]), ("test_intraday_only", w["intraday"]),
                  ("buy_and_hold", w["whole"])):
    w_on, w_id, _ = E.decide_all(spy, E.RULES[name](), cal, 0, len(bars) - 1)
    p = E.walk(w_on, w_id, legs.i_on, legs.i_id, legs.g_on, 0.0)
    tot = p["closes"][-1] - 1
    J["rule_path"][name] = {"total": tot, "decompose": ref, "abs_diff": abs(tot - ref)}
    L.append(f"  {name:<20} {tot:+.10%}   decompose {ref:+.10%}   |diff| {abs(tot - ref):.2e}")

# --- 4. conventions that would move the numbers, to explain any difference
L.append("")
L.append("conventions that move the totals (explaining differences, not choosing)")
open0 = bars[-1].close / bars[0].open - 1
L.append(f"  start at the first OPEN instead of the first close (adds session 0's intraday leg): whole "
         f"{open0:+.4%}, intraday {comp(legs.r_id) * 0 + (bars[0].close / bars[0].open) * (1 + w['intraday']) - 1:+.4%}")
J["start_at_first_open"] = {"whole": open0}
dx = E.decompose(spy, end=dt.date(2026, 9, 1))["whole"]
J["without_partial_final_bar"] = {k: dx[k] for k in ("overnight", "intraday", "whole", "to_close")}
L.append(f"  without the final bar 2026-09-02 (flagged partial): overnight {dx['overnight']:+.4%}, intraday "
         f"{dx['intraday']:+.4%}, whole {dx['whole']:+.4%}")
L.append(f"  gap legs in the window (overnight legs spanning a scheduled session with no bar): "
         f"{', '.join(d['gap_legs'])}")

# --- 5. the final bar against the nasdaq official file (prices on one date, no return)
raw = E.load("bars/SPY-1d-raw.csv", "SPY", "nasdaq", False)
rmap = {x.ts.date(): x for x in raw.bars}
fb = bars[-1]
rb = rmap.get(fb.ts.date())
J["final_bar_vs_nasdaq"] = {"date": fb.ts.date().isoformat(), "stooq": [fb.open, fb.high, fb.low, fb.close, fb.volume],
                            "nasdaq": [rb.open, rb.high, rb.low, rb.close, rb.volume] if rb else None}
L.append("")
L.append(f"final bar {fb.ts.date()}: stooq O/H/L/C/V {fb.open} {fb.high} {fb.low} {fb.close} {fb.volume:.0f}; "
         f"nasdaq official {rb.open} {rb.high} {rb.low} {rb.close} {rb.volume:.0f}")

# --- 6. is stooq's dividend adjustment applied to the open and the close alike? (prices, no return)
common = [x for x in bars if x.ts.date() in rmap]
dev = []
for x in common:
    r = rmap[x.ts.date()]
    fo, fc = x.open / r.open, x.close / r.close
    dev.append((abs(fo / fc - 1), x.ts.date().isoformat(), fo, fc))
dev_sorted = sorted(dev, reverse=True)
med = sorted(z[0] for z in dev)[len(dev) // 2]
J["adjustment_open_vs_close"] = {"common_dates": len(common), "median_abs_dev": med,
                                 "worst": dev_sorted[:5]}
L.append(f"adjustment factor open vs close, SPY-1d.csv / SPY-1d-raw.csv over {len(common)} common dates: "
         f"median |f_open/f_close - 1| = {med:.2e}; worst five:")
for z in dev_sorted[:5]:
    L.append(f"    {z[1]}  f_open {z[2]:.6f}  f_close {z[3]:.6f}  |dev| {z[0]:.2e}")

# --- 7. why max drawdown reads -56.7% here and -56.5% in EVIDENCE: marks at opens vs closes only
bh = [x.close / bars[0].close for x in bars]
dd_close = replay.max_drawdown(bh)
marks = [1.0]
for x in bars[1:]:
    marks.append(x.open / bars[0].close)
    marks.append(x.close / bars[0].close)
dd_all = replay.max_drawdown(marks)
J["max_drawdown_marks"] = {"closes_only": dd_close, "opens_and_closes": dd_all}
L.append(f"buy-and-hold max drawdown, closes only {dd_close:+.4%}; opens and closes {dd_all:+.4%}")

text = "\n".join(L)
print(text)
with open(out_path, "w") as f:
    f.write(text + "\n\n" + json.dumps(J, indent=1, default=str) + "\n")
