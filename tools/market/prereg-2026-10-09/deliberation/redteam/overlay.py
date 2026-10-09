#!/usr/bin/env python3
"""
Red Team, round 2 -- the overlay framing, analytically and on SYNTHETIC paths.
NO market data is read. Inputs: EVIDENCE.md:517 (5,413 sessions), :533 (B&H CAGR
~10.4%, vol 19.2%), the published window premium (Kayacetin 2026: ~10 bp/day in
the window vs ~0 outside, via r1-archivist §3.1), the brief's p = 7 sessions of ~21,
and labelled assumptions (cash, spread, costs, QQQ vol).

Books (margin model): L_t r_t - (L_t - 1)(f + s) - costs, per session.
  overlay      L_t = 1 + 1_W(t)
  constant     L   = 1 + p,  p = mean(1_W)   (daily reset, same financing)
  difference   (1_W - p)(r - f - s)  = the zero-exposure timing book
"""
import math
import random
from statistics import NormalDist

N01 = NormalDist()
GAMMA = 0.5772156649015329
SESSIONS = 5413
YEARS = SESSIONS / 252.0
SIG = 0.192                       # annual vol, EVIDENCE.md:533
SIG_D = SIG / math.sqrt(252)
MU = math.log(1.104) + SIG ** 2 / 2    # annual arithmetic mean (log-growth approx), as hurdles.py
MU_D = MU / 252
P = 7 / 21                        # window share (Etula [T-3,T+3] in ~21-session months)
DELTA_PUB = 10e-4                 # 10 bp/day window-minus-outside (Kayacetin, r1-archivist §3.1) ASSUMED as "published"
LEGS = 24                         # 2 unit-legs a month for the overlay's extra 1x

def emax_z(n):
    return (1 - GAMMA) * N01.inv_cdf(1 - 1.0 / n) + GAMMA * N01.inv_cdf(1 - 1.0 / (n * math.e))

def line(s=""):
    print(s)

def stats(h, c_bp=1.0, f=0.015, s=0.01, N=40, k=1):
    d = DELTA_PUB * h
    mu_w = MU_D + (1 - P) * d          # window-day mean (overall mean held at MU_D)
    cost = LEGS * c_bp / 1e4
    V = P * (1 - P) * 252 * d          # timing value, arithmetic, per year
    D = P * (1 - P) * SIG ** 2 / 2     # extra variance drag of concentrating the leverage
    m = V - D - cost                   # overlay minus constant leverage, log growth per year
    te = math.sqrt(P * (1 - P)) * SIG  # tracking error of the timing book
    t = m * math.sqrt(YEARS) / te
    # Sharpe (excess of cash f) of both books
    E_ov = MU + 252 * P * mu_w - P * (f + s) - cost - f
    s_ov = SIG * math.sqrt(1 + 3 * P)
    E_cl = (1 + P) * MU - P * (f + s) - f
    s_cl = SIG * (1 + P)
    sr_ov, sr_cl = E_ov / s_ov, E_cl / s_cl
    rho = (1 + P) / math.sqrt(1 + 3 * P)
    # Jobson-Korkie/Memmel variance of a Sharpe difference, PER SESSION, then annualised.
    # (Round-2 correction: the r2 draft applied (1 + SR^2/2) to ANNUAL Sharpes, which
    # overstates the SE by ~11% with daily data; r2-archivist's 0.073 is the right size.)
    a1, a2 = sr_ov / math.sqrt(252), sr_cl / math.sqrt(252)
    var_d = (2 * (1 - rho) + 0.5 * (a1 ** 2 + a2 ** 2 - 2 * a1 * a2 * rho ** 2)) / SESSIONS
    se_pair = math.sqrt(var_d * 252)
    se_single = math.sqrt(1 / YEARS)   # what deflated_sharpe_vs(var_sr=None) uses: 1/(T-1) per session
    z5 = (sr_ov - sr_cl) / se_pair
    z5_wrong = (sr_ov - sr_cl) / se_single
    # versus unlevered B&H (the headline, not a gate)
    m_bh = 252 * P * mu_w - P * (f + s) - cost - 3 * P * SIG ** 2 / 2
    te_bh = math.sqrt(P) * SIG
    t_bh = m_bh * math.sqrt(YEARS) / te_bh
    return dict(delta_bp=d * 1e4, V=V, D=D, cost=cost, m=m, te=te, t=t, sr_ov=sr_ov, sr_cl=sr_cl,
                dsr=sr_ov - sr_cl, rho=rho, se_pair=se_pair, z5=z5, z5_wrong=z5_wrong,
                m_bh=m_bh, te_bh=te_bh, t_bh=t_bh,
                z4=N01.inv_cdf(1 - 0.05 / k), z5_need=emax_z(N) + N01.inv_cdf(0.8))

def p_works(st, g7=1.0, step=0.025, lim=7.0):
    """P(both halves > 0, t > z4, z5 > need); t and z5 driven by the same noise (approx)."""
    th = st["t"] / math.sqrt(2)
    tot = 0.0
    n = int(2 * lim / step) + 1
    xs = [-lim + i * step for i in range(n)]
    ws = [N01.pdf(x) * step for x in xs]
    for x1, w1 in zip(xs, ws):
        if th + x1 <= 0:
            continue
        for x2, w2 in zip(xs, ws):
            if th + x2 <= 0:
                continue
            e = (x1 + x2) / math.sqrt(2)
            if st["t"] + e > st["z4"] and st["z5"] + e >= st["z5_need"]:
                tot += w1 * w2
    return tot * g7

def p_g7(h, sig_q=0.38, years_q=5.95, c_bp=1.0, veto_z=0.0):
    """QQQ 1999-03..2005-02 veto: pass unless z(overlay - constant) < veto_z.
    sig_q ASSUMED ~2x SPY; effect ASSUMED to scale with vol. veto_z 0 = r2 draft (sign),
    -1 = r2-flow G7'."""
    d = DELTA_PUB * h * sig_q / SIG
    m = P * (1 - P) * 252 * d - P * (1 - P) * sig_q ** 2 / 2 - LEGS * c_bp / 1e4
    te = math.sqrt(P * (1 - P)) * sig_q
    return N01.cdf(m * math.sqrt(years_q) / te - veto_z)

line("=" * 100)
line("15. OVERLAY (1x always + 1x financed inside [T-3,T+3]) vs CONSTANT LEVERAGE 1+p, p=1/3.")
line("    delta = window-minus-outside mean, published ~10 bp/day; h = surviving share. 1 bp/side,")
line("    cash 1.5%, spread 1%, N = 39 + k = 40 (k = 1): G4 needs z > 1.645, G5 needs z >= E[maxZ]+0.84.")
line("=" * 100)
line(f"tracking error of the timing book = sqrt(p(1-p)) * sigma = {math.sqrt(P*(1-P))*SIG:.2%}/yr "
     f"(1x long/flat vs B&H: sqrt(1-p)*sigma = {math.sqrt(1-P)*SIG:.2%}/yr)")
line(f"extra variance drag of the overlay vs constant leverage = p(1-p) sigma^2/2 = {P*(1-P)*SIG**2/2:.2%}/yr")
line(f"corr(overlay, constant) = (1+p)/sqrt(1+3p) = {(1+P)/math.sqrt(1+3*P):.3f}")
weights = [(1.0, 0.10), (0.88, 0.10), (0.69, 0.15), (0.38, 0.30), (0.0, 0.35)]   # r1 weights, h-space
tot_w = 0.0
for h, w in weights:
    st = stats(h)
    g7 = p_g7(h)
    pw = p_works(st, g7)
    tot_w += w * pw
    pf = N01.cdf(st["t"])
    ph = N01.cdf(st["t"] / math.sqrt(2)) ** 2
    p4 = N01.cdf(st["t"] - st["z4"])
    p5 = N01.cdf(st["z5"] - st["z5_need"])
    line(f"h={h:4.2f} delta={st['delta_bp']:4.1f}bp: timing value {st['V']:+.2%} - drag {st['D']:.2%} - cost {st['cost']:.2%}"
         f" = {st['m']:+.2%}/yr; t={st['t']:4.2f}; P(G1) {pf:.2f} P(G2) {ph:.2f} P(G4) {p4:.2f};"
         f" dSR {st['dsr']:+.3f} SE {st['se_pair']:.3f} z5={st['z5']:4.2f} P(G5) {p5:.2f};"
         f" P(G7) {g7:.2f}; P(WORKS) {pw:.3f}")
line(f"prior-weighted P(WORKS) with r1's h-weights {[w for _, w in weights]}: {tot_w:.3f}")
line()
line("    Same, with r2-flow's G7' (veto only if the QQQ timing book is below zero by > 1 SE),")
line("    2 bp/side (the voted primary), and a 14 bp/day 'published' delta (window = all the return):")
for dpub in (10e-4, 14e-4):
    DELTA_PUB = dpub
    tw = 0.0
    for h, w in weights:
        st = stats(h, c_bp=2.0)
        g7 = p_g7(h, c_bp=2.0, veto_z=-1.0)
        pw = p_works(st, g7)
        tw += w * pw
        line(f"  delta_pub {dpub*1e4:4.1f} bp, h={h:4.2f}: net {st['m']:+.2%}/yr, z_timing {st['t']:4.2f}, "
             f"P(G1) {N01.cdf(st['t']):.2f}, P(G2) {N01.cdf(st['t']/math.sqrt(2))**2:.2f}, "
             f"P(G4) {N01.cdf(st['t'] - st['z4']):.2f}, z5 {st['z5']:4.2f} (SE {st['se_pair']:.3f}), "
             f"P(G5) {N01.cdf(st['z5'] - st['z5_need']):.2f}, P(G7') {g7:.2f}, P(WORKS) {pw:.3f}")
    line(f"  delta_pub {dpub*1e4:4.1f} bp: prior-weighted P(WORKS) {tw:.3f}")
DELTA_PUB = 10e-4
line()
line("    G5 computed with the SINGLE-Sharpe variance 1/(T-1) (edgelab deflated_sharpe_vs default)")
for h, _ in weights:
    st = stats(h)
    line(f"h={h:4.2f}: z5 paired {st['z5']:4.2f}  vs  z5 single-SE {st['z5_wrong']:4.2f}  (need {st['z5_need']:.2f})")
line()
line("    The same overlay against UNLEVERED B&H (headline only)")
for h, _ in weights:
    st = stats(h)
    line(f"h={h:4.2f}: active vs B&H {st['m_bh']:+.2%}/yr, TE {st['te_bh']:.1%}, t {st['t_bh']:4.2f}, "
         f"P(beats B&H full window) {N01.cdf(st['t_bh']):.2f}")
line()
line("    Bracket sensitivity: overlay-minus-constant (gates) vs overlay-minus-B&H (headline), h = 0.38")
for f in (0.0, 0.015, 0.03):
    for s in (0.01, 0.04):
        st = stats(0.38, f=f, s=s)
        line(f"cash {f:4.1%} spread {s:3.0%}: vs constant {st['m']:+.3%}/yr (z5 {st['z5']:4.2f}); "
             f"vs B&H {st['m_bh']:+.2%}/yr")
line()
line("    Cost sensitivity, h = 0.38 and h = 1")
for c in (1, 2, 5):
    a, b = stats(0.38, c_bp=c), stats(1.0, c_bp=c)
    line(f"{c} bp/side: h=0.38 {a['m']:+.2%}/yr (t {a['t']:4.2f}); h=1 {b['m']:+.2%}/yr (t {b['t']:4.2f})")
line()
line("    k = 2 (Holm first slot p < 0.025) and N = 41, h = 1 and 0.69")
for h in (1.0, 0.69):
    st = stats(h, N=41, k=2)
    line(f"h={h:4.2f}: P(WORKS) {p_works(st, p_g7(h)):.3f} (k=1: {p_works(stats(h), p_g7(h)):.3f})")

# --------------------------------------------------------------- synthetic check
line()
line("=" * 100)
line("16. SYNTHETIC check (i.i.d. normal sessions, NOT market data): tracking error of the timing book")
line("    and invariance of overlay-minus-constant to cash and spread.")
line("=" * 100)
rng = random.Random(20261009)
months = int(SESSIONS / 21)
W = ([0] * 14 + [1] * 7) * months
W = W[:SESSIONS] + [0] * max(0, SESSIONS - len(W))
p_real = sum(W) / len(W)
diffs = {}
te_samples = []
REPS = 300
for rep in range(REPS):
    r = [rng.gauss(MU_D, SIG_D) for _ in range(SESSIONS)]
    tb = [(w - p_real) * x for w, x in zip(W, r)]
    m_tb = sum(tb) / len(tb)
    te_samples.append(math.sqrt(sum((x - m_tb) ** 2 for x in tb) / (len(tb) - 1)) * math.sqrt(252))
    for f in (0.0, 0.03):
        for s in (0.01, 0.04):
            F = (f + s) / 252
            fd = f / 252
            lo = lc = 0.0
            for w, x in zip(W, r):
                L = 1 + w
                lo += math.log(1 + L * x - (L - 1) * F)
                lc += math.log(1 + (1 + p_real) * x - p_real * F)
            diffs.setdefault((f, s), []).append((lo - lc) / YEARS)
line(f"realised window share p = {p_real:.4f}; mean session-level TE of the timing book over {REPS} paths: "
     f"{sum(te_samples)/REPS:.2%}/yr (formula {math.sqrt(p_real*(1-p_real))*SIG:.2%})")
base = diffs[(0.0, 0.01)]
for key, v in sorted(diffs.items()):
    dev = [a - b for a, b in zip(v, base)]
    line(f"cash {key[0]:.0%} spread {key[1]:.0%}: mean(overlay - constant) {sum(v)/REPS:+.3%}/yr; "
         f"max |change vs cash 0%/spread 1%| on the same path {max(abs(x) for x in dev):.3%}/yr")
sd = math.sqrt(sum((x - sum(base)/REPS) ** 2 for x in base) / (REPS - 1))
line(f"SD across paths of the 21.5-year mean difference (no effect): {sd:.2%}/yr "
     f"(formula TE/sqrt(Y) = {math.sqrt(p_real*(1-p_real))*SIG/math.sqrt(YEARS):.2%}/yr)")

line()
line("=" * 100)
line("17. The Archivist's +1.0%/yr (r1-archivist §0.3, estimates.txt) re-scored against CONSTANT")
line("    leverage instead of 1x B&H, with the Archivist's own inputs: window excess 7.2 bp/day intact,")
line("    unconditional 2.4 bp/day, 84 window days of 252, sigma_d 1.2%, P = 0.15/0.35/0.50.")
line("    Financing and the SSO expense ratio cancel against an identically financed constant book;")
line("    only trading costs remain (24 unit-legs/yr at 1 bp/side).")
line("=" * 100)
pa = 84 / 252
sig_a = 0.012 * math.sqrt(252)
drag_a = pa * (1 - pa) * sig_a ** 2 / 2
ev = 0.0
for h, w in ((1.0, 0.15), (0.5, 0.35), (0.0, 0.50)):
    win = 2.4 + h * (7.2 - 2.4)                    # bp/day, window excess (Archivist's construction)
    out = (2.4 * 252 - win * 84) / (252 - 84)      # implied outside-window excess
    d = (win - out) / 1e4
    m = pa * (1 - pa) * 252 * d - drag_a - 24 * 1e-4
    ev += w * m
    line(f"h={h:3.1f}: window {win:.2f} bp, outside {out:.2f} bp, delta {win - out:.2f} bp/day -> "
         f"timing value {pa*(1-pa)*252*d:+.2%} - drag {drag_a:.2%} - cost 0.24% = {m:+.2%}/yr")
line(f"expected timing contribution vs constant leverage: {ev:+.2%}/yr (Archivist's vs B&H: +1.05%/yr)")
se = math.sqrt(pa * (1 - pa)) * sig_a / math.sqrt(YEARS)
line(f"standard error of a 21.5-year mean of the timing book: {se:.2%}/yr -> the EV is {ev/se:.2f} SE")
ev_mine = 0.0
for h, w in weights:
    ev_mine += w * stats(h)["m"]
line(f"same EV with r1-redteam's h-weights and a 10 bp/day published delta: {ev_mine:+.2%}/yr ({ev_mine/se:.2f} SE)")
pw = sum(w * p_works(stats(h), p_g7(h)) for h, w in weights)
line(f"what the PROCESS is worth: P(WORKS) {pw:.3f} x a shrunk forward edge of ~3%/yr = {pw*0.03:+.2%}/yr "
     f"(with the 14 bp mapping, P(WORKS) ~0.13 -> ~+0.4%/yr)")

# --------------------------------------------------------------- section 18 (round 2, final check)
line()
line("=" * 100)
line("18. Two corrections found while checking the bracket claim (formulas only, no market data):")
line("    (a) the Sharpe-difference G5 is NOT invariant to cash/spread: its concentration penalty")
line("        SR_A*(rho - 1) scales with the excess-Sharpe LEVEL, i.e. with the assumed cash rate;")
line("    (b) r1 §3.2/541: WORKS also needs no flip at N = 100, so WORKS needs z >= E[maxZ_100]+0.84.")
line("    2 bp/side, G7' (veto if QQQ timing z < -1), k = 1. R4 pairs: cash {0,1.5,3}% x spread {1.5,4}%.")
line("=" * 100)
need40 = emax_z(40) + N01.inv_cdf(0.8)
need100 = emax_z(100) + N01.inv_cdf(0.8)
line(f"G5 threshold: N=40 z >= {need40:.2f};  N=100 z >= {need100:.2f}")

def p_works_gen(st, zkey, need, g7, step=0.025, lim=7.0):
    th = st["t"] / math.sqrt(2)
    tot = 0.0
    n = int(2 * lim / step) + 1
    xs = [-lim + i * step for i in range(n)]
    ws = [N01.pdf(x) * step for x in xs]
    for x1, w1 in zip(xs, ws):
        if th + x1 <= 0:
            continue
        for x2, w2 in zip(xs, ws):
            if th + x2 <= 0:
                continue
            e = (x1 + x2) / math.sqrt(2)
            if st["t"] + e > st["z4"] and st[zkey] + e >= need:
                tot += w1 * w2
    return tot * g7

line()
line("  (a) Sharpe-difference z5 across the six R4 pairs, delta_pub 10 bp (h = 1 and 0.69):")
for h in (1.0, 0.69):
    row = []
    for f in (0.0, 0.015, 0.03):
        for s in (0.015, 0.04):
            st = stats(h, c_bp=2.0, f=f, s=s)
            row.append((st["z5"], f, s, st))
    lo = min(row, key=lambda r: r[0])
    hi = max(row, key=lambda r: r[0])
    prim = [r for r in row if r[1] == 0.015 and r[2] == 0.015][0]
    line(f"   h={h:4.2f}: z5 primary(1.5%,1.5%) {prim[0]:.2f}; min {lo[0]:.2f} at cash {lo[1]:.1%}/spread {lo[2]:.1%}; "
         f"max {hi[0]:.2f} at cash {hi[1]:.1%}/spread {hi[2]:.1%}; timing z (log) {prim[3]['t']:.2f} at every pair")
line("   equal-volatility reading: the Sharpe difference benchmarks S1 against constant leverage scaled")
line("   to S1's volatility (x sqrt(1+3p)/(1+p) = %.4f), i.e. an extra hurdle over (A) of:" % (math.sqrt(1+3*P)/(1+P)))
for f in (0.0, 0.015, 0.03):
    E_cl = (1 + P) * MU - P * (f + 0.015) - f
    line(f"     cash {f:4.1%} (spread 1.5%): (A) excess mean {E_cl:.2%}/yr -> equal-vol hurdle +{E_cl*(math.sqrt(1+3*P)/(1+P)-1):.2%}/yr "
         f"(vs the log drag {P*(1-P)*SIG**2/2:.2%}/yr charged by the timing book)")

line()
line("  (b) P(G5) and P(WORKS) by G5 statistic; WORKS needs the N=100 threshold (no flip).")
line("      'sharpe' = (SR_S1 - SR_A)/SE_paired at the binding pair (cash 0%, spread 1.5%);")
line("      'log'    = the log timing book's own z (r2-flow G5', log form), invariant to the bracket.")
for dpub in (10e-4, 14e-4):
    DELTA_PUB = dpub
    for label, zkey, f_, s_ in (("sharpe", "z5", 0.0, 0.015), ("log", "t", 0.015, 0.015)):
        tw40 = tw100 = 0.0
        cells = []
        for h, w in weights:
            st = stats(h, c_bp=2.0, f=f_, s=s_)
            g7 = p_g7(h, c_bp=2.0, veto_z=-1.0)
            p5_40 = N01.cdf(st[zkey] - need40)
            p5_100 = N01.cdf(st[zkey] - need100)
            pw40 = p_works_gen(st, zkey, need40, g7)
            pw100 = p_works_gen(st, zkey, need100, g7)
            tw40 += w * pw40
            tw100 += w * pw100
            cells.append(f"h={h:.2f}: z {st[zkey]:.2f} P(G5@40) {p5_40:.2f} P(WORKS@40) {pw40:.3f} P(WORKS@100) {pw100:.3f}")
        line(f"   delta_pub {dpub*1e4:.0f} bp, {label}:")
        for c in cells:
            line("      " + c)
        line(f"      prior-weighted P(WORKS): {tw40:.3f} if N=40 only; {tw100:.3f} with the N=100 no-flip rule")
DELTA_PUB = 10e-4

line()
line("  (c) single-Sharpe-variance z at the voted primary (2 bp), for the edgelab default defect:")
for h in (1.0, 0.69):
    st = stats(h, c_bp=2.0)
    line(f"   h={h:4.2f}: Sharpe-difference z5 paired {st['z5']:.2f} vs single-SE {st['z5_wrong']:.2f}; "
         f"log timing-book z {st['t']:.2f} (its single-series SE IS 1/(T-1), so the default is right for it)")

line()
line("  (d) k = 2 under the final spec (G5' log, N = 41 at the gate, WORKS needs N = 100; Holm G4 z > 1.96):")
for h in (1.0, 0.69):
    st1 = stats(h, c_bp=2.0, N=40, k=1)
    st2 = stats(h, c_bp=2.0, N=41, k=2)
    g7 = p_g7(h, c_bp=2.0, veto_z=-1.0)
    line(f"   h={h:4.2f}: P(WORKS) k=1 {p_works_gen(st1, 't', need100, g7):.3f}; k=2 {p_works_gen(st2, 't', need100, g7):.3f}; "
         f"P(G4) k=1 {N01.cdf(st1['t'] - st1['z4']):.2f}, k=2 {N01.cdf(st2['t'] - st2['z4']):.2f}")

line()
line("  (e) QQQ veto rate at 2 bp/side: r1 sign test (veto if z < 0) vs r2-flow G7' (veto if z < -1):")
for h in (1.0, 0.69, 0.38, 0.0):
    line(f"   h={h:4.2f}: sign test {1 - p_g7(h, c_bp=2.0, veto_z=0.0):.2f}; G7' {1 - p_g7(h, c_bp=2.0, veto_z=-1.0):.2f}")
