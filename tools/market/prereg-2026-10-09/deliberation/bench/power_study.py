"""
Size and power of edgelab's placebo nulls — SYNTHETIC DATA ONLY. No market data
is read. Bars are generated on the real NYSE calendar 2005-02-25 -> 2026-09-02
with i.i.d. normal legs whose means/vols come from EVIDENCE §C's published SPY
figures (overnight +3.1 bp, Sharpe 0.69 -> sd ~71 bp; intraday +1.5 bp, Sharpe
0.25 -> sd ~95 bp). A known effect of `delta` bp is injected into the overnight
leg INTO the first scheduled session of each month, and a synthetic-only rule
holds exactly those legs. Measured: how often p < 0.05 (size at delta = 0,
power above it), for the shift and the blocks placebo, CAGR and Sharpe.
The rule here is an instrument probe; it is never run on market data.
Usage: python3 -B power_study.py OUT SEED_BASE REPS DRAWS DELTA_BP [DELTA_BP ...]
"""
import datetime as dt, json, math, os, random, sys, time
sys.path.insert(0, "/home/user/ca/tools/market")
import bars as B, barqc, edgelab as E

SESS = barqc.sessions_between(dt.date(2005, 2, 25), dt.date(2026, 9, 2))
CAL = E.Calendar(SESS[0], SESS[-1])
MU_ON, SD_ON, MU_ID, SD_ID = 3.1e-4, 3.1e-4 * math.sqrt(252) / 0.69, 1.5e-4, 1.5e-4 * math.sqrt(252) / 0.25
FIRST = {d for d in SESS if CAL.facts(d).month_ordinal == 1}


def series(seed, delta):
    rng = random.Random(seed)
    px, out = 100.0, []
    for i, d in enumerate(SESS):
        o = px if i == 0 else px * (1 + rng.gauss(MU_ON, SD_ON) + (delta if d in FIRST else 0.0))
        c = o * (1 + rng.gauss(MU_ID, SD_ID))
        out.append(B.Bar(dt.datetime(d.year, d.month, d.day, tzinfo=B.UTC), o, max(o, c) * 1.0005,
                         min(o, c) * 0.9995, c, 1e6))
        px = c
    return B.Series("SYN", "1d", out, {"source": "synthetic", "fetched_at": "x", "adjusted": True})


def probe(v):
    # SYNTHETIC-ONLY instrument probe: overnight into the first session of a month
    return 1.0 if v.auction == "close" and v.next_cal is not None and v.next_cal.month_ordinal == 1 else 0.0


def main():
    out_path, base, reps, draws = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])
    deltas = [float(x) * 1e-4 for x in sys.argv[5:]]
    res = {"seed_base": base, "reps": reps, "draws": draws, "sessions": len(SESS) - 1, "events": len(FIRST),
           "sd_on_bp": SD_ON * 1e4, "sd_id_bp": SD_ID * 1e4, "cost_bps_per_side": 1.0, "by_delta": {}}
    t0 = time.time()
    for delta in deltas:
        hits = {"shift_cagr": 0, "shift_sharpe": 0, "blocks_cagr": 0, "blocks_sharpe": 0}
        ps = {k: [] for k in hits}
        for r in range(reps):
            s = series(base + r, delta)
            legs = E.build_legs(s.bars, 0, len(s.bars) - 1, E.CashRate(rate=0.0))
            w_on, w_id, _ = E.decide_all(s, E.Rule("probe", probe), CAL, 0, len(s.bars) - 1)
            years = (legs.dates[-1] - SESS[0]).days / 365.25
            for m in ("shift", "blocks"):
                p = E.placebo(w_on, w_id, legs, 1e-4, years, m, draws, seed=base + r)
                for key in ("cagr", "sharpe"):
                    ps[f"{m}_{key}"].append(p[f"p_{key}"])
                    hits[f"{m}_{key}"] += p[f"p_{key}"] < 0.05
        res["by_delta"][f"{delta * 1e4:g}bp"] = {
            "rejection_rate_p_lt_0.05": {k: v / reps for k, v in hits.items()},
            "mean_p": {k: sum(v) / len(v) for k, v in ps.items()}}
        print(f"delta {delta * 1e4:g} bp: " + ", ".join(f"{k} {v / reps:.3f}" for k, v in hits.items()),
              f"({time.time() - t0:.0f}s)", flush=True)
    se = {f"{x * 1e4:g}bp": math.sqrt(0.05 * 0.95 / reps) for x in deltas}
    res["binomial_se_at_5pct"] = math.sqrt(0.05 * 0.95 / reps)
    res["one_sided_z_of_delta"] = {f"{x * 1e4:g}bp": x / (SD_ON / math.sqrt(len(FIRST))) for x in deltas}
    open(out_path, "w").write(json.dumps(res, indent=1) + "\n")


if __name__ == "__main__":
    main()
