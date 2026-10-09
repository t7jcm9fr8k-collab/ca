"""Archivist round-1 arithmetic. NO market data is read here.

Every input is either a published magnitude (cited in r1-archivist.md) or an
explicitly labelled ASSUMPTION. Output: estimates.txt next to this file.

Units: bp = basis points of return per trading day unless stated.
"""
import math

OUT = []
def p(s=""):
    OUT.append(s)

# ---------------------------------------------------------------- assumptions
SIGMA_D = {"low": 1.0, "base": 1.2, "high": 1.4}   # SPY daily SD, % (ASSUMED, not measured)
UNCOND_EX = 2.4      # bp/day: ~6%/yr equity premium / 252 (ASSUMED round number)
SSO_COST_YR = 0.88 + 0.50   # %/yr: SSO expense ratio 0.88% (ETFCentral, cited) + 0.50% swap spread (ASSUMED)
MARGIN_SPREAD_YR = 7.75 - 4.0  # %/yr: Alpaca 7.75% (undated support page, cited) minus T-bill 4% (ASSUMED)

def drag_bp(sigma_pct, l0=1.0, l1=2.0):
    """Extra log-growth drag per day from raising exposure l0 -> l1 (bp)."""
    s2 = (sigma_pct / 100.0) ** 2
    return (l1 ** 2 - l0 ** 2) / 2.0 * s2 * 1e4

p("== Variance drag of going from 1x to 2x for one day (bp/day) ==")
for k, s in SIGMA_D.items():
    p(f"  sigma_d={s:.1f}% ({k}): {drag_bp(s):.2f} bp/day")
p()

# Avellaneda & Zhang (2010): log LETF = b*log(index) - b(b-1)/2 * integrated variance
p("== Daily-reset path term over an n-day hold, 2x vs 2*index (log, bp) ==")
for n in (1, 7, 21, 126):
    for k in ("base",):
        s2 = (SIGMA_D[k] / 100.0) ** 2
        p(f"  n={n:3d} days, sigma_d={SIGMA_D[k]}%: -{2*(2-1)/2*s2*n*1e4:.1f} bp (beta=2); "
          f"-{3*(3-1)/2*s2*n*1e4:.1f} bp (beta=3)")
p()

def overlay(name, window_hist_ex, days_per_yr, sigma_pct, cost_bp_day, probs):
    """+1x exposure only on window days. h = share of the historical window premium
    (over the unconditional excess) that survives. Returns per-scenario %/yr and EV."""
    p(f"== {name} ==")
    p(f"  inputs: historical window excess {window_hist_ex} bp/day, {days_per_yr} days/yr, "
      f"sigma_d {sigma_pct}%, cost {cost_bp_day:.2f} bp/day, unconditional excess {UNCOND_EX} bp/day")
    ev = 0.0
    for h, pr in probs:
        mu = UNCOND_EX + h * (window_hist_ex - UNCOND_EX)
        net = mu - drag_bp(sigma_pct) - cost_bp_day
        yr = net * days_per_yr / 100.0
        ev += pr * yr
        p(f"  h={h:.2f} (P={pr:.2f}): window excess {mu:.2f} bp -> net {net:+.2f} bp/day -> {yr:+.2f} %/yr")
    p(f"  expected contribution: {ev:+.2f} %/yr")
    p()
    return ev

sso_bp = SSO_COST_YR / 252 * 100   # %/yr -> bp/day
margin_bp = MARGIN_SPREAD_YR / 360 * 100

# 1. Month-end equity window [T-3, T+3]; Etula et al. WP: +77 bp over 7 days (~11 bp/day raw);
#    Kayacetin 2026: 10 bp/day vs 0 bp other days. Use 11.0 raw - 1.5 rf = 9.5 bp excess (ASSUMED rf).
probs_tom = [(1.0, 0.15), (0.5, 0.35), (0.0, 0.50)]
# Base: the window carries 100% of a 6.05%/yr premium ("all returns accrued during seven days",
# Etula et al. slides; McConnell & Xu) -> 6.05% / 84 days = 7.2 bp/day.
# High: the WP's post-1995 figure, +77 bp over T-3..T+3 = 11 bp/day raw ~ 9.5 bp excess.
for k in ("base", "high"):
    overlay(f"TOM/dash-for-cash overlay, 2x on [T-3,T+3], SSO financing, sigma {k}, window = 100% of premium",
            7.2, 84, SIGMA_D[k], sso_bp, probs_tom)
overlay("TOM overlay, WP post-1995 magnitude (9.5 bp/day), SSO, sigma base",
        9.5, 84, SIGMA_D["base"], sso_bp, probs_tom)
overlay("TOM overlay financed with Alpaca margin instead of SSO (7.2 bp, sigma base)",
        7.2, 84, SIGMA_D["base"], margin_bp, probs_tom)

# 2. Macro-announcement days (~44/yr); Ai, Bansal & Guo WP: ~10 bp vs ~1 bp (1961-2023).
#    Use 9 bp excess; announcement-day sigma ASSUMED 1.4%.
overlay("Macro-announcement overlay, 2x on ~44 days", 9.0, 44, 1.4, sso_bp,
        [(1.0, 0.20), (0.5, 0.30), (0.0, 0.50)])

# 3. Treasury end-of-month: Hartley & Schwarz WP: 10y note last 3 days ~25 bp/month excess
#    = 8.3 bp/day. Adding +1x IEF-like exposure on margin; bond-on-equity drag ~0.1 bp (ASSUMED);
#    unconditional bond excess 0.5 bp/day (ASSUMED term premium).
p("== Treasury end-of-month overlay (+1x 10y-duration bonds on margin, last 3 days) ==")
ev = 0.0
for h, pr in [(1.0, 0.15), (0.5, 0.30), (0.0, 0.55)]:
    mu = 0.5 + h * (8.3 - 0.5)
    net = mu - margin_bp - 0.1
    yr = net * 36 / 100.0
    ev += pr * yr
    p(f"  h={h:.2f} (P={pr:.2f}): {mu:.2f} bp -> net {net:+.2f} bp/day -> {yr:+.2f} %/yr (10y scale)")
p(f"  expected contribution: {ev:+.2f} %/yr at 10y-note scale; TLT (duration ~2x) would roughly "
  f"double the bp IF the yield effect is equal across maturities (unverified)")
p()

# 4. Halloween: 2x Nov-Apr. Zhang & Jacobsen (2021): Nov-Apr ~4%/yr higher than May-Oct (worldwide).
p("== Halloween overlay: 2x Nov-Apr, 1x May-Oct (SSO), sigma base ==")
s2_yr = (SIGMA_D["base"] / 100) ** 2 * 252
drag_half = (4 - 1) / 2 * s2_yr * 0.5 * 100
cost_half = SSO_COST_YR * 0.5
ev = 0.0
for d, pr in [(4.0, 0.30), (2.0, 0.30), (0.0, 0.40)]:
    winter_ex = 3.0 + d / 2  # half of a 6% premium plus half the winter-summer gap (ASSUMED split)
    yr = winter_ex - drag_half - cost_half
    ev += pr * yr
    p(f"  winter-summer gap {d:.1f}%/yr (P={pr:.2f}): winter excess {winter_ex:.1f}% - drag {drag_half:.2f}% "
      f"- cost {cost_half:.2f}% = {yr:+.2f} %/yr")
p(f"  expected contribution: {ev:+.2f} %/yr (and 2x exposure through any winter crash)")
p()

# 5. Pre-refunding (Wang & Zhao WP): 4 days/yr, 'annualized Sharpe > 4'. Annualization unknown.
p("== Pre-refunding 'Sharpe > 4' — what it implies per event ==")
p(f"  if annualized over 4 events/yr: mean/SD per event > 4/sqrt(4) = {4/math.sqrt(4):.2f} SD (implausible)")
p(f"  if annualized with sqrt(252):     mean/SD per event > 4/sqrt(252) = {4/math.sqrt(252):.2f} SD")
p(f"  at a long-bond daily SD of ~0.9% (ASSUMED) the latter is > {4/math.sqrt(252)*0.9*100:.0f} bp per event")
p()

# 5b. HMM long-only switch (SPY -> 10y bonds in the last ~4 days when equities are overweight).
#     Paper: long-short futures ~10%/yr, Sharpe > 1, 1997-2023 (cited). Share a long-only switch
#     captures: 25-50% (ASSUMED, midpoint 37.5%). If no effect: lose (equity - bond) excess on ~24
#     switched days/yr (2.4 - 0.5 bp) plus ~4 auction trades/month at ~0.5 bp (ASSUMED).
p("== HMM long-only switch (SPY -> bonds, last ~4 days, months with equities overweight) ==")
ev = 0.0
for h, pr in [(1.0, 0.10), (0.5, 0.25), (0.0, 0.65)]:
    if h > 0:
        yr = 10.0 * 0.375 * h
    else:
        yr = -((2.4 - 0.5) * 24 + 0.5 * 48) / 100.0
    ev += pr * yr
    p(f"  h={h:.2f} (P={pr:.2f}): {yr:+.2f} %/yr")
p(f"  expected contribution: {ev:+.2f} %/yr")
p()
# 5c. Pre-refunding: per-event mean >= 0.25 SD (if sqrt(252) annualization), long-bond SD 0.9% (ASSUMED)
p("== Pre-refunding overlay (+1x long bonds on 4 pre-announcement days/yr) ==")
ev = 0.0
per_event = 0.25 * 0.9 * 100  # bp
for h, pr in [(1.0, 0.25), (0.5, 0.30), (0.0, 0.45)]:
    yr = (4 * h * per_event - 4 * 1.04) / 100.0
    ev += pr * yr
    p(f"  h={h:.2f} (P={pr:.2f}): {4*h*per_event:.0f} bp gross - margin {4*1.04:.0f} bp -> {yr:+.2f} %/yr")
p(f"  expected contribution: {ev:+.2f} %/yr")
p(f"  power, 2005-2026 (~86 events) at 0.25 SD/event: t ~ {0.25*math.sqrt(86):.2f}")
p()

# 6. Power of the recommended first test on the on-disk SPY span (~2005-02 .. 2026-09).
p("== Power: window-vs-outside mean daily return, SPY ~2005-02..2026-09 ==")
months = 259
n_days = 5413          # SPY file bar count as stated in EVIDENCE.md (E-15 section)
for wlen in (7, 4):
    n1 = months * wlen
    n2 = n_days - n1
    for k, s in SIGMA_D.items():
        se = s * 100 * math.sqrt(1 / n1 + 1 / n2)   # bp
        row = [f"diff {d} bp -> t {d/se:.2f}" for d in (3, 5, 7, 9)]
        p(f"  window {wlen}d (n_in {n1}, n_out {n2}), sigma {s}%: SE {se:.2f} bp; " + "; ".join(row))
p("  one-sided 5% test needs t > 1.645; power ~50% at t = 1.645, ~80% at t = 2.49")
p()
p("== Same for a TLT-type 3-day window (bond daily SD ASSUMED 0.9%) ==")
n1 = months * 3
n2 = n_days - n1
se = 0.9 * 100 * math.sqrt(1 / n1 + 1 / n2)
p(f"  SE {se:.2f} bp; diff 8.3 bp -> t {8.3/se:.2f}; diff 4.2 bp -> t {4.2/se:.2f}")
p()

# 6b. Halloween power on the on-disk span (~21 winter/summer pairs)
p("== Halloween: power with ~21 seasons ==")
ann = SIGMA_D["base"] * math.sqrt(252)          # % per year (ASSUMED sigma_d)
half = ann * math.sqrt(0.5)
diff_sd = half * math.sqrt(2)
se = diff_sd / math.sqrt(21)
p(f"  annual SD {ann:.1f}%, half-year SD {half:.1f}%, SD of (winter - summer) {diff_sd:.1f}%/yr, SE over 21 yrs {se:.2f}%")
for d in (2, 4, 6):
    p(f"  true gap {d}%/yr -> t {d/se:.2f}")
p()

# 7. Why timing alone cannot beat buy-and-hold on CAGR (window-only, cash otherwise)
p("== Window-only (cash otherwise) vs buy-and-hold, excess-return terms ==")
for h in (1.0, 0.5, 0.0):
    mu = UNCOND_EX + h * (7.2 - UNCOND_EX)
    win = mu * 84 / 100
    bh = UNCOND_EX * 252 / 100
    p(f"  h={h:.1f}: window-only earns {win:.2f}%/yr excess vs buy-and-hold {bh:.2f}%/yr")
p("  => at full strength (window = 100% of the premium) window-only roughly ties B&H in excess return at"
  " ~58% of the volatility; at half strength it trails B&H by ~2%/yr. Raising ROI above B&H"
  " requires leverage inside the window.")

with open(__file__.replace("estimates.py", "estimates.txt"), "w") as f:
    f.write("\n".join(OUT) + "\n")
print("\n".join(OUT))
