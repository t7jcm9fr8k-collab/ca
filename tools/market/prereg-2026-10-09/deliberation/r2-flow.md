```
BALLOT flow
Q1 S1 window: A
Q2 S1 expression: A
Q3 S2: A
Q4 financing over cash for the extra 1x: primary=1.5%/yr stress=4.0%/yr (model: a financed add-on, f = cash + spread on the borrowed 1×, with any expense ratio folded into the spread; bar (A) borrows its p× at the same f)
Q5 cash values=0%, 1.5%, 3% ; primary=1.5% ; verdict must hold at: all
Q6 cost per side: primary=2bp ; reported/stress=1bp reported, 5bp stress
Q7 G3 compares against: A
Q8 1x long/flat of S1 as a declared descriptive (not a trial, never traded on this run): yes
Q9 placebo: D (if more than one holds size: A, within-cycle placement)
DEAL-BREAKERS: (1) G6's concentration test as written in r1-redteam §3.2 (the rule's log return minus cash; top 5 episodes ≤ 50%) applied to an overlay; (2) G3 measured against unlevered B&H as a gate for an overlay, if that is reinstated.
```

# Round 2 — Flow Theorist

*The round-1 rules held. I opened no bar file, computed no statistic conditioned on a window, and fetched nothing. I read the June–July 2025 rows of `S/edge/data/calendar/nyse-sessions-1999-2026.csv` and the Quartermaster's dividend-placement files; neither contains prices. Every number names its file; arithmetic built on those numbers is mine and labelled as such.*

## 1 · Critique of the other reports

1. **r1-redteam §3.4 ("no leverage variant unless a 1× version has already passed") is a logic error, not just caution.** A 1× long/flat rule beats B&H only if the window carries about 85% of all of SPY's return (r1-redteam §0.2). A real flow carrying half of it would fail that test and still pass the timing test that matters for ROI (§2.3). Making the first a prerequisite of the second makes the ROI question unreachable. I agree with the lead's D1.
2. **r1-redteam §3.2 G6 (concentration) measures the wrong thing for an overlay, and rejects real effects by construction.**
   - "The rule's log return minus cash", for an always-≥1× book, is mostly the market's own return, so the gate measures the market's concentration.
   - Even computed on the timing excess, the five largest of 259 fat-tailed cycles exceed half the sum whenever the mean is modest. That is a property of fat tails, not evidence about the flow. Fix: G6′ in §3.2. This is deal-breaker (1).
3. **r1-redteam §3.2 G5 fails an *intact* flow about three times in four.** On the overlay-minus-bar series (§2.3), the published 10 bp gap, less variance drag and 2-bp costs, gives an expected z ≈ 2.4; G5 needs z ≥ 3.05 at N = 39 + k. So P(pass | intact) ≈ Φ(−0.64) ≈ 0.26 (my arithmetic, from r1-archivist §0.2 and EVIDENCE.md's 19.2% volatility). I accept the trade of false negatives for safety (r1-redteam §3.6). But "G4 passes, G5 fails" should read *below the selection-adjusted bar*, not *lucky-sized*.
4. **r1-redteam §3.2 G7 (the QQQ veto) vetoes a real half-size flow about a third of the time.** The span is 71 cycles of a bubble and bust. Assuming QQQ's session SD was about 2.5% in 2000–02, a half-size effect has z ≈ 0.37 against its own placebo median, so P(wrong sign) ≈ 0.36. A veto should need a clearly wrong sign (G7′).
5. **r1-redteam §2.7 L1 / §3.4 (G3 against unlevered B&H) measures leverage.** Every overlay at 1× or more fails it, whatever the flow does. Deal-breaker (2) if it returns.
6. **r1-archivist §3.3's power for the Treasury window mixes scales.**
   - Its t ≈ 2.4 pairs a 10-year-note effect (8.3 bp a day) with a long-bond SD (0.9%).
   - Taken on one instrument, the t for a yield effect does not depend on duration. If the 10-year note's daily SD is about half the long bond's (an assumption), the published effect gives t ≈ 4.7.
   - TLT's 20+ years lies outside Hartley & Schwarz's 2-, 5- and 10-year sample, so using it is an extrapolation along the curve.
7. **The two reports quote different Etula sizes for the selling window W−:** −17 bp per window (r1-archivist §3.1) against −3.4% annualized, about −7 bp per window (my r1 §1, row 2). Both come from working-paper snippets; the published size is not settled. One more reason not to trade W−.
8. **What changed my mind:**
   - **r1-archivist §0.2 and §3.1 (Nathan, Suominen & Tasa 2026):** the one causal test of the settlement link, whose day count does not match mine (§2.1).
   - **r1-quartermaster §0.2:** `SPY-1d.csv` is price-only after 2025-03-21. My r1 §3 called the whole file dividend-adjusted, which was wrong.
   - **r1-quartermaster §8 and §4:** opens are not guaranteed auction prints, and the event calendars are incomplete. I concede the open legs, and that my R2 announcement overlay cannot be built this round.
   - **r1-archivist §4.4:** Alpaca margin is about 7.75% a year [U]. My +1.0% spread was too low for this account.
   - **r1-redteam §0.2:** the "contaminated" point decides objection (ii) below.

## 2 · The lead's asks

### 2.1 R1b: I concede the trial to (A)

- **(i) Opens: conceded.** S1 can be priced on closes alone, which r1-quartermaster §0.8 calls dependable. R1b needs 24 open fills a year on a file whose opens are not guaranteed auction prints. When two designs test the same mechanism, the one that needs worse data loses.
- **(ii) The overnight leg: conceded, and the problem is bigger than contamination.**
  - Against the constant-leverage bar, any exposure tilted toward nights collects the known night/day gap (+3.1 vs +1.5 bp, EVIDENCE.md §C) as though it were month-end timing.
  - R1b's legs add two night-units of deviation a month: one more night at 2×, and one more at 1× where the sidestep would have been at 0×. A placebo would copy that structure and cancel it; bar (A) would not.
  - I chose those legs from the full-sample split, as the round-1 brief asked. For a test, that is exactly the leak r1-redteam §0.2 names.
- **(iii) Two signals in one trial: conceded, on the evidence.** W+ = [T−3, T+3] is the most-replicated part of the pattern; W− is weaker, and its published size is unsettled (§1.7). If W− is dead, bundling cuts the t-stat by about a quarter (√7/√12 = 0.76); if alive, it raises it by about a fifth. Bundling is a bet on the weaker half.
- **(iv) The 2025-06-20 ex-date: wrong for R1b as written, right for any close-to-close sidestep.**
  - The calendar file puts 2025-06-20 at ord_from_end −7, which is T−6.
  - R1b exits at the *open* of T−6 (r1-flow §3). The night close(06-18) → open(06-20), which carries the price-only payout drop, is therefore held at 1×, as in B&H, and the sidestep gains nothing from it.
  - A close-to-close W− (out from the close of T−7) would be credited the whole drop. Since (i) and (ii) rule out the open leg, W− has no clean expression on this file — a further reason to drop it.
- **The deeper reason is the settlement mapping.** Nathan et al. report the selling trough moving from T−4 to T−3 after T+1 (r1-archivist §3.1). My mapping predicts T−3 already under T+2, and T−2 under T+1. Either their baseline is the T+3 era or their day count differs from mine; r1-archivist §5 could not resolve which. A window that may be off by one belongs in a diagnostic, not a trial.
- **(C) Kayacetin's window.** In Etula's account T+4 opens the post-reinvestment reversal (T+4…T+8 low; r1-flow §1, row 2), so the mechanism argues against adding it. (A) also has the longer out-of-sample span: 2014 onward, against 2024 onward.
- **What I keep:**
  - the settlement diagnostic, in the exact form in §3.3 (v0's one-line pointer is not a form: it would let the reader pick which offset to look at after seeing them all);
  - no open legs anywhere in S1 or S2;
  - T-bills, not bonds, as the parking asset for any future sidestep.

### 2.2 Bonds at month-end: no conflict, and TLT should rise over close(T−3) → close(T)

- **Two windows, one story.** Etula et al. place cash-raising sales of stocks *and* Treasuries before the last settle-by-T dates: "elevated stock and bond yields right before the month end" (r1-archivist §3.1), with the bond reversal in the same windows as equities. My r1 line ("T-bills, not bonds") was about R1b's selling window, T−8…T−4 under T+3, when bonds are being sold too. Hartley & Schwarz's rise comes in the last three sessions, after that selling.
- **Over close(T−3) → close(T), both mechanisms predict TLT up.** Dash for cash: the selling ends and reverses. Hartley & Schwarz: index extension, with Treasury trading concentrated at the last close (NY Fed 2026, r1-archivist §3.3).
- **One wrinkle.** Treasuries settle T+1, so a seller timing each asset by its own settlement could still be selling bonds on T−2 and T−1. Etula's yields peaking "right before the month end" says institutions raise cash across assets together. If TLT fails while S1 passes, this is where I would look first — as a later hypothesis, never as a rescue.
- **So TLT is a fair S2, with three caveats:**
  1. It is the same family as S1. Read the two with Holm; neither may rescue the other.
  2. The noise is mostly independent. The two timing books share only T−2…T, and SPY and TLT session returns are far from perfectly correlated (an assumption, not measured here). A pass on both is close to two measurements.
  3. TLT is an extrapolation beyond Hartley & Schwarz's maturities. On the other hand, 2019-01 → 2026-03 (about 87 month-ends) is the cleanest out-of-sample span in this exercise.

### 2.3 The algebra: right, and stronger than stated

**The identity.** Let e_t be the exposure over session t, r_t SPY's simple return, and f_t the per-session financing rate on borrowed exposure. A book earns R_t = r_t + (e_t − 1)(r_t − f_t). The overlay holds e = 1 + 1_W; bar (A) holds e = 1 + p. So D_t = R^OV_t − R^A_t = (1_W(t) − p)(r_t − f_t), exactly, before costs. **The lead's formula is correct.**

**"The cash rate cancels": it never enters, because neither book holds cash.**
- What enters is f, and it drops out of the mean: mean(D) = p(1−p)(r̄_W − r̄_out) − Cov_t(1_W, f_t).
- Any constant f — and so any constant spread, or an expense ratio charged per borrowed unit — cancels exactly. A time-varying f leaves only its covariance with a calendar window, which is negligible: policy rates move at meetings, not at month-ends.
- **So the verdict against (A) is, to first order, invariant to the whole cash × spread grid.** Only the B&H headline moves with financing. That supports the lead's §2 reading.

**The variance drag is not "slight" next to a decayed effect.** In log terms (what CAGR measures), a book grows at about E[e·r] − E[(e−1)·f] − ½E[e²σ²]. E[e²] is 1 + 3p for the overlay and (1 + p)² for (A); the difference is p(1−p). With equal variance in and out of the window:

> **CAGR(OV) > CAGR(A) ⇔ r̄_W − r̄_out > σ²/2 + (sides per year × c) / (252 · p(1−p))**

- **Inputs:** p = 7/20.9 (7 window sessions; 5,413 sessions over 259 month-ends, DATA.md and r1-quartermaster §3); σ = 1.21% (19.2%/√252, EVIDENCE.md); 24 sides a year at 2 bp.
- **Threshold: 0.73 + 0.86 ≈ 1.6 bp a session**, against the published 10 bp in-minus-out gap (r1-archivist §0.2).
- **Drag alone:** ½p(1−p)σ² ≈ 0.16 bp a session, about 0.4% a year — the same size as the cost line, and several times larger in crisis months.

**Power is the same either way.** t(D) = √(p(1−p)) · (r̄_W − r̄_out) · √n / σ: 2.9 at a 10 bp gap, 1.4 at 5 bp, matching r1-archivist §2.

**Daniel's headline.** Overlay minus B&H is p(r̄_W − f) per session, less ½·3p·σ² of extra drag. With no month-end effect at all (r̄_W = the 4.6 bp average, EVIDENCE.md §C), that is about +0.5% a year at primary financing (cash 1.5% + spread 1.5%) and about −0.3% at the stress spread. **The sign of "beats B&H" is set by the financing assumption, not by the flow.**

### 2.4 Financing

- **My +1.0% had no basis beyond "prime-broker-like".** r1-flow §3 labelled it an assumption, and it is too low for this account. The two real options:
  - **Margin:** about 7.75% a year on the overnight debit (r1-archivist §4.4) [U].
  - **SSO-style 2×:** its expense ratio (0.87–0.91% by source, r1-flow §3; 0.88% in r1-archivist §4.3) plus swap financing at about cash + 0.5% (assumed, r1-archivist §6). About cash + 1.4% all-in per unit of extra exposure.
- **Primary: 1.5% over cash** (SSO-like, rounded). **Stress: 4.0%** (the quoted margin rate minus a bill rate of about 4%). A retail rate that does not float with bills would be a far larger spread in the zero-rate years, but only the headline feels that.
- **Model it as a financed add-on, with any expense ratio folded into the spread — not as a fraction of a modelled 2× fund.** With a non-zero expense ratio, edgelab's one-instrument form charges a 1× SPY position half a fund's fee outside the window, and its `walk` re-trades fractional weights on drift at every auction (edgelab.py docstring).
- **Must the verdict hold at both spreads?** Yes; it is free for the (A) bar.
- **The verdict applies to the margin implementation** (2 sides a window). Also print the SSO-switching line — 4 sides a window, f = cash + 1.4%, with its own G1′ — because that is what a cash account at Alpaca would actually run.

### 2.5 The reading rule, from the mechanism side

| Gate | Rejects a real, modest flow for a reason unrelated to its existence | Passes a fake | Fix |
|---|---|---|---|
| G1 as written (vs B&H) | 1×: the premium given up while out (85% hurdle) | Any 2× passes on leverage (§2.3 headline) | v0's re-point to (A) ✓ |
| G2 | Per-half t ≈ 1.0 at half size; decay-then-revival (Kayacetin) can sink one half | A coin flip in each half, 25% | Keep: it is the decay test |
| G3 vs B&H | Every overlay at 1× or more fails mechanically | Exclusion rules at a 0.5-point tolerance | (A), with a 2-point tolerance (G3′) |
| G4 | Power only: p ≈ 0.07 at half size | Only if the placebo did not copy the legs and leverage | Keep; the placebo copies the MOC legs and the 2× blocks |
| G5 | N counts 39 unrelated technical trials; P(pass \| intact) ≈ 0.26 | — | Keep (deliberate); compute on D_t; relabel the verdict |
| G6 concentration | Measures the market's concentration; for any modest mean, the top-5 share is over 50% by fat tails | — | G6′ on per-cycle D_t |
| G6 drop-crisis | The mechanism *predicts* amplification after high-volatility, low-return spells (Etula; Kayacetin), so this gate removes the strongest true months | — | Keep as written: it asks only for a positive result |
| G7 | 71 bubble/bust cycles: wrong sign about 36% of the time at half size (assumed SD) | — | G7′: veto at z < −1 |
| Price-only tail | — | Each of the six post-cutoff ex-dates credits the overlay +p·D vs (A) and vs the placebo, ≈ +3–5 bp a year | Declare (§3.3) |
| `rsi_dip` overlap | — | A "pass" may re-measure the known reversal premium | v0's descriptive output ✓ |

### 2.6 My numbers for S1, for the record

These are judgements: I weight the published size, a 58% decay and no effect at 0.25 / 0.45 / 0.30, and combine them with §2.3's formulas.

| Outcome | Probability |
|---|---|
| Beats (A) on CAGR | ≈ 0.7 |
| Passes G4 at Holm 0.025 | ≈ 0.3 |
| Passes G5 | ≈ 0.07 |
| WORKS on every gate | ≈ 0.05 |

**The most likely printout is "positive, below the bar".**

## 3 · Replacement text for v0 (pre-registration wording)

### 3.1 S1: instrument and bar

> **Instrument.** The extra 1× is a financed add-on. On each window session the account earns r_t − f_t on one extra unit of equity, with f = cash + s; s = 1.5%/yr (primary) and 4.0%/yr (stress), accrued per calendar day on the overnight leg. No separate expense ratio. The engine holds 1× SPY outside the window as SPY, not as a fraction of a modelled 2× fund.
> **Bar (A).** Hold (1 + p)× SPY on every leg, where p = (scored sessions inside windows) / (scored sessions), fixed from the scheduled calendar before the run. Rebalance to 1 + p at each close auction, paying the same per-side cost on the rebalancing notional, and borrow p× at f. The overlay's session excess over (A) is D_t = (1_W(t) − p)(r_t − f_t) − costs: a timing book with zero average exposure.

### 3.2 Gates for an overlay (replacing the re-pointed G1–G7)

> **G1′.** CAGR(OV) > CAGR(A) at 2 bp a side, primary cash and spread; and CAGR(OV) ≥ CAGR(A) at 5 bp.
> **G2′.** CAGR(OV) > CAGR(A) in each half (split at the midpoint session index), at 2 bp.
> **G3′.** maxDD(OV) ≥ maxDD(A) − 2.0 points. The 2.0 is a judgement: both drawdowns are set by the same crashes, so a few points is noise. Report maxDD of B&H, and the number of separate −15% episodes for OV, (A) and B&H.
> **G4.** Unchanged. The placebo moves each 2× block intact, with MOC→MOC legs, the same costs and the same financing. p < 0.05/k (Holm), and CAGR(OV) > the placebo median CAGR in each half.
> **G5′.** The deflated Sharpe of the D_t series, tested against zero, ≥ 0.80 at N = 39 + k. Its mean *is* the timing value, so it needs no benchmark centring and no cash subtraction. SE: paired circular-block bootstrap, 10-session blocks, 5,000 resamples, fixed seed. A flip at N = 100 makes the result PARTIAL. If G4 passes and G5′ fails, the verdict reads "PARTIAL — below the selection-adjusted bar".
> **G6′.** An episode is a cycle, from one close of T−4 to the next; cycle excess = Σ D_t over the cycle. Require at least 100 cycles and at least 40 per half. The sum of cycle excess with the 5 largest positive cycles removed must be ≥ 0. The drop-crisis test applies as written in r1-redteam §3.2, on CAGR(OV) − placebo-median CAGR.
> **G7′.** Run the identical overlay on QQQ, 1999-03-10 → 2005-02-24, against its own (A). Veto only if the mean of its D_t is below zero by more than one standard error (z < −1). A replication never rescues a failed gate.

### 3.3 Declared descriptive outputs (additions; never used to choose anything)

> **Settlement diagnostic.**
> - Give each month a settlement lag s by its T: 3 if T < 2017-09-05; 2 if T < 2024-05-28; 1 otherwise.
> - For each s, print the mean SPY close-to-close return and its SE at each offset T−8 … T+3 on the scheduled calendar. Exclude the six post-2025-03-21 sessions that are SPY ex-dates (brief §2), because that stretch is price-only.
> - Print one number with its SE: Δ = mean r(T−3 | s ≤ 2) − mean r(T−3 | s = 3). The mechanism predicts Δ < 0: T−3 becomes a selling day once the last settle-by-T trade date moves later.
> - Stated in advance: there are about 107 month-ends with s ≤ 2 and 150 with s = 3. At σ ≈ 1.21% the SE of Δ is about 15 bp, against a predicted 6–14 bp. **It cannot confirm or refute the mechanism.**
>
> **Ex-dividend bias.** `SPY-1d.csv` is price-only after 2025-03-21 (r1-quartermaster §0.2). Its six later ex-dates fall at T−8 … T−6 (brief §2), never inside a window, so each credits the overlay +p·D against (A) and against the placebo. At D = 30–59 bp (the located pre-cutoff range, r1-quartermaster §5), that is about +0.6–1.2% cumulative, or about +3–5 bp a year. Declared, not corrected.
>
> **FOMC overlap (r1-redteam G-k).** Report the share of windows containing a scheduled FOMC statement, and S1 with those windows excluded. This is computable for 2005–2016 and 2025–2026 only, because FOMC 2017–2024 is unverified (r1-quartermaster §0.6); the output must say so.

### 3.4 S2 (trial 41)

> **S2: TLT month-end overlay.**
> - **Window and orders.** Sessions T−2, T−1 and T, with T the last scheduled NYSE session of the month: +1× TLT from the MOC of T−3 to the MOC of T, decided from the calendar alone.
> - **Scoring.** As a financed add-on on top of S1's 1× SPY base. Bar (A2) holds p₂× TLT constantly, with p₂ = window sessions / scored sessions (≈ 3/20.9), at the same f. Per session: D_t = (1_W2(t) − p₂)(r_TLT,t − f_t) − costs.
> - **Data.** `bars/TLT-1d-long.csv` (stooq; distributions back-adjusted through 2026-04-01, r1-quartermaster §0.2), scored 2005-02-25 → 2026-08-31. TLT's located ex-dates fall on the first session of the month (104 of 113), none inside W2 (`exdates-on-calendar.txt`). The price-only months April–August 2026 credit the overlay +p₂·D against (A2) at each T+1 ex-date, about 0.2–0.3% cumulative; declared.
> - **Prediction.** TLT's mean return over W2 exceeds its mean over other sessions (Hartley & Schwarz 2019; Etula et al. 2020's month-end bond reversal).
> - **Gates.** G1′–G7′ with (A2) in place of (A); G7′ on QQQ is omitted (no bond veto file). Holm across S1 and S2; neither rescues the other.
> - **Declared descriptive.** The same window on 2019-01 → 2026-03 alone, outside Hartley & Schwarz's sample.
