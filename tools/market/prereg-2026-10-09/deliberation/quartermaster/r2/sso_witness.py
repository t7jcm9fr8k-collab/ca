#!/usr/bin/env python3
"""
sso_witness.py — Quartermaster round 2. A data-derived witness for SPY's
ex-dividend dates and amounts where no total-return SPY file exists.

SSO seeks 2x the DAILY return of the S&P 500 (a price index). SPY's price
falls by its distribution D on its own ex-date, which the index does not.
So x_t = r_SSO,t - 2 r_SPY,t is a small negative drift (fees, financing, the
dividend accrual inside SPY's NAV) plus a spike of about +2 D/P(t-1) on SPY's
ex-dates (and a negative spike on SSO's own ex-dates). Official nasdaq.com
closes for both (split back-adjusted, not dividend-adjusted).

Validation first: on the 34 SPY ex-dates located in round 1 (stooq vs
nasdaq, 2016-12..2025-03) compare x_t/2 with the stooq step. Then list the
largest positive x_t from 2025-03-22 onward as candidate ex-dates, with the
implied D = (x_t / 2) * close_SPY(t-1).

Basis data only: no rule, no window, no conditional return statistic.
Run: python3 -I -B sso_witness.py <nasdaq dir> <basis-events.csv> <out>
"""
import csv, os, statistics as st, sys
NAS, EV, OUT = sys.argv[1:4]


def load(p):
    rows = [r for r in csv.reader(open(p, newline=""))][1:]
    return {r[0][:10]: float(r[4]) for r in rows}


spy = load(os.path.join(NAS, "SPY-1d-nasdaq.csv"))
sso = load(os.path.join(NAS, "SSO-1d-nasdaq.csv"))
ds = sorted(set(spy) & set(sso))
x = {}
for a, b in zip(ds, ds[1:]):
    x[b] = (sso[b] / sso[a] - 1) - 2 * (spy[b] / spy[a] - 1)

known = {}
for r in csv.DictReader(open(EV)):
    if r["pair"].startswith("stooq SPY-1d.csv"):
        known[r["event_date"]] = float(r["jump_bp"])

L = ["sso_witness — x_t = r_SSO - 2 r_SPY on nasdaq.com official closes",
     f"dates {ds[0]}..{ds[-1]}; {len(x)} daily values"]
allx = [v * 1e4 for v in x.values()]
L.append(f"x_t, bp: median {st.median(allx):+.2f}; middle 90% {sorted(allx)[len(allx)//20]:+.2f}..{sorted(allx)[-len(allx)//20]:+.2f}")

L.append("\nValidation on the 34 SPY ex-dates located in round 1 (stooq step vs x_t/2):")
diffs, ranks = [], []
srt = sorted(x.items(), key=lambda kv: -kv[1])
rank_of = {d: i + 1 for i, (d, v) in enumerate(srt)}
for d, step in sorted(known.items()):
    if d in x:
        half = x[d] * 1e4 / 2
        diffs.append(half - step)
        ranks.append(rank_of[d])
        L.append(f"   {d}  stooq step {step:6.2f} bp   x/2 {half:6.2f} bp   diff {half - step:+6.2f}   rank of x_t among all days {rank_of[d]}")
L.append(f"   diff x/2 - step: median {st.median(diffs):+.2f} bp, worst |diff| {max(abs(v) for v in diffs):.2f} bp; "
         f"ranks of known ex-dates among all {len(x)} days: max {max(ranks)}")
# false positives: how many non-ex-dates have x_t larger than the smallest known ex-date x_t (pre-cutoff span)
pre = {d: v for d, v in x.items() if d <= "2025-03-21"}
kmin = min(pre[d] for d in known if d in pre)
fp = sorted((d for d, v in pre.items() if v >= kmin and d not in known))
L.append(f"   non-ex-dates (<= 2025-03-21) with x_t >= the smallest known ex-date x_t ({kmin*1e4:.1f} bp): {len(fp)} {fp[:10]}")

L.append("\nAfter the stooq cutoff (2025-03-22 .. last date): the 10 largest x_t, with implied D = x_t/2 * close_SPY(t-1)")
post = sorted(((d, v) for d, v in x.items() if d >= "2025-03-22"), key=lambda kv: -kv[1])[:10]
prevd = {b: a for a, b in zip(ds, ds[1:])}
for d, v in post:
    L.append(f"   {d}  x_t {v*1e4:+7.2f} bp  x/2 {v*1e4/2:6.2f} bp  SPY close(t-1) {spy[prevd[d]]:.2f}  implied D ${v/2*spy[prevd[d]]:.4f}")
open(OUT, "w").write("\n".join(L) + "\n")
print("\n".join(L))
