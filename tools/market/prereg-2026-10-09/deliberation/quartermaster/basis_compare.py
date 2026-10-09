#!/usr/bin/env python3
"""
basis_compare.py — Quartermaster, round 1. PRICE-BASIS comparisons only.

What it measures (no rule, no calendar window, no signal, no return statistic):
  1. Per symbol and calendar year, the absolute gap between a file's Open/Close
     and nasdaq.com's official Open/Close on the same date:
        gap_bp = |file - nasdaq| / nasdaq * 1e4
     median and worst (with its date), plus the share of dates matching to the
     cent. Raw gaps include any dividend back-adjustment the file carries, so a
     second pair of columns removes that day's close ratio from the open:
        open_basis_bp = |(file_open/nasdaq_open) / (file_close/nasdaq_close) - 1| * 1e4
     which is ~0 when the file's open sits on the same basis as its close.
  2. Adjustment events: dates where the close ratio file/nasdaq shifts level
     (median of the 5 sessions from t onward vs the 5 before t differs by more
     than STEP_BP). At each event: the step size, and whether the file's OPEN on
     the event date sits on the post-event basis (r_open[t] ~ r_close[t]) or the
     pre-event basis (r_open[t] ~ r_close[t-1]). For a back-adjusted dividend
     series the event date is the ex-date and "post" means the dividend is
     removed from the close->open gap; "pre" would book it inside the session.
  3. Identity of the on-disk SPY-1d-raw.csv against the fresh nasdaq pull.

Every output line is about two files' prices on the same date. Nothing here is
grouped by an event, a calendar window or a rule.

Run: python3 -I -B basis_compare.py <bars dir> <nasdaq dir> <out dir>
"""
import csv
import datetime as dt
import os
import statistics as st
import sys

BARS, NASDAQ, OUT = sys.argv[1:4]
os.makedirs(OUT, exist_ok=True)
STEP_BP = 4.0          # level-shift threshold for an adjustment event
WIN = 5


def load(p):
    rows = [r for r in csv.reader(open(p, newline="")) if r and not r[0].startswith("#")][1:]
    out = {}
    for r in rows:
        out[r[0][:10]] = tuple(float(x) for x in r[1:6])   # o h l c v
    return out


def nas(sym):
    return load(os.path.join(NASDAQ, f"{sym}-1d-nasdaq.csv"))


def yearly_gaps(A, N, label, L, csvw):
    common = sorted(set(A) & set(N))
    by_year = {}
    for d in common:
        a, n = A[d], N[d]
        go = abs(a[0] - n[0]) / n[0] * 1e4
        gc = abs(a[3] - n[3]) / n[3] * 1e4
        rc = a[3] / n[3]
        ro = a[0] / n[0]
        gb = abs(ro / rc - 1) * 1e4
        cent_o = abs(a[0] - n[0]) < 0.005
        cent_c = abs(a[3] - n[3]) < 0.005
        by_year.setdefault(d[:4], []).append((d, go, gc, gb, cent_o, cent_c))
    L.append(f"\n## {label}: {len(common)} common dates {common[0]}..{common[-1]}")
    L.append(f"{'year':<6}{'n':>5} | {'open med bp':>11}{'open worst bp':>14} {'(date)':<12}"
             f"| {'close med bp':>12}{'close worst bp':>15} {'(date)':<12}"
             f"| {'open-basis med':>14}{'worst':>8} {'(date)':<12}| {'cent-exact O/C %':>16}")
    for y in sorted(by_year):
        rows = by_year[y]
        go = [r[1] for r in rows]; gc = [r[2] for r in rows]; gb = [r[3] for r in rows]
        wo = max(rows, key=lambda r: r[1]); wc = max(rows, key=lambda r: r[2]); wb = max(rows, key=lambda r: r[3])
        po = 100 * sum(r[4] for r in rows) / len(rows); pc = 100 * sum(r[5] for r in rows) / len(rows)
        L.append(f"{y:<6}{len(rows):>5} | {st.median(go):>11.2f}{wo[1]:>14.2f} {wo[0]:<12}"
                 f"| {st.median(gc):>12.2f}{wc[2]:>15.2f} {wc[0]:<12}"
                 f"| {st.median(gb):>14.2f}{wb[3]:>8.2f} {wb[0]:<12}| {po:>7.1f} / {pc:<7.1f}")
        csvw.writerow([label, y, len(rows), round(st.median(go), 3), round(wo[1], 3), wo[0],
                       round(st.median(gc), 3), round(wc[2], 3), wc[0],
                       round(st.median(gb), 3), round(wb[3], 3), wb[0], round(po, 1), round(pc, 1)])
    return common


def events(A, N, label, L, evw):
    """
    An adjustment event at t: the close ratio jumps on that single day by more
    than STEP_BP, the 5-session median level after t differs from the 5-session
    median before t by more than STEP_BP in the same direction, and the one-day
    jump is at least half of that level shift (so a noisy drift is not counted).
    The open on t is then compared with the close basis of t (post) and of t-1
    (pre); when the two differ by less than AMBIG_BP the open is "ambiguous".
    """
    AMBIG_BP = 2.0
    common = sorted(set(A) & set(N))
    rc = [A[d][3] / N[d][3] for d in common]
    ro = [A[d][0] / N[d][0] for d in common]
    found = []
    t = WIN
    while t < len(common) - WIN:
        jump = (rc[t] / rc[t - 1] - 1) * 1e4
        level = (st.median(rc[t:t + WIN]) / st.median(rc[t - WIN:t]) - 1) * 1e4
        if abs(jump) > STEP_BP and abs(level) > STEP_BP and jump * level > 0 and abs(jump) >= 0.5 * abs(level):
            post = abs(ro[t] / rc[t] - 1) * 1e4
            pre = abs(ro[t] / rc[t - 1] - 1) * 1e4
            v = "ambiguous" if abs(post - pre) < AMBIG_BP else ("post" if post < pre else "pre")
            found.append((common[t], jump, level, post, pre, v))
            t += 3
        else:
            t += 1
    cnt = {k: sum(1 for f in found if f[5] == k) for k in ("post", "pre", "ambiguous")}
    pos = sum(1 for f in found if f[1] > 0)
    last = found[-1][0] if found else "none"
    after = [abs(r - 1) * 1e4 for d, r in zip(common, rc) if found and d >= found[-1][0]]
    L.append(f"\n## {label}: {len(found)} adjustment event(s) (one-day jump and level shift > {STEP_BP} bp); "
             f"{pos} positive; open carries it (post) {cnt['post']}, does not (pre) {cnt['pre']}, "
             f"ambiguous {cnt['ambiguous']}; last event {last}"
             + (f"; median |ratio-1| from last event to file end {st.median(after):.2f} bp" if after else ""))
    for d, jump, level, post, pre, v in found:
        L.append(f"   {d}  jump {jump:+8.2f} bp  level {level:+8.2f} bp   open vs same-day close basis "
                 f"{post:6.2f} bp, vs prior close basis {pre:6.2f} bp  -> {v}")
        evw.writerow([label, d, round(jump, 3), round(level, 3), round(post, 3), round(pre, 3), v])
    return found


L = ["basis_compare — file prices against nasdaq.com official prices, same dates",
     f"generated {dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')}",
     "gap_bp = |file - nasdaq| / nasdaq * 1e4 ; open-basis = |(fo/no)/(fc/nc) - 1| * 1e4",
     "nasdaq.com reference: edge/data/nasdaq/<SYM>-1d-nasdaq.csv, fetched 2026-10-09 (2016-10-10..2026-10-08)"]
E = ["adjustment events — level shifts in the close ratio file/nasdaq (see basis_compare.py docstring)"]

gw = csv.writer(open(os.path.join(OUT, "basis-yearly-gaps.csv"), "w", newline=""))
gw.writerow(["pair", "year", "n", "open_med_bp", "open_worst_bp", "open_worst_date", "close_med_bp",
             "close_worst_bp", "close_worst_date", "openbasis_med_bp", "openbasis_worst_bp",
             "openbasis_worst_date", "open_cent_exact_pct", "close_cent_exact_pct"])
ew = csv.writer(open(os.path.join(OUT, "basis-events.csv"), "w", newline=""))
ew.writerow(["pair", "event_date", "jump_bp", "level_shift_bp", "open_vs_sameday_close_basis_bp",
             "open_vs_prior_close_basis_bp", "open_basis"])

NINE = ["DIA", "EEM", "EFA", "GLD", "IWM", "QQQ", "TLT", "XLE", "XLF"]
L.append("\n# 1. stooq files vs nasdaq.com")
for s in ["SPY"] + NINE:
    f = "SPY-1d.csv" if s == "SPY" else f"{s}-1d-long.csv"
    A = load(os.path.join(BARS, f)); N = nas(s)
    yearly_gaps(A, N, f"stooq {f} vs nasdaq {s}", L, gw)
    events(A, N, f"stooq {f} vs nasdaq {s}", E, ew)

L.append("\n# 2. Alpaca total-return daily files (adjustment=all, IEX feed) vs nasdaq.com")
for s in NINE:
    A = load(os.path.join(BARS, f"{s}-1d.csv")); N = nas(s)
    yearly_gaps(A, N, f"alpaca {s}-1d.csv vs nasdaq {s}", L, gw)
    events(A, N, f"alpaca {s}-1d.csv vs nasdaq {s}", E, ew)

L.append("\n# 3. SPY minute-aggregated (Alpaca IEX) and on-disk nasdaq file vs fresh nasdaq.com")
for f in ["SPY-1d-agg.csv", "SPY-1d-raw.csv"]:
    A = load(os.path.join(BARS, f)); N = nas("SPY")
    yearly_gaps(A, N, f"bars/{f} vs nasdaq SPY (fresh)", L, gw)
    events(A, N, f"bars/{f} vs nasdaq SPY (fresh)", E, ew)

# 3b. exact identity of the on-disk nasdaq file and the fresh pull
A = load(os.path.join(BARS, "SPY-1d-raw.csv")); N = nas("SPY")
common = sorted(set(A) & set(N))
diff = [d for d in common if any(abs(a - b) > 1e-9 for a, b in zip(A[d], N[d]))]
L.append(f"\n## identity: bars/SPY-1d-raw.csv vs fresh nasdaq SPY on {len(common)} common dates: "
         f"{len(diff)} date(s) differ in any of O/H/L/C/V"
         + (": " + ", ".join(diff[:20]) if diff else ""))
for d in diff[:20]:
    L.append(f"   {d}: on disk {A[d]}  fresh {N[d]}")

open(os.path.join(OUT, "basis-yearly-gaps.txt"), "w").write("\n".join(L) + "\n")
open(os.path.join(OUT, "basis-events.txt"), "w").write("\n".join(E) + "\n")
print("\n".join(L))
print("\n".join(E))
