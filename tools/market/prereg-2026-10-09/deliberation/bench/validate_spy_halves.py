"""ONE hypothesis for the published §C halves: the split EVIDENCE uses elsewhere,
2005-2015 | 2016-2026 (i.e. the first half ends at the last close of 2015).
Tested once; no other split is searched. Run from tools/market."""
import datetime as dt, json, os, sys
sys.path.insert(0, os.getcwd())
import edgelab as E
spy = E.load("bars/SPY-1d.csv", "SPY", "stooq", True)
bars = spy.bars
legs = E.build_legs(bars, 0, len(bars) - 1, E.CashRate(rate=0.0))
def comp(xs):
    p = 1.0
    for x in xs: p *= 1 + x
    return p - 1
cut = sum(1 for d in legs.dates if d <= dt.date(2015, 12, 31))
res = {"split_after": legs.dates[cut - 1].isoformat(),
       "overnight": [comp(legs.r_on[:cut]), comp(legs.r_on[cut:])],
       "intraday": [comp(legs.r_id[:cut]), comp(legs.r_id[cut:])],
       "published": {"overnight": [0.82, 1.57], "intraday": [0.02, 0.71]}}
txt = (f"split after {res['split_after']} (2005-2015 | 2016-2026): overnight {res['overnight'][0]:+.2%} then "
       f"{res['overnight'][1]:+.2%}; intraday {res['intraday'][0]:+.2%} then {res['intraday'][1]:+.2%}   "
       f"published +82%/+157%, +2%/+71%")
print(txt)
open(sys.argv[1], "w").write(txt + "\n\n" + json.dumps(res, indent=1) + "\n")
