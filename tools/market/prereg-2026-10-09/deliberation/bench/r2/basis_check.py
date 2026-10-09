"""
Round-2 basis check (Bench): stooq files against nasdaq.com official prices.
PRICE RATIOS ONLY — no return, no window, no rule. For each common date:
  f_close = stooq_close / nasdaq_close,  f_open = stooq_open / nasdaq_open.
A back-adjusted series has f < 1 that steps up toward 1 at each ex-date; an
unadjusted one has f == 1. An adjustment step is a day where ln f_close moves
by > 4 bp AND the 5-session level after differs from the 5-session level
before by > 4 bp (so a one-day vendor spike is not a step). At each step the
open is 'post' if it already sits on the new close basis (the dividend is
credited to that day's overnight leg) and 'pre' if on the old one.
Usage (from tools/market): python3 -B basis_check.py OUT SYMBOL [SYMBOL ...]
"""
import json, math, os, statistics, sys
sys.path.insert(0, os.getcwd())
import bars as B

S = "/tmp/claude-0/-home-user-ca/2758dbcb-e96c-587b-81c2-e59b0c402304/scratchpad"
EXCLUDE = {"2026-04-20"}          # nasdaq placeholder bars (O=H=L=C, volume 0), per r1-quartermaster §1


def stooq_path(sym):
    return "bars/SPY-1d.csv" if sym == "SPY" else f"bars/{sym}-1d-long.csv"


def run(sym):
    st = B.load_csv(stooq_path(sym), sym, "1d", "stooq")
    nq = B.load_csv(f"{S}/edge/data/nasdaq/{sym}-1d-nasdaq.csv", sym, "1d", "nasdaq")
    nmap = {b.ts.date(): b for b in nq.bars}
    rows = []
    for b in st.bars:
        d = b.ts.date()
        n = nmap.get(d)
        if n is None or d.isoformat() in EXCLUDE:
            continue
        rows.append((d, math.log(b.close / n.close), math.log(b.open / n.open)))
    lc = [r[1] for r in rows]
    steps = []
    for i in range(5, len(rows) - 5):
        jump = lc[i] - lc[i - 1]
        if abs(jump) > 4e-4:
            before = statistics.median(lc[i - 5:i])
            after = statistics.median(lc[i:i + 5])
            if abs(after - before) > 4e-4:
                lo = rows[i][2]
                place = "post" if abs(lo - lc[i]) < abs(lo - lc[i - 1]) else "pre"
                steps.append({"date": rows[i][0].isoformat(), "step_bp": 1e4 * jump, "open": place,
                              "open_minus_newclose_bp": 1e4 * (lo - lc[i]),
                              "open_minus_oldclose_bp": 1e4 * (lo - lc[i - 1])})
    last = steps[-1]["date"] if steps else None
    after_last = [abs(r[1]) for r in rows if last and r[0].isoformat() > last]
    by_year = {}
    for d, c, o in rows:
        by_year.setdefault(d.year, []).append(c)
    ob = [abs(o - c) for d, c, o in rows]
    return {"symbol": sym, "common_dates": len(rows), "first": rows[0][0].isoformat(),
            "last": rows[-1][0].isoformat(), "steps": len(steps),
            "post": sum(1 for s in steps if s["open"] == "post"),
            "pre": sum(1 for s in steps if s["open"] == "pre"),
            "first_step": steps[0]["date"] if steps else None, "last_step": last,
            "median_abs_close_gap_after_last_step_bp": 1e4 * statistics.median(after_last) if after_last else None,
            "max_abs_close_gap_after_last_step_bp": 1e4 * max(after_last) if after_last else None,
            "median_close_gap_bp_by_year": {y: round(1e4 * statistics.median(v), 2) for y, v in sorted(by_year.items())},
            "median_abs_open_basis_bp": 1e4 * statistics.median(ob),
            "share_open_basis_over_5bp": sum(1 for x in ob if x > 5e-4) / len(ob),
            "steps_detail": steps}


def main():
    out, syms = sys.argv[1], sys.argv[2:]
    res = [run(s) for s in syms]
    L = ["stooq vs nasdaq official — price ratios only (no returns, no rule). Steps = persistent >4 bp moves in ln(stooq_close/nasdaq_close).",
         f"{'sym':<5}{'common':>7}  {'span':<23}{'steps':>6}{'post':>5}{'pre':>4}  {'first step':<11} {'last step':<11} {'|gap| after last (med/max bp)':>30}  {'open basis med bp':>17}"]
    for r in res:
        L.append(f"{r['symbol']:<5}{r['common_dates']:>7}  {r['first']}→{r['last']:<12}{r['steps']:>6}{r['post']:>5}{r['pre']:>4}  "
                 f"{str(r['first_step']):<11} {str(r['last_step']):<11} "
                 f"{(r['median_abs_close_gap_after_last_step_bp'] or 0):>14.2f} / {(r['max_abs_close_gap_after_last_step_bp'] or 0):>8.2f}"
                 f"  {r['median_abs_open_basis_bp']:>17.3f}")
    L.append("")
    L.append("median close gap by year, bp (stooq/nasdaq − 1; negative = stooq back-adjusted below the official price):")
    for r in res:
        L.append(f"  {r['symbol']:<4} " + "  ".join(f"{y}:{v:+.1f}" for y, v in r["median_close_gap_bp_by_year"].items()))
    text = "\n".join(L)
    print(text)
    open(out, "w").write(text + "\n\n" + json.dumps(res, indent=1) + "\n")


if __name__ == "__main__":
    main()
