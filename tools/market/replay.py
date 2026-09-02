#!/usr/bin/env python3
"""
replay.py — run a strategy over bars without letting it see the future.

THE LIE THIS FILE EXISTS TO MAKE IMPOSSIBLE
    Look-ahead bias. A strategy that can see bar i's close while deciding what
    to do at bar i's close will look brilliant and be worthless — it is trading
    a number that did not exist yet. Most backtests that lie, lie this way, and
    they lie without anyone writing a single dishonest line: a slice that reaches
    one element too far is all it takes.

    So this is not enforced by a rule people remember. It is enforced by shape:

    1.  The strategy never receives the Series. It receives a CURSOR that exposes
        only the bars that have CLOSED, and raises LookAhead on any attempt to
        index past them. Negative indices are relative to the visible end, so
        `cursor[-1]` is always the last closed bar and never a future one.

    2.  A decision made after bar i closes FILLS AT BAR i+1's OPEN. Never at bar
        i's close. You cannot trade a close you only learned about after it
        printed. This is the single most common cheat in retail backtests and it
        is structurally unavailable here.

WHAT IT REFUSES
    A series that `barqc.inspect` blocks. You cannot replay broken data; the
    result would be a number with the authority of a measurement and the
    substance of a guess.

WHAT IT DOES NOT MODEL
    Order book, partial fills, intraday slippage, borrow cost, dividends. A flat
    `cost_bps` per fill is the one concession, because a zero-cost backtest of
    an active strategy overstates the result by exactly the thing that kills it.
    Say what you did not model; do not pretend you modelled it.

USAGE (library — run.py is the CLI)
    result = replay(series, strategy, cost_bps=5)
"""

import math

import barqc

# Regular-session bars per year, for annualising. 252 sessions of 6.5 hours.
BARS_PER_YEAR = {"1d": 252, "1h": 252 * 7, "15m": 252 * 26, "5m": 252 * 78,
                 "1m": 252 * 390}


class LookAhead(Exception):
    """A strategy reached for a bar that has not closed yet."""


class Blocked(Exception):
    """barqc blocked the series; nothing was run."""


class Cursor:
    """
    The strategy's whole world: bars[0 : n], where n is how many have closed.

    Slices clamp to the visible window exactly as Python slices clamp to a
    list's end — `cursor[-30:]` on 12 visible bars returns 12, which is what a
    warm-up period wants. Integer indexing past the window RAISES, because a
    strategy that asks for bar 200 when 150 have closed has a bug, not a
    preference.
    """
    __slots__ = ("_bars", "_n", "symbol", "timeframe")

    def __init__(self, series, n):
        if n < 0 or n > len(series.bars):
            raise ValueError(f"cursor n={n} outside 0..{len(series.bars)}")
        self._bars = series.bars
        self._n = n
        self.symbol = series.symbol
        self.timeframe = series.timeframe

    def __len__(self):
        return self._n

    def __getitem__(self, k):
        if isinstance(k, slice):
            start, stop, step = k.indices(self._n)
            return self._bars[start:stop:step]
        if k < 0:
            k += self._n
        if k < 0 or k >= self._n:
            raise LookAhead(
                f"index {k} requested with {self._n} bar(s) closed. "
                f"Bar {k} has not happened yet from where this decision stands.")
        return self._bars[k]

    def __iter__(self):
        return iter(self._bars[:self._n])

    @property
    def last(self):
        if self._n == 0:
            raise LookAhead("no bar has closed yet")
        return self._bars[self._n - 1]

    def closes(self, n=None):
        w = self._bars[:self._n] if n is None else self._bars[max(0, self._n - n):self._n]
        return [b.close for b in w]


def max_drawdown(equity):
    peak, worst = float("-inf"), 0.0
    for e in equity:
        peak = max(peak, e)
        if peak > 0:
            worst = min(worst, e / peak - 1)
    return worst


# Keys a ledger entry must not carry: per-bar series that would make it huge.
LEDGER_EXCLUDE = ("equity", "equity_ts", "targets", "bar_returns", "fill_list")


def _stats(rets, bars_per_year):
    """Mean, dispersion, Sharpe, skew, kurtosis of per-bar returns."""
    n = len(rets)
    if n < 2:
        return {"sharpe_per_bar": 0.0, "sharpe": 0.0, "volatility": 0.0,
                "skew": 0.0, "kurt": 3.0, "returns_used": n}
    m = sum(rets) / n
    var = sum((r - m) ** 2 for r in rets) / (n - 1)
    sd = math.sqrt(var)
    if sd == 0:
        return {"sharpe_per_bar": 0.0, "sharpe": 0.0, "volatility": 0.0,
                "skew": 0.0, "kurt": 3.0, "returns_used": n}
    m3 = sum((r - m) ** 3 for r in rets) / n
    m4 = sum((r - m) ** 4 for r in rets) / n
    pvar = sum((r - m) ** 2 for r in rets) / n
    spb = m / sd
    return {"sharpe_per_bar": spb, "sharpe": spb * math.sqrt(bars_per_year),
            "volatility": sd * math.sqrt(bars_per_year),
            "skew": m3 / pvar ** 1.5 if pvar > 0 else 0.0,
            "kurt": m4 / pvar ** 2 if pvar > 0 else 3.0,
            "returns_used": n}


def replay(series, strategy, cost_bps=0.0, warmup=1, name=None, cash_yield=0.0):
    """
    Walk the bars. Returns a dict of stats plus the equity curve and fills.

    `strategy(cursor) -> target` with target in [-1, 1]: the fraction of equity
    to hold in the asset after the next open. Long-only strategies return 0 or 1.
    Returning the same target as currently held is a no-op and costs nothing.

    `cash_yield` is an annual rate earned on idle cash. A trend filter that
    sits out a bear market is not earning nothing; leaving this at zero
    understates it, so say what you assumed.
    """
    qc = barqc.inspect(series)
    if qc["verdict"] == "blocked":
        raise Blocked(f"barqc blocked {series.describe()}: "
                      f"{', '.join(qc['failed'])}. Fix the data first.")
    bars = series.bars
    # Score from the first bar the strategy could ACT on. A 200-day filter is
    # flat for 200 bars by construction; charging it for those bars against a
    # benchmark that was invested from bar 2 measures the warm-up, not the
    # rule. The first real run did exactly that, and three reviewers caught it.
    warmup = max(warmup, int(getattr(strategy, "warmup", 0) or 0), 1)
    if len(bars) < warmup + 2:
        raise Blocked(f"{len(bars)} bar(s) is not enough to make one decision "
                      f"and one fill after a warm-up of {warmup}")
    bpy = BARS_PER_YEAR.get(series.timeframe, 252)
    per_bar_yield = (1.0 + cash_yield) ** (1.0 / bpy) - 1.0 if cash_yield else 0.0

    cash, units, pos = 1.0, 0.0, 0.0
    equity, equity_ts, targets, fills = [], [], [], []
    pending = None

    for i in range(warmup, len(bars)):
        b = bars[i]
        # 1. fill whatever was decided after the PREVIOUS bar closed, at THIS open
        if pending is not None and abs(pending - pos) > 1e-12:
            price = b.open
            eq_at_fill = cash + units * price
            want_units = pending * eq_at_fill / price
            delta = want_units - units
            cost = abs(delta * price) * cost_bps / 1e4
            cash -= delta * price + cost
            units = want_units
            pos = pending
            fills.append({"ts": b.ts.isoformat(), "price": price,
                          "target": pending, "delta_units": delta, "cost": cost})
        # 1b. whatever cash is still idle through this bar earns the yield —
        #     after the fill, so cash deployed at this open earns nothing here
        if per_bar_yield and cash > 0:
            cash *= 1.0 + per_bar_yield
        # 2. mark to market at this close
        equity.append(cash + units * b.close)
        equity_ts.append(b.ts.isoformat())
        # 3. decide, seeing bars 0..i — this bar is closed, the next is not
        cur = Cursor(series, i + 1)
        pending = max(-1.0, min(1.0, float(strategy(cur))))
        targets.append(pending)

    e0, e1 = 1.0, equity[-1]
    # The first bar a strategy can possibly fill at is bars[warmup + 1] — it
    # decides after bars[warmup] closes. The benchmark buys at that same open,
    # so buy_and_hold as a strategy equals it exactly (less cost). A benchmark
    # that bought one bar earlier would be holding a trade no strategy could
    # have made.
    bench = bars[-1].close / bars[warmup + 1].open - 1
    held = sum(1 for i in range(len(equity)) if _pos_at(fills, bars, warmup, i) != 0)
    exposure = held / len(equity) if equity else 0.0
    rets = [equity[i] / equity[i - 1] - 1.0 for i in range(1, len(equity))]
    years = len(equity) / bpy
    cagr = e1 ** (1.0 / years) - 1.0 if years > 0 and e1 > 0 else None
    return {
        "strategy": name or getattr(strategy, "__name__", "strategy"),
        "symbol": series.symbol, "timeframe": series.timeframe,
        "source": series.provenance.get("source"),
        "bars": len(bars), "start": bars[0].ts.isoformat(),
        "end": bars[-1].ts.isoformat(),
        "return": e1 / e0 - 1, "benchmark": bench, "cagr": cagr,
        "max_drawdown": max_drawdown(equity),
        "fills": len(fills), "cost_bps": cost_bps, "cash_yield": cash_yield,
        "exposure": exposure, "years": years, "bars_per_year": bpy,
        "warmup": warmup, "live_bars": len(equity),
        "scored_from": bars[warmup].ts.isoformat(),
        **_stats(rets, bpy),
        "final_signal": pending,
        "not_modelled": "order book, partial fills, intraday slippage, "
                        "borrow, dividends",
        "qc_verdict": qc["verdict"], "qc_unrun": qc["unrun"],
        "equity": equity, "equity_ts": equity_ts, "targets": targets,
        "bar_returns": rets, "fill_list": fills,
    }


def window_stats(result, start=None, end=None):
    """
    Stats over a date window of an existing replay, from its per-bar returns.

    The strategy ran on the whole series, so it had its full warm-up history
    at the window's first bar; the window only chooses which bars are SCORED.
    That is how an in-sample / holdout split has to work — slicing the bars
    themselves would hand the holdout a strategy with amnesia.
    """
    ts = result["equity_ts"]
    eq = result["equity"]
    idx = [i for i, t in enumerate(ts)
           if (start is None or t >= start) and (end is None or t < end)]
    if len(idx) < 2:
        return {"bars_used": len(idx), "return": None, "sharpe": 0.0,
                "max_drawdown": 0.0, "start": start, "end": end}
    seg = [eq[i] for i in idx]
    rets = [seg[i] / seg[i - 1] - 1.0 for i in range(1, len(seg))]
    fills_in = sum(1 for f in result["fill_list"]
                   if (start is None or f["ts"] >= start) and (end is None or f["ts"] < end))
    return {"start": ts[idx[0]], "end": ts[idx[-1]], "bars_used": len(idx),
            "return": seg[-1] / seg[0] - 1.0, "max_drawdown": max_drawdown(seg),
            "fills": fills_in, **_stats(rets, result["bars_per_year"])}


def _pos_at(fills, bars, warmup, i):
    """Position held during equity index i (bar warmup+i), from the fill log."""
    ts = bars[warmup + i].ts.isoformat()
    pos = 0.0
    for f in fills:
        if f["ts"] <= ts:
            pos = f["target"]
        else:
            break
    return pos


def summary(r):
    return (f"{r['strategy']} on {r['symbol']} {r['timeframe']}: "
            f"{r['bars']} bars, return {r['return']:+.1%} vs buy&hold "
            f"{r['benchmark']:+.1%}, max drawdown {r['max_drawdown']:.1%}, "
            f"{r['fills']} fill(s) at {r['cost_bps']:g} bps, "
            f"exposure {r['exposure']:.0%}")
