#!/usr/bin/env python3
"""Red Team r3: formula-only checks of the PREREG draft (no market data)."""
import math
from statistics import NormalDist
N01 = NormalDist(); G = 0.5772156649015329
def emax(n): return (1-G)*N01.inv_cdf(1-1/n) + G*N01.inv_cdf(1-1/(n*math.e))
for n in (40, 100):
    thr = emax(n) + N01.inv_cdf(0.8)
    print(f"N={n}: E[maxZ]={emax(n):.4f}; z needed for DSR>=0.80: {thr:.4f}; "
          f"Phi(3.03-E)={N01.cdf(3.03-emax(n)):.4f}; Phi(3.37-E)={N01.cdf(3.37-emax(n)):.4f}")
# P(NULL) at half the published size, analytic model of overlay.py (2 bp, k=1):
# t = timing z; halves t/sqrt2 + x_i; G1: t+e>0 (2bp) and t-0.37+e>0 (5bp); G2: both halves>0;
# G4: t+e>1.645 and both halves>0 (placebo median ~ (A) in this model). G3 not modelled: bounds.
SIG=0.192; P=1/3; YEARS=5413/252
def tz(delta_bp, c_bp=2.0):
    V = P*(1-P)*252*delta_bp/1e4; D = P*(1-P)*SIG**2/2; cost = 24*c_bp/1e4
    return (V-D-cost)*math.sqrt(YEARS)/(math.sqrt(P*(1-P))*SIG)
def pnull(t, p3, step=0.02, lim=7.0):
    th = t/math.sqrt(2); xs=[-lim+i*step for i in range(int(2*lim/step)+1)]
    ws=[N01.pdf(x)*step for x in xs]; g4f=0.0; g4f_g12=0.0
    for x1,w1 in zip(xs,ws):
        for x2,w2 in zip(xs,ws):
            e=(x1+x2)/math.sqrt(2); w=w1*w2
            halves = th+x1>0 and th+x2>0
            g4 = halves and t+e>1.645
            g12 = (t+e>0) and (t-0.37+e>0) and halves
            if not g4:
                g4f += w
                if g12: g4f_g12 += w
    return g4f, g4f - g4f_g12, g4f - g4f_g12*p3
for pub in (10, 14):
    t = tz(pub/2)
    g4f, lo, mid = pnull(t, 0.80)
    print(f"half of {pub} bp/day ({pub/2:.0f} bp): z={t:.2f}; P(G4 fails)={g4f:.2f}; "
          f"P(NULL) >= {lo:.2f} (G3 always passes), ~{mid:.2f} if P(G3)=0.8, <= {g4f:.2f}")
# P(G1 | no effect): 2 bp only vs 2 bp and 5 bp (5 bp lowers z by 24*3bp = 0.72%/yr)
t0 = tz(0.0)
te_y = math.sqrt(P*(1-P))*SIG/math.sqrt(YEARS)
print(f"no effect: z={t0:.2f}; P(G1 at 2 bp)={N01.cdf(t0):.2f}; "
      f"P(G1 at 2 and 5 bp)={N01.cdf(t0 - 0.0072/te_y):.2f} (5 bp shifts z by {-0.0072/te_y:.2f})")
