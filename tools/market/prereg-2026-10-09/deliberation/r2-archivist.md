BALLOT archivist
Q1 S1 window: A
Q2 S1 expression: A
Q3 S2: D
Q4 financing over cash for the extra 1x: primary=1.5%/yr stress=4.0%/yr (also print one flat 7.75%/yr all-in retail-margin line for (B) only; the gates vs (A) are invariant to all three)
Q5 cash values=0, 1.5, 3 ; primary=1.5 ; verdict must hold at: all
Q6 cost per side: primary=2bp ; reported/stress=1bp reported, 5bp stress (G1 vs (A) must stay >= 0 at 5bp)
Q7 G3 compares against: A
Q8 1x long/flat of S1 as a declared descriptive (not a trial, never traded on this run): yes
Q9 placebo: D (prefer A if more than one design holds size)
DEAL-BREAKERS: none

*Archivist, round 2, 2026-10-09.*
- *New numbers come from `S/edge/archivist/estimates_r2.py` → `estimates_r2.txt`, which uses formulas, the Red Team's own inputs from `redteam/hurdles-output.txt` and labelled assumptions; it reads no bar file.*
- *Calendar facts come from `S/edge/data/calendar/nyse-sessions-1999-2026.csv`; no price was read.*
- *No new web searches; this works from my round-1 notes (`archivist/notes.md`).*

## 1 · Critique of the other reports

**r1-quartermaster — it corrected me, and I concede.**
- My round-1 §3.2/§3.3 said stooq TLT is "not dividend-adjusted". That is wrong. QM's Conclusions item 2 shows every stooq file is distribution back-adjusted up to a cutoff:
  - TLT through 2026-04-01, with the ex-date on T+1 in 104 of 113 months;
  - SPY through 2025-03-21.
- So the data obstacle I gave for S2 is gone. My objection to S2 is now fidelity, not data (§2.3).
- One disagreement. QM says turn-of-month "cannot be made out-of-sample" on this data. It can be **post-definition**: Etula's window was public in 2014–15 and is in-sample only to the 2013 end of the chart axis on their slides. But no span before 2024 is **unseen by the literature** (§2.1).
- QM's dividend placement also exposes one benchmark bias that v0 does not handle (§3.3).

**r1-flow — right about the mechanism and the bars; R1b should not be the trial.** I agree with:
- dash-for-cash as the family;
- the overlap warnings (jobs Fridays, FOMC);
- "beats B&H measures leverage";
- constant leverage plus a placebo as the bars.

To the lead's four objections to R1b (opens, overnight contamination, bundling, ex-date) I add three:
- **(v) The T+1 "prediction" has already been seen.** Nathan, Suominen & Tasa use 533 pre-reform and 19 post-reform months. That puts their data through 2025-12 [V-abs, notes.md], and their replication README states the one-day shift of the loser trough after May 2024 [V-text]. Object and day-count convention differ from ours (loser stocks, not the index), but the mechanism's T+1 prediction is public.
- **(vi) The sidestep's published depth is uncertain by a factor of 2.5.**
  - My snippet gives −17 bp over T−8..T−4 (notes.md, Etula WP). Flow's gives "−3.4% annualized" (r1-flow §1 row 2), which is about −6.7 bp over the same 5 sessions.
  - The repeated "3.4" suggests one summary mixed bp/day with %/yr. Both readings agree on the positive leg: +77 bp over 7 sessions ≈ 11 bp/day ≈ 28%/yr annualised, matching Flow's +28.6%.
  - R1a/R1b's value hinges on that depth.
- **(vii) The settlement-adjusted windows are Flow's derivation, not a published specification** (r1-flow §8 says so). Every derived offset is a fork.

Flow's P(R1b passes the matched/placebo test) of 0.30 matches my P(G4) for S1 of 0.30–0.41 (§2.2), so we do not disagree about odds.

**r1-redteam — it shaped this round most:**
- base rates;
- the two Sharpe defects, which are real and must be fixed;
- G0/G6/G7;
- k ≤ 2;
- the clean-data table.

I disagree in four places:
1. **§3.4, "no leverage variant unless a 1× version has passed".** The 1× test needs S ≥ 0.85 just to tie B&H (hurdles §3). The overlay's timing question is answerable from about S ≥ 0.75: G4 power is about 0.7–0.8 there (estimates_r2 §2). Requiring 1× first makes the only ROI-relevant test unreachable. The lead's D1 algebra is correct, and I checked one more piece of it: the overlay's extra log drag is p(1−p)σ²/2 = **0.41%/yr**. That is not "slight" next to a half-size effect.
2. **§3.4, "G3 against unlevered B&H".** An always-≥1× overlay fails that by construction, so the gate would measure risk appetite, not timing. Gate G3 against (A), and print B&H's drawdown and the −15% STOP crossings for Daniel's own decision.
3. **G5 for an overlay needs its own arithmetic.**
   - The overlay and (A) are correlated at ρ = (1+p)/√(1+3p) = 0.943, so SE(ΔSR) ≈ 0.073.
   - Concentrating exposure costs the overlay −0.030 of Sharpe even with zero timing value (SR_mkt 0.53).
   - Result: P(G5) is 0.05–0.09, not ~0.3 (estimates_r2 §2).
4. **§0.8's expected outcome is for 1×.** For the overlay at half size the likely verdict is **PARTIAL — "lucky-sized"** if G4 passes (P ≈ 0.26–0.54). If G4 fails, it is "exposure or leverage, not timing" or NULL. G5 almost surely fails (P ≤ 0.015). It is not "premium, not a strategy". Write that down before the run.

**r1-archivist (mine) — what I would now change.**
- **(a) Restate the headline.** My "+1.0%/yr" compared the overlay with 1× B&H, so it mixed timing value with the premium on extra exposure. Against constant leverage at 2 bp/side it is **+0.4%/yr** for Daniel's forward years and +1.3%/yr in backtest units (estimates_r2 §2). Lead with that.
- **(b) Fix the out-of-sample wording.** I called 2014–2026 out-of-sample without saying it overlaps Kayacetin's sample, the very paper reporting the US effect strongest in 2019–23.
- **(c) Correct the TLT basis** (above).
- **(d) Withdraw my recommendation of Treasury end-of-month as S2.**
- **(e)** I should have flagged the −17 bp vs −3.4%/yr unit clash in round 1.
- **(f) Accept 2 bp primary.** The true MOC cost is about the SEC fee, but conservatism is free here.

## 2 · Answers to the lead's asks

**2.1 Window. A, Etula [T−3, T+3], is the least-forked choice with the most out-of-sample history.**

| Window | Defined from | Complete S1 windows on disk outside its own sample (calendar count; T from 2005-03 to 2026-07 = 257) |
|---|---|---|
| A · Etula [T−3, T+3] | WP 2014–15; slides' axis to 2013 | **151** (2014-01 → 2026-07) |
| C · Kayacetin [T−3, T+4] | 1994–2023 sample | 31 (2024-01 → 2026-07) |
| B · settlement-adjusted | derived this session; T+1 shift already in Nathan et al. to 2025-12 | nominally all, but the era offsets are forks, and only 7 T+1 windows (2026-01 → 07) are unseen |

- **Nathan et al. do use post-2024-05-28 data:** 19 post-reform months, June 2024 → December 2025.
  - Flow's diagnostic is therefore a **replication on a new object** for 2024-06 → 2025-12.
  - It is a **prediction only for 2026-01 → 2026-07** (7 windows).
  - For the 2017 T+3 → T+2 change: it lies inside their 1980–2025 sample, but I could not verify whether they test it explicitly.
  - Keep the diagnostic as declared descriptive. Do not let anyone cite it as an out-of-sample confirmation.

**2.2 The Red Team's prior, and what I expect for the D1 framing.**

On one scale (window-minus-rest mean daily return, 7-session window), the two priors barely differ, and the Red Team's is the **more optimistic** about the effect (estimates_r2 §1):

| | Red Team (r1 §1.4 weights) | Archivist (round-1 weights) |
|---|---|---|
| Expected window − rest, backtest scale | **4.94 bp/day** | **3.96 bp/day** |
| Its "≈3%" | P(1× long/flat clears G0–G7 vs B&H) | — |

- **What drives the gap is the instrument and the yardstick, not the effect.**
  - A 1× long/flat rule must beat the premium forgone on two-thirds of days, which needs S ≥ 0.85.
  - The overlay forgoes nothing.
- **A second driver is units.** The Red Team prices with the realised 2005–26 SPY return (11.74%/yr arithmetic, hurdles §3). I used a forward 6.05% premium.
  - A larger premium makes "out" costlier and inflates any overlay-vs-B&H number (the leverage tailwind).
  - It does not inflate overlay vs (A), where only the window-minus-rest difference counts.

Expected results for the D1 framing — overlay vs constant leverage at the same average exposure, 2 bp/side; the 5 bp row is in estimates_r2 §2:

| Prior, units | E[annual edge net of the 0.41% extra drag and 0.48% costs] | P(G1: beats (A)) | P(G2: both halves) | P(G4) k=1 / k=2 | P(G5: z ≥ 3.05) |
|---|---|---|---|---|---|
| Red Team, backtest | **+1.9%/yr** | 0.67 | 0.50 | 0.41 / 0.36 | **0.09** |
| Archivist, backtest | **+1.3%/yr** | 0.63 | 0.45 | 0.36 / 0.30 | **0.05** |
| Archivist, forward (Daniel's next years) | **+0.4%/yr** | — | — | — | — |

- **G5 is binding in every scenario short of the full published size.**
- P(WORKS) for the overlay is therefore **at most about 0.05–0.09**: about two to three times the Red Team's ≈0.03 for 1×, and still small.
- The overlay framing does not make a pass likely. It makes the test measure timing, and it makes a PARTIAL informative.
- Under no effect, the overlay beats (A) about 32% of the time (drag and costs give it −0.89%/yr), so G1 alone must never be read as evidence.

**2.3 TLT as S2: not a faithful test of Hartley–Schwarz. Better k = 1.**
- **Their instrument** is 2-, 5- and 10-year notes on modelled daily prices, January 1990 – December 2018, excess over GC repo [V-sec, CXO via notes.md].
  - A search summary says tests on "actual issued T-notes and T-bonds generally confirm" the result, but I have no published magnitude for 20+ years.
- **Their window** is "last few days", "largest and most significant over the last 3 to 5 days". The worked example is the 10-year note's last 3 days, about 0.25%/month [V-abs]. Another summary stresses the final day [V-sec].
  - So the window is a 3–5-day degree of freedom, and CXO warns of snooping in the choice of maturity and days.
- **CXO's TLT test** (mid-2002 onward) is a turn-of-month test. Its exact window is not in my notes.
  - A month-boundary window includes T+1 (TLT's ex-date) and the post-month-end days where HS find nothing.
  - Its "does not corroborate" is therefore weak evidence either way, not a test of HS's window.
- **Timing (unverified concern).** Month-end index demand is priced at the bond market's close, while TLT fills at NYSE's 16:00 close.
- **Overlap with S1.** S2 shares S1's sessions T−2..T and its mechanism family, so it is not an independent witness, and it moves S1's Holm bar from 0.05 to 0.025.
- **Verdict.** A TLT pass would be a new claim about an unreported maturity; a fail would not refute the paper. If the lead overrules, label S2 "extension to 20+ years, not a replication", MOC close(T−3) → close(T), stooq TLT through 2026-04-01 only.

**2.4 Financing. Nothing I found is a verified retail rate for a 2× overlay.**
- **Alpaca margin, 7.75%/yr.** An undated support page, actual/360 on the end-of-day debit [U]. It is all-in, not a spread, and retail rates do not fall to zero when bills do.
- **SSO.** Expense ratio 0.88% [V-sec]. The embedded swap spread was not retrieved.
- **SSO's 2022–23 realised shortfall:** −5.7% against −3.6% for an ideal-leverage model, from a secondary review [V-sec]. The model's financing basis is unknown.
- **Futures implementations** (HMM; HS's repo excess) finance near GC/bills, but Daniel cannot use them.
- **Proposal (labelled assumptions):**
  - primary: cash + 1.5%/yr (SSO's 0.88% plus about 0.6% assumed swap spread; equals the Red Team's §12 working value);
  - stress: cash + 4.0%/yr (a retail margin rate near 7.75% against bills near 4%);
  - one extra line for (B) only: a flat 7.75%/yr all-in, which shows what margin would cost in the zero-rate years.
- **Model no expense ratio in the gate.** With S1 and (A) financed identically, any spread or expense ratio cancels exactly: average borrowing is equal at p̂ (estimates_r2 §2). Financing changes only the headline against (B).
- **The lead's cash claim checks out** (estimates_r2 §4):
  - a 0% → 3% cash bracket moves a 1× long/flat rule by 2.0%/yr against B&H;
  - it moves overlay vs (A) by 0.00%/yr, because neither book holds idle cash.

## 3 · Replacement text for v0, written as pre-registration text

**3.1 Window and orders** (replaces the first bullet of "Window and orders"):
> T is the last scheduled NYSE session of each calendar month, read from the barqc calendar as published before the decision.
>
> S1 holds 2× from the close of T−4 to the close of T+3 (sessions T−3 … T+3) and 1× at all other times. Both changes are MOC orders fixed by the calendar alone and queued the session before.
>
> Twenty-one entry or exit sessions in 2005–2026 are rule-derived half-days: Christmas Eve or the day after Thanksgiving at entry, July 3 at exit. They fill at that day's official close.
>
> If a scheduled entry or exit session is an unscheduled closure, the order fills at the close of the next actual session. This happens once: November 2018's exit, scheduled for 2018-12-05, fills 2018-12-06.
>
> Closures inside a window (2007-01-02; 2012-10-29 and 10-30) shorten it.
>
> Scored windows: T from 2005-03-31 to 2026-07-31, 257 windows.

**3.2 Benchmark (A)** (replaces "(A) constant leverage at the realized average exposure"):
> (A) holds exposure 1 + p̂ on every session, where p̂ is S1's realised share of sessions at 2×.
>
> S1 and (A) are computed with the same daily formula: e·r_SPY − (e − 1)·(cash + spread)/252. Their average borrowing, and therefore their financing, are identical.
>
> Costs are charged on S1's scheduled exposure changes only; (A) pays none.
>
> G1, G2, G3 and G5 compare S1 with (A). G5 uses excess returns, ρ is estimated from the data, and N = 39 + k.

**3.3 Dividend basis** (new):
> SPY-1d.csv is total return through 2025-03-21 and price-only after. The five later SPY ex-dates before 2026-09-01 (2025-06-20, 2025-09-19, 2025-12-19, 2026-03-20, 2026-06-18) fall outside W, where S1 holds 1× and (A) holds 1 + p̂.
>
> The Quartermaster adds those five distributions back from a cited source before the run. If it cannot, the run prints the bias bound next to every affected comparison:
> - against (A), S1 is favoured by 50–98 bp cumulative: 2.3–4.6 bp/yr over the full window, or 22–44 bp/yr over the post-T+1 span;
> - (B) is understated by 150–295 bp cumulative (estimates_r2 §5).

**3.4 Declared descriptive outputs** (replaces the "2005–2013 against 2014–2026" and "post-T+1" bullets, and the label on the settlement diagnostic):
> Spans, reported and never used to choose anything:
> - (i) 2005-03 → 2013-12, 106 windows: inside Etula et al.'s sample.
> - (ii) 2014-01 → 2023-12, 120 windows: after the window was published, but inside Kayacetin (2026)'s 1994–2023 sample, which reports the U.S. effect strongest in 2019–2023.
> - (iii) 2024-01 → 2026-07, 31 windows: outside every published sample found. Too short to decide anything.
>
> The settlement diagnostic (r1-flow §3 R1) is not a fresh prediction for 2017-09 → 2025-12: those months lie inside Nathan, Suominen & Tasa (2026)'s 1980–2025 sample.
>
> They report the post-May-2024 shift explicitly; whether they test the 2017 change is unverified. It is a prediction only for 2026-01 → 2026-07 (7 windows).

**3.5 Expected outcome, stated before the run** (new; estimates_r2 §2):
> At half its published size, S1 most likely beats (A) (P ≈ 0.7–0.9) and passes G4 only about a quarter to half the time (P ≈ 0.26–0.54 at k = 1). It almost surely fails G5 (P ≤ 0.015).
>
> The modal outcomes are PARTIAL — "lucky-sized" (if G4 passes) and "exposure or leverage, not timing" or NULL (if it does not).
>
> Under either the Red Team's or the Archivist's prior, P(WORKS) is about 0.05–0.09. A NULL would not show the flow is absent. PARTIAL means do not trade.

**3.6 S2** (replaces "S2 (trial 41): open"):
> None; k = 1, N = 40, with the N = 100 sensitivity.
>
> Hartley–Schwarz report 2-, 5- and 10-year notes on modelled prices over 1990–2018, and their window has a 3-to-5-day degree of freedom. TLT shares S1's sessions T−2…T. A second trial would halve S1's Holm threshold to test an extension the literature has not reported.
