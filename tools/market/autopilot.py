#!/usr/bin/env python3
"""
autopilot.py — the unattended daily loop. Fetch, check, decide, reconcile,
record. Runs on the Mac on a schedule; PAPER by default; live only when told
so in words, and only after paper runs have filled.

STATUS: UNVERIFIED. Written 2026-09-04 in a cloud session whose permission
    guard refused to run its checks or its dry run. It is committed so that
    Daniel can read it, not so that it can be scheduled: run test_tools.py
    with the autopilot section restored (see the plan record) and a
    --dry-run on the Mac before this file is ever pointed at a broker.
    Nothing in the README schedules it.

WHAT "MONITORING THE MARKET" MEANS HERE
    The rules this pipeline has measured are DAILY rules: they read the close
    and act at the next open. Watching them tick by tick adds nothing — the
    one intraday rule with a published edge was excluded on this feed at four
    standard errors — so the honest cadence is one run after each close.
    Alpaca queues a market order sent after hours and fills it at the next
    open, which is exactly the fill replay.py assumes.

WHAT ONE RUN DOES, PER SYMBOL IN THE UNIVERSE
    1. fetch fresh daily bars and write them to bars/
    2. barqc: BLOCKED or stale bars → skip, say why, touch nothing
    3. the strategy's target after the last close, through the cursor
    4. the broker's current position
    5. reconcile: long wanted and flat → BUY qty; flat wanted and long → SELL
       all; already aligned → nothing. Never adds to a position.
    6. the gate, exactly as run.py applies it: a recorded backtest for this
       strategy on this symbol, or no order; live also needs paper runs that
       filled AND --confirm-live. There is no --force here — an unattended
       bypass is the one thing this file must never have.
    7. record the order in the ledger with autopilot=True, and write
       out/autopilot-<date>.txt

WHAT STOPS IT
    A file named STOP beside this script: the run exits before fetching.
    --max-positions (default 3): no new buys past that many open positions.
    One order per symbol per bar date: re-running the schedule is safe.

THE FIRST THING IN THIS REPO THAT PLACES AN ORDER ON ITS OWN
    Every agent here carried "never places an order". This file does, because
    Daniel asked for it on 2026-09-04. It starts in paper. The measured
    expectation (EVIDENCE.md, Fourth run) is a premium worth about a point a
    year over cash at 5% exposure, plus the trend filter's drawdown control —
    not an income. Read the ledger report before believing anything else.

CREDENTIALS
    From the shell environment only (ALPACA_KEY_ID, ALPACA_SECRET_KEY), as
    broker.py requires. Never in a file in this repository, never in the
    scheduler entry that is committed. README.md shows the cron line.

USAGE
    python3 autopilot.py --dry-run                        # decide, send nothing
    python3 autopilot.py                                  # paper
    python3 autopilot.py --mode live --confirm-live       # real money, by hand
    python3 autopilot.py --universe universe.txt --strategy trend_or_dip:200,14,30,5 --qty 1
"""

import argparse
import datetime as dt
import os
import sys

import bars as B
import barqc
import ledger
import replay
import strategies

HERE = os.path.dirname(os.path.abspath(__file__))
STOP_FILE = os.path.join(HERE, "STOP")
DEFAULT_STRATEGY = "trend_or_dip:200,14,30,5"


def read_universe(path):
    out = []
    for line in open(path):
        t = line.split("#")[0].strip()
        if t:
            out.append(t.upper())
    return out


def refresh(symbol, root, source="yahoo"):
    """Fetch and write daily bars. Returns (Series, note) or (None, reason)."""
    import fetch
    try:
        if source == "yahoo":
            s = fetch.fetch_yahoo(symbol, adjusted_close=True)
        elif source == "alpaca":
            s = fetch.fetch_alpaca(symbol, "1d")
        else:
            return None, f"unknown source {source}"
    except Exception as e:                       # NETWORK / PARSE: no bars means no bars
        return None, f"{type(e).__name__}: {e}"
    B.to_csv(s, B.bars_path(symbol, "1d", root))
    return s, f"{len(s.bars)} bars to {s.last.ts:%Y-%m-%d}"


def decide(series, strategy, now=None):
    """
    Target after the last closed bar, or a refusal. Returns (target, note).
    target None = do not act.
    """
    qc = barqc.inspect(series)
    if qc["verdict"] == "blocked":
        return None, "BLOCKED: " + ", ".join(qc["failed"])
    st = barqc.check_staleness(series, now)
    age = (now or dt.datetime.now(B.UTC)) - series.last.ts
    if age / series.period > barqc.STALE_PERIODS:
        return None, f"STALE: {st['value']}"
    cur = replay.Cursor(series, len(series))
    if len(cur) < strategy.warmup:
        return None, f"warm-up: {len(cur)} of {strategy.warmup} bars"
    return max(-1.0, min(1.0, float(strategy(cur)))), "ok"


def reconcile(target, held, qty):
    """(side, qty) or (None, reason). Long-only. Never adds to a position."""
    if target is None:
        return None, "no decision"
    if target > 0 and held <= 0:
        return "buy", qty
    if target <= 0 and held > 0:
        return "sell", held
    return None, "aligned"


def gate(mode, strategy_name, symbol, confirm_live):
    """The same gate as run.py, with no bypass. Returns a refusal or None."""
    if ledger.latest("backtest", strategy=strategy_name, symbol=symbol) is None:
        return "no recorded backtest for this strategy on this symbol"
    if mode == "live":
        if not confirm_live:
            return "live needs --confirm-live"
        if not ledger.filled_paper_runs(strategy_name, symbol):
            return "live needs a paper run that filled"
    return None


def already_acted(mode, strategy_name, symbol, bar_date):
    for e in ledger.events(mode, strategy=strategy_name, symbol=symbol):
        if e.get("autopilot") and e.get("bar_date") == bar_date:
            return True
    return False


def run(universe, strategy_spec, mode="paper", qty=1.0, max_positions=3,
        confirm_live=False, dry_run=False, root=None, fetch_fn=refresh,
        broker_api=None, now=None, out_dir=None):
    """
    One pass over the universe. Returns the list of per-symbol records.
    `fetch_fn(symbol, root)` and `broker_api` are injectable for tests; the
    broker object needs credentials(), account(), positions(), place_order(),
    wait_for_fill(), summarise(), PAPER, LIVE.
    """
    if os.path.exists(STOP_FILE):
        return [{"symbol": "*", "action": "STOP file present — nothing run"}]
    if mode not in ("paper", "live"):
        raise ValueError("mode must be paper or live")
    strat = strategies.make(strategy_spec)
    root = root or os.path.join(HERE, "bars")
    os.makedirs(root, exist_ok=True)
    recs = []

    held = {}
    acct = None
    base = hdr = None
    if not dry_run:
        if broker_api is None:
            import broker as broker_api
        base = broker_api.PAPER if mode == "paper" else broker_api.LIVE
        try:
            hdr = broker_api.credentials()
            acct = broker_api.account(base, hdr)
            held = broker_api.positions(base, hdr)
        except Exception as e:
            return [{"symbol": "*", "action": f"broker unreachable — nothing run: {e}"}]
    open_positions = sum(1 for q in held.values() if q > 0)

    for sym in universe:
        rec = {"symbol": sym, "action": "none"}
        s, note = fetch_fn(sym, root)
        rec["fetch"] = note
        if s is None:
            rec["action"] = "skipped: no bars"
            recs.append(rec)
            continue
        target, why = decide(s, strat, now)
        rec["target"], rec["decision"] = target, why
        rec["bar_date"] = f"{s.last.ts:%Y-%m-%d}"
        side, amount = reconcile(target, held.get(sym, 0.0), qty)
        rec["held"] = held.get(sym, 0.0)
        if side is None:
            rec["action"] = f"none: {amount}" if target is not None else f"none: {why}"
            recs.append(rec)
            continue
        if side == "buy" and open_positions >= max_positions:
            rec["action"] = f"none: {open_positions} open positions, max {max_positions}"
            recs.append(rec)
            continue
        refusal = gate(mode, strat.__name__, sym, confirm_live)
        if refusal:
            rec["action"] = f"REFUSED: {refusal}"
            recs.append(rec)
            continue
        if already_acted(mode, strat.__name__, sym, rec["bar_date"]):
            rec["action"] = f"none: already acted on {rec['bar_date']}"
            recs.append(rec)
            continue
        if dry_run:
            rec["action"] = f"would {side} {amount:g} ({mode})"
            recs.append(rec)
            continue
        try:
            o = broker_api.place_order(base, hdr, sym, side, amount)
            o = broker_api.wait_for_fill(base, hdr, o["id"])
        except Exception as e:
            rec["action"] = f"broker refused: {e}"
            recs.append(rec)
            continue
        summary = broker_api.summarise(o)
        ledger.record(mode, strategy=strat.__name__, symbol=sym, signal=target,
                      endpoint=base, account=acct["account_number"], autopilot=True,
                      bar_date=rec["bar_date"], **summary)
        rec["action"] = (f"{side} {amount:g}: {summary['status']}, filled "
                         f"{summary['filled_qty']:g}")
        if side == "buy":
            open_positions += 1
        recs.append(rec)

    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
        stamp = (now or dt.datetime.now(B.UTC)).strftime("%Y-%m-%d")
        with open(os.path.join(out_dir, f"autopilot-{stamp}.txt"), "w") as f:
            f.write(render(recs, mode, strat.__name__))
    return recs


def render(recs, mode, strategy_name):
    L = [f"AUTOPILOT · {mode.upper()} · {strategy_name} · "
         f"{dt.datetime.now(B.UTC):%Y-%m-%d %H:%M} UTC",
         f"{'symbol':<7}{'bars':<32}{'target':>7}{'held':>7}  action", "-" * 90]
    for r in recs:
        t = r.get("target")
        L.append(f"{r['symbol']:<7}{(r.get('fetch') or '')[:31]:<32}"
                 f"{('-' if t is None else format(t, '+.0f')):>7}"
                 f"{(format(r['held'], 'g') if 'held' in r else '-'):>7}  {r['action']}")
    L.append("-" * 90)
    L.append("Orders go only through the gate: a recorded backtest per symbol; live also "
             "needs filled paper runs and\n--confirm-live. A STOP file beside autopilot.py "
             "halts the next run. python3 ledger.py --report for the record.")
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--universe", default=os.path.join(HERE, "universe.txt"))
    ap.add_argument("--strategy", default=DEFAULT_STRATEGY)
    ap.add_argument("--mode", default="paper", choices=["paper", "live"])
    ap.add_argument("--qty", type=float, default=1.0, help="shares per new position")
    ap.add_argument("--max-positions", type=int, default=3)
    ap.add_argument("--confirm-live", action="store_true")
    ap.add_argument("--dry-run", action="store_true", help="decide and print; send nothing")
    ap.add_argument("--source", default="yahoo", choices=["yahoo", "alpaca"])
    a = ap.parse_args()
    if a.mode == "live" and not a.confirm_live:
        sys.exit("REFUSING --mode live without --confirm-live. Real money. Say so explicitly.")
    universe = read_universe(a.universe)
    recs = run(universe, a.strategy, a.mode, a.qty, a.max_positions, a.confirm_live,
               a.dry_run, fetch_fn=lambda sym, root: refresh(sym, root, a.source),
               out_dir=os.path.join(HERE, "out"))
    print(render(recs, a.mode, strategies.make(a.strategy).__name__))


if __name__ == "__main__":
    main()
