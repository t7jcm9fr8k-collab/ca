#!/usr/bin/env python3
"""
features.py — the things a discretionary trader reads off a chart, as numbers.

EMA, VWAP, ATR, rejection-candle geometry, swing levels, a volume profile with
point of control and value area, and a bar-delta proxy for order flow. Each is
a plain function of a sequence of closed bars. None of them draws anything.

WHY THESE EXIST
    "Use the candles to see a pattern, with rejection blocks and EMA and VWAP,
    see where the market is going." Every item in that sentence can be made
    into a number computed from bars — and once it is a number, replay.py can
    test whether it predicts anything, with costs, out of sample. That is the
    whole point: the pipeline is built to MEASURE these claims rather than
    trust them, because the peer-reviewed record on most of them is unkind and
    the only honest answer to "does this hold up" is a backtest you can read.

THE ONE RULE
    Every function here takes a sequence of bars and reads only those bars. It
    never receives the Series. Called on `cursor[-n:]` it is structurally unable
    to see the future — the guarantee lives in replay.Cursor, in one place, and
    nothing here can weaken it. A swing high is only known `right` bars after it
    printed; that lag is real and this file does not hide it.

WHAT IS A PROXY, SAID PLAINLY
    `bar_delta` signs a bar's whole volume by whether it closed above its open.
    Real order flow — bid/ask delta, footprint, absorption — needs tick or
    Level-2 data that OHLCV bars do not contain. The proxy is labelled a proxy
    in its name, its docstring and its output; do not report it as order flow.
    `volume_profile` spreads each bar's volume evenly across its range, which is
    the standard OHLC approximation to a profile built from ticks. It is a
    profile of the bars, not of the tape.

USAGE (library — strategies.py uses these)
    from features import ema, vwap, rejection, levels, volume_profile
    e = ema(cursor[-60:], 20)
"""

import datetime as dt

# ---------------------------------------------------------------- helpers

def closes(bars):
    return [b.close for b in bars]


def typical(bar):
    """(H + L + C) / 3 — the price a bar's volume is conventionally assigned to."""
    return (bar.high + bar.low + bar.close) / 3.0


def _values(seq):
    """Accept bars or plain numbers."""
    return [getattr(x, "close", x) for x in seq]


# ---------------------------------------------------------------- averages

def sma(seq, n):
    v = _values(seq)
    if n <= 0 or len(v) < n:
        return None
    return sum(v[-n:]) / n


def ema(seq, n):
    """
    Exponential moving average, seeded with the SMA of the first n values, then
    alpha = 2 / (n + 1). Uses every value given, so give it the whole window you
    want it to remember — `ema(cursor[-200:], 20)` and `ema(cursor[-20:], 20)`
    are different numbers, and the second is just an SMA.
    """
    v = _values(seq)
    if n <= 0 or len(v) < n:
        return None
    a = 2.0 / (n + 1)
    e = sum(v[:n]) / n
    for x in v[n:]:
        e = a * x + (1 - a) * e
    return e


def ema_series(seq, n):
    """The EMA at every position; None where fewer than n values precede."""
    v = _values(seq)
    out = [None] * len(v)
    if n <= 0 or len(v) < n:
        return out
    a = 2.0 / (n + 1)
    e = sum(v[:n]) / n
    out[n - 1] = e
    for i in range(n, len(v)):
        e = a * v[i] + (1 - a) * e
        out[i] = e
    return out


def true_range(bar, prev_close=None):
    if prev_close is None:
        return bar.high - bar.low
    return max(bar.high - bar.low, abs(bar.high - prev_close), abs(bar.low - prev_close))


def atr(bars, n=14):
    """Average true range: the plain mean of the last n true ranges."""
    bars = list(bars)
    if n <= 0 or len(bars) < n + 1:
        return None
    trs = [true_range(bars[i], bars[i - 1].close) for i in range(len(bars) - n, len(bars))]
    return sum(trs) / n


# ---------------------------------------------------------------- vwap

def vwap(bars):
    """
    Volume-weighted average price over the bars given, anchored at the first.
    On daily bars this is a rolling or anchored VWAP; for the intraday session
    VWAP that institutions benchmark against, pass one session's bars — see
    `session_bars`.
    """
    num = den = 0.0
    for b in bars:
        num += typical(b) * b.volume
        den += b.volume
    return num / den if den > 0 else None


def session_bars(bars, tz_name="America/New_York"):
    """The bars that share the last bar's trading date, in the exchange zone."""
    bars = list(bars)
    if not bars:
        return []
    try:
        from zoneinfo import ZoneInfo
        tz = ZoneInfo(tz_name)
    except Exception:
        tz = dt.timezone.utc
    last_day = bars[-1].ts.astimezone(tz).date()
    out = []
    for b in reversed(bars):
        if b.ts.astimezone(tz).date() != last_day:
            break
        out.append(b)
    return list(reversed(out))


def session_vwap(bars, tz_name="America/New_York"):
    return vwap(session_bars(bars, tz_name))


# ---------------------------------------------------------------- candles

def rejection(bar, wick_ratio=2.0, close_zone=1 / 3):
    """
    Pin bar / hammer / shooting star geometry, as numbers.

        bull   lower wick >= wick_ratio x body  AND  close in the top third
        bear   upper wick >= wick_ratio x body  AND  close in the bottom third

    A doji has no body, so the body is floored at 5% of the range — otherwise
    every doji with any wick is a "rejection", which is not what anyone means.
    Returns "bull", "bear" or None. This is the geometry only; whether such a
    bar predicts anything is for replay.py to measure.
    """
    rng = bar.range
    if rng <= 0:
        return None
    body = max(bar.body, rng * 0.05)
    pos = (bar.close - bar.low) / rng          # 0 = closed on the low, 1 = on the high
    if bar.lower_wick >= wick_ratio * body and pos >= 1 - close_zone:
        return "bull"
    if bar.upper_wick >= wick_ratio * body and pos <= close_zone:
        return "bear"
    return None


def rejections(bars, **kw):
    """[(index, 'bull'|'bear')] over the sequence."""
    return [(i, r) for i, b in enumerate(bars) if (r := rejection(b, **kw))]


# ---------------------------------------------------------------- levels

def swings(bars, left=2, right=2):
    """
    Fractal swing points. Bar i is a swing high when its high exceeds the
    `left` highs before it and the `right` highs after it; lows mirror.

    The `right` bars after are REQUIRED, so the most recent `right` bars can
    never be swings yet. A level is only known once price has moved away from
    it. This lag is the honest cost of the definition; do not shorten `right`
    to zero to "see it sooner" — that turns every bar into a level.
    """
    bars = list(bars)
    highs, lows = [], []
    for i in range(left, len(bars) - right):
        h, l = bars[i].high, bars[i].low
        if all(h > bars[j].high for j in range(i - left, i)) and \
           all(h > bars[j].high for j in range(i + 1, i + right + 1)):
            highs.append((i, h))
        if all(l < bars[j].low for j in range(i - left, i)) and \
           all(l < bars[j].low for j in range(i + 1, i + right + 1)):
            lows.append((i, l))
    return {"highs": highs, "lows": lows}


def levels(bars, left=2, right=2, tolerance=0.002):
    """
    Price levels from swing points, clustered: swing prices within `tolerance`
    (fractional) of each other merge into one level at their mean. Sorted
    ascending. Each level carries how many swings made it — a level touched
    three times is a different claim from one touched once.
    """
    sw = swings(bars, left, right)
    pts = sorted(p for _, p in sw["highs"] + sw["lows"])
    out = []
    for p in pts:
        if out and abs(p - out[-1]["price"]) / out[-1]["price"] <= tolerance:
            grp = out[-1]
            grp["touches"] += 1
            grp["price"] = (grp["price"] * (grp["touches"] - 1) + p) / grp["touches"]
        else:
            out.append({"price": p, "touches": 1})
    return out


def nearest_level(price, lvls):
    """(level dict, signed distance as a fraction of price) or (None, None)."""
    if not lvls:
        return None, None
    best = min(lvls, key=lambda l: abs(l["price"] - price))
    return best, (price - best["price"]) / price


# ---------------------------------------------------------------- volume profile

def volume_profile(bars, bins=24, value_area=0.70):
    """
    Where the volume traded, by price. Each bar's volume is spread evenly over
    [low, high] — the standard approximation from OHLC bars, and an
    approximation is what it is.

    Returns point of control (the bin with the most volume), the value area
    (the narrowest band around the POC holding `value_area` of the volume,
    grown one bin at a time toward the heavier side), and the bins.
    """
    bars = list(bars)
    if not bars or bins <= 0:
        return None
    lo = min(b.low for b in bars)
    hi = max(b.high for b in bars)
    if hi <= lo:
        return None
    w = (hi - lo) / bins
    vol = [0.0] * bins
    for b in bars:
        span = b.high - b.low
        if span <= 0:
            k = min(bins - 1, int((b.close - lo) / w))
            vol[k] += b.volume
            continue
        per = b.volume / span
        for k in range(bins):
            a, z = lo + k * w, lo + (k + 1) * w
            overlap = min(z, b.high) - max(a, b.low)
            if overlap > 0:
                vol[k] += per * overlap
    total = sum(vol)
    if total <= 0:
        return None
    poc = max(range(bins), key=lambda k: vol[k])
    lo_k = hi_k = poc
    acc = vol[poc]
    while acc < value_area * total and (lo_k > 0 or hi_k < bins - 1):
        down = vol[lo_k - 1] if lo_k > 0 else -1
        up = vol[hi_k + 1] if hi_k < bins - 1 else -1
        if up >= down:
            hi_k += 1
            acc += vol[hi_k]
        else:
            lo_k -= 1
            acc += vol[lo_k]
    mid = lambda k: lo + (k + 0.5) * w
    return {"poc": mid(poc), "va_low": lo + lo_k * w, "va_high": lo + (hi_k + 1) * w,
            "low": lo, "high": hi, "bin_width": w,
            "bins": [(lo + k * w, lo + (k + 1) * w, vol[k]) for k in range(bins)],
            "value_area_share": acc / total}


# ---------------------------------------------------------------- order-flow proxy

def bar_delta_proxy(bar):
    """
    +volume if the bar closed above its open, -volume if below, 0 if flat.

    A PROXY. Real delta is bought-at-ask minus sold-at-bid volume and needs
    the tape. This signs a bar's entire volume by one comparison; it is the
    best OHLCV can do and it is labelled accordingly.
    """
    if bar.close > bar.open:
        return bar.volume
    if bar.close < bar.open:
        return -bar.volume
    return 0.0


def cvd_proxy(bars):
    """Cumulative bar-delta proxy over the sequence. Same caveat, cumulated."""
    out, acc = [], 0.0
    for b in bars:
        acc += bar_delta_proxy(b)
        out.append(acc)
    return out


def describe(bars, ema_n=20, atr_n=14, profile_window=40):
    """One dict of the readings a trader would want at the last closed bar."""
    bars = list(bars)
    if not bars:
        return {}
    last = bars[-1]
    lv = levels(bars)
    near, dist = nearest_level(last.close, lv)
    prof = volume_profile(bars[-profile_window:]) if len(bars) >= 5 else None
    return {
        "close": last.close,
        "ema": ema(bars, ema_n), "vwap_anchored": vwap(bars),
        "atr": atr(bars, atr_n),
        "rejection": rejection(last),
        "levels": len(lv), "nearest_level": near["price"] if near else None,
        "distance_to_level": dist,
        "poc": prof["poc"] if prof else None,
        "value_area": (prof["va_low"], prof["va_high"]) if prof else None,
        "cvd_proxy": cvd_proxy(bars)[-1],
    }
