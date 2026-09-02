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
from `sma_cross_20_50`.

SPEC STRINGS (for run.py --strategy)
    buy_and_hold
    sma_cross:10,30
    breakout:20
"""


def buy_and_hold(cursor):
    """Fully invested from the first decision. The benchmark, as a strategy."""
    return 1.0


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
    return s


REGISTRY = {
    "buy_and_hold": lambda: buy_and_hold,
    "sma_cross": sma_cross,
    "breakout": breakout,
}


def make(spec):
    """'sma_cross:10,30' -> callable. Unknown names are refused, not guessed."""
    name, _, args = spec.partition(":")
    if name not in REGISTRY:
        raise KeyError(f"unknown strategy {name!r}; one of {', '.join(REGISTRY)}")
    params = [a.strip() for a in args.split(",") if a.strip()] if args else []
    return REGISTRY[name](*params)
