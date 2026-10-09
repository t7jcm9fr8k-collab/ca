"""Exact variance arithmetic behind the linear within-cycle over-rejection (iid unit returns).
A cycle of L sessions, a block of b, linear starts u = 0..L-b. S_u = sum of the block at u; the null
centre is the mean of S_u over u. Compare Var(S_0 - centre) (the real block at the cycle's edge)
with the average over u of Var(S_u - centre) (a random placement)."""
from fractions import Fraction as F
from statistics import NormalDist
L, b = 21, 7
U = L - b + 1
c = [sum(1 for u in range(U) if u <= i < u + b) for i in range(L)]       # coverage of session i
var_mean = F(sum(x * x for x in c), U * U)
cov = lambda u: F(sum(c[i] for i in range(u, u + b)), U)
var_dev = lambda u: b - 2 * cov(u) + var_mean
avg = sum(var_dev(u) for u in range(U)) / U
ratio = (float(var_dev(0)) / float(avg)) ** 0.5
print(f"coverage by session: {c}")
print(f"Var(S_0 - centre) = {float(var_dev(0)):.4f}; mean over u of Var(S_u - centre) = {float(avg):.4f}")
print(f"sd ratio = {ratio:.4f}; one-sided rejection at a nominal 5% = P(Z > 1.6449 / ratio) = "
      f"{1 - NormalDist().cdf(1.6448536 / ratio):.4f}")
print("circular (u = 0..L-1, wrapping): every session covered", b, "times, so the ratio is exactly 1")
