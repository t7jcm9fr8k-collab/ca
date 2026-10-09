#!/usr/bin/env python3
"""
r4_verify.py — Quartermaster round 4 (post-run verification; the trial is spent,
conditioning on S1 is allowed). Rebuilds the PRIMARY cell (2 bp/side, cash 1.5%,
spread 1.5%, calendar accrual, closes only) of the frozen run with edgelab's own
functions, validates against the printed G6 aggregates, then:
  (a) the 5 largest positive cycles of the log timing book, and a bar audit of each;
  (b) the post-2025-03-21 stretch and the five add-back dates, with and without add-back;
  (c) the QQQ veto book without the 1999-11-16 hole leg and the 2001-09 closure leg.
Run from anywhere: python3 -I -B r4_verify.py <tools/market> <nasdaq dir> <out>
"""
import csv, datetime as dt, math, os, statistics as stt, sys
TOOLS, NAS, OUT = sys.argv[1:4]
sys.path.insert(0, TOOLS)
os.chdir(TOOLS)
import edgelab as E

L = []
def out(s=""):
    L.append(s); print(s)


def build(path, trt, start_close, end, dist_path=None, cash=0.015, spread=0.015, cost=0.0002):
    series = E.load(path, None, "stooq", True, trt)
    r0 = E._as_factory("month_end_overlay")()
    bars = series.bars
    dates_all = [b.ts.date() for b in bars]
    cal = E.Calendar(dates_all[0], dates_all[-1])
    s0, last = E._window(dates_all, r0.warmup, None, end, start_close)
    w_on, w_id, _ = E.decide_all(series, r0, cal, s0, last, 1)
    levels = E.interleave(w_on, w_id)
    dates = dates_all[s0 + 1:last + 1]
    applied = None
    if dist_path:
        placed = E.place_distributions(E.load_distributions(dist_path), series, dates[0], dates[-1])
        applied = placed["applied"]
    ML = E.margin_legs(bars, s0, last, E.CashRate(rate=cash), spread, cal, "calendar", applied, True)
    ch = E.levels_to_changes(levels)
    trade = [leg for leg, e, f in ch if leg > 0]
    p_hat = sum(levels) / len(levels)
    rp = E.margin_walk(ch, ML, cost, detail=True)
    ap = E.margin_walk(E.constant_changes(p_hat, trade), ML, cost, detail=True)
    r = E.session_returns(rp["marks"][2::2])
    a = E.session_returns(ap["marks"][2::2])
    d = [math.log1p(x) - math.log1p(y) for x, y in zip(r, a)]
    cycles, _ = E.session_cycles(dates, cal, r0.anchor or (lambda f: f.is_month_end))
    e_s = [(levels[2 * j] + levels[2 * j + 1]) / 2 for j in range(len(dates))]
    return dict(series=series, bars=bars, s0=s0, dates=dates, d=d, r=r, a=a, cycles=cycles,
                p_hat=p_hat, e=e_s, ML=ML, applied=applied, cal=cal)


def top5(per):
    pos = sorted((v for v in per if v > 0), reverse=True)[:5]
    return sum(pos)


# ------------------------------------------------------------- S1, primary cell
S = build("bars/SPY-1d.csv", "2025-03-21", dt.date(2005, 3, 24), dt.date(2026, 8, 25),
          "prereg-2026-10-09/spy-distributions-2025-2026.csv")
d, dates, cyc = S["d"], S["dates"], S["cycles"]
per = [sum(d[j0:j1]) for j0, j1 in cyc]
out(f"S1 rebuilt: {len(dates)} sessions {dates[0]}..{dates[-1]}, {len(cyc)} cycles, p_hat {S['p_hat']:.6f}")
out(f"validation vs run (book_log): sum {sum(per):.5f} (run 0.70647); top-5 {top5(per):.5f} (run 0.42062); "
    f"without top-5 {sum(per) - top5(per):.5f} (run 0.28584)")
n = len(d); m = stt.mean(d); sd = stt.pstdev(d)
out(f"log timing book: mean {m*252:.4%}/yr (run +3.305%), z_iid {m/sd*math.sqrt(n):.3f} (run +1.689)")

# ------------------------------------------------------------- (a) top-5 cycles and a bar audit
nas = {r[0]: [float(x) for x in r[1:6]] for r in list(csv.reader(open(os.path.join(NAS, "SPY-1d-nasdaq.csv"))))[1:]}
bars = S["bars"]; bidx = {b.ts.date(): i for i, b in enumerate(bars)}
order = sorted(range(len(cyc)), key=lambda k: -per[k])[:5]
out("\n(a) 5 largest positive cycles of d (log timing book), primary cell")
for rank, k in enumerate(order, 1):
    j0, j1 = cyc[k]
    win = [dates[j] for j in range(j0, j1) if S["e"][j] > 1.5]
    out(f" #{rank} cycle {k}: sessions {dates[j0]}..{dates[j1-1]} ({j1-j0}); sum d {per[k]:+.4f} "
        f"({per[k]/sum(per):.1%} of total); 2x sessions {win[0]}..{win[-1]} ({len(win)})")
    issues = []
    i0 = bidx[dates[j0]] - 1                  # include the entry close
    for i in range(i0, bidx[dates[j1 - 1]] + 1):
        b = bars[i]; dd = b.ts.date()
        if not (b.high >= max(b.open, b.close) and b.low <= min(b.open, b.close) and b.low > 0):
            issues.append(f"{dd} OHLC order")
        if b.volume <= 0:
            issues.append(f"{dd} volume {b.volume}")
        if b.open == b.high == b.low == b.close:
            issues.append(f"{dd} flat bar")
        if i > i0:
            pd_ = bars[i - 1].ts.date()
            if S["cal"].between(pd_, dd):
                issues.append(f"leg {pd_}->{dd} spans a scheduled session with no bar")
        if dd >= dt.date(2016, 10, 10):
            n_ = nas.get(dd.isoformat())
            if n_ is None:
                issues.append(f"{dd} not in the official file")
            else:
                ratio = b.close / n_[3]
                issues.append(None) if False else None
        jj = [x for x in range(j0, j1)]
    # official cross-check of closes: ratio stooq/official must be flat across the cycle (factor only)
    if dates[j0] >= dt.date(2016, 10, 10):
        rs = []
        for i in range(i0, bidx[dates[j1 - 1]] + 1):
            dd = bars[i].ts.date(); n_ = nas.get(dd.isoformat())
            if n_:
                rs.append((dd, bars[i].close / n_[3]))
        worst = max(abs(x / rs[0][1] - 1) for _, x in rs) * 1e4
        out(f"     official cross-check (closes): stooq/official ratio drift across the cycle {worst:.2f} bp "
            f"(a dividend step of ~30-60 bp would show; a wrong close would show)")
        dif = [(dd, abs(bars[bidx[dd]].close - nas[dd.isoformat()][3] * rs[0][1])) for dd, _ in rs]
    else:
        out("     before 2016-10: no official file; internal checks only (barqc PASS for the whole file in r1)")
    # largest |d| sessions inside the cycle, with the market return that drove them
    big = sorted(range(j0, j1), key=lambda j: -abs(d[j]))[:3]
    out("     largest |d| sessions: " + "; ".join(
        f"{dates[j]} e={S['e'][j]:.0f} r_SPY {(bars[bidx[dates[j]]].close / bars[bidx[dates[j]] - 1].close - 1):+.2%} d {d[j]:+.4f}"
        for j in big))
    out("     bar issues: " + (", ".join(x for x in issues if x) or "none"))

# ------------------------------------------------------------- (b) price-only stretch and add-backs
cut = dt.date(2025, 3, 21)
post = [j for j, x in enumerate(dates) if x > cut]
S0 = build("bars/SPY-1d.csv", "2025-03-21", dt.date(2005, 3, 24), dt.date(2026, 8, 25), None)
d0 = S0["d"]
ab = sorted(S["applied"])
out(f"\n(b) post-cutoff stretch {dates[post[0]]}..{dates[post[-1]]}: {len(post)} sessions; "
    f"sum d with add-backs {sum(d[j] for j in post):+.5f}, without {sum(d0[j] for j in post):+.5f}; whole run "
    f"sum d {sum(d):+.5f} (without add-backs {sum(d0):+.5f})")
for x in ab:
    j = dates.index(x)
    out(f"    {x}: e={S['e'][j]:.0f}; d with add-back {d[j]:+.6f}, without {d0[j]:+.6f}; "
        f"difference {d[j]-d0[j]:+.6f} (expected about -(p_hat) x D/P = "
        f"{-(S['p_hat']-1)*S['applied'][x]/bars[bidx[x]-1].close:+.6f})")
diff = sum(d) - sum(d0)
out(f"    total effect of the five add-backs on sum d: {diff:+.5f} (log; S1 relative to A)")
cagr = lambda tot_log, yrs: math.exp(tot_log / yrs) - 1
yrs = (dates[-1] - dt.date(2005, 3, 24)).days / 365.25
out(f"    as CAGR(S1)-CAGR(A) gap: about {(cagr(sum(d), yrs) - cagr(sum(d0), yrs)) * 1e4:+.2f} bp/yr "
    f"change from the add-backs (log-sum approximation)")

# ------------------------------------------------------------- (c) QQQ veto span
Q = build("bars/QQQ-1d-long.csv", "2025-03-24", dt.date(1999, 3, 25), dt.date(2005, 2, 22), None)
dq, qd = Q["d"], Q["dates"]
def z(xs):
    m_ = stt.mean(xs); s_ = stt.pstdev(xs)
    return m_ / s_ * math.sqrt(len(xs))
out(f"\n(c) QQQ veto book rebuilt: {len(qd)} sessions {qd[0]}..{qd[-1]}, p_hat {Q['p_hat']:.4f}; "
    f"z_iid {z(dq):+.3f} (run z_used +0.018); mean d {stt.mean(dq)*252:+.3%}/yr (run +0.15%)")
special = []
for j in range(len(qd)):
    p = qd[j - 1] if j else None
    if p and Q["cal"].between(p, qd[j]):
        special.append(j)
for j in special:
    out(f"    gap leg {qd[j-1]}->{qd[j]}: e={Q['e'][j]:.0f}, r_QQQ {Q['r'][j] if False else ''}"
        f"d {dq[j]:+.5f}")
keep = [x for j, x in enumerate(dq) if j not in special]
out(f"    z without the {len(special)} gap leg(s): {z(keep):+.3f}; veto threshold -1")
open(OUT, "w").write("\n".join(L) + "\n")
