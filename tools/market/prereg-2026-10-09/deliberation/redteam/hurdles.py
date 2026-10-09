#!/usr/bin/env python3
"""
Red Team, round 1 -- analytic hurdles. NO market data is read here.

Every input is either a formula constant or a number quoted from a repo file
(line cited) or from a verified source (named). Nothing below conditions on a
candidate rule's realised returns; these are arithmetic bounds and power
approximations under stated assumptions.

Inputs from the repo:
  EVIDENCE.md:517      SPY stooq file: 5,413 sessions, 2005-02-25 -> 2026-09-02
  EVIDENCE.md:531-534  buy-and-hold SPY over that file: CAGR ~10.4%, Sharpe 0.61,
                       vol 19.2%, max drawdown -56.5% (idle cash 3%, 5 bp)
External inputs (verified via search, see r1-redteam.md):
  Lucca & Moench 2015: +49 bp in the 24 h before scheduled FOMC announcements
  Ariel 1990: pre-holiday mean return 9-14x other days
  Harvey, Mazzoleni & Melone 2025: -17 bp next day when equities overweight
  FRED annual 3-month T-bill (investment basis), 11 of the 22 years only
"""
import math
from statistics import NormalDist

N01 = NormalDist()
GAMMA = 0.5772156649015329

SESSIONS = 5413                 # EVIDENCE.md:517
YEARS = SESSIONS / 252.0
BH_CAGR = 0.104                 # EVIDENCE.md:533
BH_VOL = 0.192                  # EVIDENCE.md:533
BH_SHARPE = 0.61                # EVIDENCE.md:533 (computed with 3% cash)

def emax_z(n):
    """Expected max of n iid N(0,1): Bailey & Lopez de Prado 2014 (as in combine.py:53-63)."""
    if n <= 1:
        return 0.0
    return (1 - GAMMA) * N01.inv_cdf(1 - 1.0 / n) + GAMMA * N01.inv_cdf(1 - 1.0 / (n * math.e))

def line(s=""):
    print(s)

line("=" * 78)
line("1. Deflation hurdle: E[max Z] of N null trials (combine.py:53-63 formula)")
line("=" * 78)
for n in (39, 40, 41, 42, 44, 50, 60, 100, 200):
    e = emax_z(n)
    line(f"N={n:4d}  E[maxZ]={e:5.3f}   z needed for DSR>=0.95: {e + 1.645:5.3f}"
         f"   one-sided p of that z: {1 - N01.cdf(e + 1.645):.2e}"
         f"   p of E[maxZ] alone: {1 - N01.cdf(e):.3f}")

se_sr = math.sqrt(1.0 / YEARS)   # Lo 2002 iid approx, SR small: SE(SR_ann) ~ sqrt((1+SR^2/2)/years)
se_sr_full = math.sqrt((1 + BH_SHARPE ** 2 / 2) / YEARS)
line()
line(f"years in window = {YEARS:.2f};  SE(annualised Sharpe) ~ {se_sr:.3f} (SR~0) "
     f"or {se_sr_full:.3f} at SR={BH_SHARPE}")

line()
line("=" * 78)
line("2. Sharpe-difference hurdle vs SPY, by exposure f (random-timing corr ~ sqrt(f))")
line("   SE(dSR) ~ SE(SR)*sqrt(2-2*rho); DSR_bench = Phi(dSR/SE - E[maxZ_N])")
line("=" * 78)
for n in (41, 42):
    e = emax_z(n)
    for f in (0.035, 0.19, 0.33, 0.50, 0.80, 0.976):
        rho = math.sqrt(f)
        se_d = se_sr_full * math.sqrt(max(2 - 2 * rho, 1e-9))
        line(f"N={n} f={f:5.3f} rho~{rho:4.2f} SE(dSR)~{se_d:5.3f}  "
             f"dSR for DSR>0.5: {e * se_d:5.2f}   for DSR>=0.95: {(e + 1.645) * se_d:5.2f}"
             f"   => strategy Sharpe >= {BH_SHARPE + e * se_d:4.2f} / {BH_SHARPE + (e + 1.645) * se_d:4.2f}")
    line()

line("=" * 78)
line("3. What share S of ALL the index's arithmetic return must the exposed days carry")
line("   for an unlevered part-time rule to match buy-and-hold CAGR?  (log-growth approx,")
line("   same daily variance on exposed days; cost = legs/yr * bp per leg)")
line("=" * 78)
g = math.log(1 + BH_CAGR)
half_var = BH_VOL ** 2 / 2
mu = g + half_var                # arithmetic annual mean of simple returns (approx)
line(f"B&H: log growth {g:.4f}, sigma^2/2 {half_var:.4f}, arithmetic mean mu ~ {mu:.4f}")
cases = [
    ("pre-holiday standalone", 9 / 252, 9),
    ("pre-FOMC standalone", 8 / 252, 8),
    ("turn-of-month T-1..T+3", 4 / 21, 12),
    ("TOM wide T-4..T+3", 7 / 21, 12),
    ("FOMC-cycle even weeks", 0.50, 28),
]
for name, f, rt in cases:
    for c in (0.0, 0.015, 0.03):
        for bp in (1, 2, 5):
            cost = rt * 2 * bp / 1e4
            s_needed = 1 - ((1 - f) * half_var + (1 - f) * c - cost) / mu
            line(f"{name:24s} f={f:5.3f} cash={c:4.1%} cost={bp}bp/leg ({rt} RT/yr):"
                 f" S >= {s_needed:5.2f}  (= {s_needed / f:5.1f}x the average day)")
    line()

line("=" * 78)
line("4. Published magnitudes, taken at face value, as STANDALONE unlevered rules")
line("=" * 78)
avg_day = mu / 252
fomc = 8 * 0.0049
line(f"pre-FOMC: 8 events x 49 bp = {fomc:.2%}/yr gross (Lucca-Moench), vs mu {mu:.2%}"
     f" -> S = {fomc / mu:.2f}; needed ~0.76 (section 3)")
for mult in (9, 14):
    ph = 9 * mult * avg_day
    line(f"pre-holiday at {mult}x the average day (Ariel 1990 range), 9 days/yr: "
         f"{ph:.2%}/yr -> S = {ph / mu:.2f}; needed ~0.76")
line("Both fall far short even before decay: sparse-event rules cannot beat")
line("buy-and-hold unlevered; they can only be overlays (= leverage on event days).")
excl_days = 6
cash_day = 0.015 / 252
for eff in (0.0017, 0.00085, 0.0):
    # Harvey-Mazzoleni-Melone: next-day equity return 17 bp LOWER when equities are
    # overweight. Excluded-day mean = average day - eff. Being out instead earns cash.
    m_excl = avg_day - eff
    gross = excl_days * (cash_day - m_excl)      # gain vs holding on the excluded days
    drag_save = excl_days / 252 * half_var
    cost = excl_days * 2 * 2 / 1e4
    line(f"exclusion overlay, out {excl_days} days/yr, excluded days {eff * 1e4:4.1f} bp below the "
         f"average day ({avg_day * 1e4:+.1f} bp), cash 1.5%: edge ~ {gross + drag_save - cost:+.2%}/yr at 2 bp/leg")

line()
line("=" * 78)
line("5. Null check: chance a RANDOM-timing unlevered rule beats B&H CAGR over the window")
line("   (expected shortfall = forgone premium net of drag/cash/cost; noise = sum of")
line("    returns on the (1-f) idle days relative to expectation)")
line("=" * 78)
sd_day = BH_VOL / math.sqrt(252)
for f, rt in ((0.035, 9), (0.19, 12), (0.33, 12), (0.5, 28), (0.976, 6)):
    for c in (0.015,):
        cost = rt * 2 * 2 / 1e4
        short = (1 - f) * (mu - c) - (1 - f) * half_var + cost       # per year, log approx
        sd_y = sd_day * math.sqrt(252 * f * (1 - f)) if f < 1 else 0  # hypergeometric-ish
        z = short * YEARS / (sd_y * math.sqrt(YEARS))
        line(f"f={f:5.3f}: expected shortfall {short:+.2%}/yr, timing-noise SD of the "
             f"annual difference {sd_y:.2%}; P(random beats B&H over {YEARS:.1f}y) ~ {1 - N01.cdf(z):.4f}")

line()
line("=" * 78)
line("6. Detectability of a timing effect (exposed-day mean minus other-day mean)")
line("   daily SD = 19.2%/sqrt(252); t = diff / (SD*sqrt(1/n1+1/n0))")
line("=" * 78)
n_days = SESSIONS
for name, n1 in (("TOM 4 days x 12 x 21.5y", 4 * 12 * YEARS), ("pre-FOMC 8/yr", 8 * YEARS),
                 ("pre-holiday 9/yr", 9 * YEARS), ("even weeks (f=0.5)", 0.5 * n_days)):
    n0 = n_days - n1
    se = sd_day * math.sqrt(1 / n1 + 1 / n0)
    need = (emax_z(42) + 1.645) * se
    line(f"{name:26s} n1={n1:6.0f}  SE(diff)={se * 1e4:5.2f} bp/day   diff for t=2: "
         f"{2 * se * 1e4:5.1f} bp   for t=3 (HLZ): {3 * se * 1e4:5.1f} bp   for DSR(N=42)>=0.95: {need * 1e4:5.1f} bp")

line()
line("=" * 78)
line("7. Forward paper/live period: years needed for t=2 on an ACTIVE return vs B&H")
line("=" * 78)
for edge in (0.01, 0.02, 0.03):
    for te in (0.03, 0.08, 0.17):
        yrs = (2 * te / edge) ** 2
        line(f"active edge {edge:.0%}/yr, tracking error {te:.0%}/yr -> {yrs:7.1f} years for t=2")

line()
line("=" * 78)
line("8. Cash: FRED 3-month T-bill annual averages found (investment basis), 11 of 22 years")
line("=" * 78)
fred = {2005: 3.22, 2006: 4.85, 2007: 4.48, 2008: 1.40, 2009: 0.15, 2010: 0.14,
        2015: 0.05, 2019: 2.11, 2022: 2.09, 2023: 5.28, 2024: 5.18}
avg = sum(fred.values()) / len(fred)
line(f"mean of the 11 years found: {avg:.2f}%  -- biased UP: the missing years include")
line("2011-14, 2016-18 and 2020-21; the fed funds target was 0-0.25% from 2008-12-16 to")
line("2015-12 and again from 2020-03-15 (end 2022-03 per a search engine's own note).")
for f in (0.19, 0.5):
    line(f"idle share {1 - f:.2f}: each 1 pt of cash-rate error moves the rule's CAGR by ~{(1 - f):.2f} pt/yr")

line()
line("=" * 78)
line("9. Tax illustration (assumptions stated; NOT advice; account type unknown)")
line("=" * 78)
pre = 0.104
for st in (0.24, 0.32, 0.37):
    after_rule = pre * (1 - st)                         # all gains short-term, realised yearly
    # B&H: defer, pay 15% LTCG once at the end; dividends ignored for simplicity
    W = (1 + pre) ** YEARS
    after_bh = ((W - 1) * (1 - 0.15) + 1) ** (1 / YEARS) - 1
    line(f"same 10.4% pre-tax: rule realised yearly at {st:.0%} ST rate -> {after_rule:.2%}/yr;"
         f" B&H deferred, 15% LTCG at the end -> {after_bh:.2%}/yr")

line()
line("=" * 78)
line("10. Power sketch: what an INTACT (or partly decayed) published effect would score")
line("    under the proposed gates, 21.5 years, cash 1.5%, 2 bp/leg. Normal approximations;")
line("    exposed-day variance = average-day variance; independent halves.")
line("=" * 78)
def power(name, f, rt, S, c=0.015, bp=2, N=42):
    cost = rt * 2 * bp / 1e4
    g_rule = S * mu - f * half_var + (1 - f) * c - cost
    m = g_rule - g                                  # active log growth vs B&H, per year
    te = BH_VOL * math.sqrt(1 - f)                  # active tracking error, per year
    p_full = N01.cdf(m / (te / math.sqrt(YEARS)))
    p_half = N01.cdf(m / (te / math.sqrt(YEARS / 2)))
    sr_rule = (S * mu - f * c - cost) / (BH_VOL * math.sqrt(f))
    sr_bh = (mu - c) / BH_VOL
    rho = math.sqrt(f)
    se_d = math.sqrt((1 + sr_rule ** 2 / 2) / YEARS) * math.sqrt(2 - 2 * rho)
    z = (sr_rule - sr_bh) / se_d
    e = emax_z(N)
    pd = lambda q: 1 - N01.cdf(e + N01.inv_cdf(q) - z)
    line(f"{name:22s} S={S:4.2f}: active {m:+.2%}/yr, TE {te:.1%}; P(full>B&H) {p_full:.2f}, "
         f"P(both halves) {p_half ** 2:.2f}; Sharpe {sr_rule:.2f} vs {sr_bh:.2f}, z={z:4.2f}; "
         f"P(DSR>0.5) {pd(0.5):.2f}, P(DSR>=0.8) {pd(0.8):.2f}, P(DSR>=0.95) {pd(0.95):.2f}")
for S in (1.0, 0.9, 0.75, 0.5):
    power("TOM T-1..T+3", 4 / 21, 12, S)
for S in (1.0, 0.9, 0.75):
    power("even weeks", 0.5, 28, S)

line()
line("=" * 78)
line("11. What a DSR threshold means family-wise: P(best of N null trials clears it)")
line("=" * 78)
for N in (42, 100):
    e = emax_z(N)
    for q in (0.5, 0.8, 0.95):
        zc = e + N01.inv_cdf(q)
        p1 = 1 - N01.cdf(zc)
        line(f"N={N}: DSR>={q:4.2f} <=> z>={zc:4.2f}; single-trial p={p1:.2e}; "
             f"P(max of {N} nulls clears) ~ {1 - (1 - p1) ** N:.3f}")
    line(f"N={N}: Bonferroni one-sided 5% critical z = {N01.inv_cdf(1 - 0.05 / N):4.2f}")

line()
line("=" * 78)
line("12. Event-day OVERLAY = buy-and-hold plus 1x extra on event days (i.e. leverage).")
line("    Extra leg financed at cash + 1.5%/yr (assumed spread, unverified), 2 bp/leg.")
line("    Event-day mean = average day + effect. Normal approx; halves independent.")
line("=" * 78)
def overlay(name, events, eff, c=0.015, spread=0.015, bp=2, N=42):
    sd_d = BH_VOL / math.sqrt(252)
    fin = events * (c + spread) / 252
    cost = events * 2 * bp / 1e4
    extra_mean = events * (avg_day + eff) - fin - cost          # per year, arithmetic
    extra_var = events * sd_d ** 2
    m_ar = mu + extra_mean                                       # overlay arithmetic mean
    var_tot = BH_VOL ** 2 + extra_var + 2 * events * sd_d ** 2   # 2x on event days: (2r)^2 = 4r^2
    g_ov = m_ar - var_tot / 2
    act = g_ov - g
    te = math.sqrt(extra_var)
    p_full = N01.cdf(act / (te / math.sqrt(YEARS)))
    p_half = N01.cdf(act / (te / math.sqrt(YEARS / 2)))
    sr_ov = (m_ar - c) / math.sqrt(var_tot)
    sr_bh = (mu - c) / BH_VOL
    cov = BH_VOL ** 2 + events * sd_d ** 2                       # event days: cov(2r, r) = 2 var
    rho = cov / (BH_VOL * math.sqrt(var_tot))                    # corr(overlay, B&H), exact under the model
    se_d = math.sqrt((1 + sr_ov ** 2 / 2) / YEARS) * math.sqrt(max(2 - 2 * rho, 1e-12))
    z = (sr_ov - sr_bh) / se_d
    e = emax_z(N)
    pd = lambda q: 1 - N01.cdf(e + N01.inv_cdf(q) - z)
    line(f"{name:30s} eff={eff * 1e4:5.1f} bp: active {act:+.2%}/yr, TE {te:.1%}; P(full) {p_full:.2f}, "
         f"P(both halves) {p_half ** 2:.2f}; dSR {sr_ov - sr_bh:+.3f}, z={z:4.2f}; P(DSR>=0.8) {pd(0.8):.2f}")
for eff in (0.0049, 0.00245, 0.0):
    overlay("pre-FOMC overlay, 8/yr", 8, eff)
for eff in (0.0030, 0.0015, 0.0):
    overlay("pre-holiday overlay, 9/yr", 9, eff)

line()
line("=" * 78)
line("13. Sharpe on RAW returns (replay.py:166-176 has no risk-free subtraction) inflates a")
line("    part-time rule: raw - excess = c/(sigma*sqrt(f)); bias in (rule - B&H) Sharpe edge")
line("    = (c/sigma) * (1/sqrt(f) - 1). Same-variance-on-exposed-days approximation.")
line("=" * 78)
for c in (0.015, 0.03):
    for f in (0.05, 0.19, 0.33, 0.5, 0.79):
        line(f"cash {c:.1%}  exposure f={f:4.2f}: rule inflated by {c / (BH_VOL * math.sqrt(f)):.2f}, "
             f"B&H by {c / BH_VOL:.2f}; spurious Sharpe edge {c / BH_VOL * (1 / math.sqrt(f) - 1):+.2f}")

line()
line("=" * 78)
line("14. Timing t-stat (exposed-day mean minus other-day mean) for a TOM window carrying")
line("    share S of all return: exposed-day mean = S*mu_d/f, other = (1-S)*mu_d/(1-f)")
line("=" * 78)
f = 4 / 21
n1 = 4 * 12 * YEARS
n0 = SESSIONS - n1
se = sd_day * math.sqrt(1 / n1 + 1 / n0)
mu_d = mu / 252
for S in (1.0, 0.9, 0.75, 0.5, 0.19):
    diff = S * mu_d / f - (1 - S) * mu_d / (1 - f)
    line(f"S={S:4.2f}: diff {diff * 1e4:5.1f} bp/day, SE {se * 1e4:4.2f} bp -> t = {diff / se:4.2f}")
