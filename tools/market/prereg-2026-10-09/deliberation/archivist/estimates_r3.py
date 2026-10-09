"""Archivist round-3 check of PREREG-draft line 282. No market data; same constants as estimates_r2.py.
G4 timing z per bp/day of window gap = 252*p*(1-p)/100 / (sigma*sqrt(p(1-p))/sqrt(years))."""
import math
def Phi(x): return 0.5 * (1 + math.erf(x / math.sqrt(2)))
p, sigma, years = 7/21, 19.2, 21.48
z_per_bp = (252 * p * (1 - p) / 100) / (sigma * math.sqrt(p * (1 - p)) / math.sqrt(years))
out = [f"z_timing per bp/day of gap = {z_per_bp:.4f}  (estimates_r2 §2 check: 3.49 bp -> {3.49*z_per_bp:.2f})"]
for full in (10.0, 14.0):
    half = full / 2
    z = half * z_per_bp
    out.append(f"published {full:.0f} bp/day, half = {half:.1f}: z_timing = {z:.2f}; P(G4 pass, p<0.05 one-sided) = {Phi(z-1.645):.2f}; P(fail) = {1-Phi(z-1.645):.2f}")
open("estimates_r3.txt", "w").write("\n".join(out) + "\n")
print("\n".join(out))
