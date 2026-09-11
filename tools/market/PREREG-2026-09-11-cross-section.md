# Pre-registration — the cross-section, two specifications, 2026-09-11

*Written before any cross-sectional quantity was computed. Nothing below may
change after the run; a changed reading rule is a new version and both count.*

## Why this and not another indicator

Every backtest in this repo calls `replay(series, ...)` — one series. Twelve
strategies and fourteen rules have been tested, all of them single-asset timing
on daily bars, and all are null except `rsi_oversold`, which is a documented
reversal premium worth about a point a year at 5% exposure.

Adding a fifteenth rule to that pile is not neutral. `combine.py` already
prices the cost: the deflated Sharpe was 0.43 after eight specifications and
0.61 later. Every further specification on the same data lowers the
credibility of the one survivor. The trial count is a budget being spent, not
a free parameter.

So this tests a different question on data already on disk. Not "what predicts
the next five bars" but "what premium is paid for bearing something, across a
cross-section, after costs". Two specifications. That is the entire budget for
this run; there is no third, and no grid.

## Data, fixed

Nine long files in `bars/`, all `--source stooq --adjusted yes` as recorded:
DIA EEM EFA GLD IWM QQQ TLT XLE XLF. Common window **2005-02-25 → 2026-09-04**
(QQQ's earlier history is discarded so every asset sees the same dates).

**Known defect, stated before the run:** the E-15 refutation established these
long files are largely NOT dividend-adjusted, while SPY's file is total-return.
Both the strategies and the benchmark below read the same nine files, so the
comparison between them is fair; the absolute returns are understated for all
of them, and no number here may be compared to a total-return series.

## Specification 1 — time-series momentum (TSMOM)

At each month end, for each of the nine: compute the trailing 12-month return.
Hold the asset next month if that return is positive, hold nothing in it if
not. Equal weight across whichever assets are held. Cash earns 3% annualised.

Fixed: lookback 12 months, monthly rebalance, long or flat, no shorts, no
leverage, no volatility scaling.

Distinct from `trend_filter:200`, which is a 200-day moving average on one
asset scored alone. This is a different lookback, a different family, and a
portfolio.

## Specification 2 — cross-sectional momentum (XSMOM)

At each month end, rank the nine by return over the twelve months ending one
month ago (the standard 12-1 skip, which exists to avoid the one-month
reversal). Hold the top three, equal weight, for the next month. Cash is not
used; the portfolio is always fully invested in three names.

Fixed: rank window 12 months, skip 1 month, hold top 3 of 9, monthly rebalance,
long only.

This specification cannot be expressed by anything in the repo today. It is the
reason the engine is being extended.

## Costs and mechanics, fixed

- 5 bp per round trip, applied to the traded fraction at each rebalance.
- Decisions use data through month end; fills at the **next** session's open.
  The existing `Cursor` look-ahead guard applies unchanged.
- Warm-up 13 months; scoring starts after it, and the benchmark is scored from
  the same bar.

## Benchmark, fixed

Equal-weight buy-and-hold of all nine, rebalanced monthly, same costs, same
window, same warm-up. **Not SPY.** A nine-asset strategy compared against one
index is a comparison of diversification, not of the rule.

## The reading rule — fixed now, applied without discretion

A specification **works** only if all four hold:

1. Sharpe exceeds the equal-weight benchmark's Sharpe by at least **0.20**.
2. Maximum drawdown is **no worse** than the benchmark's.
3. Permutation null over 1000 draws gives **p < 0.05**.
4. Condition 1 holds **in both halves** of the sample, split at the midpoint
   date, each half scored on its own.

Four of four is "works". Three of four is "partial, not actionable" and
nothing is built on it. Two or fewer is null.

Additionally, the deflated Sharpe — computed with the trial count carried
forward from the ledger via `--count-ledger`, plus these two — must exceed
zero, or the result is reported as indistinguishable from the best of the
search regardless of the four conditions above.

## The null

For TSMOM: permute the month-end signal across dates within each asset, so the
number of months held is preserved and only their placement changes.
For XSMOM: permute the ranking across assets at each month end, so three names
are always held and only which three changes.
1000 draws each, seeded and recorded.

## What will be written either way

The result goes into `EVIDENCE.md` in the same form as every other section:
the tool's verdict lines verbatim, the numbers only as printed in saved files
under `runs/`, and one paragraph reading it against the reading rule above.
If both are null, that is what it will say. No third specification will be
added afterwards to chase a better answer.

## Trial accounting

Trials before this run: as counted by the ledger.
Trials added by this run: **2**. Not 2 families, not 2 with variants — two.
