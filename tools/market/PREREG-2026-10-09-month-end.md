# Pre-registration — the month-end overlay, one specification, 2026-10-09

*Written before any statistic of SPY or QQQ returns conditioned on a month-end window was computed by anyone working on it. Nothing below may change after the run. A changed reading rule is a new version, and both versions count.*

*Inputs: five sub-agents worked two rounds, blind to every rule-conditioned statistic. Every report, script and output they cited is archived under `prereg-2026-10-09/deliberation/`, abbreviated `D/` below. The deliberation record, with the votes, the rulings and the minority positions, is `prereg-2026-10-09/DELIBERATION.md`.*

## Why this, and why in this form

**The ask.** Daniel asked for "something in the market to use … once, maybe twice a day … graded on gains and ROI."

**The family is month-end institutional cash flow.**
- **The proposed mechanism.** Pension funds, insurers and mutual funds sell before the month's last business day to meet payments due on it, and reinvest the cash afterwards. This is Etula, Rinne, Suominen & Vaittinen, "Dash for Cash" (RFS 2020), the mechanism they propose for the turn-of-the-month effect.
- **It is proposed, not established.** It is a deadline rather than a behaviour, but McConnell & Xu (FAJ 2008) found volume and net equity-fund flows no higher at turns of the month (`D/r1-archivist.md` §3.1).
- **There is evidence from 2026 that the *effect* is alive.**
  - Kayacetin (JIFMIM 2026) studies [T−3, T+4] across 30 indices: about 10 bp/day in the window against about 0 outside. He finds the effect decayed after publication and returned, strongest in the U.S. in 2019–2023. He attributes the revival to infrequent rebalancing and risk deferral, a "relief rally", not to payment deadlines. So his paper is evidence that the effect lives, not that this mechanism drives it.
  - Nathan, Suominen & Tasa (2026, working paper) find that the selling trough of momentum-loser stocks moved one session later after settlement went to T+1 on 2024-05-28. They use 19 post-reform months, with data through 2025-12 (`D/r1-archivist.md` §3.1; `D/r2-archivist.md` §2.1).
- Everything else considered is reported dead after publication, cannot be built from the data reachable here, or is weaker (`D/r1-archivist.md` §3.7; `D/r1-flow.md` §0.7; `D/r1-quartermaster.md` §"What this data can and cannot support").

**The form is an overlay, judged against constant leverage.**
- A 1× in-or-out calendar rule cannot beat buy-and-hold SPY on CAGR unless the window holds about 85% of all of SPY's return (`D/r1-redteam.md` §0.2).
- Account ROI rises only through extra exposure placed in the window. "Beats buy-and-hold" then mostly measures the leverage: with no month-end effect at all, the overlay below beats B&H by about +0.5%/yr at the primary financing rate (`D/r2-flow.md` §2.3).
- So the question tested is whether exposure placed in the window earns more than the same average exposure spread evenly. To first order, overlay minus constant leverage is the zero-average-exposure timing book (1_W − p)(r − f) (`D/r2-redteam.md` §1; `D/r2-flow.md` §2.3).
  - It is exact for daily-reset exposures. With shares held between changes it holds to first order.
  - The gates use the realised series d_t defined below, so nothing rests on the approximation.

**The budget is one specification.**
- A second, a TLT month-end overlay, lost 3–2. The minority view is recorded in DELIBERATION.md.
- There is no grid and no variant. Nothing will be added afterwards to chase a better answer.

## Specification S1 — the month-end overlay on SPY

**In edgelab.** S1 is registered as `month_end_overlay`, as `month_window_rule(-3, 3, inside=2.0, outside=1.0, model="margin")`, with nothing else. Registration happens after this file is committed.

**Calendar.**
- T_m is the last session of calendar month m on the *scheduled* NYSE calendar, `barqc.nyse_holidays`.
- The window W_m is the scheduled sessions T_m−3 … T_m+3. That is Etula et al.'s [T−3, T+3], unchanged.
- Bar dates never define T or an offset.

**Exposure.**
- At every close auction, the exposure for the overnight leg into the next *scheduled* session is **2** if that session lies in some W_m, and **1** otherwise.
- An open auction never changes exposure.
- So S1 raises to 2× with a market-on-close (MOC) order at the close of T_m−4, and returns to 1× with an MOC order at the close of T_m+3.
- Both orders are fixed by the calendar alone and can be queued the evening before.

**Closures.**
- A scheduled session with no bar has no auction; the leg into the next bar spans it at the exposure in force.
- A boundary whose scheduled session is an unscheduled closure executes at the close of the next session with a bar. In the scored span this happens once: November 2018's exit, scheduled for 2018-12-05 (a national day of mourning), executes at the close of 2018-12-06.
- Closures inside a window shorten it: 2007-01-02 (December 2006: 6 held sessions); 2012-10-29 and 10-30 (October 2012: 5 held sessions).
- November 2018 also contains a closure (2018-12-05) but keeps 7 held sessions, because its exit rolls to 2018-12-06.

**Instrument.**
- SPY shares in a margin account.
- At 1×, equity is fully in SPY. At 2×, one further unit of equity is borrowed at f = c + s and held in SPY.
- Shares are held between declared changes.
- Financing accrues on the borrowed balance by calendar days, on the overnight leg.
- There is no expense ratio. S1 never holds idle cash.

**The frozen window list.**
- `prereg-2026-10-09/windows-S1-SPY.csv` lists every window's scheduled and executed entry and exit.
- It was built three times, independently: by the Quartermaster (`D/quartermaster/r2/window_spec.py`), the Bench (`D/bench/r2/s1-cycle-dates.txt`) and the lead (`D/lead/windows_check.py`).
- The three agree on all 257 complete windows.
- The file also holds two incomplete windows (2005-02 and 2026-08), marked `complete=False`. Their `exit_exec` holds the scheduled date, not an executed one.
- The harness's declared exposure path must reproduce every `complete=True` row exactly (G0).

## Data, fixed

**File.**
- `tools/market/bars/SPY-1d.csv` (stooq), SHA-256 `52a006deec221ab41c869bd25b279203d3f8d9dedad0bb99ea481164a2cd45a0`, read-only.
- The row dated 2026-09-02 is never read. It is an intraday snapshot: volume 6,128,212 against the official 29,566,220, and close 765.595 against the official 765.16 (`D/r1-quartermaster.md` Conclusions 1).

**Scored span.**
- S1, (A), (B) and every placebo draw enter at the close of **2005-03-24**, the first T−4 whose window lies wholly inside the file.
- The first scored session is 2005-03-28, because 2005-03-25 (Good Friday) was a holiday.
- All are marked to the close of **2026-08-25**, the T−4 of the incomplete August 2026 window.
- That is **257** complete cycles and **5,387** scored sessions (`D/quartermaster/r2/s1-exposure-shares.txt`; `D/bench/r2/s1-cycle-dates.txt`).
- No session of the February 2005 or August 2026 windows is scored.

**Prices.**
- Fills and marks use closes only. Equity is marked at each session's close, and no gate reads an open, the dividend add-back included.
- Opens were found not to be guaranteed opening-auction prints (`D/r1-quartermaster.md` Conclusions 8).

**Dividend basis.**
- The file is back-adjusted, with each adjustment on the ex-date open, through 2025-03-21.
- That was measured twice: `D/r1-quartermaster.md` Conclusions 2, and `D/bench/r2/basis-stooq-vs-nasdaq.txt`, 34 of 34 quarterly ex-dates from 2016-12 to 2025-03.
- After 2025-03-21 the file is price-only. Five SPY distributions fall in that stretch before the span ends.
- From `prereg-2026-10-09/spy-distributions-2025-2026.csv`, which records sources and verification grades, with SSO-vs-2×SPY witness checks in `D/quartermaster/r2/spy-distributions-crosscheck.txt`:

  | ex-date | amount per share |
  |---|---|
  | 2025-06-20 | $1.7611 |
  | 2025-09-19 | $1.8311 |
  | 2025-12-19 | $1.9934 |
  | 2026-03-20 | $1.797 |
  | 2026-06-18 | $1.90352 |

- They are added back in the ex-date's close-to-close return, r_t = (close_t + D) / close(t−1) − 1, for S1, (A), (B) and every placebo draw alike. No open is read.
  - close(t−1) is the previous bar's close. For 2025-06-20 that is 2025-06-18's, because 2025-06-19 (Juneteenth) was a holiday.
  - On each of the five ex-dates and the bar before it, the file's closes equal the official prices to the cent, so the formula gives the total return (`D/r3-quartermaster.md`).
- The rows dated 2025-03-21 (already in the file's adjustment) and 2026-09-18 (after the span) are **not** added.
- All five lie outside every window, at T−6 … T−7.

**Veto file (G7′).**
- `tools/market/bars/QQQ-1d-long.csv`, SHA-256 `4433bdbc019328196c84e610fe5f834aa72097de70a9d3bc2d499a6dfeae790e`.
- Scored from the close of 1999-03-25 to the close of 2005-02-22: 71 complete cycles, 1,485 sessions.
- Window list: `prereg-2026-10-09/windows-G7-QQQ.csv`, built twice and identical on all 71 complete windows. It also holds the incomplete windows 1999-02 and 2005-02, marked `complete=False`.
- 2001-09-11…14, 2004-06-11 and the 1999-11-16 data hole lie outside every window and are spanned at the exposure in force.
- The dividend basis of this span cannot be measured, and is declared so (`D/r2-quartermaster.md` §2.1).

## Benchmarks

**(A) is the bar.**
- A SPY book at constant exposure 1 + p̂.
- p̂ = S1's mean declared session exposure over the scored sessions, minus 1 = 1,796 / 5,387 = **0.3334** (`D/quartermaster/r2/s1-exposure-shares.txt`).
- It borrows p̂ at the same f, is held as shares, and is reset to 1 + p̂ at every close auction where S1 changes exposure.
- It pays the same per-side cost on its reset notional.

**(B) is a headline, never gated.** Buy-and-hold SPY at 1×, total return, over the same sessions, from the same first close.

**(C) is the placebo.** Defined under G4.

**The quantity under test** is the daily log timing book d_t = ln(1 + R_S1,t) − ln(1 + R_A,t).

## Costs, cash and financing

**Costs.**
- **2 bp per side** on traded notional is primary.
- Results at 1 bp and 5 bp are printed, and G1 must also hold at 5 bp.
- S1 trades one unit of equity at each change: 2 sides a window, 24 a year.

**No daily T-bill or cash series was reachable.**
- FRED, the Federal Reserve and home.treasury.gov refused connections.
- nasdaq.com has no bill index, and no dividend history for BIL or SHV (`D/data/cash/probe-log.txt`).
- So every rate below is an assumption, and every gate must hold at every pair.

**Rates.**
- Cash c ∈ {0%, 1.5%, 3%}/yr; spread s ∈ {1.5%, 4%}/yr; borrowing pays f = c + s.
- These six (c, s) pairs are gated. **Primary** is (1.5%, 1.5%).
- One further pair, (0%, 7.75%), is printed for (B) only. It means all borrowing at a flat 7.75%/yr, an unverified retail margin rate.
- Accrual is by calendar days: (1 + rate)^(days/365) − 1, on the overnight leg.
- S1 and (A) hold no idle cash, so c enters only through f.
- The residual from (A)'s session-based p̂ against calendar-day financing is printed. It is about 0.005 × the rate (`D/r2-quartermaster.md` §3.6).

## The null (C): circular within-cycle placement

**Cycles and blocks.**
- A cycle is the run of bars after one executed entry close, up to and including the next executed entry close.
- A block is the run of bars on which S1's exposure differs from its 1× baseline: the 2× window. In the real rule it occupies the start of its cycle.
- A block keeps the number of sessions it actually held (bars): 7 in most cycles; 6 in December 2006; 5 in October 2012; 7 in November 2018, which spans 8 scheduled sessions.

**Each draw.**
- Every cycle's block moves intact to a uniformly random start among all sessions of its own cycle.
- It wraps from the cycle's last session to its first, so it never leaves its cycle. The real placement is one of the cycle's rotations.
- The draw keeps the block's held-bar count, the leverage, the MOC-only changes (made only at closes), the financing and the dividend add-back.
- Costs: a wrapped block is two runs, and it pays the sides it trades.

**Draws and p-value.**
- B = 10,000. The seed is `edgelab --seed 20261009`; the harness derives the placebo and bootstrap streams from it.
- One-sided p = (1 + #{placebo CAGR ≥ S1 CAGR}) / (B + 1).
- In edgelab this is `--placebo within_cycle_circular`. It is named first, which makes it the placebo that gates G4 and G6's drop-crisis median.

**Why this design and not the others.** Three designs were size-tested on synthetic S1-shaped books before any real data: i.i.d., GARCH and regime-switching volatility, R = 1,000 each, B = 200 (`D/bench/r2/size/size-interim2.txt`).

| design | rejection rate at p < 0.05 under no effect: iid / GARCH / regime | verdict |
|---|---|---|
| Linear within-cycle (a draft's design: a block may not wrap) | 0.087 / 0.092 / 0.077 | **failed**, against a limit of 0.064 (nominal + 2 binomial SE) |
| Circular within-cycle (this design) | 0.053 / 0.057 / 0.052, with flat p deciles and sd(z) of 0.98–1.04 | holds |
| `shift` | 0.040 / 0.056 / 0.052 | holds, with lower power |
| `blocks` | 0.038 / 0.044 / 0.036 | holds, with lower power |

- **Why the linear design failed.** Its set of starts is not a group orbit. The real block sits at the cycle's edge, which fewer placements cover, so the observed statistic is over-dispersed against its null (`D/r2-bench.md` Build).
- **Power.** At δ = 40 bp per window, about half the published size, the circular design rejects 0.41–0.51 of the time; shift rejects 0.32–0.40 and blocks 0.33–0.43. At 80 bp per window: 0.89–0.95, against 0.79–0.86 and 0.84–0.93.
- **The Red Team's ruling** (`D/r3-redteam.md`): circular placement counts as its design A, provided it holds size with costs charged.
- **One known bias, stated.** Wrapped draws trade about 0.35 more sides per cycle than S1, which is about 8.5 bp/yr of extra placebo cost at 2 bp. That moves the nominal 5% size to about 5.5%, toward rejection (`D/redteam/r3wrap-output.txt`). The harness size run, which charges those sides, measured 0.052–0.057.

## The reading rule — fixed now, applied without discretion

Every gate compares S1 with (A), and must hold at all six (c, s) pairs unless it says otherwise.

**G0 · Integrity.** If any item fails, the run is VOID and no performance number is printed. A fixed rerun counts as the same trial only if nothing was printed.
- barqc PASS on both files, and both SHA-256s match.
- The SHA-256 of this file is printed.
- The declared exposure paths reproduce every `complete=True` row of the two frozen window lists exactly.
- edgelab's leak check finds 0 differences.
- The dividend add-back is applied exactly to the five dates above.
- The synthetic harness checks below all pass.
- One invocation computes every gate, every pair and every printed stress: the frozen command in `prereg-2026-10-09/invocation.sh`, run verbatim.
- Any deviation from that command makes the run VOID. Exit code 3 is VOID: nothing price-based is computed or printed.

**G1 · Gains.** CAGR(S1) > CAGR(A) at 2 bp a side, and CAGR(S1) ≥ CAGR(A) at 5 bp a side.

**G2 · Stability.**
- CAGR(S1) > CAGR(A) in each half at 2 bp.
- The halves split at the midpoint session index: session 2,694 = 2015-12-07 (`D/bench/r2/s1-cycle-dates.txt`).
- Each half's CAGR comes from the full run's equity at that half's first and last closes.

**G3 · Risk.**
- maxDD(S1) ≥ maxDD(A) − 0.05, on close marks. Drawdowns are signed: ≤ 0, as `replay.max_drawdown` returns them (replay.py:149-155).
- So S1's worst drawdown may be at most 5 percentage points deeper than (A)'s. For example, if (A) falls 60%, S1 must not fall more than 65%.
- Why 5 points: concentrating the leverage alone makes S1's drawdown about 3 points deeper than (A)'s with no timing skill. A 2-point tolerance fails about a quarter of intact effects (`D/redteam/ddnoise2-output.txt`; `D/r2-redteam.md` §3.2).

**G4 · Timing against random placement** (the circular within-cycle placebo, (C)).
G4 passes only if both of these hold at every pair:
- placebo p < 0.05 (with k = 1, Holm is the unadjusted test);
- CAGR(S1) > the placebo median CAGR in each half.

Otherwise G4 fails.

**G5′ · Selection-adjusted timing.**
- z = SR(d) / SE, where SR(d) = mean(d) / sd(d) per session.
- SE is the standard deviation of SR(d) over 5,000 circular-block bootstrap resamples of d: blocks of 10 sessions, from the same `--seed 20261009`.
- Because d is a difference series, each resample takes the same blocks of S1 and (A): the bootstrap is paired.
- The analytic z = SR(d)·√(T−1) / √(1 − γ₃·SR(d) + (γ₄ − 1)/4·SR(d)²), with γ₃ and γ₄ the skewness and kurtosis of d, is printed beside it. **The smaller of the two z is used.**
- Pass: Φ(z − E[max Z_N]) ≥ 0.80 at N = 39 + 1 = **40**. The Φ form governs; it means z ≥ **3.0311** (`D/redteam/r3check-output.txt`).
  - E[max Z_N] = (1 − γ)Φ⁻¹(1 − 1/N) + γΦ⁻¹(1 − 1/(N·e)), with γ = 0.5772 (`combine.expected_max_sharpe`).
- The same z is checked at **N = 100**, where the Φ form means z ≥ **3.3722**. A pass at 40 that fails at 100 makes the verdict PARTIAL.
- The Sharpe-ratio difference SR(S1) − SR(A), on returns in excess of c, with a paired bootstrap SE, is printed at all six pairs and never gated. In effect it benchmarks S1 against (A) levered to S1's volatility, which sets a hurdle the unobservable cash rate would decide (`D/r2-redteam.md` §3.4; `D/redteam/overlay-output.txt` §18a).

**G6 · Breadth.**
- **Cycle counts.** At least 100 cycles in all, and at least 40 in each half. A cycle belongs to the half that holds its entry close.
- **Concentration.**
  - A cycle's excess is the sum of d over the cycle.
  - The total of all cycle excess, after removing the 5 largest positive cycles, must be ≥ 0.
- **Drop-crisis.**
  - Remove 2008-09-01 → 2009-06-30 and 2020-02-15 → 2020-04-30 from S1 and from every placebo draw.
  - CAGR(S1) − the median placebo CAGR, both recomputed on the kept sessions, must stay > 0.
  - "CAGR on kept sessions" means: chain the book's daily returns over the kept sessions, and annualise over the kept share of the scored span's calendar years (`D/r2-bench.md` §3).

**G7′ · Veto replication.**
- The identical rule, on QQQ over the veto span, against its own (A) with its own p̂.
- Veto only if its z_used is below **−1** at 2 bp a side, at any of the six pairs.
- z_used is the smaller of its bootstrap z and its analytic z, computed as in G5′ on its own log timing book.
- Using the smaller z makes a veto easier, which is the conservative direction for a veto. The run applies z_used, never the bootstrap z alone.
- QQQ-1d-long is back-adjusted through 2025-03-24. The veto span ends in 2005, so no add-back applies there.
- A replication never rescues a failed gate. QQQ is never the instrument traded.

**Verdicts (exhaustive).**
1. **VOID**: G0 fails.
2. **WORKS**: G1–G7′ all pass at every pair, with no flip at N = 100. A WORKS rule becomes eligible for a forward paper period. It is not eligible for money (see "What happens next").
3. **G4 passes and any other gate fails: PARTIAL — DO NOT TRADE.** Every failed gate is printed with its reason:

   | failed gate | printed reason |
   |---|---|
   | G1 | "timing not worth its drag and costs" |
   | G2 | "unstable" |
   | G3 | "riskier than (A)" |
   | G5′, or a flip at N = 100 | "below the selection-adjusted bar" |
   | G6 | "concentrated" |
   | G7′ | "did not replicate" |

4. **G4 fails** (p ≥ 0.05 at any pair, or S1 at or below the placebo median in either half):
   - if G1–G3 all pass: PARTIAL — "beat (A), indistinguishable from random placement";
   - otherwise: **NULL**.

## Harness checks, on synthetic data, before SPY is read

These are part of G0. They are run and saved before the real run.

1. Across the six (c, s) pairs, on a fixed synthetic path, Σd over the path moves by no more than the printed calendar-day residual. Each d_t moves by about −(1_W − p̂)·f_t; only the sum is invariant.
2. d's tracking error is within 5% of √(p(1−p))·σ.
3. On a synthetic timing book with a known mean, G5′ returns z within 5% of mean·√years / tracking error.
4. The printed Sharpe difference on a pair correlated at about 0.94 uses the paired SE (about 0.073 over 21.5 years), never the single-Sharpe 1/(T−1) default.
5. The placebo holds size under clustered volatility: its rejection rate is ≤ nominal + 2 binomial SE. A conservative placebo passes. The study is already saved: 0.053 / 0.057 / 0.052 against a limit of 0.064 (`D/bench/r2/size/size-interim2.txt`).
6. The exposure path on the real calendar reproduces every `complete=True` row of both frozen window lists. This reads bar dates only.
7. The placebo evaluator, fed each design's identity arrangement, reproduces S1's CAGR, half CAGRs and drop-crisis CAGR with a difference of 0.0 in every cell (`D/bench/r2/size/identity-check.txt`). This is a permanent test.

## Declared descriptive outputs

These are printed after the verdict. They cannot change it, cannot rescue it, and cannot be cited as a reason to trade. Any hypothesis they suggest needs its own pre-registration, tested on sessions after this run.

1. **The settlement diagnostic** (`D/r2-flow.md` §3.3).
   - Each month gets a settlement lag by its T: 3 if T < 2017-09-05, 2 if T < 2024-05-28, 1 otherwise.
   - It is computed over the scored span.
   - For each lag, print the mean SPY close-to-close return and its SE at offsets T−8 … T+3, with the five added-back ex-dates excluded.
   - Print Δ = mean r(T−3 | s ≤ 2) − mean r(T−3 | s = 3), with its SE. The mechanism predicts Δ < 0.
   - Declared in advance:
     - Its SE (about 15 bp) exceeds the predicted size (6–14 bp), so it cannot confirm or refute.
     - 2017-09 → 2025-12 lies inside Nathan, Suominen & Tasa's sample, so only 2026-01 → 2026-07 is a fresh prediction (`D/r2-archivist.md` §2.1).
2. **Spans.** S1 against (A): d's mean and z over the cycles whose entry close lies in each span.

   | span | windows | status |
   |---|---|---|
   | 2005-03 → 2013-12 | 106 | inside Etula et al.'s sample |
   | 2014-01 → 2023-12 | 120 | after the 2014–15 working papers (RFS 2020), inside Kayacetin's sample |
   | 2024-01 → 2026-07 | 31 | outside every academic sample found; practitioner posts may cover it |

3. **The rsi_dip overlap.**
   - The share of S1's 2× sessions on which `rsi_dip:14,30,5` (strategies.py:208), run on the same file, holds SPY.
   - And d's mean over the 2× sessions it does not hold.
4. **FOMC overlap.**
   - The share of windows containing a scheduled FOMC statement, and the mean cycle excess with and without one.
   - This covers only 2005–2016 (without April 2014) and 2025–2026. The 2025 dates are secondary grade, and 2017–2024 is not dated (`D/r1-quartermaster.md` Conclusions 6; `D/data/events/fomc-statements-2005-2026.csv`).
5. **1× long/flat** (1× SPY inside the window, cash at c otherwise), against (B) and against a constant p̂× SPY book, at every pair.
6. **The headline.**
   - S1 against (B) at every pair and at the (0%, 7.75%) line.
   - Max drawdown of S1, (A) and (B).
   - The count of separate −15% drawdowns in each.
   - The results at 1 bp and 5 bp.
7. **SSO-switch implementation.** For an account without margin: switch 1× SPY into a modelled 2× daily-reset fund for the window and back, which is 4 sides a window. The fund's drag is its expense ratio, 0.88%/yr, plus 1 × (c + 0.6%/yr) of swap financing (`D/r2-archivist.md` §2.4). The 0.6% swap spread is an assumption; the fund's actual spread was not retrieved. In edgelab both enter as `--sso-expense 0.0148`. Cost is 2 bp per side on SPY and 3 bp per side on the fund (assumed). It is a report line, never a gate.

## Stated before the run: what we expect

**Priors.** Each agent wrote its odds down before any data was read.

- **Red Team**, on the final rule (G5′ in log form, no flip at N = 100; `D/redteam/overlay-output.txt` §18b). P(WORKS) at two published sizes of the window gap. These are **upper bounds**: the model omits G3, G6 and the smaller-z rule.

  | published gap | effect intact | prior-weighted |
  |---|---|---|
  | 10 bp/day | 0.165 | **0.032** |
  | 14 bp/day | 0.572 | **0.120** |

- **Archivist:** at most 0.05 and at most 0.09. These are prior-weighted P(G5) alone, in Sharpe-difference form at z ≥ 3.05, with intact gaps of 12.2 and 14 bp/day. They are upper bounds on P(WORKS), not 10 bp/day figures (`D/archivist/estimates_r2.txt` §1–2).
- **Flow Theorist:** a judgement of about 0.03 under the frozen rule, or 0.05 before the N = 100 rule (`D/r2-flow.md` §2.6; `D/r3-flow.md`).

**The most likely outcomes.**
- **A real but decayed effect** most likely prints PARTIAL — "below the selection-adjusted bar".
- **No effect** most likely prints NULL. Even then, S1 beats (A) on CAGR at 2 bp about a third of the time (0.32), and passes G1's 2 bp and 5 bp legs together 0.20 of the time (`D/redteam/overlay-output.txt` §15; `D/redteam/r3check-output.txt`). So G1 alone is never evidence.

**How to read the result.**
- A failed G4 does not show the flow is absent. At half the published size, G4 fails roughly half the time or more:

  | half of | G4 fails |
  |---|---|
  | 10 bp/day | 58–76% |
  | 14 bp/day | 36–55% |

  - The lower figure is the Archivist's, against random placement, where drag and costs cancel (`D/archivist/estimates_r3.txt`).
  - The upper figure is the Red Team's, which nets them out (`D/redteam/r3check-output.txt`). Its P(NULL) is about 0.5 and about 0.3.
  - A G4 failure prints NULL, or PARTIAL if G1–G3 pass.
- PARTIAL means do not trade.

## Known limits and disclosures

- **Indirect contamination.**
  - The family and window were chosen with published and practitioner looks at recent SPY in view.
  - 2014–2023 lies inside Kayacetin's sample. Only 2024-01 → 2026-07 (31 windows) is outside every academic sample found, and practitioner posts on recent SPY may cover it.
  - The team has seen EVIDENCE §C's overnight/intraday split of SPY. S1 is MOC-only and never uses it.
- **Unverifiable before 2016.** Stooq's adjustments before 2016 cannot be checked against an unadjusted reference. Measured against official lists for 2016–2026, stooq missed two payouts: TLT 2023-12-14 and QQQ 2023-12-27. Both are outside this run's scored spans. SPY's record is complete, 34 of 34 (`D/r3-quartermaster.md`).
- **Source grade of the add-backs.** The five SPY amounts are graded V-sec: listing sites quoted in search summaries, cross-checked against an SSO-vs-SPY data witness.
- **Margin is modelled as a frictionless loan.** There are no maintenance calls and no whole-share rounding. Alpaca's `opg` and `cls` orders take whole shares.
- **Half-day boundaries.** 21 window boundaries fall on rule-derived half-days. The backtest fills at the official close, but the MOC cutoff on those days is unverified (`D/r2-quartermaster.md` §2.4).
- **The deflated Sharpe's independence assumption.** It treats the 40 trials as independent and uses this run's T for all of them.

## What happens next, whatever the verdict

**What will be written.**
- The result goes into `EVIDENCE.md` in the same form as every other section: the verdict lines verbatim, the numbers only as printed in the saved files under `runs/`, and one paragraph reading the result against this rule.
- No second specification will be added afterwards to chase a better answer.

**After each verdict.**
- **NULL or PARTIAL:** the honest advice is to hold SPY as before.
- **WORKS:** the rule earns a forward paper period, at least 6 months and 6 windows, graded on implementation fidelity only.

**Before any money moves.** Deployment needs its own pre-registration, because the autopilot's −15% STOP halts without liquidating. A halt inside a window would leave the extra 1× on, and every book here crosses −15% in each large drawdown (`D/r2-redteam.md` §2 A6).

## Trial accounting

- Trials before this run: 39 (`trials.json`).
- Added by this run: **1**. Not a family, not one with variants: one.
- N = 40, with the N = 100 sensitivity.
- The trials.json row is appended in the same commit as this file, before the run.
- The declared descriptive outputs are not trials, because nothing may be selected or traded on them.
