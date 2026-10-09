# Red Team — Round 1

*2026-10-09 · Red Team (the skeptic who writes the reading rule) · scratch files in `edge/redteam/`: `hurdles.py`, `hurdles-output.txt`.*

*Nothing was tested and no bar file was opened. Each number carries one of four marks:*
- ***[R]*** *a repo file and line;*
- ***[S]*** *a source confirmed only through search-result text. No full text could be read: WebFetch failed DNS on every host and the proxy refused direct downloads;*
- ***[C §n]*** *a formula result in `hurdles-output.txt` section n. Its inputs are EVIDENCE.md:517 and 531-534 plus the cited papers, with no market data;*
- ***[U]*** *unverified.*

---

## 0 · Conclusions

### 1. Prior (reasoned in §1.4)

These figures assume the best candidate these families allow: a turn-of-month (TOM) window, 1×, long or flat SPY.

| question | probability |
|---|---|
| The backtest point estimate beats buy-and-hold (B&H) SPY on net CAGR over 2005–2026 | **≈ 25%** |
| It beats B&H in a way that survives a luck-robust reading rule | **≈ 3%** (range 1–5%) |
| It then also beats B&H over the next five live years, given the line above | **≈ 55%** |
| Both of the last two together | **≈ 1.5–2%** |

- **A point estimate must not be read as an edge.** About 25% of backtests would show a win but only about 3% would hold up, so most apparent wins would be noise or a decayed effect.
- **In-house anchor for the 3%:** none of the 39 trials so far "works", and Laplace's rule gives (0+1)/(39+2) = 2.4% [R trials.json].
- **Why five live years cannot settle it:**
  - the five-year standard error of a TOM-like active return is ≈ 7.7 pts/yr [C §10: tracking error 17.3%/√5];
  - published edges shrink 26–73% out of sample (§1.1).
- **Sparse-event standalone rules** (pre-FOMC, pre-holiday, an opex day) have P ≈ 0, by arithmetic rather than opinion (next point).

### 2. Which families can win on Daniel's metric at all (arithmetic, not a test)

**The hurdle.**
- B&H runs at ≈ 10.4% CAGR with 19.2% volatility [R EVIDENCE.md:533].
- Assume idle cash earns 1.5% and each leg costs 2 bp.
- A long or flat SPY rule must then earn this share of *all* the index's arithmetic return during its exposed sessions to match B&H [C §3]:

| rule | share of sessions exposed | share of all return it must earn |
|---|---|---|
| pre-holiday | 3.6% | ≥ 76% |
| pre-FOMC | 3.2% | ≥ 75% |
| TOM, T−1..T+3 | 19% | ≥ 81% |
| TOM, T−4..T+3 | 33% | ≥ 85% |
| FOMC-cycle even weeks (28 round trips a year) | 50% | ≥ 95% |

**Published magnitudes, taken at face value, fall short** [C §4]:
- pre-FOMC delivers 33% (8 events × 49 bp);
- pre-holiday delivers 32–50% (Ariel's 9–14× an average day).

**Consequences, family by family.**
- **Sparse-event rules cannot beat B&H unlevered, even undecayed.** They can only work as overlays: B&H plus extra exposure on event days, which is leverage.
- **Even weeks cannot pass the statistical gate, even fully intact.** Its z ≈ 1.0 against 3.05 needed [C §10].
- **Month-end rebalancing as an exclusion overlay is worth at most +0.6%/yr.** It means stepping out of SPY ~6 days a year.
  - Fully intact: +0.58%/yr. At half strength: +0.07%. At zero: −0.44% [C §4].
  - It is statistically invisible over 21.5 years.
- **Overnight-structure rules are contaminated and their published premium has gone.**
  - The team has already seen SPY's 2005–26 overnight/intraday split, by halves [R EVIDENCE.md:727-731].
  - The overnight drift has averaged ≈ 0 since 2021 (Boyarchenko, Larsen & Whelan, NY Fed, July 2026) [S].
- **Crypto is out of scope.**
  - There is no crypto data on disk and no 2005 window.
  - Alpaca charges 15/25 bp maker/taker at its entry tier [S].

**Only two paths can reach WORKS at all.**
- **A TOM-type window,** and only if about 90% or more of its historical concentration survived. My estimates of P(WORKS) [C §10]:
  - fully intact: ≈ 0.1–0.2;
  - 10% decay: ≈ 0.05–0.1;
  - 25% decay: ≈ 0.01–0.03.
- **An event-day overlay (leverage),** and only if the event premium survived in *both* halves.
  - A pre-FOMC overlay gives z ≈ 4.2 at Lucca–Moench's full 49 bp, and z ≈ 1.8 at half that [C §12].
  - The drift is reported gone after 2015 [S].

### 3. The reading rule (full text in §3)

**WORKS needs all eight gates to pass.**

| gate | condition |
|---|---|
| G0 | Integrity checks pass; otherwise the run is VOID. |
| G1 | Account CAGR beats B&H SPY total return over the full window at 2 bp a leg with actual T-bill cash, and is still ≥ B&H at 5 bp a leg. |
| G2 | Account CAGR beats B&H in each half. |
| G3 | Maximum drawdown is no worse than B&H's (0.5-pt tolerance, §3.2). |
| G4 | The within-cycle placebo gives p < 0.05/k (Holm), and the rule beats the placebo median in each half. |
| G5 | Deflated Sharpe *against the benchmark* ≥ 0.80 at N = 39 + k, and the verdict must not flip at N = 100. |
| G6 | At least 100 episodes (≥ 40 per half); the top 5 episodes give ≤ 50% of the excess; the result survives deleting 2008-09→2009-06 and 2020-02-15→2020-04-30. |
| G7 | Same sign on QQQ 1999-03-10 → 2005-02-24, as a veto only. |

- **Why 0.80 for G5:** it equals z ≥ 3.05, a family-wise false-positive rate of ≈ 5%. That is the same bar as Bonferroni and as Harvey–Liu–Zhu's t > 3 [C §11].
- **ROI is the CAGR of the whole account**, with idle cash earning the actual 3-month T-bill rate. It is never the return per day invested.
- **Every other outcome is one of three verdicts** (§3.3): "PARTIAL — do not trade" with a named reason, NULL, or VOID.

### 4. Two defects to fix before any Sharpe ratio is read

**(a) The deflated Sharpe is deflated against zero, not against the benchmark.**
- `crosstest.py:171-175` hands off to `combine.py:74`, which centres the expected maximum at zero.
- Yet the same output reports a null mean Sharpe of 0.54/0.46 and benchmark Sharpes of 0.56/0.55 [R runs/crosstest-2026-09-11.txt:21,44; EVIDENCE.md:1237,1246].
- `srs` (crosstest.py:169) is computed and never used.
- PREREG:89-92's "must exceed zero" is vacuous for a probability.
- The fix is in §3.5.

**(b) Every Sharpe in the repo is computed on raw returns.**
- `replay.py:166-176` subtracts no risk-free rate; `portfolio.py` and `crosstest.py` both reuse it.
- A part-time rule's idle-cash interest is therefore credited as risk-free Sharpe.
- At 3% cash, a 19%-exposure rule gains a spurious +0.20 Sharpe edge over B&H — the whole of the old +0.20 hurdle. A 5%-exposure rule gains +0.54 [C §13].
- G5 must use returns in excess of the T-bill rate.

### 5. Trial budget (§4)

- **At most 2 specifications this round** (hard maximum 3).
- **One trial** = one combination of window or event definition × instrument × fill convention × leverage × exit.
- **Not trials:** veto-only replications and cost or cash stresses, provided they are pre-registered.
- **Trials:** anything that could rescue a failed result, or could be selected for trading.
- **N = 39 + k**, with a sensitivity run at N = 100. trials.json itself says nulltest runs and `--no-record` runs are not counted [R trials.json:23-25].

### 6. Clean data (§4.2)

**Only forward data is truly clean.**

**Clean for calendar hypotheses:**
- **QQQ 1999-03-10 → 2005-02-24.**
  - 1,499 sessions that the aligned tools cannot reach [R DATA.md:164-167].
  - Nearly dividend-free [S, partial].
  - Use it as a veto only; it has too little power for anything else.
- **SPY 2005–2026.**
  - No calendar rule has used it, but it has been viewed intensively.
  - It is not clean for overnight rules.

**Not usable as they stand:** the other stooq ETF files have a dirty dividend basis for calendar work.

**Forward paper trading:** at least 6 months and at least 6 event cycles, graded on implementation fidelity only.
- A forward P&L cannot confirm a 1–3%/yr edge in useful time [C §7].
- At part-time-rule tracking errors of 8–17%/yr, t = 2 takes 28–1,156 years.
- Even a low-tracking-error overlay (3%/yr) needs 4–36 years.

### 7. Three questions for Daniel, via the lead, before the freeze

1. **Taxable account or IRA?** In a taxable account, a part-time rule needs +2.3 to +4.9 pts/yr pre-tax just to tie B&H after tax (§2.0 G-f).
2. **Where would idle cash sit — a T-bill fund, or uninvested at 0%?** This decides which cash case is the binding one (G-e).
3. **Is the autopilot's 15% drawdown STOP a hard limit?** B&H's own drawdown on this window was −56.5% [R EVIDENCE.md:534]. Any rule close to fully invested, or levered, will trip it.

### 8. Expected outcome of this round

**NULL, or "PARTIAL — premium, not a strategy" (or "unstable" for an overlay).** I am stating this before the run so it can be checked against the result.

The reasoning: a TOM effect at half strength (S = 0.5) would still show a timing t ≈ 2.2 [C §14], so it passes G4. It would trail B&H by ≈ 3.6%/yr [C §10], so it fails G1. A real but decayed premium lands exactly in "PARTIAL — premium, not a strategy". That is the RSI-dip result again, in a calendar costume.

---

## 1 · The base-rate case

### 1.1 The published record

All rows in this table are marked [S].

| Source | Sample | Finding used here |
|---|---|---|
| McLean & Pontiff, *J. Finance*, Feb 2016 | 97 predictors | Returns 26% lower out of sample and 58% lower after publication. Larger in-sample returns → larger declines. |
| Falck, Rej & Thesmar 2022, *Quant. Finance* 22(11) | 72 published US equity strategies, out of sample to 2014 | Out-of-sample performance ≈ 50% of in-sample. |
| Suhonen, Lennkh & Perez 2017, *JPM* | 215 bank "alternative beta" products, live ~2005–15 | Median Sharpe fell 73% from backtest to live (1.20 → 0.31). Only 18 of 215 matched their backtest; 65 were negative live (per secondary summaries). |
| Wiecki, Campbell, Lent & Stauth 2016 (Quantopian) | 888 algorithms | Backtest Sharpe explains < 2.5% of out-of-sample Sharpe (R² < 0.025). More backtesting → a bigger gap. |
| Harvey, Liu & Zhu 2016, *RFS* 29(1) | 316 factors | A new factor should clear t > 3.0. |
| Harvey & Liu 2015, *JPM* 41(1) | Sharpe haircuts | Haircuts are nonlinear. Marginal Sharpes (< 0.4) lose more than 50%. |
| Hou, Xue & Zhang 2020, *RFS* 33(5) | 452 anomalies | 65% fail \|t\| ≥ 1.96 and 82% fail t ≥ 2.78. Survivors are smaller than originally reported. |
| Jensen, Kelly & Pedersen 2023, *J. Finance* 78(5) — counterpoint | Cross-sectional factors | Most factors replicate. This says nothing about calendar timing of an index. |
| Sullivan, Timmermann & White 2001, *J. Econometrics* 105 | ~100 years of daily data; the full universe of calendar rules | Calendar effects are not significant once the searched universe is accounted for. |
| Schwert 2003, *Handbook of the Economics of Finance*, ch. 15 | Anomalies after publication | Weekend, size, value and dividend-yield effects weakened or vanished. |
| Lakonishok & Smidt 1988, *RFS* 1(4) | DJIA 1897–1986 | TOM's four days carried all of the positive return. |
| McConnell & Xu 2008, *FAJ* 64(2) | CRSP 1926–2005 | Outside the TOM window, no reward for market risk. The effect persisted through 1987–2005. |
| Maberly & Waggoner 2000, Atlanta Fed WP 2000-11 | S&P 500 futures and spot | TOM gone after 1990. |
| Chen & Chua 2011, *J. Financial Planning*, Apr | ETF era | TOM concentrated on day 1. **Switching from T-bills into the index on TOM days underperformed buy-and-hold "in recent years".** |
| Etula, Rinne, Suominen & Vaittinen 2020, *RFS* 33(1) | Month-end cash needs | Patterns across liquid markets; a reversal around T−4/T−3 (depends on the paper version). |
| Harvey, Mazzoleni & Melone 2025, NBER w33554 | Institutional rebalancers | When equities are overweight: −17 bp the next day. Cost ≈ $16bn a year; front-running occurs. |
| Ariel 1990, *J. Finance* 45(5) | 1963–82 | Pre-holiday returns 9–14× other days. |
| Vergin & McGinnis 1999, *Appl. Fin. Econ.* 9(5) | 1987–96 | Pre-holiday effect gone for large firms. |
| Ko & Yang 2024, *Critical Finance Review* 13(3-4) | 1983–2019 | Pre-holiday now a small-firm effect only; large firms insignificant, especially after 1990. |
| Lucca & Moench 2015, *J. Finance* 70 | From 1994 (end ≈ 2011, inferred) | +49 bp in the 24 hours before scheduled FOMC announcements. |
| Kurov, Wolfe & Gilbert 2021, *Fin. Res. Letters* 40 | Through 2019 | The pre-FOMC drift disappeared after 2015. |
| Cieslak, Morse & Vissing-Jorgensen 2019, *J. Finance* 74(5) | Since 1994 | The equity premium was earned in even FOMC-cycle weeks. |
| Savor & Wilson 2013, *JFQA* 48(2) | 1958–2009 | 11.4 bp on announcement days vs 1.1 bp on other days. |
| Boyarchenko, Larsen & Whelan 2023, *RFS* 36(9); Liberty Street post, 1 Jul 2026 | ES futures 1998–2020 | The 2–3 a.m. drift was ≈ 3.6–3.7%/yr. **≈ 0 since 2021.** |
| Caporale & Plastun 2019, *Fin. Res. Letters* 31 | Crypto day-of-week | A Monday effect in BTC only. Trading results "not significantly different from the random ones". |

**What the table shows.** Every calendar family in the brief has a published decline or disappearance after discovery. The positive evidence that exists is either old (pre-2005) or from practitioners.

### 1.2 The in-house record [R]

- **No method has passed:** 39 trials, and none "works" [trials.json].
- **The one (c)-grade published effect failed after publication.** Intraday momentum was excluded at ≈ 4.5 standard errors [EVIDENCE.md:1186].
- **Cross-sectional momentum was null.** p = 0.073 against a pre-registered threshold of 0.05 [EVIDENCE.md:1278].
- **The overnight premium is real but untradeable.** Overnight compounded +367% against +75% intraday, but the trade loses at any cost this account gets [EVIDENCE.md:727-736].
- **The RSI dip-buy is a premium, not a strategy.** It is worth 1–3.5 pts/yr once collapsed into trades, and does not beat B&H [EVIDENCE.md:1093-1094].
- **The only line ever to beat B&H did so over six years, not 21** [EVIDENCE.md:690-692].

### 1.3 The arithmetic of being out of the market

**Being out costs the equity premium on idle days.**
- A random-timing rule with 19% exposure trails B&H by ≈ 7.3%/yr in expectation.
- Its chance of beating B&H over 21.5 years is ≈ 0 [C §5].
- So for inclusion rules, G1 alone is a powerful test.

**G1 is weak or blind in two other cases.**
- **Exclusion rules:** G1 is close to a coin flip. A random 2.4% exclusion beats B&H 24% of the time [C §5].
- **Leverage:** G1 is fooled outright.
- G4 and G5 exist to cover these cases.

**Raw Sharpe flatters rules that sit in cash** (defect 4b above).
- A part-time rule with random timing has a Sharpe of only about √f times the index's, where f is the share of sessions exposed.
- So the right yardstick is the exposure-matched placebo, not zero.

### 1.4 The prior, decomposed

The weights below are subjective; the arithmetic is in [C §10].

**Let S = the share of the 2005–26 return carried by a TOM-type window.** I put weights on five scenarios:

| scenario | weight | basis for the weight | P(full window beats B&H) | P(WORKS) |
|---|---|---|---|---|
| S ≈ 1.0 (fully intact) | 0.10 | McConnell–Xu's persistence to 2005 | 0.72 | ≈ 0.15 |
| S ≈ 0.9 | 0.10 | — | 0.61 | ≈ 0.07 |
| S ≈ 0.75 | 0.15 | — | 0.42 | ≈ 0.02 |
| S ≈ 0.5 | 0.30 | typical decay (McLean–Pontiff, Falck) | 0.16 | ≈ 0 |
| no effect | 0.35 | Maberly–Waggoner, Chen–Chua, Sullivan–Timmermann–White | ≈ 0 | ≈ 0 |

**What follows:**
- **P(full window beats B&H) ≈ 0.24** (weighted sum of the fourth column).
- **P(WORKS) ≈ 0.025** from the last column, plus ≈ 0.005–0.01 from luck, so **≈ 3%**.
- **Forward:** the expected surviving margin is ≈ 1 pt/yr against a five-year standard error of ≈ 7.7 pts/yr. So P(beats B&H over the next five years) = Φ(0.13) ≈ 0.55.

---

## 2 · Failure modes, written as checks

**"Check"** items belong in G0 or G6. **"Rule"** items are design constraints for the Flow Theorist.

### 2.0 Cross-cutting (every family)

**G-a · Fill model**
- `replay.py` has only one fill model, "next open" [R EVIDENCE.md:737; replay.py:229-231].
- The fill choice decides which overnight moves are captured, and SPY's 2005–26 return is mostly overnight [R EVIDENCE.md:727].
- *Rule:* the fill convention is part of the specification: MOC→MOC or MOO→MOO, stated.
- *Check:* a test proving a close-fill decision cannot read that day's close.

**G-b · Order cutoffs**
- **Known cutoffs:**
  - NYSE MOC/LOC entry closes at 15:50 [S NYSE fact sheet].
  - NYSE Arca, SPY's listing venue, freezes at 15:59 [S SEC filings].
  - Alpaca's `cls` cutoff of ~15:50 is the lead's figure [U].
  - Alpaca's `opg` window is 19:00–09:28 [S, a forum quote of Alpaca's docs].
- *Rule:* calendar-only decisions are fine at the close.
- *Rule:* a price-conditional decision that fills at the same day's close must use data from 15:45 or earlier, or the previous close.
- Minute data exist only for 2020–26.

**G-c · Auction price vs vendor price**
- A vendor's daily "open" is often the first consolidated print, not the primary-exchange auction. One vendor reprocessed its data over differences larger than 0.1% [S QuantConnect and Alpaca forums].
- The Alpaca files' open and close are IEX prints, not auction prices [R EVIDENCE.md:907-908].
- *Check:* add an adverse 3 bp to every open fill as a stress; the verdict must not flip.

**G-d · Costs per leg, stated explicitly**
- `nulltest` charges once per round trip; `replay` charges per fill [R EVIDENCE.md:905-906].
- **Primary: 2 bp a leg.** A SPY round trip is "nearer 0.5 bp than 2" [R EVIDENCE.md:458], plus auction uncertainty.
- **Stress: 5 bp a leg.**
- At 12 round trips a year, TOM pays 0.48%/yr at the primary cost and 1.2%/yr at the stress.

**G-e · Cash**
- **Use the actual 3-month T-bill rate** (FRED DTB3, daily), not a flat 3%. The repo itself calls 3% "generous" [R EVIDENCE.md:539-541].
  - FRED annual averages [S]: 0.15% (2009), 0.14% (2010), 0.05% (2015), 2.11% (2019), 5.28% (2023).
  - The fed funds target sat at 0–0.25% from 2008-12-16 to 2015-12, and again from 2020-03-15 [S].
- **The cash assumption moves results directly.** For a rule idle 81% of the time, each 1 pt of cash error moves its CAGR by 0.81 pt/yr [C §8].
- **Also report 0% cash.** If Daniel's idle cash would sit uninvested at the broker, the 0% figure is the one that applies to him [U: whether Alpaca pays interest].

**G-f · Tax**
- **The rates.** Gains on positions held 1 year or less are taxed at ordinary rates of 10–37%. Long-term gains are taxed at 0/15/20% [S IRS Topic 409].
- **The gap at equal pre-tax returns.** At 10.4% pre-tax for both:
  - a rule that realises gains yearly at 32% nets 7.1%/yr;
  - deferred B&H, taxed at 15% only at the end, nets 9.7% [C §9].
- **What the rule needs to tie after tax in a taxable account:** +2.3 pts/yr pre-tax at the 24% bracket, up to +4.9 pts at 37%.
- **Wash sales:** rebuying SPY within 30 days may defer losses [U this session].
- **The verdict is pre-tax.** Daniel must be asked which account type he uses.

**G-g · Benchmark dividend basis**
- **B&H must be total return.**
- **SPY:** the stooq file measures as adjusted only on 2020–26, with a first gap of −6.617% [R DATA.md:77-80]. Before 2020 its basis is assumed, not measured.
- **The other stooq files are largely unadjusted**, unevenly by symbol and by date [R DATA.md:55-65]:
  - DIA's first gap is 10.7%; EFA's is 14.3%;
  - TLT's is 2.2%, concentrated at the recent end;
  - GLD's is 0.000.
- *Rule:* no unadjusted file enters a calendar test unless it is first rebuilt as total return. GLD is the only long file with a clean basis.

**G-h · Calendar look-ahead**
- **Every calendar label must come from the schedule as it was known on the decision date.**
- **Holiday schedule:**
  - The NYSE publishes holiday calendars about 3 years ahead [S ICE releases].
  - Juneteenth is a closure only from 2022 [S].
  - Under NYSE Rule 7.2, New Year's Day 2022 (a Saturday) was not observed [S].
  - Early 13:00 closes produce half-day bars. Their MOC cutoff is presumably 12:50 [U, inferred from the "10 minutes before scheduled close" freeze].
- **Unscheduled closures in the window:** 2007-01-02, 2012-10-29/30, 2018-12-05 and 2025-01-09 [R EVIDENCE.md:930-931].
  - Carter's closure (2025-01-09) was announced on 2024-12-30 [S].
  - Sandy's (2012) came at about one day's notice [S dates; U exact time]. So 2012-10-26 cannot count as a known "pre-holiday" day, and October 2012's T−k counts shift.
  - The 2007-01-02 closure moves January 2007's T+1..T+3.
- **Data holes:**
  - 2011-02-17 is missing from SPY and from eight of the nine ETF long files; only QQQ's file has it [R EVIDENCE.md:929-933, 1103]. It is the Thursday of February 2011's opex week (the third Friday was 18 February).
  - QQQ also lacks 1999-11-16 [R EVIDENCE.md:935].
- *Check:* the leak-check analogue. Recompute every decision with calendar and data truncated at the decision date, and expect zero differences.
- *Check:* each closure above has a written handling rule.

**G-i · Few independent events; crisis clustering**
- How precisely each family's exposed-day vs other-day mean difference can be measured [C §6]:

| family | standard error | difference needed for t = 3 |
|---|---|---|
| TOM | 4.2 bp | 12.6 bp |
| pre-FOMC | 9.4 bp | 28 bp |
| pre-holiday | 8.9 bp | 27 bp |

- *Check:* episode counts, the top-5 share, and the drop-crisis test (all in G6).

**G-j · Regime and publication timing**
- The halves split at the midpoint session, around late 2015.
- That split coincides with the end of the first zero-rate period and with Kurov's FOMC break.
- Report the pre- and post-publication sub-windows of each family, but do not gate on them.

**G-k · Overlapping families**
- FOMC days, month-ends, quarterly opex, SPY ex-dividend dates and index rebalances share sessions.
- So two specifications from different families are correlated trials, not independent replications.
- *Check (report only):* rerun TOM excluding any window that contains a scheduled FOMC announcement.

**G-l · Crowding**
- At Daniel's size in SPY, capacity is irrelevant.
- Crowding instead moves the timing. Three documented shifts:
  - TOM moved to day 1 in the ETF era (Chen–Chua);
  - the month-end reversal sits around T−4/T−3 (Etula);
  - rebalancers get front-run (Harvey et al.).
- Every window shift is a new trial.

### 2.1 Turn of the month

- **T1 · Each window is a separate hypothesis.** T−1..T+3 (Lakonishok–Smidt, McConnell–Xu), T−4..T+3 (Etula) and day-1-only (Chen–Chua) are three different trials. Pick one, with a mechanism, before the run.
- **T2 · Fill convention** (see G-a). Use MOC→MOC for a window defined by closes. "Next-open" fills shift the window by one overnight.
- **T3 · Dividend artifact in SPY's own files.**
  - SPY goes ex-dividend on the third Friday of March, June, September and December [S]. Those are non-TOM days.
  - On the unadjusted nasdaq `SPY-1d-raw` file, those ex-date drops land outside the window. They amount to ≥ ~1%/yr, per the −6.6% gap over 2020–26.
  - This manufactures TOM outperformance and understates B&H.
  - *Check:* compute B&H on both bases over 2020–26 and report the difference.
- **T4 · Dividend artifacts in replication files.**
  - DIA goes ex monthly on the third Friday [S]. Its unadjusted file therefore flatters TOM.
  - TLT goes ex on the first business day of each month [S], inside the TOM window. Its file is only partly adjusted [R DATA.md:60; EVIDENCE.md:1056], so it can create or erase a TOM effect in one half only.
  - *Rule:* no TOM replication on stooq long files except GLD. Use GLD only if the stated mechanism predicts gold should show the effect.
- **T5 · Calendar handling** (see G-h). January 2007 and October 2012 each need a written rule.
- **T6 · The bar is high and the literature disagrees.**
  - The window must carry ≥ 81% of all return [C §3].
  - Intact through 2005 (McConnell–Xu); gone after 1990 in futures (Maberly–Waggoner); underperformed buy-and-hold as a switching rule in the ETF era (Chen–Chua).

### 2.2 Month-end stock–bond rebalancing

- **R1 · Long-or-flat form and its worth.**
  - The only long-or-flat version is "out of SPY on the predicted day(s)".
  - At 2 bp a leg it is worth at most +0.58%/yr intact, +0.07% at half strength, and −0.44% at zero [C §4].
  - Tracking error is ≈ 3%/yr, so even an intact effect gives t ≈ 0.9 over 21.5 years.
  - It cannot pass G5, which would need a Sharpe difference of about 0.11 or more at 97.6% exposure [C §2].
- **R2 · Signal timing** (see G-b). The month-to-date stock-minus-bond return must be known before the cutoff.
- **R3 · TLT's dividends bias the signal.** TLT's first-business-day ex-dates enter its month-to-date return. On an unadjusted file, bonds look worse than they were, so "equities overweight" fires more often [S; R DATA.md:60].
- **R4 · Every design choice is a trial.** The bond proxy, the threshold, the day(s), the target weights, and month-end vs quarter-end each count separately.
- **R5 · Our window is in-sample for the paper.**
  - The working paper's sample covers our window [U exact end date].
  - The first post-publication data are 2025–26.
  - Expect the usual 50–58% decay.

### 2.3 Pre-holiday

- **H1 · It cannot win standalone.** It needs ≥ 76% of all return on 3.6% of days. Ariel's 9–14× gives only 32–50% [C §3-4]. It can only work as an overlay, which is leverage.
- **H2 · Decay.** The effect is gone for large firms (Vergin–McGinnis), and insignificant for large firms after 1990 (Ko–Yang). The prior for SPY is null.
- **H3 · Calendar traps.**
  - Juneteenth only from 2022.
  - The Rule 7.2 Saturday convention.
  - Half-day sessions.
  - Sandy (2012).
  - Good Friday is an exchange holiday but not a federal one [U formal source].
- **H4 · Too few events to see anything smaller than published sizes.**
  - About 193 events; t = 3 needs ≈ 27 bp [C §6].
  - As an overlay [C §12]:
    - an intact 30 bp gives z ≈ 2.5 and P(passing G5) ≈ 0.29;
    - 15 bp gives z ≈ 0.9.

### 2.4 FOMC and macro announcements

- **F1 · Arithmetic.**
  - **Standalone pre-FOMC fails.** At the full 49 bp it reaches S = 0.33, against ≥ 0.75 needed [C §4].
  - **Even weeks fail G5 even when intact** [C §10].
  - **An overlay is the only live path.**
    - It passes G5 at the full 49 bp (z ≈ 4.2) but not at half that (z ≈ 1.8) [C §12].
    - Kurov reports the drift at zero after 2015, so G2's second half is the expected failure.
- **F2 · Which events count.** Use scheduled meetings only, from calendars published in advance. Intermeeting moves cannot be anticipated and must not be event days: 2008-01-22, 2008-10-08, 2020-03-03 and 2020-03-15 [S].
- **F3 · Daily bars measure a different window.** Lucca–Moench measure 2 p.m. on day t−1 to 2 p.m. on day t. A close-to-close daily bar also includes the post-announcement reaction, which is a different object. Minute data exist only for 2020–26.
- **F4 · Unverified regime changes:**
  - the drift may sit only in meetings with a press conference (Boguth et al., known only via a search summary [U]);
  - press-conference frequency changed in 2011 and 2019 [U];
  - the statement release time changed [U].
- **F5 · Use the calendar as published beforehand.** Macro release dates moved during government shutdowns [U], so use the advance calendars, not the realised dates.
- **F6 · Few events.** 8 a year gives 172 in total, about 86 per half. The standard error of the mean difference is ≈ 9.4 bp [C §6].

### 2.5 Options expiration

- **O1 · The definition changed during the window.**
  - Expirations went from monthly third-Fridays, to Friday weeklies, to Monday/Wednesday, to Tuesday (from 2022-04-18) and Thursday (from 2022-05-11) SPX expirations [S Cboe].
  - "Opex" concentration is diluted after 2022: a built-in regime break.
- **O2 · Ex-dividend dates sit on opex days.**
  - SPY's quarterly ex-date *is* the quarterly-opex Friday [S]. The unadjusted SPY file therefore shows a spurious drop every triple witching.
  - DIA's monthly ex-date is the monthly-opex Friday [S]. Its unadjusted stooq file therefore shows a spurious opex-day drop every month.
- **O3 · Unverified mechanics to check** [U]:
  - SPX settles AM, while SPY settles PM;
  - expiry moves to Thursday when the third Friday is a holiday;
  - index rebalances take effect after the quarterly third Friday.
- **O4 · Data hole.** The 2011-02-17 hole is the Thursday of that month's opex week (see G-h).
- **O5 · No index-timing evidence.** What exists is about individual stocks across the cross-section:
  - Ni–Pearson–Poteshman [R EVIDENCE.md];
  - Johnson & So, or Stivers & Sun — sources disagree on authorship [S].

### 2.6 Overnight/intraday splits and gaps

- **N1 · Contaminated.** The team already knows the 2005–26 overnight/intraday split, by halves [R EVIDENCE.md:727-731].
- **N2 · Costs kill it.**

| cost per leg | overnight-only return per year |
|---|---|
| 5 bp | −17% |
| 1 bp | +2.8% |
| 0.5 bp | +5.3% |
| (B&H for comparison) | ~10.4% |

  [R EVIDENCE.md:733-736]
- **N3 · The edge is smaller than the price error.** The edge is +3.1 bp a night [R EVIDENCE.md:728], while vendor-open vs auction-price differences can exceed 10 bp (see G-c).
- **N4 · Decay.** The overnight drift has been ≈ 0 since 2021 [S].
- **N5 · Gaps continue rather than reverse** (Caporale & Plastun, cited in EVIDENCE.md §14). Fade-the-gap rules have no support.
- **N6 · Ex-dates create fake losing nights.** On an unadjusted series, the ex-date drop lands overnight: four spurious negative nights a year for SPY.

### 2.7 Leveraged-ETF expressions

- **L1 · Leverage is not edge.**
  - 2× on random days can beat 1× B&H's CAGR in a rising window without any skill.
  - So the placebo must carry the same leverage.
  - G3 compares against **unlevered** B&H.
  - Each leverage level is its own trial.
- **L2 · The products don't cover the window.**
  - SSO started 2006-06-19 and UPRO 2009-06-23; UPRO's expense ratio is 0.89% [S issuer].
  - Before those dates a backtest uses synthetic leverage, which is not the product.
  - State the financing rate used [U: Alpaca's margin rate].
- **L3 · Daily reset makes multi-day returns path-dependent.**
  - A daily-reset fund's return depends on realised variance (Avellaneda & Zhang 2010) [S].
  - Its rebalancing creates order flow near the close, and it destroys value for multi-day holders (Cheng & Madhavan 2009) [S].
  - In crisis months, a multi-day window diverges from L × the index.
- **L4 · The autopilot halts at a 15% drawdown** [R autopilot.py:374, 565].
  - Report how many times the backtest crosses −15%.
  - Levered variants will trip the STOP, so live results will diverge from the backtest.
- **L5 · Gap and margin risk scale with leverage.** Overnight gap risk is multiplied by the leverage factor L, and so is margin-call risk.

### 2.8 Crypto

- **C1 · No data and no common window.** Nothing is on disk, and there is no 2005–26 history, so it cannot be graded against SPY on Daniel's window.
- **C2 · Fees.** Alpaca charges 15/25 bp maker/taker at Tier 1 (up to $100k traded per 30 days) [S Alpaca docs]. A round trip as a taker costs ≈ 50 bp, against ≈ 1–4 bp for SPY.
- **C3 · No official close.** Crypto trades 24/7 with no auction, so a "daily close" is a convention (UTC vs New York). Any calendar effect depends on that choice.
- **C4 · No calendar evidence.**
  - The BTC Monday effect is not significant in a trading simulation (Caporale & Plastun).
  - What predicts crypto returns is momentum and attention (Liu & Tsyvinski 2021) [S], not the calendar.
- **C5 · Structural breaks and venue risk** [U specifics].
- **Recommendation:** do not spend a trial here.

---

## 3 · The reading rule (proposed text for the freeze)

### 3.1 Definitions

**D1 · Account and ROI**
- Equity = position value + cash.
- Idle cash accrues the 3-month T-bill rate daily (FRED DTB3, with the day-count stated).
- **ROI = the CAGR of account equity over the scored window.** It is never return per day invested, per trade, or "annualised while in the market".
- Also report the 0%-cash case.

**D2 · Benchmark**
- B&H SPY total return over exactly the same scored sessions.
- Bought with the same first-fill type and price convention, and charged the same entry cost.

**D3 · Fills**
- The fill convention (MOC or MOO, stated) is part of the specification.
- Every input to a decision must be available before that venue's cutoff (see G-b).

**D4 · Costs**
- Per leg: 2 bp primary, 5 bp stress.
- A further stress adds an adverse 3 bp to every open fill (see G-c).

**D5 · Halves**
- Split at the midpoint *session index* of the scored window; score each half on its own.
- crosstest.py:81-90 already splits by bar, although the PREREG text says "date". Write "session".

**D6 · Episodes**
- An episode is a maximal run of exposed sessions.
- Runs separated by fewer than 5 idle sessions merge into one episode.

**D7 · Placebo (within-cycle placement)**
- A cycle is the interval between consecutive scheduled anchors of the rule: TOM entries, scheduled FOMC announcements, holidays, or calendar months for exclusion rules.
- Each exposure block is moved, intact, to a uniformly random start inside its own cycle, without crossing the cycle's ends.
- The placebo keeps the rule's leverage, number of legs, costs, cash and fill type.
- B = 10,000 draws, seed = 20261009 + specification index.
- p = (1 + #{placebo CAGR ≥ rule CAGR}) / (B + 1).
- A circular-shift placebo is reported as a robustness check.

**D8 · Trial count**
- k = the number of specifications frozen this round; N = 39 + k.

### 3.2 Gates

**G0 · Integrity.** Any failure makes the run VOID, and nothing is printed. Required:
- barqc PASS on every file;
- the calendar/data truncation check (G-h) shows zero differences;
- the leak check passes;
- a test confirms that a close fill cannot use that day's close for a price-conditional decision;
- every file's dividend basis is declared, and the benchmark is total return;
- one single invocation computes every gate and every stress, and prints the SHA-256 of the frozen pre-registration;
- **no performance number is printed unless G0 passes.**

**G1 · Gains, full window**
- CAGR_rule − CAGR_B&H > 0 at 2 bp a leg with T-bill cash.
- And ≥ 0 at 5 bp a leg.

**G2 · Gains, each half**
- CAGR_rule − CAGR_B&H > 0 in both halves, at 2 bp a leg.

**G3 · Risk**
- Maximum drawdown of account equity ≥ B&H's maximum drawdown − 0.5 pt.
- The 0.5-pt tolerance is a deliberate departure from the lead's "not worse". It stops a 97%-invested exclusion rule from failing on noise.
- Also report how many separate −15% episodes occur (the autopilot's STOP level).

**G4 · Timing skill**
- Placebo p < 0.05/k under Holm: sort the k p-values ascending and compare the i-th smallest with 0.05/(k − i + 1).
- And CAGR_rule > the placebo median CAGR in each half.

**G5 · Selection-adjusted Sharpe against the benchmark**
- DSR_bench ≥ 0.80 at N = 39 + k (method in §3.5).
- At N = 42 that means z ≥ 3.05: a family-wise false-positive rate ≈ 4.7%, equal to Bonferroni at 5% and to Harvey–Liu–Zhu's t > 3 [C §11].
- If the verdict flips at N = 100 (z ≥ 3.37), the result is PARTIAL.
- Report whether DSR_bench ≥ 0.95 ("strong").

**G6 · Breadth**
- At least 100 episodes in total, and at least 40 per half.
- Concentration: per episode, take the rule's log return minus the cash accrual over the same sessions. The 5 largest positive episodes supply no more than 50% of the sum over all episodes.
- Drop-crisis: CAGR_rule − placebo-median CAGR stays above zero when 2008-09-01→2009-06-30 and 2020-02-15→2020-04-30 are removed from both the rule and the placebo.

**G7 · Replication (veto only)**
- The identical rule on QQQ 1999-03-10→2005-02-24 has a CAGR above its own placebo median. The 9/11 closure and the 1999-11-16 hole must be handled.
- Any mechanism-implied instrument named in the freeze shows the predicted sign.
- A replication can never rescue a failed gate, and can never be the instrument that gets traded.

### 3.3 Verdicts (exhaustive)

1. **VOID** — G0 fails. A fixed rerun counts as the same trial only if nothing was printed.
2. **WORKS** — G0–G7 all pass. The rule is eligible for the forward paper period (§4.3). It is not yet eligible for money.
3. **PARTIAL — DO NOT TRADE** (G4 at unadjusted p < 0.05, but something else failed). Every failed gate is printed with its named reason:

| failed gate | named reason |
|---|---|
| G1 | "premium, not a strategy" |
| G2 | "unstable" |
| G3 | "riskier than holding" |
| G4 with Holm, or G5 | "lucky-sized" |
| G6 | "concentrated" |
| G7 | "did not replicate" |

4. **Unadjusted G4 p ≥ 0.05** has two outcomes:
   - G1–G3 all pass → **PARTIAL — "exposure or leverage, not timing"**;
   - otherwise → **NULL**.

### 3.4 Leverage

**Leverage variants are allowed only as separate trials, and are judged on the same scale:**
- account equity, with financing charged at a stated, actual rate;
  - after the product launched: the LETF's real NAV;
  - before launch: synthetic leverage plus the expense ratio;
- a placebo carrying the same leverage;
- G3 measured against unlevered B&H;
- the number of −15% STOP crossings reported.

**Recommendation:** no leverage variant this round unless a 1× version of the same signal has already passed.

### 3.5 Deflated Sharpe against the benchmark: the fix

**What is wrong now.**
- `crosstest.py:171-175` calls `combine.deflated_sharpe`. There, SR₀ = √V · E[max Z_N] (`combine.py:74`): the expected best of N **zero-mean** Sharpes.
- So the printed 0.982/0.959 only say "not zero" [R runs/crosstest-2026-09-11.txt:23,46].
- Yet that same run reports a null mean Sharpe of 0.54/0.46 [R :21,44] and benchmark Sharpes of 0.56/0.55 [R EVIDENCE.md:1237,1246].
- The variable `srs` (crosstest.py:169-170) was evidently meant for this centring and is never used.

**Preferred fix.**
1. Compute daily account returns **in excess of that day's T-bill accrual**, for both the rule and B&H, over the same sessions.
2. ΔSR = SR_rule − SR_B&H (annualised).
3. Estimate SE(ΔSR) with a paired circular-block bootstrap: blocks of 10 sessions, 5,000 resamples, a fixed seed. This is a non-studentised simplification of Ledoit & Wolf 2008 [S].
4. DSR_bench = Φ(ΔSR / SE − E[max Z_N]).
   - E[max Z_N] = (1−γ)Φ⁻¹(1−1/N) + γΦ⁻¹(1−1/(Ne)), with γ = 0.5772.
   - That is `combine.expected_max_sharpe(N, 1.0)`.

**Minimal patch** (if the existing function is kept):
- pass `sr = SR_rule,bar − SR_B&H,bar` and `var_sr = SE_bar²`;
- set skewness to 0 and kurtosis to 3.

**For a timing question** (as opposed to the benchmark question), centre on the placebo mean instead.

**Also fix the old pre-registration's wording.** PREREG:89-92 says the DSR "must exceed zero", which is vacuous for a probability. The new freeze must state a number.

### 3.6 What this rule can and cannot detect [C §10, §12]

| scenario | P(both halves) | z (Sharpe vs B&H) | P(G5) | P(WORKS), my combination |
|---|---|---|---|---|
| TOM, fully intact (S = 1.0) | 0.44 | 2.49 | 0.29 | ≈ 0.1–0.2 |
| TOM, S = 0.9 | 0.34 | 2.14 | 0.18 | ≈ 0.05–0.1 |
| TOM, S = 0.75 | 0.20 | 1.54 | 0.07 | ≈ 0.01–0.03 |
| TOM, S = 0.5 | 0.06 | 0.30 | 0.00 | ≈ 0 |
| Even weeks, fully intact | 0.31 | 1.04 | 0.02 | ≈ 0 |
| Pre-FOMC overlay, 49 bp in both halves | 1.00 | 4.18 | 0.87 | high, if the drift had survived post-2015 (it is reported gone) |
| Pre-FOMC overlay, 24.5 bp | 0.91 | 1.82 | 0.11 | low |
| Pre-holiday overlay, 30 bp | 0.97 | 2.50 | 0.29 | low (and the large-firm effect is reported gone) |

P(WORKS) for TOM combines P(both halves) and P(G5), which are positively correlated, with an assumed (subjective) ≈ 0.8 chance of passing the QQQ veto. G4 almost surely passes when the effect is intact: the timing t is ≈ 5.8 at S = 1, 4.0 at S = 0.75 and 2.2 at S = 0.5 [C §14].

**What the table means.**
- **The rule can only certify effects about as large as the published historical ones.** That is the honest limit of 21.5 years of daily data after 42 trials, not a flaw in the rule.
- **Wrongly saying "no" costs Daniel nothing relative to the benchmark,** because holding SPY *is* the benchmark. That is why this design accepts false negatives to avoid false positives.

---

## 4 · Trial budget and clean holdout

### 4.1 How many specifications, and what counts as a trial

- **k ≤ 2 (hard maximum 3).**
  - Each extra specification raises the Holm bar: p < 0.025 at k = 2, p < 0.0167 at k = 3.
  - Each extra specification multiplies the forking paths.
  - N barely moves: E[max Z] goes from 2.20 to 2.21 [C §1].
- **One trial** = event or window definition × instrument × fill convention × exit × leverage.
- **Not trials:**
  - pre-registered stresses (cost, cash, open-fill, N = 100), which can only veto;
  - the veto-only QQQ replication;
  - diagnostics that cannot change the verdict.
- **Trials:**
  - any instrument that could be traded if it passed;
  - any shift of the window (for example T−4 instead of T−1);
  - switching between MOC and MOO;
  - each leverage level;
  - any rerun after numbers were seen.
- **Trial count used in the gate: N = 39 + k. Sensitivity: N = 100.**
  - The 39 leaves out nulltest sweeps and `--no-record` runs [R trials.json:23-25].
  - The lead, not the sub-agents, should append the k rows to trials.json **before** the run, with `in_ledger: false`.
  - The ledger fails optimistically in a fresh clone [R DATA.md:238-247].

### 4.2 What data is clean

| Data | Status | Allowed use |
|---|---|---|
| Forward sessions after the freeze | Clean. | Implementation test (§4.3). |
| QQQ 1999-03-10 → 2005-02-24 (1,499 sessions) | Clean for calendar hypotheses, with caveats below. | G7 veto only. About 71 cycles: no power for significance. |
| SPY 2005-02-25 → 2026-09-02 (5,413 sessions) | Unused for calendar hypotheses, but heavily viewed. Overlaps the FOMC and rebalancing papers' discovery samples. **Not clean for overnight rules.** | The primary test, run once. |
| SPY sessions / minute bars 2020–26 | Already used for intraday momentum. | 15:45 signal checks only. |
| Alpaca total-return ETF files 2020–26 | Already used for the RSI replication. Same days as SPY. | Report only. |
| Stooq ETF long files except GLD | Dirty dividend basis. | Not for calendar tests unless rebuilt as total return. |

**The QQQ 1999–2005 segment in detail:**
- **Barely touched:** only the RSI nulltest used it [R EVIDENCE.md E-15]. The aligned tools cannot reach it [R DATA.md:164-167].
- **Nearly dividend-free:** one secondary source counts QQQ's distributions only from December 2003 [S partial].
- **Contains** the 9/11 closure and the 1999-11-16 hole [R EVIDENCE.md:934-935].
- **Not fresh for the literature:** it sits inside the published discovery samples (McConnell–Xu to 2005, Lucca–Moench from 1994).

### 4.3 Forward paper period (implementation, not evidence)

**Why P&L cannot be the test.** A forward P&L cannot confirm a calendar edge in any useful time [C §7]:
- reaching t = 2 on a 2%/yr edge at 17% tracking error takes ≈ 289 years;
- even at 3% tracking error it takes ≈ 9 years.

**Length.** At least 6 months **and** 6 complete event cycles.

**Pass requires all four:**
1. Every scheduled order is submitted before the venue cutoff and fills — zero misses.
2. The median absolute deviation of fills from the official auction price is ≤ 2 bp a leg, and the mean adverse deviation is ≤ 2 bp.
3. The live decision log matches an offline replay over the same dates, with zero mismatches.
4. Each window's paper return is within ±5 bp of the engine's return for that window on official prices.

**What does not count.**
- A paper loss is not a failure, and a paper gain is not a pass.
- **Kill switch:** an implementation failure, or a drawdown beyond the backtest's worst for this rule.

**What happens after.**
- Any decision to commit money is Daniel's.
- The Red Team's position: no forward horizon he would wait for can confirm the edge statistically.
- That decision therefore rests on the WORKS verdict plus implementation fidelity.

---

## 5 · What I could not verify

**Source access**
- **No full text of any paper was read.** WebFetch failed DNS on every host, and the proxy refused direct downloads.
- Every [S] item rests on search-result text: abstracts, publisher listings and secondary summaries.
- **The Suhonen, Wiecki and Chen–Chua details** come from secondary summaries.
- **The Etula T−4 vs T−3 detail** varies between versions of the paper.

**Search budget**
- The turn's shared web-search budget ran out near the end. As a result, these went unchecked:
  - the S&P 500 move on 2008-10-28 and its timing relative to that FOMC meeting — kept only as a G-k check, not as a claim;
  - the wash-sale rule;
  - the dates of FOMC press-conference and statement-time changes.

**Unverified [U] items**
- Alpaca: the 15:50 `cls` cutoff (the lead's figure), the `opg` window (a forum quote of Alpaca's docs), the margin rate, and interest on idle cash.
- Exchange mechanics: the early-close MOC cutoff (inferred as 12:50), SPX AM settlement, expiry shifting when the third Friday is a holiday, and S&P rebalance timing.
- Data: SPY's stooq dividend basis before 2020 cannot be checked on disk.
- Cash rates: FRED annual T-bill averages were obtained for 11 of 22 years only; the other years are not stated.

**Deliberately not used**
- A 1999–2017 TOM study reporting 13.8% vs 1.2% annualised; its journal could not be identified.

**Assumptions in my own numbers**
- The weights in §1.4 are subjective, and stated as such.
- All [C] figures are normal and log-growth approximations, assuming exposed days are as volatile as other days.
- The repo's B&H Sharpe (0.61) is computed on raw returns; my formula's (0.53) is on excess returns.

---

## Sources

**Decay and multiple testing**
- [McLean & Pontiff 2016 (listing)](https://academicnewsletter.sufe.edu.cn/info/359722)
- [McLean & Pontiff 2016 (PDF)](https://counterpointfunds.com/wp-content/uploads/2017/07/PredictabilityMcleanPontiff.pdf)
- [Harvey, Liu & Zhu (NBER w20592)](https://www.nber.org/papers/w20592)
- [Bailey & López de Prado, Deflated Sharpe Ratio (SSRN 2460551)](https://papers.ssrn.com/abstract=2460551)
- [Bailey & López de Prado 2012, Sharpe Ratio Efficient Frontier](https://ideas.repec.org/a/rsk/journ4/2223785.html)
- [Bailey et al., Probability of Backtest Overfitting](https://ideas.repec.org/a/rsk/journ0/2471206.html)
- [Harvey & Liu 2015, Backtesting](https://people.duke.edu/~charvey/Research/Published_Papers/P120_Backtesting.PDF)
- [Sullivan, Timmermann & White 2001](https://ideas.repec.org/a/eee/econom/v105y2001i1p249-286.html)
- [Suhonen et al. (Alpha Architect summary)](https://alphaarchitect.com/?p=36892)
- [Suhonen et al. (CXO summary)](https://www.cxoadvisory.com/big-ideas/live-performance-of-alternative-beta-products/)
- [Wiecki et al. (Quantpedia summary)](https://quantpedia.com/?p=673)
- [Wiecki et al. (CXO summary)](https://www.cxoadvisory.com/big-ideas/in-sample-vs-out-of-sample-performance-of-888-trading-strategies)
- [Hou, Xue & Zhang 2020](https://ideas.repec.org/a/oup/rfinst/v33y2020i5p2019-2133..html)
- [Jensen, Kelly & Pedersen (NBER w28432)](https://www.nber.org/papers/w28432)
- [Falck, Rej & Thesmar (MIT DSpace)](https://dspace.mit.edu/handle/1721.1/163650)
- [Schwert 2003 (NBER w9277)](https://nber.org/papers/w9277)
- [Ledoit & Wolf 2008](https://www.uzh.ch/cmsssl/econ/dam/jcr:ffffffff-935a-b0d6-0000-00007214c2bc/jef_2008pdf.pdf)
- [Lo 2002](https://ideas.repec.org/a/taf/ufajxx/v58y2002i4p36-52.html)

**Turn of the month and month-end flows**
- [Lakonishok & Smidt 1988](https://academicnewsletter.sufe.edu.cn/info/355994)
- [McConnell & Xu 2008](https://ideas.repec.org/a/taf/ufajxx/v64y2008i2p49-64.html)
- [Maberly & Waggoner 2000](https://www.atlantafed.org/research/publications/wp/2000/11.aspx)
- [Chen & Chua 2011](https://www.financialplanningassociation.org/article/journal/APR11-turn-month-anomaly-age-etfs-reexamination-return-enhancement-strategies)
- [Etula et al. 2020](https://academic.oup.com/rfs/article/33/1/75/5494694)
- [Harvey, Mazzoleni & Melone (NBER w33554)](https://www.nber.org/papers/w33554)
- [Duke Fuqua summary of Harvey, Mazzoleni & Melone](https://www.fuqua.duke.edu/duke-fuqua-insights/what-do-pensions-lose-from-rebalancing)

**Pre-holiday**
- [Ariel 1990](https://ideas.repec.org/a/bla/jfinan/v45y1990i5p1611-26.html)
- [Vergin & McGinnis 1999](https://ideas.repec.org/a/taf/apfiec/v9y1999i5p477-482.html)
- [Ko & Yang 2024](https://nowpublishers.com/article/Details/CFR-0111)

**FOMC and macro announcements**
- [Lucca & Moench (VoxEU)](https://cepr.org/voxeu/columns/predictable-movements-asset-prices-around-fomc-meetings)
- [Kurov, Wolfe & Gilbert 2021](https://ideas.repec.org/a/eee/finlet/v40y2021ics1544612320315956.html)
- [Cieslak, Morse & Vissing-Jorgensen](https://papers.ssrn.com/abstract=2687614)
- [Savor & Wilson 2013](https://ideas.repec.org/a/cup/jfinqa/v48y2013i02p343-375_00.html)

**Overnight returns**
- [Lou, Polk & Skouras 2019](https://researchonline.lse.ac.uk/id/eprint/87481)
- [Boyarchenko, Larsen & Whelan (NY Fed SR 917)](https://www.newyorkfed.org/medialibrary/media/research/staff_reports/sr917.pdf)
- [The Disappearing Overnight Drift (Liberty Street, 2026)](https://libertystreeteconomics.newyorkfed.org/2026/07/the-disappearing-overnight-drift/)

**Leveraged ETFs**
- [Cheng & Madhavan 2009](https://joim.com/dynamics-leveraged-inverse-exchange-traded-funds)
- [Avellaneda & Zhang 2010](https://epubs.siam.org/doi/10.1137/090760805)
- [ProShares UPRO](https://www.proshares.com/our-etfs/leveraged-and-inverse/upro)
- [SSO (stockanalysis)](https://stockanalysis.com/etf/sso)

**Crypto**
- [Caporale & Plastun 2019](https://bura.brunel.ac.uk/handle/2438/17208)
- [Liu & Tsyvinski 2021](https://ideas.repec.org/a/oup/rfinst/v34y2021i6p2689-2727..html)
- [Alpaca crypto fees](https://docs.alpaca.markets/docs/crypto-fees)

**Order cutoffs and auction prices**
- [NYSE closing auction fact sheet](https://www.nyse.com/publicdocs/nyse/NYSE_Auctions_Closing_Process_Fact_Sheet.pdf)
- [SEC 34-84804 (NYSE Arca 15:59)](https://www.sec.gov/files/rules/sro/nyse/2018/34-84804.pdf)
- [SEC 34-91479 (Cboe BZX)](https://www.sec.gov/files/rules/sro/cboebzx/2021/34-91479.pdf)
- [QuantConnect forum: Alpaca OPG window](https://www.quantconnect.com/forum/discussion/18268)
- [Alpaca forum: daily bar prices vs auction prices](https://forum.alpaca.markets/t/open-close-daily-bar-prices-vs-open-close-auction-prices-on-primary-exchange/14227)
- [QuantConnect forum: auction-price reprocessing](https://www.quantconnect.com/forum/discussion/9345)

**Dividend calendars**
- [SPY ex-dates (digrin)](https://www.digrin.com/stocks/detail/SPY/)
- [SPY ex-dates (dividendvision)](https://www.dividendvision.com/dividends/spy-dividend-calendar)
- [TLT ex-dates](https://stockanalysis.com/etf/tlt/dividend/)
- [DIA ex-dates](https://stockanalysis.com/etf/DIA/dividend/)
- [QQQ distributions](https://www.wisesheets.io/etf/QQQ/dividends)

**Holidays, closures and rates**
- [NYSE 2022–24 holiday calendar](https://ir.theice.com/press/news-details/2021/NYSE-Group-Announces-2022-2023-and-2024-Holiday-and-Early-Closings-Calendar/default.aspx)
- [Juneteenth added](https://www.thecorporatecounsel.net/blog/2021/10/nyse-makes-juneteenth-a-new-market-holiday.html)
- [Carter closure (NYSE)](https://ir.theice.com/press/news-details/2024/The-New-York-Stock-Exchange-Will-Close-Markets-on-January-9-to-Honor-the-Passing-of-Former-President-Jimmy-Carter-on-National-Day-of-Mourning/default.aspx)
- [Sandy closure](https://investinglive.com/news/!/nyse-euronext-confirms-us-mkt-close-tues-20121029/)
- [Intermeeting cuts](https://247wallst.com/economy/2020/03/03/modern-history-of-surprise-rate-cuts-do-they-actually-work/2/)
- [Fed funds history (Chicago Fed)](https://www.chicagofed.org/research/dual-mandate/the-federal-funds-rate)
- [FRED 3-month T-bill (annual)](https://fred.stlouisfed.org/data/RIFLGFCM03NA)
- [Cboe Tue/Thu SPX expirations](https://ir.cboe.com/news/news-details/2022/Cboe-Plans-to-List-SPX-Tuesday-Thursday-Expiring-Weeklys-Options-02-03-2022/default.aspx)
- [IRS Topic 409](https://www.irs.gov/taxtopics/tc409)
