# Round 1 — Archivist: what the published record supports

*2026-10-09. Evidence came from WebSearch snippets only. Every scholarly host was blocked to both WebFetch and curl (see §6), so no journal PDF was opened. No bar file was opened and no conditional statistic was computed. Every estimate below comes from `edge/archivist/estimates.py`, which writes `estimates.txt`; it uses only formulas, published magnitudes and labelled assumptions. Working notes are in `edge/archivist/notes.md`. Verification codes are explained in §6.*

---

## 0. Conclusions

1. **Almost nothing published has been shown to earn money at its original size after both costs and its own publication.** Where the original authors or close replicators re-tested after publication, they mostly report decay or death:
   - **Pre-FOMC drift:** "essentially disappeared after 2015" (Kurov, Wolfe & Gilbert 2021).
   - **The 2–3 a.m. overnight drift:** "has averaged close to zero since 2021". This comes from the original authors themselves (Boyarchenko, Larsen & Whelan, Liberty Street, July 2026).
   - **Pre-holiday premium:** declined in the US, UK and Hong Kong, significantly only in the US. The same paper reports a sign reversal in 1991–97 and disappearance in 1997–2003, though the snippet does not make clear for which market (Chong et al. 2005).
   - **FOMC even-week cycle:** I found no clean out-of-sample support.

   This repo's base rate (almost everything null) is the literature's base rate.

2. **One family is different in kind: month-end institutional cash-flow pressure.**
   - **The mechanism is not behavioural.** It comes from settlement deadlines, benefit payments, fixed-weight rebalancing and the month-end extension of bond indices.
   - **The evidence is peer-reviewed.**
   - **Unusually, there is 2026 evidence that it is alive:**
     - (a) **Kayacetin (JIFMIM vol. 109, 2026):** 30 indices, 1994–2023. The turn-of-month return is 10 bp/day against 0 bp on other days. It was "arbitraged away in the first decade following its publication" but then "comes back in full force". It is most economically significant in the U.S. in 2019–2023.
     - (b) **Nathan, Suominen & Tasa (2026, working paper):** when US settlement moved from T+2 to T+1 on 28 May 2024, the month-end selling trough moved one trading day later. That is a natural experiment tying the pattern to settlement mechanics rather than to data mining.
     - (c) **Harvey, Mazzoleni & Melone (NBER WP 33554, 2025; a December 2025 version is listed on the AFA conference site):** predictable 60/40 rebalancing moves equity prices (−17 bp next day per 1-SD signal) and bond prices. The effect peaks in the last four days of the month over 1997–2023 and is stronger toward quarter-end.
   - **The contrary evidence is real (§3.1).** Practitioner tests find the classic [−1,+3] window weak over the last decade. Chen & Chua (2011) found that after ETFs the effect concentrated on day 1 and the ETF's last-day return was negative. An Atlanta Fed paper (2000) found the effect gone in futures after 1990.

3. **It is worth about one point a year, not more.**
   - **As a 2× overlay on SPY**, held only in the 7-day window, my expected contribution is **+1.0%/yr**. The scenario range is −0.9% to +5.7%, and I put P(effect at ≥ half its published size) ≈ 0.5 (`estimates.txt`).
   - **Held instead of the index** (in the window, cash otherwise), it cannot beat buy-and-hold on return even if fully intact. It only cuts volatility, exactly as the trend filter and volatility targeting did here.
   - **Calendar edges add ROI only through leverage inside the window.**

4. **Pre-register first: the SPY month-end window [T−3, T+3] exactly as Etula, Rinne, Suominen & Vaittinen define it (RFS 2020).** Section 2 gives the full sketch.
   - **The trade:** let T be the last NYSE trading day of the month. Buy at the close of T−4 and sell at the close of T+3, both with market-on-close orders. That is one specification and no grid.
   - **Data:** what is on disk is enough (SPY total-return file, 2005–2026).
   - **Out-of-sample spans:** 2014–2026 is out-of-sample for Etula's data (their chart axis ends in 2013), and 2006–2026 is out-of-sample for McConnell & Xu (data to 2005).
   - **Power, which the Red Team must design for:** with about 259 months, a half-size effect (5 bp/day) gives only t ≈ 1.45. A null result would therefore not rule out a half-size premium; it would only mean we cannot justify trading it.

5. **Second, if the budget allows one more trial: Treasury end-of-month** (Hartley & Schwarz 2019, working paper). The trade is long 10-year-duration Treasuries over the last 3 trading days of each month.
   - **More decisive per trial:** t ≈ 2.4 if the published 10-year magnitude holds.
   - **Clean out-of-sample:** 2019–2026 lies outside the paper's sample.
   - **New asset:** no prior test here used it.
   - **Data gap:** it needs IEF, which is not on disk, or a dividend-correct TLT.

6. **Not recommended:** pre-FOMC drift; the FOMC even-week cycle; the overnight drift and conditional overnight reversal; pre-holiday; option-expiration week; leveraged-ETF rebalancing flows; the Treasury auction cycle at daily frequency; crypto time-series momentum; the "16th-of-month payday" effect; quarter-end window dressing. Section 3.7 gives the reasons.

7. **Harvey, Mazzoleni & Melone, as asked.**
   - **The signal:** how far a 60/40 portfolio held in E-mini S&P 500 and 10-year T-note futures has drifted from 60% equity. The calendar version accumulates the drift since the previous month-end; the baseline assumes rebalancing 5 trading days before month-end. The threshold version fires when the weight leaves a band (e.g. 2 pp).
   - **Timing:** the effect sits in the last ~4 trading days of the month and reverts within about two weeks.
   - **Size:** a 1-SD signal moves equities −17 bp and bonds +2–3 bp the next day. One summary attributes the 17 bp to the calendar signal and another to the threshold signal; this is unresolved. The long-short futures strategy earned about 10%/yr at Sharpe > 1 over 1997–2023, and about 1 after costs.
   - **Tradeable with SPY/TLT?** Mechanically yes: the signal is known before the close and the trades fit the closing auction. Practically it is weaker:
     - TLT's duration is about twice the 10-year note's, so IEF matches the paper better.
     - A long-only account captures only part of a long-short result.
     - Independent replications are mixed.
     - Only 2024–2026 is out-of-sample.

---

## 1. Ranking — top six

**How the score is built.** Score = expected net annual contribution to a small account holding SPY, from `estimates.txt`. Each candidate is scored as a leverage or switch overlay with three scenarios: the effect intact, at half size, or gone. Each scenario is weighted by my probability, and net means after variance drag, financing and fees. These are order-of-magnitude numbers whose assumptions are shown in the script.

| # | Candidate | Rule (one line) | Best evidence | Post-publication status | If at half size | P(≥ half size, 2026) | **Expected %/yr** | Testable on disk? |
|---|---|---|---|---|---|---|---|---|
| 1 | **Month-end equity window** | 2× SPY from close T−4 to close T+3; 1× otherwise | Etula et al. RFS 2020; Kayacetin JIFMIM 2026; Nathan et al. WP 2026 | decayed, then revived 2019–23 (Kayacetin); classic [−1,+3] weak (practitioners) | +1.8 | 0.50 | **+1.0** (σ-sensitivity +0.4 to +1.7) | **yes** (SPY) |
| 2 | Treasury end-of-month | +1× 10-yr-duration Treasuries, last 3 trading days | Hartley & Schwarz WP 2019 | weaker 2015–18 but significant; a CXO test on TLT did not corroborate (different window) | +1.2 (10-yr scale) | 0.45 | **+0.6** (TLT scale possibly ~2×, unverified) | partly (needs IEF or total-return TLT) |
| 3 | Macro-announcement days | 2× SPY on FOMC/CPI/PPI/jobs days (~44/yr) | Savor & Wilson JFQA 2013; Ai, Bansal & Guo WP (sample to 2023) | survives in the full sample to 2023; FOMC part shrank to ~22 bp after 2012 | +1.0 | 0.50 | **+0.5** | no (needs event dates) |
| 4 | Halloween | 2× SPY Nov–Apr, 1× May–Oct | Bouman & Jacobsen AER 2002; Andrade et al. FAJ 2013 (out-of-sample 1998–2012); Zhang & Jacobsen JIMF 2021 | survived its first out-of-sample test at full size (37 markets) | +0.6 | 0.60 | **+0.5**, with 2× exposure through any winter crash | no power (21 winters: a 4%/yr gap gives t ≈ 0.96) |
| 5 | Harvey–Mazzoleni–Melone (HMM) rebalancing switch | SPY → 10-yr bonds for the last ~4 days when stocks are overweight month-to-date | NBER WP 33554 (1997–2023) | no peer-reviewed out-of-sample; practitioner replications mixed | +1.9 | 0.35 | **+0.4** | partly (bond leg data; out-of-sample only 2024–26) |
| 6 | Pre-refunding Treasury gains | +1× long Treasuries on the day before each quarterly refunding announcement | Wang & Zhao WP 2025 (1991–2023) | "strengthened over time" (in-sample) | +0.4 | 0.55 | **+0.3** | no (needs dates) |

**After #1, the order is within the error of my assumptions.** #2 to #6 all land at about half a point. I broke ties by testability on the data already on disk and by the strength of the mechanism.

**The two leaders share a mechanism.** #1 and #2 are both month-end flows, so their probabilities of existing are correlated. Together they are worth about 1.5 points a year in expectation, not two independent bets.

---

## 2. What I would pre-register first, and the inputs the Flow Theorist, Red Team and Bench need

**The spec: SPY month-end window, Etula et al. (2020) definition.**

- **Calendar.** T is the last NYSE session of each calendar month. Count sessions with `barqc.nyse_holidays`, not bar positions: the SPY file has a known hole on 2011-02-17. The window W is sessions T−3 … T+3, which earns close(T−4) → close(T+3). That is 7 sessions a month, about 84 a year.
- **Kayacetin's alternative.** His window is the last 4 plus first 4 sessions, i.e. [T−3, T+4]. It differs by one day. Fix one before the run; Etula's has more out-of-sample history on disk.
- **Effect statistic.** Mean daily SPY return inside W minus the mean outside W. For the null, re-place a 7-session block at a random offset within each month, preserving the count. Test one-sided.
- **Money statistic.** Compare three books:
  - (a) 1× SPY always, plus another 1× inside W, via a synthetic daily-reset 2× series: SSO's expense ratio of 0.88%, plus financing at the T-bill rate plus a spread;
  - (b) **constant leverage at the same average exposure (~1.33×)**, which is the fair benchmark;
  - (c) 1× buy-and-hold.

  Without (b), any gain is only the equity premium earned on extra leverage. Report CAGR, max drawdown and Sharpe.
- **Sub-windows, declared in advance and descriptive only.**
  - 2005–2013, inside Etula's sample;
  - 2014–2026, outside it;
  - 2024-06 to 2026-09, after T+1 settlement: about 28 month-ends. Nathan et al. predict the trough shifts one day later. Report this, but let no decision rest on it.
- **Overlap reporting.** Kayacetin calls the premium a "relief rally" after high-volatility, low-return episodes, which is when RSI(14) < 30 fires. So report:
  - the share of W days that sit inside an active `rsi_dip` hold, and W's effect with those days excluded, so the one existing survivor is not counted twice;
  - the share of windows containing a jobs-report Friday. That release usually falls on the first Friday of the month, which overlaps the macro-announcement premium.
- **Costs.** Both legs fill at the official closing auction, so the backtest price is the fill price. The real cost is regulatory fees, about 0.2 bp on sells (third-party rate, unverified), so 1 bp per fill is conservative. The repo's 5 bp per fill is very conservative for auction trades.
- **Executability.** Two MOC orders a month, both decided from the calendar alone with no price input, before Alpaca's ~15:50 ET MOC cutoff. Whole shares only, because Alpaca accepts fractional orders with DAY time-in-force only.
- **Trials.** One added: 39 → 40.
- **Power** (`estimates.txt`, assuming SPY daily SD of 1.2%). The standard error of the in-minus-out difference is 3.46 bp/day. True differences of 5, 7 and 9 bp/day give t of 1.45, 2.03 and 2.60. The Red Team should write the reading rule knowing that a half-size premium has roughly even odds of reading null.
- **If the budget allows two trials,** add the bond window (§3.3) to the same document and read the two together.

---

## 3. Candidate dossiers

### 3.1 Month-end equity flows — turn of the month (TOM) and the "dash for cash"

- **Rules as published**
  - Lakonishok & Smidt (1988) and McConnell & Xu (FAJ 2008, 64(2):49–64): TOM is the last trading day plus the first three, [−1, +3]. [V-abs]
  - Etula et al. (RFS 2020, 33(1):75–111): [T−3, T+3]. Under T+3 settlement, T−3 is "the last monthly settlement day … which guarantees liquidity for month-end cash distributions". Later versions describe "a strong market level return reversal four days before month end at T−4 (in stocks and bonds)". [V-abs]
  - Kayacetin (JIFMIM 2026): the last 4 plus the first 4 trading days. [V-abs]
- **Samples and effects, quoted**
  - **McConnell & Xu** (CRSP 1926–2005): "investors received no reward for bearing market risk except at turns of the month". The effect appears in 31 of 35 countries. It is not explained by month-end volume or fund flows, and volatility in the window is no higher than on other days. [V-abs]
  - **Etula et al., working paper** (S&P 500 value-weighted, since the 1995 move to T+3):
    - −17 bp over T−8..T−4 and +77 bp over T−3..T+3;
    - T−3..T−1 earned 47% of the 7-day return after June 1995, against 30% "in the sample" (as the snippet words it);
    - T−3..T−1 returns are about 2.5× higher when month-end T falls on a Friday;
    - it strengthened as mutual-fund ownership grew. [V-abs]
  - **Etula et al., slides:** a chart labelled "From T−3 to T+3" against "On other days", with years 1926–2013 on the axis, and the line "all returns in the US stock market have accrued during just seven days around the turn of the month". [V-sec]
  - **Etula et al., published version:**
    - institutions are net sellers on T−4 and T−3, and net buyers on the last day and the first days of the next month;
    - selling over T−8..T−4 predicts higher T−3..T−1 returns;
    - "elevated stock and bond yields right before the month end". [V-abs]
  - **Kayacetin:** 10 bp/day in the window against 0 bp outside it. The window accounts for all positive mean returns in 25 of 30 markets and for more than two-thirds in the other five. It is stronger at fiscal quarter and half-year ends and after high-volatility, low-return spells. Two searches agree on this. [V-abs]
  - **Nathan, Suominen & Tasa (SSRN 6426026; authors' replication README) [V-text].** This is stock-level, but it is the one causal test of the mechanism.
    - Momentum earns +10.2 bp/day (t 3.7) in the "PreTOM" window (t−9..t−4), against +2.4 bp/day (t 1.2) elsewhere, over 1980–2025.
    - Losers earn −11.3 bp/day (t −3.5) in PreTOM.
    - After T+1, "T−3 absorbs −27 bp additional selling pressure; T−4 shifts up +43 bp".
    - The post-reform sample is 19 months, against 533 before. [V-abs]
- **Costs.** I found no index-level cost treatment in these papers (unknown). For MOC-to-MOC trades in SPY, cost is essentially regulatory fees.
- **Evidence against persistence**
  - Maberly & Waggoner (Atlanta Fed WP 2000-11): the effect in S&P 500 futures "disappear[s] after 1990". [V-abs]
  - Chen & Chua (J. Financial Planning, April 2011):
    - after ETFs, the S&P 500 effect concentrates on the first trading day;
    - the ETF's last-trading-day return is negative on average;
    - switching from T-bills into the index on TOM days "underperforms … buying and holding index funds in recent times". [V-abs]
  - Liu (JBER 2013): SPY 2001–2011 — the effect still exists but has moved earlier. [V-abs]
  - Practitioner tests:
    - Quantseeker: the classic window "appears to have largely disappeared in the past decade";
    - ATB Research (2026, E-mini futures): p > 0.05;
    - QuantConnect (SPY 2001–2018): CAGR 3.0%, Sharpe 0.35. [V-sec / U]
  - Marquering et al.: the time-of-month effect disappeared after publication, but another version of the same study disagrees. [V-sec]
- **Evidence for persistence**
  - Kayacetin's revival, strongest in the US in 2019–23.
  - Nathan et al.: the mechanism was alive through 2025 and moved with the settlement change.
  - Norgate-based practitioner study (S&P 500, 1980 to 2024 Q3): four TOM days a month earned only 0.89%/yr less than all other days combined. [V-sec]
- **Mechanism and who is on the other side.**
  - Funds meeting redemptions and pensions paying benefits must sell by the last settlement day before month-end.
  - Month-start inflows (payroll and 401(k) contributions) buy afterwards.
  - Liquidity providers are balance-sheet constrained at month-end and quarter-end.
  - The trade is to be the buyer once the forced selling stops.
- **Capacity and crowding.** Capacity is irrelevant for a small account. The effect has been public since 1987–88 and was explained in RFS in 2020. It persists, if it does, because the counterparty does not care about price.
- **Data.** SPY's total-return file (2005–2026) is enough. The QQQ, DIA and IWM long files could serve as witnesses, but they are not all dividend-adjusted, so their ex-dates must be checked against the window.
- **Confidence it still exists at ≥ half size:** 0.5 for [T−3, T+3]; 0.35 for the classic [−1, +3].

### 3.2 Fixed-weight rebalancing — Harvey, Mazzoleni & Melone (NBER WP 33554; March 2025, revised January 2026; December 2025 version on the AFA conference site)

- **The signal**
  - The equity weight of a 60/40 portfolio in E-mini S&P 500 and 10-year T-note futures, measured against 60%. [V-abs]
  - Calendar version: in the baseline, the drift accumulates since the last month-end and rebalancing is assumed 5 trading days before month-end. [V-sec]
  - Threshold version: a band, for example 2 pp. [V-abs]
  - The band width δ and the day count N were chosen by predictive regressions: a researcher degree of freedom. [V-abs]
- **Timing and size**
  - "Leading to a decrease in equity returns of 17 basis points over the next day." [V-abs, abstract] Summaries disagree on whether this is the calendar or the threshold signal; one gives "approximately 17 bps" per 1-SD of the calendar signal.
  - Calendar predictability "peaks in the last four days of the month" and is "absent at other times"; it grows toward quarter-end. [V-abs / V-sec]
  - Bonds +2–3 bp; "reverts almost entirely within two weeks"; significant only from the early 2000s. [V-sec]
- **Strategy and costs.** Long-short S&P against 10-year futures: about 10%/yr at Sharpe > 1, against 0.35 for equities and 0.48 for bonds, 1997–2023. "After transaction costs, the Sharpe ratio is close to 1." [V-abs]
- **Independent checks**
  - QuantReturns (practitioner; calendar signal excluding the final day; 1997-09 to 2023-03): CAGR 8.11%, volatility 6.51%, Sharpe 1.24, max drawdown −8.9%. [V-sec]
  - paperswithbacktest (1990–2026): Sharpe −0.20, method unknown. [U]
  - An unreviewed GitHub research pull request (KAFKA2306/investor2 #278) tested SPY/BND over January–August 2026, eight month-ends. The signal returned +1.72%, against +4.66% for a plain month-end long. With n = 8 it carries no weight.
  - Kent Daniel's discussion questions the $16 bn/yr cost estimate, which rests on no holdings data. [V-abs]
- **Who is on the other side**
  - Defined-benefit pensions, target-date funds and balanced funds.
  - Parker, Schoar & Sun (JF 2023): target-date funds rebalance "within a few months", and stocks they own more of earn lower returns after strong markets. [V-abs]
  - Harvey cites about $20 tn following fixed-target rules. [V-sec]
- **Crowding.** Sell-side desks publish month-end pension flow estimates; one headline read "Pensions May Sell $26 Billion in Stocks by Thursday: Wells Fargo". Mazzoleni reports that pension managers say they front-run their own rebalancing. [V-sec]
- **Data**
  - SPY is on disk.
  - The bond leg needs IEF, or a total-return TLT. The Stooq TLT file is not dividend-adjusted (2.3% gap in 2020, per EVIDENCE.md §E-15).
  - Only 2024-01 to 2026-09 (about 33 month-ends) is out of the paper's sample.
- **Confidence: 0.35.**
- **How it relates to §3.1.** The same mechanism predicts the equity window is weaker after strong equity months and stronger after weak ones. That fits Kayacetin's "relief rally" and Graziani (2024 job-market paper, 1975–2020): a negative S&P return from the 4th Friday to month-end predicts a higher return next month. [V-abs] Conditioning the window on month-to-date stock-versus-bond performance is therefore a natural **second** step, worth taking only if the unconditional window survives.

### 3.3 Treasury end-of-month — Hartley & Schwarz (2019 working paper; Rodney White Center 17-19; SSRN 3440417; I found no journal version)

- **Rule.** Hold coupon Treasuries over the last few (3–5) trading days of each month.
- **Sample.** 2-, 5- and 10-year notes, January 1990 to December 2018, modelled daily prices, excess over the general-collateral repo rate. [V-sec]
- **Effect**
  - "Positive and highly significant in the last few days of the month, and … not significantly different from zero at other times." [V-abs]
  - 10-year note, last 3 days: about 0.25%/month excess, roughly 3 points a year. Holding only those days gives a Sharpe of about 1. [V-abs]
  - 2015–2018 is weaker but still significant. [V-sec]
  - Life insurers are large net buyers on benchmark rebalancing dates. [V-abs]
- **Costs and caveats.** Results are gross. CXO warns of snooping in the maturity-and-days choice, says the method is not accessible to most investors, and notes that its own TLT-since-2002 test does not corroborate the result (different window). [V-sec]
- **Mechanism.**
  - Bond indices add new issues at month-end, so index trackers must buy. Window dressing adds to it.
  - A NY Fed Liberty Street post (Sept 2026) says Treasury trading concentrates on the last trading day of each month, when indices rebalance. [V-abs]
  - This fits Etula's "elevated … bond yields right before the month end".
  - McConnell & Xu found no TOM in Treasuries, but they used a window that includes the first days of the next month. [V-sec]
- **Data.**
  - TLT's Stooq file is not dividend-adjusted. I believe TLT's monthly ex-dates fall at the start of the month (unverified). If so, a last-3-days window ends before the ex-date and the defect may not bite. The Quartermaster should check this against the Alpaca total-return file for 2020–2026.
  - IEF matches the 10-year note better and is not on disk.
- **Out-of-sample.** 2019-01 to 2026-09, about 93 month-ends.
- **Power** (`estimates.txt`, assuming a bond daily SD of 0.9%): t = 2.38 at 8.3 bp/day; t = 1.20 at half size.
- **Confidence: 0.45.**

### 3.4 Macro-announcement days, the pre-FOMC drift and the FOMC cycle

- **Savor & Wilson (JFQA 2013):** 1958–2009. 11.4 bp on announcement days (inflation, jobs and FOMC releases) against 1.1 bp on other days. Over 60% of the premium is earned on 13% of days. [V-abs; release list V-sec]
- **Ai & Bansal (Econometrica 2018):** about 55% of the premium is earned on pre-scheduled announcement days. [V-abs]
- **Ai, Bansal & Guo (NBER WP 31923):** 1961–2023. About 10 bp against about 1 bp. 44 days a year earn about 4.65%/yr, roughly 71% of a 6.59% premium (the figure is OCR-garbled in the snippet). [V-abs]
- **Hu, Pan, Wang & Zhu (JFE 2022):** pre-announcement returns pooled across jobs, ISM, GDP and FOMC releases come to 5.66%/yr. FOMC alone is 27.1 bp (t 5.95); the others about 10 bp. [V-abs]
- **Decay**
  - Lucca & Moench (JF 2015, 1994–2011): more than 80% of the equity premium came in the 24 hours before FOMC announcements (working-paper wording). [V-abs]
  - Kurov, Wolfe & Gilbert (FRL 40, 2021): "essentially disappeared after 2015". [V-abs]
  - BIS WP 1079: the FOMC premium is "only 22 bps after 2012". [V-abs, one search]
  - Cieslak, Morse & Vissing-Jorgensen (JF 2019): the premium since 1994 is earned in even weeks of the FOMC cycle. [V-abs] An independent working paper reports no out-of-sample support. A claim that a 2025 survey finds the opposite cycle in 2017–2021 was not confirmed by a second search. [U]
- **Mechanism.** A risk premium for resolving macro uncertainty. As compensation for risk rather than mispricing, it is the most likely of these to persist.
- **Data.** Not on disk. It needs FOMC dates and BLS dates for CPI, PPI and the jobs report; federalreserve.gov and bls.gov are blocked from this machine.
- **Confidence (≥ half size):** macro-day premium 0.5; pre-FOMC drift 0.1; FOMC cycle 0.1.

### 3.5 Pre-refunding gains — Wang & Zhao (working paper, July 2025)

- **Rule.** Long medium- and long-term Treasuries on the trading day before each quarterly refunding announcement (February, May, August, November).
- **Evidence.** Hand-collected data, 1991–2023. [V-abs]
  - Gains rise steadily with maturity and have "strengthened over time".
  - They are not information leakage.
  - They are stronger right after an FOMC meeting and near the debt ceiling.
  - A strategy trading four days a year has a "Sharpe ratio exceeding four".
- **Magnitude.** Not retrieved. If that Sharpe is annualised with √252, it implies at least 0.25 SD per event, about 23 bp for a long bond with 0.9% daily SD. If it is annualised over the four events, it would imply 2 SD per event, which is implausible (`estimates.txt`).
- **Data and power.** Needs the announcement dates. Only about 11 events since 2024 are out-of-sample. Over 2005–2026 (about 86 events), t ≈ 2.3 at 0.25 SD per event.
- **Confidence: 0.55**, but it is worth at most about 1%/yr even if fully intact.

### 3.6 Halloween / "Sell in May"

- **Bouman & Jacobsen (AER 2002):** May–October returns are significantly lower than November–April in 36 of 37 markets, 1970–1998. Andrade et al.'s text instead says higher in 35 and significant in 20, a discrepancy I could not resolve. [V-abs]
- **Andrade, Chhaochharia & Fuerst (FAJ 2013, 69(4)):** out-of-sample 1998–2012 in the same 37 markets, about 10 pp higher in November–April, "same economic magnitude". [V-abs]
- **Zhang & Jacobsen (JIMF 2021, vol. 110):** all indices worldwide (62,962 observations). November–April is about 4% higher, and the summer excess return is about −1%. [V-abs]
- **Assessment.** This is the cleanest post-publication survival among calendar effects. Three caveats:
  - I did not verify the US-specific size;
  - on 21 seasons the test has no power (a 4%/yr gap gives t ≈ 0.96, `estimates.txt`);
  - the ROI version carries 2× exposure through any winter crash, such as Q4 2008 or February–March 2020.

### 3.7 Not recommended

- **Pre-holiday.**
  - Ariel (JF 1990): returns 9–14× those of a normal day. [V-abs]
  - Vergin & McGinnis (1999): gone for major US indices in 1987–96. [V-sec]
  - Chong et al. (JIMF 2005): the effect declined in the US, UK and Hong Kong, significantly only in the US. A sign reversal in 1991–97 and disappearance in 1997–2003 are also reported; the snippet does not make clear for which market. [V-abs]
  - About 9 days a year. P ≈ 0.15.
- **Option-expiration week.**
  - Stivers & Sun (JBF 2013): optionable S&P 100 stocks. [V-abs]
  - Index-level evidence is only in their 1983–2008 working paper: 28 large caps earned 0.45%/week against 0.12% in other weeks over 1996–2008. [V-sec]
  - A practitioner test of holding only in expiration week reports a CAGR of about 2%. [U]
  - P ≈ 0.2.
- **Overnight drift and conditional overnight reversal.**
  - Boyarchenko, Larsen & Whelan (RFS 2023): returns concentrate at 2–3 a.m. ET; selloffs are followed by overnight reversals. [V-abs]
  - The authors' 2026 update: the window "averaged close to zero since 2021". [V-abs]
  - Bondarenko & Muravyev (JFQA 2023): four hours around the European open account for the whole average return (E-mini futures, 2004–2018). [V-abs]
  - These are futures hours, not executable at US auctions. The close-to-open version was already tested here and lost to buy-and-hold at realistic cost.
  - Lou, Polk & Skouras (JFE 2019) is a stock-level result.
- **Leveraged-ETF rebalancing flows.**
  - Lenkey's 2024 survey: statistically significant but "economically insignificant", with method errors common. [V-abs]
  - Ivanov & Lenkey (JFM 2018): insignificant once fund flows are controlled for. [V-abs]
  - Beckmeyer et al.: the price pressure reverts at the next open and has shrunk over time. [V-abs]
  - The end-of-day momentum form was already tested here (null).
- **Treasury auction cycle.**
  - Lou, Yan & Zhang (RFS 2013): a 5-day price gap of about 22–24 bp around 5- and 10-year auctions (draft figures). [V-abs]
  - NY Fed Staff Report 1188 (2026): pre-auction pressure persists intraday but has not grown. [V-abs]
  - HBS WP 26-033: the post-auction fall in yields is gone after 2010. [V-abs]
  - Robeco (2025): 10-year futures fall about 6 bp ahead of an auction and recover within hours. [V-abs]
  - It is now mostly intraday. P ≈ 0.25 at daily frequency.
- **Crypto time-series momentum.**
  - Liu & Tsyvinski (RFS 2021): momentum at 1–4 week horizons. [V-abs]
  - Since July 2020, crypto momentum has been "negative and statistically insignificant" in a cross-sectional large-cap study (FMPM 2025). [V-abs]
  - Han, Kang & Ryu: after costs and liquidations many portfolios are insignificant; time-series evidence is stronger than cross-sectional. [V-abs]
  - Quantpedia's 2024 Bitcoin revisit: "slightly less effective" than the original. [V-sec]
  - Time-series momentum on the nine ETFs was already null here. P ≈ 0.25.
- **Others.**
  - The 16th-of-month payday effect: Ma & Pratt (SSRN working paper, 1980–2010). [U]
  - Quarter-end window dressing: Carhart et al. (JF 2002) is a fund-NAV phenomenon. [V-sec]
  - Quantpedia's 2026 sector-ETF intramonth momentum: practitioner work; needs nine sector ETFs, of which only XLE and XLF are on disk; same family as the cross-sectional momentum that was null here. [V-sec]

---

## 4. Turning a high-return-per-day edge into account ROI

1. **Timing alone cannot add return.**
   - At full strength (the window carries 100% of the premium), "window-only, cash otherwise" ties buy-and-hold's excess return at about 58% of its volatility. At half strength it trails by about 2%/yr (`estimates.txt`).
   - This matches Chen & Chua (2011) and this repo's own trend-filter and volatility-target results.
2. **Leverage inside the window is the only lever, and its main cost is variance, not fees.**
   - Going from 1× to 2× for one day costs 1.5σ² of log growth: 1.50, 2.16 or 2.94 bp/day at daily volatility of 1.0, 1.2 or 1.4% (`estimates.txt`).
   - That cost is the same whether the leverage comes from margin or from a 2× ETF.
   - The window must beat this plus financing. That is why the "gone" scenario costs only −0.3 to −0.9%/yr while the "intact" scenario earns +3 to +6%/yr.
3. **Daily-reset leveraged ETFs (Avellaneda & Zhang 2010, SIAM J. Fin. Math. 1:586–603).** The fund's log return is β·log(index) − β(β−1)/2·∫σ²dt, less fees and financing. [V-abs]
   - The path term at 1.2% daily volatility (`estimates.txt`):

     | Hold length | 2× | 3× |
     |---|---|---|
     | 7 days | −10 bp | −30 bp |
     | 6 months | −181 bp | −544 bp |

   - So 2× funds suit windows of about a week. 3× funds and multi-month holds are where "decay" really bites.
   - Realised shortfall can exceed the model. In 2022–23, SSO returned −5.7% against −3.6% modelled, and UPRO −15.3% against −10.6%. [V-sec]
   - Expense ratios: SSO 0.88%, UPRO 0.89% [V-sec], plus swap financing (not retrieved).
   - Gap risk: a 2× fund loses about twice a crash day, and there is no stop.
4. **Margin at Alpaca.**
   - About 7.75%/yr on the overnight debit balance, actual/360 (undated support page) [U].
   - 2× overnight under Reg T.
   - Since June 2026, FINRA's intraday framework allows 4× intraday with $2,000 equity (Alpaca blog) [V-abs]. That does not help a multi-day window.
   - Financed with margin, the window overlay's expected value falls from +1.0 to +0.6%/yr (`estimates.txt`). **For a small account, a 2× ETF is the cheaper leverage.**
5. **Execution constraint.** Alpaca accepts fractional orders with DAY time-in-force only [V-abs, docs], so market-on-open and market-on-close orders need whole shares.
6. **The fair benchmark for any leverage overlay is constant leverage at the same average exposure.** "2× on a third of days" averages about 1.33×. Without that benchmark, any gain is just the equity premium earned on more leverage.
7. **Leverage plus trend, the documented precedent.**
   - Gayed & Bilello (2016 Dow Award, CMT) apply leverage only when the S&P 500 is above its moving average. [V-sec]
   - CXO's reconstruction (1928–2015): 2× above the 200-day average and T-bills below gives Sharpe 0.51 against 0.30, assuming a 1% leverage cost and no switching costs. [V-sec]
   - Volatility clusters: below the average, volatility is higher and returns lower, so leverage drags less above it.
   - This is how the repo's existing Sharpe gains (trend filter 0.78 against 0.61) could become return. It is a design option, not new evidence, and it re-uses a signal already tested here.
8. **Sizing.** Growth-optimal leverage is μ/σ², which is large for a window with a high return per day. But μ is exactly the uncertain quantity (P ≈ 0.5 here), so **do not exceed 2× inside the window.**
9. **Disagreeing with conventional wisdom.** "Never hold leveraged ETFs" is too strong. For week-long windows the decay is the same variance drag any 2× exposure pays, and at a 7.75% margin rate the ETF is cheaper. What the evidence condemns is multi-month holding of 3× funds through volatile regimes.

---

## 5. Notes for the other roles

- **Quartermaster.** Four data needs:
  - IEF daily total-return history, 2005–2026;
  - checking TLT ex-dates against month-end windows (use the Alpaca total-return file);
  - if macro or refunding candidates advance, FOMC, BLS and Treasury refunding dates (their sites are blocked here; a GitHub-hosted copy would need provenance);
  - checking that the "open" in each daily file is the auction print, if any open-auction rule advances.
- **Flow Theorist.**
  - The settlement-cycle mapping, T+3 (until 5 Sept 2017) → T+2 → T+1 (28 May 2024), is the one place where a mechanism-derived window could differ from the published fixed window.
  - I could not resolve from snippets which day count Nathan et al. use. Do not tune it on the data.
- **Red Team.**
  - Use the constant-leverage benchmark for any overlay.
  - The power figures in §2 and §3.3 show a null on 2005–2026 is weak evidence against a half-size effect. Decide in advance what a null licenses: "do not trade", not "no effect".
  - Watch for double counting with `rsi_dip` (relief rallies) and with jobs-report Fridays.
- **Bench.**
  - Count sessions from the NYSE calendar, not from bar positions (SPY lacks 2011-02-17).
  - Drop the incomplete final window: the SPY file ends 2026-09-02, before T+3 of the August→September turn.
  - Score fills at the official close.

---

## 6. What I could not verify, and how to read the tags

**Tags**

- **[V-text]:** read in a primary text. Only the authors' own replication README (Nathan, Suominen & Tasa) reached this level.
- **[V-abs]:** an abstract, landing page or PDF snippet of the primary source surfaced by search, with the full text not opened. The search tool summarises results with a model; load-bearing claims were checked with a second query (Kayacetin, the 17 bp figure, McConnell & Xu, Kurov et al., Boyarchenko 2026).
- **[V-sec]:** a secondary source (CXO, Quantpedia, a blog, or slides) describing the paper.
- **[U]:** unverified — a single uncorroborated snippet, an undated page, or practitioner work with unknown method.

**Access**

- The proxy refused WebFetch and curl for SSRN, NBER, OUP, Elsevier, Wiley, arXiv, RePEc, Crossref, OpenAlex, author sites, github.io and every publisher I tried. Only github.com and raw.githubusercontent.com answered.
- **The shared web-search budget (200 calls per turn across all five agents) ran out mid-research.** Other roles may now find their searches refused.

**Still open**

- Etula et al.'s RFS tables and exact sample end. "2013" is read from a slide axis.
- Harvey–Mazzoleni–Melone's exact signal formula and their tables.
- Hartley–Schwarz's results by maturity and the Allocate Smartly TLT check.
- Kayacetin's US-subperiod numbers.
- Wang–Zhao's magnitude in bp and how their Sharpe is annualised.
- Ai–Bansal–Guo's list of announcement days. Whether it is FOMC, CPI, PPI and jobs (8 + 12 + 12 + 12 = 44) is my inference.
- The date of Alpaca's margin rate.
- The current SEC fee rate ($20.60 per $1 M as of April 2026 comes from a third party).
- TLT's ex-dividend timing.
- The US-specific Halloween size.
- McLean & Pontiff's 26% and 58% decay figures (quoted only in a search summary).

**Assumed, not measured**

- SPY daily SD of 1.0–1.4%.
- An equity premium of about 6%/yr.
- A T-bill rate of 4%.
- SSO swap spread of 0.5%/yr.
- Long-bond daily SD of 0.9%.
- TLT duration about twice the 10-year note's.
- All scenario probabilities. They are my judgement, built around a McLean–Pontiff-style halving for published US effects. Jacobs & Müller (JFE 2020) find the US is the only country with a reliable decline after publication [V-abs].

**Untrusted content.** No fetched page tried to instruct me. Two GitHub pull requests from unrelated automated-research repos appeared in search results; one (KAFKA2306/investor2 #278) was read as data and is cited only as n = 8 noise.

---

## 7. Citation ledger

| Source | What I rely on | Status | URL |
|---|---|---|---|
| McConnell & Xu, FAJ 2008 | [−1,+3]; 1926–2005; no reward outside TOM; 31/35 countries | V-abs | https://papers.ssrn.com/sol3/papers.cfm?abstract_id=1135217 |
| Etula, Rinne, Suominen & Vaittinen, RFS 2020 | T−3..T+3; −17 / +77 bp (WP); institutional selling at T−4/T−3 | V-abs | https://academic.oup.com/rfs/article/33/1/75/5494694 ; https://orbilu.uni.lu/bitstream/10993/21145/1/Dash4Cash.pdf |
| Etula et al. slides | 1926–2013 chart; "all returns … seven days" | V-sec | https://www.aalto.fi/sites/g/files/flghsv161/files/2021-03/dash4cashpresentation_bi_r.pdf |
| Kayacetin, JIFMIM 109 (2026) | [−4,+4] 10 vs 0 bp; revival; US 2019–23 | V-abs | https://www.sciencedirect.com/science/article/abs/pii/S1042443126000259 ; https://papers.ssrn.com/sol3/papers.cfm?abstract_id=7201062 |
| Nathan, Suominen & Tasa, WP 2026 | PreTOM momentum; T+1 shift | V-text (README) / V-abs | https://raw.githubusercontent.com/dannyboy990/momentum-replication/main/README.md ; https://dx.doi.org/10.2139/ssrn.6426026 |
| Chen & Chua, J. Fin. Planning 2011 | concentrated on day 1; switching underperforms | V-abs | https://www.financialplanningassociation.org/article/journal/APR11-turn-month-anomaly-age-etfs-reexamination-return-enhancement-strategies |
| Maberly & Waggoner, Atlanta Fed WP 2000-11 | TOTM gone after 1990 (futures) | V-abs | https://www.atlantafed.org/research/publications/wp/2000/11.aspx |
| Liu, JBER 2013 | SPY 2001–11 effect moved earlier | V-abs | https://core.ac.uk/download/pdf/268112617.pdf |
| Quantseeker / ATB Research / QuantConnect / Norgate (ETF Trends) | practitioner tests | V-sec / U | https://www.quantseeker.com/p/turn-of-the-month-strategies-do-they ; https://atbresearch.substack.com/p/the-turn-of-the-month-effect-tested ; https://www.etftrends.com/etf-strategist-content-hub/turn-month-effect/ |
| Graziani, JMP 2024 | end-of-month return predicts next month (1975–2020) | V-abs | https://csef.it/wp-content/uploads/JMP_GG_02Nov2024.pdf |
| Harvey, Mazzoleni & Melone, NBER WP 33554 | −17 bp; last 4 days; ~10%/yr, Sharpe > 1; costs | V-abs | https://www.nber.org/papers/w33554 ; https://afajof.org/management/viewp.php?n=144452 |
| HMM presentation/practitioner summaries | baseline rebalancing at T−5; QuantReturns figures | V-sec | https://quantreturns.com/strategy-review/front-running-the-rebalancers/ ; https://www.edhec.edu/sites/default/files/2026-03/slides_EDHEC_Michele%20Mazzoleni%20(1).pdf |
| Kent Daniel discussion (2025) | critique of the cost estimate | V-abs | https://kentdaniel.net/discuss/2025/HMM.pdf |
| Parker, Schoar & Sun, JF 2023 | TDF contrarian rebalancing | V-abs | https://www.nber.org/papers/w28028 |
| Hartley & Schwarz, WP 2019 | last 3–5 days; 25 bp/month 10y; Sharpe ~1; 1990–2018 | V-abs / V-sec | https://rodneywhitecenter.wharton.upenn.edu/wp-content/uploads/2019/12/17-19.Schwarz.pdf ; https://www.cxoadvisory.com/bonds/term-premium-end-of-month-effect/ |
| NY Fed Liberty Street, Sept 2026 | month-end Treasury trading at the close | V-abs | https://libertystreeteconomics.newyorkfed.org/2026/09/treasury-trading-at-the-close/ |
| Wang & Zhao, WP 2025 | pre-refunding gains, Sharpe > 4 | V-abs | https://ideas.repec.org/p/osf/socarx/xucf8.html |
| Savor & Wilson, JFQA 2013 | 11.4 vs 1.1 bp | V-abs | https://www.ssrn.com/abstract=1342933 |
| Ai, Bansal & Guo, NBER WP 31923 | 1961–2023; 44 days; ~71% | V-abs | https://www.nber.org/papers/w31923 |
| Hu, Pan, Wang & Zhu, JFE 2022 | pre-announcement 5.66%/yr | V-abs | https://www.sciencedirect.com/science/article/abs/pii/S0304405X21004037 |
| Lucca & Moench, JF 2015 | >80% in 24 h (WP) | V-abs | https://www.newyorkfed.org/medialibrary/media/research/staff_reports/sr512.pdf |
| Kurov, Wolfe & Gilbert, FRL 2021 | drift gone after 2015 | V-abs | https://www.sciencedirect.com/science/article/pii/S1544612320315956 |
| BIS WP 1079 | FOMC premium 22 bp after 2012 | V-abs (single) | https://www.bis.org/publ/work1079.pdf |
| Cieslak, Morse & Vissing-Jorgensen, JF 2019 | even-week cycle | V-abs | https://papers.ssrn.com/abstract=2687614 |
| Ariel, JF 1990; Chong et al., JIMF 2005 | pre-holiday; decline/reversal | V-abs | https://www.researchgate.net/publication/222245676_Pre-holiday_effects_International_evidence_on_the_decline_and_reversal_of_a_stock_market_anomaly |
| Bouman & Jacobsen, AER 2002; Andrade et al., FAJ 2013; Zhang & Jacobsen, JIMF 2021 | Halloween in-sample, out-of-sample, worldwide | V-abs | https://moya.bus.miami.edu/~sandrade/andrade_chhaochharia_fuerst_FAJ2013.pdf ; https://www.sciencedirect.com/science/article/abs/pii/S0261560620302242 |
| Boyarchenko, Larsen & Whelan, RFS 2023 + Liberty Street July 2026 | overnight drift and its disappearance | V-abs | https://ideas.repec.org/a/oup/rfinst/v36y2023i9p3502-3547..html ; https://libertystreeteconomics.newyorkfed.org/2026/07/the-disappearing-overnight-drift/ |
| Bondarenko & Muravyev, JFQA 2023 | EU-open window | V-abs | https://ideas.repec.org/a/cup/jfinqa/v58y2023i3p939-967_1.html |
| Lou, Polk & Skouras, JFE 2019 | stock-level tug of war | V-abs | https://personal.lse.ac.uk/polk/research/TugOfWar.pdf |
| Lou, Yan & Zhang, RFS 2013; NY Fed SR 1188; HBS 26-033; Robeco 2025 | auction cycle | V-abs | https://personal.lse.ac.uk/loud/Shocks.pdf ; https://www.newyorkfed.org/medialibrary/media/research/staff_reports/sr1188.pdf ; https://www.hbs.edu/ris/download.aspx?name=26-033.pdf |
| Stivers & Sun, JBF 2013 | option-expiration week | V-abs / V-sec | https://ideas.repec.org/a/eee/jbfina/v37y2013i11p4226-4240.html |
| Lenkey 2024; Ivanov & Lenkey 2018; Beckmeyer et al. | LETF flows small and reverting | V-abs | http://www.aimspress.com/article/doi/10.3934/QFE.2024031?viewType=HTML ; https://papers.ssrn.com/abstract=3925725 |
| Liu & Tsyvinski, RFS 2021; FMPM 2025 | crypto momentum and its decay | V-abs | https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3226952 ; https://link.springer.com/article/10.1007/s11408-025-00474-9 |
| Avellaneda & Zhang, SIAM 2010 | LETF path formula | V-abs | https://epubs.siam.org/doi/pdf/10.1137/090760805 |
| Gayed & Bilello 2016; CXO reconstruction | leverage above the moving average | V-sec | https://cmtassociation.org/?p=75350 ; https://www.cxoadvisory.com/volatility-effects/leveraging-the-u-s-stock-market-based-on-sma-rules/ |
| ETFCentral; levered-ETF anomaly review | SSO/UPRO expense ratios; 2022–23 shortfall | V-sec | https://www.etfcentral.com/compare-etfs/UPRO-vs-SSO ; https://www.themoonlight.io/fr/review/a-levered-etf-anomaly-explained |
| Alpaca docs and blog | fractional DAY-only; Reg T; 4× intraday from June 2026; fees | V-abs; margin rate and SEC rate U | https://docs.alpaca.markets/docs/fractional-trading ; https://alpaca.markets/blog/finra-retires-the-pdt-rule-introducing-alpacas-new-intraday-margin-framework/ ; https://docs.alpaca.markets/docs/regulatory-fees |
| Jacobs & Müller, JFE 2020 | US-only post-publication decline | V-abs | https://www.sciencedirect.com/science/article/abs/pii/S0304405X19301618 |
