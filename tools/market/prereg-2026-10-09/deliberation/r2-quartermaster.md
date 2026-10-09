```
BALLOT quartermaster
Q1 S1 window: A=Etula[T-3,T+3] MOC->MOC
Q2 S1 expression: A=2x overlay vs constant leverage
Q3 S2: A=TLT month-end overlay (data supports it, with the add-backs in §3.3)
Q4 financing over cash for the extra 1x: primary=1.0%/yr stress=4.0%/yr (plus one flat 7.75%/yr all-in line for (B) only)
Q5 cash values=0 / 1.5 / 3 %/yr ; primary=1.5 ; verdict must hold at: all
Q6 cost per side: primary=2bp ; reported 1bp, stress 5bp
Q7 G3 compares against: A=constant leverage
Q8 1x long/flat of S1 as a declared descriptive: yes
Q9 placebo: D=whichever holds size in the Bench study
DEAL-BREAKERS: any session offset (T, T-4, T+3, T-3) counted on bar dates or on the realised calendar instead of the scheduled one
```

*Quartermaster, round 2, 2026-10-09. `S` = `/tmp/claude-0/-home-user-ca/2758dbcb-e96c-587b-81c2-e59b0c402304/scratchpad`. New outputs are in `S/edge/quartermaster/r2/` and `S/edge/data/{events,cash}/`. Every number cites one of them. No rule, window or event conditions any return; the only prices read were for basis checks and dividend placement. Network use was five requests to api.nasdaq.com through `fetch.py`'s `_get`, plus WebSearch for SPY's distributions and the cutoff question. Nothing under `bars/` was touched, and nothing was committed.*

## 0 · Five things the freeze needs from the data side

1. **SPY's five post-cutoff distributions are now sourced and cross-checked** (`S/edge/data/events/spy-distributions-2025-2026.csv`). Add them back, and the Archivist's and Bench's bias bounds are no longer needed.
   - **The amounts** (share of the prior official close):

     | ex-date | amount | D/P |
     |---|---|---|
     | 2025-06-20 | $1.7611 | 29.48 bp |
     | 2025-09-19 | $1.8311 | 27.65 bp |
     | 2025-12-19 | $1.9934 | 29.47 bp |
     | 2026-03-20 | $1.797 | 27.24 bp |
     | 2026-06-18 | $1.90352 | 25.69 bp |

   - **Three independent checks** (`r2/spy-distributions-crosscheck.txt`):
     - **(i) The anchor.** The source's 2025-03-21 amount ($1.6955 = 29.98 bp) matches the stooq step I located in round 1 (30.08 bp).
     - **(ii) A data witness built from SSO and SPY.** x = r_SSO − 2·r_SPY spikes on each date. Validated on all 34 ex-dates from 2016–2025: median error −1.7 bp, and every known ex-date ranks in the top 41 of 2512 days (`r2/sso-witness.txt`).
     - **(iii) Scale.** The five steps sit just below the 2024–25 steps (30.1–33.7 bp), as a rising price predicts.
   - **What the price-only tail costs if not patched:** S1 is favoured over (A) by p̂ × 139.5 bp = 0.3334 × 139.5 ≈ **46.5 bp** cumulative, and (B) is understated by **139.5 bp**. Both are below the Archivist's 50–98 / 150–295 bp bounds (r2-archivist §3.3) and the Bench's "at most about 1.0%" (r2-bench §4).
2. **The scored span must be stated as dates, and the Bench and I computed the same ones.** S1 runs from the close of 2005-03-24 to the close of 2026-08-25: 257 complete entry-to-entry cycles, 5,387 sessions (`r2/cycle-spans.txt`; r2-bench §4 gives the same figures). "2005-02-25 → 2026-09-01" as written in the brief would score the excluded February 2005 and August 2026 window sessions at 1×.
3. **Offsets must come from the scheduled calendar, and closures roll forward.** Three closures touch S1's windows (`r2/window-spec.txt`):
   - December 2006: 2007-01-02 is T+1, leaving 6 held sessions.
   - October 2012: Sandy falls on T−2 and T−1, leaving 5.
   - November 2018: the T+3 exit falls on 2018-12-05 (closed) and executes at the close of 2018-12-06.

   Counting on the realised calendar would look ahead at Sandy: October 2012's T−4 would move to 10-23 on news that arrived around 10-28. That is my deal-breaker.
4. **TLT is clean inside S2's window, through 2026-04-01 and beyond** (the TLT section below). nasdaq.com serves TLT's official dividend history (203 rows), because TLT is Nasdaq-listed. All 113 stooq adjustment steps for 2016-10 → 2026-04 sit exactly on official ex-dates, and their sizes match within a median 0.22 bp. Two things need fixing:
   - stooq misses one payout, 2023-12-14;
   - the tail is price-only after 2026-04-01.

   Both fall outside the window but inside any always-on TLT benchmark, so add them back.
5. **No daily cash proxy is reachable.** Every rate is an assumption (probes listed below). That supports the overlay framing: against (A), financing cancels up to a residual of about 0.005 × the rate for S1 (0.013 for S2; §3.6).

## 1 · Critique of the other reports, from the data side

- **Brief §1.6 (span).** "2005-02-25 → 2026-09-01 … drop the August 2026 window" leaves two inconsistencies:
  - the incomplete February 2005 window (its entry, 2005-02-22, predates the file) is never mentioned;
  - the dropped August window starts at the close of 2026-08-25, not after 2026-09-01.

  Use the dates in §3.1 (they agree with r2-bench §4).
- **Brief §2 (ex-date table).** The positions are correct. I recomputed T−6, T−7, T−7, T−7, T−7, T−8 (`r2/positions.txt`). The dates are now sourced rather than inferred. The lead's "latest expiration is T−4" also holds: of 336 expirations, 4 sit at T−4, all on 21 November in Thanksgiving-shortened months (2003, 2008, 2014, 2025). None is in T−3…T+3.
- **Brief §2 (T-bill).** Confirmed: no daily cash series is reachable. FRED, the Fed and Treasury are blocked; the probes in §2.2 show nasdaq.com has none. The financing-cancels argument holds with one refinement (Q-financing in §3.6).
- **r1-archivist §3.3, §3.2, §5 and §1's table ("TLT's Stooq file is not dividend-adjusted").**
  - Wrong: stooq TLT is back-adjusted, on the ex-date open, through 2026-04-01.
  - The 2.2% stooq-vs-Alpaca gap DATA.md reports is the post-cutoff payouts (5 × 37–40 bp) plus the 2023-12-14 miss (32 bp) (`r2/tlt-dividends.txt`).
  - IEF is still not on disk before 2016-10.
- **r1-archivist §2 ("the SPY total-return file, 2005–2026").** It is total-return only through 2025-03-21, and its last bar (2026-09-02) is mid-session. Both are fixable as in §3.1.
- **r1-flow §3, shared definitions.**
  - **"Offsets count sessions … the dates in bars/SPY-1d.csv"** is the deal-breaker in §0.3. The file also lacks a session that traded: 2011-02-17, which is T−6 of February 2011 and inside R1b's T+3-era W− (T−8…T−4). Counting on bars shifts W− by one session that month.
  - **"None [of the closures] is a month-end"** is wrong: Sandy falls on T−2 and T−1, 2018-12-05 is November's T+3 exit, and 2007-01-02 is T+1.
- **r1-flow R1b (open legs).**
  - What holds: from 2016-10 to 2026-09, stooq SPY opens equal the official opens after the factor (median 0.0–0.2 bp a year, r1 §5). The two stooq open defects in that span (2017-10-09 and 2018-02-20, where O=L=C) are not R1b boundaries.
  - What is unverified: opens for 2005–2016 have no reference, which is half of R1b's sample. And no vendor documents its "open" as the primary-listing auction print.
  - **The tail.** In the T+1 era, the 2025-06-20 ex-date (T−6) lies inside W−. With the add-back in §3.1, that contamination is removed.
- **r1-flow R3 and §7.6.**
  - "TLT's stooq file is unadjusted": wrong, as above.
  - "TLT goes ex on T+1 every month": 185 of the 203 official distributions do. December extras sit at T−2 (2006), T−3 (2011–13), T−4 (2014–15) and T−5…T−10 since 2016.
  - The "overnight fact" (+3.1 bp a night, EVIDENCE §C) was measured on a file that credits SPY's dividends to the overnight leg until 2025-03-21. The located quarterly steps, 30–59 bp (r1 `exdate-step-ranges.txt`), are of order 0.5–0.9 bp a session. So part of that premium is the dividend's placement, not the market.
- **r1-redteam G-g, T4 and §4.2.**
  - "The other stooq files are largely unadjusted … no TOM replication except GLD": the files are back-adjusted up to symbol-specific cutoffs. What matters is where each fund's ex-dates fall relative to the window. QQQ's 34 located ex-dates sit at T−4…T−10 and never in [T−3, T+3] (`r2/positions.txt`), so G7 on QQQ-long is admissible.
  - "QQQ nearly dividend-free 1999–2005 [S]" stays unverifiable: nasdaq's official QQQ history starts 2012-06-15 (`events/qqq-distributions-official.csv`).
  - G-h's "October 2012's T−k counts shift" is true only on the realised calendar. On the scheduled one, the closures simply remove sessions from the window.
- **r1-redteam G-b (half-day cutoff "12:50 [U]")** is still unverified. What I could source is in §2.4.

## 2 · Answers to the lead's asks

**2.1 Ex-dividend placement.**
- **SPY.** No located ex-date in the adjusted era falls in [T−3, T+3]: 34 of 34 sit at T−5…T−10 (T−10 ×8, T−9 ×10, T−8 ×5, T−7 ×2, T−6 ×5, T−5 ×4). The post-cutoff five sit at T−6/T−7 and 2026-09-18 at T−8. Other funds, for reference:
  - in the window: IWM 4 of 24 (2017-07-06 T+3, 2017-09-26 T−3, 2018-07-03 T+2, 2018-09-26 T−2); EEM and EFA 2021-12-30 (T−1); XLE 2019-12-30 (T−1);
  - never in the window: DIA, QQQ, XLF.
- **QQQ 1999–2005 and the G7 veto.**
  - Not verifiable. No official record before 2012-06-15 is reachable, there is no unadjusted reference, and the cent-grid recovery failed (§4).
  - Bound: QQQ's located steps in 2016–2025 were 11–30 bp, and none fell in [T−3, T+3]. Even if every payout from December 2003 to February 2005 (at most 5, if the Red Team's [S] start date is right) were unadjusted and inside a window, the cost would be at most about 150 bp across 71 windows, about 2 bp per window.
  - That cannot flip a sign-only veto unless the effect is near zero. **So: it cannot materially matter.**

**2.2 Cash: none reachable.** Probes, `S/edge/data/cash/probe-log.txt`, raw bodies saved:

| time (UTC) | request | result |
|---|---|---|
| 05:30:13 | SHV dividends | "Dividend History for Non-Nasdaq symbols is not available" |
| 05:30:19 | TLT dividends | 203 rows, 2002-09-03…2026-10-01 |
| 05:30:25 | BIL dividends | non-Nasdaq, same message |
| 05:30:31 | IRX index history | rCode 400, "Symbol not exists" |
| 05:36:58 | QQQ dividends | 58 rows, 2012-06-15… |

BIL and SHV are not Nasdaq listings, nasdaq.com has no T-bill index, and FRED, the Fed and Treasury are blocked (brief §2). Yahoo was not retried after its 429. **Every cash and financing rate is an assumption.**

**2.3 Frozen data spec.** In §3.1–3.3, as exact text.
- **Calendar recommendation: scheduled, always.** T and every offset come from `barqc.nyse_holidays`. A boundary on an unscheduled closure executes at the next close with a bar; this is what edgelab does, and it happens once in S1 (2018-12-05 → 2018-12-06). An actual-calendar T−4 would use Sandy's closure before it was announced.

**2.4 Half-days at window boundaries** (calendar only, `r2/window-spec.txt`; "observed" = short in the 2020–26 minute feed).
- **S1 (entry at T−4 close, exit at T+3 close): 21.**
  - Entries:
    - Christmas Eve: 2007, 2008, 2009, 2012, 2013, 2014, 2015, 2018, 2019, plus 2020, 2024 and 2025 observed;
    - the day after Thanksgiving: 2006-11-24, 2017-11-24, and 2023-11-24 observed.
  - Exits on July 3: 2008, 2013, 2014, 2019, plus 2024 and 2025 observed.
- **G7: 6**, rule only: 2000-11-24, 2001-12-24, 2002-07-03, 2002-12-24, 2003-07-03, 2003-12-24.
- **S2 (T−3 / T close): 10**, all the day after Thanksgiving:
  - entries 2005-11-25, 2011-11-25, 2016-11-25, and 2022-11-25 observed;
  - exits 2008-11-28, 2013-11-29, 2014-11-28, 2019-11-29, and 2024-11-29 and 2025-11-28 observed.
- **The MOC cutoff on those days is unverified.** What I sourced (WebSearch):
  - NYSE MOC entry closes at 15:50 on normal days ([NYSE fact sheet](https://www.nyse.com/publicdocs/nyse/NYSE_Auctions_Closing_Process_Fact_Sheet.pdf));
  - NYSE Arca freezes at 15:59 ([Arca trading info](https://www.nyse.com/markets/nyse-arca/trading-info));
  - old Arca rule text bars cancelling routed MOC/LOC orders "15 minutes before the close" on an early scheduled close (2015–16 SEC exhibits);
  - Alpaca rejects `cls` orders entered after 15:50, and queues those entered after 19:00 for the next day's closing auction ([Alpaca docs](https://docs.alpaca.markets/us/docs/orders-at-alpaca)). Its half-day handling is unverified;
  - NYSE lists 1:00 p.m. closes on 2026-11-27 and 2026-12-24 ([NYSE hours](https://www.nyse.com/trade/hours-calendars)). **S1's December 2026 entry falls on 2026-12-24**, the first live half-day boundary.

  The backtest is unaffected, because the fill is the official close either way. In paper trading, queue the order after 19:00 the evening before, and confirm the fill on 2026-12-24.

**2.5 TLT.**
- **Through 2026-04-01 the window close(T−3) → close(T) is clean.**
  - 2016-10 → 2026-04: all 113 stooq adjustments sit on official ex-dates, every one on the open. 104 are at T+1 and the December extras at T−5…T−10, so none falls in T−2…T (`r2/tlt-dividends.txt`).
  - 2005-02 → 2016-10: the official dates put exactly one ex-date in the window, 2006-12-27 (T−2, $0.302586). Whether stooq adjusted it cannot be checked. If it did, December 2006 is total-return-correct; if not, that window carries one payout-sized drop.
- **The tail after 2026-04-01** is the stooq file itself. It now equals the official closes (2026 median gap 0.0 bp, r1 §5), plus the official distributions added back on their ex-date's overnight leg (table in §3.3). All the tail ex-dates are at T+1, outside the window. Only an always-on TLT holding needs the add-back, so (A) and any placebo must get it. Alpaca's TLT total-return file covers the same span but carries IEX closes, so prefer official closes plus official dividends.

## 3 · Replacement text for v0, as pre-registration text

**3.1 Data — S1.**
> **File.** `tools/market/bars/SPY-1d.csv` (stooq), SHA-256 `52a006deec221ab41c869bd25b279203d3f8d9dedad0bb99ea481164a2cd45a0`, read-only. The row dated 2026-09-02 is never read: it is an intraday snapshot (volume 6,128,212 against the official 29,566,220; close 765.595 against the official 765.16).
>
> **Scored span.** S1, (A), (B) and the placebo all enter at the close of 2005-03-24, the first T−4 whose window lies wholly inside the file, and are marked to the close of 2026-08-25, the T−4 of the incomplete August 2026 window. That is 257 complete cycles and 5,387 scored sessions. No session of the February 2005 or August 2026 windows is scored.
>
> **Calendar.** T is the last session of the month on the scheduled NYSE calendar (`barqc.nyse_holidays`). T−4 and T+3 count scheduled sessions. Bar dates never define T or an offset.
>
> **Closures and holes.** A scheduled session with no bar has no auction: the leg into the next bar spans it at the exposure in force. A boundary whose scheduled session is closed executes at the close of the next session with a bar. In the span this applies to:
> - December 2006: 2007-01-02 is inside the window (6 held sessions);
> - October 2012: 10-29 and 10-30 are inside (5 held sessions);
> - November 2018: the exit is scheduled for 2018-12-05, which was closed, and executes at the close of 2018-12-06.
>
> 2025-01-09 falls outside every window. The data hole 2011-02-17 (T−6, outside every window) is spanned at the exposure in force.
>
> **Dividend basis.** Back-adjusted, with the adjustment on the ex-date open, through 2025-03-21. Every quarterly ex-date from 2016-12 to 2025-03 (34 of 34) is located; 2005–2016 cannot be measured. After 2025-03-21 the file is price-only. The distributions in `S/edge/data/events/spy-distributions-2025-2026.csv` (2025-06-20 $1.7611; 2025-09-19 $1.8311; 2025-12-19 $1.9934; 2026-03-20 $1.797; 2026-06-18 $1.90352; SHA-256 `780a360f01fa86b49ddd53d470951fdb228ae7a013e6adf8f34ea980bcf8ac5e`) are added back on the overnight leg of their ex-date, r_on = (open + D)/close(t−1) − 1, for S1, (A), (B) and the placebo alike. All five lie outside every window. If the add-back is not implemented, print beside every affected line: "price-only tail: S1 favoured over (A) by ≈ 46.5 bp cumulative; (B) understated by ≈ 139.5 bp."
>
> **Prices.** Fills use closes only. Opens enter only the descriptive overnight/intraday split.

**3.2 Data — G7.**
> **File.** `bars/QQQ-1d-long.csv`, SHA-256 `4433bdbc019328196c84e610fe5f834aa72097de70a9d3bc2d499a6dfeae790e`; rows 1999-03-10 to 2005-02-24.
>
> **Span.** Enter at the close of 1999-03-25 and mark to the close of 2005-02-22: 71 complete cycles, 1,485 sessions. The February 2005 window is excluded.
>
> **Closures and hole.** 2001-09-11…14 (T−13…T−10), 2004-06-11 (mid-June) and the 1999-11-16 hole (T−9) lie outside every window. They are spanned at the exposure in force, by the S1 rules.
>
> **Dividend basis.** Unmeasurable for this span, and declared so. No located QQQ ex-date (2016–2025) falls in [T−3, T+3].

**3.3 Data — S2, if TLT is chosen.**
> **File.** `bars/TLT-1d-long.csv`, SHA-256 `e4483c7bad20ee09cf7a7ab1973a72bd31ab3ae844567906eeccbe7b343a1e27`.
>
> **Window.** Entry at the close of scheduled T−3, exit at the close of T.
>
> **Span.** Enter at the close of 2005-03-28 and mark to the close of 2026-08-26: 257 complete cycles, 5,387 sessions. Alternatively, to the close of 2026-08-31 (258 windows), with the last cycle truncated after its exit. October 2012's window holds one leg, close 10-26 → close 10-31, which spans Sandy.
>
> **Dividend basis.** Back-adjusted on the ex-date open through 2026-04-01; 2005–2016 is declared assumed. Add back, on the overnight leg of the ex-date and for every series holding TLT that day, the official distributions stooq lacks (source: nasdaq.com dividend history, `S/edge/data/events/tlt-distributions-2002-2026.csv`, SHA-256 `acab1fc211fc35a3b61b063065918778b280ff213743cc4c4151bdcc56bcd5e4`):
>
> | ex-date | amount | D/P | note |
> |---|---|---|---|
> | 2023-12-14 | $0.310534 | 32.07 bp | missed by stooq |
> | 2026-05-01 | $0.315346 | 36.83 bp | |
> | 2026-06-01 | $0.335777 | 39.15 bp | |
> | 2026-07-01 | $0.318030 | 36.80 bp | |
> | 2026-08-03 | $0.330454 | 40.18 bp | |
>
> None lies inside an S2 window.

**3.4 Cash and financing.**
> No daily cash or bill-rate series was reachable (probes in r2-quartermaster §2.2). Every cash and financing rate is an assumption, and every result is printed at each bracketed value.

**3.5 Half-days.**
> Boundary sessions on a 13:00 close are filled at that day's official close. The backtest assumes the order reached the auction. Live, the order is queued after 19:00 ET the previous evening. The cutoff on half-days is unverified and is checked on the first live half-day boundary, 2026-12-24.

**3.6 (A)'s exposure basis.**
> p̂ is computed on the same basis as financing accrual. On the scored span, S1's window share is 0.3334 on sessions (1,796 of 5,387) and 0.3384 on calendar days. S2's is 0.1428 on sessions and 0.1294 on calendar days (`r2/s1-exposure-shares.txt`). If financing accrues per calendar day while (A) holds 1 + p̂(sessions), the residual (about 0.005 × the rate for S1, about 0.013 × the rate for S2) is printed.

## 4 · What I could not do, or verify

- **Pre-2016 completeness of stooq's adjustments, for SPY, QQQ and TLT.** There is no unadjusted reference on disk.
  - **A cent-grid recovery failed validation.** stooq stores 6 significant figures, but its adjusted O/H/L are not the official prices times the close's factor: on 2016-12-15 the ratios are O 0.868014, H 0.868197, L 0.868600, C 0.868101. Its adjusted closes also wander by about 1e-4 between events (`r2/grid_factor.py` and `r2/close_grid.py`, kept as negative results).
  - **The only miss measured is TLT's 2023-12-14 payout.** SPY's 2016–2025 adjustments are complete.
- **Source quality of the SPY amounts.** They are V-sec (dividend-listing sites, quoted in WebSearch summaries). The 2026-03-20 date also appears on State Street's 2026 schedule PDF (search snippet). My second query named the amounts, so that summary may echo them. The SSO witness and the anchor match are the independent checks.
- **Half-day MOC cutoffs** at NYSE Arca and at Alpaca: unverified.
- **QQQ distributions before 2012-06-15**: unverified.
