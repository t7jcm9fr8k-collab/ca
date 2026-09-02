#!/usr/bin/env python3
"""
intraday.py — the one result in EVIDENCE.md with documented after-cost edge,
pre-registered, with its own null and its own holdout.

THE RULE, AS PUBLISHED
    Gao, Han, Li & Zhou 2018 (J. Financial Economics): on SPY, the return of
    the first half-hour (09:30–10:00) predicts the return of the last
    half-hour (15:30–16:00). Baltussen, Da, Lammers & Martens 2021 (JFE)
    find the same across 60+ futures markets using the open-to-15:30 return.
    Mechanism: end-of-day hedging by option dealers and leveraged-ETF
    rebalancing is flow that must trade regardless of price.

    Both rules are implemented EXACTLY as published and nothing else is tried.
    No parameter is searched. That is what "pre-registered" means, and it is
    the only reason a positive result here would mean anything.

    Published samples end in 2020. Whether the effect survived publication is
    the open question — and the reason --holdout-from defaults to 2021-01-01.
    Reproduce the paper on the in-sample years; then read the holdout, once.

WHAT IT IS NOT
    Not the opening-range breakout. Not "negative gamma = trend day". Those
    are different trades with no test, and the vocabulary that suggests them
    is exactly what EVIDENCE.md warns about.

NO LOOK-AHEAD, BY CONSTRUCTION
    The decision uses closes up to 15:29. The fill is the OPEN of the 15:30
    bar. The exit is the close of the session's last bar. A session missing
    its 09:30 bar, its 15:30 bar, or ending before 15:55 is skipped and
    counted, never patched.

THE NULL
    A permutation test: shuffle the predictor signs across sessions, keep
    everything else, recompute the mean trade return, repeat. The p-value is
    the fraction of shuffles that did as well as the real pairing. This is
    the right baseline for "does the morning predict the afternoon", because
    it keeps the afternoon returns exactly as they were.

TRIAL 3 — THE OFFICIAL CLOSE
    IEX has no closing cross for SPY, so on that feed the exit is the last IEX
    print before 16:00 and the closing auction — which the papers' last-half-
    hour return includes — is unobserved. --close-from joins a daily CSV whose
    closes ARE official (Stooq's are consolidated) by date and uses that as the
    exit: entry still the 15:30 bar's open on IEX, exit the official close.
    Pre-registered 2026-09-02 as trial 3, rule first30, nothing else changed.
    Sessions with no official close for their date are skipped and counted.
    The two feeds can differ by a cent or so at any instant (~0.2 bp); that is
    in not_modelled.

USAGE
    python3 intraday.py --csv bars/SPY-1m.csv --symbol SPY --rule first30 --cost-bps 2
    python3 intraday.py --csv bars/SPY-1m.csv --symbol SPY --rule first30 \
                        --close-from bars/SPY-1d.csv --close-source stooq
    python3 intraday.py --synth 600 --effect 0.4          # planted effect, offline
    python3 intraday.py --synth 600 --effect 0.0          # no effect: expect p ~ 0.5
"""

import argparse
import datetime as dt
import math
import os
import random
import sys

import bars as B
import barqc
import ledger

HERE = os.path.dirname(os.path.abspath(__file__))

RULES = {
    "first30": "sign of the 09:30–10:00 return (Gao, Han, Li & Zhou 2018)",
    "open_to_1530": "sign of the 09:30–15:30 return (Baltussen et al. 2021)",
}
MIN_BARS = 312                  # 80% of 390, the same line barqc draws; fewer is skipped
BASIS_TOLERANCE = 0.01          # official close vs this feed's last print: cents, never percent
PUBLISHED_BP = 2.7              # Gao et al. 2018, SPY: roughly 2.5–3 bp per session gross
T_OPEN, T_10, T_1530, T_LAST = (dt.time(9, 30), dt.time(10, 0),
                                dt.time(15, 30), dt.time(15, 55))
SESSIONS_PER_YEAR = 252


def _et():
    try:
        from zoneinfo import ZoneInfo
        return ZoneInfo("America/New_York")
    except Exception as e:
        sys.exit(f"REFUSED: no timezone database ({type(e).__name__}); cannot "
                 f"place minute bars in the New York session")


def sessions(series):
    """[(date, [(local_dt, bar), ...])] for the regular session, sorted."""
    tz = _et()
    by = {}
    for b in series.bars:
        loc = b.ts.astimezone(tz)
        if loc.time() < T_OPEN or loc.time() >= dt.time(16, 0):
            continue
        by.setdefault(loc.date(), []).append((loc, b))
    return [(d, sorted(v, key=lambda x: x[0])) for d, v in sorted(by.items())]


def measure(pts):
    """
    One session → the three returns the rules need, or None with a reason.
    Uses only what was known at each moment: closes before 10:00 and before
    15:30 for the predictors; the 15:30 bar's OPEN for the fill.
    """
    if len(pts) < MIN_BARS:
        return None, f"{len(pts)} bars"
    if pts[0][0].time() != T_OPEN:
        return None, "no 09:30 bar"
    if pts[-1][0].time() < T_LAST:
        return None, f"ends {pts[-1][0]:%H:%M}"
    open_930 = pts[0][1].open
    c_10 = c_1530 = None
    bar_1530 = None
    for loc, b in pts:
        t = loc.time()
        if t < T_10:
            c_10 = b.close
        if t < T_1530:
            c_1530 = b.close
        elif bar_1530 is None:
            bar_1530 = b
    if c_10 is None or c_1530 is None or bar_1530 is None:
        return None, "missing 10:00 or 15:30"
    fill_at = next(loc for loc, b in pts if b is bar_1530).time()
    return {"date": pts[0][0].date().isoformat(),
            "r_first30": c_10 / open_930 - 1.0,
            "r_open_to_1530": c_1530 / open_930 - 1.0,
            "open_1530": bar_1530.open,
            "last_print": pts[-1][1].close,
            "r_last30": pts[-1][1].close / bar_1530.open - 1.0,
            "fill_slipped": fill_at != T_1530,        # the 15:30 minute was missing
            "exit_time": pts[-1][0].time().isoformat(timespec="minutes")}, None


def trades(rows, rule, cost_bps):
    """Per-session signed trade returns, net of a round-trip cost."""
    key = "r_first30" if rule == "first30" else "r_open_to_1530"
    cost = cost_bps / 1e4
    out = []
    for r in rows:
        sgn = (r[key] > 0) - (r[key] < 0)
        if sgn == 0:
            continue
        out.append({"date": r["date"], "side": sgn,
                    "gross": sgn * r["r_last30"],
                    "ret": sgn * r["r_last30"] - cost})
    return out


def stats(tr):
    n = len(tr)
    if n == 0:
        return {"n": 0}
    rets = [t["ret"] for t in tr]
    gross = [t.get("gross", t["ret"]) for t in tr]
    m = sum(rets) / n
    mg = sum(gross) / n
    sd = math.sqrt(sum((r - m) ** 2 for r in rets) / (n - 1)) if n > 1 else 0.0
    se = sd / math.sqrt(n) if n > 1 else 0.0
    return {"n": n, "mean_bp": m * 1e4, "gross_bp": mg * 1e4, "se_bp": se * 1e4,
            "ci95_bp": ((mg - 1.96 * se) * 1e4, (mg + 1.96 * se) * 1e4),
            "hit_net": sum(1 for r in rets if r > 0) / n,
            "hit_gross": sum(1 for r in gross if r > 0) / n,
            "t": m / se if se > 0 else 0.0,
            "t_gross": mg / se if se > 0 else 0.0,
            "annualised": m * SESSIONS_PER_YEAR,
            "sharpe": (m / sd) * math.sqrt(SESSIONS_PER_YEAR) if sd > 0 else 0.0,
            "worst": min(rets), "best": max(rets)}


def permutation_p(rows, rule, cost_bps, shuffles, seed=0):
    """Fraction of sign-shuffles whose mean trade return >= the real one."""
    real = stats(trades(rows, rule, cost_bps)).get("mean_bp", 0.0)
    key = "r_first30" if rule == "first30" else "r_open_to_1530"
    rng = random.Random(seed)
    preds = [r[key] for r in rows]
    hits = 0
    for _ in range(shuffles):
        rng.shuffle(preds)
        fake = [{**r, key: p} for r, p in zip(rows, preds)]
        if stats(trades(fake, rule, cost_bps)).get("mean_bp", 0.0) >= real:
            hits += 1
    return hits / shuffles if shuffles else None


def by_year(tr):
    years = {}
    for t in tr:
        years.setdefault(t["date"][:4], []).append(t)
    return {y: stats(v) for y, v in sorted(years.items())}


def official_closes(daily):
    """{'YYYY-MM-DD': close} from a daily Series whose closes are official."""
    return {b.ts.strftime("%Y-%m-%d"): b.close for b in daily.bars}


def run(series, rule, cost_bps, holdout_from, shuffles, published_bp=PUBLISHED_BP,
        close_map=None, close_source=None):
    qc = barqc.inspect(series)
    if qc["verdict"] == "blocked":
        sys.exit(f"REFUSED: barqc blocked {series.describe()}: {', '.join(qc['failed'])}")
    rows, skipped = [], {}
    for d, pts in sessions(series):
        m, why = measure(pts)
        if m:
            rows.append(m)
        else:
            skipped[why] = skipped.get(why, 0) + 1
    if not rows:
        sys.exit("REFUSED: no complete regular sessions in these bars")
    exit_price = "last regular-session print on this feed"
    if close_map is not None:
        joined, dropped, gaps = [], 0, []
        for r in rows:
            oc = close_map.get(r["date"])
            if oc is None:
                dropped += 1
                continue
            gaps.append(abs(oc / r["last_print"] - 1.0))
            joined.append({**r, "r_last30": oc / r["open_1530"] - 1.0, "official_close": oc})
        skipped["no official close for the date"] = dropped
        if not joined:
            sys.exit("REFUSED: no session had an official close for its date — check the dates line up")
        # The official close and this feed's last print are the same instrument
        # a minute apart; they differ by cents. A dividend-adjusted file differs
        # by the cumulative dividends since — percent, growing with age — and
        # joining it would manufacture a last-half-hour return out of thin air.
        med = sorted(gaps)[len(gaps) // 2]
        if med > BASIS_TOLERANCE:
            sys.exit(f"REFUSED: the closes in --close-from are not on the same price basis as "
                     f"the minute bars — median gap {med:.2%} against this feed's last print, "
                     f"tolerance {BASIS_TOLERANCE:.1%}. A dividend-adjusted series looks exactly "
                     f"like this. Trial 3 needs RAW official closes (Stooq, or yahoo without "
                     f"--adjusted-close).")
        rows = joined
        exit_price = (f"official close from {close_source or 'daily file'} (trial 3); "
                      f"median gap to this feed's last print {med:.3%}")

    ins = [r for r in rows if r["date"] < holdout_from]
    out = [r for r in rows if r["date"] >= holdout_from]
    slipped = sum(1 for r in rows if r.get("fill_slipped"))
    src = str(series.provenance.get("source", "")).lower()
    feed = str(series.provenance.get("feed", "")).lower()
    iex = "alpaca" in src or "iex" in feed or "iex" in src
    not_modelled = ("partial fills, intraday slippage beyond the flat cost, "
                    "borrow for the short side")
    if close_map is not None:
        not_modelled += ("; entry on this feed's 15:30 print, exit on the official close from "
                         "another feed — the two can differ by about a cent at any instant (~0.2 bp)")
    elif iex:
        not_modelled += ("; THE CLOSING AUCTION — IEX has no closing cross for SPY, so the "
                         "exit is the last IEX print before 16:00, not the official close. "
                         "The published last-half-hour return includes the auction print. "
                         "--close-from closes this gap.")
    # The published samples run 1993–2013 (Gao et al.) and 1974–2020
    # (Baltussen et al.). A feed that begins after 2019 cannot reproduce them;
    # its "< holdout" window is just more of the post-publication period, and
    # must not be read as "the paper checks out".
    reproduction = rows[0]["date"] <= "2019-01-01"
    res = {"strategy": f"intraday_{rule}" + ("_official_close" if close_map is not None else ""),
           "rule": RULES[rule] + (" · exit at the official close" if close_map is not None else ""),
           "exit_price": exit_price, "trial": 3 if close_map is not None else None,
           "symbol": series.symbol, "timeframe": series.timeframe,
           "source": series.provenance.get("source"),
           "data_start": rows[0]["date"], "data_end": rows[-1]["date"],
           "reproduction_possible": reproduction,
           "sessions": len(rows), "skipped": skipped, "cost_bps": cost_bps,
           "holdout_from": holdout_from,
           "all": stats(trades(rows, rule, cost_bps)),
           "in_sample": stats(trades(ins, rule, cost_bps)),
           "holdout": stats(trades(out, rule, cost_bps)),
           "by_year": by_year(trades(rows, rule, cost_bps)),
           "p_all": permutation_p(rows, rule, cost_bps, shuffles),
           "p_holdout": permutation_p(out, rule, cost_bps, shuffles) if len(out) >= 30 else None,
           "shuffles": shuffles, "fills_slipped_past_1530": slipped,
           "published_bp": published_bp,
           "not_modelled": not_modelled,
           "pre_registered": True, "parameters_searched": 0}
    a = res["all"]
    if a.get("n", 0) > 1:
        lo, hi = a["ci95_bp"]
        res["published_excluded"] = hi < published_bp
        res["power_note"] = (f"gross {a['gross_bp']:+.2f} ± {a['se_bp']:.2f} bp/session "
                             f"(95% CI {lo:+.2f} to {hi:+.2f}); the published effect of about "
                             f"{published_bp:+.1f} bp/session is "
                             + ("EXCLUDED by this sample" if hi < published_bp else "not excluded"))
    return res


def render(r):
    L = [f"\n{'='*72}", f"INTRADAY — {r['symbol']} · {r['rule']}", "=" * 72,
         f"exit: {r['exit_price']}",
         f"data {r['data_start']} → {r['data_end']}: sessions {r['sessions']}, "
         f"skipped {sum(r['skipped'].values())} "
         f"({', '.join(f'{v} {k}' for k, v in r['skipped'].items()) or 'none'}), "
         f"cost {r['cost_bps']:g} bp round trip"]
    if not r["reproduction_possible"]:
        L.append(f"NOTE  the published samples end in 2020; this feed begins "
                 f"{r['data_start']}. The '< {r['holdout_from']}' row is NOT a "
                 f"reproduction of the papers — it is {r['in_sample'].get('n', 0)} "
                 f"sessions of the same post-publication period.")
    L.append("")
    L.append(f"{'window':<14}{'n':>6}{'gross bp':>10}{'± se':>7}{'net bp':>8}{'hit(gross)':>11}{'t(gross)':>9}{'ann. net':>10}")
    L.append("-" * 78)
    for name, s in (("all", r["all"]), (f"< {r['holdout_from']}", r["in_sample"]),
                    (f">= {r['holdout_from']}", r["holdout"])):
        if s.get("n"):
            L.append(f"{name:<14}{s['n']:>6}{s['gross_bp']:>10.2f}{s['se_bp']:>7.2f}{s['mean_bp']:>8.2f}"
                     f"{s['hit_gross']:>11.1%}{s['t_gross']:>9.2f}{s['annualised']:>10.1%}")
        else:
            L.append(f"{name:<14}{0:>6}   (no sessions)")
    L.append("")
    L.append(f"{'year':<14}{'n':>6}{'gross bp':>10}{'± se':>7}{'net bp':>8}{'hit(gross)':>11}")
    L.append("-" * 56)
    for y, s in r["by_year"].items():
        L.append(f"{y:<14}{s['n']:>6}{s['gross_bp']:>10.2f}{s['se_bp']:>7.2f}{s['mean_bp']:>8.2f}{s['hit_gross']:>11.1%}")
    L.append("")
    if r.get("power_note"):
        L.append(r["power_note"])
    if r.get("fills_slipped_past_1530"):
        L.append(f"{r['fills_slipped_past_1530']} session(s) had no 15:30 bar; the fill moved to the "
                 f"next bar's open (later, never earlier)")
    L.append(f"permutation null, {r['shuffles']} shuffles: p = {r['p_all']:.3f} (all)"
             + (f", p = {r['p_holdout']:.3f} (holdout)" if r["p_holdout"] is not None
                else ", holdout too short for a p-value"))
    L.append(f"not modelled: {r['not_modelled']}")
    L.append("pre-registered: the published rule, nothing searched")
    return "\n".join(L)


# ---------------------------------------------------------------- synthetic

def synth(n_sessions=600, effect=0.0, seed=7, start=dt.date(2024, 1, 2),
          symbol="SYN"):
    """
    Regular-session minute bars with a PLANTED last-half-hour drift equal to
    `effect` x sign(first-30-min return) x 8 bp. effect=0 is the null. Used by
    the tests to prove the measurement finds what is there and nothing else.
    """
    tz = _et()
    rng = random.Random(seed)
    days = barqc.sessions_between(start, start + dt.timedelta(days=n_sessions * 2))[:n_sessions]
    p, out = 400.0, []
    for d in days:
        first30 = None
        for k in range(390):
            loc = dt.datetime.combine(d, T_OPEN, tzinfo=tz) + dt.timedelta(minutes=k)
            drift = 0.0
            if k >= 360 and first30 is not None:
                drift = effect * ((first30 > 0) - (first30 < 0)) * 0.0008 / 30
            o = p
            c = o * (1 + drift + rng.gauss(0, 0.0004))
            hi = max(o, c) * (1 + abs(rng.gauss(0, 0.0002)))
            lo = min(o, c) * (1 - abs(rng.gauss(0, 0.0002)))
            out.append(B.Bar(loc.astimezone(B.UTC), o, hi, lo, c, rng.randint(500, 5000)))
            p = c
            if k == 29:
                first30 = p / out[-30].open - 1
    return B.Series(symbol, "1m", out, {"source": "synthetic-intraday",
                                        "fetched_at": dt.datetime.now(B.UTC).isoformat(timespec="seconds"),
                                        "adjusted": True, "effect": effect, "seed": seed})


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--csv")
    ap.add_argument("--symbol")
    ap.add_argument("--source")
    ap.add_argument("--rule", choices=sorted(RULES), default="first30")
    ap.add_argument("--cost-bps", type=float, default=2.0,
                    help="round-trip cost in bp (SPY: 1–3 is realistic)")
    ap.add_argument("--holdout-from", default="2021-01-01",
                    help="published samples end 2020; score this range separately")
    ap.add_argument("--shuffles", type=int, default=1000)
    ap.add_argument("--published-bp", type=float, default=PUBLISHED_BP,
                    help="the published gross effect per session, for the power statement")
    ap.add_argument("--close-from", help="daily CSV with OFFICIAL closes; used as the exit (trial 3)")
    ap.add_argument("--close-source", help="where that daily file came from, e.g. stooq; recorded")
    ap.add_argument("--synth", type=int, help="generate N synthetic sessions instead of loading")
    ap.add_argument("--effect", type=float, default=0.0)
    ap.add_argument("--no-record", action="store_true")
    a = ap.parse_args()

    if a.synth:
        s = synth(a.synth, a.effect)
    else:
        if not (a.csv and a.symbol):
            ap.error("--csv and --symbol are required (or --synth N)")
        try:
            s = B.load_csv(a.csv, a.symbol, "1m", a.source)
        except (B.Unparseable, B.NoProvenance) as e:
            sys.exit(f"REFUSED: {e}")
    close_map = None
    if a.close_from:
        if not a.close_source:
            ap.error("--close-source is required with --close-from, so the ledger records where the closes came from")
        try:
            daily = B.load_csv(a.close_from, a.symbol or s.symbol, "1d", a.close_source)
        except (B.Unparseable, B.NoProvenance) as e:
            sys.exit(f"REFUSED: {e}")
        close_map = official_closes(daily)
    r = run(s, a.rule, a.cost_bps, a.holdout_from, a.shuffles, a.published_bp,
            close_map, a.close_source)
    print(render(r))
    if not a.no_record:
        ledger.record("backtest", **{k: v for k, v in r.items() if k != "by_year"},
                      **{"return": r["all"].get("annualised"), "bars": r["sessions"]})
        print("\nrecorded to the ledger")


if __name__ == "__main__":
    main()
