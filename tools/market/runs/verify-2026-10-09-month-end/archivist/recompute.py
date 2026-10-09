"""Archivist round 4: independent recomputation of the month-end overlay's core numbers.

Stdlib only. Imports no repo module (not edgelab, not bars) and was written without reading
edgelab's code. Inputs: tools/market/bars/SPY-1d.csv (rows after 2026-08-25 never read),
prereg-2026-10-09/windows-S1-SPY.csv (complete=True rows), prereg-2026-10-09/spy-distributions-
2025-2026.csv (the five frozen add-back dates). Conventions: PREREG-2026-10-09-month-end.md and
the lead's round-4 message:
  * scored from the close of 2005-03-24 to the close of 2026-08-25 (5,387 sessions), closes only;
  * r_t = close_t/close_{t-1} - 1; on the five ex-dates (close_t + D)/close_{t-1} - 1;
  * exposure 2 from each complete window's entry_exec close to its exit_exec close, else 1;
  * margin book, shares held between changes: position V grows at r_t, debt L accrues
    (1+f)^(days/365) - 1 per overnight leg (days = calendar gap between closes), f = 1.5% + 1.5%;
  * 2 bp per side on traded notional; (A) at constant exposure 1 + p_hat, reset to target at
    every close where S1 trades; B&H 1x total return. CAGR over calendar days / 365.25.
Two conventions the spec leaves open were identified by matching the run's own diagnostics
(B&H cost_paid 0.0002; S1's trough falls on an entry close) and are run both ways:
  (i)  capital is 1.0 at the start close BEFORE the opening purchase, which pays 2 bp;
  (ii) a change-close cost is booked after that close's mark (it lands in the next leg).
Output: recompute.txt (this file's printout).
"""
import csv
import datetime as dt
import json
import math

REPO = "/home/user/ca/tools/market"
BARS = f"{REPO}/bars/SPY-1d.csv"
WINDOWS = f"{REPO}/prereg-2026-10-09/windows-S1-SPY.csv"
DIVS = f"{REPO}/prereg-2026-10-09/spy-distributions-2025-2026.csv"
RUN = f"{REPO}/runs/edgelab-2026-10-09-month-end.txt"
ADD_BACK = {"2025-06-20", "2025-09-19", "2025-12-19", "2026-03-20", "2026-06-18"}
START, END = "2005-03-24", "2026-08-25"
F = 0.015 + 0.015
BPS = 0.0002
HALF = 2694
YLEN = [365.25]          # mutable so the sensitivity section can switch it
OUT = []


def p(s=""):
    OUT.append(s)


def d(s):
    return dt.date.fromisoformat(s)


# ------------------------------------------------------------------ data
dates, closes = [], []
with open(BARS, newline="") as fh:
    for row in csv.DictReader(fh):
        if row["Date"] > END:
            break
        dates.append(row["Date"])
        closes.append(float(row["Close"]))
assert dates[-1] == END
i0 = dates.index(START)
div = {}
with open(DIVS, newline="") as fh:
    for row in csv.DictReader(fh):
        if row["ex_date"] in ADD_BACK:
            div[row["ex_date"]] = float(row["amount_usd"])
assert set(div) == ADD_BACK
wins = []
with open(WINDOWS, newline="") as fh:
    for row in csv.DictReader(fh):
        if row["complete"] == "True":
            wins.append((row["entry_exec"], row["exit_exec"]))
assert len(wins) == 257

sess = list(range(i0 + 1, len(dates)))
T = len(sess)
R = [(closes[i] + div.get(dates[i], 0.0)) / closes[i - 1] - 1.0 for i in sess]
DAYS = [(d(dates[i]) - d(dates[i - 1])).days for i in sess]
EXPO = [2.0 if any(a < dates[i] <= b for a, b in wins) else 1.0 for i in sess]
n2 = sum(1 for e in EXPO if e == 2.0)
P_HAT = 1.0 + n2 / T
entries = {a for a, _ in wins}
exits = {b for _, b in wins}
assert START in entries and not (entries & exits)
changes = (entries | exits) - {START}
H = dates[sess[HALF - 1]]
p(f"sessions {T} ({dates[sess[0]]}..{dates[sess[-1]]}); 2x sessions {n2}; p_hat 1+{n2}/{T} = {P_HAT:.10f}; "
  f"change closes {len(changes)} + start; session {HALF} = {H}")


# ------------------------------------------------------------------ engine
def run(start_target, schedule, opening_cost=True, mark_pre_cost=True):
    E = 1.0
    eq = [E]
    cost_paid = BPS * start_target * E if opening_cost else 0.0
    E -= cost_paid
    V = start_target * E
    L = V - E
    fin = 0.0
    for k, i in enumerate(sess):
        V *= 1.0 + R[k]
        accr = (1.0 + F) ** (DAYS[k] / 365.0) - 1.0
        fin += L * accr
        L *= 1.0 + accr
        E = V - L
        mark = E
        tgt = schedule(dates[i])
        if tgt is not None:
            cost = BPS * abs(tgt * E - V)
            cost_paid += cost
            E -= cost
            V = tgt * E
            L = V - E
        eq.append(mark if mark_pre_cost else E)
    return eq, cost_paid, fin


def years(a, b):
    return (d(b) - d(a)).days / YLEN[0]


def cagr(e0, e1, a, b):
    return (e1 / e0) ** (1.0 / years(a, b)) - 1.0


def maxdd(eq):
    peak, worst = -1e300, 0.0
    for e in eq:
        peak = max(peak, e)
        worst = min(worst, e / peak - 1.0)
    return worst


def timing(s1, aa):
    x = [math.log(s1[k + 1] / s1[k]) - math.log(aa[k + 1] / aa[k]) for k in range(T)]
    m = sum(x) / T
    v1 = sum((y - m) ** 2 for y in x) / (T - 1)
    v0 = sum((y - m) ** 2 for y in x) / T
    g3 = (sum((y - m) ** 3 for y in x) / T) / v0 ** 1.5
    g4 = (sum((y - m) ** 4 for y in x) / T) / v0 ** 2
    sr = m / math.sqrt(v1)
    z = sr * math.sqrt(T - 1) / math.sqrt(1 - g3 * sr + (g4 - 1) / 4 * sr * sr)
    return {"mean_annual": m * 252, "te": math.sqrt(v1 * 252), "z": z, "skew": g3, "kurt": g4, "sum": sum(x)}


def s1_sched(day):
    if day in changes:
        return 2.0 if day in entries else 1.0
    return None


def book_set(target_a, opening_cost=True, mark_pre_cost=True):
    s1 = run(2.0, s1_sched, opening_cost, mark_pre_cost)
    aa = run(target_a, lambda day: target_a if day in changes else None, opening_cost, mark_pre_cost)
    bh = run(1.0, lambda day: None, opening_cost, mark_pre_cost)
    return s1, aa, bh


def metrics(s1, aa, bh):
    out = {}
    for name, (eq, cost, fin) in (("S1", s1), ("A", aa), ("BH", bh)):
        out[name] = {"cagr": cagr(eq[0], eq[-1], START, END), "maxdd": maxdd(eq),
                     "h1": cagr(eq[0], eq[HALF], START, H), "h2": cagr(eq[HALF], eq[-1], H, END),
                     "final": eq[-1], "cost": cost, "fin": fin}
    out["d"] = timing(s1[0], aa[0])
    return out


# ------------------------------------------------------------------ the run's printed values
txt = open(RUN).read().splitlines()
blob = "\n".join(txt[189:])
J = json.loads(blob[blob.index("{"):])
c0 = J["run"]["cells"][0]
assert (c0["cost_bps_per_side"], c0["cash_rate"], c0["spread"]) == (2.0, 0.015, 0.015)
RUNV = {
    ("S1", "cagr"): c0["rule"]["cagr"], ("A", "cagr"): c0["bar_A"]["cagr"], ("BH", "cagr"): c0["buy_and_hold"]["cagr"],
    ("S1", "maxdd"): c0["rule"]["max_drawdown"], ("A", "maxdd"): c0["bar_A"]["max_drawdown"],
    ("BH", "maxdd"): c0["buy_and_hold"]["max_drawdown"],
    ("S1", "h1"): c0["halves"]["first"]["rule"]["cagr"], ("A", "h1"): c0["halves"]["first"]["bar_A"]["cagr"],
    ("BH", "h1"): c0["halves"]["first"]["buy_and_hold"]["cagr"],
    ("S1", "h2"): c0["halves"]["second"]["rule"]["cagr"], ("A", "h2"): c0["halves"]["second"]["bar_A"]["cagr"],
    ("BH", "h2"): c0["halves"]["second"]["buy_and_hold"]["cagr"],
    ("d", "mean_annual"): c0["timing_book"]["log"]["mean_annual"], ("d", "te"): c0["timing_book"]["log"]["tracking_error"],
    ("d", "z"): c0["timing_book"]["log"]["z_analytic"],
}
TOL = {"cagr": 1e-4, "h1": 1e-4, "h2": 1e-4, "maxdd": 1e-3, "mean_annual": 1e-4, "te": None, "z": 0.02}

prim = metrics(*book_set(P_HAT))
p()
p("== PRIMARY (opening cost from cash; change-close cost after the mark; A at 1 + 1796/5387) vs the run's JSON ==")
p(f"  {'quantity':16s} {'mine':>12s} {'run':>12s} {'diff':>14s}  tolerance")
all_ok = True
for (book, q), rv in RUNV.items():
    mine = prim[book][q]
    scale = 1.0 if q == "z" else 100.0
    unit = "" if q == "z" else ("pt" if q == "maxdd" else "%")
    tol = TOL[q]
    ok = tol is None or abs(mine - rv) <= tol
    all_ok &= ok
    tol_s = "none set" if tol is None else ("0.02" if q == "z" else ("0.1 pt" if q == "maxdd" else "1 bp/yr"))
    p(f"  {book + ' ' + q:16s} {mine * scale:12.6f} {rv * scale:12.6f} {(mine - rv) * scale:+12.8f}{unit:2s} {tol_s:8s} {'ok' if ok else 'OUT'}")
p(f"  all within tolerance: {all_ok}")
p(f"  final equity S1 {prim['S1']['final']:.8f} (run {c0['rule']['final_equity']:.8f}), A {prim['A']['final']:.8f} "
  f"(run {c0['bar_A']['final_equity']:.8f}), B&H {prim['BH']['final']:.8f} (run {c0['buy_and_hold']['final_equity']:.8f})")
p(f"  cost paid S1 {prim['S1']['cost']:.8f} (run {c0['rule']['cost_paid']:.8f}), A {prim['A']['cost']:.8f} "
  f"(run {c0['bar_A']['cost_paid']:.8f}); financing S1 {prim['S1']['fin']:.8f} (run {c0['rule']['financing_paid']:.8f}), "
  f"A {prim['A']['fin']:.8f} (run {c0['bar_A']['financing_paid']:.8f})")
p(f"  d skew {prim['d']['skew']:.6f} (run {c0['timing_book']['log']['skew']:.6f}), kurt {prim['d']['kurt']:.6f} "
  f"(run {c0['timing_book']['log']['kurt']:.6f}), sum {prim['d']['sum']:.8f} (run {c0['timing_book']['log']['sum']:.8f})")
p(f"  CAGR(S1) - CAGR(A) {100 * (prim['S1']['cagr'] - prim['A']['cagr']):.5f}% "
  f"(run {100 * c0['accrual_residual']['rule_minus_A_cagr']:.5f}%)")

p()
p("== SENSITIVITY: each open convention flipped alone ==")
cases = (("A at the brief's rounded 1.333395", {}, 1.333395, 365.25),
         ("change-close cost booked into that close's mark", {"mark_pre_cost": False}, P_HAT, 365.25),
         ("no opening cost", {"opening_cost": False}, P_HAT, 365.25),
         ("CAGR over days/365 instead of /365.25", {}, P_HAT, 365.0))
for lab, kw, tgt, yl in cases:
    YLEN[0] = yl
    m_ = metrics(*book_set(tgt, **kw))
    YLEN[0] = 365.25
    p(f"  {lab}: CAGR S1 {100 * m_['S1']['cagr']:.4f}% A {100 * m_['A']['cagr']:.4f}% B&H {100 * m_['BH']['cagr']:.4f}%; "
      f"maxDD S1 {100 * m_['S1']['maxdd']:.4f} A {100 * m_['A']['maxdd']:.4f}; h1 S1 {100 * m_['S1']['h1']:.4f}%; "
      f"d mean {100 * m_['d']['mean_annual']:.4f}%/yr TE {100 * m_['d']['te']:.4f}% z {m_['d']['z']:.4f}")

with open(__file__.replace("recompute.py", "recompute.txt"), "w") as fh:
    fh.write("\n".join(OUT) + "\n")
print("\n".join(OUT))
