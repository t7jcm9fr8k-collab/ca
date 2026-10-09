```
BALLOT redteam
Q1 S1 window: A
Q2 S1 expression: A
Q3 S2: D
Q4 financing over cash for the extra 1x: primary=1.5%/yr stress=4.0%/yr (financed add-on, no separate expense ratio; (A) borrows its p at the same rate, so the R2 gates, with G5 in log form, move <= 0.04%/yr across the bracket)
Q5 cash values=0%, 1.5%, 3% ; primary=1.5% ; verdict must hold at: all
Q6 cost per side: primary=2bp ; reported/stress=1bp reported, 5bp reported (never a gate)
Q7 G3 compares against: A (tolerance 5 pts; B&H drawdown and every book's -15% STOP count reported, not gated)
Q8 1x long/flat of S1 as a declared descriptive (not a trial, never traded on this run): yes
Q9 placebo: D, provided the size study includes volatility clustering; among designs that hold size, A > B > C
DEAL-BREAKERS: (1) G5 scored as a Sharpe difference with the single-Sharpe variance (edgelab deflated_sharpe_vs default var_sr = 1/(T-1)), which cuts z about 3x; (2) any verdict word for the overlay derived from a comparison with unlevered B&H; (3) any declared-descriptive output allowed to select a spec, rescue a verdict or justify a trade
```

*Red Team, round 2, 2026-10-09. No market data was read. Sources in `S/edge/redteam/`: [O §n] = `overlay-output.txt` (formulas plus an i.i.d. synthetic check); [DD] = `ddnoise-output.txt`, `ddnoise2-output.txt` and [G6] = `g6check-output.txt` (synthetic, 2-state volatility); [C §n] = round-1 `hurdles-output.txt`. Inputs: EVIDENCE.md:517 and 533, the files cited, or labelled assumptions. edgelab is cited by function name, because the Bench is still editing it.*

## 1 · Headline

1. **I concede D1.**
   - Overlay minus constant leverage at 1+p is the timing book (1_W − p)(r − f). 1× long/flat minus a constant p× is the *same* book.
   - So my §3.4 prerequisite ("1× must first beat B&H") tested the equity premium given up while out, not timing.
   - Its purpose was to stop leverage passing as edge. The constant-leverage bar (A) and a same-leverage placebo now do that.
2. **The overlay makes G1 a real timing test, and the failure moves to G5.**
   - The timing book's tracking error is √(p(1−p))σ = 9.05%/yr (synthetic: 9.05%), against 15.7% for 1× vs B&H [O §15–16].
   - P(G1) is 0.32 with no effect and 0.99 with an intact effect.
   - At the voted primary (2 bp/side, G5 in log form, G7′, N = 40, no flip at N = 100), the outcome depends on which "published" size is true [O §18b]:

     | published size | P(G5) at N = 40, if intact | P(WORKS) if intact | prior-weighted P(WORKS) |
     |---|---|---|---|
     | 10 bp/day window gap (Kayacetin) | 0.27 | 0.17 | **0.03** |
     | 14 bp/day (the window carries all of SPY's 2005–26 return; my r1 scale) | 0.70 | 0.57 | **0.12** |

   - **The modal verdict for a real effect at 10 bp is PARTIAL, "below the selection-adjusted bar".**
3. **Cash cancels, provided G5 is computed on the log timing book.**
   - Σ(1_W − p)(f + s) = 0 when p is the realized window share. On synthetic paths the timing book moves ≤ 0.003%/yr across cash 0–3% × spread 1–4% [O §16].
   - Financing accrued by calendar day leaves a residual of about 0.005 × the rate, ≤ 0.04%/yr (r2-quartermaster §3.6). Only the B&H headline moves materially, by about 2 pts/yr.
   - A Sharpe-difference G5 does **not** cancel. Its z moves from 2.12 to 2.27 across the six R4 pairs (intact, 10 bp), lowest at 0% cash [O §18a]. This is one reason I now back G5′ (§3.4).
4. **The harness: one trap, now closed in the Bench's build.**
   - edgelab's `deflated_sharpe_vs` defaults to the variance of a single Sharpe, 1/(T−1).
   - Applied to SR_S1 − SR_A (ρ = 0.943, paired SE 0.073), that default cuts z from 2.17 to 0.74. The trial then cannot pass whatever the truth [O §18c].
   - The Bench found the same defect independently (r2-bench §1b). Its build gates with `dsr_paired`, a paired block bootstrap, and keeps the old function for comparison only. Deal-breaker 1 stays as a guard on the freeze text.
5. **The round is worth about +0.1 to +0.4%/yr in expectation to Daniel's ROI.**
   - That is the prior-weighted P(WORKS) of 0.03–0.12 times an assumed shrunk forward edge of ~3%/yr [O §18b].
   - Its value is mainly information.

## 2 · Answers to the lead's asks

**A1 · Replace §3.4 (text R6).** Every gate compares S1 with (A), financed and charged as S1.
- G1 and G2 have tolerance 0; G3 has 5 pts (§3.2).
- G5′ deflates the log timing book against zero.
- The G4 placebo carries the same leverage.

G3 against unlevered B&H fails an always-≥1× book almost surely: synthetic median drawdown −55% vs −41% [DD].

**A2 · Power against (A).** 2 bp/side, k = 1, G5′ (log), G7′; WORKS also needs z ≥ 3.37, i.e. no flip at N = 100 (r1-redteam.md:541). δ = window-minus-outside mean; h = surviving share [O §15, §18b].

| δ_pub | h | net vs (A) %/yr | z | P(G1) | P(G2) | P(G4) | P(G5′) at N=40 | P(G7′) | P(WORKS) |
|---|---|---|---|---|---|---|---|---|---|
| 10 | 1.00 | +4.71 | 2.41 | 0.99 | 0.91 | 0.78 | 0.27 | 0.99 | 0.165 |
| 10 | 0.69 | +2.97 | 1.52 | 0.94 | 0.74 | 0.45 | 0.07 | 0.96 | 0.031 |
| 10 | 0.38 | +1.24 | 0.63 | 0.74 | 0.45 | 0.16 | 0.01 | 0.90 | 0.003 |
| — | 0 | −0.89 | −0.46 | 0.32 | 0.14 | 0.02 | 0.00 | 0.76 | 0.000 |
| 14 | 1.00 | +6.95 | 3.56 | 1.00 | 0.99 | 0.97 | 0.70 | 1.00 | 0.572 |
| 14 | 0.69 | +4.52 | 2.31 | 0.99 | 0.90 | 0.75 | 0.24 | 0.99 | 0.144 |

- **The overlay makes the timing question testable.** G1 now discriminates.
- **G5 binds at every size.** WORKS becomes more likely than not only above ≈ 1.3× the 10 bp size. G4 falls below one-half near 0.7× it.
- **k = 2 leaves P(WORKS) unchanged** (0.165 and 0.031). It lowers P(G4 | intact) from 0.78 to 0.67 [O §18d].
- **DSR > 0.5 is not an option.** It means a 44% family-wise false-positive rate [C §11].
- **A correction to all three round-2 power estimates, mine included.** The Archivist, Flow and I scored G5 at N = 40 only. WORKS also needs no flip at N = 100, and that cuts intact P(WORKS) at 10 bp from 0.26 to 0.17 [O §18b].

**A3 · Cash (text R4).**
- S1 vs (A), every gate: no binding value; sensitivity ≤ 0.04%/yr.
- S1 vs B&H (headline): binds at the highest cash + spread; about 2 pts/yr.
- 1× long/flat vs B&H (descriptive): binds at 0%; about 2 pts/yr.

The verdict must hold at all values. With G5′ that costs nothing, and R7 tests it.

**A4 · Placebo.**
- `power_study.py` uses i.i.d. normal legs (its docstring). Under those legs every design holds size by construction.
- What separates the designs is regime alignment:
  - **`blocks`** shuffles globally, so a draw can put three windows in 2008-Q4 and none in 2009.
  - **`shift`** keeps each period's exposure share, but is conservative near 21-session offsets.
  - **Within-cycle placement** keeps one block per cycle.
- **Vote D**, once the study adds clustered volatility (as `ddnoise.py` does) and tests overlay CAGR with the leverage carried. Among the designs that hold size: A > B > C.

**A5 · My two defects.**
- **For this round, the harness fix is enough,** provided G5 is G5′ or uses a paired SE.
- **No re-run of the 2026-09-11 runs.** The NULLs needed +0.20 and got +0.02 and +0.03.
  - Excess-of-cash Sharpe shrinks TSMOM's edge.
  - It can raise XSMOM's by only about c·(1/σ_bench − 1/σ_xsmom), a few hundredths. σ_bench is not on file [U].
- **A correction note is owed (R8).** EVIDENCE quotes raw Sharpes of cash-heavy rules as gains: 1.24 vs 0.89 (EVIDENCE.md:640) and 1.23 (EVIDENCE.md:685). These carry about c/(σ√f) of idle-cash interest: ≈ +0.70 at 5% exposure and 3% cash [C §13].

**A6 · Daniel's questions. None changes the frozen spec.**
- **Tax** prices a pass. S1 needs +2.3 to +4.9 pts/yr pre-tax to tie B&H after tax [r1 G-f]. Wash sales [U].
- **Cash location** does not matter: S1 holds no idle cash, and the gates are invariant to it.
- **The STOP can make a pass undeployable.**
  - B&H, (A) and S1 all cross −15% in every big drawdown (B&H −56.5%, EVIDENCE.md:534).
  - A halt inside a window would leave the extra 1× on, because the STOP halts and never liquidates.
  - Deploying a pass under the STOP needs its own pre-registration. Ask Daniel before any money moves.

## 3 · Answers to r2-flow and r2-archivist, and to the late r2-bench and r2-quartermaster

1. **G6: I accept Flow's G6′, amended. Flow was right about r1's wording.**
   - On an always-≥1× book, "the rule's log return minus cash" measures the market's own concentration.
   - Even on the timing book, "top 5 ≤ 50% of the total" behaves badly [G6]:

     | effect strength | "top 5 ≤ 50%" passes | "total minus the 5 best cycles ≥ 0" passes |
     |---|---|---|
     | none | 0.03 | 0.17 |
     | 0.69× | 0.58 | 0.88 |
     | intact | 0.88 | 0.99 |

   - G4 and G5 already guard against luck. G6 should ask whether the result survives without its best cycles, and that is Flow's question.
   - **Amendment:** cycle excess is S1's log growth minus (A)'s over the cycle, so the 0.41%/yr drag is charged, as it is in G1.
2. **G3: I keep 5 pts against (A).**
   - Concentrating the leverage makes S1's drawdown structurally ~3 pts deeper than (A)'s even with no skill. The 5th percentile is −12 pts [DD].
   - Pass rates [DD]: at Flow's 2 pts, 0.44 with no effect and 0.74 intact; at 5 pts, 0.64 and 0.88.
   - A 2-pt tolerance sits below the structural gap and fails a quarter of intact effects. My r1 0.5 pt against B&H is withdrawn.
3. **G7: I concede Flow's G7′: veto only if the QQQ timing book's z < −1.**
   - At 2 bp, the veto rate on a real effect falls from 0.11 to 0.01 (intact) and from 0.39 to 0.10 (0.38×). With no effect it is 0.24, down from 0.61 [O §18e].
   - G5 already holds a single-trial false-positive rate near 0.1%, so the sign veto bought little.
   - The Bench's build reports G7 as the within-cycle placebo's z of CAGR (`run_margin`, `cell["g7"]`), not the timing book's z against (A). The freeze must name one; I accept either at −1.
4. **G5: I checked the arithmetic. The Archivist corrects me, and I change my vote to G5′ in log form.**
   - **The SE.** With daily data the Jobson–Korkie/Memmel variance is [2(1−ρ) + O(SR_daily²)]/T, so SE = 0.073 (r2-archivist §1; the Bench's bootstrap gives 0.0712, r2-bench §1b). My draft applied (1 + SR²/2) to annual Sharpes and got 0.081. Fixed.
   - **The −0.030 concentration penalty checks** (0.53 × (0.943 − 1)). **Their "P(G5) ≈ 0.05–0.09" is prior-weighted;** the intact-case values are 0.32–0.51 (estimates_r2.txt:35, 42).
   - **Flow's z ≈ 2.4 checks.** My log timing-book z is 2.41 at 2 bp; the Sharpe-difference z is 2.17. So P(G5) at N = 40 is 0.27 on Flow's statistic and 0.20 on the Archivist's.
   - **Why I switch.**
     - SR_S1 > SR_A holds only if S1 beats (A) levered up to S1's *volatility* (×1.061), not to its average exposure.
     - That swaps the 0.41%/yr drag for a hurdle of 0.68–0.92%/yr, set by the unobserved cash rate. The −0.030 penalty is that hurdle [O §18a].
     - The team's bar is (A). The log timing book charges the drag exactly once, in Daniel's unit (CAGR), and is invariant to the bracket.
     - Neither form lets a no-effect book through: P(G5) is 0.00 at h = 0 either way [O §18b].
   - **The log form is required.** Arithmetic D_t omits the 0.41%/yr drag, ≈ 0.2 in z.
   - **This meets the Bench's deal-breaker in substance.** A block bootstrap of d resamples the same blocks of S1 and (A), so it is a paired bootstrap; `dsr_paired(d, 0)` computes it. I am not making G5′ a deal-breaker.
   - **If the lead keeps ΔSR** (the Bench's built form), it must hold at all six pairs, so it binds at 0% cash. Intact P(WORKS) at 10 bp is then 0.105, not 0.165 [O §18b]. ΔSR is reported either way.
   - **I accept Flow's relabel:** "PARTIAL — below the selection-adjusted bar" replaces "lucky-sized".
5. **Drag: agreed.** p(1−p)σ²/2 = 0.41%/yr [O §15]. With 0.48%/yr of costs at 2 bp, the break-even gap is δ ≈ 1.6 bp/day, matching Flow.
6. **S2: D (k = 1). D carries 3–2** (Archivist, Bench, Red Team; Flow and Quartermaster vote A).
   - G7 cannot be applied to S2: there is no bond veto file, so S2 would face fewer gates than S1.
   - Hartley–Schwarz's window has a 3–5-day degree of freedom, and TLT (20+ years) lies outside the maturities they report (r2-archivist §2.3).
   - It shares S1's sessions T−2…T, and TLT has its own price-only tail.
   - Pre-register a bond month-end trial later, with a dividend-corrected veto file. It is not a rescue for S1.
7. **R1b, objection (iv): I was wrong.** R1b sells at the open of T−6, so the 2025-06-20 ex-date night is held at 1×. Flow's concessions on opens, the overnight-derived legs and bundling stand.
8. **Overlay verdict mapping (my addition).** For the overlay, "G1–G3 pass, G4 fails" cannot read "exposure or leverage, not timing", because (A) already matches exposure. It should read "beat (A), indistinguishable from random placement".
9. **Bench and Quartermaster r2: I adopt their data and bar texts.**
   - **(A) as the Bench built it** (r2-bench §4): held as shares, reset at every auction where S1 changes exposure, with the same costs. The difference from my cost-free daily-reset bar is second-order (≈ 0.01%/yr, my estimate, not run).
   - **The Bench's scored window, MOC-only orders, closes-only marks, session-index halves** and its definition of CAGR with sessions removed.
   - **The Quartermaster's SPY add-back** of five sourced distributions. It replaces my truncation stress.

## 4 · Critique of round 1 (brief)

**Archivist.**
- Its "+1.0%/yr" (§0.3) priced leverage. Against (A), with its own inputs, it is +0.67%/yr: 0.34 SE of a 21.5-year test [O §17]. r2-archivist now says +0.4–1.3%/yr.
- Its "2014–2026 out-of-sample" is out-of-sample relative to Etula only. Kayacetin's 1994–2023 sample covers most of it, so only 2024-01 → 2026-07 is post-literature. Conceded in r2-archivist §1(b).
- Its §3.1 ranking leaned on practitioner tests of recent SPY. Disclose that fork.

**Flow.**
- Its MOC-up / MOO-down legs came from EVIDENCE §C's in-sample night/day split. Conceded.
- R1b bundled two bets: its tracking error is ≈ 14.4%, against S1's 9.05%.

**Quartermaster.** It corrects my r1 G-g: the stooq files are back-adjusted to their cutoffs.

**Lead v0.**
- No direct post-data choice. Indirectly, the family and window were picked with practitioner looks at recent SPY in view. Disclose this.
- v0 lacks R3 (the price-only tail), R5 (descriptives cannot rescue) and a G3 tolerance.

## 5 · Replacement pre-registration text

**R1 · Bars.**
> - **(A)** is a SPY book at constant exposure equal to S1's mean declared session exposure, 1 + p with p ≈ 0.333, as built in r2-bench §4. It is held as shares and reset at every auction where S1 changes exposure, with the same cash, spread and cost.
> - **(B)** is B&H SPY 1× total return. It is reported, never gated.
> - **(C)** is the R2 placebo.
> - The quantity under test is the log timing book, d_t = ln(1 + R_S1,t) − ln(1 + R_A,t).

**R2 · Gates.**
> - **G0.** R3 and R7 must hold. Otherwise the run is VOID and nothing is printed.
> - **G1.** CAGR(S1) > CAGR(A) at 2 bp a side, at all six (c, s) pairs.
> - **G2.** G1's inequality holds in each half, split at the midpoint session index.
> - **G3.** maxDD(S1) ≥ maxDD(A) − 5 pts.
> - **G4.** The placebo moves each 2× block intact to a random start inside its own cycle (one T−4 close to the next), or uses the Bench design that held size under clustered volatility. It keeps the same leverage, MOC legs, costs and financing, with 10,000 draws and seed 20261009. G4 passes if one-sided p < 0.05/k (Holm) and CAGR(S1) > the placebo median in each half.
> - **G5′.**
>   - z = SR(d)/SE, with SE the 10-session paired circular-block bootstrap SE (5,000 draws, fixed seed; edgelab `dsr_paired(d, 0)`).
>   - The analytic z, SR(d)·√(T−1) with the Bailey–López de Prado skew/kurtosis term, is printed beside it, and the smaller of the two is used.
>   - Pass: Φ(z − E[max Z_N]) ≥ 0.80 at N = 39 + k (z ≥ 3.03 at N = 40).
>   - Recompute at N = 100 (z ≥ 3.37). A flip there makes the verdict PARTIAL.
> - **G6.**
>   - At least 100 cycles, and at least 40 per half.
>   - Cycle excess is the sum of d over the cycle. The total without its 5 largest positive cycles must be ≥ 0.
>   - CAGR(S1) − the placebo-median CAGR must stay > 0 with 2008-09-01 → 2009-06-30 and 2020-02-15 → 2020-04-30 removed, using r2-bench §3's CAGR with sessions removed.
> - **G7′.** For the identical overlay on QQQ-1d-long, 1999-03-10 → 2005-02-24, against its own (A): veto only if its log timing book's z < −1. A replication never rescues a failed gate.
> - **Verdicts.** As in r1 §3.3, with B&H read as (A), except for these labels:
>   - G1 fails: "timing not worth its drag and costs";
>   - G4 passes and G5′ fails: "below the selection-adjusted bar";
>   - G1–G3 pass and G4 fails: "beat (A), indistinguishable from random placement".
> - **Reported, never gated:**
>   - (B), and SR_S1 − SR_A with a paired bootstrap SE, each at all six (c, s) pairs;
>   - maxDD of S1, (A) and (B), and the number of separate −15% drawdowns in each;
>   - results at 1 bp and 5 bp.

**R3 · Data.**
> - **Scored window, orders, marks and halves:** r2-bench §4 verbatim (close of 2005-03-24 → close of 2026-08-25; 257 cycles; 5,387 sessions; MOC only; offsets on the scheduled calendar).
> - **Distributions:** add back SPY's five post-cutoff distributions as in r2-quartermaster §3.1 (`S/edge/data/events/spy-distributions-2025-2026.csv`), on the ex-date's overnight leg, for S1, (A), (B) and the placebo alike.
> - If the add-back is not built, S1's wealth relative to (A) is cut by the Quartermaster's 46.5 bp before every gate.

**R4 · Cash and financing.**
> - **Cash:** c ∈ {0%, 1.5%, 3%}/yr, accrued per session at (1+c)^(1/252) − 1.
> - **Borrowed exposure:** pays c + s, with s ∈ {1.5%, 4%}/yr. No separate expense ratio.
> - **Primary:** (1.5%, 1.5%).
> - G1–G7 must hold at all six pairs. The calendar-day financing residual (r2-quartermaster §3.6) is printed.

**R5 · Descriptives.**
> These are printed after the verdict:
> - the settlement diagnostic in r2-flow §3.3's exact form;
> - 2005–2013, 2014–2023 and 2024-01 → 2026-07;
> - the rsi_dip overlap;
> - the FOMC overlap, where dated;
> - 1× long/flat against (B) and against constant p×.
>
> They cannot change or rescue the verdict, and cannot be cited as a reason to trade. Any hypothesis they suggest needs its own pre-registration on sessions after this run.

**R6 · Leverage (replaces r1 §3.4).**
> S1 holds 1× SPY always, plus a further 1× on window sessions, financed at c + s.
> - It is a timing trial against (A).
> - Unlevered B&H is a headline, never a gate.
> - Other leverage levels, and leveraged-ETF implementations, are separate trials. None is run this round.

**R7 · Harness checks on synthetic data, before SPY is read.**
> 1. Across the six (c, s) pairs on a fixed path, d moves by no more than the printed calendar-day residual.
> 2. d's tracking error is within 5% of √(p(1−p))σ.
> 3. On a synthetic timing book with a known mean, G5′ returns z within 5% of mean·√Y/TE.
> 4. The reported Sharpe difference on a ρ ≈ 0.94 pair uses a paired SE (≈ 0.073 at 21.5 years), not the 1/(T−1) default.
> 5. The placebo holds size under clustered volatility.

**R8 · Note for EVIDENCE.md (no re-run).**
> **Sharpe ratios.** Before 2026-10-09, Sharpe ratios here were computed on raw returns (replay.py:166-176). For rules that sit in cash at 3%, that adds about c/(σ√f), roughly +0.7 at 5% exposure.
> - The Sharpe comparisons of rsi_dip, vol_target, trend_filter and trend_or_dip are therefore overstated.
> - Their verdicts stand.
>
> **2026-09-11 deflated Sharpes.** 0.982 and 0.959 were deflated against zero. The NULLs stand.
>
> **Stooq long files.** They are back-adjusted to cutoffs in 2022–26 (r1-quartermaster §0.2), not unadjusted.
