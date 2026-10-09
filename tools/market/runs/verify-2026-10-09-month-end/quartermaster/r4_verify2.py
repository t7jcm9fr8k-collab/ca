#!/usr/bin/env python3
"""
r4_verify2.py — Quartermaster round 4, second pass (post-run verification; the trial is spent,
conditioning on S1 is allowed for verification only). Same rebuild as r4_verify.py (edgelab's own
functions, primary cell: 2 bp/side, cash 1.5%, spread 1.5%, calendar accrual, closes only), then:
  (d) cycle #3 (2020-02/03): per-session step of the stooq/official close ratio;
  (e) placeholder patterns (repeated close, O/H/L equal to C, H = L) in the top-5 cycles and across S1;
  (f) single-close sensitivity: +1% on ONE close, in memory only, at the entry, an inside, the exit and
      an outside close of cycle #1; the window decisions do not read prices, so they are unchanged;
  (g) peer scan: SPY close-to-close vs DIA, IWM, QQQ (stooq long files) over S1, OLS residuals, and a
      spike-and-reversal score at each close (an isolated bad close shows as +e then -e);
  (h) S1's gap legs (closures and the data hole): e, d, and the timing book without them;
  (i) QQQ veto book at the six 2 bp pairs, with and without its three gap legs, z_used exactly as
      edgelab.timing_book computes it (block 10, 5,000 draws, seed 20261009).
No file under tools/market is written. Usage: python3 -I -B r4_verify2.py <tools/market> <nasdaq dir> <out>
"""
import csv, dataclasses, datetime as dt, math, os, sys
TOOLS, NAS, OUT = sys.argv[1:4]
sys.path.insert(0, TOOLS)
os.chdir(TOOLS)
import edgelab as E

SEED, DRAWS, BLOCK = 20261009, 5000, 10
PAIRS = [(0.015, 0.015), (0.015, 0.04), (0.0, 0.015), (0.0, 0.04), (0.03, 0.015), (0.03, 0.04)]
L = []


def out(s=""):
    L.append(s)
    print(s, flush=True)


def setup(path, trt, start_close, end, dist_path=None):
    series = E.load(path, None, "stooq", True, trt)
    r0 = E._as_factory("month_end_overlay")()
    bars = list(series.bars)
    dates_all = [b.ts.date() for b in bars]
    cal = E.Calendar(dates_all[0], dates_all[-1])
    s0, last = E._window(dates_all, r0.warmup, None, end, start_close)
    w_on, w_id, _ = E.decide_all(series, r0, cal, s0, last, 1)
    levels = E.interleave(w_on, w_id)
    dates = dates_all[s0 + 1:last + 1]
    applied = None
    if dist_path:
        applied = E.place_distributions(E.load_distributions(dist_path), series, dates[0], dates[-1])["applied"]
    cycles, _ = E.session_cycles(dates, cal, r0.anchor or (lambda f: f.is_month_end))
    e = [(levels[2 * j] + levels[2 * j + 1]) / 2 for j in range(len(dates))]
    return dict(bars=bars, s0=s0, last=last, dates=dates, levels=levels, applied=applied, cal=cal,
                cycles=cycles, e=e, idx={b.ts.date(): i for i, b in enumerate(bars)})


def books(S, bars=None, cash=0.015, spread=0.015, cost=0.0002):
    bars = bars or S["bars"]
    ML = E.margin_legs(bars, S["s0"], S["last"], E.CashRate(rate=cash), spread, S["cal"], "calendar",
                       S["applied"], True)
    ch = E.levels_to_changes(S["levels"])
    trade = [leg for leg, e, f in ch if leg > 0]
    p_hat = sum(S["levels"]) / len(S["levels"])
    rp = E.margin_walk(ch, ML, cost, detail=True)
    ap = E.margin_walk(E.constant_changes(p_hat, trade), ML, cost, detail=True)
    r = E.session_returns(rp["marks"][2::2])
    a = E.session_returns(ap["marks"][2::2])
    d = [math.log1p(x) - math.log1p(y) for x, y in zip(r, a)]
    return r, a, d, ML


def tb(r, a):
    return E.timing_book(r, a, None, 100, BLOCK, DRAWS, SEED)["log"]


# ------------------------------------------------------------------ S1 primary, validated
S = setup("bars/SPY-1d.csv", "2025-03-21", dt.date(2005, 3, 24), dt.date(2026, 8, 25),
          "prereg-2026-10-09/spy-distributions-2025-2026.csv")
r, a, d, ML = books(S)
dates, cyc, e = S["dates"], S["cycles"], S["e"]
t_full = tb(r, a)
out(f"S1 primary rebuilt: {len(dates)} sessions; sum d {sum(d):.5f} (run 0.70647); z_boot {t_full['z_boot']:.4f} "
    f"(run 1.8116), z_analytic {t_full['z_analytic']:.4f} (run 1.6879), z_used {t_full['z_used']:.4f} (run 1.6879)")
h1, h2 = sum(d[:2694]), sum(d[2694:])
out(f"halves (cut after session 2694, {dates[2693]}): sum d first {h1:+.5f}, second {h2:+.5f}")
per = [sum(d[j0:j1]) for j0, j1 in cyc]
order = sorted(range(len(cyc)), key=lambda k: -per[k])[:5]
bars, idx = S["bars"], S["idx"]

# boundary closes of the top-5 cycles: entry = the close before the first 2x session, exit = the last 2x session
bounds = []
for k in order:
    j0, j1 = cyc[k]
    two = [j for j in range(j0, j1) if e[j] > 1.5]
    entry = bars[idx[dates[two[0]]] - 1].ts.date()
    bounds.append((k, entry, dates[two[-1]]))

# ------------------------------------------------------------------ (d) cycle #3 official ratio steps
nas = {row[0]: [float(x) for x in row[1:6]] for row in list(csv.reader(open(os.path.join(NAS, "SPY-1d-nasdaq.csv"))))[1:]}
k3 = order[2]
j0, j1 = cyc[k3]
steps = []
for i in range(idx[dates[j0]] - 1, idx[dates[j1 - 1]] + 1):
    dd, pp = bars[i].ts.date(), bars[i - 1].ts.date()
    if dd.isoformat() in nas and pp.isoformat() in nas:
        q = (bars[i].close / nas[dd.isoformat()][3]) / (bars[i - 1].close / nas[pp.isoformat()][3]) - 1
        steps.append((dd, q * 1e4))
ex = [s for s in steps if s[0] == dt.date(2020, 3, 20)]
rest = [s for s in steps if s[0] != dt.date(2020, 3, 20)]
w = max(rest, key=lambda s: abs(s[1]))
out(f"\n(d) cycle #3 {dates[j0]}..{dates[j1-1]}: stooq/official close-ratio step per session ({len(steps)} sessions): "
    f"2020-03-20 {ex[0][1]:+.2f} bp (the ex-date adjustment); largest other |step| {abs(w[1]):.2f} bp ({w[0]})")

# ------------------------------------------------------------------ (e) placeholder patterns
def patterns(i):
    b, p = bars[i], bars[i - 1]
    f = []
    if b.close == p.close:
        f.append("close = previous close")
    if b.high == b.low:
        f.append("H = L")
    if b.open == b.low == b.close or b.open == b.high == b.close:
        f.append("O = C = H or L")
    if b.volume == p.volume:
        f.append("volume = previous")
    return f

top_hits = []
for k in order:
    j0, j1 = cyc[k]
    for i in range(idx[dates[j0]] - 1, idx[dates[j1 - 1]] + 1):
        for x in patterns(i):
            top_hits.append(f"{bars[i].ts.date()} {x}")
span_hits = {}
for i in range(S["s0"] + 1, S["last"] + 1):
    for x in patterns(i):
        span_hits.setdefault(x, []).append(bars[i].ts.date())
out(f"\n(e) placeholder patterns in the top-5 cycles (entry close to cycle end): {', '.join(top_hits) or 'none'}")
def eio(q):
    jq = dates.index(q)
    return f"e={e[jq]:.0f}/{e[jq + 1] if jq + 1 < len(e) else float('nan'):.0f}"
for x, v in sorted(span_hits.items()):
    out(f"    whole S1 span, '{x}': {len(v)} bar(s): " + ", ".join(f"{q} {eio(q)}" for q in v))
rep = span_hits.get("close = previous close", [])
at_trade = [q for q in rep if eio(q)[2] != eio(q)[4]]
post = [q for q in rep if q >= dt.date(2016, 10, 10)]
def nas_rep(q):
    i = idx[q]; pq = bars[i - 1].ts.date().isoformat()
    return q.isoformat() in nas and pq in nas and nas[q.isoformat()][3] == nas[pq][3]
out(f"    repeated closes at a trade close (exposure changes there): {len(at_trade)}; after 2016-10-10: "
    + (", ".join(f"{q} official close also repeats: {nas_rep(q)}" for q in post) or "none"))

# ------------------------------------------------------------------ (f) single-close sensitivity
k1 = order[0]
j0, j1 = cyc[k1]
two = [j for j in range(j0, j1) if e[j] > 1.5]
probe = [("entry close (T-4)", bars[idx[dates[two[0]]] - 1].ts.date()),
         ("inside close (T)", next(dates[j] for j in two if dates[j] == dt.date(2008, 10, 31))),
         ("exit close (T+3)", dates[two[-1]]),
         ("outside close", dt.date(2008, 11, 14))]
out(f"\n(f) one close raised 1% (in memory), cycle #1; the rule's exposures do not read prices")
for name, q in probe:
    b2 = list(bars)
    i = idx[q]
    b2[i] = dataclasses.replace(bars[i], close=bars[i].close * 1.01)
    _, _, d2, _ = books(S, b2)
    jq = dates.index(q)
    out(f"    {name} {q} (e {e[jq]:.0f} into it, {e[jq + 1]:.0f} after it): change in sum d {sum(d2) - sum(d):+.6f}")

# ------------------------------------------------------------------ (g) peer residual scan
def closes(path):
    rows = list(csv.DictReader(open(path)))
    return {row["Date"]: float(row["Close"]) for row in rows}

peers = {p: closes(f"bars/{p}-1d-long.csv") for p in ("DIA", "IWM", "QQQ")}
X, Y, J = [], [], []
for j, q in enumerate(dates):
    i = idx[q]
    pq, qs = bars[i - 1].ts.date().isoformat(), q.isoformat()
    if all(pq in peers[p] and qs in peers[p] for p in peers):
        X.append([1.0] + [peers[p][qs] / peers[p][pq] - 1 for p in peers])
        Y.append(bars[i].close / bars[i - 1].close - 1)
        J.append(j)
# OLS by the normal equations (4x4, Gauss-Jordan)
k_ = len(X[0])
A = [[sum(x[u] * x[v] for x in X) for v in range(k_)] + [sum(x[u] * y for x, y in zip(X, Y))] for u in range(k_)]
for c in range(k_):
    piv = max(range(c, k_), key=lambda rr: abs(A[rr][c]))
    A[c], A[piv] = A[piv], A[c]
    for rr in range(k_):
        if rr != c:
            f = A[rr][c] / A[c][c]
            A[rr] = [u - f * v for u, v in zip(A[rr], A[c])]
beta = [A[c][k_] / A[c][c] for c in range(k_)]
res = {J[n]: Y[n] - sum(b * x for b, x in zip(beta, X[n])) for n in range(len(J))}
sd = math.sqrt(sum(v * v for v in res.values()) / (len(res) - k_))
def spike(j):          # an isolated error in the close of dates[j] shows as res[j] = +x, res[j+1] = -x
    if j in res and j + 1 in res and res[j] * res[j + 1] < 0:
        return min(abs(res[j]), abs(res[j + 1]))
    return 0.0
sp = sorted(((spike(j), dates[j]) for j in range(len(dates) - 1)), reverse=True)
out(f"\n(g) peers: SPY ~ DIA + IWM + QQQ over {len(J)} common sessions of S1; betas {', '.join(f'{b:+.3f}' for b in beta[1:])}; "
    f"residual SD {sd:.3%}; largest |residual| {max(abs(v) for v in res.values()):.3%} "
    f"({dates[max(res, key=lambda j: abs(res[j]))]})")
out("    largest spike-and-reversal scores over S1 (min(|res_t|,|res_t+1|), opposite signs): "
    + "; ".join(f"{q} {s:.3%}" for s, q in sp[:5]))
out("    top-5 cycles' boundary closes (entry / exit): " + "; ".join(
    f"#{n} {en} {spike(dates.index(en)) if en in dates else 0.0:.3%} / {ex_} {spike(dates.index(ex_)):.3%}"
    for n, (k, en, ex_) in enumerate(bounds, 1)))

# every trade close of S1: entry (exposure 1 into it, 2 after) and exit (2 into it, 1 after)
def sspike(j):
    if j in res and j + 1 in res and res[j] * res[j + 1] < 0:
        return math.copysign(min(abs(res[j]), abs(res[j + 1])), res[j])
    return 0.0
tc = [(j, "entry" if e[j] < 1.5 else "exit") for j in range(len(dates) - 1) if (e[j] < 1.5) != (e[j + 1] < 1.5)]
worst = max(tc, key=lambda t: abs(sspike(t[0])))
impl = sum((sspike(j) if kind == "entry" else -sspike(j)) for j, kind in tc)
impl2 = sum((sspike(j) if kind == "entry" else -sspike(j)) for j, kind in tc if j >= 2694)
out(f"    all {len(tc)} trade closes in S1 ({sum(1 for t in tc if t[1] == 'entry')} entry, "
    f"{sum(1 for t in tc if t[1] == 'exit')} exit): largest |spike| {abs(sspike(worst[0])):.3%} ({dates[worst[0]]}, "
    f"{worst[1]}); count above 0.5%: {sum(1 for j, _ in tc if abs(sspike(j)) > 0.005)}; "
    f"sum d if EVERY reversal at a trade close were a bad close and were removed: {impl:+.4f} "
    f"(second half alone {impl2:+.4f})")

# ------------------------------------------------------------------ (h) S1 gap legs
gaps = [j for j in range(len(dates)) if ML.gap[j]]
out(f"\n(h) S1 gap legs (a scheduled session with no bar inside the leg): {len(gaps)}")
for j in gaps:
    out(f"    {ML.prev_dates[j]}->{dates[j]}: e={e[j]:.0f}, d {d[j]:+.5f}")
keep = [j for j in range(len(dates)) if j not in set(gaps)]
t_ng = tb([r[j] for j in keep], [a[j] for j in keep])
out(f"    without them: sum d {sum(d[j] for j in keep):+.5f}; z_used {t_ng['z_used']:+.4f} (boot {t_ng['z_boot']:+.4f}, "
    f"analytic {t_ng['z_analytic']:+.4f}); with them z_used {t_full['z_used']:+.4f}")

# ------------------------------------------------------------------ (i) QQQ veto at the six 2 bp pairs
Q = setup("bars/QQQ-1d-long.csv", "2025-03-24", dt.date(1999, 3, 25), dt.date(2005, 2, 22), None)
out(f"\n(i) QQQ veto book, {len(Q['dates'])} sessions {Q['dates'][0]}..{Q['dates'][-1]}; z_used = min(boot, analytic)")
for cash, spread in PAIRS:
    rq, aq, dq, MQ = books(Q, cash=cash, spread=spread)
    g = [j for j in range(len(dq)) if MQ.gap[j]]
    full = tb(rq, aq)
    kq = [j for j in range(len(dq)) if j not in set(g)]
    ng = tb([rq[j] for j in kq], [aq[j] for j in kq])
    out(f"    cash {cash:.2%} spread {spread:.2%}: z_used {full['z_used']:+.4f} (boot {full['z_boot']:+.4f}); without the "
        f"{len(g)} gap legs ({', '.join(str(MQ.dates[j]) for j in g)}) z_used {ng['z_used']:+.4f} "
        f"(boot {ng['z_boot']:+.4f}, analytic {ng['z_analytic']:+.4f}); veto needs < -1")

open(OUT, "w").write("\n".join(L) + "\n")
