```
BALLOT bench
Q1 S1 window: A
Q2 S1 expression: A
Q3 S2: D
Q4 financing over cash for the extra 1x: primary=1.0%/yr stress=3.0%/yr
Q5 cash values=0%,1.5%,3% ; primary=1.5% ; verdict must hold at: all
Q6 cost per side: primary=2bp ; reported/stress=1bp,5bp
Q7 G3 compares against: A
Q8 1x long/flat of S1 as a declared descriptive (not a trial, never traded on this run): yes
Q9 placebo: D
DEAL-BREAKERS: G5 computed with any SE other than the paired bootstrap SE of ΔSR — my own round-1 form included
```

*Bench, round 2. `S` = `/tmp/claude-0/-home-user-ca/2758dbcb-e96c-587b-81c2-e59b0c402304/scratchpad`. New evidence is in `S/edge/bench/r2/`. All of it is synthetic data, price-ratio basis checks, or dates; nothing conditions a return on a window, an event or a rule.*

## 1 · The two conflicts, resolved

### (a) The stooq basis: the Quartermaster stands, and my round-1 claim is withdrawn

- **What I claimed.** In round 1 I wrote that the stooq `-long` files "are unadjusted". I cited DATA.md §2 and my own DIVIDENDS line, but that line only echoes the `--adjusted no` flag I passed. It was second-hand.
- **What I measured now.** An independent re-implementation (`r2/basis_check.py` → `r2/basis-stooq-vs-nasdaq.txt`). It uses price ratios against nasdaq official prices, 2016-10 → 2026-09; a "step" is a persistent change of more than 4 bp in ln(stooq/official close).
  - **TLT:** 117 adjustment steps, the first on 2016-11-01, the last on **2026-04-01**. **115 are "post"**: the open already sits on the new basis, so the payout is credited to the ex-date's overnight leg. After 2026-04-01 the gap is 0.00 bp.
  - **SPY:** 34 steps, 34 post, last on **2025-03-21**. The open-basis median is 0.05 bp.
  - **The others:** QQQ 2025-03-24, XLE 2025-12-22, EEM 2024-12-17, DIA 2022-10-21, IWM 2022-09-26, XLF 2022-09-19, EFA 2022-06-09.
  - **GLD:** zero steps. It is the control.
  - **Every cutoff equals r1-quartermaster §Conclusions-2.** The median TLT gap is −2,587 bp in 2016, falling to −333 bp in 2025 and 0.0 in 2026.
- **The finding.** These files are total-return until a symbol-specific cutoff and price-only after it.
- **Consequences.**
  - My round-1 V2 numbers do not move; the flag never enters a calculation. But the DIVIDENDS text printed for the nine long files was wrong.
  - The harness's single `adjusted` boolean cannot state a cutoff. The build adds `--total-return-through DATE`.
- **For S1.** Inside the scored window, five SPY ex-dates fall after the cutoff, on the quarterly expirations at T−6…T−8: 2025-06-20, 2025-09-19, 2025-12-19, 2026-03-20 and 2026-06-18 (brief §2).
  - On those nights the overlay holds 1× while bar (A) holds (1+p)×. (A) therefore eats p × the artificial drop more than the rule does.
  - With p ≈ 0.33 and the located SPY steps of 30–59 bp (r1-quartermaster §5), that is **0.5–1.0% cumulative in S1's favour**, about 0.05%/yr. This is small but signed; the replacement text in §4 states it.

### (b) The deflated Sharpe: the Red Team's paired form should gate, and mine should not

- **The two forms differ only in the SE that standardises ΔSR.**
  - Mine used SE(one Sharpe) = √(1/(T−1)) and treated the benchmark's Sharpe as known.
  - The variance of a difference of two equal-variance estimates with correlation ρ is 2(1−ρ) times that of one estimate. So my form is right only at ρ ≈ 0.5.
- **On synthetic data** (`r2/dsr_se_demo.py` → `r2/dsr-se-demo.txt`):
  - SPY-like returns, i.i.d. and GARCH; the real 2005–26 calendar; W = T−3…T+3; cash 1.5%; financing cash + 1%.
  - Paired circular-block bootstrap, block 10, 5,000 resamples.
  - The last two columns are the ΔSR (annualised) needed at N = 42.

| pair | corr | SE(ΔSR) paired | × round-1 SE | for DSR = 0.5 | for DSR = 0.8 |
|---|---|---|---|---|---|
| overlay vs constant (1+p)× | 0.943 | 0.0712 | **0.33** | +0.157 | +0.217 |
| 1× long/flat vs B&H | 0.578 | 0.1934 | 0.90 | +0.427 | +0.590 |
| B&H vs an independent series | −0.008 | 0.3163 | **1.47** | +0.699 | +0.965 |
| round-1 form (any pair) | — | 0.2157 | 1.00 | +0.476 | +0.658 |

- **GARCH gives the same ratios:** 0.33, 0.89 and 1.46. The GARCH(1,1) parameters are ω 2.88e-6, α 0.08, β 0.90, giving an unconditional 1.20%/day; they are assumptions, stated in the script.
- **What this means.** My round-1 "+0.48 bar" was 3× too strict for S1's comparison, and would be about 1.5× too lenient for an uncorrelated rule. The paired SE is also the only one of the two that carries the benchmark's own sampling error.
- **It is built** (Build §B1). The round-1 function stays in the code for comparison only and is never printed as a gate.

## 2 · What the harness expresses, per proposal (after this round's build)

**v0 / S1 — SPY 2× month-end overlay, MOC→MOC.**
- **Faithful:**
  - the exposure path 1× / 2×, decided from the scheduled calendar at the MOC auctions of T−4 and T+3;
  - the extra unit financed at cash + spread by calendar days, with no expense ratio;
  - cost on declared changes;
  - bar (A) at the realised mean exposure;
  - the within-cycle placebo at the same leverage;
  - the paired deflated Sharpe;
  - halves by session index;
  - the G6 inputs;
  - all stresses in one invocation.
- **Independent of the opens.** With shares held between changes and closes-only marks, the result never touches an opening price. That matters, because opens are not guaranteed to be auction prints (r1-quartermaster §8). This is pinned by a test that perturbs every open.
- **Approximate:**
  - cash and financing are constant brackets, not T-bills;
  - margin is a frictionless loan: no maintenance calls and no whole-share rounding. Alpaca's `opg`/`cls` orders need whole shares (r1-archivist §4.5);
  - the price-only stretch after 2025-03-21 (§1a);
  - **2018-12-05**, the Bush day of mourning, is the scheduled exit T+3 of November 2018 (`r2/s1-cycle-dates.txt`). Unless the rule is MOC-only, the harness would exit at the 2018-12-06 *open*. §4 fixes this.
- **Cannot:** an SSO version on the fund's real NAV before 2016-10; fills that differ from the official close; the half-day MOC cutoffs.

**R1b — Flow's 0× sidestep then 2×, settlement-adjusted.**
- **Expressible:** the 0/1/2 levels, MOO and MOC legs, and the settlement eras by date.
- **Approximate, and decisively so:**
  - its MOO legs are priced at vendor opens;
  - the 2025-06-20 ex-date sits at T−6, inside W−, on the price-only stretch. The sidestep would be credited with a payout-sized drop that never happened, and no dividend amounts are on disk to correct it (brief §2).
- **The placebo.** R1b's block is the composite "0× then 2×" deviation from the 1× baseline, moved intact.
- **Cannot:** tell the sidestep's contribution from the overlay's inside one trial.

**TLT S2.**
- **Expressible as a TLT-only account:** TLT 1× plus the month-end overlay, against TLT at constant leverage and TLT B&H, on closes.
  - Stooq TLT is total-return through 2026-04-01 (verified above).
  - Its T+1 ex-dates after the cutoff fall in baseline legs, the same signed bias as S1.
- **Cannot:** "Daniel's SPY account plus a TLT overlay". The harness is single-instrument, and a two-asset account is out of reach. TLT also answers a different account question from Daniel's.

## 3 · Critique, from the instrument's side

**r1-quartermaster.**
- **The basis finding is right and better than mine (§1a).**
- **Their calendar and mine agree** on all 7,052 scheduled sessions 1999–2026: ordinals from start and end, month length, quarter and year ends, and all 336 expirations (`r2/calendar-crosscheck.txt`). Two independent builds, three differences:
  - post-holiday adjacency next to the 2007-01-02 closure: mine is scheduled, theirs actual;
  - 2026-12-31: theirs ends with 2026, so it cannot see the 2027-01-01 holiday.
- **Their §8 on opens is why I now recommend closes-only marks for S1.**
- **They found two things my tooling missed:**
  - SPY-1d-agg is not dividend-adjusted. My V2 passed `--adjusted yes` for it, per README; only that file's DIVIDENDS line was wrong.
  - The 2026-04-20 placeholder bar (O=H=L=C, volume 0) passes barqc, because zero volume is report-only. The build adds a flat-zero-volume-bar flag to the calendar report.

**r1-archivist.**
- **The spec (§2) is exactly expressible.**
- **"Money statistic (a) via SSO's 0.88% expense" is a different instrument from v0's margin** (no expense). The two have nearly the same variance drag to second order (their §4.2 is right), but different fees.
  - The freeze must name one.
  - The coordinator's "SSO-switch" line is now a descriptive (Build §B5).
- **"Drop the incomplete final window" needs a date, not a phrase.** Brief §1.6's "→ 2026-09-01" and "drop the August window" conflict, because August's entry is at the close of 2026-08-25. §4 gives the dates.

**r1-flow.**
- **§3 asked me to confirm that the opens carry the closes' adjustment factor.** Confirmed for SPY on 2016–26: all 34 steps sit on the open, and the open-basis median is 0.05 bp.
- **The §2 convention (raise at MOC, cut at the next MOO) is expressible, but it makes the P&L depend on vendor opens**, and the Red Team's contamination point stands. For S1, MOC→MOC is the only fully close-priced form.
- **"SPY-1d.csv … dividend-adjusted" should read "through 2025-03-21".**
- **I agree with Flow §0.3 that CAGR vs B&H is the wrong bar for 2× variants.** Bar (A) and the within-cycle placebo at the same leverage are now built.

**r1-redteam.**
- **§3.5 is right** (§1b), and is built.
- **D7 needs one clarification for an overlay.** An "exposure block" must be a run of sessions that *deviate from the rule's baseline exposure* (1× for S1), not a run of nonzero exposure. Otherwise every session of an always-≥1× book counts as "exposed" and the placebo is degenerate.
  - My round-1 `shift`/`blocks` placebos had exactly this flaw.
  - The build takes the baseline from the rule.
- **G6's drop-crisis test needs a defined "CAGR with sessions removed".**
  - The build uses: chain the book's daily returns over the kept sessions, and annualise over the kept share of the window's years.
  - The freeze should adopt this text or replace it.
- **G1's "actual T-bill" is infeasible** (brief §2), so the cash bracket replaces it.
- **G-c's adverse 3 bp on open fills cannot bite S1.** S1 has no open fills except the 2018-12-06 case if left unfixed.
- **D5:** built as `--halves session`.
  - Three conventions now exist on record: EVIDENCE §C's year split at 2016-01-01 (reproduced in round 1), my round-1 date midpoint, and D5's session index.
  - For S1's scored window the session midpoint is 2015-12-07 and the date midpoint 2015-12-09.

**Q3, my vote for D (k = 1).**
- Holm at k = 2 halves S1's G4 threshold to p < 0.025, at a power that is already the binding limit (brief §1.4). The Build's power table shows what this costs.
- TLT shares S1's month-end mechanism, so it is not an independent witness.
- It cannot be measured as part of Daniel's SPY account.
- If k = 2 anyway, TLT is the only S2 the harness prices on closes alone.

**Q4 and Q5.** Against bar (A), cash and spread enter both books on the same average borrowing, so they nearly cancel. Requiring the verdict at every cash value therefore costs little and closes the "assumption chose the verdict" door. The Build quantifies the residual.

## 4 · Replacement text for v0 (pre-registration wording)

*Two of these paragraphs are superseded by the Build:*
- *the Placebo paragraph, by circular placement (B4, B6 item 1), because the linear design below does not hold size;*
- *the G5 paragraph, by the draft's G5′, which I sign (B6 item 2).*

> **Scored window.** From the close of 2005-03-24 (the T−4 entry of the first window lying wholly inside `bars/SPY-1d.csv`) to the close of 2026-08-25 (the last T−4 before the incomplete August 2026 window): 257 complete cycles, 5,387 sessions. The 2026-09-02 bar is never read.

> **Orders.** MOC only. At every close auction, exposure for the overnight leg into the next *scheduled* session is 2 if that session is T−3 … T+3 of its month, else 1. At every open auction, exposure is unchanged. If a scheduled entry or exit session is an unscheduled closure, the change happens at the next actual close. In this window that is once: November 2018 exits at the close of 2018-12-06, because 2018-12-05 was closed.

> **Instrument.** SPY itself, held as shares between declared changes (the margin-account convention). Borrowed (e−1)⁺ is financed at cash + spread, accrued by calendar days on the overnight leg. No expense ratio.

> **Bar (A).** Constant exposure equal to the rule's mean declared session exposure over the scored sessions. Same cash, spread and cost. Held as shares, and reset to target at every auction where the rule changes exposure.

> **Placebo (G4).** Within-cycle placement (r1-redteam D7). A cycle runs from one scheduled T−4 close to the next. The 7-session 2× block is moved intact to a uniformly random start inside its own cycle and never crosses the cycle's end. B = 10,000; seed 20261009 + spec index; p = (1 + #{placebo CAGR ≥ rule CAGR}) / (B + 1). Same leverage, cost, cash and financing.

> **G5.** DSR = Φ(ΔSR / SE − E[max Z_N]).
> - ΔSR = SR(rule) − SR(bar A), on daily returns in excess of cash, annualised √252.
> - SE = the standard deviation of ΔSR over 5,000 paired circular-block bootstrap resamples, block length 10 sessions, seed fixed.
> - N = 39 + k; sensitivity at N = 100.

> **Marks and halves.** All statistics use equity at each session's close; opens are never read. Halves split at the midpoint session index (session 2,694 = 2015-12-07).

> **Known bias, stated in advance.** Five post-cutoff SPY ex-dates (2025-06-20 … 2026-06-18) fall in baseline legs. Price-only data charges bar (A) p × each payout more than the rule: at most about 1.0% cumulative in S1's favour. The verdict must hold without that margin.

## Build

*Everything below is synthetic or dates-only. No rule is registered. No bar file was read for a price; the window lists, the distributions file and the FOMC dates were read as dates and amounts. `B` = `S/edge/bench/`. Files: `tools/market/edgelab.py` (3,951 lines) and `test_edgelab.py` (1,538 lines), SHA-256s in `B/r2/build-hashes.txt`. Not committed by me.*

### B1 · What was built

| # | Piece | Where (edgelab.py) | CLI |
|---|---|---|---|
| 1 | Paired deflated Sharpe: ΔSR on returns in excess of cash, against a named benchmark; paired circular-block bootstrap SE (block 10, 5,000, seeded); E[max Z_N] at N and at 100. Round 1's form is printed beside it, never gated. Also used by the weight-model `run()` | `dsr_paired`, `block_sharpes`, `paired_block_se` | `--trials --trials-sensitivity --dsr-benchmark constant\|buy_and_hold --dsr-draws --dsr-block` |
| 2 | Margin overlay: e ∈ [0, 2]; borrowed (e−1)⁺ at cash + a REQUIRED spread; idle at cash; per-side cost on traded notional. **Drift convention:** shares held between declared changes, trade = \|e − drifted exposure\| × equity | `margin_legs`, `margin_walk` (closed-form segments, O(changes) per walk) | `--spread`, lists |
| 3 | Bar (A) at the rule's mean declared exposure, held as shares, reset (forced) at every auction where the rule trades, same costs. Reported beside it: B&H 1×, the 1× long/flat line, a constant-p̂ 1× book, and the SSO-switch line | `constant_changes`, `run_margin` | — |
| 4 | Placebos: `within_cycle` (the draft's text), `within_cycle_circular` (new, exact), `shift`, `blocks` (both baseline-aware). p = (1 + #null ≥ obs)/(B + 1); null medians per half and with crises removed; z; percentile | `WithinCycle(wrap=)`, `ShiftPlacebo`, `BlocksPlacebo`, `run_placebo` | `--placebo` (the first named gates) |
| 5 | Halves at the midpoint session index or the date midpoint. EVIDENCE §C's halves were a 2016-01-01 year split, which is neither | `split_halves` | `--halves session\|date` |
| 6 | One invocation: costs × cash × spreads grid (the first value of each is primary) plus `--cell` extras. **G0 first, for both files:** barqc, leak check (`--leak-samples all` = every decision), information sets, calendar, declared basis, total-return benchmark, file SHA-256 vs expected, frozen window list reproduced, add-backs as frozen, self-checks 1–4, pre-registration SHA-256. A failure means VOID: nothing that depends on a price is computed or printed, exit 3 | `integrity_check`, `declared_windows`, `check_window_list`, `total_return_status`, `harness_selfcheck` | `--expect-sha256 --window-list --expect-addbacks --prereg --selfcheck` |
| 7 | G6: episodes (runs < 5 sessions apart merge) overall and per half; cycles per half by entry close; four concentration forms (r1 top-5 share; Flow's formula; the book's simple and log per-cycle excess with the 5 largest POSITIVE cycles removed); drop-crisis CAGR minus the gating placebo's median | `g6_inputs`, `ProbeSet` | `--crisis` |
| A | SSO-switch line: 4 sides a window, fund drag = expense + (k−1)·cash, its own cost per side | `sso_switch_path` | `--sso-k --sso-expense --sso-cost-bps-per-side` |
| B | G6 in Red Team's and Flow's forms, plus the Red Team's amendment (log book) | as 7 | — |
| C | Offset profile: offsets × groups, count and SE, exclusions (`addbacks` = the applied dates), one declared contrast, labelled "cannot confirm or refute" | `offset_profile` | `--offset-profile --offsets= --group-labels --group-breaks --exclude-dates --contrast=` |
| D | G7: placebo z, and the timing-book z (z_used, as G5′), each under "same sign" and "z < −1", computed on the replication file in the same invocation | `g7_inputs`, `render_veto` | `--veto-csv --veto-start-close --veto-end --veto-expect-sha256 --veto-window-list …` |

**Added for the draft:**
- **G5′ log timing book.** z_boot, z_analytic (Bailey–López de Prado skew/kurtosis), z_used = min, and Φ(z − E[max Z_N]) at N = 40 and 100. Built as `timing_book`.
- **Close-based add-back.** `--closes-only`: each session is one close-to-close step, so no open is read. The run refuses a rule that trades at an open auction.
- **Distributions.** Loaded with their SHA-256 and placed by `place_distributions`: payouts on or before the cutoff are skipped, and an ex-date in the window with no bar fails G0.
- **Accrual.** `--accrual calendar|session`. The other convention's CAGR(S1) − CAGR(A) is printed per cell as the residual, with p̂ also weighted by calendar days.
- **Declared descriptives:**
  - spans of cycles by entry close;
  - overlap with a repo strategy (`--overlap-strategy`, via replay.py);
  - event windows (`--event-*`).

### B2 · Tests

`test_edgelab.py`: **251 checks, all pass**, offline (`B/r2/test-run.txt`). 82 of them are in the new round-2 block, all synthetic:
- **Margin engine.** The margin walk matches an exact Fraction step-walk at every leg boundary, and on a random path to 1e-12.
- **Calendar windows.** The scheduled-calendar windows for Dec 2006, Oct 2012 and Nov 2018 match the frozen list's rows (6, 5 and 7 sessions; exit at the close of 2018-12-06).
- **Open independence.** With `--closes-only`, moving every open leaves every number bit-identical.
- **The coordinator's decisive test.** It is pinned twice:
  - every design's identity arrangement is the rule's change list;
  - each placebo's observed CAGR equals the rule's own, in every cell.
- **Placebo coverage.** Circular placement covers every session 7/21 of the time. Linear placement covers the edge 1/15 against 7/15 in the middle.
- **Bootstrap.** The block bootstrap equals resampling by hand, including the wrap and the short last block.
- **G5′ thresholds.** The bars z ≥ 3.03 (N = 40) and 3.37 (N = 100) are pinned.
- **Integrity.** VOID prints no performance number. The prereg SHA-256 is printed. A wrong add-back list makes the run VOID; a wrong file hash or an undeclared replication basis exits 3 from the command line.

### B3 · Mutation score

`B/mutate2.py` → `B/mut/round2-mutation-all.txt`:
- **Round 2: 48 planted bugs, 48 caught.** The first pass missed 4, and each now has a test:
  - the placebo p without its +1 (it only survived when all nulls beat the rule);
  - the second half's CAGR measured from 1;
  - episodes merging at a gap of exactly 5;
  - run_placebo's observed CAGR walked at a different cost.
- **Round 1, re-pointed at the refactored code: 45 of 46.** The survivor is the same equivalent mutant as in round 1 (r1-bench).

### B4 · Size and power (synthetic; `B/r2/size/size-power.txt`)

**Setup.**
- Built by `size_study.py`, through edgelab's own code.
- The real scheduled calendar, scored from the close of 2005-03-24 to the close of 2026-08-25: 5,387 sessions, 257 cycles, p̂ = 1.333395.
- 2 bp, cash 1.5%, spread 1.5%, B = 200 draws per replication. δ = bp per window.
- The generators are stated in the script:
  - iid;
  - GARCH(1,1) with ω 2.88e-6, α 0.08, β 0.90;
  - two-state regime with sd 0.85% / 2.6% a day, stressed share 0.2.

Cells give the rejection rate at p < 0.05 (binomial SE). Size holds if the δ = 0 row is ≤ 0.064, i.e. 0.05 + 2 SE at R = 1,000.

| δ | gen | WC linear (draft) | **WC circular** | shift | blocks |
|---|---|---|---|---|---|
| 0 | iid | **0.087** (0.009) | 0.053 (0.007) | 0.040 (0.006) | 0.038 (0.006) |
| 0 | GARCH | **0.092** (0.009) | 0.057 (0.007) | 0.056 (0.007) | 0.044 (0.006) |
| 0 | regime | **0.077** (0.008) | 0.052 (0.007) | 0.052 (0.007) | 0.036 (0.006) |
| 10 | iid / GARCH / regime | 0.16 / 0.18 / 0.16 | 0.11 / 0.11 / 0.12 | 0.09 / 0.11 / 0.08 | 0.06 / 0.09 / 0.07 |
| 20 | iid / GARCH / regime | 0.29 / 0.24 / 0.23 | 0.24 / 0.18 / 0.17 | 0.17 / 0.15 / 0.12 | 0.18 / 0.13 / 0.12 |
| 40 | iid / GARCH / regime | 0.56 / 0.53 / 0.49 | 0.51 / 0.48 / 0.41 | 0.40 / 0.39 / 0.32 | 0.43 / 0.40 / 0.33 |
| 80 | iid / GARCH / regime | 0.98 / 0.95 / 0.91 | 0.95 / 0.92 / 0.89 | 0.86 / 0.85 / 0.79 | 0.93 / 0.90 / 0.84 |

**Linear within-cycle placement is not an exact randomization test.**
- It is not an evaluator bug: the identity arrangements reproduce the observed CAGR to 0.0 in 144 cells (`size/identity-check.txt`).
- The real block sits at its cycle's edge, which linear placements cover least. So the observed statistic is over-dispersed against its null: sd(z) is 1.17 / 1.25 / 1.22, and the p-values are U-shaped.
- Theory for a 7-of-21 block gives an sd ratio of 1.194, hence a rejection rate of 0.084 (`size/edge-theory.txt`).
- A harness-free check gives 0.088 linear against 0.059 circular (`size/edge-check.txt`).

**Circular placement holds size, has flat p deciles, and is the most powerful design that holds.**

### B5 · Run time at B = 10,000

The draft's single invocation (`B/r2/runtime/frozen-invocation-template.txt`), run on synthetic files carrying the real files' dates (`runtime/time_frozen.py`), took **273 s on one core** (`runtime/run-B10000.txt.time`). It covered:
- 19 cells, with the placebo at 10,000 draws in each;
- three 5,000-resample bootstraps per cell;
- every one of the 10,774 decisions leak-checked;
- self-checks 1–4;
- the QQQ replication;
- the descriptives and the offset profile.

Its G0 reproduced all 257 S1 and 71 QQQ windows of the Quartermaster's frozen lists. Its synthetic outputs check against three earlier figures:
- **Calendar-weighted p̂** is 1.338446 against 1.333395 by session, matching r2-quartermaster §3.6's 0.3384 / 0.3334.
- **The settlement contrast's SE** is 15.2 bp, matching Flow's "about 15".
- **Window counts** are 106 / 120 / 31, matching the draft's table.

Also measured on that synthetic path (`runtime/bar-a-variants.txt`):
- (A) as built beats the Archivist's daily-reset, cost-free (A) by +2.7 to +3.5 bp/yr across the six pairs. Holding shares avoids daily-reset decay, so the bar as built is the slightly harder one.
- Across the six pairs, d's annual mean moves at most 3.07 bp/yr; the printed calendar-day residuals reach 3.84 bp/yr (self-check 1).

### B6 · Reply to `lead/PREREG-draft.md`

**SIGN, conditional on item 1.** Without item 1, DISSENT: the placebo as written does not hold size.

1. **(C) fails size as written; circular placement holds** (B4).
   - Replace the placement sentence with: "Every cycle's block moves intact to a uniformly random start among all sessions of its own cycle, wrapping from the cycle's end to its start, so it never leaves its cycle."
   - Replace "length in scheduled sessions" with "length in the sessions it held (bars)". The two differ only for Dec 2006, Oct 2012, Nov 2018 (7 bars over 8 scheduled sessions) and draws that cover the 2011-02-17 hole.
   - The flag is `--placebo within_cycle_circular`.
2. **G5′: I agree it meets my deal-breaker.** Resampling d's blocks resamples the same blocks of S1 and (A), and ρ enters through var(d). Built as specified, and the 3.03 and 3.37 bars are pinned.
3. **"seed 20261009" should read `edgelab --seed 20261009`.** The harness derives named streams from it: `edgelab/20261009/within_cycle_circular` for G4, and `…/dsr-paired` for every block bootstrap. Every pair reuses the same draws.
4. **G7′: "z as in G5′" is z_used, the smaller z.** That makes a veto easier, so say so. The cost is unstated: I print every cell, and suggest "at 2 bp, at any of the six pairs".
5. **The add-back is built as the close form** (`--closes-only`). On the Quartermaster's file (SHA-256 780a360f…), exactly the five dates apply; 2025-03-21 and 2026-09-18 are skipped (`B/r2/addback-placement.txt`). With it, "opens are never read" is literal for every number; barqc and the leak check still load each bar whole.
6. **Harness checks.** 1–4 are `--selfcheck` items: check 1, |Δ mean d| ≤ the two residuals + 0.1 bp/yr; checks 2 and 3, ±5% (check 3 with 20 bp a session injected); check 4, SE within 15% of √(2(1−ρ)) single-Sharpe SEs. Check 5 is B4; check 6 is `--window-list` / `--veto-window-list`.
7. **Residual.** Printed per pair as CAGR(S1) − CAGR(A) under calendar accrual minus the same under per-session accrual, with the calendar-weighted p̂ beside it.
8. **G6 halves.** On the S1 dates, 129 / 128 cycles fall in the two halves by entry close. A cycle whose entry close is the split close is ambiguous; none exists in S1, because 2015-12-07 is not a T−4.
9. **The draft leaves these unstated; my choices are in `B/r2/runtime/frozen-invocation-template.txt`:** QQQ's basis cutoff, 2025-03-24; spans by cycle entry close; rsi_dip "holds" means after that session's open fill; FOMC "contains" means a scheduled statement date among the held sessions; the settlement diagnostic runs over the scored span.

