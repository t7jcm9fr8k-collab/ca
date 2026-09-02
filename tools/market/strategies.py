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


REGISTRY = {
    "buy_and_hold": lambda: buy_and_hold,
    "sma_cross": sma_cross,
    "breakout": breakout,
    "trend_filter": trend_filter,
    "ema_pullback": ema_pullback,
    "vwap_reclaim": vwap_reclaim,
    "value_area": value_area,
}


def make(spec):
    """'sma_cross:10,30' -> callable. Unknown names are refused, not guessed."""
    name, _, args = spec.partition(":")
    if name not in REGISTRY:
        raise KeyError(f"unknown strategy {name!r}; one of {', '.join(REGISTRY)}")
    params = [a.strip() for a in args.split(",") if a.strip()] if args else []
    return REGISTRY[name](*params)
