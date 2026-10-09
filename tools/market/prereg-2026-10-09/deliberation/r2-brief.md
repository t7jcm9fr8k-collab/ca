# Round 2 brief — cross-critique and votes

*From the lead, 2026-10-09 ~05:20Z. `S` = `/tmp/claude-0/-home-user-ca/2758dbcb-e96c-587b-81c2-e59b0c402304/scratchpad`. Read this brief first, then the other round-1 reports: `S/edge/r1-quartermaster.md`, `r1-archivist.md`, `r1-flow.md`, `r1-redteam.md`. `r1-bench.md` is still being written; I will forward its findings.*

## 0 · Rules for this round (unchanged)

- **Still blind.** Nobody computes a return, volatility or any other statistic conditioned on a candidate window, event or rule, from any real bar file.
  - Allowed: data checks that do not condition on a rule — barqc, basis comparisons, calendars, dividend placement.
  - The Bench tests on synthetic data only.
- **No broker calls.** No network fetches except the Quartermaster's: low volume, through `tools/market/fetch.py` or `nasdaq_json.py`, and never around a bot check (a Yahoo 429 means stop).
- **Nothing written** under `tools/market/bars/`. You commit nothing; the lead does.
- **Every number comes from a file**, repo or `S/edge/`, and you cite it. Otherwise label it an assumption.

## 1 · Settled unless you object, with a reason

1. **The family is month-end institutional cash flow** (Etula et al. 2020 "dash for cash"; turn of the month).
   - Everything else was ruled out as dead, infeasible on our data, or weaker.
   - The event families cannot be built: FOMC 2017–2024, CPI after 2005 and every jobs report are missing (r1-quartermaster §4).
2. **A 1× long/flat calendar rule will almost surely trail buy-and-hold (B&H) SPY on CAGR.** The window would need to hold about 85% of all of SPY's return (r1-redteam §0.2; r1-archivist §0.3; r1-flow §0.2).
3. **Account ROI rises only through extra exposure inside the window, which is leverage.**
   - "Beats B&H" then mostly measures the leverage (r1-flow §0.3).
   - The honest bars are constant leverage at the same average exposure, and a within-cycle placebo that carries the same leverage.
4. **Power is the binding limit.** A half-size effect reads null about half the time, so a NULL does not show the flow is absent.
5. **Budget: k ≤ 2.** N = 39 + k, with a sensitivity check at N = 100.
6. **Data for S1: `bars/SPY-1d.csv` (stooq), 2005-02-25 → 2026-09-01.**
   - Total-return through 2025-03-21; price-only after that.
   - Drop the mid-session 2026-09-02 bar, and with it the August 2026 window, whose T+3 would be 2026-09-03.
   - Closes are dependable. Opens are not guaranteed to be the opening-auction print (r1-quartermaster §8).
   - Veto replication: QQQ 1999-03-10 → 2005-02-24.
7. **The Red Team's two defects get fixed in the new harness**, not patched into old runs:
   - the deflated Sharpe is centred on zero;
   - Sharpe is computed on raw returns.

## 2 · Facts that arrived after your round-1 report

- **No T-bill series is reachable.**
  - FRED and the Fed answer 403.
  - I probed `home.treasury.gov`'s daily bill-rate CSV at 05:10Z: CONNECT 403.
  - nasdaq.com's dividend endpoint returns no rows for SPY (not a Nasdaq listing).
  - So every cash and financing rate is an assumption and must be bracketed.
- **I think the missing T-bill rate argues for the overlay framing. Check this:**
  - For a 1× long/flat rule judged against B&H, idle cash earns the assumed rate on about two-thirds of days. A 0%-vs-3% bracket should then move the result by roughly 2 pts/yr, which is wider than the effect being sought.
  - For an overlay judged against constant leverage at the same average exposure, both sides pay financing on the same average borrowing. The rate should then largely cancel.
- **SPY's ex-dividend dates after the stooq cutoff land outside [T−3, T+3].**
  - They are the quarterly-expiration sessions. Positions from `S/edge/data/calendar/nyse-sessions-1999-2026.csv`, where `ord_from_end` −1 = T:

    | date | position |
    |---|---|
    | 2025-06-20 | T−6 |
    | 2025-09-19 | T−7 |
    | 2025-12-19 | T−7 |
    | 2026-03-20 | T−7 |
    | 2026-06-18 | T−7 |
    | 2026-09-18 | T−8 |

  - Over all 336 expirations, 1999–2026, the latest position is T−4. No expiration ever falls in T−3 … T+3.
  - **This does hurt R1b.** 2025-06-20 sits at T−6, inside R1b's T+1-era selling window W− = T−6…T−2, on the price-only stretch of the file. The sidestep would be credited with one artificial, payout-sized drop.
- **The Bench has not reported yet.**
  - It is running a synthetic size and power study of two placebo designs, `shift` and `blocks`.
  - The committed `tools/market/edgelab.py` models a k× instrument as k × the daily return − (k−1) × cash − expense ratio, held at a weight in [0, 1] of one instrument.
  - It cannot yet express "1× SPY always, plus a financed 1× inside the window".

## 3 · The open disputes

**D1 · Leverage.**
- **The two positions:**
  - r1-redteam §3.4: "no leverage variant this round unless a 1× version of the same signal has already passed."
  - r1-archivist §0.3 and r1-flow §5: only an overlay can add ROI.
- **My reading: these are two different questions.**
  - "Does the 1× long/flat rule beat B&H?" asks whether timing is worth more than the equity premium given up while out. Everyone predicts no.
  - "Does the 2× overlay beat constant leverage at the same average exposure?" asks whether exposure placed in the window earns more than the same exposure spread evenly. That is a pure timing question, and it is the one Daniel's metric needs.
- **The algebra.**
  - Write r for SPY's daily return, f for the financing rate, 1_W for the window indicator, and p = mean(1_W).
  - The overlay's exposure is 1 + 1_W(t); the constant-leverage book holds 1 + p.
  - Ignoring costs: overlay − constant leverage = (1_W(t) − p)(r_t − f_t). That is a timing book with zero average exposure.
  - In log terms the overlay also carries slightly more variance drag, which works against it.
- **So a 1× pass is not a logical prerequisite for the overlay's timing value.** Requiring one makes the only test relevant to Daniel's ROI unreachable.

**D2 · Window.**
- **The options:**
  - (a) Etula's fixed [T−3, T+3]: MOC at the close of T−4, MOC at the close of T+3 (r1-archivist §2);
  - (b) Flow's settlement-adjusted R1b: a 0× sidestep over W−, then 2× from the close of T−(s+1) to the open of T+4 (r1-flow §3);
  - (c) Kayacetin's [T−3, T+4].
- **My straw: (a) as the trial**, with Flow's settlement shift reported as a declared descriptive diagnostic. Flow already proposed that diagnostic as descriptive. My objections to (b):
  - (i) It exits at the open, and opens are unreliable (r1-quartermaster §8).
  - (ii) It adds an overnight leg chosen after the team has already seen SPY's overnight/intraday split (r1-redteam §0.2, "contaminated").
  - (iii) It bundles two signals, the sidestep and the overlay, into one trial, so a pass could not say which one worked.
  - (iv) It has the ex-date contamination in §2.

**D3 · Second trial.** The options:
- (i) Treasury end-of-month (Hartley–Schwarz) on TLT, as an overlay, over the last three sessions, close of T−3 → close of T.
  - Stooq TLT is total-return through 2026-04-01.
  - TLT goes ex on T+1, outside that window (r1-quartermaster §7).
  - It overlaps S1 in time, so the two are not independent witnesses (r1-archivist §1).
- (ii) R1b as a second trial;
- (iii) Kayacetin's window;
- (iv) none, k = 1.

**D4 · Financing and instrument for 2×.**
- **The instrument.** Synthetic: SPY plus 1× borrowed at cash + spread.
- **The spread.** Flow assumed +1.0%/yr, labelled as an assumption. A retail margin rate is higher, and I have no verified figure.
- **Real-NAV check.** SSO exists on disk only from 2016-10 (nasdaq), so there is no 2008 check against a real product's NAV.
- **Decide:**
  - a primary spread and a stress spread;
  - whether to model an expense ratio;
  - whether the verdict must hold at both spreads.

**D5 · Cash.** Choose between a 0% / 3% bracket (3% is the repo convention) and 0% / 1.5% / 3%. Say which is primary, and whether the verdict must hold at every value.

**D6 · Costs.**
- 1 bp a side, for auction fills (r1-archivist; r1-flow), or 2 bp primary (r1-redteam D4).
- 5 bp a side as the stress.

**D7 · Reading rule for an overlay.** G0–G7 were written for a long/flat rule against B&H. For the overlay:
- Do G1, G2 and G5 compare against constant leverage at the realized average exposure, with the same financing, cost and cash?
- What does G3 compare against? The options:
  - constant leverage, which is fair;
  - unlevered B&H (r1-redteam §3.4), which an always-≥1× overlay will almost surely fail;
  - both.
- Is the count of −15% STOP crossings a gate, or only a report?

**D8 · Placebo.** The candidates are the Red Team's within-cycle placement (D7) and the Bench's `shift` and `blocks`. I will forward the Bench's size study; vote conditionally on it.

## 4 · Lead's straw proposal v0 — break it

**S1 (trial 40): SPY month-end overlay.**
- **Window and orders.**
  - T is the last scheduled NYSE session of the month (barqc calendar).
  - Exposure is 2× from the close of T−4 to the close of T+3, covering sessions T−3 … T+3, and 1× at all other times.
  - Both changes are MOC orders, decided from the calendar alone.
- **Instrument.** The extra 1× is financed at cash + spread, as margin, with no expense ratio.
- **Cash and cost.** Cash and financing per D4/D5. Costs: 2 bp a side primary; 1 bp and 5 bp reported.
- **Benchmarks.**
  - (A) constant leverage at the realized average exposure: **the bar**;
  - (B) B&H SPY 1× total return: reported, as Daniel's headline;
  - (C) within-cycle placebo at the same leverage.
- **Gates.** The Red Team's G0–G7, re-pointed at (A) wherever they compare with B&H. G3 is measured against (A); B&H's drawdown and the number of −15% crossings are reported.
- **Declared descriptive outputs, never used to choose anything:**
  - the settlement diagnostic (r1-flow §3 R1);
  - 2005–2013 against 2014–2026;
  - the post-T+1 era (about 28 month-ends);
  - the share of window days inside an active `rsi_dip` hold (r1-archivist §2);
  - the 1× long/flat version of the same window.

**S2 (trial 41): open — your vote.**

## 5 · Your deliverable: `S/edge/r2-<role>.md`

Open the file with this block, filled in exactly; I tally it mechanically:

```
BALLOT <role>
Q1 S1 window: A=Etula[T-3,T+3] MOC->MOC | B=R1b settlement-adjusted | C=Kayacetin[T-3,T+4] | D=other(say)
Q2 S1 expression: A=2x overlay vs constant leverage | B=1x long/flat vs B&H | C=both, counted as 2 trials | D=other
Q3 S2: A=TLT month-end overlay | B=R1b | C=Kayacetin | D=none (k=1) | E=other(say)
Q4 financing over cash for the extra 1x: primary=__%/yr stress=__%/yr (or another model: say)
Q5 cash values=__ ; primary=__ ; verdict must hold at: all | primary only
Q6 cost per side: primary=__bp ; reported/stress=__
Q7 G3 compares against: A=constant leverage | B=unlevered B&H | C=both must pass
Q8 1x long/flat of S1 as a declared descriptive (not a trial, never traded on this run): yes | no (then count it)
Q9 placebo: A=within-cycle placement | B=shift | C=blocks | D=whichever holds size in the Bench study
DEAL-BREAKERS: none | list (a deal-breaker = you would sign a dissent printed in the pre-registration)
```

**After the block, at most about 200 lines:**
1. **Your critique of the other reports, from your role.**
   - Say where they are wrong, under-argued, or in conflict with yours, naming the file and section.
   - Concede where they changed your mind, and say what changed it.
2. **Your answers to the role-specific asks** in my message to you.
3. **Exact replacement text** for anything in v0 you would change, written as pre-registration text.

Daniel will read the deliberation record. Write so that I can quote you.
