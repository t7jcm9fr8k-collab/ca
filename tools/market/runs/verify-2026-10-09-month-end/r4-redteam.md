STANDS — PARTIAL, "below the selection-adjusted bar". The verdict follows mechanically from the printed inputs. None of the passes is an implementation artefact. The fail sits far below the bar on every form of z.

*Red Team, round 4, 2026-10-09. Verification only; the trial is spent. Sources: [V] my independent re-implementation, written without edgelab, `S/edge/redteam/r4/verify.py` → `verify-output.txt`; [R] the run, `runs/edgelab-2026-10-09-month-end.txt`; [P] the frozen PREREG-2026-10-09-month-end.md, whose SHA-256 (85dede81…) matches the one the run printed.*

## 1 · The verdict, branch by branch (P L236–252)
- **VOID? No.** G0 passes on both files: 0 leak differences in 10,774 decisions, the window list reproduced exactly, add-backs as frozen, self-checks 1–4 and 7 within limits, and both SHA-256s match.
- **WORKS? No.** G5′ fails at all six pairs: the smallest z_used is 1.6802, so Φ = 0.3053 < 0.80 (bar 3.0311), and Φ = 0.1976 at N = 100.
- **Branch 3 applies.** G4 passes at every pair: the largest p is 0.0114, and S1 is above the placebo median in both halves at 6 of 6 pairs. The only other gate that fails is G5′, so the only reason printed is "below the selection-adjusted bar".
- **Every other gate clears its bar:** G1 +3.7086% at 2 bp and +2.8976% at 5 bp; G2 +1.9962%; G3 +0.1925; G6 has 257 cycles (129 / 128), trimmed sum +0.2825 and drop-crisis +2.137%; G7′'s smallest z is +0.018, above −1. The crisis spans start at the first sessions on or after the frozen dates (2008-09-02, 2020-02-18).

## 2 · The passes: real, but they rest on the same few crisis sessions
**No implementation artefact.** My re-implementation [V] reproduces the printed figures [R]:

| | printed [R] | independent [V] |
|---|---|---|
| CAGR S1 / (A) / B&H | 16.13 / 12.37 / 10.56% | 16.14 / 12.37 / 10.56% |
| maxDD S1 / (A), with dates | −54.7% (2007-07-19 → 2008-10-27) / −69.0% | the same values and dates |
| d: mean, TE, z i.i.d.; top 5 cycles' share of Σd | +3.305%/yr, 9.04%, 1.689; 0.4206 of 0.7065 | +3.307%/yr, 9.05%, 1.690; 0.4205 of 0.7070 |

**Data.** Closes before 2016 cannot be checked on disk (P L337). Stooq gives SPY +11.69% on 2008-10-28 (the window's first session) and +14.52% on 2008-10-13, and I have no second 2008 source to check them [U]. A 1-point error in a boundary close moves Σd by about 0.01 of 0.707, and no gate is that sensitive.

**G3 is real, but it is not independent evidence.** At S1's own trough (2008-10-27) the books stood at S1 −54.7%, (A) −58.0% and B&H −46.4% [V]. The 14-point margin was built afterwards: the October and November 2008 windows lifted S1 while (A) went on falling to −69.0%. 2008-10-28 at 2× has d +0.065, the largest of any session. Had S1 merely tracked B&H after its trough, it would have bottomed near −63%, which still passes (my arithmetic).

**G4 is real, but it rests on two crises.**
- The printed null distribution (median 11.48%; 5th–95th percentile 8.21–14.81%) implies z ≈ 2.3, which fits p = 0.0112.
- That z exceeds the timing z (1.69) because random placement pays the same drag and costs as S1: the null median sits 0.89 points below (A).
- The design held size with costs charged (P L166, L173), and the identity check is exact.
- But the two crisis spans, 261 sessions or 4.8% of the total, carry 67% of Σd: 2008 gives +0.298 and 2020 gives +0.199, out of +0.707 [V].
- Outside those spans d is +1.13%/yr with z 0.69. Against the null that is ≈ 1.3 (p ≈ 0.09), from the printed drop-crisis margin of +2.18% over a standard error of ≈ 1.6%/yr. That is my estimate, never a gate, but on it G4 would probably have failed without the crises. The six largest sessions alone add +0.28 of the +0.71.

**G6 passes the frozen trimmed sum, but 59% of Σd comes from 5 of 257 cycles:** 2008-10-27, 2008-12-24, 2020-02-24, 2008-11-21 and 2008-09-24 [V]. Applied to d, my withdrawn r1 test ("top 5 ≤ 50%") would have failed; the verdict word would not change.

**G7′ passed only by not vetoing.** On QQQ 1999–2005, z is +0.018 and d is +0.15%/yr: nothing replicated. At 5 bp, the old sign test would have vetoed [R].

## 3 · The fail is not an understatement
- Every form of z lies between 1.68 and 1.93: analytic 1.688, i.i.d. 1.689, bootstrap 1.812, per-cycle 1.876 [V], simple form 1.785 / 1.930, and 1.81 at 1 bp. The Sharpe-difference DSR is 0.29 [R].
- To reach 3.0311 the mean would need to be 1.57–1.80 times larger, or the standard error 0.56–0.64 times its size [V]. Costs, financing (residual −0.017%), the definition of (A) and boundary-close errors each move z by less than 0.15.
- The only lever that flips the result is N: it passes only at N ≤ 2 (N = 3 needs 1.694) [V]. N = 40 is frozen, and the disclosed indirect contamination (P L333–336) argues that N is understated, not overstated.

## 4 · Hindsight: what the rule forbids
- **The 2005–2013 span** (+6.22%/yr, bootstrap z 2.07) is Etula et al.'s own sample, and even it misses 3.03. The only span outside every published sample, 2024-01 → 2026-07, is negative: −2.75%/yr, z −0.6.
- **The FOMC split** (+68.8 against +20.2 bp a cycle) is a 48.6 bp difference with an SE of ≈ 41 bp, from a per-cycle SD of 235 bp [V], on partial dating. It is noise.
- **2008 and 2020:** dropping them leaves +1.13%/yr at z 0.69; keeping them rests the case on a handful of sessions. Neither reaches the bar.
- **"+16.1% against B&H's +10.6%, with a shallower drawdown":** B&H is a headline, never gated. Leverage alone beats it by about 0.5%/yr with no effect (P L21), and the drawdown edge comes from the same late-2008 sessions.
- **p = 0.011 is not selection-adjusted.** Among 40 null trials, at least one would reach it about 36% of the time (1 − 0.989⁴⁰).
- **The rule:** descriptives cannot change or rescue the verdict, nor be cited as a reason to trade (L268). No second specification may chase a better answer (L28, L347). A changed reading rule is a new version, and both versions count (L3). PARTIAL means do not trade; hold SPY as before (L329, L350).
- **Any new idea** — a settlement shift, the FOMC subset, a crisis overlay, another window, TLT, SSO — needs its own pre-registration, tested only on sessions after 2026-08-25. All of SPY's month-end history has now been seen.

## 5 · My forecast, scored
- **Right:**
  - The modal call, "a real but decayed effect prints PARTIAL — below the selection-adjusted bar" (P L315), is exactly what printed.
  - P(WORKS) was at most 0.032 or 0.120, for Brier scores of 0.001 and 0.014.
  - The SE model held: my formula gives z = 3.305·√21.4 / 9.05 = 1.69 against 1.689 printed (TE 9.04% against my 9.05%).
  - The realized effect, about 0.75 of the 10 bp/day size, is where my table gave P(G5) ≈ 0.1.
- **Wrong:**
  - **G4.** I modelled it as the timing z > 1.645 and missed that the placebo nets out drag and costs, worth +0.46 in z. The Archivist was closer (P L326).
  - **G3.** My synthetic gap (−3 points with no skill) cannot produce crisis-timed tails; the realized gap was +14.3.
  - **G6.** My synthetic gave "top 5 ≤ 50%" a 0.88 pass rate with the effect intact; the realized share was 59%.
- **Decay matches the base rate.** The span means fall +6.2 → +2.3 → −2.8%/yr, so the middle span keeps 37% of the first, against McLean–Pontiff's ≈ 42% survival after publication [S].
- **Value to Daniel's ROI: none, by rule.** The overlay's timing is at most a crisis-dependent 1–3%/yr, and it cannot be told apart from selection at N = 40.
