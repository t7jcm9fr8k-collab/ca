# Quartermaster: Round 1 data report

*2026-10-09. Scratch root `S = /tmp/claude-0/-home-user-ca/2758dbcb-e96c-587b-81c2-e59b0c402304/scratchpad`. Every number below comes from a file saved under `S/edge/` (path given) or from a cited URL. I tested no trading rule. Nothing here is a return or volatility statistic grouped by a rule, a calendar window or an event. Where I place dividend dates on the calendar, that is a corporate-action placement, not a price statistic. I left the repo untouched, and `bars/` and `__pycache__` are unchanged. At my final check, though, `git status` showed two untracked files I did not write: `tools/market/edgelab.py` and `tools/market/test_edgelab.py` (directory changed 04:56:01Z). I did not touch them.*

## Conclusions

1. **The on-disk inventory matches DATA.md exactly.** All 21 bar files pass barqc, and the counts and spans match. There are three defects DATA.md does not record:
   - **`SPY-1d.csv`'s last bar (2026-09-02) was captured mid-session.** Its volume is 6,128,212 against nasdaq's official 29,566,220, and its close is 765.595 against the official 765.16.
   - **`SPY-1d-raw.csv` (used for trial 3) has a placeholder bar on 2026-04-20.** It reads O=H=L=C=710.14 with volume 0. The true bar, per stooq and agreed by the Alpaca aggregate, is O 708.78 H 709.91 L 706.14 C 708.72. The same file has a placeholder volume of 9,999,999 on 2026-04-17.
   - **`SPY-1d-agg.csv` is not dividend-adjusted**, although README runs it with `--adjusted yes`. Its median close gap to the official close is 0.8–1.3 bp in every year.
2. **DATA.md §2 is wrong that "the stooq long files are the unadjusted ones".** All ten stooq files, SPY included, are distribution back-adjusted, with the adjustment placed on the ex-date open. Each stops being adjusted at a symbol-specific date and is unadjusted after it:
   - **DIA** 2022-10-21. Its monthly adjustments were already sparse in 2020–22: 3, 2 and 3 a year against 12 a year in 2017–19.
   - **EFA** 2022-06-09; **XLF** 2022-09-19; **IWM** 2022-09-26; **EEM** 2024-12-17.
   - **SPY** 2025-03-21; **QQQ** 2025-03-24; **XLE** 2025-12-22; **TLT** 2026-04-01.
   - **GLD** has no adjustment events and a 0.00 bp gap in every year. It pays no distributions, so it is the control.

   DATA.md's 2020–26 window sits mostly after these cutoffs, which is why the nine looked unadjusted. SPY's cutoff is later, which is why SPY "went the other way". In 2016 (Oct–Dec), the stooq-vs-official median close gaps are SPY 1319 bp, TLT 2279, XLE 3208, EEM 1681, EFA 1487, XLF 1098, IWM 733, DIA 726 and QQQ 600. They fall to 0.00 after each cutoff. This touches the inputs of the E-15 and cross-section runs, which is for the lead to weigh, not me.
3. **I fetched 21 files with `nasdaq_json.py`: official prices, split back-adjusted, not dividend-adjusted.** They are SPY QQQ IWM DIA TLT, BIL SHV SHY IEF, SSO UPRO QLD TQQQ, EEM EFA GLD XLE XLF, and IBIT BITO GBTC.
   - **History is capped at 10 years**: 2016-10-10 → 2026-10-08, 2513 bars. A probe for 2005-01-01..2016-10-09 returned an empty table.
   - **18 pass barqc and 3 are BLOCKED.** IWM, XLE and XLF each have one OHLC-inconsistent row, all on 2023-06-05, where the high is below the open.
   - **nasdaq.com also has placeholder bars on 2026-04-20** for SPY, SSO, GLD and GBTC.
4. **I could not obtain VIX, ^IRX or Bitcoin.** Yahoo answered HTTP 429 to the ^VIX request and to fetch.py's three built-in retries (04:33:01–04:33:21Z), so I stopped. I made no other Yahoo request. No Bitcoin daily series is reachable through the repo's fetchers. The only reachable proxies are US-session ETFs: IBIT from 2024-01-11, BITO from 2021-10-19 and GBTC from 2019-01-17.
5. **Calendar artifacts are built for 1999–2026.**
   - 7052 scheduled sessions, of which 10 were unscheduled closures, leaving 7042 actual sessions.
   - Each session's position counting from the start and from the end of its month.
   - The session before and after each of 253 holidays.
   - 336 monthly expirations, 8 of them moved to a Thursday.
   - 112 quarter ends.
   - Half-days are derived by rule. Against the minute feed for 2020-07-27 → 2026-09-01, all 12 rule half-days were observed short, and the only other short days were feed holes (2021-04-13, 2024-12-23).
6. **The event calendars are incomplete.** WebFetch is unusable here: every call failed with `getaddrinfo ENOTFOUND`, even for example.com. WebSearch worked until the shared budget of 200 searches per turn ran out.
   - **FOMC 2005–2016**: 95 of 96 scheduled statement dates, 73 of them corroborated by an official URL. April 2014 is missing.
   - **FOMC 2025** comes from a secondary source, and **FOMC 2026** from the Fed's calendar page as summarised by the search tool.
   - **FOMC 2017–2024 is not verified.** That leaves only 16 FOMC dates inside the official nasdaq window.
   - **CPI** covers 2005 only (12 of 13 releases). **Employment Situation** dates: none.
7. **Dividend dates collide with the calendar windows people test** (no prices involved). These are the ex-dividend dates located from stooq vs nasdaq between 2016-10 and each cutoff:
   - **SPY**'s ex-date is the quarterly options-expiration Friday at all 34 located dates.
   - **DIA**'s is the monthly expiration Friday at all 47.
   - **QQQ** goes ex the Monday after expiration (31 of 34); XLE does so 24 of 38 times and XLF 11 of 24 times.
   - **TLT** goes ex on the first session of the month (104 of 113).

   In any dividend-unadjusted series, those sessions carry an artificial overnight drop the size of the payout. That covers every nasdaq file, every stooq file after its cutoff, and `SPY-1d-agg.csv`. The located SPY steps are 30–59 bp, and the TLT steps in 2023–2026 are 17–43 bp. **Options-expiration and turn-of-month specs must run on a series that puts the adjustment on the ex-date open, or add the dividends back.**
8. **No file is guaranteed to carry the primary-exchange opening-auction price**, which is what an `opg` order fills at. Stooq and nasdaq opens agree to the cent on most days. They disagree by more than 10 bp on XLE for 53 days and XLF for 17 days, mostly in 2024–26, and the Alpaca reading sides with neither consistently. Alpaca's daily opens are IEX first prints, 1.4–10.5 bp off the official open (median per year). Closes are dependable; opens need care.

## Support

### 1 · The on-disk inventory, re-verified (`S/edge/quartermaster/barqc/barqc-onDisk-2026-10-09.txt`)

| File(s) | barqc source / adjusted flag | Bars | Span | Missing (all listed in `S/edge/data/calendar/calendar-vs-files.txt`) | Verdict |
|---|---|---|---|---|---|
| `{DIA,EEM,EFA,GLD,IWM,TLT,XLE,XLF}-1d-long.csv` | stooq / no | 5415 | 2005-02-25→2026-09-04 | 6: closures 2007-01-02, 2012-10-29/30, 2018-12-05, 2025-01-09 + hole 2011-02-17 | PASS |
| `QQQ-1d-long.csv` | stooq / no | 6915 | 1999-03-10→2026-09-04 | 11: closures (9/11 ×4, 2004-06-11, the five above) + hole 1999-11-16 | PASS |
| nine `X-1d.csv` | alpaca / yes | 1536 | 2020-07-27→2026-09-04 | 1: 2025-01-09 | PASS |
| `SPY-1d.csv` | stooq / yes | 5413 | 2005-02-25→2026-09-02 | 6 (as the long files) | PASS |
| `SPY-1d-raw.csv` | nasdaq / no | 1553 | 2020-07-01→2026-09-04 | 1: 2025-01-09; one zero-volume bar (2026-04-20) | PASS |
| `SPY-1d-agg.csv` | alpaca-1m-aggregated / yes | 1532 | 2020-07-27→2026-09-01 | 2: 2025-01-09, 2025-03-10 (feed hole) | PASS |
| `SPY-sessions.csv` | not a bar file | 1518 sessions | 2020-07-27→2026-09-01 | lacks 15 sessions: 12 half-days + 2021-04-13, 2024-12-23, 2025-03-10 | UNRUN (header) |

The adjusted flags I passed only change barqc's note, never its verdict. `SPY-1d-raw.csv` is identical to my fresh 2026-10-09 pull on all 1553 common dates (`S/edge/quartermaster/basis/basis-yearly-gaps.txt`, last line), so nasdaq has not revised the 2026-04-20 placeholder.

### 2 · Fetches (`S/edge/data/nasdaq/*-fetch.log`, barqc in `S/edge/quartermaster/barqc/barqc-nasdaq-*.txt`)

Every file was written with `nasdaq_json.py --from 1990-01-01 --to 2026-10-09 --out S/edge/data/nasdaq/<SYM>-1d-nasdaq.csv` between 04:30:19Z and 04:34:40Z. Requests were spaced about 3 seconds apart, and every one answered on the first try. Checksums are in `SHA256SUMS.txt`.

| Group | Symbols | Span / bars | barqc |
|---|---|---|---|
| (a) indexes | SPY QQQ IWM DIA TLT | 2016-10-10→2026-10-08 / 2513 | PASS except **IWM BLOCKED** (2023-06-05 H 180.82 < O 181.26; stooq shows H = 181.26) |
| (b) cash, Treasuries | BIL SHV SHY IEF | same / 2513 | PASS. BIL has 4 flat bars with real volume, plausible for a T-bill fund but unverified |
| (c) leveraged | SSO UPRO QLD TQQQ | same / 2513 | PASS. SSO has the 2026-04-20 placeholder |
| other on-disk names | EEM EFA GLD XLE XLF | same / 2513 | PASS except **XLE and XLF BLOCKED** (both on 2023-06-05, high < open). GLD has the 2026-04-20 placeholder |
| (e) bitcoin proxies | IBIT / BITO / GBTC | 2024-01-11 (688) / 2021-10-19 (1248) / 2019-01-17 (1942) | PASS. GBTC has the 2026-04-20 placeholder |
| (d) Yahoo `^VIX` | — | — | **NETWORK: HTTP 429 after 3 retries** (`S/edge/data/yahoo/VIX-fetch.log`). I did not attempt ^IRX or BTC-USD. |

**nasdaq.com's basis**, from `S/edge/quartermaster/basis/nasdaq-subcent-closes.txt`:
- **Split back-adjusted.** Closes with fractions of a cent stop exactly at a boundary:
  - UPRO: whole-cent closes from 2022-01-13.
  - QLD, SSO and TQQQ: from 2025-11-20.
  - XLE: from 2025-12-04; its 2023-06-05 open is 40.5325, against roughly 81 in stooq-adjusted terms.
  - GBTC: from 2024-07-29.

  These are consistent with splits or distributions on those dates; I did not check them against issuer notices.
- **Not dividend-adjusted.** No file shows a level step against itself, and the stooq comparison below confirms it.
- **Default window.** `nasdaq_json.py` defaults `--from` to 2020-07-01, so ten years needs `--from` passed explicitly.

### 3 · Calendar artifacts (`S/edge/data/calendar/`, built by `S/edge/quartermaster/calendar_build.py` from `barqc.sessions_between` / `nyse_holidays`)

- **`nyse-sessions-1999-2026.csv`**: one row per scheduled session. Columns:
  - the closure flag;
  - the session's position counting from the start and from the end of its month, on both the scheduled and the actual calendar (−1 is the last session; Sandy shifts October 2012's positions on the actual calendar);
  - the last session before a holiday and the first after;
  - monthly expiration, with a note when it is moved;
  - triple witching, quarter end, year end;
  - the rule-derived half-day (labelled unverified);
  - whether the minute feed observed a short session (2020-07-27..2026-09-01).
- **`holidays-1999-2026.csv`**: the 253 holidays, named, with the session on each side.
- **`opex-1999-2026.csv`**: 336 monthly expirations. These moved to a Thursday because the third Friday was a holiday: 2000-04-20, 2003-04-17, 2008-03-20, 2014-04-17, 2019-04-18, 2022-04-14, 2025-04-17 (all Good Friday) and 2026-06-18 (Juneteenth). 2026-06-18 is also the session before a holiday and a triple-witching day.
- **`calendar-vs-files.txt`**: every disagreement between the calendar and the bar files.
  - The 10 known closures are absent from every file that spans them. For 2007-01-02, 2012-10-29/30, 2018-12-05 and 2025-01-09 that means 10, 10, 28 and 42 files, across stooq, nasdaq and Alpaca. The four 9/11 days and 2004-06-11 have only QQQ-long as a witness.
  - The only other gaps are holes: 2011-02-17 in the nine stooq files but present in QQQ-long; 1999-11-16 in QQQ-long, the only file spanning it; and 2025-03-10 in the Alpaca aggregate.
  - No file has a bar on a closed day.
- **Sample sizes** (calendar counts only; `S/edge/quartermaster/sample-size-counts.txt`):

| Span | Month-ends | Sessions before a holiday | Expirations | Quarter ends | Rule half-days |
|---|---|---|---|---|---|
| stooq SPY | 259 | 195 | 258 | 86 | 45 |
| QQQ since 1999 | 330 | 248 | 330 | 110 | 58 |
| nasdaq 2016–26 | 120 | 94 | 120 | 40 | 21 |

### 4 · Event calendars (`S/edge/data/events/`)

**How they were retrieved.** WebFetch failed on every host, so I used WebSearch restricted to `federalreserve.gov` or `bls.gov`. `websearch-log.md` records the query, the time window (04:44–04:47Z), every returned URL and the dates as the tool summarised them. The summaries are second-hand: the tool read the official page, I did not.

**What each date's status means:**
- **URL**: an official filename encodes the date, e.g. `fomcminutes20081029.htm` or `cpi_09152005.pdf`.
- **PAGE**: the tool's summary of the official year page.
- **MINUTES-REF**: only mentioned as the "next meeting" in other minutes.
- **SECONDARY**: from a non-official site.

**What was retrieved:**
- **`fomc-statements-2005-2026.csv`**: 111 dated scheduled statements (URL 73, PAGE 26, MINUTES-REF 4, SECONDARY 8). Every one is an NYSE session. There are 9 placeholders marked UNVERIFIED (April 2014, and 2017–2024), plus 14 intermeeting actions found in 2007–2010; that list is not complete.
  - Statement times quoted in results: 12:30 p.m. on 2011 press-conference days and 2:15 p.m. for December 2011; 12:20–12:35 p.m. on 2012 press-conference days; 2:00 p.m. for the 2013–2016 dates quoted.
  - Times for 2005–2010 are not sourced.
  - Official year pages, for example: [2005](https://www.federalreserve.gov/monetarypolicy/fomchistorical2005.htm), [2010](https://www.federalreserve.gov/monetarypolicy/fomchistorical2010.htm), [2015](https://www.federalreserve.gov/monetarypolicy/fomchistorical2015.htm), [2021–27 calendar](https://federalreserve.gov/monetarypolicy/fomccalendars.htm).
- **`cpi-releases-2005.csv`**: 12 dated releases. The release of June 2005 data is unverified. Sources: [BLS 2005 schedule](https://www.bls.gov/bls/bls2005sched.pdf) and archived releases such as [cpi_09152005](https://www.bls.gov/news.release/archives/cpi_09152005.pdf).
- **`employment-situation-releases.csv`**: empty and marked UNVERIFIED.

No fetched text tried to instruct me. The search tool did append its own formatting reminder, and in its 2012 summary it offered a March 2012 date "from general knowledge". I did not accept that date until an official URL (`monetary20120313a.htm`) confirmed it.

### 5 · Price basis (`S/edge/quartermaster/basis/`, built by `basis_compare.py`, `disagreements.py`, `threeway_open.py`)

**Method.** For each common date, I compared each file's Open and Close against nasdaq.com's official Open and Close.
- `gap = |file − nasdaq| / nasdaq`, by year: median and worst.
- `open-basis = |(file_open/nasdaq_open) / (file_close/nasdaq_close) − 1|`. This is about 0 when the open is on the same basis as that day's close.
- An **adjustment event** is a single-day jump in the close ratio of more than 4 bp that is confirmed by a 5-session level shift.
- At each event, the open is classed **post** if it sits on the new close's basis (the dividend is removed from the close-to-open gap) and **pre** if it sits on the prior close's basis.

Full tables are in `basis-yearly-gaps.txt/.csv`, `basis-events.txt/.csv` and `compact-2020-2026.txt`.

**Median close gap to official, bp, 2020–2026** (raw, so it includes any back-adjustment):

| file | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|---|---|
| SPY-1d.csv | 662 | 523 | 388 | 230 | 94 | 0.0 | 0.0 |
| DIA-long | 50 | 31 | 10 | 0.0 | 0.0 | 0.0 | 0.0 |
| EEM-long | 981 | 848 | 632 | 415 | 166 | 0.0 | 0.0 |
| EFA-long | 460 | 237 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| GLD-long | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| IWM-long | 258 | 157 | 51 | 0.0 | 0.0 | 0.0 | 0.0 |
| QQQ-long | 288 | 232 | 178 | 108 | 45 | 0.0 | 0.0 |
| TLT-long | 1571 | 1449 | 1302 | 1045 | 724 | 327 | 0.0 |
| XLE-long | 1964 | 1550 | 1155 | 791 | 482 | 168 | 0.0 |
| XLF-long | 416 | 230 | 51 | 0.0 | 0.0 | 0.0 | 0.0 |
| SPY-1d-agg (IEX) | 1.2 | 0.9 | 1.3 | 0.9 | 0.8 | 1.1 | 0.9 |

**Worst single days.** For the stooq files, the open-basis median is 0.0–0.4 bp in every year 2020–26, except XLE 2025 (3.3 bp) and XLF 2025 (1.0 bp). The worst open-basis days, from `disagreements.txt`:
- **2018-02-20**: stooq shows O=L=C on SPY, EEM, EFA, GLD, QQQ and XLE. GLD's open is 82 bp off the official open, XLE's 75 bp.
- **XLF 2018-02-14**: stooq shows a flat O/H/L, 245 bp off.
- **QQQ and TLT, 2023-06-26**: 35 and 30 bp. The Alpaca reading matches nasdaq, so stooq is wrong.
- **XLE**: 53 days over 10 bp, most in 2024-11..2026-03, with a worst of 58 bp on 2025-04-03.
- **XLF**: 17 days over 10 bp.
- Isolated close spikes: only SPY and GLD on 2026-04-20 (the nasdaq placeholders) and two small ones on XLE and XLF.

The three-way check in `threeway-open.txt` covers 72 disagreements from 2020-07-27 on. The Alpaca open is nearer stooq's 45 times and nasdaq's 27 times. Neither vendor documents whether its "open" is the primary-listing opening auction.

**Where the ex-dividend adjustment falls between a close and the next open:**
- **stooq**, for each file between 2016-10-10 and its cutoff: SPY 34, DIA 47, EEM 18, EFA 12, IWM 24, QQQ 34, TLT 113, XLE 38, XLF 24, GLD 0. **All 344 are post** (zero pre, zero ambiguous), so the dividend is credited to the overnight leg. After each cutoff the files are unadjusted, so later ex-dates are charged to the overnight leg as price drops. Per year: `stooq-events-per-year.txt`.
- **Alpaca total-return files**, checked at the ex-dates located exactly by stooq: post 129, pre 9, ambiguous 8 (`alpaca-open-at-known-exdates.txt`). The pre and ambiguous cases are small DIA dividends, noisy IEX opens on XLF, and the 2024-12-23 feed hole. **Alpaca puts the adjustment on the ex-date open.**
- **nasdaq files and SPY-1d-agg**: no dividend adjustment, so every ex-date shows up as a close-to-open drop.
- **Not located**: ex-dates after each stooq cutoff for SPY, and anything before 2016-10-10, have no adjusted-plus-unadjusted pair on disk.
- **Size of the steps** (`exdate-step-ranges.txt`, basis steps not returns): SPY 30–59 bp, QQQ 11–30, IWM 15–52, XLF 34–85, XLE 53–299 (the 299 bp step on 2019-12-30 is unverified), EEM 6–189, EFA 20–222, DIA 4–31, TLT 10–40.
- **Placement on the calendar**: `exdates-on-calendar.txt` and `exdates-in-tom-window.txt`. Only 5 non-TLT ex-dates fall in a turn-of-month window (sessions −2..+4): EEM and EFA on 2021-12-30, IWM on 2017-07-06 and 2018-07-03, and XLE on 2019-12-30. TLT has 104.

### 6 · Manifest

`S/edge/data/MANIFEST.csv` has 43 rows. Each row gives file, source, URL, fetched_at, span, bars, missing, adjustment basis, barqc verdict and caveats, covering every on-disk and fetched file. In short:

| File | Source | fetched_at | Basis | barqc | Key caveat |
|---|---|---|---|---|---|
| nine stooq `-long` | stooq browser download | not recorded; committed 2026-09-06 (EEM 2026-09-07) | split-adj; distributions back-adjusted to the cutoff above, unadjusted after | PASS | 2018-02-20 open defects; XLE and XLF opens unreliable vs official |
| `SPY-1d.csv` | stooq browser download | committed 2026-09-03 | adjusted to 2025-03-21, unadjusted after | PASS | **last bar mid-session** |
| nine Alpaca `X-1d.csv` | Alpaca v2, IEX | committed 2026-09-04 | total return, adjustment on ex-date open | PASS | O/C are IEX prints; IEX-only volume |
| `SPY-1d-raw.csv` | nasdaq JSON | 2026-09-06T23:16:06Z | split-adj, no dividends | PASS | **2026-04-20 placeholder**; 2026-04-17 volume placeholder |
| `SPY-1d-agg.csv` | Alpaca IEX 1m → daily | minute fetch 2026-09-03T18:45:53Z | **no dividends** (README says adjusted) | PASS | IEX prints; 2025-03-10 hole |
| 21 `edge/data/nasdaq/*` | nasdaq JSON | 2026-10-09 04:30–04:34Z | split back-adjusted, no dividends, 10-year cap | 18 PASS, 3 BLOCKED | 2023-06-05 high < open (IWM XLE XLF); 2026-04-20 placeholders (SPY SSO GLD GBTC) |

## What this data can and cannot support

- **Calendar / turn-of-month (equity index): supported on closes.**
  - SPY 2005-02-25 → 2026-09-02 gives 259 month-ends, and QQQ 1999 → 2026 gives 330.
  - Stooq closes match official closes once the adjustment factor is removed. None of the 34 SPY or 34 QQQ ex-dates falls in a −2..+4 window, so the dividend basis does not touch SPY or QQQ turn-of-month days.
  - Market-on-close entry and exit is priced correctly by these closes.
  - Required fix: drop or replace SPY's mid-session 2026-09-02 bar.
  - Official cross-check: nasdaq 2016-10 → 2026-10 has 120 month-ends.
  - Nothing before 2005 for SPY. Turn-of-month is a heavily published effect, so this data cannot make it out-of-sample.
- **Month-end stock–bond rebalancing: supported for SPY and TLT on stooq through 2026-04-01 only, with care.**
  - TLT goes ex on the first session of the month (104 of 113). Stooq TLT puts that adjustment on the day-+1 open, so close-to-close turn-of-month returns are total-return until its cutoff.
  - Raw nasdaq TLT, IEF and SHY carry an artificial day-+1 drop of 17–43 bp (TLT, 2023–26), the size of the effect being sought. They must not be used unadjusted.
  - IEF and SHY exist only from 2016-10 and have no dividend reference, so they are unusable here.
  - A month-to-date relative-performance signal must be computed from prices available before the market-on-close cutoff. Signing with the same close you trade at is look-ahead.
- **Pre-holiday: supported for close-to-close (MOC).**
  - 195 such sessions in the SPY span and 248 in QQQ since 1999.
  - 45 of those sessions in the SPY span are rule-derived half-days. These are verified only for 2020-07..2026-09 (12 of 12). Their earlier market-on-close cutoff is not verified here.
  - Watch collisions: 2026-06-18 is pre-holiday, the moved expiration and triple witching on the same day.
- **FOMC / macro announcements: FOMC is partly supported; CPI and jobs are not.**
  - There are 107 verified or secondary FOMC dates inside the SPY span, but only 16 inside the official nasdaq window, because 2017–2024 is missing.
  - Daily bars can express close(t−1) → close(t), or the overnight and intraday legs. That window includes the 2 p.m. announcement and its reaction, not the published 2 p.m.-to-2 p.m. pre-announcement window. Minute data are not on disk: `SPY-1m.csv` is absent.
  - There is no usable CPI or Employment Situation calendar.
  - Finishing the FOMC, CPI and jobs dates needs roughly 3 searches per year in a turn with search budget. For CPI and jobs, the BLS schedule PDFs give planned dates; the shutdown years (2013, 2025) need the archived-release filenames for the actual dates.
- **Options expiration: the calendar is supported; the prices are hazardous.**
  - SPY's quarterly and DIA's monthly ex-dates fall on the expiration Friday itself, and QQQ, XLE and XLF mostly go ex the Monday after. On any unadjusted series those days carry the payout as an overnight drop: SPY 30–59 bp.
  - Usable series: stooq before its cutoff, or Alpaca total-return. Not usable: nasdaq raw, SPY-1d-agg, or SPY-1d.csv after 2025-03-21 unless the dividends are added back.
  - There is no options data at all (open interest or gamma).
- **Overnight / intraday splits: supported on SPY with explicit repairs.**
  - Closes are reliable.
  - Opens need these excluded: 2017-10-09 and 2018-02-20 (stooq), and 2026-04-20 (nasdaq).
  - XLE and XLF opens are not dependable.
  - Alpaca and the aggregate's opens are IEX prints and cannot price a market-on-open fill.
  - Dividends ride the overnight leg wherever the adjustment is applied. SPY-1d.csv switches to unadjusted after 2025-03-21. Its later ex-dates are not located on disk, so that tail of EVIDENCE §C books an unknown number of payouts as overnight losses.
  - Best basis: nasdaq official 2016-10 → 2026-10 plus a dividend list, which the stooq steps supply up to 2025-03-21. For 2005–2016, use stooq with the listed defects removed.
- **Leveraged expression: supported 2016-10 → 2026-10 only.**
  - SSO, UPRO, QLD and TQQQ are official prices, split back-adjusted, with dividends not adjusted.
  - SSO needs its 2026-04-20 bar patched.
  - No 2008: the nasdaq history is capped and Yahoo answered 429.
  - Synthetic SPY leverage needs a financing rate, which is not on disk. ^IRX was not obtained, and BIL and SHV prices are dividend-unadjusted, so the cash yield cannot be read off them.
- **Crypto: not supported for crypto-native edges.**
  - There is no BTC daily through the repo's fetchers.
  - IBIT (2.7 years), BITO (futures-based) and GBTC (a trust before 2024, adjusted at 2024-07-29) trade only in the US session. Weekend and 24/7 effects are invisible, and IBIT is too short for calendar work.

## What I could not verify

- **FOMC 2017–2024** (all meetings), **April 2014**, statement times before 2011, and completeness of intermeeting actions. **CPI 2006–2026**, plus the release of June 2005 data. **Employment Situation**, all years. Every event date is second-hand from a search summary; none was read directly.
- **Opens**: whether any vendor's "open" is the primary-exchange opening auction, and the market-on-open and market-on-close cutoffs on half-days.
- **Half-days before 2020-07-27**: rule only.
- **Closures before 2005-02-25**: the 2001 and 2004 closures and the 1999-11-16 hole each rest on one file (`QQQ-1d-long.csv`), plus EVIDENCE.md §E-15.
- **Split dates and ratios**: UPRO 2022-01-13, QLD/SSO/TQQQ 2025-11-20, XLE 2025-12-04, GBTC 2024-07-29 are inferred from where fractions of a cent stop in the closes, not from issuer notices.
- **Stooq's adjustment placement before 2016-10-10**: there is no unadjusted reference for that period. The early-year gaps grow as you go back, which is consistent with adjustment, but this is not event-checked. XLE's 299 bp step on 2019-12-30 is unverified.
- **Ex-dividend dates and amounts after each stooq cutoff**, for SPY in particular.
- **BIL's flat bars** may be genuine. **GBTC's premium history** is not measured.
- **Retry count**: fetch.py retried Yahoo three times automatically inside one invocation. That is the repo's built-in behaviour; I did not re-invoke it.

**Files.**
- Scripts: `S/edge/quartermaster/{calendar_build,basis_compare,disagreements,threeway_open,events_build}.py`
- barqc logs: `S/edge/quartermaster/barqc/`
- Basis outputs: `S/edge/quartermaster/basis/`
- Data: `S/edge/data/{nasdaq,calendar,events,yahoo}/`
- Manifest: `S/edge/data/MANIFEST.csv`
