#!/usr/bin/env python3
"""
strategies.py — reference strategies, deliberately dull.

These exist so the pipeline can be exercised end to end: bars → barqc → replay
→ ledger → gate. They are not a claim to edge. The peer-reviewed evidence on
simple technical rules is unkind, and nothing here should be read as more than
a working example of the CONTRACT a strategy has to honour:

    strategy(cursor) -> target position in [-1, 1]

`cursor` is a replay.Cursor: only closed bars are visible, `cursor[-1]` is the
last of them, and reaching past them raises. The return value is the fraction
of equity to hold after the NEXT open. Long-only strategies return 0 or 1.

A strategy is a plain callable. Parameterised ones are factories that return a
callable with a stable `__name__`, so the ledger can tell `sma_cross_10_30`
from `sma_cross_20_50`, and a `warmup`: how many closed bars it needs before
it can act. replay.py scores from there. The first real run scored a 200-day
filter from bar 2 against buy-and-hold from bar 2, and most of its "cost" was
the 200 bars it was forbidden to trade.

SPEC STRINGS (for run.py --strategy)
    buy_and_hold
    sma_cross:10,30
    breakout:20
    ema_pullback:20,50,5     trend + pullback to the fast EMA + bull rejection candle
    vwap_reclaim:20          close above anchored VWAP and EMA
    value_area:40            close above the volume profile's value-area high
    rsi_dip:14,30,5          long for 5 bars after RSI(14) < 30 — the null test's one survivor
    rsi_dip_exit:14,30,50,10 the same entry, exit on RSI > 50 or after 10 bars — the one alternative
    trend_or_dip:200,14,30,5 the filter OR the dip — declared before it was run
    vol_target[SPEC]:0.10,20 any strategy scaled to a 10% vol target, never above 1

The last three are the discretionary "confluence" setups — candle + EMA +
VWAP + level + volume — made mechanical so replay.py can measure them. On a
drifting random walk all three lag buy-and-hold after costs; whether they do
on real bars is exactly the question the pipeline exists to answer.
"""


def buy_and_hold(cursor):
    """Fully invested from the first decision. The benchmark, as a strategy."""
    return 1.0


buy_and_hold.warmup = 0


def sma_cross(fast=10, slow=30):
    """Long when the fast simple average is above the slow one, else flat."""
    fast, slow = int(fast), int(slow)
    if not 0 < fast < slow:
        raise ValueError(f"need 0 < fast < slow, got {fast}, {slow}")

    def s(cursor):
        if len(cursor) < slow:
            return 0.0
        c = cursor.closes(slow)
        return 1.0 if sum(c[-fast:]) / fast > sum(c) / slow else 0.0
    s.__name__ = f"sma_cross_{fast}_{slow}"
    s.warmup = slow
    return s


def breakout(lookback=20):
    """Long when the last close is the highest close of the lookback, else flat."""
    lookback = int(lookback)

    def s(cursor):
        if len(cursor) < lookback + 1:
            return 0.0
        c = cursor.closes(lookback + 1)
        return 1.0 if c[-1] >= max(c[:-1]) else 0.0
    s.__name__ = f"breakout_{lookback}"
    s.warmup = lookback + 1
    return s


def ema_pullback(fast=20, slow=50, lookback=5):
    """
    The discretionary "trend + pullback + rejection" setup, made mechanical.

    Long when the trend is up (close above the slow EMA, fast above slow) AND
    within the last `lookback` bars a bull rejection candle printed with its
    low within one ATR of the fast EMA — price came back to the average, was
    refused, and closed strong. Flat when close is below the slow EMA. Between
    those, flat: stateless, so it does not "hold" a position it cannot see.
    """
    import features as F
    fast, slow, lookback = int(fast), int(slow), int(lookback)
    if not 0 < fast < slow:
        raise ValueError(f"need 0 < fast < slow, got {fast}, {slow}")

    def s(cursor):
        w = cursor[-(slow * 4):]
        if len(w) < slow + 15:
            return 0.0
        e_fast, e_slow, a = F.ema(w, fast), F.ema(w, slow), F.atr(w, 14)
        last = w[-1]
        if e_fast is None or e_slow is None or a is None or a <= 0:
            return 0.0
        if last.close < e_slow or e_fast < e_slow:
            return 0.0
        for b in w[-lookback:]:
            if F.rejection(b) == "bull" and abs(b.low - e_fast) <= a:
                return 1.0
        return 0.0
    s.__name__ = f"ema_pullback_{fast}_{slow}_{lookback}"
    s.warmup = slow + 15
    return s


def vwap_reclaim(n=20):
    """Long when close is above both the n-bar anchored VWAP and the n EMA."""
    import features as F
    n = int(n)

    def s(cursor):
        w = cursor[-(n * 3):]
        if len(w) < n:
            return 0.0
        v, e = F.vwap(w[-n:]), F.ema(w, n)
        c = w[-1].close
        return 1.0 if (v is not None and e is not None and c > v and c > e) else 0.0
    s.__name__ = f"vwap_reclaim_{n}"
    s.warmup = n
    return s


def value_area(window=40):
    """
    Market-profile style: long when close is above the value-area high of the
    last `window` bars' volume profile — price accepted above value — flat
    when below the point of control. In between, flat.
    """
    import features as F
    window = int(window)

    def s(cursor):
        w = cursor[-window:]
        if len(w) < window:
            return 0.0
        p = F.volume_profile(w)
        if not p:
            return 0.0
        c = w[-1].close
        return 1.0 if c > p["va_high"] else 0.0
    s.__name__ = f"value_area_{window}"
    s.warmup = window
    return s


def trend_filter(n=200):
    """
    Long when close is above the n-bar simple average, else flat. The slow
    filter EVIDENCE.md ranks fourth: documented to cut drawdowns on an index
    at a few trades a year, and documented NOT to raise returns. Run it with
    --cash-yield so the time out of the market is not scored as earning zero.
    """
    import features as F
    n = int(n)

    def s(cursor):
        if len(cursor) < n:
            return 0.0
        return 1.0 if cursor[-1].close > F.sma(cursor[-n:], n) else 0.0
    s.__name__ = f"trend_filter_{n}"
    s.warmup = n
    return s


def rsi_dip_exit(n=14, level=30, exit_level=50, max_hold=10):
    """
    The dip rule with a different exit: enter after a close with RSI(n) below
    `level`; while in, leave after the first close with RSI(n) above
    `exit_level`, or once the last RSI-below-`level` close is `max_hold` or
    more bars ago. Pre-registered 2026-09-04 as the ONE alternative exit to
    the fixed five-bar hold (step B of the day run): 50 is RSI's midpoint,
    the "reversal has played out" reading; 10 bars is a cap so a failed
    reversal cannot become a position. Counted as a trial beside rsi_dip.

    v1 kept "in" and an age counter in closure state and the leak check
    caught it (1 of 25 bars decided differently when re-run from a truncated
    series). v2 reads `cursor.position` for "in" and counts the age from the
    bars themselves. Both count as trials.
    """
    import features as F
    n, level, exit_level, max_hold = int(n), float(level), float(exit_level), int(max_hold)

    def s(cursor):
        if len(cursor) < n + 1:
            return 0.0
        r = F.rsi_series(cursor.closes(), n)
        last = r[-1]
        fired = [k for k in range(len(r)) if r[k] is not None and r[k] < level]
        if float(getattr(cursor, "position", 0.0)) > 0:
            age = (len(r) - 1 - fired[-1]) if fired else max_hold
            if (last is not None and last > exit_level) or age >= max_hold:
                return 0.0
            return 1.0
        return 1.0 if (last is not None and last < level) else 0.0
    s.__name__ = f"rsi_dip_exit_{n}_{level:g}_{exit_level:g}_{max_hold}"
    s.warmup = n + 1
    return s


def rsi_dip(n=14, level=30, hold=5):
    """
    Long for `hold` bars after any closed bar whose RSI(n) is below `level`;
    flat otherwise. Overlapping signals merge into one holding.

    This is the null test's `rsi_oversold` rule promoted to a strategy so
    replay can price it: same RSI, same trigger, entry at the next open, the
    same 5-bar hold. It is pre-registered here on 2026-09-04 after that rule
    was the only one of fourteen to survive the vol-matched null on 21 years
    of SPY with witnesses in both halves. What it buys is the short-term
    reversal premium at volatility extremes — liquidity provision — so expect
    its worst days to be the market's worst days. Run with --cash-yield: it
    is out of the market ~90% of the time.
    """
    import features as F
    n, level, hold = int(n), float(level), int(hold)
    if n < 2 or hold < 1:
        raise ValueError(f"need n >= 2 and hold >= 1, got {n}, {hold}")

    def s(cursor):
        if len(cursor) < n + 1:
            return 0.0
        r = F.rsi_series(cursor.closes(), n)
        recent = r[-hold:]
        return 1.0 if any(x is not None and x < level for x in recent) else 0.0
    s.__name__ = f"rsi_dip_{n}_{level:g}_{hold}"
    s.warmup = n + 1
    return s


def trend_or_dip(n=200, rsi_n=14, level=30, hold=5):
    """
    Long when the trend filter is long OR the dip rule is long. The two
    pre-registered survivors of three runs, combined the one way that makes
    sense: the filter holds through bull markets and steps aside in bear
    markets, and the dip rule buys the five days after a capitulation, which
    is exactly when the filter is out. Declared 2026-09-04 BEFORE it was run,
    as one trial, after both parts had been measured alone.
    """
    tf, rd = trend_filter(n), rsi_dip(rsi_n, level, hold)

    def s(cursor):
        return max(tf(cursor), rd(cursor))
    s.__name__ = f"trend_or_dip_{int(n)}_{int(rsi_n)}_{float(level):g}_{int(hold)}"
    s.warmup = max(tf.warmup, rd.warmup)
    return s


def vol_target(inner, target=0.10, window=20, band=0.10):
    """
    Scale an inner strategy's target by min(1, target_vol / realized_vol),
    where realized_vol is the annualised standard deviation of the last
    `window` close-to-close returns. Never above 1 — no leverage. A change
    smaller than `band` (fraction of equity) is not traded, so the position
    is not rebalanced every day for a few basis points at 5 bp a trade.

    Pre-registered 2026-09-04, v1: target 10% annualised, window 20, band
    0.10, ONE setting, before any run. (v1 kept the held fraction in closure
    state; the leak check caught it deciding differently when re-run from a
    truncated series. v2, same rule, reads `cursor.position` instead. The
    numbers in EVIDENCE.md are from v2.) The claim being tested is Harvey,
    Hoyle, Korgaonkar, Rattray, Sargaison & Van Hemert 2018, "The impact of
    volatility targeting": for equities it raises the Sharpe ratio and cuts
    the left tail, because equity volatility clusters and high-volatility
    stretches carry lower returns per unit of risk. Applied to a long-only
    rule it can only reduce exposure, so it trades return for risk; whether
    that is a better trade than the rule alone is the question.

    Spec form: vol_target[trend_or_dip:200,14,30,5]:0.10,20
    """
    import math
    inner_fn = make(inner) if isinstance(inner, str) else inner
    target, window, band = float(target), int(window), float(band)
    if not 0 < target < 1 or window < 2:
        raise ValueError(f"need 0 < target < 1 and window >= 2, got {target}, {window}")
    def s(cursor):
        want = float(inner_fn(cursor))
        held = float(getattr(cursor, "position", 0.0))
        if len(cursor) < window + 1:
            scale = 1.0
        else:
            c = cursor.closes(window + 1)
            rets = [c[i] / c[i - 1] - 1.0 for i in range(1, len(c))]
            m = sum(rets) / len(rets)
            sd = math.sqrt(sum((r - m) ** 2 for r in rets) / (len(rets) - 1))
            vol = sd * math.sqrt(252)
            scale = 1.0 if vol <= 0 else min(1.0, target / vol)
        new = max(-1.0, min(1.0, want * scale))
        # a fractional rebalance smaller than the band is not worth its cost;
        # going to or from flat always is, because that is the rule speaking
        if want == 0.0 or held == 0.0 or abs(new - held) >= band:
            return new
        return held
    s.__name__ = f"vol_target_{inner_fn.__name__}_{target:g}_{window}"
    s.warmup = max(inner_fn.warmup, window + 1)
    return s


REGISTRY = {
    "buy_and_hold": lambda: buy_and_hold,
    "vol_target": vol_target,
    "rsi_dip": rsi_dip,
    "rsi_dip_exit": rsi_dip_exit,
    "trend_or_dip": trend_or_dip,
    "sma_cross": sma_cross,
    "breakout": breakout,
    "trend_filter": trend_filter,
    "ema_pullback": ema_pullback,
    "vwap_reclaim": vwap_reclaim,
    "value_area": value_area,
}


def make(spec):
    """'sma_cross:10,30' -> callable. Unknown names are refused, not guessed."""
    inner = None
    if "[" in spec:                        # wrapper[inner spec]:args
        name, _, rest = spec.partition("[")
        inner, _, tail = rest.rpartition("]")
        spec = name + tail
    name, _, args = spec.partition(":")
    if name not in REGISTRY:
        raise KeyError(f"unknown strategy {name!r}; one of {', '.join(REGISTRY)}")
    params = [a.strip() for a in args.split(",") if a.strip()] if args else []
    if inner is not None:
        return REGISTRY[name](inner, *params)
    return REGISTRY[name](*params)
