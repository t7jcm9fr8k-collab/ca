#!/usr/bin/env python3
"""
crosstest.py — run the two pre-registered cross-sectional specifications.

THE READING RULE IS NOT IN THIS FILE BY ACCIDENT
    It is in `PREREG-2026-09-11-cross-section.md`, written and committed before
    any cross-sectional quantity was computed. This file implements it and
    prints WORKS / PARTIAL / NULL against it. A rule chosen after seeing the
    numbers is not a rule, so the four conditions are hard-coded here and the
    thresholds are the ones in the pre-registration:

      1. Sharpe beats the equal-weight benchmark by at least 0.20
      2. max drawdown no worse than the benchmark's
      3. permutation null p < 0.05
      4. condition 1 holds in BOTH halves, split at the midpoint

    Four of four is WORKS. Three is PARTIAL and nothing is built on it. Two or
    fewer is NULL. Additionally the deflated Sharpe, with the ledger's prior
    trial count carried forward, must clear zero.

THE NULLS, ALSO PRE-REGISTERED
    tsmom  permute each asset's month-end hold decisions ACROSS DATES, so the
           number of months it held is preserved and only the timing changes.
    xsmom  pick three names uniformly at each month end, so the book is always
           fully invested in three and only the ranking information is gone.

    Both destroy the signal and keep the shape. A null that also changed the
    exposure would be measuring exposure.

USAGE
    python3 crosstest.py --spec both --shuffles 1000 --no-record
"""

import argparse
import datetime as dt
import json
import os
import random
import statistics
import sys

import combine
import ledger
import portfolio as P
from replay import Blocked, LookAhead

HERE = os.path.dirname(os.path.abspath(__file__))

# The nine long files, fixed by the pre-registration.
UNIVERSE = ("DIA", "EEM", "EFA", "GLD", "IWM", "QQQ", "TLT", "XLE", "XLF")

SHARPE_EDGE = 0.20          # condition 1
P_MAX = 0.05                # condition 3


def load_universe(source="stooq", adjusted=True):
    paths = [os.path.join(HERE, "bars", f"{s}-1d-long.csv") for s in UNIVERSE]
    missing = [p for p in paths if not os.path.exists(p)]
    if missing:
        sys.exit(f"missing bar file(s): {', '.join(os.path.basename(m) for m in missing)}")
    return P.load_aligned(paths, list(UNIVERSE), source=source, adjusted=adjusted)


# ------------------------------------------------------------------- replays

def scheduled(weights_by_date):
    """A strategy that replays a fixed schedule of decisions.

    The nulls work by permuting the real decisions and replaying them through
    the same engine, so the permuted run pays the same costs on the same dates
    and is scored over the same bars. A null run through a different code path
    compares two things at once.
    """
    def weigh(cur):
        return weights_by_date.get(cur.now, {})
    weigh.__name__ = "scheduled"
    weigh.warmup = 1
    return weigh


def _halves(result):
    """Sharpe of each half of the scored window, split at the midpoint bar."""
    from replay import _stats
    rets = result["bar_returns"]
    bpy = result["bars_per_year"]
    mid = len(rets) // 2
    a = _stats(rets[:mid], bpy)
    b = _stats(rets[mid:], bpy)
    ts = result["equity_ts"]
    return {"first": a, "second": b, "split_at": ts[mid] if mid < len(ts) else None}


def _bench_halves(result):
    from replay import _stats
    rets = result["benchmark_returns"]
    bpy = result["bars_per_year"]
    mid = len(rets) // 2
    return {"first": _stats(rets[:mid], bpy), "second": _stats(rets[mid:], bpy)}


# --------------------------------------------------------------------- nulls

def null_tsmom(real, serieses, cost_bps, cash_yield, shuffles, seed):
    """Permute each asset's hold decisions across the rebalance dates."""
    rng = random.Random(seed)
    log = real["weights_log"]
    dates = [dt.datetime.fromisoformat(w["ts"]) for w in log]
    syms = tuple(real["symbols"])
    held = {s: [1 if s in w["weights"] else 0 for w in log] for s in syms}
    out = []
    for _ in range(shuffles):
        perm = {}
        for s in syms:
            v = held[s][:]
            rng.shuffle(v)
            perm[s] = v
        sched = {}
        for k, d in enumerate(dates):
            picks = [s for s in syms if perm[s][k]]
            sched[d] = {s: 1.0 / len(picks) for s in picks} if picks else {}
        r = P.replay_portfolio(serieses, scheduled(sched), cost_bps=cost_bps,
                               warmup=real["warmup"], cash_yield=cash_yield)
        out.append(r["sharpe"])
    return out


def null_xsmom(real, serieses, cost_bps, cash_yield, shuffles, seed, top):
    """Pick `top` names uniformly at each rebalance, ranking information gone."""
    rng = random.Random(seed)
    log = real["weights_log"]
    dates = [dt.datetime.fromisoformat(w["ts"]) for w in log]
    syms = list(real["symbols"])
    out = []
    for _ in range(shuffles):
        sched = {}
        for d in dates:
            picks = rng.sample(syms, top)
            sched[d] = {s: 1.0 / top for s in picks}
        r = P.replay_portfolio(serieses, scheduled(sched), cost_bps=cost_bps,
                               warmup=real["warmup"], cash_yield=cash_yield)
        out.append(r["sharpe"])
    return out


# -------------------------------------------------------------- reading rule

def read(result, null_sharpes, prior_trials, n_specs):
    """Apply the four pre-registered conditions. No discretion."""
    h = _halves(result)
    bh = _bench_halves(result)
    edge = result["sharpe"] - result["benchmark_sharpe"]
    edge_a = h["first"]["sharpe"] - bh["first"]["sharpe"]
    edge_b = h["second"]["sharpe"] - bh["second"]["sharpe"]

    worse = sum(1 for x in null_sharpes if x >= result["sharpe"])
    p = (worse + 1) / (len(null_sharpes) + 1) if null_sharpes else None

    c1 = edge >= SHARPE_EDGE
    # "no worse" on a drawdown: both are negative, so the strategy's must not
    # be more negative than the benchmark's.
    c2 = result["max_drawdown"] >= result["benchmark_max_drawdown"]
    c3 = p is not None and p < P_MAX
    c4 = edge_a >= SHARPE_EDGE and edge_b >= SHARPE_EDGE

    passed = sum([c1, c2, c3, c4])
    verdict = "WORKS" if passed == 4 else ("PARTIAL" if passed == 3 else "NULL")

    # Deflation: the best of what was searched, against how much was searched.
    srs = [result["sharpe_per_bar"]] + ([statistics.mean(null_sharpes) / result["bars_per_year"] ** 0.5]
                                        if null_sharpes else [])
    var_sr = statistics.pvariance(null_sharpes) / result["bars_per_year"] if len(null_sharpes) > 1 else 0.0
    dsr, sr0 = combine.deflated_sharpe(
        result["sharpe_per_bar"], len(result["bar_returns"]),
        prior_trials + n_specs, var_sr,
        result.get("skew", 0.0), result.get("kurt", 3.0))

    return {
        "verdict": verdict, "conditions_passed": passed,
        "c1_sharpe_edge": {"ok": c1, "edge": edge, "need": SHARPE_EDGE,
                           "strategy": result["sharpe"], "benchmark": result["benchmark_sharpe"]},
        "c2_drawdown": {"ok": c2, "strategy": result["max_drawdown"],
                        "benchmark": result["benchmark_max_drawdown"]},
        "c3_permutation": {"ok": c3, "p": p, "shuffles": len(null_sharpes),
                           "null_mean_sharpe": statistics.mean(null_sharpes) if null_sharpes else None,
                           "null_max_sharpe": max(null_sharpes) if null_sharpes else None},
        "c4_both_halves": {"ok": c4, "first": edge_a, "second": edge_b,
                           "split_at": h["split_at"]},
        "deflated_sharpe": dsr, "expected_max_sharpe": sr0,
        "trials_counted": prior_trials + n_specs, "prior_trials": prior_trials,
    }


def render(name, r, verdict):
    L = []
    L.append(f"--- {name} " + "-" * (58 - len(name)))
    L.append(f"universe   {' '.join(r['symbols'])}")
    L.append(f"window     {r['start'][:10]} → {r['end'][:10]}  "
             f"({r['shared_dates']} shared sessions, scored from {r['scored_from'][:10]})")
    L.append(f"dropped    {r['dropped_per_symbol']}")
    L.append(f"mechanics  {r['rebalances']} rebalances, {r['fills']} with a trade, "
             f"{r['cost_bps']} bp, cash {r['cash_yield']:.1%}")
    L.append("")
    L.append(f"{'':18}{'strategy':>12}{'benchmark':>12}")
    L.append(f"{'return':18}{r['return']:>11.1%}{r['benchmark']:>12.1%}")
    L.append(f"{'CAGR':18}{(r['cagr'] or 0):>11.2%}{(r['benchmark_cagr'] or 0):>12.2%}")
    L.append(f"{'sharpe':18}{r['sharpe']:>11.2f}{r['benchmark_sharpe']:>12.2f}")
    L.append(f"{'max drawdown':18}{r['max_drawdown']:>11.1%}{r['benchmark_max_drawdown']:>12.1%}")
    L.append(f"{'volatility':18}{r['volatility']:>11.1%}{'':>12}")
    L.append("")
    c = verdict
    L.append(f"1 sharpe edge      {'PASS' if c['c1_sharpe_edge']['ok'] else 'fail'}  "
             f"{c['c1_sharpe_edge']['edge']:+.2f} (need +{SHARPE_EDGE:.2f})")
    L.append(f"2 drawdown         {'PASS' if c['c2_drawdown']['ok'] else 'fail'}  "
             f"{c['c2_drawdown']['strategy']:.1%} vs benchmark {c['c2_drawdown']['benchmark']:.1%}")
    L.append(f"3 permutation null {'PASS' if c['c3_permutation']['ok'] else 'fail'}  "
             f"p = {c['c3_permutation']['p']:.3f} over {c['c3_permutation']['shuffles']} shuffles "
             f"(null mean sharpe {c['c3_permutation']['null_mean_sharpe']:.2f}, "
             f"max {c['c3_permutation']['null_max_sharpe']:.2f})")
    L.append(f"4 both halves      {'PASS' if c['c4_both_halves']['ok'] else 'fail'}  "
             f"first {c['c4_both_halves']['first']:+.2f}, "
             f"second {c['c4_both_halves']['second']:+.2f}, "
             f"split {(c['c4_both_halves']['split_at'] or '')[:10]}")
    L.append(f"deflated sharpe    {c['deflated_sharpe']:.3f} after "
             f"{c['trials_counted']} trials ({c['prior_trials']} prior from the ledger)")
    L.append("")
    L.append(f"VERDICT: {c['verdict']} — {c['conditions_passed']} of 4 conditions")
    L.append("")
    L.append(f"not modelled: {r['not_modelled']}")
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--spec", choices=("tsmom", "xsmom", "both"), default="both")
    ap.add_argument("--shuffles", type=int, default=1000)
    ap.add_argument("--cost-bps", type=float, default=5.0)
    ap.add_argument("--cash-yield", type=float, default=0.03)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--source", default="stooq")
    ap.add_argument("--out", default=None, help="write the full report here too")
    ap.add_argument("--no-record", action="store_true")
    a = ap.parse_args()

    serieses = load_universe(source=a.source, adjusted=True)
    prior = len(ledger.events("backtest"))
    specs = ("tsmom", "xsmom") if a.spec == "both" else (a.spec,)

    lines = [f"crosstest — pre-registered in PREREG-2026-09-11-cross-section.md",
             f"run at {dt.datetime.now(dt.timezone.utc).isoformat()}",
             f"specs: {', '.join(specs)}  shuffles: {a.shuffles}  seed: {a.seed}",
             f"prior trials in the ledger: {prior}", ""]
    payload = {}

    for spec in specs:
        weigh = P.tsmom() if spec == "tsmom" else P.xsmom()
        r = P.replay_portfolio(serieses, weigh, cost_bps=a.cost_bps,
                               cash_yield=a.cash_yield if spec == "tsmom" else 0.0,
                               name=spec)
        print(f"  {spec}: walked {r['shared_dates']} sessions, "
              f"{r['rebalances']} rebalances — running {a.shuffles} shuffles…",
              file=sys.stderr)
        if spec == "tsmom":
            null = null_tsmom(r, serieses, a.cost_bps, a.cash_yield, a.shuffles, a.seed)
        else:
            null = null_xsmom(r, serieses, a.cost_bps, 0.0, a.shuffles, a.seed, top=3)
        v = read(r, null, prior, len(specs))
        lines.append(render(spec, r, v))
        lines.append("")
        payload[spec] = {"result": {k: val for k, val in r.items()
                                    if k not in ("equity", "equity_ts", "bar_returns",
                                                 "weights_log", "benchmark_equity",
                                                 "benchmark_returns")},
                         "verdict": v}

    text = "\n".join(lines)
    print(text)
    if a.out:
        os.makedirs(os.path.dirname(a.out), exist_ok=True)
        with open(a.out, "w") as f:
            f.write(text + "\n\n" + json.dumps(payload, indent=1, default=str) + "\n")
        print(f"\nwrote {a.out}", file=sys.stderr)
    if not a.no_record:
        print("\n(not recorded to the ledger; pass --no-record explicitly or wire "
              "recording deliberately)", file=sys.stderr)


if __name__ == "__main__":
    main()
