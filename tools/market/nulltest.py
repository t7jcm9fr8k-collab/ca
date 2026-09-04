#!/usr/bin/env python3
"""
nulltest.py — the null exercises. Code the pattern, apply real costs, compare
it to days that look like the event days, and watch it go to zero.

WHY
    EVIDENCE.md's build-first list, item 4: these are what the stack is built
    from, they are cheap, and seeing them fail against a proper baseline IS the
    financial-literacy lesson. Every rule here is fixed in advance and written
    down below. Nothing is tuned to the data.

THE RULES (pre-registered; v2 for pin_near_round, see below)
    hammer_after_decline      bull rejection bar AND the prior 5-bar return < 0
    star_after_rise           bear rejection bar AND the prior 5-bar return > 0  (short)
    engulf_bull_after_decline bull engulfing AND prior 5-bar return < 0
    engulf_bear_after_rise    bear engulfing AND prior 5-bar return > 0          (short)
    pin_near_round            bull rejection with its low within 2.5% OF THE
                              GRID STEP of a round number ($0.25 on a $10 grid)
    rsi_oversold              RSI(14) < 30
    fell_5pct_10bars          close down >= 5% from 10 bars ago — the plain thing
                              RSI<30 is a dressed-up version of
    doji                      body <= 10% of range — a VOLATILITY claim; its
                              direction test is included so you can see it is ~50%

THE ICT SET (pre-registered 2026-09-04, v1; run because the classic set
went to zero three times and the standing instruction was "if we plateau,
try to incorporate it"). Each concept has ONE fixed definition in
features.py so that it can fail:
    fvg_bull_formed           a bullish three-bar fair value gap forms at bar i — the
                              continuation claim, entered at the next open
    fvg_bull_retest           the previous close sat above a bullish gap formed in the
                              last 20 bars; bar i trades down into it and closes back
                              above its top — the "gap as support" claim
    ob_bull_retest            the same re-entry into a bullish order block (the last
                              down bar before a >= 1-ATR displacement)
    (ICT v1, run once on 2026-09-04, had no re-entry condition on the two
    retest rules and fired on 29% of all bars. v2 adds it. Both runs count as
    trials; v1's retest rows were nulls at t = -2.2 and -1.4.)
    sweep_bull                bar i takes out the 20-bar low and closes back above it —
                              the stop-hunt reversal claim
    sweep_bear                the mirror, short
    bos_bull                  bar i closes above the last confirmed swing high, the
                              previous bar did not — the break-of-structure continuation claim

WITNESSES
    Events on consecutive or nearby days are one witness, not several: the
    same crash fires RSI<30 for a week. Events closer than EPISODE_GAP bars
    are grouped into one episode; `epis` is the number of episodes and `t_ep`
    is the t of the episode means — the money question asked of independent
    witnesses. Read t_ep before t.

    v1 of the round-number rule used 0.2% of PRICE, which on a $500 stock is
    ±$1 on a $10 grid — one price in five qualifies, so the rule was "bull
    rejection bar" wearing a hat. The 2026-09-02 SPY run used v1 and is not
    comparable with v2. Tightening a rule after seeing its results is a new
    trial and is counted as one.

THE MEASUREMENT
    For every bar where a rule fires at bar i, the trade enters at the OPEN of
    bar i+1 and exits at the CLOSE of bar i+h. No look-ahead: the rule reads
    bars 0..i only. Short rules negate the return. A flat round-trip cost is
    charged. Note that h=1 is an open-to-close (intraday) hold, not the
    close-to-close return the pattern literature usually reports.

THE BASELINE — and why the first version was wrong
    v1 shuffled the bars in blocks of 20 and re-ran the rule. With a one-bar
    horizon, bar i and bar i+1 sit in the same block 19 times in 20, so the
    (pattern, next-bar) pair the shuffle claimed to destroy was preserved for
    almost every event, and the "null" distribution was anchored on the real
    events. No p from that version was a p-value. Three reviewers found it;
    the numbers had shown it (shuffled means tracked real means) and I read
    past them.

    v2 keeps the real event set and asks the question directly: is the mean
    forward return of THESE n days unusual for n days LIKE them? "Like them"
    means matched on trailing 20-bar realized volatility — the dip rules fire
    on the wildest days in the sample, and comparing them to calm days is not
    a test of anything. Each shuffle draws n eligible bars from the same
    volatility deciles as the real events and takes their mean forward return.
    p is the share of draws that did at least as well as the real events.

READ THE t COLUMN FIRST
    t is the mean against zero, given the variance of THESE events. It is the
    number that says whether you would have made money. p says whether the
    pattern picked unusual days. With eight rules, the smallest of eight null
    p-values is expected around 0.11; one 0.05 is what eight tries look like.
    The largest single event's share of the total is printed so that one +10%
    day cannot hide inside a mean.

USAGE
    python3 nulltest.py --csv bars/SPY-1d.csv --symbol SPY --source stooq --horizon 1 --cost-bps 5
    python3 nulltest.py --csv bars/SPY-1d.csv --symbol SPY --horizon 5 --shuffles 1000 --no-vol-match
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
LOOKBACK = 5
VOL_WINDOW = 20
VOL_DECILES = 10
ROUND_TOL_OF_STEP = 0.025
RULE_VERSION = 2
ICT_VERSION = 2
ZONE_LOOKBACK = 20
EPISODE_GAP = 10
CLASSIC = ("hammer_after_decline", "star_after_rise", "engulf_bull_after_decline",
           "engulf_bear_after_rise", "pin_near_round", "rsi_oversold", "fell_5pct_10bars",
           "doji")
ICT = ("fvg_bull_formed", "fvg_bull_retest", "ob_bull_retest", "sweep_bull", "sweep_bear",
       "bos_bull")
SHORT = {"star_after_rise", "engulf_bear_after_rise", "sweep_bear"}


def _ret(bars, i, k):
    return bars[i].close / bars[i - k].close - 1.0 if i >= k else None


def ict_rules(bars):
    """{rule: [indices]} for the ICT set — each index i fires on bars 0..i only."""
    n = len(bars)
    out = {k: [] for k in ICT}
    bos = F.structure_breaks(bars)
    gaps, blocks = [], []                     # (formed_at, lo, hi), oldest first
    for i in range(2, n):
        b = bars[i]
        gaps = [g for g in gaps if i - g[0] <= ZONE_LOOKBACK]
        blocks = [o for o in blocks if i - o[0] <= ZONE_LOOKBACK]
        # retests read zones formed BEFORE this bar. v2: the previous close
        # must sit ABOVE the zone, so the bar re-enters it from above and
        # closes back out. v1 had no re-entry condition and fired on 29% of
        # all bars — "price is somewhere near a recent gap" is not a setup.
        prev = bars[i - 1].close
        if any(prev > hi and b.low <= hi and b.close > hi for _, lo, hi in gaps):
            out["fvg_bull_retest"].append(i)
        if any(prev > hi and b.low <= hi and b.close > hi for _, lo, hi in blocks):
            out["ob_bull_retest"].append(i)
        g = F.fair_value_gap(bars, i)
        if g and g[0] == "bull":
            out["fvg_bull_formed"].append(i)
            gaps.append((i, g[1], g[2]))
        o = F.order_block(bars, i)
        if o and o[0] == "bull":
            blocks.append((i, o[1], o[2]))
        sw = F.liquidity_sweep(bars, i)
        if sw == "bull":
            out["sweep_bull"].append(i)
        elif sw == "bear":
            out["sweep_bear"].append(i)
        if bos[i] == "bull":
            out["bos_bull"].append(i)
    return out


def rules(bars, which="all"):
    """{rule: (side, [indices])} — each index i fires on bars 0..i only."""
    n = len(bars)
    rsi = F.rsi_series(bars, 14)
    out = {k: [] for k in CLASSIC}
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
            step = F.round_step(b.low)
            _, nearest = F.round_distance(b.low, step)
            if step and nearest is not None and abs(b.low - nearest) <= ROUND_TOL_OF_STEP * step:
                out["pin_near_round"].append(i)
        if rsi[i] is not None and rsi[i] < 30:
            out["rsi_oversold"].append(i)
        r10 = _ret(bars, i, 10)
        if r10 is not None and r10 <= -0.05:
            out["fell_5pct_10bars"].append(i)
        if F.doji(b):
            out["doji"].append(i)
    if which in ("ict", "all"):
        ict = ict_rules(bars)
        out = ict if which == "ict" else {**out, **ict}
    return {k: (-1 if k in SHORT else 1, v) for k, v in out.items()}


def episodes(idx, gap=EPISODE_GAP):
    """Group event indices closer than `gap` bars into episodes: [[i, i, ...], ...]."""
    out = []
    for i in sorted(idx):
        if out and i - out[-1][-1] < gap:
            out[-1].append(i)
        else:
            out.append([i])
    return out


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
            "sd_bp": sd * 1e4,
            "hit": sum(1 for r in rets if r > 0) / n,
            "t": m / (sd / math.sqrt(n)) if sd > 0 and n > 1 else 0.0}


# ---------------------------------------------------------------- the null

def trailing_vol(bars, window=VOL_WINDOW):
    """Std of close-to-close returns over the previous `window` bars, per bar."""
    out = [None] * len(bars)
    rets = [None] + [bars[i].close / bars[i - 1].close - 1.0 for i in range(1, len(bars))]
    for i in range(window, len(bars)):
        w = rets[i - window + 1:i + 1]
        m = sum(w) / window
        out[i] = math.sqrt(sum((r - m) ** 2 for r in w) / (window - 1))
    return out


def vol_deciles(vol, eligible):
    """decile index per eligible bar, by rank of trailing vol among eligible bars."""
    known = sorted((vol[i], i) for i in eligible if vol[i] is not None)
    dec = {}
    for rank, (_, i) in enumerate(known):
        dec[i] = min(VOL_DECILES - 1, rank * VOL_DECILES // max(len(known), 1))
    for i in eligible:
        dec.setdefault(i, None)          # not enough history: unmatched pool
    return dec


def date_permutation_p(bars, idx, side, h, cost, shuffles, rng, vol_match=True):
    """
    p = share of draws of n bars LIKE the event bars whose mean forward return
    is at least the real events'. Returns (p, mean of the draw means in bp).
    """
    real = forward(bars, idx, side, h, cost)
    if not real or shuffles <= 0:
        return None, None
    real_mean = sum(real) / len(real)
    eligible = [i for i in range(LOOKBACK, len(bars) - h)]
    used = [i for i in idx if i + h < len(bars)]
    if vol_match:
        dec = vol_deciles(trailing_vol(bars), eligible)
        pools = {}
        for i in eligible:
            pools.setdefault(dec[i], []).append(i)
        targets = [dec.get(i) for i in used]
    hits, means = 0, []
    for _ in range(shuffles):
        if vol_match:
            draw = [rng.choice(pools[d]) for d in targets]
        else:
            draw = rng.sample(eligible, len(used))
        fr = forward(bars, draw, side, h, cost)
        m = sum(fr) / len(fr)
        means.append(m)
        if m >= real_mean:
            hits += 1
    return hits / shuffles, sum(means) / len(means) * 1e4


def run(series, h, cost_bps, shuffles, seed=0, vol_match=True, which="all"):
    qc = barqc.inspect(series)
    if qc["verdict"] == "blocked":
        sys.exit(f"REFUSED: barqc blocked {series.describe()}: {', '.join(qc['failed'])}")
    bars = list(series.bars)
    cost = cost_bps / 1e4
    rng = random.Random(seed)
    real = rules(bars, which)
    base = stats([bars[i + h].close / bars[i + 1].open - 1.0 - cost
                  for i in range(LOOKBACK, len(bars) - h)])

    res = {}
    for k, (side, idx) in real.items():
        rets = forward(bars, idx, side, h, cost)
        used = [i for i in idx if i + h < len(bars)]
        events = [{"date": bars[i].ts.strftime("%Y-%m-%d"), "ret_bp": r * 1e4}
                  for i, r in zip(used, rets)]
        s = {"side": "short" if side < 0 else "long", **stats(rets), "events": events}
        by_i = dict(zip(used, rets))
        ep_means = [sum(by_i[i] for i in ep) / len(ep) for ep in episodes(used)]
        s["episodes"] = len(ep_means)
        s["t_ep"] = stats(ep_means)["t"] if ep_means else 0.0
        if rets:
            total = sum(rets)
            big = max(events, key=lambda e: abs(e["ret_bp"]))
            s["largest_event"] = big
            s["largest_share"] = (big["ret_bp"] / (total * 1e4)) if total else None
            p, null_mean = date_permutation_p(bars, idx, side, h, cost, shuffles, rng, vol_match)
            s["p"], s["null_mean_bp"] = p, null_mean
        else:
            s["p"] = s["null_mean_bp"] = None
        res[k] = s

    return {"symbol": series.symbol, "timeframe": series.timeframe,
            "source": series.provenance.get("source"), "bars": len(bars),
            "start": bars[0].ts.strftime("%Y-%m-%d"), "end": bars[-1].ts.strftime("%Y-%m-%d"),
            "horizon": h, "cost_bps": cost_bps, "shuffles": shuffles,
            "null": "vol-matched date permutation" if vol_match else "date permutation",
            "unconditional": base, "rules": res,
            "rule_set": which, "rule_version": RULE_VERSION, "ict_version": ICT_VERSION,
            "pre_registered": True, "parameters_searched": 0,
            "episode_gap": EPISODE_GAP,
            "expected_min_p": 1.0 / (len(res) + 1), "n_rules": len(res)}


def render(r):
    L = [f"\n{'='*104}", f"NULL TEST — {r['symbol']} {r['timeframe']} · {r['bars']} bars "
         f"{r['start']} → {r['end']} · hold {r['horizon']} bar(s) · {r['cost_bps']:g} bp · "
         f"{r['shuffles']} draws · null: {r['null']} · rules {r['rule_set']} "
         f"v{r['rule_version']}/ict v{r['ict_version']}", "=" * 104]
    u = r["unconditional"]
    L.append(f"\nunconditional {r['horizon']}-bar return, net: mean {u['mean_bp']:+.1f} bp, "
             f"hit {u['hit']:.1%}  (what ANY entry earns on these bars, open→close)\n")
    L.append(f"{'rule':<27}{'side':<6}{'n':>5}{'epis':>5}{'mean bp':>9}{'sd bp':>8}{'hit':>7}"
             f"{'t':>7}{'t_ep':>7}{'null bp':>9}{'p':>7}   largest event")
    L.append("-" * 104)
    for k, s in r["rules"].items():
        if not s["n"]:
            L.append(f"{k:<27}{s['side']:<6}{0:>5}   (never fired)")
            continue
        p = f"{s['p']:.3f}" if s["p"] is not None else "  n/a"
        big = s.get("largest_event")
        share = s.get("largest_share")
        if big and share is not None and 0 < share <= 1.0:
            bigtxt = f"{big['date']} {big['ret_bp']:+.0f} bp = {share:.0%} of total"
        elif big:
            bigtxt = f"{big['date']} {big['ret_bp']:+.0f} bp (total near zero or opposite sign)"
        else:
            bigtxt = ""
        L.append(f"{k:<27}{s['side']:<6}{s['n']:>5}{s['episodes']:>5}{s['mean_bp']:>9.1f}"
                 f"{s['sd_bp']:>8.0f}{s['hit']:>7.1%}{s['t']:>7.2f}{s['t_ep']:>7.2f}"
                 f"{(s['null_mean_bp'] if s['null_mean_bp'] is not None else float('nan')):>9.1f}"
                 f"{p:>7}   {bigtxt}")
    L.append("-" * 104)
    L.append("t = mean against zero given THESE events' variance: the money question. "
             "epis = witnesses: events\ncloser than "
             f"{r['episode_gap']} bars are one episode, and t_ep is the t of the episode means "
             "— read it before t. p = share\nof draws of n volatility-matched days that did at "
             f"least this well: the pattern question. With {r['n_rules']}\nrules the smallest null p "
             f"is expected near {r['expected_min_p']:.2f}; a single 0.05 is what "
             f"{r['n_rules']} tries look like.")
    return "\n".join(L)


def render_events(r, rule):
    s = r["rules"].get(rule)
    if not s or not s.get("events"):
        return f"{rule}: no events"
    L = [f"\n{rule} — {s['n']} event(s), {s['side']}"]
    for e in s["events"]:
        L.append(f"  {e['date']}  {e['ret_bp']:+8.1f} bp")
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
    ap.add_argument("--shuffles", type=int, default=1000)
    ap.add_argument("--set", default="all", choices=["classic", "ict", "all"],
                    help="which pre-registered rule set to run")
    ap.add_argument("--no-vol-match", action="store_true",
                    help="draw comparison days from all days, not volatility-matched ones")
    ap.add_argument("--events", nargs="*", default=[],
                    help="rules whose event dates and returns to list, e.g. rsi_oversold")
    ap.add_argument("--no-record", action="store_true")
    a = ap.parse_args()
    try:
        s = B.load_csv(a.csv, a.symbol, a.timeframe, a.source,
                       {"yes": True, "no": False}.get(a.adjusted))
    except (B.Unparseable, B.NoProvenance) as e:
        sys.exit(f"REFUSED: {e}")
    r = run(s, a.horizon, a.cost_bps, a.shuffles, vol_match=not a.no_vol_match, which=a.set)
    print(render(r))
    for k in a.events:
        print(render_events(r, k))
    if not a.no_record:
        slim = {**r, "rules": {k: {kk: vv for kk, vv in v.items() if kk != "events"}
                               for k, v in r["rules"].items()}}
        ledger.record("nulltest", **slim)
        print("\nrecorded to the ledger")


if __name__ == "__main__":
    main()
