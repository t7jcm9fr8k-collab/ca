"""
SYNTHETIC ONLY — size and power of the three placebo designs (within-cycle,
shift, blocks) for an S1-shaped overlay, run through edgelab's own code paths
(decide_all, margin_legs, margin_walk, WithinCycle/ShiftPlacebo/BlocksPlacebo,
run_placebo). No bar file is opened.

Calendar: the real scheduled NYSE sessions (barqc.nyse_holidays) from
2005-03-01 to 2026-09-01, with the dates the real SPY file lacks removed so the
structure matches the frozen run (unscheduled closures 2007-01-02, 2012-10-29,
2012-10-30, 2018-12-05, 2025-01-09; data hole 2011-02-17). Scored from the
close of 2005-03-24 to the close of 2026-08-25. Rule: edgelab.month_window_rule
(-3, +3): 2x over T-3..T+3, 1x otherwise, MOC only. Costs 2 bp/side, cash 1.5%,
spread 1.5% (the draft's primary), calendar-day accrual.

Returns (ASSUMPTIONS, stated):
- iid:    session return ~ N(4.6 bp, 1.21%), split into an overnight and an
          intraday leg with variance shares 0.358 / 0.642 and means 3.1 / 1.5 bp.
- garch:  GARCH(1,1) on the session return, omega 2.88e-6, alpha 0.08, beta 0.90
          (unconditional sd 1.20%/day, persistence 0.98), normal innovations;
          legs split the conditional variance 0.358 / 0.642.
- regime: two-state Markov volatility, calm sd 0.85%/day, stressed sd 2.6%/day,
          P(stay calm) 0.995, P(stay stressed) 0.98 (stationary stressed share
          0.2), normal innovations; same leg split.
Effect: delta bp PER WINDOW added to the mean of the 7 sessions T-3..T+3
(delta/7 per session, on the intraday leg). delta = 0 is the size case.

Usage: size_study.py GEN DELTA REP0 REP1 DRAWS OUT.jsonl [METHOD,METHOD...]
(methods: within_cycle, within_cycle_circular, shift, blocks; default the first, third and fourth)
"""
import datetime as dt, json, math, random, sys, time
sys.path.insert(0, "/home/user/ca/tools/market")
import bars as B, barqc, edgelab as E

MISSING = {dt.date(2007, 1, 2), dt.date(2012, 10, 29), dt.date(2012, 10, 30), dt.date(2018, 12, 5),
           dt.date(2025, 1, 9), dt.date(2011, 2, 17)}
DATES = [d for d in barqc.sessions_between(dt.date(2005, 3, 1), dt.date(2026, 9, 1)) if d not in MISSING]
START, END = dt.date(2005, 3, 24), dt.date(2026, 8, 25)
S0, LAST = DATES.index(START), DATES.index(END)
TS = [dt.datetime(d.year, d.month, d.day, tzinfo=B.UTC) for d in DATES]
SH_ON, SH_ID = 0.358, 0.642
MU_ON, MU_ID = 3.1e-4, 1.5e-4


def bars_from(r_on, r_id):
    px, out = 100.0, []
    for ts, a, b in zip(TS, r_on, r_id):
        o = px * (1 + a)
        c = o * (1 + b)
        out.append(B.Bar(ts, o, max(o, c), min(o, c), c, 1e6))
        px = c
    return out


def gen_returns(kind, rng, n):
    r_on, r_id = [], []
    if kind == "iid":
        s = 1.21e-2
        for _ in range(n):
            r_on.append(rng.gauss(MU_ON, s * math.sqrt(SH_ON)))
            r_id.append(rng.gauss(MU_ID, s * math.sqrt(SH_ID)))
    elif kind == "garch":
        w, a, b = 2.88e-6, 0.08, 0.90
        h = w / (1 - a - b)
        for _ in range(n):
            s = math.sqrt(h)
            x_on, x_id = rng.gauss(0, s * math.sqrt(SH_ON)), rng.gauss(0, s * math.sqrt(SH_ID))
            r_on.append(MU_ON + x_on)
            r_id.append(MU_ID + x_id)
            e = x_on + x_id
            h = w + a * e * e + b * h
    elif kind == "regime":
        calm, stress, p_cc, p_ss = 0.85e-2, 2.6e-2, 0.995, 0.98
        st = 0 if rng.random() < 0.8 else 1
        for _ in range(n):
            s = calm if st == 0 else stress
            r_on.append(rng.gauss(MU_ON, s * math.sqrt(SH_ON)))
            r_id.append(rng.gauss(MU_ID, s * math.sqrt(SH_ID)))
            if st == 0:
                st = 0 if rng.random() < p_cc else 1
            else:
                st = 1 if rng.random() < p_ss else 0
    else:
        raise ValueError(kind)
    return r_on, r_id


# ----- the rule, its levels and cycles: computed once (they depend on dates only)
_r_on0, _r_id0 = gen_returns("iid", random.Random(0), len(DATES))
SER0 = B.Series("SYN", "1d", bars_from(_r_on0, _r_id0),
                {"source": "synthetic", "fetched_at": "2026-10-09T00:00:00+00:00", "adjusted": True})
CAL = E.Calendar(DATES[0], DATES[-1])
FAC = E.month_window_rule(-3, 3)
RULE = FAC()
W_ON, W_ID, _log = E.decide_all(SER0, RULE, CAL, S0, LAST, 1)
LEVELS = E.interleave(W_ON, W_ID)
SC = DATES[S0 + 1:LAST + 1]
CYCLES, ANCHORS = E.session_cycles(SC, CAL, RULE.anchor)
CUT, SPLIT = E.split_halves(SC, START, "session")
SPANS = E.crisis_spans(SC, E.DEFAULT_CRISES)
PROBES = E.ProbeSet(SC, START, CUT, SPANS)
CHANGES = E.levels_to_changes(LEVELS)
IN_W = [W_ON[j] > 1.5 for j in range(len(SC))]           # session j held at 2x (MOC-only: on == id)
assert all(abs(a - b) < 1e-12 for a, b in zip(W_ON, W_ID))
WC = E.WithinCycle(LEVELS, CYCLES, 1.0)
SH = E.ShiftPlacebo(LEVELS)
BL = E.BlocksPlacebo(LEVELS, 1.0)
WCC = E.WithinCycle(LEVELS, CYCLES, 1.0, wrap=True)
GENS = {"within_cycle": (WC.draw, WC.observed), "within_cycle_circular": (WCC.draw, WCC.observed),
        "shift": (SH.draw, 0), "blocks": (BL.draw, tuple(CHANGES))}


def one(kind, delta_bp, rep, draws, methods=("within_cycle", "shift", "blocks")):
    rng = random.Random(f"size/{kind}/{delta_bp}/{rep}")
    n = len(DATES)
    r_on, r_id = gen_returns(kind, rng, n)
    add = delta_bp / 7.0 * 1e-4
    for j, w in enumerate(IN_W):
        if w:
            r_id[S0 + 1 + j] += add
    bars = bars_from(r_on, r_id)
    ML = E.margin_legs(bars, S0, LAST, E.CashRate(rate=0.015), 0.015, CAL, "calendar")
    out = {"gen": kind, "delta_bp": delta_bp, "rep": rep}
    for m in methods:
        g, okey = GENS[m]
        p = E.run_placebo(m, g, CHANGES, okey, ML, 2e-4, PROBES, draws, 1000003 * rep + 17)
        out[m] = {"p": p["p_cagr"], "halves": p["beats_median_each_half"], "obs": p["observed_cagr"],
                  "med": p["null_cagr_median"], "z": p["z_cagr"]}
    return out


if __name__ == "__main__":
    kind, delta, r0, r1, draws, path = (sys.argv[1], float(sys.argv[2]), int(sys.argv[3]),
                                        int(sys.argv[4]), int(sys.argv[5]), sys.argv[6])
    methods = tuple(sys.argv[7].split(",")) if len(sys.argv) > 7 else ("within_cycle", "shift", "blocks")
    t0 = time.time()
    with open(path, "a") as f:
        for rep in range(r0, r1):
            f.write(json.dumps(one(kind, delta, rep, draws, methods)) + "\n")
            f.flush()
    print(f"{kind} delta={delta:g} reps {r0}..{r1} draws {draws}: {time.time() - t0:.1f}s", file=sys.stderr)
