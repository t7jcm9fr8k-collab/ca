# How does this hold up? — the evidence, method by method

*2026-09-02. Produced by an adversarial research pass: six clusters covering the
ten methods you named, one researcher per cluster verifying its citations by
search, two skeptics per cluster (one attacking every claim of edge, one
attacking every dismissal), one synthesis. 19 agents, 832 tool calls, 1.6M
tokens. Where a citation says* (verified) *the researcher confirmed the paper
exists and says what is claimed; where it says* (unverified this run) *it was
introduced by a skeptic whose search budget was exhausted, and it was used only
to scope a verdict, never to upgrade one to "edge".*

The stack, in your words: *candles to see a pattern, rejection blocks, EMA,
VWAP, order flow/volume, market auction theory, options and greeks, price
levels, indicators, sentiment.*

---

## The honest paragraph

Taken as a whole, your stack is a good vocabulary for describing what the
market did and a poor set of rules for predicting what it will do. Almost every
piece has a real thing behind it: institutions really are benchmarked to VWAP,
stops and take-profits really do cluster at round numbers and prior highs,
option dealers really do hedge, signed order flow really does move prices, and
sentiment really does push speculative stocks around for months. But in each
case the money is made by someone with data, latency or horizon you do not
have — dealers and HFTs with the order book, monthly-rebalanced long-short
portfolios across hundreds of stocks — and the retail translation into a chart
rule (a hammer at a level, an EMA cross, a fair value gap, a gamma flip, an RSI
extreme, a VWAP bounce) has either been tested and found worthless after costs
or has never been tested because it is defined after you see the outcome. The
ICT/Smart Money layer in particular has no evidence at all, and the one
mechanism it borrows (stop clustering) predicts the *opposite* of "sweep and
reverse". Stacking these signals into "confluence" does not fix this: they are
mostly transforms of the same closing prices, agreement among them is the
expected state in a trend, and the search that produced your favourite
parameter set was guaranteed to find something.

Two things do survive: a slow trend filter on an index reliably cuts drawdowns
(without raising returns), and the last-half-hour intraday momentum effect
created by hedging flow has published after-cost evidence on SPY through 2020
and is sitting inside your minute bars waiting for a 2021–2026 holdout. The base
rate for people who trade the rest of the stack persistently at small size is
that about **97% lose money after fees**, in two separate countries, and that is
the number to have in mind when a chart looks obvious in hindsight.

---

## The grades

Every method was sorted into one of four bins. Most land in (a) or (b).

| | means |
|---|---|
| **(c) edge** | documented out-of-sample profit **after costs**, in a peer-reviewed sample |
| **(b) mechanism** | a real economic or microstructure reason it *could* work, documented — but no after-cost edge for a retail chart rule |
| **(a) descriptive** | genuinely useful for *reading* what the market did; no predictive claim survives |
| **✗ / unfalsifiable** | tested and null after costs, or defined after the outcome so it cannot be tested |

## The ranking

| # | method | grade | testable with |
|---|---|---|---|
| 1 | **Intraday momentum from hedging flow** — sign of the first 30 min / rest-of-day return predicts the last 30 min on SPY/ES | **(c)** through 2020; post-2020 untested | minute bars, free |
| 2 | **Systematic fixed-weight combination** of pre-chosen trend/volume signals, monthly or weekly | (b) with documented OOS predictability, ~1% R² | daily bars, 20+ yrs |
| 3 | **Variance risk premium / VIX term structure** | (b) a real premium; not directional | daily VIX/SPX, free |
| 4 | **Slow trend filter** — 200-day / 10-month SMA on an index | (b) cuts drawdown, does not raise return | daily bars, 30+ yrs |
| 5 | **Price levels** — S/R, prior-day extremes, round numbers | (b) real order-book mechanism; no cost-aware profit test is positive | minute bars for a pre-registered rule |
| 6 | **Order flow / volume** — delta, CVD, footprint, L2 | (b) the best-documented mechanism here; harvested by HFT in seconds | **tick / L2 — paid**; not computable from bars |
| 7 | **VWAP** as level or trigger | (a) real execution benchmark; no test of it as a signal | minute bars, free |
| 8 | **Options positioning** — GEX, 0DTE, put/call, max pain | GEX (b) but sign unidentifiable from public OI; 0DTE ✗; public P/C (a); max pain ✗ | options chain, ~$25–30/mo |
| 9 | **Generic indicators** — EMA/SMA crosses, MACD, RSI, stochastics | ✗ on liquid data since ~1990, snooping-corrected | daily bars |
| 10 | **Sentiment** — Baker-Wurgler, AAII, VIX level, social, Trends | (b) at *months*; (a) for AAII; ✗ for Twitter mood and Trends | daily; the paid feeds are where it works |
| 11 | **Classic candlestick patterns** — doji, hammer/pin bar, engulfing | ✗ every rigorous US, Japanese, intraday test | daily bars |
| 12 | **Market Profile / auction theory** — value area, POC, day types | (a); POC inherits the level mechanism (b); no test of the rest | minute bars, free |
| 13 | **"Rejection candles" / ICT rejection blocks** | unfalsifiable as stated; pre-register the level and it is a pin bar at support: ✗ | minute bars, only with a fixed level rule |
| 14 | **ICT / Smart Money** — order blocks, fair value gaps, liquidity sweeps | unfalsifiable; zero tests at any level; the stop-cluster mechanism predicts *continuation*, not reversal | — |
| 15 | **Discretionary confluence** and grid-searched parameters | no rigorous evidence either way; correlated agreement ≈ zero information; ~97% base rate | daily bars: correlation matrix, trial count, holdout |

---

## Each one, in a few lines

### 1 · Intraday momentum from hedging flow — (c) on paper, through 2020

**Mechanism.** End-of-day delta-hedging by option dealers and leveraged-ETF
rebalancing is flow that must trade regardless of price, plus late-informed
traders. Strongest on high-volatility, high-volume days. **Uses no options data
at all.**

**One line.** This is the closest thing to a real after-cost edge in the entire
stack, it lives in the exact instrument and bar size you have, and it is *not*
the opening-range breakout or "negative gamma = trend day" rule the vocabulary
suggests. Run the published rule on 2021–2026 data before believing the
2018–2021 numbers.

- Gao, Han, Li & Zhou 2018, *J. Financial Economics* (verified; SPY 1993–2013)
- Baltussen, Da, Lammers & Martens 2021, *J. Financial Economics* (verified; 60+ futures 1974–2020; the ~6.5% p.a. after-cost figure came from a search snippet and is unverified)
- McLean & Pontiff 2016, *J. Finance* (post-publication decay; unverified this run)

### 2 · Systematic signal combination at monthly/weekly horizon — (b), the defensible version of "confluence"

**Mechanism.** Slow-moving information gives trend and volume signals real but
weak forecasting power at 1–12 month horizons; averaging pre-specified
forecasts reduces estimation variance. **Requiring everything to AGREE is the
opposite operation and has never been tested.**

**One line.** Combining technical signals has peer-reviewed support only as a
fixed-weight average of pre-chosen signals, rebalanced monthly or weekly, with
a holdout — a research design you can replicate on daily ETF data, not the
chart-by-chart AND-gate.

- Rapach, Strauss & Zhou 2010, *Rev. Financial Studies* (verified; macro predictors)
- Neely, Rapach, Tu & Zhou 2014, *Management Science* (verified; 14 technical indicators via PCA, ~1% OOS R²)
- Jiang, Kelly & Xiu 2023, *J. Finance* (verified; CNN on chart images, cross-sectional, weekly turnover)
- Han, Zhou & Zhu 2016, *J. Financial Economics* (trend factor; unverified this run)

### 3 · Variance risk premium and VIX term structure — (b), a real premium

**Mechanism.** Investors overpay for volatility insurance, so implied exceeds
realized and VIX futures sit above future spot; sellers collect a premium and
bear crash risk. Predicts equity returns only at 1–6 months. **The term
structure does not forecast where VIX goes.**

**One line.** IV-minus-RV and contango measure a real premium you are paid for
eating crashes; use them as a monthly regime and sizing input in a daily-bar
backtest, and do not short volatility with real money after looking at February
2018.

- Bollerslev, Tauchen & Zhou 2009, *Rev. Financial Studies* (verified)
- Cheng 2019, *Rev. Financial Studies* (verified; predicts VIX futures, not equities)
- Simon & Campasano 2014, *J. Derivatives* (verified; in-sample)
- Johnson 2017, *JFQA* (verified)
- Augustin, Cheng & Van den Bergen 2021, *Financial Analysts Journal* (verified; the XIV/SVXY collapse)

### 4 · Slow trend filter — (b), risk management, not alpha

**Mechanism.** Time-series momentum at 6–12 months and persistent bear
regimes: a slow filter cuts exposure during extended declines at a few trades a
year. The *return premium* evidence is for diversified multi-asset futures you
cannot hold.

**One line.** The most defensible thing in the "EMA" family, but it lowers
drawdowns and roughly matches buy-and-hold return — and ten years of data
contains one or two signals of interest.

- Moskowitz, Ooi & Pedersen 2012, *J. Financial Economics* (verified)
- Zakamulin 2014, *J. Asset Management* (verified; data-mining bias, buy-and-hold-like return with lower risk)
- Huang, Li, Wang & Zhou 2020, *J. Financial Economics* (TSMOM fragility; unverified this run)

### 5 · Price levels — (b), the one chart concept with an order-book mechanism

**Mechanism.** Take-profit limit orders cluster at round numbers and salient
highs/lows (book depth = bounce); stop-losses cluster just beyond them (cascade
= breakout **continuation**). Documented directly in dealer and NYSE order
books, mostly 1996–2000 data.

**One line.** The people levels pay are dealers and limit-order posters; every
breakout/bounce profit test after costs and snooping correction is negative or
mixed. Use levels to know where liquidity and stops sit, and **never park a stop
exactly on the round number.**

- Osler 2000, *FRBNY Economic Policy Review* (verified; no costs); Osler 2003, *J. Finance* (verified); Osler 2005, *J. Int'l Money & Finance* (verified; stop cascades = continuation)
- Kavajecz & Odders-White 2004, *Rev. Financial Studies* (verified; levels coincide with book depth)
- Bhattacharya, Kuo, Lin & Zhao 2018, *Management Science* (verified; round-number clusterers lose)
- Marshall, Cahan & Cahan 2008, *J. Empirical Finance* (verified; 5-min S/R and breakout rules null)
- Barrot, Kaniel & Sraer 2016, *J. Financial Economics* (retail limit orders compensated; unverified this run)

### 6 · Order flow / volume — (b), the best-documented mechanism, and the least reachable

**Mechanism.** Signed order flow moves prices because market makers infer
information from it; queue imbalance predicts the next one-tick move by pure
queueing. Predictability decays within seconds to ~30 minutes and the profit
accrues to passive orders at the front of the queue, not to a taker paying the
spread at 100+ ms latency.

**One line.** Delta, CVD and the DOM measure something real, and that is
exactly why the information is gone before a minute bar closes. On your data
this is a way to read *why* a move happened, not to time entries; no footprint
or CVD-divergence rule has ever been tested in a journal, and **OHLCV cannot
compute delta at all** — `features.bar_delta_proxy` is labelled a proxy for
this reason.

- Hasbrouck 1991, *J. Finance* (verified); Chordia, Roll & Subrahmanyam 2002, *J. Financial Economics* (verified)
- Cont, Kukanov & Stoikov 2014, *J. Financial Econometrics* (verified); Gould & Bonart 2016 (verified; one tick ahead)
- Brogaard, Hendershott & Riordan 2014, *Rev. Financial Studies* (verified; HFT harvests imbalance in seconds)
- Baron, Brogaard, Hagströmer & Kirilenko 2019, *JFQA* (verified; latency rank = profit)
- Andersen & Bondarenko 2014/2015 (verified; VPIN lags, measures classification error)

### 7 · VWAP — (a), legitimate to plot, untested as a signal

**Mechanism.** Institutions are benchmarked to VWAP and run volume-schedule
algorithms, so it is where the day's volume-weighted flow transacted — a
fair-value reference and a partly self-fulfilling anchor. **The crossover rule
has no mechanism.**

**One line.** Nothing in the literature shows a VWAP touch or cross pays after
costs; the only pro-signal evidence is a vendor's 74,800-configuration
in-sample sweep. Backtest a mean-reversion-to-VWAP rule with honest slippage
and expect it to fail.

- Berkowitz, Logue & Noser 1988, *J. Finance* (verified; execution benchmark only)
- Madhavan 2002 (verified; VWAP algos are volume-schedule followers)
- Grinblatt & Han 2005, *J. Financial Economics* (anchored-VWAP analogue at monthly horizon; unverified this run)

### 8 · Options and greeks — mostly ✗, with one real mechanism you cannot see

**Mechanism.** Dealer delta-hedging is real: net short gamma amplifies moves,
net long gamma dampens them. It requires one-sided customer positioning, which
SPX/0DTE flow does not show — **dampening, not squeezes, is what is measured.**
Informed option trading exists but lives in buyer-initiated open-position
volume the public does not see.

**One line.** The GEX number a retail trader computes from open interest is a
guess whose sign can be wrong; 0DTE loses on average even for sellers once real
spreads are charged; the free put/call ratio has no post-1990s test that beats
buy-and-hold; max pain is folklore around a ~16 bp pinning effect. Use greeks to
understand the market, not to time it.

- Ni, Pearson, Poteshman & White 2021, *Rev. Financial Studies* (verified; hedging affects volatility)
- Barbon & Buraschi 2021, "Gamma Fragility", SSRN (verified; illiquid single stocks)
- Dim, Eraker & Vilkov 2023; Adams et al. 2025, SSRN (verified; SPX 0DTE gamma dampens)
- Beckmeyer, Branger & Gayda 2023, SSRN (verified; retail 0DTE loses on net)
- **Vilkov 2024/2026, SSRN 4641356 and its GitHub `KNOWN-ISSUES.md`, Aug 2026** (directly verified by a skeptic: after a 100× cost-scale correction, no 0DTE structure retains positive net Sharpe)
- Pan & Poteshman 2006, *Rev. Financial Studies* (verified; non-public open/close volume)
- Ni, Pearson & Poteshman 2005, *J. Financial Economics* (verified; 16.5 bp expiration clustering)

### 9 · Generic indicators — ✗

**Mechanism.** Positive autocorrelation exists at 3–12 month horizons; at the
2–6 week horizon of a 9/21 EMA on daily bars, individual stock returns *revert*;
on minute bars bid-ask bounce dominates. RSI<30 is "price fell a lot", whose
reversal flips to momentum in low-turnover stocks. 12/26/9 and 14/30/70 are
1950s–70s conventions with no return model behind them.

**One line.** Every rigorous, snooping-corrected, cost-aware test of crossover
and oscillator rules on liquid US data since ~1990 is negative, and the winning
parameters change by index. Keep the indicators as a way to describe a trend
after the fact.

- Brock, Lakonishok & LeBaron 1992, *J. Finance* (verified; in-sample, no costs)
- Sullivan, Timmermann & White 1999, *J. Finance* (verified; fails 1987–96 out of sample)
- Bajgrowicz & Scaillet 2012, *J. Financial Economics* (verified; nothing selectable ex ante survives costs)
- Marshall, Cahan & Cahan 2008 (verified; 5-min SPY); Coe & Laosethakul 2010 (verified; 576 stocks, no rule beats market)
- Nagel 2012; Medhat & Schmeling 2022, *Rev. Financial Studies* (reversal is liquidity provision; unverified this run)

### 10 · Sentiment — (b) at months, ✗ at minutes

**Mechanism.** Noise-trader demand plus limits to arbitrage pushes hard-to-value,
hard-to-short stocks away from fundamentals for *months*; media pessimism
causes temporary pressure that reverses in days; retail attention herding
reverses over ~20 days. **Surveys are caused by past returns.**

**One line.** Sentiment describes the regime and works, when it works, at
months (Baker-Wurgler) or days-after-a-paid-newswire. The free things you can
scrape — AAII, Twitter mood, Robinhood most-bought — either add nothing beyond
last month's returns or predict *losses*.

- Baker & Wurgler 2006, *J. Finance* (verified); Huang, Jiang, Tu & Zhou 2015, *Rev. Financial Studies* (verified; ~1% OOS R²)
- Brown & Cliff 2004; Wang, Keswani & Taylor 2006 (verified; surveys caused by returns)
- Tetlock 2007; Garcia 2013, *J. Finance* (verified; small, index-level, recession-concentrated)
- Lachanski & Pav 2017, *Econ Journal Watch* (verified; Bollen et al. 2011 fails replication)
- Bradley, Hanousek, Jame & Xiao 2024, *Rev. Financial Studies* (verified; the WSB signal died post-GME)
- Da, Engelberg & Gao 2011/2015 (verified; tiny, reversing); Boehmer, Jones, Zhang & Zhang 2021 (verified; paid TAQ)

### 11 · Classic candlestick patterns — ✗

**Mechanism.** A long wick records an intrabar liquidity shock; the reversal
premium it proxies is earned by the resting limit order that *created* the
wick, not by buying the next open — which is why every mechanical next-bar
test fails. A doji is a low-range bar: volatility information, not direction.

**One line.** Every rigorous US, Japanese and intraday test finds candlestick
patterns worthless after costs; the positive papers test different objects
(3-bar patterns, touch-based "success", pre-2008 Taiwan and China). Code one,
apply real costs, watch it go to zero, and keep candles as a compact way to see
what a bar did. `features.rejection` exists so you can do exactly that.

- Marshall, Young & Rose 2006, *J. Banking & Finance* (verified; DJIA, no value)
- Marshall, Young & Cahan 2008 (verified; Japan, 30 years, none); Duvinage, Mazza & Petitjean 2013, *Quantitative Finance* (verified; 5-min DJIA, none after costs)
- Fock, Klein & Zwergel 2005, *J. Derivatives* (verified; intraday DAX/Bund, none); Horton 2009 (verified)
- Lu, Chen & Hsu 2015, *J. Banking & Finance* (verified; result flips with exit rule)
- Lu, Shiu & Liu 2012; Zhu, Atri & Yegen 2016 (verified; emerging-market, pre-2008, not transferable)

### 12 · Market Profile / auction theory — (a)

**One line.** A good way to draw where the market has traded and nothing more:
zero peer-reviewed tests of value-area reversion or POC targets exist, the
"2.3:1 at value-area extremes" figures are unsourced marketing, and the
balance/imbalance story explains every outcome after it happens. POC and
high-volume nodes inherit the level mechanism in §5. `features.volume_profile`
computes it so you can write a rule down precisely enough for the pipeline to
reject it.

- Steidlmayer & Koy 1986, practitioner book (unverified; contains no test)
- Kavajecz & Odders-White 2004; Osler 2003 (verified; the level mechanism)
- Researcher's search of finance journals for "market profile", "value area", "point of control": no empirical test found

### 13 · "Rejection candles" and ICT rejection blocks — unfalsifiable

**One line.** "Rejection" is defined after the fact by whichever level you drew.
Fix the level rule in advance and you are testing a pin bar at support: expect
a measurable but sub-spread bounce frequency. Rejection blocks specifically —
the story about resting orders at wick midpoints — have **zero** evidence, and
no order-book data supports it.

- Osler 2000/2003 (verified; only the level matters); Marshall, Young & Rose 2006 (verified; wick patterns null)
- Researcher's search of arXiv/SSRN/journal indexes for "rejection block": nothing found

### 14 · ICT / Smart Money Concepts — unfalsifiable, and the one mechanism points the other way

**Mechanism.** Stops cluster beyond salient highs/lows and trigger
self-reinforcing bursts lasting *hours*. Institutions work orders over days via
VWAP/TWAP and dark pools; unfilled limit orders are cancelled, not left at "the
last opposing candle". A 3-candle non-overlap is an intrabar artifact of
positive volatility.

**One line.** No peer-reviewed, preprint or thesis-level test of any ICT
construct exists; the public definitions let you pick the block or sweep after
seeing the outcome; the "70–85% fill rate" for fair value gaps is what a random
walk produces at any unstated horizon; and the one real mechanism (stop
clustering) points toward **breakout continuation rather than fading the
sweep**. Nothing here should be traded.

- Osler 2003/2005 (verified; cascades continue for hours)
- Caporale & Plastun 2017; Plastun, Sibande, Gupta & Wohar 2020 (verified; true session gaps *continue*, they do not fill)
- Community backtests ("2,600 trades", "70–85% FVG fill"): no costs, no significance tests, discretionary selection — not evidence

### 15 · Discretionary confluence and grid-searched parameters — no evidence either way, ~97% base rate

**Mechanism.** None new. An AND-gate over smoothed transforms of the same
closes shrinks the trade sample and raises win-rate noise; P(all agree | trend)
≈ P(one agrees | trend). **Abnormal volume is the one genuinely separate
witness.** The maximum of N noisy backtests is biased upward by roughly
√(2 ln N), which for a few hundred trades exceeds any plausible true edge.

**One line.** Five indicators agreeing is one witness wearing five hats. The
grid search that found your favourite parameters was expected to find
something. The documented outcome for people who trade this way persistently is
that roughly 97% lose money after fees — so if you want to know whether your
*reading* has value, log every trade and compare it to the mechanical version.

- Novy-Marx 2015, NBER WP 21329 (verified); Bailey, Borwein, López de Prado & Zhu 2014, *Notices of the AMS* (verified; Deflated Sharpe)
- White 2000, *Econometrica*; Sullivan, Timmermann & White 1999 (verified; Reality Check)
- Harvey, Liu & Zhu 2016, *Rev. Financial Studies* (verified; t > 3 hurdle — contested by Jensen, Kelly & Pedersen 2023, unverified this run)
- **Chague, De-Losso & Giovannetti 2020**, FGV working paper (verified; 97% of persistent Brazilian day traders lose)
- Barber, Lee, Liu, Odean & Zhang 2020; Barber, Lee, Liu & Odean 2014 (verified; Taiwan, <1% reliably profitable)
- Lee & Swaminathan 2000; Gervais, Kaniel & Mingelgrin 2001, *J. Finance* (volume as a second witness; unverified this run)

---

## What to build first, in order

The pipeline already has the bars, the gate, the no-look-ahead replay, and the
features. This is what to point it at.

1. **Intraday momentum on SPY minute bars.** Sign of the first-30-minute (or
   open-to-15:30) return → hold the last 30 minutes. 1–3 bp round-trip cost.
   Reproduce 1998–2020 first, **then 2021–2026 as an untouched holdout.** It is
   the only (c)-grade result, it lives in your exact data, and the open question
   — did it decay after publication? — is one this pipeline can answer. Needs
   Alpaca minute bars (`fetch.py --source alpaca --timeframe 1m`).
2. **Slow trend filter on 30+ years of SPY.** 200-day / 10-month SMA, with a
   cash yield when out. Measure drawdown, Sharpe and mean return versus
   buy-and-hold, then count how few independent signals a 10-year window
   contains. Cheapest way to learn that "edge" can mean risk reduction rather
   than higher return.
3. **The defensible confluence.** Equal-weight or PCA combination of
   pre-specified trend and volume signals on daily ETF data, weights frozen
   before a holdout, every combination tried logged, Deflated Sharpe applied.
   Then run the same signals as an AND-gate and watch the trade count collapse
   without a rise in per-trade edge.
4. **Null-result exercises with a shuffled-bars baseline** — these are what the
   stack is built from, they are cheap, and seeing them fail against a proper
   baseline is the financial-literacy lesson: hammer/engulfing/doji with a
   prior-trend filter and 2–10 bp costs; fair-value-gap fill rate on real vs
   block-shuffled bars; pin bar at pre-registered round numbers; RSI<30 versus
   a plain "fell N% in K days" rule split by turnover and VIX; "close near max
   pain on expiry" on free chains.
5. **VWAP mean-reversion with honest slippage** (expect failure), and the
   variance risk premium (VIX² minus 20-day realized variance) as a monthly
   sizing input in a daily-bar backtest.
6. **If you insist on discretionary confluence:** a complete, timestamped log of
   *every* trade, benchmarked against a mechanical twin of the same setup,
   several hundred trades minimum. It is the only falsification test for
   "feel", and the population evidence says the expected result is negative.

## What needs data you would have to pay for

| for | data | cost |
|---|---|---|
| order flow, delta, CVD, footprint | tick-by-tick with aggressor side (Databento, Rithmic, Sierra Chart) | tens to low hundreds USD/mo |
| L2, queue imbalance, absorption, icebergs | market-by-order depth (Nasdaq TotalView, CME MBO) | live: tens–hundreds/mo; historical: expensive, GB/day, needs queue simulation this pipeline cannot do |
| GEX, max pain, 0DTE gamma by strike | full options chain with OI and greeks (ThetaData ~$25/mo; Polygon ~$29/mo delayed) | and the dealer side is still an assumption |
| the informed put/call signal | Cboe open/close by account type | institutional pricing |
| retail order imbalance | NYSE TAQ or Nasdaq RTAT; Robintrack ended Aug 2020 | thousands/yr |
| social sentiment | Twitter/X API; Pushshift is largely gone | $100+/mo, no free firehose |
| news tone where it pays | Dow Jones / Bloomberg / RavenPack | thousands/mo |

**Free and sufficient:** minute bars with true traded volume (Alpaca IEX feed);
daily bars (Stooq); VIX, VIX3M and VIX futures settlements from Cboe/FRED;
AAII; Google Trends; Vilkov's 0DTE replication data on GitHub; the
Loughran-McDonald dictionary; EDGAR 8-K text.

---

## Where this document is weakest

- **Every citation a skeptic introduced is unverified this run** — their search
  budgets were exhausted against blocked scholarly hosts. Those cites were used
  to scope or reframe verdicts, never to upgrade a method to "edge". The one new
  fact a skeptic verified directly — Vilkov's Aug 2026 correction that no 0DTE
  structure survives real costs — was decisive for that verdict.
- **Specific numbers not relied on** because a skeptic could not verify them:
  Baltussen's 6.52%/7.96% after-cost figures; Barber et al.'s 23.9 / 37.9
  bp/day; Beckmeyer's dollar losses; López-Lira & Tang's "90% hit rate". The
  *direction* of every one of these results was consistent across all passes.
- **Cost assumptions matter.** A legacy 0.2–0.5% round-trip cost manufactures
  "no edge" by construction for a 2026 retail trader in liquid names, where
  2–10 bp is realistic. Use measured spreads. In liquid large caps the honest
  failure mode is a gross signal near zero; in illiquid names it is
  spread-dominated costs. Neither rescues any pattern.
- **The 97% base rate** (Chague et al. 2020, Brazil; Barber et al., Taiwan) is
  a prior on persistent retail day trading generally, not evidence against any
  specific method. It is used that way here.
- **Disagreements resolved by splitting, not averaging:** intraday momentum was
  split into the published rule (c) versus the opening-range-breakout as
  practised (untested); VWAP into session VWAP as a level (a) versus long-window
  anchored VWAP as a monthly cross-sectional effect (b); liquidity sweeps kept
  the real stop-clustering mechanism with the direction corrected to
  continuation.
- One arXiv preprint and one vendor backtest were dropped as load-bearing: the
  preprint was never read and used unrealistic friction; the vendor sweep was
  in-sample.

---

## First real data — SPY, 2026-09-02, and what three reviewers corrected

Daniel ran the pipeline on SPY from Alpaca's free IEX feed: 669 daily bars
(2024-01 → 2026-09) and 584,845 minute bars (2020-07 → 2026-09). The numbers
were then put in front of three adversarial reviewers — statistics, data and
market structure, implementation — who agreed on every verdict and corrected
the reading in five places and the tools in four. Both sets of corrections are
recorded here because the corrections *are* the finding.

### The verdicts, as corrected

**Intraday momentum (method #1) is a powered null.** Gross mean **−0.5 ± 0.67
bp per session**, 95% CI [−1.8, +0.8], n = 1,513. The published effect of
roughly +2.7 bp/session is *excluded* at about four standard errors — not
merely unconfirmed. The t of −3.79 the tool first printed was the 2 bp cost
being reliably subtracted; "every year negative" was the cost restated seven
times, and gross by year is noise within ±2.5 bp of zero. Two caveats the data
cannot resolve: IEX has no closing cross for SPY, so the exit is the last IEX
print before 16:00 and the closing-auction leg the papers include is
unobserved; and the pre-2021 slice is 109 sessions of late 2020, not the
papers' sample. Real SPY round-trip cost is nearer 0.5 bp than 2, which makes
the net less negative and the gross exactly as zero. **Do not trade it.**

**The trend filter's "39 points of lost return" was mostly warm-up.** The rule
is flat for its first 200 bars by construction, and the tool scored it from
bar 2 against buy-and-hold from bar 2 — while SPY rose ~20%. Over the bars it
could act on, the shortfall is on the order of 12 points. The drawdown halving
(−10.3% vs about −19% in April 2025) is real and is one episode. Its Sharpe did
not beat holding SPY. Fixed: strategies declare their warm-up; `replay` and
`combine` score from there.

**The null test's p-values were not p-values.** The v1 baseline shuffled bars
in blocks of 20 with a one-bar horizon, so bar *i* and bar *i+1* stayed in the
same block 19 times in 20 and the pattern→next-bar pair the shuffle claimed to
destroy was preserved for 84–96% of candle events. Every p in that table was
anchored on the real events. The t column was always the honest number:
`rsi_oversold` t = 0.65 (n = 9), `fell_5pct` t = 0.60 (n = 16), per-event
standard deviations of 3–4% — dip-buying rules firing on the wildest days in a
two-V bull market, with one ~+10% day (2025-04-09) likely inside both means.
`hammer` is a separate, ordinary-variance case: one-sided p ≈ 0.06 alone, ≈
0.37 after eight rules. Fixed: v2 keeps the real events and draws comparison
days matched on trailing volatility; events and the largest event's share are
printed; `pin_at_round` was tightened (v1 qualified one price in five).

**Combine: every line trailed buy-and-hold in both windows.** Implied
buy-and-hold was ~30% in-sample and ~25% in the holdout; `sma_cross` (18.5% /
16.5%) and `vwap_reclaim` (15.6% / 8.2%) trailed in both, and the AND-gate was
worst. Holdout Sharpes over 15 months carry a standard error of ~1.2: the table
reports noise to two decimals. The deflated Sharpe of 0.43 means the best
in-sample per-bar Sharpe (0.080) sat *below* the expected best of eight
nothings (0.089). The four signals are four long-only expressions of one bet
— long SPY after it has risen — so averaging diversifies implementation noise,
never the bet. The 2025-06 → 2026-09 window remains a valid single test of the
pre-registered set (answer: no alpha versus buy-and-hold); it can never be used
to select among those signals or to test anything designed after 2026-09-02.

### What the data cannot show, stated once

Nearly all of SPY's 2024–26 return was overnight: the unconditional
open-to-close mean was +1.5 bp gross against ~8 bp/day close-to-close, so the
null test's next-open-to-close hold is not comparable to the close-to-close
pattern literature. The 669-bar daily sample has no bear market in it. The
minute bars from 2020-07 do — the 2022 decline — and `aggregate.py` now turns
them into daily sessions so the daily tools can see it.

### Base rate, restated

Nothing tested is tradeable. The one method with a published edge is excluded
on six years of the exact instrument and bar size it was published on; the
patterns and indicators behave as the literature says; the trend filter cuts
drawdown at the cost of return. This is what a correct pipeline was expected
to find, and it found it on the first real run.
