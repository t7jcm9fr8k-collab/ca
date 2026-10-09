# How the month-end overlay was chosen — the deliberation record, 2026-10-09

*The lead (the main session) and five sub-agents co-wrote `PREREG-2026-10-09-month-end.md`. This file records who argued what, what changed whose mind, how each dispute was settled, and what was overruled. Every report, script and output is archived in `deliberation/`. No one computed any statistic of returns conditioned on a candidate window, event or rule at any point; the only real-data reads were integrity, basis, calendar and dividend-placement checks.*

## The ask and the set-up

**The ask.** Daniel: "Find a new edge … something in the market to use … once maybe twice a day … graded on gains and ROI." He then asked for five sub-agents to co-create the edge with the lead, so that he could see how well the deliberation goes.

**The five roles, each with its own scratch folder:**

| role | job |
|---|---|
| **Quartermaster** | the data: what is on disk, what can be fetched, what is clean |
| **Archivist** | the published record: what has survived publication and costs |
| **Flow Theorist** | mechanisms: which forced, price-insensitive flows could turn into a rule run once or twice a day |
| **Red Team** | the reading rule: base rates, failure modes, gates, the trial budget |
| **Bench** | the instrument: a two-leg (overnight/intraday) test harness, `tools/market/edgelab.py`, built and mutation-tested before any rule existed |

**The process.**
- **Round 1:** each role reported blind, without seeing the others' reports.
- **Round 2:** each read all the others, critiqued them from its role, and voted on a fixed ballot. The lead's brief (`deliberation/r2-brief.md`) stated the disputes, put the lead's own straw proposal up to be attacked, and set the ballot.
- **Round 3:** each signed or dissented on the draft pre-registration.

## Round 1 — five independent reports

**The Quartermaster** (`deliberation/r1-quartermaster.md`)
- Re-verified every bar file and fetched 21 official series from nasdaq.com, capped at 10 years.
- Found that DATA.md §2 is wrong. The stooq files are not "the unadjusted ones": each is dividend back-adjusted up to a symbol-specific cutoff (SPY 2025-03-21, TLT 2026-04-01, others 2022–2025).
- Found a mid-session last SPY bar, a placeholder bar on 2026-04-20, and an unadjusted `SPY-1d-agg.csv`.
- Found that ex-dividend dates collide with calendar windows: SPY on quarterly expiration Fridays, TLT on the first session of the month.
- Reached no T-bill series. Could not build the FOMC/CPI/jobs calendars.

**The Archivist** (`deliberation/r1-archivist.md`)
- Almost every published calendar edge decays after publication: pre-FOMC, the overnight drift, pre-holiday, the FOMC cycle.
- Month-end institutional cash flow is different in kind, a deadline rather than a behaviour, and there is 2026 evidence that it is alive.
- Recommended Etula et al.'s window exactly, and estimated +1.0%/yr for a 2× overlay.
- Warned that a half-size effect gives t ≈ 1.45.

**The Flow Theorist** (`deliberation/r1-flow.md`)
- Turned the dash-for-cash mechanism into rules, including a window that shifts with each settlement-cycle change (T+3 → T+2 in 2017, T+2 → T+1 in 2024).
- Pointed out that "beats buy-and-hold" mostly measures leverage: a 2× overlay on five *random* sessions a month beats SPY's CAGR with probability ≈ 0.8.

**The Red Team** (`deliberation/r1-redteam.md`)
- Put the prior at ≈ 3% for a luck-robust win.
- Showed by arithmetic that a 1× in-or-out calendar rule must capture ≥ 85% of all of SPY's return to tie buy-and-hold.
- Wrote eight gates (G0–G7) and capped the budget at k ≤ 2.
- Found two defects in the repo's statistics: the deflated Sharpe is centred on zero, and every Sharpe is computed on raw returns.
- Ruled out leverage until a 1× version passed.

**The Bench** (`deliberation/r1-bench.md`)
- Built edgelab: 168 checks, 45 of 46 planted bugs caught, and placebo size 3.5–4.0% against an exact 4.0%.
- It reproduces every number of EVIDENCE §C. Along the way it found that §C's "halves" were a split at 2016-01-01, not a midpoint.
- Measured power: 25% / 60% / 100% at 5 / 10 / 20 bp per event.

## The lead's synthesis, and the straw proposal

The one real dispute was leverage: the Red Team against the Archivist and the Flow Theorist. The lead argued they were answering two different questions:
- **"Does a 1× in-or-out rule beat buy-and-hold?"** prices the equity premium given up while out.
- **"Does 2× in the window beat constant leverage at the same average exposure?"** is pure timing, because overlay − constant leverage = (1_W − p)(r − f).

The straw proposal (v0) was Etula's window as a 2× overlay against constant leverage, judged by the Red Team's gates re-pointed at that bar.

## Round 2 — what changed whose mind

**The Red Team conceded the leverage dispute** (`deliberation/r2-redteam.md` §1).
- Its 1×-first prerequisite "tested the equity premium given up while out, not timing."
- It then did the work that made the concession useful:
  - Recomputed power for the overlay.
  - Showed the binding gate moves to the selection-adjusted Sharpe.
  - Corrected everyone's pass probability, its own included, for the N = 100 no-flip rule.
  - Switched its G5 to the log timing book after checking that a Sharpe-difference G5 quietly depends on the unobservable cash rate.

**The Archivist corrected its own headline** (`deliberation/r2-archivist.md` §1).
- Its +1.0%/yr had priced leverage. Against constant leverage it is +0.4%/yr forward.
- It withdrew its TLT second trial: the paper studied 2–10-year notes, and the window is a free choice of 3 to 5 days.
- It found that the overlay's extra variance drag is 0.41%/yr. The lead had called that "slight".

**The Flow Theorist conceded its own rule on three of the lead's four objections and refuted the fourth** (`deliberation/r2-flow.md` §1). The lead claimed the rule would dodge a June 2025 dividend; it sells at the open, so it would not.

**The Quartermaster sourced what was missing** (`deliberation/r2-quartermaster.md` §0).
- It found SPY's five distributions after the cutoff and cross-checked each one with an independent data witness, SSO − 2×SPY. That witness matches all 34 known ex-dates from 2016–2025.
- It corrected the lead's scored span.
- It made counting on the scheduled calendar a deal-breaker: counting on actual sessions would have shifted October 2012's window using Hurricane Sandy's closure before it was announced.

**The Bench re-measured and withdrew its claim that the old stooq files are unadjusted** (`deliberation/r2-bench.md` §1a).
- It quantified the deflated-Sharpe defect: its own round-1 bar was 3× too strict for this comparison, and about 1.5× too lenient for an unrelated rule.
- It made the paired standard error a deal-breaker, against its own earlier code.

**Errors the agents caught in the lead's work:**
- objection (iv) to the Flow Theorist's rule (wrong);
- "slight" drag (wrong: 0.41%/yr);
- the brief's scored span (inconsistent: "→ 2026-09-01" and "drop the August window" disagree).

## The votes (round 2)

| question | Quartermaster | Archivist | Flow Theorist | Red Team | Bench | carried |
|---|---|---|---|---|---|---|
| Q1 window | Etula | Etula | Etula | Etula | Etula | **Etula [T−3, T+3], MOC → MOC**, 5–0 |
| Q2 expression | overlay vs (A) | overlay vs (A) | overlay vs (A) | overlay vs (A) | overlay vs (A) | **2× overlay vs constant leverage**, 5–0 |
| Q3 second trial | TLT | none | TLT | none | none | **none, k = 1**, 3–2 |
| Q4 financing spread, primary / stress | 1.0 / 4.0 | 1.5 / 4.0 | 1.5 / 4.0 | 1.5 / 4.0 | 1.0 / 3.0 | **1.5 / 4.0** (gates invariant) |
| Q5 cash | 0, 1.5, 3; all | same | same | same | same | **0 / 1.5 / 3, must hold at all**, 5–0 |
| Q6 cost per side | 2 bp | 2 bp | 2 bp | 2 bp | 2 bp | **2 bp primary**, 5–0 |
| Q7 G3 against | (A) | (A) | (A) | (A), 5 pts | (A) | **(A)**, 5–0 |
| Q8 1× as a descriptive | yes | yes | yes | yes | yes | **yes**, 5–0 |
| Q9 placebo | size study | size study | size study | size study | size study | **circular within-cycle** (the linear form failed the size study; round 3) |

## Deal-breakers, and how each was met

| raised by | deal-breaker | how it was met |
|---|---|---|
| Flow Theorist | G6 "top 5 episodes ≤ 50%" on an always-≥1× book | Replaced by G6′: per-cycle sum of the log timing book, total without the 5 best cycles ≥ 0. The Red Team amended and accepted it. |
| Flow Theorist; Red Team | any gate or verdict word from comparison with unlevered buy-and-hold | Buy-and-hold is a headline only. |
| Quartermaster | any offset counted on bar dates or the realised calendar | All offsets are on the scheduled calendar. The window list is frozen and checked. |
| Bench; Red Team | G5 standardised by a single-Sharpe variance | G5′ standardises the paired difference series by its own block-bootstrap SE. [Bench confirmation: round 3] |
| Red Team | any descriptive used to select, rescue or justify a trade | Written into the pre-registration's descriptive section. |

## The lead's rulings where the vote did not decide

1. **G5′ (log timing book) gates; the Sharpe difference is reported.**
   - It is invariant to the cash bracket and charges the 0.41%/yr drag exactly once, in Daniel's unit (CAGR). A Sharpe-difference G5 benchmarks against equal volatility, with a hurdle that the unobservable cash rate sets.
   - The Red Team and the Flow Theorist asked for it. The Bench's built form is kept as a printed line.
2. **G3 tolerance is 5 points, not 2.** The Red Team's synthetic study shows that concentrating leverage alone deepens drawdown by about 3 points, so 2 points would fail about a quarter of intact effects. This overrules the Flow Theorist.
3. **G1 must also hold at 5 bp.**
   - The Archivist and the Flow Theorist asked for it, and it was the Red Team's round-1 text.
   - The Red Team's round-2 ballot made 5 bp "never a gate" without a stated reason.
   - It costs almost nothing in power, because G5′ binds first.
4. **Accrual is by calendar days.** This is the harness's tested convention, and the way brokers charge. The Red Team had per-session accrual.
5. **The financing spread uses the majority values.** The gates are invariant to it; it moves only the buy-and-hold headline.

## Minority positions, recorded and not adopted

- **TLT month-end overlay as a second trial** (Flow Theorist, Quartermaster).
  - For: both mechanisms predict bonds rise over the last three sessions; 2019–2026 is the cleanest unseen span; and the data supports it with dividend add-backs.
  - Against: an unreported maturity; a free window length; overlap with S1; no bond veto file; and Holm would halve S1's bar.
  - The Red Team's suggestion: pre-register it later with a dividend-corrected veto file, never as a rescue for S1.
- **G3 at 2 points** (Flow Theorist).
- **5 bp as a report only** (Red Team, round 2).

## Round 3 — sign-offs on the frozen text

| agent | verdict | corrections | the ones that mattered |
|---|---|---|---|
| Quartermaster (`deliberation/r3-quartermaster.md`) | **SIGN** | 6, all adopted | The frozen window lists also hold incomplete windows, which G0 must skip. The first scored session is 2005-03-28 (Good Friday 2005-03-25). The add-back formula was verified against official prices on the five dates. Stooq's second measured miss is QQQ 2023-12-27, outside every scored span. |
| Archivist (`deliberation/r3-archivist.md`) | **SIGN** | 6, all adopted | The dash-for-cash mechanism is *proposed*, not established. Kayacetin's 2026 revival is evidence that the effect lives, not that this mechanism drives it. Nathan et al. measured momentum-loser stocks, not the index. "Outside every published sample" became "outside every academic sample found". |
| Flow Theorist (`deliberation/r3-flow.md`) | **SIGN** | 5, all adopted | Harness check 1 as written would have VOIDed the run: only Σd, not each d_t, is invariant to the rate pair. The add-back read an open where the rule promises closes only, so dividends are now credited at the close. The placebo's block length was ambiguous; it is now the held-bar count. |
| Red Team (`deliberation/r3-redteam.md`) | **SIGN** | 8, all adopted | The verdict table had a gap: p < 0.05 but below the placebo median in a half. G3's sign was ambiguous, since drawdowns are negative numbers. The thresholds are exact: z ≥ 3.0311 and 3.3722, with the Φ form governing. G7′ uses the smaller z, not the printed bootstrap flag. Its own P(WORKS) figures are upper bounds. |
| Bench (`deliberation/r2-bench.md`, Build §B6) | **SIGN**, on condition that the placebo text is the circular one (met) | 5, all adopted | G5′ meets its deal-breaker, since each bootstrap resample of d takes the same blocks of S1 and (A). It found that the linear within-cycle placebo is not exact, and built and size-tested the circular one. It named the choices the draft left silent (QQQ's basis cutoff, span and overlap definitions, the diagnostic's span) and wrote the full frozen command. It built the close-only add-back and z_used for G7′. Its suite has 251 checks; mutation testing caught 48 of 48 round-2 bugs. |

**Two findings by the lead in round 3:**
- **The Red Team's G4 power nets out the overlay's drag and costs**, but the placebo pays the same drag and costs, so they cancel in G4. The Archivist's G4 figures (fails 58% at half of 10 bp/day) are the right ones for G4; the Red Team's (76%) suit G1 and G5′. P(WORKS) is unaffected, because G5′ binds first. Both are printed.
- **The Bench's synthetic size study found the within-cycle placebo rejecting a true null about 8–9% of the time at a 5% level**, even under i.i.d. returns. The lead sent it back as a probable code-path asymmetry between the observed statistic and the placebo statistics.
  - **The lead's guess was wrong.** Fed through the placebo's own evaluator, the observed arrangement reproduces the rule exactly, with a difference of 0.0 in 144 cells.
  - **The Bench showed the design itself was not exact.** The Red Team's round-1 placement (a block may not cross its cycle's end) uses a start set that is not a group orbit. The real block sits at the edge, where fewer placements reach, so the observed statistic is over-dispersed against its null: an sd ratio of 1.19, a predicted 8.3%, a measured 7.7–9.2%, and U-shaped p-values.
  - **The fix is circular placement.** A block may wrap from the cycle's end to its start, so every session is covered equally and the real placement is one rotation.
  - **The Red Team conceded its design** and ruled the circular one its "A", provided it holds size with the extra sides of wrapped draws charged. It measured that cost bias itself: about 8.5 bp/yr, moving the size to about 5.5%.
  - **Circular placement holds:** 0.053 / 0.057 / 0.052 under i.i.d., GARCH and regime volatility, with flat p deciles. It is the most powerful of the three designs that hold (`deliberation/bench/r2/size/size-interim2.txt`).
  - Without the size study, the pre-registration would have frozen a placebo that roughly doubles the false-positive rate.

## What the five expect, written before the run

The modal outcome for a real but decayed effect is "PARTIAL — below the selection-adjusted bar". The modal outcome for no effect is NULL. Prior-weighted chances of passing every gate:

| source | P(WORKS) |
|---|---|
| Red Team (`deliberation/redteam/overlay-output.txt` §18b) | 0.032 at the 10 bp published size; 0.120 at 14 bp |
| Archivist (before the N = 100 correction) | 0.05–0.09 |
| Flow Theorist | ≈ 0.05 |
