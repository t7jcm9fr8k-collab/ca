# Bench — Round 1: `edgelab.py`, the harness that will run the test

Scratch root below = `/tmp/claude-0/-home-user-ca/2758dbcb-e96c-587b-81c2-e59b0c402304/scratchpad`. Every number here comes from a file under `<scratch>/edge/bench/`, and each is cited.

## Bottom line

- **Built:** `tools/market/edgelab.py` (the harness) and `tools/market/test_edgelab.py` (168 checks, all pass, offline, about 1 s). The registry holds `buy_and_hold` plus two test-only rules, which are refused on a file unless `--allow-test-rule` is given. **No candidate rule was written or run.** Your snapshot `fdb5945` contains the final versions of both files.
- **Proved correct, not just tested:**
  - The fills match a hand walk in exact fractions to 1e-12.
  - 45 of 46 deliberately planted bugs were caught. The one survivor is an equivalent mutant (explained below).
  - The placebo's false-positive rate is 3.5–4.0% against an exact expected 4.0% (400 synthetic replications).
  - It reproduces **every** number EVIDENCE §C published, including the "halves". Those turn out to be a split at 2016-01-01, not a midpoint.
- **Three data facts the pre-registration must handle:**
  1. **SPY-1d.csv's last bar (2026-09-02) is a partial session.** Its volume is 16% of the usual level, and its close is 765.595 against the official 765.16. → Use `--end 2026-09-01`.
  2. **Dividends land in the overnight leg.** On files that are not total-return (the stooq `-long` files), every ex-dividend price drop shows up as an overnight loss with no dividend credited. That biases exactly the overnight-versus-intraday comparisons this team is likely to propose. → Any rule that holds overnight should be tested on total-return files: SPY-1d.csv, or the Alpaca `X-1d.csv` files for 2020–26.
  3. **The halves convention must be named.** The harness splits at the date midpoint, as instructed; §C split by year.
- **The detectable effect size:**
  - A once-a-month overnight effect over 21 years of SPY-like noise is detected (p < 0.05) about 25% of the time at 5 bp per event, about 60% at 10 bp, and 100% at 20 bp.
  - The deflated Sharpe is much stricter. With 42 trials, a rule must beat buy-and-hold's annualised Sharpe by **+0.48** on 21 years of SPY (**+0.90** on the 6-year Alpaca files) just to reach DSR = 0.5.

## 1. What I built

One file, stdlib only, in the style of the repo. It reuses `bars.load_csv`, `barqc.inspect` (a blocked file is refused), `replay.LookAhead` / `Blocked` / `_stats` / `max_drawdown`, and `combine.expected_max_sharpe`.

- **The session as two legs.**
  - Overnight leg: close[t−1] → open[t]. Its weight is set at the close auction (MOC) of t−1.
  - Intraday leg: open[t] → close[t]. Its weight is set at the open auction (MOO) of t.
  - Scoring is close-to-close: the window opens at a close auction, so every scored session has both legs.
- **The view and its information sets.**
  - At the open auction, the rule sees bars through close[t−1].
  - At the close auction, it sees bars through close[t−1] plus `open_today`.
  - Indexing today's bar, reading `open_today` at the open auction, or reading `close_today`/`high_today`/`low_today`/`volume_today` at either auction raises `LookAhead`.
  - `__slots__` stops a rule from storing state on the view. `view.held` tells the rule the weight of the leg that just ended.
- **The leak check, run on every run.** It re-decides up to 100 random decisions plus up to 200 "the decision changed" points, at both auctions. Each one is re-run on bars truncated to that auction's information set (at a close auction, today's bar holds only its open; high, low, close and volume are NaN), with a fresh rule from the factory and the weight the run actually held. Any difference: the output says "NOT A RESULT" and the CLI exits with code 3.
- **The calendar.** Facts come from barqc's *scheduled* NYSE calendar, never from bar dates:
  - month ordinal from the start and from the end (−1 = last session of the month), sessions in the month;
  - month, quarter and year end;
  - pre-holiday and post-holiday rank (1 = adjacent to a weekday exchange holiday);
  - monthly opex (the third Friday, or the session before it when that Friday is a holiday) and the offset in sessions from it;
  - calendar days of the overnight leg into and out of each session.

  A separate report compares bar dates to the calendar. It separates unscheduled closures from **DATA HOLES** (sessions that traded but are missing from the file), lists overnight legs that span a missing session, and counts how many bars a bar-counted ordinal would have mislabelled, and why. It also flags a possibly partial final bar.
- **Cash.** A constant annual rate, or a dated `date,rate` CSV (refused before its first date, never extrapolated). It accrues by calendar days, all of it on the overnight leg.
- **Leveraged variant** (`--leverage 2|3`, requires `--expense-ratio`). It is labelled **"A MODEL, NOT DATA"**:
  - overnight leg: k·r_on;
  - intraday leg: k·r_id·(1+r_on)/(1+k·r_on), because the fund reset its exposure at the previous close;
  - close-to-close this is exactly k·r_cc;
  - less the expense ratio plus (k−1)×the cash rate, by calendar days on the overnight leg;
  - a 1× buy-and-hold benchmark plus a k× buy-and-hold reference column.
- **Metrics, for the strategy and for buy-and-hold over identical legs.** Total return (ROI), CAGR (calendar years), volatility, Sharpe and Sortino in excess of the cash rate, max drawdown with the peak, trough and recovery dates (marks at every open and every close), legs exposed (all / overnight / intraday), mean and capital-weighted effective exposure, gross and net bp per leg per unit of exposure, sides, round trips, turnover, cost paid, the gross-of-cost path, a per-year table, and halves at the date midpoint.
- **Nulls and statistics.**
  - **Placebo** `shift`: a random circular shift of the session-state sequence.
  - **Placebo** `blocks`: the same exposed blocks and flat gaps, in a shuffled order.
  - With both, the **larger p** is printed as the conservative reading. An exposure with no timing to move is reported as degenerate, with no p.
  - **Deflated Sharpe against buy-and-hold's Sharpe**, with the trial count as an argument.
  - **Stationary bootstrap** of paired session returns: 95% CIs for the CAGR difference and the Sharpe difference.
- **CLI.**
  - Required: `--rule`, `--csv` (one or many files), `--cost-bps-per-side` and `--cash-yield` (there is **no default** for either).
  - Optional: `--symbol/--source/--adjusted` (one for all files or one per file), `--leverage`, `--expense-ratio`, `--start/--end`, `--trials`, `--seed`, `--placebo-draws`, `--placebo shift|blocks|both`, `--boot-draws`, `--block-len`, `--leak-samples`.
  - Outputs and modes: `--out` (text, then JSON), `--curves DIR` (a per-session CSV: weights, leg returns, both equity paths, for auditing which days a rule held), `--list-rules`, `--calendar-report`.
  - With several files, a summary table comes first. A file barqc blocks gets a `BLOCKED` row, never a gap.
  - Exit codes: 0 = ok, 2 = refused or blocked, 3 = the leak check found a difference.
- **Adding a rule after the freeze** takes about five lines under the marked `PRE-REGISTERED RULES` comment:

  ```python
  @register("name_from_prereg", warmup=0)
  def _x(v):
      if v.auction == "close":   # weight for the overnight leg into v.next_cal
          return 1.0 if v.next_cal.month_ordinal_from_end == -1 else 0.0
      return 0.0                 # weight for today's intraday leg
  ```

  A rule must return a weight in [0, 1] of the instrument. Anything else is refused, not clamped.

## 2. Design decisions, and the failure each one prevents

1. **Calendar facts come from the scheduled calendar, never from bar dates.** A bar-counted "last session of the month" is look-ahead: it is known only once the month is over. It is also wrong in the file's final partial month, and a missing bar shifts every ordinal after it. Measured in `V1-calendar-report-all.txt`: on the 21-year stooq files a bar-counted ordinal would mislabel 61 bars counted from the start and 41–43 counted from the end (101 and 55 on QQQ). The causes: 5 unscheduled closures (Ford 2007-01-02, Sandy 2012-10-29/30, Bush 2018-12-05, Carter 2025-01-09), one DATA HOLE (**2011-02-17** in SPY-1d.csv and in the eight stooq ETF files that start in 2005; QQQ-1d-long.csv has that day, and its hole is **1999-11-16** instead), and files that start or end mid-month. A test pins this: with 2026-03-04 missing, March's 5th scheduled session is still 03-06, not 03-09. An unscheduled closure is, correctly, unknown to the rule; the overnight leg across it takes the weight set at the last real close, as it would in reality.
2. **Close-to-close windows, so the benchmark starts at the same close.** The benchmark buys at the same MOC auction at which the rule could first act (after its warm-up) and is scored over the identical legs. This is the warm-up asymmetry EVIDENCE.md documents twice; tests pin it from both directions, including a flat rule with a 30-bar warm-up.
3. **Cost is per side, and stated first in every output.** One `walk()` function does all the accounting, and the rule, the benchmark, the zero-cost path and every placebo draw go through it (crosstest's lesson: a null on a different code path compares two things at once). A fractional weight is rebalanced back to its declared value at every auction, and that rebalance is a trade that pays cost. A 0/1 rule never trades on drift. There is no terminal liquidation cost for either side.
4. **Cash accrues on the overnight leg only** (end-of-day balance, calendar days). A broker pays interest on the end-of-day balance, and a weekend or holiday is part of the overnight leg. The leveraged fund's fees follow the same convention, consistent with a fair value that books each day's accrual by the next NAV.
5. **The leak check compares against an independent probe of the engine.** The leak check re-decides with the *same* number of closed bars the engine used, so an engine that handed the view one bar too many would pass it. A separate probe test therefore asserts that at both auctions the view's last bar is the previous session's bar. Two planted engine bugs (n+1 at the close, n−1 at the open) are caught only by that probe.
6. **The deflated Sharpe uses V = 1/(T−1)** (the sampling variance of one Sharpe estimate under the null), against the benchmark's Sharpe. This is overridable with `--sr-var`. The benchmark's own sampling error is not in the deflated Sharpe; the paired bootstrap carries it.
7. **Refuse rather than guess.** There is no default cost or cash rate. A rate that looks like a percent (5 instead of 0.05) is refused. A leveraged variant without an expense ratio is refused, and so is leverage above 3. Weights out of range, NaN or non-numeric are refused, never clamped. Test-only rules are refused on files. A rule instance (rather than a factory) is refused.

## 3. Tests: `python3 -B test_edgelab.py` → 168 ok, 0 FAIL (`<scratch>/edge/bench/T-test_edgelab-run.txt`)

- **Fill math:** a 4-session hand series whose opens gap away from the previous close, at both auctions, including a 0.5 weight. The final equity and the cost paid match an exact-`Fraction` walk to 1e-12. A drift-rebalance walk with 0.5 held across 6 legs also matches by hand.
- **Per-side cost:** one round trip at 1 bp a side leaves exactly (1−1e-4)². Overnight-only on a flat market loses exactly (1−c)^(2·sessions). The convention string is in the output.
- **Leverage model:** the overnight, intraday and close-to-close identities; three days of drag over a weekend; a 40% gap wipes out the modelled fund and the output says so; "A MODEL, NOT DATA" appears in the output; a missing expense ratio or leverage of 4 is refused.
- **Cash:** across Fri 2026-01-16 → Tue 2026-01-20 (MLK Monday), the overnight legs span 1, 1, 4, 1, 1 days. All-cash from 01-14 to 01-22 equals exactly 1.05^(8/365). Intraday legs accrue nothing. The dated series uses the rate in force at the start of the leg and is refused before its first date.
- **Information sets:** a cheater is caught (`LookAhead`) at the open auction (`open_today`), at the close auction (`close_today`), and by indexing today's bar at either auction. Using today's open at the close auction is allowed and passes the leak check. The engine probe described in §2.5.
- **Leak check:** catches a peek at today's close at the close auction, a peek at today's bar at the open auction, a read of tomorrow's bar, state kept between calls, and a memoised full-series table (caught because the rule is rebuilt for every sample). Clean rules have 0 differences, including one that reads `view.held`.
- **Calendar:**
  - 2020-03-31 is day −1 and a quarter end; 2020-04-30 is a month end but not a quarter end.
  - 2018-03's last session is Thursday 03-29 (its last weekday was Good Friday); 2021-05's is 05-28 (Memorial Day).
  - Opex 2022-04 is **2022-04-14** (Good Friday on the 15th); opex 2026-06 is 06-18 (Juneteenth); opex 2026-09 is 09-18.
  - Pre-holiday and post-holiday ranks around Thanksgiving and MLK day.
  - Known closures are labelled as closures, not holes; ends mid-month and partial final bars are flagged.
- **Placebo:** identical draws under the same seed and different draws under a different seed. The shift keeps every session state. The block placebo keeps the exposed legs of each kind, every block intact, and every gap length. p = (1+hits)/(1+draws) exactly. The conservative reading is the larger p. A timing-free exposure is reported as degenerate.
- **Window:** `buy_and_hold` run as a rule equals the benchmark on every key (return, CAGR, volatility, Sharpe, Sortino, drawdown and its dates, cost, sides). A 30-bar warm-up moves both starts. `--start` and `--end` behave as specified.
- **Deflated Sharpe:** an observed Sharpe equal to the benchmark's plus SR0 gives **0.5 to 1e-12**. With a zero benchmark it equals `combine.deflated_sharpe` to 1e-15. With 1 trial there is no selection penalty. More trials raise the bar.
- **Also covered:** per-year and halves compound to the total; the halves split at the date midpoint (on a window where that differs from the bar midpoint); drawdown is marked at opens (a −20% gap recovered by the close counts); CAGR uses calendar years; Sortino; turnover; the decomposition through the rule path; the bootstrap; the multi-file runner with a BLOCKED row; the CLI refusals; `--out`; `--curves`.
- **Offline, and leaves nothing behind:** socket connections are refused; the bar files and trials.json are unchanged at the end.

**Mutation testing** (`<scratch>/edge/bench/mutate.py`, final run `mut/mutation-round4-final.txt`): **46 planted bugs, 45 caught.** The one survivor ("store `open_today` at the open auction") is an equivalent mutant: the engine passes `None` there and the property raises anyway. Rounds 1–2 found four real gaps in my own tests (halves at the bar midpoint, drawdown ignoring the open marks, quarter end on a non-quarter month end, the exact (1+hits)/(1+draws) p), and each is now pinned. I added the engine probe and the `held` check on my own initiative; their mutants are caught only by those checks.

**The existing suite** still passes with these files present: `test_tools.py` 646 ok (`dev/test_tools-run.txt`), and a before/after snapshot of the repo shows no file changed (`dev/snap-before.txt`, `dev/snap-after.txt`).

## 4. Validation on real data (the only runs made)

**V1, bar dates against the calendar, all 21 bar files** (`V1-calendar-report-all.txt`). All files pass barqc. SPY-sessions.csv is not a bar file and was excluded.

**V2, buy-and-hold on every file** (`V2-buy-and-hold-all.txt`; command in `V2-command.sh`; 1 bp/side, cash 0).
- On all 21 files the strategy equals the benchmark exactly, the leak check finds 0 differences, and the bootstrap CI is [0, 0].
- SPY 2005-02-25 → 2026-09-02: CAGR +10.25%, Sharpe 0.61 (EVIDENCE: 0.61), max drawdown −56.7%. EVIDENCE says −56.5%; the difference is the marks. On closes only it is −56.47%; with the opens included, −56.70% (`V3-spy-decomposition.txt`).

**V3, the SPY decomposition** (`V3-spy-decomposition.txt`, script `validate_spy.py`). Close 2005-02-25 → close 2026-09-02, 5,412 sessions, no cost, no cash:

| | measured | EVIDENCE §C |
|---|---|---|
| close→open compounds | **+367.3885%** | +367% |
| open→close compounds | **+74.8258%** | +75% |
| whole | **+717.1158%** (C_last/C_first − 1 = +717.115784%) | +717% |
| mean per night / per day | +3.105 bp / +1.462 bp | +3.1 / +1.5 |
| Sharpe overnight / intraday | 0.691 / 0.250 | 0.69 / 0.25 |
| halves, 2005–2015 \| 2016–2026 (`V3b-spy-halves-hypothesis.txt`) | overnight +82.02% / +156.78%; intraday +2.20% / +71.06% | +82%/+157%; +2%/+71% |

- **Through the rule path** (`decide_all` + `walk`, cost 0): test_overnight_only, test_intraday_only and buy_and_hold equal the direct products to within 0, 0 and 3.55e-15.
- **Explaining the differences:**
  - **The halves.** At the date midpoint (2015-11-29) the halves are overnight +80.54%/+158.89% and intraday +5.28%/+66.06%; at the bar midpoint they are similar. Neither matches §C. I tested exactly one hypothesis, the year split EVIDENCE uses elsewhere, and it reproduces §C to the rounding. So §C's "both halves" was 2005–2015 | 2016–2026.
  - **The start.** §C started at the first *close*. Starting at the first open would give a whole of +725.04%.
  - **The partial bar.** §C included the partial final bar. Without it: overnight +366.98%, intraday +74.11%, whole +713.04%.
- **Data checks:**
  - Stooq applies its dividend adjustment to opens and closes alike: the median |f_open/f_close − 1| over 1,551 dates shared with SPY-1d-raw.csv is 1.32e-6. So the leg split on this adjusted file is sound.
  - The final bar is partial: stooq has close 765.595 and volume 6,128,212; nasdaq has the official close 765.16 and volume 29,566,220.
  - Five overnight legs in the window span a session with no bar: 2007-01-03, 2011-02-18 (a DATA HOLE), 2012-10-31, 2018-12-06, 2025-01-10.

**V4, a full-size run** (SPY buy-and-hold, 1,000 placebo draws × 2 methods + 1,000 bootstrap draws): **14.7 s per 21-year file** (`V4-time.txt`, `V4-spy-buy-and-hold-fullsize.txt`). At 3% cash, buy-and-hold's Sharpe in excess of cash is 0.45.

## 5. Size and power of the placebo (synthetic bars only, `power/SUMMARY.txt`)

The setup:
- i.i.d. legs on the real calendar for 2005–2026, with overnight sd 71.3 bp and intraday sd 95.2 bp, derived from §C's published means and Sharpes;
- an effect of δ bp injected into the overnight leg into the first session of each month (259 events);
- a synthetic-only probe rule that holds exactly those legs, at 1 bp/side, with 99 draws.

Results (share of runs with p < 0.05; with 99 draws the exact rate under no effect is 4.0%):

| δ per event | reps | shift CAGR / Sharpe | blocks CAGR / Sharpe |
|---|---|---|---|
| 0 bp (size) | 400 | 0.040 / 0.035 | 0.037 / 0.035 |
| 5 bp | 100 | 0.250 / 0.270 | 0.230 / 0.240 |
| 10 bp | 100 | 0.640 / 0.650 | 0.620 / 0.590 |
| 20 bp | 100 | 1.000 / 1.000 | 1.000 / 1.000 |

- The size is right, and the power tracks a textbook z-test.
- I suspected the shift placebo would lose power on monthly rules (shifts of about 21 sessions land near the true phase). It did not show at these effect sizes.
- Not tested: volatility clustering, which real data has.

**Deflated Sharpe thresholds** (`dsr-thresholds.txt`): the annualised Sharpe a rule must add on top of buy-and-hold's just to reach DSR = 0.5, at the default V:

| file span | N = 40 | N = 42 | N = 45 |
|---|---|---|---|
| 21 years | +0.473 | +0.477 | +0.482 |
| 6-year Alpaca | +0.887 | +0.895 | +0.906 |

## 6. What the pre-registration has to state (the harness's knobs)

- **File and window.**
  - SPY-1d.csv with `--end 2026-09-01`.
  - Total-return files for any rule that holds overnight. The stooq `-long` files are unadjusted (DATA.md §2, and the run's own DIVIDENDS line).
  - Alpaca files: their open and close are IEX prints, not the primary-market auction prices that MOO and MOC orders get.
- **Costs and rates.**
  - `--cost-bps-per-side`: one number for both auctions. A leveraged ETF's spread is wider than SPY's, so state a separate, higher cost for any leveraged variant.
  - `--cash-yield`: what the account will actually earn. No dated series is on disk.
  - `--leverage` / `--expense-ratio`, if a leveraged variant is pre-registered.
- **Trial count.** `--trials N`: 39 before this round, plus every specification frozen now. The harness writes nothing to the ledger; each run needs a trials.json row citing its saved output.
- **The nulls.** Which placebo counts (or "the larger p"). The number of draws (1000). The seed (0). `--block-len` (default 20).
- **The halves convention:** the date midpoint (the harness) or a year split (as §C did).
- **The reading rule.** Every number the reading rule needs is in the JSON. A `read()` function in the style of crosstest can be added in a few lines once the Red Team fixes the rule.

## 7. Known limitations (honest)

- **Scope:** daily bars only; one instrument per run, so there is no cross-asset signal; long only. Half-day sessions and their 12:50 MOC cutoff are not marked.
- **Not modelled:** auction imbalance, slippage beyond the per-side cost, partial fills, taxes, T+1 settlement and cash-account good-faith rules. Also the **pattern-day-trader rule**, which every intraday-only round trip counts against.
- **The calendar:** it is barqc's rules, so an unscheduled closure announced days in advance (a mourning day) is still unknown to the rule. The pre-holiday flag uses scheduled weekday holidays only.
- **The leak check:**
  - It samples (100 random decisions plus up to 200 change points), so it could miss a leak that fires rarely.
  - No leak check can catch a rule that reads its own copy of the data from a global; that needs code review. The registry starts empty, which keeps that review small.
- **The leveraged model:** no tracking error, no swap spread, and it uses the underlying's bars rather than the fund's own. Its drag sits on the overnight leg, so an intraday-only leveraged holder pays no drag. That matches the end-of-day convention, but it is optimistic if the market prices intraday accrual.
- **The deflated Sharpe** treats the benchmark's Sharpe as known and the trials as independent, and uses the current T for all trials.
- **The placebo** was size-tested only on i.i.d. synthetic data. The final-bar heuristic also flags GLD-1d.csv (47%; 2026-09-04 is the Friday before Labor Day), which is probably a false positive. I did not tune the threshold after seeing that.
- **Annualisation:** the Sharpe uses √252; CAGR uses calendar years.

## 8. Commands (from `tools/market`)

```bash
python3 -B test_edgelab.py                                   # 168 checks
python3 -B edgelab.py --list-rules
python3 -B edgelab.py --calendar-report --csv bars/SPY-1d.csv
bash <scratch>/edge/bench/V2-command.sh                      # buy-and-hold, all 21 files
python3 -B <scratch>/edge/bench/validate_spy.py <scratch>/edge/bench/V3-spy-decomposition.txt
python3 -B <scratch>/edge/bench/validate_spy_halves.py <scratch>/edge/bench/V3b-spy-halves-hypothesis.txt
bash <scratch>/edge/bench/V4-command.sh                      # full-size timing
python3 -B <scratch>/edge/bench/mutate.py                    # 46 mutants in temporary copies; touches nothing in the repo
python3 -B <scratch>/edge/bench/power_study.py OUT SEED_BASE REPS DRAWS DELTA_BP...   # synthetic only
# a frozen rule (illustrative flags):
python3 -B edgelab.py --rule NAME --csv bars/SPY-1d.csv --source stooq --adjusted yes --end 2026-09-01 \
  --cost-bps-per-side C --cash-yield Y --trials N --seed 0 --placebo-draws 1000 --placebo both \
  --boot-draws 1000 --out runs/NAME.txt --curves runs/curves
```

## 9. Files

**Repo** (no other repo file touched; I ran only read-only git — `status`, `log`, `diff`, `show` — and never add/commit/push/checkout/reset/stash):
- `tools/market/edgelab.py`
- `tools/market/test_edgelab.py`

**Scratch** (`<scratch>/edge/bench/`):
- `T-test_edgelab-run.txt` — the test run
- `V1-calendar-report-all.txt`
- `V2-buy-and-hold-all.txt`, `V2-command.sh`
- `V3-spy-decomposition.txt`, `V3b-spy-halves-hypothesis.txt`
- `V4-spy-buy-and-hold-fullsize.txt`, `V4-time.txt`
- `dsr-thresholds.txt`
- `power/` (`SUMMARY.txt` plus the json files)
- `mut/mutation-round1..4*.txt`
- `dev/` — `example-synthetic-report.txt` (a full leveraged report on synthetic bars), the `test_tools` run and the repo snapshots
- the scripts: `validate_spy.py`, `validate_spy_halves.py`, `mutate.py`, `power_study.py`, `example_synthetic.py`
