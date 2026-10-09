"""
SYNTHETIC ONLY. How large is SE(ΔSR) — the paired circular-block bootstrap
standard error of (Sharpe_rule − Sharpe_benchmark) — against the single-Sharpe
SE = sqrt(1/(T−1)) that the round-1 deflated Sharpe used?

Returns: SPY-like daily r_t, mean 4.6 bp and sd 1.21% (EVIDENCE §C means;
19.2%/yr vol), i.i.d. normal, and a GARCH(1,1) variant (assumption:
omega=2.88e-6, alpha=0.08, beta=0.90: unconditional variance omega/(1-alpha-beta)
= 1.44e-4, i.e. sd 1.20%/day; persistence 0.98). The calendar
is real (NYSE scheduled sessions 2005-02-25..2026-09-01) so month-end windows
are where S1 would put them: W = sessions T-3..T+3.
Cash 1.5%/yr, financing cash + 1.0%/yr (assumptions). Daily-rebalanced books
(a demo of the statistic, not the engine).
Pairs:
  overlay (1x + 1x inside W)  vs constant (1+p)x
  long/flat (1x inside W, cash outside) vs B&H 1x
  B&H vs an independent series of the same law (uncorrelated)
"""
import datetime as dt, json, math, random, statistics, sys
sys.path.insert(0, "/home/user/ca/tools/market")
import barqc, combine

SESS = barqc.sessions_between(dt.date(2005, 2, 25), dt.date(2026, 9, 1))
months = {}
for i, d in enumerate(SESS):
    months.setdefault((d.year, d.month), []).append(i)
inW = [False] * len(SESS)
for ym, idx in months.items():
    for i in idx[-4:]:                    # T-3..T
        inW[i] = True
    nxt = (ym[0] + (ym[1] == 12), ym[1] % 12 + 1)
    for i in months.get(nxt, [])[:3]:     # T+1..T+3
        inW[i] = True
T = len(SESS)
p = sum(inW) / T
CASH, FIN = 0.015 / 252, 0.025 / 252


def gen(seed, garch):
    rng = random.Random(seed)
    out, h = [], 1.21e-2 ** 2
    for _ in range(T):
        if garch:
            z = rng.gauss(0, 1)
            r = 4.6e-4 + math.sqrt(h) * z
            h = 2.88e-6 + 0.08 * (r - 4.6e-4) ** 2 + 0.90 * h
        else:
            r = rng.gauss(4.6e-4, 1.21e-2)
        out.append(r)
    return out


def books(r, r2):
    ov = [(2 if w else 1) * x - (1 if w else 0) * FIN - CASH for x, w in zip(r, inW)]
    co = [(1 + p) * x - p * FIN - CASH for x in r]
    lf = [(x if w else CASH) - CASH for x, w in zip(r, inW)]
    bh = [x - CASH for x in r]
    ind = [x - CASH for x in r2]
    return {"overlay vs constant (1+p)x": (ov, co), "long/flat 1x vs B&H": (lf, bh),
            "B&H vs independent same-law series": (bh, ind)}


def sr(xs):
    m = sum(xs) / len(xs)
    v = sum((x - m) ** 2 for x in xs) / (len(xs) - 1)
    return m / math.sqrt(v) * math.sqrt(252)


def paired_se(a, b, B=5000, L=10, seed=7):
    rng = random.Random(seed)
    n = len(a)
    nb = -(-n // L)
    d = []
    for _ in range(B):
        sa = sb = qa = qb = 0.0
        cnt = 0
        for _k in range(nb):
            s = rng.randrange(n)
            for j in range(L):
                if cnt == n:
                    break
                i = (s + j) % n
                x, y = a[i], b[i]
                sa += x; sb += y; qa += x * x; qb += y * y
                cnt += 1
        va = (qa - sa * sa / n) / (n - 1)
        vb = (qb - sb * sb / n) / (n - 1)
        d.append((sa / n) / math.sqrt(va) * math.sqrt(252) - (sb / n) / math.sqrt(vb) * math.sqrt(252))
    return statistics.pstdev(d)


def corr(a, b):
    ma, mb = sum(a) / len(a), sum(b) / len(b)
    return sum((x - ma) * (y - mb) for x, y in zip(a, b)) / math.sqrt(
        sum((x - ma) ** 2 for x in a) * sum((y - mb) ** 2 for y in b))


def main():
    out = sys.argv[1]
    se_single = math.sqrt(1 / (T - 1)) * math.sqrt(252)
    emz = {N: combine.expected_max_sharpe(N, 1.0) for N in (41, 42, 100)}
    res = {"T": T, "p_window_share": p, "se_single_annualised": se_single, "E_max_Z": emz, "rows": []}
    L = [f"T = {T} sessions; window share p = {p:.4f}; single-Sharpe SE (round-1 form) = sqrt(1/(T-1))*sqrt(252) = {se_single:.4f}",
         f"E[max Z_N]: N=41 {emz[41]:.4f}, N=42 {emz[42]:.4f}, N=100 {emz[100]:.4f}",
         "",
         f"{'returns':<8}{'pair':<38}{'corr':>7}{'SE paired':>11}{'ratio':>8}{'dSR for DSR=.5 (N=42)':>24}{'for DSR=.8':>12}{'round-1 form .5 / .8':>24}"]
    for garch in (False, True):
        r, r2 = gen(1, garch), gen(2, garch)
        for name, (a, b) in books(r, r2).items():
            se = paired_se(a, b)
            row = {"returns": "GARCH" if garch else "iid", "pair": name, "corr": corr(a, b),
                   "se_paired": se, "ratio_to_single": se / se_single,
                   "dSR_needed_dsr50_N42": se * emz[42], "dSR_needed_dsr80_N42": se * (emz[42] + 0.8416),
                   "round1_dsr50_N42": se_single * emz[42], "round1_dsr80_N42": se_single * (emz[42] + 0.8416),
                   "observed_dSR_this_sample": sr(a) - sr(b)}
            res["rows"].append(row)
            L.append(f"{row['returns']:<8}{name:<38}{row['corr']:>7.3f}{se:>11.4f}{row['ratio_to_single']:>8.2f}"
                     f"{row['dSR_needed_dsr50_N42']:>24.3f}{row['dSR_needed_dsr80_N42']:>12.3f}"
                     f"{row['round1_dsr50_N42']:>12.3f} / {row['round1_dsr80_N42']:.3f}")
    L.append("")
    L.append("Block length 10, 5000 resamples, seed 7, circular blocks; dSR in annualised Sharpe units. 'dSR needed' = SE x E[max Z_N] (DSR=0.5) and SE x (E[max Z_N] + 0.8416) (DSR=0.8).")
    text = "\n".join(L)
    print(text)
    open(out, "w").write(text + "\n\n" + json.dumps(res, indent=1) + "\n")


if __name__ == "__main__":
    main()
