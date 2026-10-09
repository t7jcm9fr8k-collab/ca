"""Archivist round-2 arithmetic. NO market data is read. Formulas + cited inputs only.

Purpose: put the Red Team's prior (r1-redteam §1.4, §3.6; hurdles-output.txt) and the
Archivist's round-1 scenarios (estimates.txt) on ONE scale, and evaluate the brief's D1
framing: 2x-in-window overlay vs constant leverage at the same average exposure.

Inputs and where they come from:
  MU_TOTAL = 11.74%/yr arithmetic B&H return, sigma = 19.2%/yr, 21.48 years
             -> hurdles-output.txt §1, §3 (from EVIDENCE.md:533)
  CASH     = 1.5%/yr (the Red Team's working value; FRED annual averages found for 11 of
             22 years average 2.63% and are biased up: hurdles-output.txt §8). ASSUMPTION.
  FWD_EX   = 6.05%/yr forward equity premium (Archivist round-1 assumption, estimates.txt).
  p        = 7/21 sessions in [T-3, T+3] (calendar approximation; the run uses the real count).
  Scenario weights: Red Team r1 §1.4 table; Archivist estimates.txt (TOM block).
  SPY ex-date steps after the stooq cutoff: 30-59 bp (r1-quartermaster §5) at the five
  ex-dates listed in r2-brief §2 (2025-06-20 ... 2026-06-18).
"""
import math

OUT = []
def p_(s=""):
    OUT.append(s)

def Phi(x):
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))

MU_TOTAL = 11.74     # %/yr arithmetic, B&H
SIGMA = 19.2         # %/yr
YEARS = 21.48
CASH = 1.5           # %/yr  (ASSUMPTION, bracketed elsewhere)
FWD_EX = 6.05        # %/yr  (ASSUMPTION)
P = 7.0 / 21.0       # share of sessions in the window
DAYS = 252.0
W_DAYS = P * DAYS    # ~84
O_DAYS = DAYS - W_DAYS

def delta_from_share_total(S):
    """Red Team's S = share of ALL arithmetic return (incl. the cash part) carried by the window.
    Returns window-minus-rest mean daily return, bp."""
    win = S * MU_TOTAL / W_DAYS
    out = (1 - S) * MU_TOTAL / O_DAYS
    return (win - out) * 100

def delta_from_h(h, excess):
    """Archivist's h: window carries share q = P + h*(1-P) of the EXCESS premium.
    h=1 -> all excess in window (rest earns cash); h=0 -> no timing effect."""
    q = P + h * (1 - P)
    win = q * excess / W_DAYS
    out = (1 - q) * excess / O_DAYS
    return (win - out) * 100

# ---------------------------------------------------------------- 1. one scale
p_("== 1. Both priors on one scale: window-minus-rest mean daily return (bp), 7-session window ==")
rt = [(1.0, 0.10), (0.9, 0.10), (0.75, 0.15), (0.5, 0.30), (P, 0.35)]
ex_bt = MU_TOTAL - CASH          # realized 2005-26 excess premium at 1.5% cash
ar = [(1.0, 0.15), (0.5, 0.35), (0.0, 0.50)]
e_rt = 0.0
p_("  Red Team scenarios (S = share of all return; 'no effect' = S equal to exposure share):")
for S, w in rt:
    d = delta_from_share_total(S)
    e_rt += w * d
    p_(f"    S={S:.2f} w={w:.2f}: delta = {d:5.2f} bp/day")
p_(f"    expected delta = {e_rt:.2f} bp/day")
for label, ex in (("backtest units (realized excess 10.24%/yr)", ex_bt), ("forward units (6.05%/yr)", FWD_EX)):
    e_ar = 0.0
    p_(f"  Archivist scenarios, {label}:")
    for h, w in ar:
        d = delta_from_h(h, ex)
        e_ar += w * d
        p_(f"    h={h:.2f} w={w:.2f}: delta = {d:5.2f} bp/day")
    p_(f"    expected delta = {e_ar:.2f} bp/day")
p_("  => on the backtest scale the two priors differ by ~25% in expected delta; the Red Team's is")
p_("     the MORE optimistic about the effect. The disagreement is not about the effect.")
p_()

# ---------------------------------------------------------------- 2. D1: overlay vs constant leverage
p_("== 2. D1: 2x-in-window overlay minus constant leverage (1+p), timing book (1_W - p)(r - f) ==")
te = SIGMA * math.sqrt(P * (1 - P))                  # %/yr
se_full = te / math.sqrt(YEARS)
se_half = te / math.sqrt(YEARS / 2)
drag_extra = P * (1 - P) / 2 * (SIGMA / 100) ** 2 * 100   # %/yr, log-growth
p_(f"  tracking error of the timing book = {te:.2f}%/yr; SE over {YEARS} yrs = {se_full:.2f}%/yr; per half = {se_half:.2f}%/yr")
p_(f"  extra variance drag of the overlay vs constant leverage = p(1-p)/2 * sigma^2 = {drag_extra:.2f}%/yr")
p_("  financing: both books borrow the same average amount -> a constant spread cancels exactly;")
p_("  cash rate: neither book holds idle cash -> the cash bracket does not move this comparison.")
legs = 24  # 1x bought + 1x sold each month
for cost in (1, 2, 5):
    p_(f"  cost {cost} bp/side -> {legs*cost/100:.2f}%/yr on the overlay's 24 legs")
p_()

# Sharpe-difference (G5-style) for the overlay vs constant leverage
rho = (1 + P) / math.sqrt(1 + 3 * P)
sr_mkt = (MU_TOTAL - CASH) / SIGMA * 0.0 + 0.53   # Red Team's excess-return B&H Sharpe (r1-redteam §5)
conc_pen = sr_mkt * ((1 + P) / math.sqrt(1 + 3 * P) - 1)
se_dsr = math.sqrt(2 * (1 - rho) / YEARS)
p_(f"  corr(overlay, constant leverage) = (1+p)/sqrt(1+3p) = {rho:.3f}; SE(dSR) ~ sqrt(2(1-rho)/T) = {se_dsr:.3f}")
p_(f"  concentration penalty on the overlay's Sharpe = SR_mkt*((1+p)/sqrt(1+3p) - 1) = {conc_pen:+.3f} (SR_mkt 0.53)")
p_()

Z_G5 = 3.05   # DSR_bench >= 0.80 at N = 40-42 (hurdles-output.txt §11)
def evaluate(label, scen, cost_bp):
    p_(f"  -- {label}, {cost_bp} bp/side --")
    ev = pg4_1 = pg4_2 = pg5 = pg2 = pg1 = 0.0
    for name, d, w in scen:
        a_gross = DAYS * P * (1 - P) * d / 100.0              # %/yr
        a_net = a_gross - drag_extra - legs * cost_bp / 100.0
        z_g4 = a_gross / se_full                               # placebo shares the drag and costs
        z_net = a_net / se_full
        z_half = a_net / se_half
        dsr = conc_pen + a_net / (SIGMA * math.sqrt(1 + 3 * P))
        z5 = dsr / se_dsr
        g4_1, g4_2 = Phi(z_g4 - 1.645), Phi(z_g4 - 1.96)
        g5 = Phi(z5 - Z_G5)
        g2 = Phi(z_half) ** 2
        g1 = Phi(z_net)
        ev += w * a_net; pg4_1 += w * g4_1; pg4_2 += w * g4_2; pg5 += w * g5; pg2 += w * g2; pg1 += w * g1
        p_(f"    {name:10s} w={w:.2f} delta={d:5.2f}bp  A_gross={a_gross:+5.2f}  A_net={a_net:+5.2f}%/yr  "
           f"z_timing={z_g4:4.2f}  z_dSR={z5:5.2f}  P(G4,k=1)={g4_1:.2f} P(G4,k=2)={g4_2:.2f} "
           f"P(G1)={g1:.2f} P(G2)={g2:.2f} P(G5)={g5:.3f}")
    p_(f"    weighted: E[A_net]={ev:+.2f}%/yr  P(G1)={pg1:.2f}  P(G2)={pg2:.2f}  P(G4,k=1)={pg4_1:.2f}  "
       f"P(G4,k=2)={pg4_2:.2f}  P(G5)={pg5:.3f}")
    return ev, pg5

rt_scen = [(f"S={S:.2f}", delta_from_share_total(S), w) for S, w in rt]
ar_bt = [(f"h={h:.1f}", delta_from_h(h, ex_bt), w) for h, w in ar]
ar_fw = [(f"h={h:.1f}", delta_from_h(h, FWD_EX), w) for h, w in ar]
for cost in (2, 5):
    evaluate("Red Team weights, backtest units", rt_scen, cost)
    evaluate("Archivist weights, backtest units", ar_bt, cost)
evaluate("Archivist weights, FORWARD units (Daniel's next years)", ar_fw, 2)
p_()
p_("  Reading: G5 (z >= 3.05 on the Sharpe difference) is the binding gate in every scenario short of")
p_("  the full published size. P(WORKS) for the overlay is bounded above by P(G5) ~ 0.05-0.10, versus")
p_("  the Red Team's ~0.03 for 1x long/flat vs B&H: the framing makes the test measure timing, it does")
p_("  not make a pass likely. Expected verdict at half size: PARTIAL ('lucky-sized'), not NULL.")
p_()

# ---------------------------------------------------------------- 3. my round-1 headline re-expressed
p_("== 3. Archivist round-1 '+1.0%/yr' re-expressed against the fair benchmark ==")
p_("  round 1 compared the overlay with 1x B&H (it included the equity premium on the extra exposure,")
p_("  net of drag and financing). Against constant leverage at 2 bp/side, forward units: see the")
p_("  'FORWARD units' weighted E[A_net] above.")
p_()

# ---------------------------------------------------------------- 4. cash bracket for the 1x descriptive
p_("== 4. Cash bracket sensitivity ==")
for c0, c1 in ((0.0, 3.0), (0.0, 1.5), (1.5, 3.0)):
    p_(f"  1x long/flat vs B&H: cash {c0}% -> {c1}% moves the rule by ~(1-p)*{c1-c0} = {(1-P)*(c1-c0):.2f}%/yr; "
       f"overlay vs constant leverage: 0.00%/yr")
p_()

# ---------------------------------------------------------------- 5. SPY price-only tail bias
p_("== 5. SPY-1d.csv is price-only after 2025-03-21: bias from the five later ex-dates (all outside W) ==")
n_ex = 5
for step in (30, 59):
    vs_A = n_ex * P * step          # constant leverage holds 1+p, overlay holds 1 on those dates
    vs_B = n_ex * 1.0 * step        # B&H loses the full payout
    p_(f"  step {step} bp: overlay favored vs (A) by {vs_A:.0f} bp cumulative = {vs_A/YEARS:.1f} bp/yr over the full window, "
       f"{vs_A/2.25:.0f} bp/yr over the ~2.25-yr post-T+1 span; B&H (B) understated by {vs_B:.0f} bp cumulative")
p_()

# ---------------------------------------------------------------- 6. out-of-sample spans
p_("== 6. Month-ends available, by what has (not) been seen (calendar counts, approx.) ==")
p_("  Etula window defined in the 2014 working paper; slide axis ends 2013 -> 2014-01..2026-08: ~152 month-ends")
p_("  Kayacetin sample 1994-2023 -> 2024-01..2026-08: ~32 month-ends")
p_("  Nathan-Suominen-Tasa sample ends 2025-12 (533 pre + 19 post months) -> 2026-01..2026-08: ~8 month-ends")

with open(__file__.replace("estimates_r2.py", "estimates_r2.txt"), "w") as f:
    f.write("\n".join(OUT) + "\n")
print("\n".join(OUT))
