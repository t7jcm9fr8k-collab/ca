# Market bars pipeline

Eight files that take OHLCV bars from a source to a strategy decision, with a
gate between every stage that has to be earned past. Python 3, stdlib only,
offline — the same posture as `../etsy/`, and the same idiom: tools that report
a **number** rather than a verdict, and refuse rather than guess.

```
bars/             fetched CSVs, one per symbol and timeframe (gitignored)
out/              the ledger and its report (gitignored)
```

| File | Does |
|---|---|
| `bars.py` | `Bar` and `Series` — five exact numbers per period, with provenance the series **refuses to exist without**. Loads CSV. |
| `barqc.py` | nine integrity checks on a series, each with a number. Session count against the real NYSE calendar. |
| `replay.py` | walks bars through a strategy **without letting it see the future** — enforced by shape, not by rule. |
| `strategies.py` | reference strategies, deliberately dull. The contract, not an edge. |
| `ledger.py` | append-only record of backtests, paper runs, live runs and gate bypasses; renders `out/ledger.html`. |
| `run.py` | the gate. `signal → backtest → paper → live`, each refused without the record the last one made. |
| `fetch.py` | Stooq (no key) or Alpaca. **Runs on the Mac.** NETWORK / PARSE / OK kept strictly apart. |
| `broker.py` | Alpaca paper and live orders. **Runs on the Mac, by Daniel's hand.** No agent calls it. |
| `demo.sh` | the whole loop on synthetic bars, refusals included |
| `test_tools.py` | 144 checks. `python3 test_tools.py` |

## Candles or the data?

The question this was built to answer. The answer is: **the data, kept whole.**

A close-only series throws away three numbers per period — where the bar
opened, how high and how low it went. A gap, a long wick, a bar that closed on
its high: none of that survives in a list of closes. `Bar` keeps all five
numbers, exactly, as numbers.

It does **not** draw candlesticks and feed them to a vision model. A rendered
chart is the same information made lossy. If candle *shape* ever matters, it is
computed — `Bar.body`, `Bar.upper_wick`, `Bar.lower_wick` are already there —
never read off a picture.

**And the evidence note, so nobody over-promises:** moving from closes to OHLCV
is a real upgrade because everything downstream needs correct data. But
candlestick *patterns* are a separate claim, and the peer-reviewed record is
unkind — Marshall, Young & Rose (2006, *J. Banking & Finance*) found no excess
returns from candlestick rules on DJIA stocks; Horton (2009) found the same.
Better representation is not edge. Build the bar layer for the correctness; do
not expect the candles themselves to be the profitable part.

## The order

```bash
# on the Mac — every market host is unreachable from a cloud session
python3 fetch.py --dry-run                       # prove the failure path first
python3 fetch.py --source stooq --symbol AAPL     # writes bars/AAPL-1d.csv

# anywhere
python3 barqc.py --csv bars/AAPL-1d.csv --symbol AAPL --source stooq
python3 run.py --mode signal   --strategy sma_cross:10,30 --csv bars/AAPL-1d.csv --symbol AAPL
python3 run.py --mode backtest --strategy sma_cross:10,30 --csv bars/AAPL-1d.csv --symbol AAPL --cost-bps 5
python3 ledger.py --report

# on the Mac, with ALPACA_KEY_ID / ALPACA_SECRET_KEY exported, by hand
python3 run.py --mode paper --strategy sma_cross:10,30 --csv bars/AAPL-1d.csv --symbol AAPL --qty 10
python3 run.py --mode live  --strategy sma_cross:10,30 --csv bars/AAPL-1d.csv --symbol AAPL --qty 1 --confirm-live
```

## The gate

```
signal  →  backtest recorded  →  paper  →  paper run FILLED  →  live
```

`--mode paper` refuses without a recorded backtest of that strategy on that
symbol. `--mode live` refuses without a backtest **and** a paper run that
actually filled, and needs `--confirm-live` on top — a real-money order should
not be one typo away from a paper one. Exit **3** for a gate refusal.

The escape hatch is deliberately awkward. `--force` skips the record check but
only with `--force-reason`; without one it exits **4** and does nothing. With
one, the bypass is appended to the ledger and rendered in red in the report. A
forced run that looked identical to an earned one would make the ledger lie,
and the ledger's only value is that a live run sitting below a paper run
*proves* the paper run happened.

Run `./demo.sh` to watch all of it, refusals included.

## No look-ahead, by shape

The most common way a backtest lies is a slice that reaches one bar too far.
`replay.py` makes that structurally unavailable rather than something to
remember:

- The strategy never receives the series. It receives a **cursor** exposing only
  the bars that have closed; `cursor[-1]` is always the last closed bar, and an
  integer index past the window **raises** `LookAhead`.
- A decision made after bar *i* closes **fills at bar *i+1*'s open**, never at
  bar *i*'s close. You cannot trade a close you learned about after it printed.
- The benchmark buys at the first open a strategy could possibly have bought at,
  so `buy_and_hold` as a strategy matches it exactly, less cost — pinned by test.

## Three things this pipeline refuses to do

**Hand over an empty series.** `fetch.py` keeps NETWORK failure, PARSE failure
and a genuine result strictly apart — the `rival.py` principle — because an
empty bar series and a flat market are the same array, and the next tool along
would backtest it and report a number. Only OK writes a file. Stooq's literal
`No data` reply is a PARSE failure, never zero bars.

**Backtest bars that failed inspection.** `replay()` runs `barqc.inspect` and
raises `Blocked` on a blocked verdict. The result of a replay on broken data
would have the authority of a measurement and the substance of a guess.

**Place an order on its own.** Every agent here carries the fleet's standing
rule — never publish, post, list, or buy — which reads for this pipeline as
*never trade*. `broker.py` exists so that the paper and live stages are real,
and it runs by Daniel's hand only. Keys come from the environment, never from
arguments, and are never committed.

## The nine checks

| check | blocks? | prevents |
|---|---|---|
| ohlc sanity | **yes** | a corrupt or misparsed row |
| order | **yes** | a bar counted twice, or a series silently reordered |
| sessions | **yes** | *the killer* — a short series that looks complete. Counted against the NYSE calendar, including Good Friday and observed holidays. Daily only; intraday reports UNRUN. |
| calendar | **yes** | a bar on a closed day, which means the dates are shifted |
| provenance | **yes** | a series nobody can trace |
| volume | reported | halts and thin names are real; look, do not assume |
| adjustment | reported | an unadjusted split reads as a −50% crash. Any split-sized gap is named with its date. |
| staleness | reported | irrelevant to a backtest, fatal to a live decision |
| span | reported | under 60 bars is an anecdote |

Up to **2 missing sessions** (or 1%) are tolerated, because special closures —
a day of mourning, weather — are not knowable in advance. The missing dates are
listed either way.

## The agents

Two, in `.claude/agents/`, matching the six shirt-pipeline agents in form.

| Agent | Job | Effort | Network |
|---|---|---|---|
| `bar-wright` | fetch, inspect, write the CSV. Never a zero-bar file. | low | yes — Mac only |
| `strategy-inspector` | the gate: barqc, a costed backtest and its parameter neighbours, the record check for paper and live. | **high** | no |

`strategy-inspector` runs high for the same reason `print-inspector` does: it is
the one whose output is a refusal, and a false pass here costs money after the
fact, on a fill nobody can undo. Both carry the standing constraint **never
place an order**.

## What is not modelled, on purpose

Order book, partial fills, intraday slippage, borrow cost, dividends. A flat
`--cost-bps` per fill (default 5) is the one concession, because a zero-cost
backtest of an active strategy overstates the result by exactly the thing that
kills it. Every backtest record carries the `not_modelled` string so nobody has
to remember.

## Where this sits

Not among the ten income channels in the adversarial research of 2026-08-31,
and not booked against any revenue gate. It exists for the learning, for FIN
200, and as a correct foundation if it ever becomes more than that.
