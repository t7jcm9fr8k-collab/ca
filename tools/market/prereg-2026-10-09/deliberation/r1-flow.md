# Round 1 — Flow Theorist: price-insensitive flows → once/twice-a-day rules

*This round is blind. I did not open any bar file or any other agent's output, and I computed no statistic from market data. Every number comes from a named repo file or from a published source found by web search. The agent proxy refused every direct page fetch (HTTP 403 on SSRN, NBER, OUP, the Fed, arXiv, AEA and Alpaca's docs). So "verified" here means **confirmed in search-result text — an abstract, a snippet or a table excerpt — not read in full**. The shared web-search budget ran out before I finished; §8 lists what that left open.*

---

## 0 · Conclusions

1. **One mechanism deserves the trial: the month-end cash cycle.** Etula, Rinne, Suominen & Vaittinen (RFS 2020, "Dash for Cash") tie the turn-of-the-month effect to a named forced flow:
   - Pension funds, insurers and mutual funds sell equities in the days before the month's last business day (T), to fund payments due on T.
   - The recipients reinvest afterwards.
   - The authors tie the timing to the 3-day settlement cycle.

   It has the largest published effect I found. It needs nothing beyond the SPY file, the NYSE calendar already in `barqc.py` and a T-bill series. And the market has since handed us a test specific to the mechanism: US settlement moved from T+3 to **T+2 on 2017-09-05** and to **T+1 on 2024-05-28**, so the selling window should have moved one session later each time. **I recommend pre-registering R1b (§3). Add nothing else unless the event dates for R2 can be built cleanly.**

2. **Unlevered "sidestep the weak days" rules are unlikely to beat buy-and-hold on this sample.** SPY averaged **+4.6 bp a session** over 2005–2026 (+3.1 overnight and +1.5 intraday; EVIDENCE.md §C).
   - A sidestep pays only if the skipped window returns less than T-bills.
   - The best published negative window is the dash-for-cash selling days: −3.4% annualized in-sample, about −1.35 bp a session. It clears that bar only at close to its full published depth.
   - Effects usually shrink after publication.

   P(R1a beats buy-and-hold) ≈ 0.25.

3. **For any 2x variant, "beats buy-and-hold on CAGR" mostly measures leverage.** A 2x overlay on five *random* sessions a month would beat SPY's CAGR with probability ≈ 0.8 at 1 bp a side, because 2005–2026 paid a large equity premium. Two bars are honest for these variants:
   - a constant-leverage SPY at the rule's own average exposure;
   - a placebo that moves the windows to random positions in the month.

   I'd ask the Red Team to read every 2x variant against those two, not against 1x SPY.

4. **The limit is statistical power, not cleverness.** At published effect sizes, 21 years of one index gives roughly t ≈ 3.1 for R1b, ≈ 2.4 for the FOMC cycle and ≈ 2 at best for announcement days.
   - Assume the typical post-publication decay: −58% across 97 cross-sectional predictors (McLean & Pontiff 2016). That is an analogy for calendar effects, not a measurement of them. Under it, each figure falls to t ≈ 1.
   - **The most likely verdict for every rule here is "positive point estimate, not proven."**
   - A null would not show the flow is absent. A pass would rest on a handful of crisis months.

5. **The overnight fact gives one leg convention for every rule.** Raise exposure at the closing auction (MOC) of the session before a window. Cut it at the opening auction (MOO) of the session after. Every boundary night is then held at the higher exposure. This costs no extra fill, and it keeps one more night of the premium per window than close-to-close legs do.

6. **Month-end windows and announcement days overlap.** The Employment Situation report usually lands in the first days of a month, inside T…T+3, and some FOMC meetings end in a month's last days. A pass on both R1 and R2 would not be two independent witnesses.

7. **Everything else I examined is weaker or not new:**

   | Flow | Why it was set aside |
   |---|---|
   | Leveraged-ETF rebalancing | Measured as economically insignificant; its late-day leg is what the repo's three intraday-momentum trials already priced |
   | Vol-control deleveraging | It is the other side of the repo's tested reversal premium |
   | Index reconstitutions | No direction at the index level |
   | Pre-holiday | Now a small-cap effect |
   | January / tax-loss | Faded since the early 1990s |
   | Pre-FOMC drift | Gone after 2015 |
   | Buyback blackouts | No measured market effect |
   | Dividend-reinvestment pressure | Real, but needs a payment calendar that is not on disk |

---

## 1 · The flows, one by one

Segments: **N** = close→open (the night), **D** = open→close (the session).

| # | Flow | Who is forced, and when | Size | Why arbitrage leaves it | Predicted sign · segment | Best ETF | Verdict |
|---|---|---|---|---|---|---|---|
| 1 | Pay-cycle inflows (payroll, 401(k), reinvested pension receipts) | Plan contributions and recipients of month-end payments, around T…T+3; also mid-month paydays | **Unknown.** McConnell & Xu (FAJ 2008) found **no** evidence that volume or net equity-fund flows are higher at turns of the month, even though 1926–2005 equity returns came only at turns of the month (31 of 35 countries) | Diffuse; may barely exist as a flow that moves prices | + · D and the closing prints of T…T+3 (funds buy at NAV) | SPY | Folded into R1 as its reinvestment leg |
| 2 | **Dash for cash** | Pensions, insurers and mutual funds raising cash for payments due on T. Pension payments must be in accounts on T's morning. Under T+3: selling T−8…T−4; reversal T−3…T−1; reinvestment T…T+3; weak T+4…T+8 | S&P 500 −3.4% annualized over T−8…T−4 vs +28.6% over T−3…T+3. Source: 2015 working paper; the authors' slides start the sample in July 1995. Published-version magnitudes not read | Catching the reversal means carrying a week of index risk into month-end, when dealer balance sheets are tightest. The authors find the effect is stronger when volatility is high | − then + · selling in the sessions and closes of W−; reversal from the last W− close | SPY. Park in T-bills, not bonds: Treasury yields also peak a few days before month-end (same paper) | **R1** |
| 3 | Pension and balanced-fund rebalancing after a stock–bond gap | DB pensions, target-date and 60/40 funds on calendar or threshold rules. Pressure is in the last four trading days, avoiding the very last day; it resolves within about 2 weeks | Calendar signal ≈ −17 bp in equities, threshold ≈ −16 bp, bonds +2 to +4 bp (regression horizon not confirmed). Cost to funds ≈ $16bn a year ≈ 8 bp a year (Harvey, Mazzoleni & Melone, NBER w33554, 2025). Bank-desk forecasts reported in the press: about $20bn of pension equity selling for one month-end (May 2025), and more than $25bn (April 2026) | Front-runners exist and collect the $16bn, but they carry index risk. Crowding grows as desks publish forecasts | Conditional: if stocks led month-to-date, weaker last days; if bonds led, stronger · D and closes | SPY vs a Treasury total-return series | **R3** (a variant of R1; not this round) |
| 4 | Index reconstitutions (S&P quarterly, Russell) | Index funds, at the close on the effective date | Not pursued | — | None at index level: additions are bought and deletions sold inside the same index | none | Excluded |
| 5 | Option-expiration hedge unwind | Dealers who are short customer-owned puts buy back their hedges as deltas decay into the third Friday, then re-hedge new protection afterwards | S&P 100 stocks with heavy option activity have high returns in expiration week and modestly lower returns the week after (Stivers & Sun 2013). No peer-reviewed index-level magnitude found. Pinning: 16.5 bp (Ni, Pearson & Poteshman 2005, in EVIDENCE.md) | Dealer positioning cannot be identified from public open interest (EVIDENCE.md §8); 0DTE options have changed the gamma book | + into the third Friday, softer the week after · D | SPY | **R5** (low prior) |
| 6 | Leveraged / inverse ETF rebalancing | 2x, 3x and inverse funds, at the close. Demand ∝ (L²−L)·AUM·day's return: coefficient 2 for a +2x fund, 6 for +3x or −2x, always in the direction of the day's move (Cheng & Madhavan 2009, as restated in arXiv 2608.03703) | AUM unknown (not verified). Capital flows offset much of the rebalancing; the impact on late-day returns is "economically insignificant" (Ivanov & Lenkey, J. Financial Markets 2018; US equity ETFs 2006–14) | The closing auction absorbs it; creations and redemptions offset it | With the day's move into the close; any reversal is in N. Trading it needs today's return before the MOC cutoff, which daily bars don't show | — | Excluded: intraday-momentum trials 1–3 already priced the late-day leg (a powered null) |
| 7 | Vol-targeting / risk-parity deleveraging | Funds keyed to trailing realized volatility, selling for days after a spike | Unknown (only practitioner estimates, none verified) | Spread over days; the counter-trade is the liquidity-provision reversal | − for days after a spike. But the repo's survivor (RSI<30, 5-day hold, 30 witnesses) shows the reversal dominates at that horizon | SPY | Excluded: already tested from the other side (`rsi_dip`, `vol_target`) |
| 8 | Overnight risk transfer | Liquidity providers who absorb the closing imbalance carry it overnight and are paid when overseas buyers arrive (Boyarchenko, Larsen & Whelan, RFS 2023). Clienteles also split by session (Lou, Polk & Skouras, JFE 2019) | SPY 2005–26: +3.1 bp a night vs +1.5 bp a session, in both halves (EVIDENCE.md §C). The authors' own 2026 update: the 02:00–03:00 ET futures window, which earned about 3.7% a year, has averaged near zero since 2021 (Liberty Street Economics, 2026-07-01) | Harvesting it alone takes two fills a day; EVIDENCE §C found that loses to holding at ≥1 bp a leg. Gap risk | + · N. Larger after selloffs than after rallies (Boyarchenko, Larsen & Whelan) | SPY | The design constraint in §2, and **R6** (no trial) |
| 9 | Holiday and pre-weekend inventory | Market makers and short sellers flattening before closures | Ariel (JF 1990): pre-holiday returns 9–14× other days, 1963–82. Out of sample to 2019 the premium survives only in small firms; the large-firm difference is insignificant, especially after 1990 (Ko & Yang, Critical Finance Review 2024). Day-of-week effects fade after the early 1990s (2026 calendar-anomaly re-test) | Cheap to arbitrage in large caps | ≈ 0 for SPY | IWM, if anything | Excluded |
| 10 | Tax-motivated year-end flows | Taxable investors harvesting losses in December and buying back in January; funds with an October fiscal year | The January effect fades after the early 1990s (2026 re-test); concentrated in small caps | Small-cap trading costs; one event a year | − late December, + early January, in small caps | IWM | Excluded: 21 observations |
| 11 | **Scheduled macro announcements** | Not a flow: a premium for holding through the scheduled resolution of macro risk | Savor & Wilson (JFQA 2013): 11.4 bp excess on announcement days vs 1.1 bp on other days, 1958–2009. Ai, Bansal & Guo (NBER w31923, 2023, Table 1): 1961–2023, about 44 days a year, 10.68 vs 0.93 bp, 4.65% a year ≈ 71% of the 6.59% premium; 16.33 bp per announcement from January 2020 to August 2023. The FOMC component (Lucca & Moench, JF 2015: over 80% of the 1994–2011 premium earned in the 24 hours before statements) essentially disappeared after 2015 (Kurov, Wolfe & Gilbert, FRL 2021) | It is compensation for bearing the jump | + · N for 08:30 releases (the risk resolves before the open); the D of the day for FOMC (14:00) | SPY | **R2** |
| 12 | FOMC communication cycle | Not a flow: Fed news arriving on a two-week rhythm | Since 1994 the equity premium was earned entirely in even weeks (0, 2, 4, 6) of FOMC cycle time, with week 0 starting the day before a scheduled announcement (Cieslak, Morse & Vissing-Jorgensen, JF 2019). No test after 2016 found | — | + in even weeks, ≈ 0 in odd · all segments | SPY | **R4** (low prior) |
| 13 | Dividend reinvestment | Holders reinvesting cash dividends, mostly into other stocks | Market returns on the top quintile of aggregate payment days ≈ 4× those of the bottom quintile; market price multiplier 1.5–2.3 (Hartzmark & Solomon, "Predictable Price Pressure", NBER w30688) | Small per day; you need the payment calendar | + on heavy payment days | SPY | Excluded for data: needs a daily aggregate payment calendar |
| 14 | Month-end Treasury demand | Bond funds tracking indexes; window dressing | Treasury excess returns are positive and significant only in the last few days of the month, 1990–2018, Sharpe ≈ 1 (Hartley & Schwarz 2019 working paper). A TLT test since 2002 did not corroborate it (CXO) | — | + in the last days · bonds | TLT / IEF | Not a lever on SPY gains. Consistent with parking in T-bills, not bonds, during W− |
| 15 | Buyback blackout windows | Companies pausing buybacks before earnings | No negative market effect found (Alpha Architect 2019, headline). 10b5-1 plans keep buying through blackouts | — | ≈ 0 | — | Excluded |

---

## 2 · Legs: what the overnight fact decides

SPY earns about two-thirds of its daily return overnight (+3.1 bp a night vs +1.5 bp a session; EVIDENCE.md §C). Every rule below is therefore written as exposure windows defined on sessions, with one convention:

- **Exposure goes up at the MOC (`cls`) of the session before a window, and comes down at the MOO (`opg`) of the session after it.**
- **A zero-exposure (sidestep) window starts with a sale at the MOO of its first session and ends with a purchase at the MOC of its last.**

Each boundary night is then held at the higher of the two exposures. This uses the same number of fills as close→close legs, and gains one night of premium per window. The convention comes from the overnight fact alone, not from any look at window returns. A sidestep window still gives up its inner nights; that is the price of sidestepping a multi-day window.

**For the Bench.** Each session splits into a night segment N_d = close(d−1)→open(d) and a session segment D_d = open(d)→close(d). The exposure in force applies to each segment. `replay.py`'s single fill model (next open only) cannot express an MOC leg. For a pure calendar rule, filling at the decision day's close is not look-ahead, because the decision is known before that session starts.

---

## 3 · The candidate rules

### Shared definitions (every rule)

- **Sessions.** The dates in `bars/SPY-1d.csv` (stooq, dividend-adjusted, 2005-02-25 → 2026-09-02; DATA.md §1). Offsets count sessions.
  - Every scheduled date is knowable in advance from `barqc.nyse_holidays`.
  - The window contains five unscheduled closures: 2007-01-02, 2012-10-29/30, 2018-12-05 and 2025-01-09 (EVIDENCE.md §E-15). None is a month-end. They shift a few offsets by one session in those months; accept that and note it.
- **T_m** is the last session of calendar month m. **T_m+k** is the k-th session after it.
- **Prices.** SPY opens and closes from the same adjusted file. The Bench should confirm that the opens carry the same adjustment factor as the closes; otherwise ex-dividend nights are corrupted.
- **Cash.** The 3-month T-bill (FRED DTB3), accrued per calendar day. If it can't be obtained, report at 3% (the repo convention, which EVIDENCE.md calls generous for 2009–2021) and at 0% (cash at a broker may earn nothing).
- **2x exposure** is always a separately labelled variant.
  - Backtest: SPY plus 1x borrowed at the T-bill rate + 1.0% a year. The +1.0% is my assumption, not a quoted rate.
  - Live: Reg-T margin, or switching into SSO (ProShares Ultra S&P500; inception 2006-06-19; expense ratio 0.87–0.91% depending on the source).
- **Cost per side.**
  - SPY at either auction: 1 bp of traded exposure. EVIDENCE.md §G puts a small SPY market order's real round trip at "nearer half a point to one".
  - Report every result at 5 bp as well (the repo convention).
  - SSO, if used live: assume 3 bp (my assumption).
- **Benchmarks.**
  1. 1x SPY buy-and-hold from the same first decision.
  2. For 2x variants: constant-leverage SPY at the rule's realized average exposure, with the same financing.
  3. A placebo that puts each month's windows at a random other position in the month, keeping their lengths and order.
- **Halves.** Split at the midpoint date (about 2015-12). For R1, R4 and the FOMC part of R2, this also separates "inside the samples the effect was found in" (first half) from "after publication" (second half). **Read the second half as the test.**

### R1 — Month-end cash cycle ("dash for cash"), adjusted for the settlement cycle

**Mechanism.** Institutions sell before T so they have cash on T. The reversal starts after the last trade date that settles by T, and recipients reinvest from T to T+3 (§1, row 2).

**Settlement lag s** for month m: **3** if T_m < 2017-09-05, **2** if T_m < 2024-05-28, **1** otherwise. These are the SEC compliance dates.

**Windows.**

| Era | W− (5 sessions, selling) | W+ (reversal + reinvestment) |
|---|---|---|
| T+3 (s = 3) | T−8 … T−4 | T−3 … T+3 (7 sessions) |
| T+2 (s = 2) | T−7 … T−3 | T−2 … T+3 (6 sessions) |
| T+1 (s = 1) | T−6 … T−2 | T−1 … T+3 (5 sessions) |

In general, W− = sessions T−(s+5) … T−(s+1), and W+ = sessions T−s … T+3.

**R1a — unlevered sidestep.** This is the only unlevered rule here aimed at beating buy-and-hold on CAGR.
- MOO (`opg`) on the first session of W−: sell all SPY and hold T-bills.
- MOC (`cls`) on the last session of W−: buy SPY back to 100%.
- 100% SPY at all other times.
- Two fills a month.

**R1b — 2x variant (my recommendation).**
- MOO on the first session of W−: sell all SPY and hold T-bills.
- MOC on the last session of W−: buy up to 2x.
- MOO on session T+4: cut back to 1x.
- The result: 0x from open(T−(s+5)) to close(T−(s+1)); 2x from that close to open(T+4); 1x otherwise.
- Three orders a month, trading four units of exposure in total. Average exposure ≈ 1.1 (the exact figure comes from the run).

**Inputs:** the calendar only. **Decision time:** known in advance. Queue `opg` orders after 19:00 the evening before, and `cls` orders any time before the cutoff. **Capital otherwise:** T-bills. Not bonds, because Treasuries are sold in the same pre-payment window. **Cost:** 1 bp per side (5 bp reported).

**What must be true to beat holding.**
- **R1a:** SPY's return over W− must sit below the T-bill return by more than the cost of two fills, which means close to its full published depth.
- **R1b:** the extra exposure in W+ (net of financing) must out-earn what the sidestep gives up in W−, by more than about 4 bp a month, to beat buy-and-hold.
- **R1b vs constant 1.1x SPY:** the W+/W− spread must exceed what the same windows earn when placed at random in the month.

**The one falsifiable prediction.** In 2016-01 → 2026-09, SPY's mean return over W+ (close T−(s+1) → open T+4) exceeds its mean over W− (open T−(s+5) → close T−(s+1)).
- The published in-sample levels imply about +80 bp a month for the tilt. That is implausibly large for the most-watched index, which is itself a reason to expect decay.
- A decayed but real effect would be about +30 bp a month.
- A spread of zero or less in that half falsifies the rule.

**Mechanism diagnostic.** This is computed in the same run and declared in advance; it is never used to choose between rules.
- Under T+2 (2017-09 → 2024-05), session T−3 should now behave like W− (below the month's average), not like W+.
- Under T+1, sessions T−3 and T−2 should do the same.
- If T−3 stays strong after 2017, the settlement story is wrong, even if a turn-of-month effect is real.

**Alternative — freeze one, not both.** The literature's fixed windows: W− = T−8…T−4 and W+ = T−3…T+3 in every year. I pick the adjusted version because it is what the mechanism predicts, and it can fail in a specific way.

### R2 — Scheduled macro announcements (the risk-resolution premium)

**Event sessions** (2005–2026):
- scheduled FOMC statement days, with no unscheduled or intermeeting actions;
- BLS Employment Situation release days;
- BLS CPI release days.

Only dates that were public at least one session in advance count. A release on a non-session day maps to the next session.

**Windows** (by §2):
- 08:30 releases: the night before, close(d−1) → open(d).
- FOMC (statement around 14:00): close(d−1) → open(d+1).
- Overlapping windows merge.

**R2a — unlevered.** T-bills by default, 100% SPY inside the windows. This is a Sharpe design. It cannot beat buy-and-hold on CAGR unless time outside events earns less than T-bills; Ai, Bansal & Guo measure +0.93 bp a day excess on non-event days.

**R2b — 2x variant.** 1x by default, 2x inside the windows. Buy at the MOC on d−1 and cut at the next MOO. About 32 events a year (the exact count comes from the list), two fills each.

**What must be true to beat holding.** R2b beats buy-and-hold if its windows return more than financing plus about 2 bp of cost. At 1 bp a side that is almost automatic from the equity premium alone. So it must be read against constant leverage and against a placebo of non-event windows with the same shape.

**Prediction.** SPY's mean return per event window exceeds the mean over non-event windows of the same shape by at least 5 bp, and stays positive in 2016–2026. Ai, Bansal & Guo's 2020–23 figure says it should.

**Choice of exit.** Exiting the 08:30 events at the open follows from where the risk resolves, and from the overnight fact. The literature measures close-to-close. If the lead prefers a replication, use MOC→MOC for every event — one or the other, not both.

### R3 — Month-end conditioned on rebalancing (a variant of R1b)

- **Rule.** As R1b, except that W+ goes to 2x only if a Treasury total-return proxy has beaten SPY month-to-date. Measure this at the last close before the MOC decision (the close of T−(s+2)); if stocks led, W+ stays at 1x. W− is unchanged.
- **Prediction.** W+ is stronger in months led by bonds than in months led by stocks, which is the sign Harvey et al. report.
- **Data trap.** TLT's stooq file is unadjusted, and TLT goes ex-dividend on the first business day of each month — that is, on T+1, every month. Raw TLT therefore understates every month-to-date bond return by one distribution. R3 needs a total-return series, or an approximation from the FRED 10-year yield declared in advance.
- **Not recommended this round.** It splits 259 months in two, and bank desks now forecast this flow publicly.

### R4 — The FOMC cycle

**Definition I would use.** Verify it against Cieslak, Morse & Vissing-Jorgensen before freezing; I could not confirm the exact week boundaries.
- For each scheduled statement session t_k, block j is the five sessions starting at t_k − 1 + 5j, for j = 0, 1, 2, …, up to the session before t_{k+1} − 1.
- A final short block keeps its parity.
- Even j is "high"; odd j is "low".

**R4a — unlevered.** 100% SPY in even blocks, T-bills in odd blocks.

**R4b — 2x variant.** 2x in even blocks, 0x in odd. Average exposure is about 1, so a CAGR win here could not come from extra market exposure. Legs follow §2. There are about 56 switches a year, and R4b trades 2x of notional at each one: about 1.1% a year at 1 bp a side, about 5.6% at 5 bp.

**Prediction.** In 2016–2026, mean even-block return > mean odd-block return.

### R5 — Option-expiration week

- **Dates.** E_m is the last session on or before the third Friday of month m. The window is the five sessions ending at E_m, or fewer if a holiday falls in that week.
- **R5b — 2x variant.** 2x from the close of the session before the window to the open of the session after E_m. About 24 fills a year.
- **Prediction.** The window beats the average five-session return, and the following five sessions lag.
- **Trap.** SPY usually goes ex-dividend on the third Friday of March, June, September and December, which is inside this window. The rule must run on the adjusted file, never on `SPY-1d-raw.csv` or on unadjusted SSO.
- **Low prior.** The academic evidence is for single stocks only.

### R6 — Overnight leverage (do not spend a trial on it)

- **Rule.** At the MOC of every session, buy an extra 1x; at the next MOO, sell it. That is 2x every night and 1x every session — two orders a day, literally "twice a day".
- **Why no trial.** Its 2005–2026 result is already fixed by EVIDENCE.md §C (+3.1 bp a night) minus costs and financing, so a backtest adds no information.
- **Break-even.** The all-in cost per side must stay under about (3.1 bp − one night's financing) / 2.
  - With SSO's expense ratio (about 0.35 bp a day) and T-bills between 0% and 4%, that is about 0.8–1.4 bp a side.
  - A margin version also pays the broker's overnight rate, which I don't know.
- **What to do instead.** In the paper-trading phase, log every `opg` and `cls` fill against the official open and close, for SPY (and SSO). That measures the one number every rule here depends on.

---

## 4 · Priors

**Method.** These are judgments, shown so they can be argued with.
- Each probability averages three states: the effect at its published size, decayed by 58%, or absent.
- Inputs: SPY's σ = 1.21% a session (19.2% a year, EVIDENCE.md); its mean of +4.6 bp a session (§C); 1 bp a side; financing at the T-bill rate + 1%.
- State weights:
  - **R1:** 0.25 / 0.45 / 0.30. The years 2005–13 sit inside the sample the effect was found in, so "absent" cannot be the whole story.
  - **R2:** 0.30 / 0.30 / 0.40. A risk premium decays less, but its FOMC component died after 2015.
  - **R4:** 0.15 / 0.30 / 0.55.
  - **R5:** mostly "absent".

| Rule | P(beats B&H net CAGR, 2005–26) | P(beats it in both halves) | P(passes an exposure-matched / placebo test at 5%) | Single biggest way it could fool us |
|---|---|---|---|---|
| R1a | 0.25 | 0.10 | 0.08 | One crisis month decides the sign. March 2020's W− under T+2 (2020-03-20 → 03-26) contains that month's low and its first rebound sessions |
| **R1b** | **0.70** | **0.50** | **0.30** | 2005–13 lies inside the sample the effect was found in, so a full-sample pass could come entirely from the first half. Read 2016–26 |
| R2a | < 0.05 | < 0.02 | — (Sharpe design) | — |
| R2b | 0.70 | 0.45 | 0.15 | The event list: which releases count, and look-ahead in rescheduled dates. Plus t ≈ 2 at best even if the premium is real |
| R3 | 0.60 | 0.40 | 0.15 (≈ 0.10 for what it adds over R1b) | Raw TLT's ex-dividend on T+1 biases the condition toward "stocks led" |
| R4a | 0.10 | 0.03 | — | — |
| R4b | 0.45 | 0.25 | 0.12 | An off-by-one in the week definition, and a Fed regime (2022) unlike 1994–2016 |
| R5b | 0.75 | 0.55 | 0.07 | Leverage passes for an edge; ex-dividend days fall inside the window on any unadjusted file |
| R6 | Break-even at 1 bp a side; positive only below about 0.8–1.4 bp all-in | — | not a test | The backtest result is already known; only live fills are news |
| *Control: 2x on 5 random sessions a month* | *≈ 0.8* | *≈ 0.55* | *0.05* | *Shows why CAGR vs buy-and-hold is the wrong bar for 2x variants* |

**At 5 bp a side,** the high-turnover rules collapse and the low-turnover ones barely move: R1b ≈ 0.55, R2b ≈ 0.35, R4b ≈ 0.2, R5b ≈ 0.65, R1a ≈ 0.13.

**Reasoning, in one line each.**
- **R1a.** It gives up about 60 sessions a year at +4.6 bp each, and the published selling window is only just deep enough to repay that.
- **R1b.** The net market exposure is roughly neutral (0x for 5 sessions vs 2x for 7), so beating buy-and-hold needs a real spread. But the tilt's tracking error is about 14.5% a year, and its 21-year average has a standard deviation of about 3% a year. Even with no edge, the tilt beats buy-and-hold about half the time; the states with an edge lift that to about 0.7.
- **R2b.** Low cost plus extra market exposure makes buy-and-hold easy to beat. The matched test is hard: t ≈ 2 even at the full published size.
- **R4b.** There is no tailwind from extra market exposure, and turnover costs about 1.1% a year. It needs the 1994–2016 pattern to have survived, and I found no evidence either way after 2016.
- **R5b.** Nearly all of its CAGR edge is leverage.

---

## 5 · What I recommend the lead freeze

1. **R1b alone**, set up as follows:
   - adjusted for the settlement cycle, with the §2 legs;
   - 1 bp per side as the primary cost, with 5 bp reported;
   - T-bills from DTB3;
   - synthetic 2x as defined in §3.
2. **Reading rule** (for the Red Team to set). My suggestions:
   - compare against constant-leverage SPY at R1b's realized exposure, and against the random-window placebo;
   - treat **2016–2026** as the deciding half;
   - also report the result with the two months contributing most (by absolute size) removed.
3. **Declare these as descriptive outputs in advance, never to be used to select a rule:**
   - R1a's W− leg on its own;
   - the settlement diagnostic;
   - the count of R1 windows that contain an FOMC or Employment Situation session, if R2's dates exist.
4. **R2b only if** the Quartermaster can build the event list from primary schedules with no look-ahead, and then as the second and last specification. Do not run R3–R5. R6 is a paper-trading measurement, not a trial. The repo already holds 39 trials (trials.json); each specification added raises the bar for every one.
5. **What to expect.** The most likely outcome is "positive, not proven". If so, the honest advice to Daniel does not change:
   - Buy-and-hold already collects the overnight premium.
   - More gains come from choosing a higher average exposure, which is a risk decision, not from timing it.
   - R1b's 2x windows sit inside the same crises as everything else, so expect drawdowns at least as deep as buy-and-hold's −56.5% (EVIDENCE.md).

---

## 6 · Data and implementation dependencies

| Need | For | Status |
|---|---|---|
| NYSE scheduled calendar | R1, R4, R5 | In the repo (`barqc.nyse_holidays`) |
| SPY open and close, adjusted with the same factor | all | On disk (`SPY-1d.csv`); confirm the opens are adjusted like the closes |
| Daily 3-month T-bill (FRED DTB3) | all (cash and financing) | Quartermaster |
| Scheduled FOMC statement dates 2005–26, excluding unscheduled actions | R2, R4 | Quartermaster (the Fed's historical calendars) |
| BLS Employment Situation and CPI release dates 2005–26, as scheduled; shutdown-delayed releases handled explicitly | R2 | Quartermaster (BLS schedules; ALFRED vintage dates might cross-check, not checked by me) |
| Treasury total-return proxy | R3 | Quartermaster. Do not use raw stooq TLT (unadjusted; ex-dividend on T+1) |
| Two-segment (night / session) engine with MOC and MOO legs | all | Bench (`replay.py` fills at the next open only) |
| SSO daily bars (nasdaq.com) | optional live cross-check of the synthetic 2x | Unadjusted for distributions; SSO's distribution dates not verified |

---

## 7 · Ways these could fool us — across all rules

1. **The sample overlaps the discovery samples.** About 2005–2013 lies inside the samples the dash-for-cash and turn-of-month effects were found in; 2005–2016 inside the FOMC-cycle paper's; 2005–2011 inside Lucca & Moench's. The second half is the test.
2. **A few months carry the result.** There are only 12 month-ends a year, and at 2x a few crisis windows decide the sign. Two examples, from the calendar alone (I have computed no returns):
   - 2008-09-25 → 2008-10-03 is September 2008's W+: the days around the House's first TARP vote.
   - 2020-03-20 → 2020-03-26 is March 2020's W− under T+2: it contains that month's low and the first rebound sessions.
3. **R1 and R2 overlap.** First-of-month jobs reports and month-end FOMC meetings fall inside the R1 windows.
4. **Leverage passes for an edge** in every 2x variant (§0.3).
5. **The cash assumption.** A flat 3% overstates any sidestep rule in the zero-rate years. EVIDENCE.md already calls it generous for 2009–2021. Use DTB3.
6. **Ex-dividend artefacts in unadjusted files.**
   - TLT goes ex-dividend on T+1 every month.
   - SPY goes ex-dividend on the third Friday of quarter months, inside R5's window. That is harmless on the adjusted file but not on `SPY-1d-raw.csv` or SSO.
   - SSO's own distribution dates are not verified.
7. **Costs.** Overlays with 50–60 fills a year move by about 2–3% a year between 1 and 5 bp a side.
8. **Taxes.** Monthly round trips realize short-term gains, while buy-and-hold defers them. Whether Daniel's account is taxable is unknown.
9. **Data mining across calendar rules.** Sullivan, Timmermann & White (2001), as summarized by secondary sources, found that calendar effects lose significance once the universe of 9,452 calendar rules is accounted for. A 2026 re-test finds day-of-week, week-of-month and January effects fade in the US after the early 1990s.
10. **Contaminated search results.** Two blog or vendor backtests of these exact windows on recent SPY surfaced unasked in my searches: a Substack piece saying the turn-of-month effect "mostly fails on current data", and a vendor's options-expiration-week backtest. I did not use them as evidence or to pick windows. They are unverified, and they sit on the test sample.

---

## 8 · What I could not verify

- **Etula et al.:** the published version's magnitudes and exact sample. I have the 2015 working paper's annualized S&P figures and slide text giving a July 1995 start. I also don't know whether the authors examined the T+2 period; the settlement-adjusted windows are my derivation from their stated mechanism.
- **Harvey et al.:** the regression horizon behind "≈ −17 bp".
- **Cieslak, Morse & Vissing-Jorgensen:** the exact week boundaries.
- **The announcement set:** which releases make up Savor & Wilson's set and Ai, Bansal & Guo's 44 days a year. Ai & Bansal's abstract names the employment report and FOMC statements; whether CPI, PPI, GDP or ISM are included is unconfirmed. My R2 set is a choice.
- **Lucca & Moench's 49 bp:** it appears in a VoxEU column, not in the abstracts I saw.
- **Alpaca's own `cls` cutoff.** Secondary sources give NYSE 15:50 and Nasdaq 15:55. Alpaca's `opg` window of 19:00–09:28 ET comes from a quote of its docs on a forum.
- **Sizes I could not find:** leveraged-ETF AUM, vol-control AUM and 401(k) flows; SSO's distribution dates.
- **Stivers & Sun:** the magnitudes, and the journal details (sources disagree on who wrote it).
- **Choi, Hong, Lou & Mukherjee (2022, preliminary):** the 401(k)-exposure result. One search summary says it goes against the payroll-inflow explanation; I could not confirm it.
- **Full text of everything** (the proxy returned 403 on every direct fetch). The shared search budget ran out before I could check Savor & Wilson's list of releases.

---

## Sources

**Repo:**
- `tools/market/EVIDENCE.md`: §C (overnight vs intraday), the third run (SPY volatility 19.2%, drawdown −56.5%, CAGR ≈ 10.4%), §G (costs), §E-15 (closures)
- `tools/market/DATA.md` §1
- `tools/market/trials.json` (39 trials)
- `tools/market/PREREG-2026-09-11-cross-section.md` (midpoint split)
- `tools/market/barqc.py` (`nyse_holidays`)
- `tools/market/intraday.py` (session fields)
- `tools/market/strategies.py` and `README.md` (next-open fill model)

**Web (search-verified, not full text):**
- McConnell & Xu 2008: https://rpc.cfainstitute.org/research/financial-analysts-journal/2008/equity-returns-at-the-turn-of-the-month · https://ideas.repec.org/a/taf/ufajxx/v64y2008i2p49-64.html
- Etula, Rinne, Suominen & Vaittinen 2020: https://academic.oup.com/rfs/article/33/1/75/5494694 · working paper https://orbilu.uni.lu/bitstream/10993/21145/1/Dash4Cash.pdf · slides https://www.aalto.fi/sites/default/files/2021-03/dash4cashpresentation_bi_r.pdf · https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2528692
- Choi, Hong, Lou & Mukherjee 2022: https://www.aeaweb.org/conference/2022/preliminary/paper/iQikdBKZ
- Harvey, Mazzoleni & Melone 2025: https://www.nber.org/system/files/working_papers/w33554/w33554.pdf · https://rpc.cfainstitute.org/blogs/enterprising-investor/2025/rebalancings-hidden-cost-how-predictable-trades-cost-pension-funds-billions · https://www.cnbc.com/2025/05/29/rough-stretch-for-bonds-may-force-some-pensions-to-sell-stocks-friday.html
- Lucca & Moench 2015: https://www.newyorkfed.org/medialibrary/media/research/staff_reports/sr512.pdf · https://cepr.org/voxeu/columns/predictable-movements-asset-prices-around-fomc-meetings
- Kurov, Wolfe & Gilbert 2021: https://www.skidmore.edu/economics/documents/KurovWolfeGilbert-TheDisappearingPre-FOMC-Announce-Drift-200914.pdf
- Cieslak, Morse & Vissing-Jorgensen 2019: https://scholars.duke.edu/publication/1136749 · https://stern.nyu.edu/sites/default/files/assets/documents/cycle_paper_cieslak_morse_vissingjorgensen.pdf
- Savor & Wilson 2013: https://ideas.repec.org/a/cup/jfinqa/v48y2013i02p343-375_00.html
- Ai, Bansal & Guo 2023: https://www.nber.org/papers/w31923 · Ai & Bansal 2018: https://www.econometricsociety.org/doi/10.3982/ECTA14607
- Boyarchenko, Larsen & Whelan 2023: https://academic.oup.com/rfs/article-abstract/36/9/3502/7076616 · the 2026 update: https://libertystreeteconomics.newyorkfed.org/2026/07/the-disappearing-overnight-drift/
- Lou, Polk & Skouras 2019: https://eprints.lse.ac.uk/87481/
- Cheng & Madhavan 2009: https://joim.com/dynamics-leveraged-inverse-exchange-traded-funds · arXiv 2608.03703: https://arxiv.org/abs/2608.03703
- Ivanov & Lenkey 2018: https://pure.psu.edu/en/publications/do-leveraged-etfs-really-amplify-late-day-returns-and-volatility/ · https://www.federalreserve.gov/econres/feds/are-concerns-about-leveraged-etfs-overblown.htm
- Stivers & Sun 2013 (listing): https://quantpedia.com/Screener/Details/102
- Ariel 1990: https://ideas.repec.org/a/bla/jfinan/v45y1990i5p1611-26.html · Ko & Yang 2024: https://nowpublishers.com/article/Details/CFR-0111
- Hartzmark & Solomon: https://www.nber.org/system/files/working_papers/w30688/w30688.pdf
- Hartley & Schwarz 2019: https://rodneywhitecenter.wharton.upenn.edu/wp-content/uploads/2019/12/17-19.Schwarz.pdf · https://www.cxoadvisory.com/bonds/term-premium-end-of-month-effect/
- Sullivan, Timmermann & White 2001: https://www.sciencedirect.com/science/article/abs/pii/S030440760100077X · the 2026 calendar re-test: https://www.sciencedirect.com/science/article/pii/S1062940826000756
- McLean & Pontiff 2016: https://Www.Gwern.net/doc/economics/2016-mclean.pdf
- Alpha Architect 2019: https://alphaarchitect.com/buyback-blackout-periods-do-not-negatively-impact-market-performance/
- Settlement cycle: T+2 https://www.sec.gov/tm/t2-sbrefa · T+1 https://www.sec.gov/news/press-release/2024-62
- SPY distributions: https://www.ssga.com/library-content/products/fund-data/etfs/us/distribution/SPDR_Dividend_Distribution_Schedule.pdf · https://www.dividendvision.com/dividends/spy-dividend-calendar
- TLT ex-dividend dates: https://www.dividendvision.com/dividends/tlt-dividend-calendar
- SSO: https://etfdb.com/etf/SSO/ · UPRO: https://www.proshares.com/our-etfs/leveraged-and-inverse/upro
- Alpaca `opg` window (forum quote): https://www.quantconnect.com/forum/discussion/18268/day-resolution-trade-and-have-issue-with-alpaca/ · MOC cutoffs: https://www.deltavalue.de/?p=30796
