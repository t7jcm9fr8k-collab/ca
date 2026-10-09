#!/usr/bin/env python3
"""
threeway_open.py — Quartermaster, round 1. Which vendor's OPEN is wrong?

On dates (>= 2020-07-27) where stooq's open and nasdaq.com's open disagree by
more than 10 bp after removing the day's close-ratio factor, bring in a third
witness: Alpaca's IEX open (also normalised by its own close ratio to nasdaq).
IEX's first print is not the official open, so it is a noisy witness; the
question is only which of the two disagreeing opens it sits closer to.

Run: python3 -I -B threeway_open.py <bars dir> <nasdaq dir> <out file>
"""
import csv
import os
import sys

BARS, NASDAQ, OUT = sys.argv[1:4]


def load(p):
    rows = [r for r in csv.reader(open(p, newline="")) if r and not r[0].startswith("#")][1:]
    return {r[0][:10]: tuple(float(x) for x in r[1:6]) for r in rows}


L = ["threeway_open — stooq vs nasdaq open disagreements > 10 bp, with Alpaca IEX as third witness",
     "values are opens expressed on nasdaq's price basis: file_open / (file_close / nasdaq_close)"]
tot = {"stooq closer": 0, "nasdaq closer": 0}
for s in ["DIA", "EEM", "EFA", "GLD", "IWM", "QQQ", "TLT", "XLE", "XLF"]:
    S = load(os.path.join(BARS, f"{s}-1d-long.csv"))
    N = load(os.path.join(NASDAQ, f"{s}-1d-nasdaq.csv"))
    A = load(os.path.join(BARS, f"{s}-1d.csv"))
    cnt = {"stooq closer": 0, "nasdaq closer": 0}
    rows = []
    for d in sorted(set(S) & set(N) & set(A)):
        so = S[d][0] / (S[d][3] / N[d][3])
        ao = A[d][0] / (A[d][3] / N[d][3])
        no = N[d][0]
        if abs(so / no - 1) > 1e-3:
            ds, dn = abs(ao / so - 1) * 1e4, abs(ao / no - 1) * 1e4
            who = "stooq closer" if ds < dn else "nasdaq closer"
            cnt[who] += 1
            rows.append(f"   {d}  stooq {so:.4f}  nasdaq {no:.4f}  alpaca-IEX {ao:.4f}  "
                        f"|IEX-stooq| {ds:6.1f} bp  |IEX-nasdaq| {dn:6.1f} bp  -> IEX {who}")
    tot["stooq closer"] += cnt["stooq closer"]; tot["nasdaq closer"] += cnt["nasdaq closer"]
    L.append(f"\n## {s}: {len(rows)} disagreement(s) on dates all three files hold; IEX open closer to "
             f"stooq {cnt['stooq closer']}, to nasdaq {cnt['nasdaq closer']}")
    L.extend(rows)
L.append(f"\nTOTAL: IEX closer to stooq {tot['stooq closer']}, to nasdaq {tot['nasdaq closer']}")
open(OUT, "w").write("\n".join(L) + "\n")
print("\n".join(L))
