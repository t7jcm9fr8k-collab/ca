**SIGN** (Quartermaster). My deal-breaker, offsets taken from the scheduled calendar, is adopted at L31–33.
**Checked against files** (`S/edge/quartermaster/r3/prereg-draft-checks.txt`, `r2/*`); all correct: both SHA-256s (L62, L94); S1's 257 cycles and 5,387 sessions (session 1 = 2005-03-28, session 5,387 = 2026-08-25); p̂ = 1,796/5,387 = 0.3334; the G2 midpoint, session 2,694 = 2015-12-07.
Also correct: G7′'s 71 cycles and 1,485 sessions; the 106 / 120 / 31 sub-span windows; the add-back dates at T−6…T−7; the closure dates; `strategies.py:208` is `rsi_dip`.
**Confirmed: the add-back formula is right on this file's basis.** On each of the five ex-dates and the bar before it, the file's open and close equal the official prices to the cent (stooq/official ratio 1.000000), so the file is raw there and r_on = (open + D)/close(t−1) − 1 is the total-return overnight leg.
**Confirmed: both exclusions are right.**
- **2025-03-21** is already inside the file's adjustment: the ratio is 0.997001 on 2025-03-20 and 1.000000 on 2025-03-21, open and close alike, so the step sits on that day's open.
- **2026-09-18** falls after the last row read (2026-09-01).
**Corrections:**
1. **L89, ambiguity.** "close(t−1)" means the previous bar's close. For 2025-06-20 that is 2025-06-18, because 2025-06-19 (Juneteenth) was closed.
2. **L54 / L96 / L157, ambiguity.** Each frozen CSV also holds two incomplete windows (S1: 2005-02 and 2026-08; G7: 1999-02 and 2005-02), with `complete=False` and exit_exec set to the scheduled date. G0 should match only the `complete=True` rows (257 and 71), or those rows should be dropped from the frozen files.
3. **L44.** Add: "November 2018 also contains a closure (2018-12-05) but keeps 7 held sessions, because its exit rolls to 2018-12-06."
4. **L256.** The FOMC dates also lack April 2014, and the 2025 dates are SECONDARY grade (`D/data/events/fomc-statements-2005-2026.csv`).
5. **L291, wrong (and so is my r2 §4).** Measured against official lists, stooq misses two payouts: TLT 2023-12-14, and QQQ 2023-12-27 ($0.21584, at T−2; the QQQ ratio stays at 0.992612–0.992614 across it). Neither enters S1, and the QQQ miss lies outside G7′'s 1999–2005 span. SPY is 34 of 34 for 2016-12 → 2025-03. Suggested text: "Measured misses in 2016–2026: TLT 2023-12-14 and QQQ 2023-12-27, both outside this run's scored spans; SPY 34/34."
6. **L66, clarity.** The first scored session is 2005-03-28, because 2005-03-25 (Good Friday) was closed.
