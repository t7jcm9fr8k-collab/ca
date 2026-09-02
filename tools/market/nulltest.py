#!/usr/bin/env python3
"""
nulltest.py — the null exercises. Code the pattern, apply real costs, compare
it to shuffled bars, and watch it go to zero.

WHY
    EVIDENCE.md's build-first list, item 4: these are what the stack is built
    from, they are cheap, and seeing them fail against a proper baseline IS the
    financial-literacy lesson. Every rule here is fixed in advance and written
    down below. Nothing is tuned to the data.

THE RULES (pre-registered)
    hammer_after_decline      bull rejection bar AND the prior 5-bar return < 0
    star_after_rise           bear rejection bar AND the prior 5-bar return > 0  (short)
    engulf_bull_after_decline bull engulfing AND prior 5-bar return < 0
    engulf_bear_after_rise    bear engulfing AND prior 5-bar return > 0          (short)
    pin_at_round              bull rejection with its low within 0.2% of a round number
    rsi_oversold              RSI(14) < 30
    fell_5pct_10bars          close down >= 5% from 10 bars ago — the plain thing
                              RSI<30 is a dressed-up version of
    doji                      body <= 10% of range — a VOLATILITY claim; its
                              direction test is included so you can see it is ~50%

THE MEASUREMENT
    For every bar where a rule fires at bar i, the trade enters at the OPEN of
    bar i+1 and exits at the CLOSE of bar i+h. No look-ahead: the rule reads
    bars 0..i only. Short rules negate the return. A flat round-trip cost is
    charged.

THE BASELINE
    Block-shuffled bars: the bar sequence is cut into blocks of 20 and the
    blocks are shuffled, which destroys any real link between a pattern and
    what follows it while keeping the within-block texture (autocorrelation,
    volatility clustering). The rule is re-run on each shuffle. The p-value is
    the fraction of shuffles whose mean forward return was at least as good
    as the real one. This is the honest comparison: not "did it make money"
    but "did it make more than the same rule on bars where it cannot work".

USAGE
    python3 nulltest.py --csv bars/SPY-1d.csv --symbol SPY --source stooq --horizon 1 --cost-bps 5
    python3 nulltest.py --csv bars/SPY-1d.csv --symbol SPY --horizon 5 --shuffles 500
"""

import argparse
import math
import os
import random
import sys

import bars as B
import barqc
import features as F
import ledger

HERE = os.path.dirname(os.path.abspath(__file__))
BLOCK = 20
LOOKBACK = 5


def _ret(bars, i, k):
    return bars[i].close / bars[i - k].close - 1.0 if i >= k else None


def rules(bars):
    """{rule: (side, [indices])} — each index i fires on bars 0..i only."""
    n = len(bars)
    rsi = F.rsi_series(bars, 14)
    out = {k: [] for k in ("hammer_after_decline", "star_after_rise",
                           "engulf_bull_after_decline", "engulf_bear_after_rise",
                           "pin_at_round", "rsi_oversold", "fell_5pct_10bars", "doji")}
    for i in range(LOOKBACK, n):
        b = bars[i]
        r5 = _ret(bars, i, LOOKBACK)
        rej = F.rejection(b)
        eng = F.engulfing(bars[i - 1], b)
        if rej == "bull" and r5 < 0:
            out["hammer_after_decline"].append(i)
        if rej == "bear" and r5 > 0:
            out["star_after_rise"].append(i)
        if eng == "bull" and r5 < 0:
            out["engulf_bull_after_decline"].append(i)
        if eng == "bear" and r5 > 0:
            out["engulf_bear_after_rise"].append(i)
        if rej == "bull":
            d, _ = F.round_distance(b.low)
            if d is not None and abs(d) <= 0.002:
                out["pin_at_round"].append(i)
        if rsi[i] is not None and rsi[i] < 30:
            out["rsi_oversold"].append(i)
        r10 = _ret(bars, i, 10)
        if r10 is not None and r10 <= -0.05:
            out["fell_5pct_10bars"].append(i)
        if F.doji(b):
            out["doji"].append(i)
    sides = {"star_after_rise": -1, "engulf_bear_after_rise": -1}
    return {k: (sides.get(k, 1), v) for k, v in out.items()}


def forward(bars, idx, side, h, cost):
    """Net forward returns for events at idx: open[i+1] → close[i+h]."""
    out = []
    for i in idx:
        if i + h >= len(bars):
            continue
        r = bars[i + h].close / bars[i + 1].open - 1.0
        out.append(side * r - cost)
    return out


def stats(rets):
    n = len(rets)
    if n == 0:
        return {"n": 0}
    m = sum(rets) / n
    sd = math.sqrt(sum((r - m) ** 2 for r in rets) / (n - 1)) if n > 1 else 0.0
    srt = sorted(rets)
    return {"n": n, "mean_bp": m * 1e4, "median_bp": srt[n // 2] * 1e4,
            "hit": sum(1 for r in rets if r > 0) / n,
            "t": m / (sd / math.sqrt(n)) if sd > 0 and n > 1 else 0.0}


def block_shuffle(bars, rng, block=BLOCK):
    blocks = [bars[i:i + block] for i in range(0, len(bars), block)]
    rng.shuffle(blocks)
    return [b for blk in blocks for b in blk]


def run(series, h, cost_bps, shuffles, seed=0):
    qc = barqc.inspect(series)
    if qc["verdict"] == "blocked":
        sys.exit(f"REFUSED: barqc blocked {series.describe()}: {', '.join(qc['failed'])}")
    bars = list(series.bars)
    cost = cost_bps / 1e4
    real = rules(bars)
    base = stats([bars[i + h].close / bars[i + 1].open - 1.0 - cost
                  for i in range(LOOKBACK, len(bars) - h)])

    res = {}
    for k, (side, idx) in real.items():
        res[k] = {"side": "short" if side < 0 else "long",
                  **stats(forward(bars, idx, side, h, cost)),
                  "shuffled_means_bp": []}

    rng = random.Random(seed)
    for _ in range(shuffles):
        sh = block_shuffle(bars, rng)
        fake = rules(sh)
        for k, (side, idx) in fake.items():
            s = stats(forward(sh, idx, side, h, cost))
            if s["n"]:
                res[k]["shuffled_means_bp"].append(s["mean_bp"])

    for k, r in res.items():
        sm = r.pop("shuffled_means_bp")
        if r["n"] and sm:
            r["p"] = sum(1 for x in sm if x >= r["mean_bp"]) / len(sm)
            r["shuffled_mean_bp"] = sum(sm) / len(sm)
            r["shuffles_with_events"] = len(sm)
        else:
            r["p"] = None
    return {"symbol": series.symbol, "timeframe": series.timeframe,
            "source": series.provenance.get("source"), "bars": len(bars),
            "horizon": h, "cost_bps": cost_bps, "shuffles": shuffles,
            "unconditional": base, "rules": res, "block": BLOCK,
            "pre_registered": True, "parameters_searched": 0}


def render(r):
    L = [f"\n{'='*84}", f"NULL TEST — {r['symbol']} {r['timeframe']} · {r['bars']} bars · "
         f"hold {r['horizon']} bar(s) · {r['cost_bps']:g} bp · {r['shuffles']} block-shuffles",
         "=" * 84]
    u = r["unconditional"]
    L.append(f"\nunconditional {r['horizon']}-bar return, net: mean {u['mean_bp']:+.1f} bp, "
             f"hit {u['hit']:.1%}  (what ANY entry earns on these bars)\n")
    L.append(f"{'rule':<28}{'side':<6}{'n':>6}{'mean bp':>9}{'hit':>7}{'t':>7}"
             f"{'shuffled':>10}{'p':>7}")
    L.append("-" * 84)
    for k, s in r["rules"].items():
        if not s["n"]:
            L.append(f"{k:<28}{s['side']:<6}{0:>6}   (never fired)")
            continue
        p = f"{s['p']:.3f}" if s["p"] is not None else "  n/a"
        L.append(f"{k:<28}{s['side']:<6}{s['n']:>6}{s['mean_bp']:>9.1f}{s['hit']:>7.1%}"
                 f"{s['t']:>7.2f}{s.get('shuffled_mean_bp', float('nan')):>10.1f}{p:>7}")
    L.append("-" * 84)
    L.append("p = share of shuffles where the SAME rule did at least this well on bars "
             "where it cannot work.\nBelow 0.05 across a holdout too, with n in the "
             "hundreds, is the bar. One low p among eight rules is what eight tries "
             "look like.")
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--csv", required=True)
    ap.add_argument("--symbol", required=True)
    ap.add_argument("--timeframe", default="1d", choices=sorted(B.TIMEFRAMES))
    ap.add_argument("--source")
    ap.add_argument("--adjusted", choices=["yes", "no"])
    ap.add_argument("--horizon", type=int, default=1, help="bars held after entry")
    ap.add_argument("--cost-bps", type=float, default=5.0)
    ap.add_argument("--shuffles", type=int, default=200)
    ap.add_argument("--no-record", action="store_true")
    a = ap.parse_args()
    try:
        s = B.load_csv(a.csv, a.symbol, a.timeframe, a.source,
                       {"yes": True, "no": False}.get(a.adjusted))
    except (B.Unparseable, B.NoProvenance) as e:
        sys.exit(f"REFUSED: {e}")
    r = run(s, a.horizon, a.cost_bps, a.shuffles)
    print(render(r))
    if not a.no_record:
        ledger.record("nulltest", **r)
        print("\nrecorded to the ledger")


if __name__ == "__main__":
    main()
