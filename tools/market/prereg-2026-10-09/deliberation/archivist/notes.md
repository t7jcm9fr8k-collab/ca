# Archivist working notes (round 1) — started 2026-10-09

## Access constraints observed (measured this session)
- WebFetch: getaddrinfo ENOTFOUND for nber.org, ssrn, duke, kentdaniel.net, inquire-europe (i.e. blocked); works for github.com.
- curl via proxy: 403 CONNECT for ssrn, nber, arxiv, oup, sciencedirect, wiley, crossref, openalex, semanticscholar, core, repec, archive.org, quantpedia, alphaarchitect, cxo, etc.
- Allowed: github.com (HTML), raw.githubusercontent.com (files), pypi.org; Yahoo 429.
- So: verification levels used:
  V-text  = read in primary text (GitHub-hosted copy or repo README by the authors)
  V-snip  = confirmed in search-engine snippet attributed to the primary source (abstract / landing page / PDF snippet)
  U       = unverified (secondary only / memory)

## Intramonth Momentum Cycle (Nathan, Suominen, Tasa 2026, SSRN 6426026, working paper)
- README at raw.githubusercontent.com/dannyboy990/momentum-replication/main/README.md (V-text, authors' replication repo):
  "nearly all US momentum profits accrue in a six-day window before the turn of the month (PreTOM, trading days t-9 to t-4)"
  "PreTOM is 28.6% of trading days but produces 77% of momentum's log wealth."
  "WML in PreTOM: +10.2 bps/day (t = 3.7). WML in the rest of the month: +2.4 bps/day (t = 1.2)."
  "Losers earn -11.3 bps/day in PreTOM (t = -3.5) and +5.5 bps/day outside it."
  "The shift from T+2 to T+1 settlement in May 2024 moves the loser trough one day later"
  sample 1980-2025 (bundled 1927-2025 daily)
- Search snippet (V-snip): post-reform 19 months vs 533 pre; "T-3 absorbs -27 bp additional selling pressure; T-4 shifts up +43 bp" after May 2024.

## Dash for cash (Etula, Rinne, Suominen, Vaittinen, RFS 33(1) 2020 pp 75-111)
- V-snip: WP version: S&P500 VW -17bp over T-8..T-4, +77bp over T-3..T+3 (since 1995 T+3 settlement). Share of 7-day TOM return earned T-3..T-1 = 47% after June 1995 vs 30%.
- V-snip: returns larger when T is a Friday (T-3..T-1 returns 2.5x).
- V-snip: US reversals strengthened over time with mutual fund ownership.

## McConnell & Xu 2008 FAJ 64(2):49-64
- V-snip: TOM = last trading day + first three ([-1,+3]); CRSP 1926-2005 (published) — "investors received no reward for bearing market risk except at turns of the month"; 31 of 35 countries; no evidence volume/flows higher at TOM.

## Pension rebalancing (Harvey, Mazzoleni, Melone; NBER w33554, March 2025, rev Jan 2026; SSRN 5122748) — working paper
- V-snip abstract: "When stocks are overweight, funds sell stocks and buy bonds, leading to a decrease in equity returns of 17 basis points over the next day." ; cost ~$16bn/yr (~$200/household).
- V-snip: threshold rule (e.g. 2pp band around 60/40); calendar rule: rebalance on last business day of month; N days before month-end chosen via predictive regressions (=> in-sample choice of N and delta!).

## HMM rebalancing — more (V-snip unless noted)
- Sample: daily futures 1997-2023 (S&P 500 futures vs 10y T-note futures); 60/40 drift.
- Calendar predictability peaks in the last four days of the month.
- 1-SD calendar signal -> equity -17 bp, bonds +2 bp next trading day. Reverts almost entirely within two weeks.
- Long-short futures strategy: ~10% annualized, Sharpe > 1 (vs 0.35 equities, 0.48 bonds), after TC Sharpe close to 1.
- Practitioner (QuantReturns, U): calendar signal excl. final day, 1997-09-10..2023-03-17: CAGR 8.11%, vol 6.51%, Sharpe 1.24, MDD -8.9% (unscaled).
- Others (U): SPY/TLT version CAGR 15.6% Sharpe 1.17 (unknown source); paperswithbacktest 1990-2026 Sharpe -0.20 (method unknown).
- Kent Daniel discussion (Red Rock 2025): questions $16bn cost estimate (no holdings/trades data).

## Kayacetin 2026, JIFMIM vol 109 (peer-reviewed) — "Infrequent rebalancing, risk deferral, and equity returns at the turn of the month" (SSRN 7201062)
- V-snip (2 searches agree): 30 indices 1994-2023; window = last 4 + first 4 trading days; mean 10 bp/day in window vs 0 bp other days; window = all positive mean returns in 25 markets, >2/3 in other 5.
- Persistence: "arbitraged away in the first decade following its publication, it comes back in full force"; most economically significant in the U.S. in 2019-2023.
- Stronger at fiscal quarter/half-year ends; relief rally after high-vol/low-return episodes.

## TOM others
- Chen & Chua 2011 J. Financial Planning: after ETFs, S&P500 TOM concentrated on 1st trading day; for the ETF, last trading day of month NEGATIVE average; T-bill switching underperforms B&H in recent times (V-snip).
- Carchano & Pardo (S&P500 futures 1991-2008): TOM is the only calendar effect significant & persistent (V-snip via secondary).
- ATB Research substack 2026 (blog): TOM "mostly doesn't survive" on E-mini 60-min data (U).
- Quantpedia 2026 sector-ETF intramonth momentum (blog; 1998-12..2026-06): composite 5.99%/yr Sharpe 0.55 (L/S) — practitioner.

## FOMC family
- Lucca & Moench JF 2015 70:329-371; WP: >80% of equity premium in 24h pre-FOMC (1994-2011); FOMC-day ~33 bp vs ~1 bp (LSE blog) (V-snip).
- Kurov, Wolfe & Gilbert FRL 40 (2021): drift essentially disappeared after 2015 (sample to Dec 2019) (V-snip).
- BIS WP 1079: FOMC premium diminishing, "only 22 bps after 2012" (V-snip, single).
- Cieslak, Morse, Vissing-Jorgensen JF 74(5) 2019: equity premium since 1994 earned in even weeks 0,2,4,6. Post-pub: an indep WP says no OOS; one summarizer claims Annual Review reports opposite cycle 2017-2021 (NOT confirmed on second search => U).

## Macro announcement premium
- Savor & Wilson JFQA 2013: 1958-2009, 11.4 bp announcement days vs 1.1 bp other days; >60% of equity premium on 13% of days (V-snip).
- Ai, Bansal, Guo NBER w31923 (2023 WP): 1961-2023; ~10 bp/day vs ~1 bp; 44 announcement days/yr = 4.65%/yr = ~71% of 6.59% premium (V-snip; OCR-garbled number).
- Hu, Pan, Wang, Zhu JFE 2022 "Premium for heightened uncertainty": pre-announcement pooled (NFP, ISM, GDP, FOMC) 5.66%/yr; FOMC 27.1 bp t 5.95; others ~10 bp (V-snip).

## Pre-holiday
- Ariel JF 1990 45(5):1611-1626: pre-holiday 9-14x normal day mean (V-snip).
- Vergin & McGinnis AFE 1999: disappeared for major US indices 1987-1996 (V-snip secondary).
- Chong, Hudson, Keasey, Littler JIMF 2005 24(8):1226-36: decline significant in US; reversed 1991-97; vanished 1997-2003 (V-snip).

## Halloween
- Bouman & Jacobsen AER 2002: 36/37 markets 1970-1998 (V-snip; Andrade et al. text says 35 higher, 20 significant).
- Andrade, Chhaochharia, Fuerst FAJ 2013 69(4): OOS 1998-2012, ~10pp higher Nov-Apr vs May-Oct avg across 37 (V-snip).
- Zhang & Jacobsen JIMF 2021 vol 110 art 102268: all indices worldwide, 62,962 obs: Nov-Apr ~4% higher; summer excess ~ -1% (V-snip).

## Overnight
- Boyarchenko, Larsen, Whelan RFS 2023 36(9):3502-3547: US equity futures returns concentrated 2-3am ET (European open); selloffs -> robust positive overnight reversals (V-snip).
- Liberty Street Economics July 2026 "The Disappearing Overnight Drift" (same authors): 2-3am window previously ~3.7%/yr "has averaged close to zero since 2021" (V-snip).
- Bondarenko & Muravyev JFQA 2023 58(3):939-967: 4 hours around EU open = entire avg market return, E-mini 2004-2018 (V-snip).

## Treasury auction cycle
- Lou, Yan, Zhang RFS 2013 26(8):1891-1912: yields rise before auctions, fall after; 5-day gap ~22.5 bp (5y) / 23.8 bp (10y) price (V-snip draft numbers).
- NY Fed SR 1188 (Fleming, Liu, Nguyen, Mar 2026): intraday pre-auction rise/reversal persists, not grown (V-snip).
- HBS WP 26-033: post-auction yield decline vanished after 2010 (V-snip).
- Robeco 2025 note: 10y futures decline ~6 bp (price) ahead of auction, recover in hours after; 1983-2024 (V-snip).

## Treasury end-of-month
- Hartley & Schwarz WP 2019 (Rodney White Center 17-19; SSRN 3440417): coupon Treasuries excess returns positive & highly significant in last few (3-5) days of month, ~0 otherwise; 10y last 3 days ~0.25%/month (3pp/yr); Sharpe ~1; Jan 1990-Dec 2018 modeled prices; 2015-2018 weaker but significant; life insurers buy on index rebalancing dates (V-snip). Not found as published.
- CXO: TLT since 2002 TOM test does not corroborate (V-snip secondary).

## OpEx
- Stivers & Sun JBF 2013 37(11):4226-4240: S&P 100 stocks high returns in OE week; 4th-Friday weeks modestly underperform (V-snip).
- WP (CXO summary): S&P 500 index OE-week high 1983-2008, not before 1983; 28 large caps 0.45% vs 0.12% other weeks 1996-2008 (V-snip secondary).
- Practitioner: hold S&P only in OE week CAGR ~2% (U).

## LETF
- Lenkey 2024 survey (QFE): stat-significant but economically insignificant; methodological errors common (V-snip).
- Ivanov & Lenkey JFM 2018 41:36-56: after flows, economically insignificant (V-snip).
- Beckmeyer et al. (SSRN 3925725): LETF price pressure reverts at next open; LETF effects decreased over time (V-snip).

## Crypto
- Liu & Tsyvinski RFS 2021: TSMOM at 1-4 week horizons (V-snip).
- "Cryptocurrency momentum has (not) its moments" FMPM 2025: post-July-2020 crypto momentum negative & insignificant (cross-sectional) (V-snip).
- Han, Kang, Ryu: after costs/liquidation many momentum portfolios insignificant; TSMOM evidence strong vs XS weak (V-snip).

## More TOM evidence (round 2 searches)
- Etula et al. slides (V-snip): chart "From T-3 to T+3" vs "On other days", years 1926-2013 on axis; "all returns in the US stock market have accrued during just seven days around the turn of the month"; later version: "strong market level return reversal four days before month end at T-4 (in stocks and bonds)"; published: institutions net sellers T-4,T-3, net buyers last day & first days; selling T-8..T-4 predicts higher T-3..T-1 returns; "elevated stock and bond yields right before the month end".
- WP quote via hedgefundalpha (V-snip): since 1926, hold S&P 500 seven business days/month -> almost entire market return with 40% lower volatility.
- Maberly & Waggoner 2000 (Atlanta Fed WP 2000-11): TOTM in S&P futures disappears after 1990, carries to spot (V-snip) — conflicts with McConnell-Xu persistence 1987-2005.
- Liu 2013 JBER: SPY 2001-2011 TOM exists but moved earlier (V-snip).
- Quantseeker blog (U): classical [-1,+3] TOM largely disappeared in past decade.
- Norgate-based (ETF Trends, practitioner): S&P 500 1980-2024Q3, 4 TOM days/month -> annual return only 0.89% lower than all other days combined (U).
- QuantConnect (practitioner): SPY TOM 2001-2018 CAGR 3.0%, Sharpe 0.354 (U).
- Dynamic anomaly study (Marquering et al.?): time-of-month effect disappeared after publication (V-snip, version discrepancy).
- Graziani JMP 2024 (WP): S&P 500 end-of-month return (4th Friday -> last trading day) negatively predicts next-month return; long after negative, 1975-2020; link to pension liquidity trading (V-snip).
- Wang & Zhao 2025 WP "Pre-Refunding Announcement Gains in U.S. Treasurys": positive returns in medium/long Treasuries on day before quarterly refunding announcements, 1991-2023, increasing with maturity, strengthening; 4-days/yr strategy Sharpe > 4 (V-snip; magnitude not found).
- Nuance: Kayacetin's [-4,+4] ~ Etula's [T-3, T+4]: the dash-for-cash window, not the classic [-1,+3].

## Execution/leverage facts (V-snip)
- Alpaca fractional orders: DAY TIF only => MOO/MOC (opg/cls) need whole shares (docs.alpaca.markets/docs/fractional-trading).
- Alpaca: commission-free; SEC fee (sells) ~ $20.60/$1M as of Apr 2026 (third-party, U); FINRA TAF $0.000195/sh cap $9.79 (third-party, U); CAT fee small.
- Alpaca margin rate 7.75%/yr (undated support page), charged on EOD debit, actual/360; 2x overnight (Reg T); FINRA intraday margin framework replaced PDT (June 2026): 4x intraday with >= $2,000 equity (Alpaca blog).
- Avellaneda & Zhang 2010 SIAM J Fin Math 1:586-603: log LETF = beta*log(index) - beta(beta-1)/2 * integrated variance (+ fees/financing).
- SSO TER 0.88%, UPRO 0.89% (ETFCentral) (V-snip).
- "A Levered ETF Anomaly Explained" (2023-24): Jan 2022-Dec 2023 SSO actual -5.7% vs ideal -3.6%; UPRO -15.3% vs -10.6% (V-snip).
- Gayed & Bilello 2016 (Dow Award): leverage when S&P above MA; CXO reconstruction 2x above SMA200 / T-bills below, Oct 1928-Oct 2015: Sharpe 0.51 vs 0.30 B&H (1% leverage cost, no switching costs) (V-snip secondary).
