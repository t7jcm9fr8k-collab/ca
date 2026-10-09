#!/usr/bin/env python3
"""
tlt_dividends.py — Quartermaster round 2. TLT's official distribution history
(nasdaq.com dividends endpoint, fetched 2026-10-09T05:30:19Z through fetch.py's
_get) placed on the scheduled NYSE calendar relative to month-end T, and
cross-checked against the stooq adjustment steps located in round 1.

Outputs: the CSV of distributions with calendar positions, and a report:
  - how many ex-dates fall inside S2's window (sessions T-2, T-1, T: the
    returns close(T-3) -> close(T)), and inside [T-3, T+3]
  - stooq-located events (2016-10..2026-04-01) vs official ex-dates: date
    agreement and step size vs D / close(t-1)
  - the distributions after stooq's last adjustment (2026-04-01): the tail
No return is computed; no rule, window or event conditions any price statistic.
Run: python3 -I -B tlt_dividends.py <tools/market> <TLT-dividends.json> <basis-events.csv> <TLT nasdaq csv> <out csv> <out txt>
"""
import csv, datetime as dt, json, sys
TOOLS, JS, EV, NAS, OUTCSV, OUTTXT = sys.argv[1:7]
sys.path.insert(0, TOOLS)
import barqc

SCHED = barqc.sessions_between(dt.date(2002, 1, 1), dt.date(2027, 1, 31))
idx = {d: i for i, d in enumerate(SCHED)}
last = {}
for d in SCHED:
    last[(d.year, d.month)] = d
Ts = sorted(last.values())


def position(d):
    """(k_before, k_after): sessions to this month's T, and since the previous T."""
    i = idx[d]
    kb = idx[last[(d.year, d.month)]] - i
    prevT = [t for t in Ts if t < d][-1]
    return kb, i - idx[prevT]


rows = json.load(open(JS))["data"]["dividends"]["rows"]
dist = []
for r in rows:
    d = dt.datetime.strptime(r["exOrEffDate"], "%m/%d/%Y").date()
    amt = float(r["amount"].replace("$", "").replace(",", ""))
    dist.append((d, amt, r["type"], r["recordDate"], r["paymentDate"]))
dist.sort()
nas = {r[0]: float(r[4]) for r in list(csv.reader(open(NAS)))[1:]}
nd = sorted(nas)
prevclose = {b: nas[a] for a, b in zip(nd, nd[1:])}

L = [f"TLT official distributions (nasdaq.com dividends endpoint): {len(dist)} rows, {dist[0][0]}..{dist[-1][0]}"]
with open(OUTCSV, "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["ex_date", "weekday", "amount_usd", "type", "record_date", "payment_date", "scheduled_session",
                "position_vs_T", "in_S2_window_T-2..T", "in_[T-3,T+3]", "D_over_prev_close_bp(nasdaq, 2016-10+)"])
    nonsess, inS2, inTOM, pos_hist = [], [], [], {}
    for d, amt, typ, rec, pay in dist:
        sess = d in idx and barqc.is_session_day(d)
        if not sess:
            nonsess.append(d)
            w.writerow([d, d.strftime("%a"), amt, typ, rec, pay, 0, "", "", "", ""])
            continue
        kb, ka = position(d)
        lab = f"T+{ka}" if ka <= 5 else f"T-{kb}"
        pos_hist[lab] = pos_hist.get(lab, 0) + 1
        s2 = kb <= 2
        tom = kb <= 3 or ka <= 3
        if s2:
            inS2.append(d)
        if tom:
            inTOM.append(d)
        dp = f"{amt / prevclose[d.isoformat()] * 1e4:.2f}" if d.isoformat() in prevclose else ""
        w.writerow([d, d.strftime("%a"), amt, typ, rec, pay, 1, lab, int(s2), int(tom), dp])

span = [x for x in dist if dt.date(2005, 2, 25) <= x[0] <= dt.date(2026, 9, 4)]
L.append(f"inside the stooq TLT span 2005-02-25..2026-09-04: {len(span)} distributions")
L.append(f"ex-dates that are not scheduled NYSE sessions: {nonsess or 'none'}")
L.append(f"position histogram (T+k for k<=5 after a month-end, else T-k): {dict(sorted(pos_hist.items(), key=lambda kv: (kv[0][1], int(kv[0][2:]))))}")
L.append(f"ex-dates inside S2's window (sessions T-2..T, i.e. returns close(T-3)->close(T)): {len(inS2)} {[str(d) for d in inS2]}")
L.append(f"ex-dates inside [T-3, T+3]: {len(inTOM)} (expected: the first-session-of-month ones)")

# cross-check with stooq-located events
ev = {r["event_date"]: float(r["jump_bp"]) for r in csv.DictReader(open(EV)) if r["pair"].startswith("stooq TLT")}
off = {x[0].isoformat(): x[1] for x in dist}
match = [d for d in ev if d in off]
miss_in_official = [d for d in ev if d not in off]
win = [x[0].isoformat() for x in dist if dt.date(2016, 10, 11) <= x[0] <= dt.date(2026, 4, 1)]
miss_in_stooq = [d for d in win if d not in ev]
L.append(f"\nstooq-located TLT events 2016-10..2026-04-01: {len(ev)}; on an official ex-date: {len(match)}; "
         f"not on one: {miss_in_official}")
L.append(f"official ex-dates in the same span: {len(win)}; not located as stooq events: {miss_in_stooq}")
diffs = []
for d in sorted(match):
    if d in prevclose:
        dp = off[d] / prevclose[d] * 1e4
        diffs.append((d, ev[d], dp, ev[d] - dp))
if diffs:
    ad = sorted(abs(x[3]) for x in diffs)
    L.append(f"stooq step minus D/close(t-1): median |diff| {ad[len(ad)//2]:.2f} bp, worst {ad[-1]:.2f} bp "
             f"({max(diffs, key=lambda x: abs(x[3]))[0]})")

tail = [x for x in dist if dt.date(2026, 4, 2) <= x[0] <= dt.date(2026, 10, 9)]
L.append("\nDistributions after stooq's last TLT adjustment (2026-04-01): the tail stooq/nasdaq carry unadjusted")
for d, amt, typ, rec, pay in tail:
    kb, ka = position(d)
    dp = amt / prevclose[d.isoformat()] * 1e4 if d.isoformat() in prevclose else float("nan")
    L.append(f"   {d} {d:%a}  ${amt:.6f}  {'T+'+str(ka) if ka <= 5 else 'T-'+str(kb)}  D/close(t-1) {dp:.2f} bp")
open(OUTTXT, "w").write("\n".join(L) + "\n")
print("\n".join(L))
