# Competitors — who else does what this pipeline does, and what that says about it

*A research pass on 2026-09-04 by an agent with web search; reviewed and kept as
written, with its UNVERIFIED flags intact. Vendor sites for QuantConnect, Nautilus,
Jesse, Composer, Trade Ideas, Tickeron, FINRA, SEC and SSRN are blocked from the
cloud container, so those rows rest on GitHub mirrors and search snippets and say
so. Re-check any price before repeating it.*

**The read, in one paragraph.** Ten frameworks and eight retail products; none
ships a permutation null, a deflated Sharpe or a trial counter, and the one
vendor that sells those three charges £100 a month per seat to institutions.
Every optimiser they ship manufactures the in-sample result the witnesses in
section (c) say does not survive. Across three countries and three decades
roughly one to three percent of persistent retail traders are profitable after
costs, and no track-record platform publishes the share of its strategies that
beat buy-and-hold. So the market for "your strategy is null" is real, small and
institutional; the retail market pays $178 a month for a win rate. That is why
the money plan keeps this as coursework and credibility, not a product — and why
the five features in (f) are worth copying anyway: they make the nulls harder
to argue with.

**Acted on the same day:** (f) item 1, the indicator-level look-ahead diff, is
now `replay.leak_check` and runs inside every backtest. Items 2–5 are parked in
the README's next-steps list.

---

## (a) Open-source frameworks

| Project | What / licence / language | Stars | Backtest model | Look-ahead protection | Fill model | Live brokers | Data-integrity checks | Statistical honesty | Price |
|---|---|---|---|---|---|---|---|---|---|
| **NautilusTrader** | Rust-core event-driven engine, Python API. LGPL-3.0 | 28.4k | Event-driven, nanosecond ticks/bars; same code backtest→live | Deterministic event replay; no explicit look-ahead guard found in README | `FillModel(prob_fill_on_limit, prob_fill_on_stop, prob_slippage)`, `LatencyModel`, fee models, `bar_execution` flag (snippet) | IB, Binance, Bybit, Coinbase, Kraken, OKX, dYdX, Hyperliquid, Polymarket, Betfair, Databento data | None found for calendars/gaps (UNVERIFIED) | None found | Free |
| **Freqtrade** | Crypto bot. GPL-3.0, Python, pushed 2026-09-04 | 54.0k | Event-driven candle loop | **`lookahead-analysis`** re-runs sliced backtests and diffs indicator/entry columns; **`recursive-analysis`** checks startup-candle sensitivity | Entry at candle open, exits at next open; stoploss "exactly at stoploss price"; ROI vs candle high; **no slippage**; docs say backtest "will never replace dry-run" | Binance, Bybit, Kraken, OKX, Gate, Hyperliquid etc. via CCXT | Fills missing candles with flat "empty" candles (prev close, zero volume) and warns "data gaps"; no exchange-calendar concept (24/7 crypto) | Hyperopt (a parameter search, i.e. the overfitting engine) + the two bias tools above; no permutation/DSR/multiple-testing | Free |
| **VectorBT** (OSS) | Vectorised NumPy/Numba. "Fair Code": Apache-2.0 + Commons Clause | 9.0k | Vectorised | None structural; user must shift signals | Vectorised order sim | None (research only) | None found | README claims "walk-forward optimization" | Free |
| **VectorBT PRO** | Closed-source successor | n/a | Vectorised + Rust engine | UNVERIFIED | UNVERIFIED | None | UNVERIFIED | Walk-forward, CV splitters (snippet) | ~$20–25/mo, lifetime from ~$500 (ko-fi shop + snippets; exact tiers UNVERIFIED) |
| **Backtrader** | Classic Python OO engine. GPL-3.0 | 23.1k | Event-driven | Cheat-on-close off by default | Next-bar open; commission schemes | IB (IbPy), Oanda v20, Visual Chart | None | None | Free. Last push 2024-08-19: effectively unmaintained |
| **backtesting.py** | Minimal Python engine. AGPL-3.0, updated 2026-07 | 8.9k | Event loop over pandas | Market orders fill "on next bar's open" unless `trade_on_close=True`; backtest starts after indicator warm-up | Next open; commission | None | None | `optimize()` grid/SAMBO + heatmap; docstring says nothing about overfitting or walk-forward | Free |
| **QuantConnect LEAN** | C#/Python engine + cloud. Apache-2.0 | 21.5k | Event-driven, multi-asset | Fill model refuses stale data ("wait for fresh prices"), checks exchange open | `EquityFillModel`: bid/ask best-effort + slippage model | IB, Schwab, Tradier, Alpaca, TradeStation, Tastytrade, Binance, Bybit, Kraken, Coinbase (snippet) | Cloud data curated; local LEAN inherits whatever you feed it | None built in; cloud "optimization" is a grid search | LEAN free; cloud Researcher ~$60/mo, Quant Trader ~$120/mo, live nodes $24–1,000/mo (third-party reviews; official page blocked) |
| **Zipline-reloaded** | Quantopian's engine kept alive. Apache-2.0, Python ≥3.9 | 1.9k | Event-driven daily/minute | Pipeline API is inherently point-in-time | Volume-share slippage models | None (Quantopian's live layer is gone) | Uses `exchange_calendars` ≥4.2 — the one framework with a real calendar built in | None | Free |
| **Jesse** | Crypto framework. MIT core | 8.4k | Event-driven, multi-timeframe; README claims "without look-ahead bias" | UNVERIFIED beyond claim | UNVERIFIED | Binance, Bybit etc.; Alpaca/IB "on roadmap" 2026-08 (snippet) | None found | README lists "Monte Carlo analysis and rule significance testing" (UNVERIFIED what test) | Live-trade plugin is paid: **$899 / $999 / $1,599 one-time** by IP and route count (snippet) |
| **Hummingbot** | Crypto market-making. Apache-2.0 | 19.8k | V2 "controllers" can be backtested; mostly paper against live feed | None | Live paper vs Binance data | 40+ CEX/DEX connectors | None | None | Free |
| **Vibe-Trading** (HKUDS, 2026 entrant) | LLM "personal trading agent". MIT, Python+React; created 2026-04-01 | **32.4k** | Event-driven; warm-up separated from evaluation; positions vs target_positions split | Execution-time price bands rather than decision-bar | UNVERIFIED | Alpaca, IB, OKX, Binance, Futu, Tiger, eToro, MT5 (13+) | None found | `quantlib` has purged CV among 249 functions | Free |

Also seen: `nmj94/momentum-lab` (101 stars, 2026-08): "1.6M+ parameter combinations" per ticker — the exact thing DSR was invented to punish.

**Reading.** Only Freqtrade's `lookahead-analysis` (detects leakage by re-running) and our cursor (prevents it by construction) are anti-look-ahead *tooling* rather than convention. Only Zipline ships an exchange calendar. None of the ten ships a permutation null, a deflated Sharpe, or a trial counter; every optimiser they ship (hyperopt, SAMBO, LEAN, VectorBT sweeps) manufactures the in-sample results the rest of this document says do not survive.

## (b) Retail / no-code products

| Product | Price (2026) | Promise | Evidence they publish |
|---|---|---|---|
| **Composer (SoFi)** | Trading Pass $40/mo or $384/yr; build/backtest free (snippet) | No-code "symphonies", backtest, auto-trade | Backtests on **daily adjusted closes**, estimated regulatory fees + slippage; disclaimer "past performance of any strategy, backtested or live, is not indicative". Third-party 30-day tests report live lagging backtest by 3–15 pp annualised (UNVERIFIED, blog samples) |
| **Trade Ideas / Holly AI** | Basic $89/mo annual ($127 monthly); Premium with Holly $178/mo annual (vendor snippet) | Holly "runs millions of backtests each night across 70+ strategies", deploys top performers next day | Vendor's own backtested win rates; reviewers note "not independently audited live-trading results" |
| **TrendSpider** | ~$54–349/mo; paid trial $19–49 (third-party) | Strategy Tester → Strategy Bots (alerts or order routing) | None found beyond in-app backtest |
| **Capitalise.ai** | Free via partner brokers (IBKR, Eightcap) | Natural-language rules → automated execution | None found |
| **3Commas** | Free tier (no real trading); Pro $29/mo, Expert $49/mo, up to ~$200/mo | Crypto DCA/grid bots | Marketing cites "18.7% annualized across verified users" (blog claim, UNVERIFIED) |
| **Tickeron** | From ~$30–60/mo | Vendor headlines: "up to 279% annualized", "112% returns", "5,995% annualized" (their own article titles) | Self-reported; no audit found |
| **Alpaca** | Free IEX-only data + free paper trading; Algo Trader Plus $99/mo for SIP + 10k rpm (docs snippet) | Broker API, not a strategy vendor | Promises nothing about returns — which is why it is our broker |
| **Darwinex Zero** | ~€38/mo to trade virtual capital and build a "DARWIN" track record; 15% profit split (third-party) | Verified track record → allocation | Their own investable-attribute scoring; risk warning "56% of retail investor accounts lose money" |

## (c) Witnesses: what verified evidence says about retail algo/day trading

- **Chague, De Losso & Giovannetti 2020**, Brazilian equity-futures day traders 2013–15 (SSRN 3423101): of those persisting **>300 days, 97% lost money**; 1.1% earned above minimum wage; 0.5% above a bank-teller's starting salary; "no evidence of learning". (SSRN snippet + QuantPedia summary.)
- **Barber, Lee, Liu & Odean**, Taiwan 1992–2006, ~450k day traders (*Rev. Asset Pricing Studies* 2020): **less than 1%** earn positive abnormal returns net of fees predictably; past Sharpe is the best predictor of future profit.
- **Barber & Odean 2000** (*J. Finance*): 66,465 US households 1991–96; most active quintile earned 11.4% vs market 17.9%, i.e. **−6.5%/yr**.
- **ESMA** CFD interventions: national regulators found **74–89% of retail CFD accounts lose money**; since 2018 every EU/UK CFD broker must print its own loss percentage (Darwinex's is 56%).
- **Myfxbook**: no official statistic exists. A Medium summary claims 89–92% of 100k+ accounts unprofitable and "funds lost ≈ 3.7× funds won" — **UNVERIFIED**, and survivorship-biased in the opposite direction (losing accounts get deleted).
- **Collective2**: 609 "scored" strategies in its evaluation universe; **no published survival or beat-buy-and-hold statistic found** (its forum thread "Are there any C2 strategies that stay profitable?" was unreachable). The share of verified public strategies beating buy-and-hold is **unknown — nobody publishes it**, which is itself the finding.
- **Liu 2026, arXiv 2604.18821** (1,726 commercially distributed structured strategies, ten institutions): marketed backtests "have only limited portability into the live period"; after peer-benchmark adjustment median strategies underperform ~0.8 pp/yr, widening to ~3.0 pp vs external benchmarks, **59% negative relative return**; backtests "predominantly reflect the common factor regime present before launch". Institutional product, but the mechanism is the one we test for.
- **Deep, Deep & Lamptey 2025, arXiv 2512.12924**: pre-specified hypotheses, 34 walk-forward windows, 100 US equities 2015–24, realistic costs → **0.55%/yr, Sharpe 0.33**. The rigorous version of "microstructure signals" earns almost nothing; the contribution is the protocol.
- **Copy trading** (Apesteguia, Oechssler & Weidenholzer, *Management Science*): the copy option "leads to excessive risk taking"; eToro followers overreact to leaders' risk. Studies claiming positive copy-portfolio alphas (21 of 28) are small samples, UNVERIFIED here.
- **Regulators**: SEC/NASAA/FINRA joint alert on AI investment fraud, **2024-01-25**; FINRA "Know the Risks of Auto-Trading Services Offered by Unregistered Entities", **2025-08**; FCA warning on "Ai Trader Bot", **2025-06-06**; BaFin warning on "best AI trading bots" platforms, 2025-05-30. A press claim that "retail bot users lose 77× more per user than humans" (UC Berkeley/AnChain.ai, via ventureburn) is **UNVERIFIED** and appears to concern crypto/prediction-market bots.

Net: across three countries and three decades, ~1–3% of persistent retail traders are profitable after costs; the one large study of marketed backtests finds most of their information disappears live; no track-record platform publishes a beat-buy-and-hold rate.

## (d) Who sells rigor rather than edge

| Tool | What | Price / licence | Reach |
|---|---|---|---|
| **mlfinlab** (Hudson & Thames) | López de Prado toolkit: CPCV, PBO, DSR, bet sizing | **£100 + VAT/user/month** (QuantConnect docs snippet); repo frozen 2023-10, licence "Other" | 4.9k stars — the proof a rigor product can charge |
| **skfolio** | sklearn-style portfolio lib with `CombinatorialPurgedCV`, walk-forward | BSD-3, free; pushed 2026-09-03 | 2.3k stars |
| **quantstats** | Tearsheets; includes probabilistic Sharpe, Monte Carlo | Apache-2.0, free | 7.6k stars |
| **pypbo** | Probability of Backtest Overfitting (CSCV) | AGPL-3.0 | 140 stars, still pushed 2026-07 |
| **purgedcv** (eslazarev) | Purged/embargo CV + **deflated Sharpe**; created 2026-05 | MIT | 31 stars |
| **AuditZK** "Is your backtest overfit?" | Web PBO calculator | UNVERIFIED | — |
| Pre-registration | No registry for trading strategies exists; nearest is the arXiv 2512.12924 protocol and "predefine your hypothesis" advice in broker education pages | — | — |

Market size: one company charges £1,200/yr per seat for it; everything else is free and under 10k stars. Rigor sells to institutions, not to the retail buyer who pays $178/mo for Holly's win rate.

## (e) SWOT of our pipeline

**Strengths**
- Look-ahead is prevented by shape (cursor raises), not detected afterwards (Freqtrade) or left to convention (backtesting.py, backtrader, VectorBT). No other project here refuses the future structurally.
- Calendar-checked session counts against real NYSE holidays: only Zipline-reloaded has a calendar at all, and it does not block a backtest on a short series; we do.
- Volatility-matched permutation null, deflated Sharpe with a ledger-counted trial number, and a pre-registered holdout — nothing in the framework table ships any of the three; the only vendor of them charges £100/month.
- The gate + append-only ledger + red-rendered `--force` is unique. LEAN's cloud enforces nothing between backtest and live; Composer sells the skip.
- Stdlib-only, zero cost, and three honest nulls already on record — a credibility asset no vendor has (Tickeron's headline is 279%).

**Weaknesses**
- One symbol, one timeframe, one flat cost model; no partial fills, no slippage distribution (NautilusTrader's `FillModel`, LEAN's slippage models), no portfolio.
- Data supply is fragile: Stooq behind a bot-check, Alpaca IEX pre-2020 daily "full of holes", Yahoo keyless. Every framework above lets the user plug in paid feeds; we cannot afford them.
- No community, no docs site, 376 tests vs 13k commits (LEAN); anonymous brand.
- Freqtrade's `lookahead-analysis` catches *indicator* leakage (e.g. a centred moving average); our cursor stops slice leakage but a strategy can still compute a leaking feature over the visible window.

**Opportunities**
- The 2026 entrants (Vibe-Trading 32k stars in five months, momentum-lab's 1.6M combinations) are LLM agents that generate strategies at scale; none has a null test. A stdlib `nulltest`/DSR module that scores *their* output is a bolt-on nobody else offers.
- Nobody publishes "share of verified public strategies that beat buy-and-hold". Publishing our own ledger — nulls included — is a category of its own.
- arXiv 2512.12924 shows the pre-registration protocol is publishable; FIN 200 plus a written pre-registration is a paper, not a product.

**Threats**
- Freqtrade could add DSR in a weekend; NautilusTrader is funded and bi-weekly.
- Retail demand runs the other way: the money is in $178/mo win-rate dashboards, not in "your strategy is null".
- Data access is the choke point and is getting worse (Stooq 2026-09-02).
- To an outsider "null" looks like "couldn't find anything"; reputation rests on the intraday replication being visibly correct.

## (f) What we could copy — five features

1. **Indicator-level look-ahead diff** (Freqtrade `lookahead-analysis`). Re-run each strategy on a truncated series and assert its last-bar signal equals the full-series signal at that bar. Closes the leaking-feature gap the cursor leaves. Effort: ~1 day, pure stdlib, test-pinned.
2. **Startup-sensitivity check** (Freqtrade `recursive-analysis`). Vary warm-up length and report indicator drift at the scoring start. Complements our warm-up scoring rule. Effort: half a day.
3. **Probabilistic fill/slippage model** (NautilusTrader `FillModel`, LEAN slippage). A seeded `prob_slippage` of one tick per fill beside the flat bps — report both. Makes the "not modelled" string smaller without pretending to know the book. Effort: 1–2 days.
4. **Stale-data refusal at fill time** (LEAN `EquityFillModel`). Live/paper mode already has a staleness check in barqc; move it to the order path so `broker.py` refuses a fill request when the last bar is older than one resolution. Effort: half a day.
5. **Probability of Backtest Overfitting via CSCV** (pypbo / mlfinlab). We already count trials for DSR; CSCV over the `combine.py` grid gives the López de Prado number that mlfinlab charges for. Effort: 2–3 days with only stdlib combinatorics; needs ≥16 trial paths to mean anything.

## (g) What not to copy

- **Hyperopt / SAMBO / grid optimisers** (Freqtrade, backtesting.py, LEAN, VectorBT). They manufacture the in-sample Sharpe that Liu 2026 and DSR exist to deflate; we already have the honest version (parameter neighbours in the inspector).
- **Multi-exchange/crypto connectors** (Hummingbot's 40+, Nautilus's 20+). Our evidence is on SPY minute bars; each connector is untested maintenance surface.
- **LLM strategy generation** (Vibe-Trading). Multiplies the trial count; add the null, not the generator.
- **Nanosecond order-book simulation** (NautilusTrader). Needs tick/L2 data we cannot afford; a simulated book on OHLCV is precision without accuracy.
- **Dashboards and win-rate tiles** (Trade Ideas, Tickeron). A win rate without a null is the product we are the antidote to.
- **Paid live-trading plugins** (Jesse's $899). The gate is the feature; charging to bypass it would be Composer.

## Sources (all seen 2026-09-04)

- NautilusTrader: https://github.com/nautechsystems/nautilus_trader ; FillModel/LatencyModel: https://docs.nautilustrader.io/api_reference/backtest.html (snippet)
- Freqtrade: https://github.com/freqtrade/freqtrade ; backtest assumptions https://github.com/freqtrade/freqtrade/blob/develop/docs/backtesting.md ; lookahead https://www.freqtrade.io/en/stable/lookahead-analysis/ ; recursive https://www.freqtrade.io/en/stable/recursive-analysis/ ; data gaps https://www.freqtrade.io/en/stable/faq/ (snippets)
- VectorBT: https://github.com/polakowo/vectorbt ; PRO pricing https://vectorbt.pro/become-a-member/ , https://ko-fi.com/s/88d8ca176c (snippets)
- Backtrader: https://github.com/mementum/backtrader (GitHub API)
- backtesting.py: https://github.com/kernc/backtesting.py ; source https://raw.githubusercontent.com/kernc/backtesting.py/master/backtesting/backtesting.py
- LEAN: https://github.com/QuantConnect/Lean ; fill model https://github.com/QuantConnect/Lean/blob/master/Common/Orders/Fills/EquityFillModel.cs ; pricing (third-party) https://newyorkcityservers.com/blog/quantconnect-review , https://www.newtrading.io/quantconnect-review/
- Zipline-reloaded: https://github.com/stefan-jansen/zipline-reloaded
- Jesse: https://github.com/jesse-ai/jesse ; pricing https://jesse.trade/pricing (snippet); roadmap https://jesse.trade/roadmap (snippet)
- Hummingbot: https://github.com/hummingbot/hummingbot
- Vibe-Trading: https://github.com/HKUDS/Vibe-Trading ; momentum-lab: https://github.com/nmj94/momentum-lab
- Composer: https://help.composer.trade/article/78-slippage-and-fees , https://help.composer.trade/article/67-backtest-basics , https://www.therundown.ai/tools/composer , https://alphagaindaily.com/en/blog/composer-ai-trading-review (snippets)
- Trade Ideas: https://www.trade-ideas.com/pricing/ (snippet); https://www.stockbrokers.com/review/tools/trade-ideas
- TrendSpider: https://www.stockbrokers.com/review/tools/trendspider
- Capitalise.ai: https://support.capitalise.ai/en/articles/2509112-fees-on-capitalise
- 3Commas: https://www.daytrading.com/3commas , https://3commas.io/blog/were-improving-our-subscription-plans
- Tickeron: https://tickeron.com/trading-investing-101/top-10-ai-trading-bots-achieving-up-to-279-annualized-returns/ (title only)
- Alpaca: https://docs.alpaca.markets/us/docs/about-market-data-api , https://docs.alpaca.markets/us/docs/paper-trading (snippets)
- Darwinex: https://www.darwinex.com/ , https://help.darwinex.com/performance-attribute ; Zero pricing https://tradersunion.com/brokers/forex/view/darwinex-zero/fees-and-spread/
- Chague et al.: https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3423101 ; https://quantpedia.com/retail-day-trading-is-an-uphill-battle/
- Barber, Lee, Liu, Odean: https://papers.ssrn.com/sol3/papers.cfm?abstract_id=529063 ; https://ideas.repec.org/a/oup/rasset/v10y2020i1p61-93..html
- Barber & Odean 2000: https://papers.ssrn.com/sol3/papers.cfm?abstract_id=219228
- ESMA: https://www.esma.europa.eu/press-news/esma-news/esma-agrees-prohibit-binary-options-and-restrict-cfds-protect-retail-investors ; https://cms.law/en/int/regulatory-news/esma-fca-measures-on-the-provision-of-contracts-for-differences-and-binary-options-to-retail-investors-in-the-eu
- Myfxbook (UNVERIFIED): https://medium.com/@Forexinsights/myfxbook-profile-statistics-explained-fc52890cca7f
- Collective2: https://trade.collective2.com/performance-metrics-of-trading-strategies.html ; https://forums.collective2.com/t/are-there-any-c2-strategies-that-stay-profitable/16231 (unreachable)
- Liu 2026: https://arxiv.org/abs/2604.18821 ; Deep et al.: https://arxiv.org/abs/2512.12924 (snippets)
- Copy trading: https://pubsonline.informs.org/doi/10.1287/mnsc.2019.3508 ; https://www.sciencedirect.com/science/article/pii/S2214804322000234
- Regulators: https://www.investor.gov/introduction-investing/general-resources/news-alerts/alerts-bulletins/investor-alerts/artificial-intelligence-fraud ; https://www.finra.org/investors/insights/auto-trading-unregistered-entities ; https://www.fca.org.uk/news/warnings/ai-trader-bot ; https://www.bafin.de/SharedDocs/Veroeffentlichungen/EN/Verbrauchermitteilung/unerlaubte/2025/meldung_2025_05_30_Tor_zu_informierten_Handelsentscheidungen_en.html ; "77×" claim https://ventureburn.com/ai-trading-bots-vs-human-traders-in-2026-what-the-data-actually-shows/ (UNVERIFIED)
- Rigor tools: https://github.com/hudson-and-thames/mlfinlab ; pricing https://www.quantconnect.com/docs/v2/drafts/mlfinlab (snippet) ; https://github.com/skfolio/skfolio ; https://github.com/ranaroussi/quantstats ; https://github.com/esvhd/pypbo ; https://github.com/eslazarev/purged-cross-validation ; https://www.auditzk.com/tools/backtest-overfitting
