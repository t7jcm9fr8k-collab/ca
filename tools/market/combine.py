#!/usr/bin/env python3
"""
combine.py — "confluence", done the way the literature says it works, and the
way it is usually done, side by side.

TWO WAYS TO COMBINE SIGNALS
    average    equal-weight mean of pre-specified 0/1 signals → a fractional
               position. This is the shape with peer-reviewed support
               (Rapach, Strauss & Zhou 2010; Neely et al. 2014): averaging
               pre-chosen forecasts reduces estimation variance.
    and-gate   1 only when EVERY signal is 1. This is what "confluence" means
               on a chart, and it has never been tested in a journal. It
               shrinks the trade sample and raises win-rate noise, and because
               the signals are mostly transforms of the same closes,
               P(all agree | trend) ≈ P(one agrees | trend).

    Both are run on the same bars, with the same costs, and scored the same
    way, so the difference is the combination rule and nothing else.

THREE THINGS THIS FILE INSISTS ON
    1. Signals are named up front. Nothing is chosen after seeing results.
    2. A holdout. The strategy runs on the whole series (so it has its warm-up
       history) but is SCORED separately before and after --holdout-from.
    3. Every trial is counted. The best Sharpe of N tries is biased upward by
       roughly sqrt(2 ln N); the Deflated Sharpe Ratio (Bailey & López de
       Prado 2014) asks whether the best one is distinguishable from the best
       of N lucky draws. N here includes every strategy scored in this run
       plus, with --count-ledger, every prior backtest of this symbol.

USAGE
    python3 combine.py --csv bars/SPY-1d.csv --symbol SPY --source stooq \\
        --signals sma_cross:10,30 breakout:20 trend_filter:200 vwap_reclaim:20 \\
        --holdout-from 2021-01-01 --cost-bps 5
"""

import argparse
import math
import os
import sys
from statistics import NormalDist

import bars as B
import ledger
import replay
import strategies

HERE = os.path.dirname(os.path.abspath(__file__))
EULER_GAMMA = 0.5772156649015329


# ---------------------------------------------------------------- deflated sharpe

def expected_max_sharpe(n_trials, var_sr):
    """
    E[max SR] of n_trials independent zero-edge strategies whose Sharpes have
    variance var_sr — Bailey & López de Prado 2014, eq. for SR0. The number a
    "best of N" backtest has to beat before it means anything.
    """
    if n_trials <= 1 or var_sr <= 0:
        return 0.0
    N = NormalDist()
    return math.sqrt(var_sr) * ((1 - EULER_GAMMA) * N.inv_cdf(1 - 1.0 / n_trials)
                                + EULER_GAMMA * N.inv_cdf(1 - 1.0 / (n_trials * math.e)))


def deflated_sharpe(sr, T, n_trials, var_sr, skew=0.0, kurt=3.0):
    """
    P(true Sharpe > 0 | observed per-bar Sharpe sr over T bars, after N trials).

    sr is PER BAR, not annualised. Returns (probability, sr0). Read it as: a
    value near 1 means the observed Sharpe is hard to get by luck even after
    N tries; near 0.5 means it is what the best of N nothings looks like.
    """
    sr0 = expected_max_sharpe(n_trials, var_sr)
    denom = math.sqrt(max(1e-12, 1 - skew * sr + (kurt - 1) / 4.0 * sr * sr))
    z = (sr - sr0) * math.sqrt(max(T - 1, 1)) / denom
    return NormalDist().cdf(z), sr0


# ---------------------------------------------------------------- combination

def pearson(x, y):
    n = len(x)
    if n < 2:
        return None
    mx, my = sum(x) / n, sum(y) / n
    sxx = sum((a - mx) ** 2 for a in x)
    syy = sum((b - my) ** 2 for b in y)
    if sxx == 0 or syy == 0:
        return None
    return sum((a - mx) * (b - my) for a, b in zip(x, y)) / math.sqrt(sxx * syy)


def average_of(strats):
    def s(cursor):
        return sum(float(f(cursor)) for f in strats) / len(strats)
    s.__name__ = "average_" + "+".join(f.__name__ for f in strats)
    return s


def and_gate(strats):
    def s(cursor):
        return 1.0 if all(float(f(cursor)) > 0.5 for f in strats) else 0.0
    s.__name__ = "and_" + "+".join(f.__name__ for f in strats)
    return s


def run(series, specs, cost_bps, holdout_from, cash_yield=0.0, count_ledger=False):
    strats = [strategies.make(sp) for sp in specs]
    # One scoring start for every line, including the reference: the longest
    # warm-up among the signals. Otherwise a 200-day filter is scored flat
    # against a benchmark that was invested 198 bars earlier, and the AND-gate
    # "cannot fire" for a stretch nobody is told about.
    warm = max([1] + [int(getattr(f, "warmup", 0) or 0) for f in strats])
    trials = []
    for f in strats + [average_of(strats), and_gate(strats)]:
        r = replay.replay(series, f, cost_bps=cost_bps, cash_yield=cash_yield, warmup=warm)
        r["in_sample"] = replay.window_stats(r, end=holdout_from)
        r["holdout"] = replay.window_stats(r, start=holdout_from)
        trials.append(r)
    # The reference, scored the same way in the same windows from the same
    # bar. Not a trial — nobody chose it — but without it a 16% holdout return
    # in a 25% up-market reads as a result instead of as a lag.
    bench = replay.replay(series, strategies.buy_and_hold, cost_bps=cost_bps, warmup=warm)
    bench["in_sample"] = replay.window_stats(bench, end=holdout_from)
    bench["holdout"] = replay.window_stats(bench, start=holdout_from)

    # correlation of the individual signals' decisions — the "one witness in
    # five hats" number
    n = len(strats)
    corr = [[None] * n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            corr[i][j] = 1.0 if i == j else pearson(trials[i]["targets"], trials[j]["targets"])

    # how often everything agrees when at least one is on
    tg = [t["targets"] for t in trials[:n]]
    any_on = sum(1 for k in range(len(tg[0])) if any(t[k] > 0.5 for t in tg))
    all_on = sum(1 for k in range(len(tg[0])) if all(t[k] > 0.5 for t in tg))

    # deflation: N trials, variance of their in-sample per-bar Sharpes
    n_trials = len(trials)
    prior = len(ledger.events("backtest", symbol=series.symbol)) if count_ledger else 0
    n_trials += prior
    srs = [t["in_sample"]["sharpe_per_bar"] for t in trials]
    m = sum(srs) / len(srs)
    var_sr = sum((x - m) ** 2 for x in srs) / max(len(srs) - 1, 1)
    best = max(trials, key=lambda t: t["in_sample"]["sharpe_per_bar"])
    dsr, sr0 = deflated_sharpe(best["in_sample"]["sharpe_per_bar"],
                               best["in_sample"]["returns_used"], n_trials, var_sr,
                               best["in_sample"].get("skew", 0.0),
                               best["in_sample"].get("kurt", 3.0))
    return {"symbol": series.symbol, "signals": specs, "cost_bps": cost_bps,
            "cash_yield": cash_yield, "holdout_from": holdout_from,
            "trials": trials, "benchmark": bench,
            "corr": corr, "names": [f.__name__ for f in strats],
            "any_on": any_on, "all_on": all_on, "bars_scored": len(tg[0]),
            "warmup": warm, "scored_from": trials[0]["scored_from"],
            "n_trials": n_trials, "trials_in_run": len(trials), "trials_prior": prior,
            "var_sr": var_sr,
            "best": best["strategy"], "best_dsr": dsr, "best_sr0": sr0}


def render(r):
    L = [f"\n{'='*78}", f"COMBINE — {r['symbol']} · {len(r['signals'])} signals · "
         f"{r['cost_bps']:g} bp · holdout from {r['holdout_from']}", "=" * 78,
         f"scored from {r['scored_from'][:10]} (after the longest warm-up, {r['warmup']} bars), "
         f"{r['bars_scored']} live bars"]
    L.append(f"\n{'strategy':<36}{'window':<10}{'return':>9}{'sharpe':>8}{'max dd':>9}{'fills':>7}")
    L.append("-" * 78)
    for w in ("in_sample", "holdout"):
        s = r["benchmark"][w]
        if s.get("return") is not None:
            L.append(f"{'buy_and_hold (reference)':<36}{w:<10}{s['return']:>9.1%}{s['sharpe']:>8.2f}"
                     f"{s['max_drawdown']:>9.1%}{'':>7}")
    L.append("-" * 78)
    for t in r["trials"]:
        for w in ("in_sample", "holdout"):
            s = t[w]
            if s.get("return") is None:
                L.append(f"{t['strategy'][:35]:<36}{w:<10}   (no bars)")
                continue
            L.append(f"{t['strategy'][:35]:<36}{w:<10}{s['return']:>9.1%}{s['sharpe']:>8.2f}"
                     f"{s['max_drawdown']:>9.1%}{s.get('fills', 0):>7}")
    L.append("")
    L.append("signal correlation (decisions):")
    names = [n[:14] for n in r["names"]]
    L.append(" " * 16 + "".join(f"{n:>15}" for n in names))
    for i, row in enumerate(r["corr"]):
        L.append(f"{names[i]:<16}" + "".join(f"{(c if c is not None else float('nan')):>15.2f}" for c in row))
    L.append(f"\nbars with any signal on: {r['any_on']}   all on: {r['all_on']}   "
             f"({r['all_on'] / r['any_on']:.0%} of the time they can agree, they do)" if r["any_on"] else "")
    L.append(f"\ntrials counted: {r['n_trials']} ({r['trials_in_run']} in this run"
             + (f" + {r['trials_prior']} prior backtests of {r['symbol']} in the ledger" if r['trials_prior'] else "")
             + f")   best in-sample: {r['best']}")
    L.append("the Sharpe dispersion used for deflation comes from this run's trials only; the "
             "10/30, 20, 200 conventions carry\ndecades of prior search the count cannot see, "
             "and a 15-month window puts an SE of ~1.2 on every Sharpe above")
    L.append(f"expected best-of-{r['n_trials']} per-bar Sharpe under no edge: {r['best_sr0']:.4f}")
    L.append(f"deflated Sharpe (P[true SR > 0] after {r['n_trials']} tries): {r['best_dsr']:.2f}")
    L.append("read the holdout column once, and only after the in-sample column is settled")
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--csv", required=True)
    ap.add_argument("--symbol", required=True)
    ap.add_argument("--timeframe", default="1d", choices=sorted(B.TIMEFRAMES))
    ap.add_argument("--source")
    ap.add_argument("--adjusted", choices=["yes", "no"])
    ap.add_argument("--signals", nargs="+", required=True, help="strategy specs, named up front")
    ap.add_argument("--holdout-from", required=True, help="YYYY-MM-DD; scored separately")
    ap.add_argument("--cost-bps", type=float, default=5.0)
    ap.add_argument("--cash-yield", type=float, default=0.0)
    ap.add_argument("--count-ledger", action="store_true",
                    help="add this symbol's prior backtests to the trial count")
    ap.add_argument("--no-record", action="store_true")
    a = ap.parse_args()

    try:
        s = B.load_csv(a.csv, a.symbol, a.timeframe, a.source,
                       {"yes": True, "no": False}.get(a.adjusted))
    except (B.Unparseable, B.NoProvenance) as e:
        sys.exit(f"REFUSED: {e}")
    try:
        r = run(s, a.signals, a.cost_bps, a.holdout_from, a.cash_yield, a.count_ledger)
    except (replay.Blocked, KeyError, ValueError) as e:
        sys.exit(f"REFUSED: {e}")
    print(render(r))
    if not a.no_record:
        for t in r["trials"]:
            keep = {k: v for k, v in t.items() if k not in replay.LEDGER_EXCLUDE}
            ledger.record("backtest", combine_run=True, **keep)
        ledger.record("combine", symbol=r["symbol"], signals=r["signals"],
                      n_trials=r["n_trials"], best=r["best"], best_dsr=r["best_dsr"],
                      best_sr0=r["best_sr0"], any_on=r["any_on"], all_on=r["all_on"],
                      holdout_from=r["holdout_from"], cost_bps=r["cost_bps"])
        print(f"\nrecorded {len(r['trials'])} backtests and the combine summary to the ledger")


if __name__ == "__main__":
    main()
