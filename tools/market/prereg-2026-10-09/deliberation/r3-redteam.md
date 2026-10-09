# r3 · Red Team · SIGN

**SIGN.** None of my deal-breakers is triggered. G5′ deflates d with a paired bootstrap SE, and the Sharpe difference is printed with a paired SE (L178–186, L228). (B) is never gated (L108). Descriptives cannot select, rescue or justify a trade (L234, L315). My Q9 vote carries the same condition as L148, so L148 must be resolved before the freeze.
**Rulings.** G1 at 5 bp: no objection; my ballot dropped it by oversight. It cannot bind WORKS: moving from 2 bp to 5 bp lowers the timing z by 0.37 (overlay-output §15: +4.71 → +3.99%/yr at h = 1), and WORKS needs z ≥ 3.37. It only changes which PARTIAL reasons print. Calendar-day accrual and the single seed: no objection. Harness check 1 already allows the printed residual.
**Thresholds.** Correct to two decimals. The exact values are 3.0311 (N = 40) and 3.3722 (N = 100), from combine.expected_max_sharpe at variance 1 (redteam/r3check-output.txt). edgelab's timing_book applies the exact values.
**Verdict table.** Exhaustive and disjoint, except for correction 1.

**Corrections.**
1. L217, ambiguity. "G4 fails (p ≥ 0.05)" leaves a case in no branch: p < 0.05 with S1 at or below the placebo median in a half. Read: "G4 fails (p ≥ 0.05 at any pair, or S1 at or below the placebo median in either half)".
2. L183/L185, ambiguity. The rounded bars pass z in [3.030, 3.031) and [3.370, 3.372). There Φ(z − E[max Z_N]) is 0.7997 and 0.7994, below 0.80. Write 3.031 and 3.372, or state that the Φ form governs.
3. L171, ambiguity. State the sign: maxDD ≤ 0, as replay.max_drawdown returns it (replay.py:149-155). Read as a positive magnitude, the inequality passes a deeper drawdown.
4. L229, ambiguity. "Within binomial error of its nominal level", read two-sided, makes the run VOID if the placebo is conservative. Read: "rejection rate ≤ nominal + 2 binomial SE".
5. L72 vs L89, inconsistency. The add-back (open + D)/close(t−1) reads the open, and so does edgelab's margin_legs. Add to L72: "except through D/open on the five add-back dates". The effect is ≈ D × the intraday return.
6. L200 vs the harness, two readings. edgelab's g7_inputs sets the timing_log veto flag from z_boot alone. "As in G5′" means z_used = min(z_boot, z_analytic). Name z_used in L200, and the run applies it, not the printed flag.
7. L271–272, errors.
   - Mine: the P(WORKS) model omits G3, G6 and the smaller-z rule (G3 passes 0.88 when intact [DD]). Label 0.165 / 0.032 / 0.572 / 0.120 as upper bounds.
   - The Archivist's 0.05–0.09 is an "at most": prior-weighted P(G5) in Sharpe-difference form at z ≥ 3.05, on its own 12–14 bp/day intact scenarios (estimates_r2.txt:35-45). It is not a 10 bp/day P(WORKS).
8. L279/L282, errors.
   - P(G1 | no effect) = 0.32 is in overlay-output §15, not §18b. With the 5 bp leg it is 0.20.
   - At half size, P(NULL) ≈ 0.5 for a 10 bp/day published size and ≈ 0.3 for 14 bp/day (r3check-output.txt). "More often than not" should read "about half the time or less".

## Addendum · placebo ruling (r3b)
1. **(a) Circular counts as my A, ranked A > shift > blocks, if it holds size.** A's purpose was to place the same leverage once per cycle, keeping each cycle's regime and exposure share. Circular keeps both, and adds what D7 lacked: every session is covered equally, and the real placement is one rotation. I concede D7 as written; the Bench's diagnosis (the start set is not an orbit, and offset 0 sits at the edge) is right.
2. **Condition: the wrap cost.** Wrapped draws add +0.35 sides per cycle on average, not +0.57, because boundary changes are shared between cycles (redteam/r3wrap-output.txt). That is ≈ 8.5 bp/yr at 2 bp, or 0.04 SD of the placebo CAGR, moving the nominal 0.050 size to ≈ 0.055: a bias toward rejection. So circular counts as A only if its size run charges the sides the real run will charge, and L142 says "wrapped draws pay the sides they trade".
3. **(b) If circular fails the limit on any generator, confirm shift** (0.041 / 0.056 / 0.052 in the Bench's run).
4. **L141 wording, if circular stands:** "each cycle's block starts at a uniformly random session of its own cycle and wraps from the cycle's last session to its first, never leaving the cycle."
