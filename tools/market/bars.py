#!/usr/bin/env python3
"""
bars.py — OHLCV bars, and the one rule about where they came from.

WHY BARS AND NOT CLOSES
    A close-only series throws away three numbers per period. The high and low
    say how far price travelled inside the bar; the open says where it started
    relative to the last close. A gap, a long wick, a bar that closed at its
    high — none of that exists in a list of closes. This file keeps all five
    numbers, exactly, as numbers.

    It does NOT draw candlesticks. A rendered chart converts exact prices into a
    lossy picture; the numbers are strictly more information than any image of
    them. If candle SHAPE ever matters (body ratio, wick ratio, gap), it is
    computed from these bars, not read off a PNG.

THE ONE RULE
    A Series refuses to exist without provenance — source, when it was fetched,
    whether it is adjusted. `compose.py` in the shirt pipeline refuses to render
    a layer without a source URL and licence, for the same reason: a number
    whose origin nobody can name must not reach a decision. Here a decision can
    cost money.

WHAT THIS FILE DOES NOT DO
    It does not validate the VALUES. A bar with high < low loads fine here and
    is caught by `barqc.py`. Loading and judging are kept apart, as
    `compose.py` and `qc.py` are, so that a check can never be skipped by
    accident because the loader "already handled it".

USAGE
    python3 bars.py --csv bars/AAPL-1d.csv --symbol AAPL --timeframe 1d
    python3 bars.py --csv x.csv --symbol AAPL --timeframe 1d --source stooq --show 5
"""

import argparse
import csv
import datetime as dt
import io
import os
import sys
from dataclasses import dataclass, field

HERE = os.path.dirname(os.path.abspath(__file__))
UTC = dt.timezone.utc

# Timeframes this pipeline understands. Daily is what a free source gives you
# without a key; the intraday ones exist so the type is honest about what a
# bar covers, and so barqc can tell "session count" apart from "bar count".
TIMEFRAMES = {"1d": dt.timedelta(days=1),
              "1h": dt.timedelta(hours=1),
              "15m": dt.timedelta(minutes=15),
              "5m": dt.timedelta(minutes=5),
              "1m": dt.timedelta(minutes=1)}


class Unparseable(Exception):
    """Read the file and could not make bars of it. NOT the same as no bars."""


class NoProvenance(Exception):
    """A series without a named origin. Refused, not defaulted."""


@dataclass(frozen=True)
class Bar:
    """One period. Immutable, so a strategy cannot 'fix' a bar it is looking at."""
    ts: dt.datetime            # tz-aware UTC. For daily bars, the date at 00:00Z.
    open: float
    high: float
    low: float
    close: float
    volume: float

    def __post_init__(self):
        if self.ts.tzinfo is None:
            raise ValueError("Bar.ts must be tz-aware; a naive timestamp is a "
                             "session-boundary bug waiting to happen")

    # Candle geometry, computed rather than drawn. Not used by anything in
    # stage 1 — kept here so that when shape matters it is one property away
    # and never a picture.
    @property
    def body(self):
        return abs(self.close - self.open)

    @property
    def range(self):
        return self.high - self.low

    @property
    def upper_wick(self):
        return self.high - max(self.open, self.close)

    @property
    def lower_wick(self):
        return min(self.open, self.close) - self.low

    @property
    def bullish(self):
        return self.close > self.open


@dataclass(frozen=True)
class Series:
    """
    Bars for one symbol at one timeframe, with the receipt attached.

    `provenance` must carry `source` and `fetched_at`; `adjusted` is recorded
    as given (True/False/None) and barqc reports on it. Nothing here sorts or
    de-duplicates — if the source handed over disorder, that is a finding.
    """
    symbol: str
    timeframe: str
    bars: tuple
    provenance: dict = field(default_factory=dict)

    def __post_init__(self):
        if self.timeframe not in TIMEFRAMES:
            raise ValueError(f"unknown timeframe {self.timeframe!r}; "
                             f"one of {', '.join(TIMEFRAMES)}")
        missing = [k for k in ("source", "fetched_at")
                   if not str(self.provenance.get(k, "")).strip()]
        if missing:
            raise NoProvenance(
                f"series for {self.symbol} has no {' / '.join(missing)}. "
                f"A bar whose origin nobody can name must not reach a decision.")
        object.__setattr__(self, "bars", tuple(self.bars))

    def __len__(self):
        return len(self.bars)

    def __getitem__(self, i):
        return self.bars[i]

    @property
    def first(self):
        return self.bars[0] if self.bars else None

    @property
    def last(self):
        return self.bars[-1] if self.bars else None

    @property
    def period(self):
        return TIMEFRAMES[self.timeframe]

    def describe(self):
        if not self.bars:
            return f"{self.symbol} {self.timeframe}: 0 bars"
        return (f"{self.symbol} {self.timeframe}: {len(self.bars)} bars, "
                f"{self.first.ts:%Y-%m-%d} → {self.last.ts:%Y-%m-%d}, "
                f"source {self.provenance.get('source')}")


# ---------------------------------------------------------------- CSV in/out

# Column names we will accept, lowercased. Single letters are Alpaca's JSON
# keys; the long forms are Stooq / Yahoo / most exports. `adj close` is
# deliberately NOT an alias for close — if a file has both, we take `close`
# and leave `adjusted` for the caller to state, because guessing wrong there
# is a silent −50% "crash" on every split.
_TS_COLS = ("date", "timestamp", "datetime", "time", "t")
_COLS = {"open": ("open", "o"), "high": ("high", "h"), "low": ("low", "l"),
         "close": ("close", "c"), "volume": ("volume", "vol", "v")}


def _parse_ts(text, timeframe):
    """
    A date or an instant, to tz-aware UTC.

    Daily bars carry a trading DATE, not a moment; they are pinned to 00:00Z so
    that two daily bars from different sources for the same day compare equal.
    Intraday bars are instants and must say their zone; a naive intraday
    timestamp is refused, because "09:30" means different things in New York
    and in UTC and the difference is an entire session.
    """
    s = text.strip()
    if timeframe == "1d":
        try:
            d = dt.date.fromisoformat(s[:10])
        except ValueError:
            raise Unparseable(f"cannot read {s!r} as a date")
        return dt.datetime(d.year, d.month, d.day, tzinfo=UTC)
    try:
        t = dt.datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        raise Unparseable(f"cannot read {s!r} as a timestamp")
    if t.tzinfo is None:
        raise Unparseable(f"intraday timestamp {s!r} has no timezone")
    return t.astimezone(UTC)


def parse_csv(text, symbol, timeframe, source, fetched_at=None,
              adjusted=None, extra=None):
    """
    CSV text → Series. Raises Unparseable; never returns an empty Series for a
    file that had rows it could not read.

    A file with a valid header and ZERO data rows does return an empty Series,
    because that is a true statement about the file — and barqc's session-count
    check will then say exactly how many bars are missing.
    """
    rdr = csv.reader(io.StringIO(text))
    try:
        header = next(rdr)
    except StopIteration:
        raise Unparseable("empty file — not even a header")
    cols = [h.strip().lower() for h in header]

    def find(names):
        for n in names:
            if n in cols:
                return cols.index(n)
        return None

    ts_i = find(_TS_COLS)
    idx = {k: find(v) for k, v in _COLS.items()}
    missing = [k for k, v in idx.items() if v is None]
    if ts_i is None:
        missing.insert(0, "timestamp/date")
    if missing:
        raise Unparseable(f"header {header} is missing {', '.join(missing)}")

    bars = []
    for n, row in enumerate(rdr, start=2):
        if not row or all(not c.strip() for c in row):
            continue
        try:
            bars.append(Bar(
                ts=_parse_ts(row[ts_i], timeframe),
                open=float(row[idx["open"]]), high=float(row[idx["high"]]),
                low=float(row[idx["low"]]), close=float(row[idx["close"]]),
                volume=float(row[idx["volume"]] or 0)))
        except (ValueError, IndexError) as e:
            raise Unparseable(f"row {n}: {e} — {row}")

    prov = {"source": source,
            "fetched_at": fetched_at or dt.datetime.now(UTC).isoformat(timespec="seconds"),
            "adjusted": adjusted}
    if extra:
        prov.update(extra)
    return Series(symbol, timeframe, bars, prov)


def load_csv(path, symbol, timeframe="1d", source=None, adjusted=None):
    """
    The offline door. Everything downstream can be tested against a file, which
    is why the whole pipeline runs in a container that cannot reach a single
    market-data host.
    """
    if not os.path.exists(path):
        raise Unparseable(f"no such file: {path}")
    src = source or f"csv:{os.path.basename(path)}"
    fetched = dt.datetime.fromtimestamp(os.path.getmtime(path), UTC)
    with open(path, newline="") as f:
        return parse_csv(f.read(), symbol, timeframe, src,
                         fetched_at=fetched.isoformat(timespec="seconds"),
                         adjusted=adjusted, extra={"path": os.path.abspath(path)})


def to_csv(series, path):
    """Write bars back out in the plain form parse_csv reads."""
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["timestamp", "open", "high", "low", "close", "volume"])
        for b in series.bars:
            ts = b.ts.strftime("%Y-%m-%d") if series.timeframe == "1d" \
                else b.ts.isoformat(timespec="seconds")
            w.writerow([ts, repr(b.open), repr(b.high), repr(b.low),
                        repr(b.close), repr(b.volume)])
    os.replace(tmp, path)
    return path


def bars_path(symbol, timeframe, root=None):
    return os.path.join(root or os.path.join(HERE, "bars"),
                        f"{symbol.upper()}-{timeframe}.csv")


# ---------------------------------------------------------------- cli

def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--csv", required=True)
    ap.add_argument("--symbol", required=True)
    ap.add_argument("--timeframe", default="1d", choices=sorted(TIMEFRAMES))
    ap.add_argument("--source", help="where the file came from; recorded")
    ap.add_argument("--adjusted", choices=["yes", "no"],
                    help="whether prices are split/dividend adjusted; recorded")
    ap.add_argument("--show", type=int, default=3, help="print the last N bars")
    a = ap.parse_args()

    adj = {"yes": True, "no": False}.get(a.adjusted)
    try:
        s = load_csv(a.csv, a.symbol, a.timeframe, a.source, adj)
    except (Unparseable, NoProvenance) as e:
        sys.exit(f"REFUSED: {e}")

    print(s.describe())
    print(f"provenance: {s.provenance}")
    for b in s.bars[-a.show:]:
        print(f"  {b.ts:%Y-%m-%d %H:%M}  O {b.open:<10g} H {b.high:<10g} "
              f"L {b.low:<10g} C {b.close:<10g} V {b.volume:g}")
    print("\nnext:  python3 barqc.py --csv", a.csv, "--symbol", a.symbol)


if __name__ == "__main__":
    main()
