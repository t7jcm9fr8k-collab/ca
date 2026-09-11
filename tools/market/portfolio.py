#!/usr/bin/env python3
"""
portfolio.py — hold more than one thing at once.

WHY THIS FILE EXISTS
    Every backtest in this repo calls `replay(series, ...)`. One series. That
    shape can express "am I in SPY or in cash" and cannot express "of these
    nine, which three". Twelve strategies and fourteen rules have been run
    through the single-asset engine and all are null but one, which is not
    surprising: single-asset timing of a mega-cap ETF on daily bars with
    published indicators is the most crowded question in the field.

    Cross-sectional questions need a different engine, so here is one. It is
    not a better backtester. It asks a different question.

WHAT IT KEEPS FROM `replay`
    Everything that stops a backtest from lying:
      - the decision sees only closed bars, enforced by a cursor that RAISES;
      - a decision made after bar i closes fills at bar i+1's OPEN;
      - idle cash earns its yield AFTER the fill, so cash deployed at an open
        does not also earn that bar;
      - the benchmark is scored over the same bars from the same open, so the
        comparison is not against a position no strategy could have held;
      - `barqc` gates every input series before a single bar is walked.

WHAT IS DIFFERENT
    A strategy returns a dict of weights, not a scalar. Weights are the
    fraction of equity in each symbol after the next open; they must be
    non-negative and sum to at most 1, and the remainder is cash. Long only,
    because borrow costs are not modelled and pretending otherwise would be
    the kind of quiet lie this pipeline exists to prevent.

    Rebalancing is on a schedule, not every bar. A monthly rule that is
    re-decided daily is a different rule.

USAGE
    from portfolio import load_aligned, replay_portfolio, tsmom, xsmom, equal_weight
"""

import bisect
import datetime as dt

import barqc
import bars as bars_mod
from replay import Blocked, LookAhead, _stats, max_drawdown, BARS_PER_YEAR


# ------------------------------------------------------------------ alignment

def align(serieses):
    """
    Cut every series down to the dates they all share.

    Intersection, never union, and never a forward fill. A missing bar in one
    name is a real hole; carrying the last price across it would invent a
    return of exactly zero on a day the market moved, which flatters any
    strategy that happened to be holding. The count that is dropped is
    reported so the size of the compromise is visible.
    """
    if len(serieses) < 2:
        raise ValueError("a portfolio needs at least two series")
    by_sym = {}
    for s in serieses:
        if s.symbol in by_sym:
            raise ValueError(f"{s.symbol} given twice")
        by_sym[s.symbol] = {b.ts: b for b in s.bars}

    common = None
    for m in by_sym.values():
        common = set(m) if common is None else (common & set(m))
    dates = sorted(common)
    if len(dates) < 3:
        raise Blocked(f"only {len(dates)} shared date(s) across "
                      f"{len(serieses)} series; nothing to walk")

    dropped = {sym: len(m) - len(dates) for sym, m in by_sym.items()}
    aligned = {sym: tuple(m[d] for d in dates) for sym, m in by_sym.items()}
    return dates, aligned, dropped


def month_end_indices(dates):
    """Index of the last shared session in each calendar month."""
    out = []
    for i, d in enumerate(dates):
        if i + 1 == len(dates) or (dates[i + 1].year, dates[i + 1].month) != (d.year, d.month):
            out.append(i)
    return out


# --------------------------------------------------------------------- cursor

class PortfolioCursor:
    """
    The strategy's whole world: for every symbol, the bars that have CLOSED.

    Same contract as `replay.Cursor`, one level up. Asking for a bar that has
    not happened raises `LookAhead` rather than returning something plausible,
    because a cross-sectional rule has nine chances per rebalance to peek and
    a convention nobody enforces is a convention nobody keeps.
    """
    __slots__ = ("_aligned", "_dates", "_n", "symbols", "held")

    def __init__(self, aligned, dates, n, held=None):
        if n < 0 or n > len(dates):
            raise ValueError(f"cursor n={n} outside 0..{len(dates)}")
        self._aligned = aligned
        self._dates = dates
        self._n = n
        self.symbols = tuple(sorted(aligned))
        # What is held right now, as the engine knows it. A strategy that
        # needs to know reads this rather than keeping state between calls —
        # state between calls is invisible to any leak check and dies with
        # the process.
        self.held = dict(held or {})

    def __len__(self):
        return self._n

    @property
    def now(self):
        """The timestamp of the most recently closed bar."""
        if self._n == 0:
            raise LookAhead("no bar has closed yet")
        return self._dates[self._n - 1]

    def bars(self, symbol):
        """Closed bars for one symbol, oldest first."""
        if symbol not in self._aligned:
            raise KeyError(f"{symbol} is not in this portfolio")
        return self._aligned[symbol][:self._n]

    def close(self, symbol, back=0):
        """
        Close `back` bars ago; back=0 is the most recent close.

        A NEGATIVE `back` is a request for a bar that has not happened, and it
        raises. An earlier version guarded only the far end, so `close(s, -1)`
        indexed one past the visible window and returned tomorrow's price with
        no complaint — caught by the check that claims to pin this, which is
        the entire argument for writing the check.
        """
        if back < 0:
            raise LookAhead(
                f"close {back} bar(s) back is a bar that has not closed yet")
        i = self._n - 1 - back
        if i < 0:
            raise LookAhead(
                f"close {back} bar(s) back requested with {self._n} closed")
        return self._aligned[symbol][i].close

    def bars_back_to(self, symbol, when):
        """How many closed bars ago the last close at or before `when` sits."""
        col = self._aligned[symbol]
        lo = bisect.bisect_right(self._dates, when, 0, self._n) - 1
        if lo < 0:
            raise LookAhead(f"no closed bar at or before {when.isoformat()}")
        return self._n - 1 - lo

    def trailing_return(self, symbol, months, skip_months=0):
        """
        Return over `months`, ending `skip_months` before the last close.

        Returns None when the window is not fully inside the closed bars —
        never a partial window silently scored as if it were whole.
        """
        end_back = 0
        if skip_months:
            end_when = _months_before(self.now, skip_months)
            if end_when < self._dates[0]:
                return None
            end_back = self.bars_back_to(symbol, end_when)
        anchor = self._dates[self._n - 1 - end_back]
        start_when = _months_before(anchor, months)
        if start_when < self._dates[0]:
            return None
        start_back = self.bars_back_to(symbol, start_when)
        p0 = self.close(symbol, start_back)
        p1 = self.close(symbol, end_back)
        if p0 <= 0:
            return None
        return p1 / p0 - 1.0


def _months_before(when, months):
    y, m = when.year, when.month - months
    while m <= 0:
        m += 12
        y -= 1
    day = min(when.day, [31, 29 if y % 4 == 0 and (y % 100 or y % 400 == 0) else 28,
                         31, 30, 31, 30, 31, 31, 30, 31, 30, 31][m - 1])
    return when.replace(year=y, month=m, day=day)


# ------------------------------------------------------------------ the walk

def replay_portfolio(serieses, weigh, cost_bps=0.0, warmup=1, cash_yield=0.0,
                     name=None, rebalance="monthly"):
    """
    Walk aligned bars, rebalancing on a schedule.

    `weigh(cursor) -> {symbol: weight}` with weights >= 0 summing to <= 1.
    Whatever is not allocated is cash. Called only on rebalance dates; between
    them the holdings drift with prices, which is what a monthly rule does.
    """
    for s in serieses:
        qc = barqc.inspect(s)
        if qc["verdict"] == "blocked":
            raise Blocked(f"barqc blocked {s.describe()}: "
                          f"{', '.join(qc['failed'])}. Fix the data first.")

    dates, aligned, dropped = align(serieses)
    symbols = tuple(sorted(aligned))
    if rebalance != "monthly":
        raise ValueError("only monthly rebalancing is implemented")
    sched = set(month_end_indices(dates))

    warmup = max(warmup, int(getattr(weigh, "warmup", 0) or 0), 1)
    if len(dates) < warmup + 2:
        raise Blocked(f"{len(dates)} shared date(s) is not enough for one "
                      f"decision and one fill after a warm-up of {warmup}")

    bpy = BARS_PER_YEAR.get(serieses[0].timeframe, 252)
    per_bar_yield = (1.0 + cash_yield) ** (1.0 / bpy) - 1.0 if cash_yield else 0.0

    cash = 1.0
    units = {s: 0.0 for s in symbols}
    equity, equity_ts, fills, weights_log = [], [], [], []
    pending = None

    for i in range(warmup, len(dates)):
        # 1. fill what was decided after the previous close, at THIS open
        if pending is not None:
            opens = {s: aligned[s][i].open for s in symbols}
            eq = cash + sum(units[s] * opens[s] for s in symbols)
            traded = 0.0
            for s in symbols:
                want = pending.get(s, 0.0) * eq / opens[s]
                delta = want - units[s]
                if abs(delta * opens[s]) < 1e-12:
                    continue
                notional = abs(delta * opens[s])
                cost = notional * cost_bps / 1e4
                cash -= delta * opens[s] + cost
                units[s] = want
                traded += notional
            if traded > 0:
                fills.append({"ts": dates[i].isoformat(), "traded": traded,
                              "weights": dict(pending)})
            pending = None

        # 1b. idle cash earns AFTER the fill, so cash deployed here earns nothing
        if per_bar_yield and cash > 0:
            cash *= 1.0 + per_bar_yield

        # 2. mark to market at this close
        equity.append(cash + sum(units[s] * aligned[s][i].close for s in symbols))
        equity_ts.append(dates[i].isoformat())

        # 3. decide, seeing bars 0..i — this bar is closed, the next is not
        if i in sched and i + 1 < len(dates):
            eq_now = equity[-1]
            held = {s: (units[s] * aligned[s][i].close / eq_now if eq_now else 0.0)
                    for s in symbols}
            cur = PortfolioCursor(aligned, dates, i + 1, held=held)
            w = weigh(cur)
            pending = _clean_weights(w, symbols)
            weights_log.append({"ts": dates[i].isoformat(), "weights": dict(pending)})

    rets = [equity[k] / equity[k - 1] - 1.0 for k in range(1, len(equity))]
    years = len(equity) / bpy
    final = equity[-1]

    bench = _equal_weight_benchmark(aligned, dates, symbols, warmup, sched,
                                    cost_bps, bpy)

    return {
        "strategy": name or getattr(weigh, "__name__", "portfolio"),
        "symbols": list(symbols), "timeframe": serieses[0].timeframe,
        "sources": sorted({s.provenance.get("source") for s in serieses}),
        "shared_dates": len(dates), "dropped_per_symbol": dropped,
        "start": dates[0].isoformat(), "end": dates[-1].isoformat(),
        "scored_from": dates[warmup].isoformat(),
        "rebalances": len(weights_log), "fills": len(fills),
        "return": final - 1.0, "cagr": final ** (1.0 / years) - 1.0 if years > 0 and final > 0 else None,
        "max_drawdown": max_drawdown(equity),
        "benchmark": bench["return"], "benchmark_sharpe": bench["sharpe"],
        "benchmark_max_drawdown": bench["max_drawdown"],
        "benchmark_cagr": bench["cagr"],
        "cost_bps": cost_bps, "cash_yield": cash_yield,
        "years": years, "bars_per_year": bpy, "warmup": warmup,
        "live_bars": len(equity),
        **_stats(rets, bpy),
        "not_modelled": "order book, partial fills, intraday slippage, borrow, "
                        "dividends (these files are largely unadjusted), taxes",
        "equity": equity, "equity_ts": equity_ts,
        "bar_returns": rets, "weights_log": weights_log,
        "benchmark_equity": bench["equity"], "benchmark_returns": bench["returns"],
    }


def _clean_weights(w, symbols):
    """Reject anything a long-only book cannot hold, loudly."""
    out = {}
    for s, v in (w or {}).items():
        if s not in symbols:
            raise KeyError(f"weight for {s}, which is not in this portfolio")
        v = float(v)
        if v < -1e-12:
            raise ValueError(f"negative weight {v} for {s}; this engine is long only")
        if v > 1e-12:
            out[s] = v
    total = sum(out.values())
    if total > 1.0 + 1e-9:
        raise ValueError(f"weights sum to {total:.4f}; leverage is not modelled")
    return out


def _equal_weight_benchmark(aligned, dates, symbols, warmup, sched, cost_bps, bpy):
    """
    Equal weight across every symbol, rebalanced on the same schedule.

    This, and not SPY, is what a nine-asset rule has to beat. Comparing a
    diversified book against one index measures diversification and calls it
    skill. It pays the same costs on the same dates for the same reason.
    """
    # Starts flat and buys at the FIRST scheduled rebalance, exactly as the
    # strategy does. An earlier version seeded `pending` before the loop, so
    # the benchmark was invested from the warm-up open while the strategy sat
    # in cash until the first month end — up to a month of free return, handed
    # to the benchmark. That is the same warm-up asymmetry three reviewers
    # caught in the first real run, one level up.
    cash = 1.0
    units = {s: 0.0 for s in symbols}
    eq, pending = [], None
    for i in range(warmup, len(dates)):
        if pending is not None:
            opens = {s: aligned[s][i].open for s in symbols}
            e = cash + sum(units[s] * opens[s] for s in symbols)
            for s in symbols:
                want = pending[s] * e / opens[s]
                delta = want - units[s]
                if abs(delta * opens[s]) < 1e-12:
                    continue
                cash -= delta * opens[s] + abs(delta * opens[s]) * cost_bps / 1e4
                units[s] = want
            pending = None
        eq.append(cash + sum(units[s] * aligned[s][i].close for s in symbols))
        if i in sched and i + 1 < len(dates):
            pending = {s: 1.0 / len(symbols) for s in symbols}
    rets = [eq[k] / eq[k - 1] - 1.0 for k in range(1, len(eq))]
    years = len(eq) / bpy
    st = _stats(rets, bpy)
    return {"return": eq[-1] - 1.0, "equity": eq, "returns": rets,
            "max_drawdown": max_drawdown(eq), "sharpe": st["sharpe"],
            "cagr": eq[-1] ** (1.0 / years) - 1.0 if years > 0 and eq[-1] > 0 else None}


# ---------------------------------------------------------------- strategies
#
# Both are pre-registered in PREREG-2026-09-11-cross-section.md. The parameters
# below are the ones written down BEFORE the data was touched; changing one is
# a new specification and counts as a new trial.

def tsmom(lookback_months=12, warmup_bars=273):
    """
    Time-series momentum, v1 (Moskowitz, Ooi & Pedersen 2012, long-only form).

    At each month end hold every asset whose trailing 12-month return is
    positive, equal weight among those; hold cash for the rest. No shorts, no
    leverage, no volatility scaling.
    """
    def weigh(cur):
        picks = []
        for s in cur.symbols:
            r = cur.trailing_return(s, lookback_months)
            if r is not None and r > 0:
                picks.append(s)
        if not picks:
            return {}
        return {s: 1.0 / len(picks) for s in picks}
    weigh.__name__ = f"tsmom:{lookback_months}"
    weigh.warmup = warmup_bars
    return weigh


def xsmom(rank_months=12, skip_months=1, top=3, warmup_bars=294):
    """
    Cross-sectional momentum, v1 (12-1, long the top third).

    Rank on the return over the twelve months ending one month ago — the skip
    is standard and exists because the most recent month reverses. Hold the
    top three equal weight, always fully invested.
    """
    def weigh(cur):
        scored = []
        for s in cur.symbols:
            r = cur.trailing_return(s, rank_months, skip_months=skip_months)
            if r is not None:
                scored.append((r, s))
        if len(scored) < top:
            return {}
        scored.sort(reverse=True)
        picks = [s for _, s in scored[:top]]
        return {s: 1.0 / top for s in picks}
    weigh.__name__ = f"xsmom:{rank_months},{skip_months},{top}"
    weigh.warmup = warmup_bars
    return weigh


def equal_weight():
    """The benchmark as a strategy, so it can be run through the same path."""
    def weigh(cur):
        return {s: 1.0 / len(cur.symbols) for s in cur.symbols}
    weigh.__name__ = "equal_weight"
    weigh.warmup = 1
    return weigh


def load_aligned(paths, symbols, source, adjusted=None, timeframe="1d"):
    """Load several CSVs as Series, provenance required as everywhere else."""
    if len(paths) != len(symbols):
        raise ValueError("one symbol per path")
    return [bars_mod.load_csv(p, sym, timeframe=timeframe, source=source,
                              adjusted=adjusted)
            for p, sym in zip(paths, symbols)]
