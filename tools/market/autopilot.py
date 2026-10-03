#!/usr/bin/env python3
"""
autopilot.py — the unattended daily loop. Fetch, check, decide, reconcile,
record. Runs on the Mac on a schedule; PAPER by default; live only when told
so in words, and only after paper runs have filled.

VERIFIED 2026-09-04: fifteen checks in test_tools.py drive it against a fake
    broker — refuses without a backtest, dry run sends nothing, buys once
    when long and flat, never adds, sells all when flat and long, idempotent
    per bar date, honours max positions, refuses live without --confirm-live
    and without filled paper runs, never trades stale bars, halts on STOP.
    Run --dry-run on the Mac before pointing it at a broker anyway.

WHAT "MONITORING THE MARKET" MEANS HERE
    The rules this pipeline has measured are DAILY rules: they read the close
    and act at the next open. Watching them tick by tick adds nothing — the
    one intraday rule with a published edge was excluded on this feed at four
    standard errors — so the honest cadence is one run after each close.
    Alpaca queues a market order sent after hours and fills it at the next
    open, which is exactly the fill replay.py assumes.

WHAT ONE RUN DOES, PER SYMBOL IN THE UNIVERSE
    1. fetch fresh daily bars and write them to bars/live/ (never over the
       research files in bars/)
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

SIZING
    --qty N        whole shares per position; targets are read as long/flat.
    --notional D   dollars per symbol; the rule's fractional target (a
                   vol_target wrapper returns 0.37, say) is bought as 0.37 × D
                   in fractional shares, then traded ONLY when the target
                   changes by more than 10% — never because the price moved,
                   which is exactly how replay treats a target. The position
                   the cursor sees is the last target this loop sent for the
                   symbol, read back from the ledger; flat is 0.

REVIEWED 2026-09-04 (four finders, three refuters per finding): an order is
    recorded the moment the broker accepts it, so a failed fill poll cannot
    lead to a duplicate; one order per symbol per bar date for ANY strategy;
    a same-day bar seen before 21:05 UTC is the open session and is dropped;
    no equity reading → nothing traded; a backtest that failed its leak check
    does not pass the gate.

WHAT STOPS IT
    A file named STOP beside this script: the run exits before fetching.
    --max-positions (default 3): no new buys past that many open positions.
    --max-drawdown (default 0.15): every run records the account's equity;
      if it sits more than this far below the highest equity recorded for
      this mode, the run writes STOP and trades nothing. It halts; it does
      not liquidate — what to do with the open positions is a decision, not
      a reflex, and it is Daniel's.
    One order per symbol per bar date: re-running the schedule is safe.
    An order whose fate a failure hid (reply and lookup both lost) is
      recorded 'unknown'; the next run asks the broker about it before it
      decides anything for that symbol, and waits while the answer is still
      unknown. One run per mode at a time: a second waits for the lock.

THE FIRST THING IN THIS REPO THAT PLACES AN ORDER ON ITS OWN
    Every agent here carried "never places an order". This file does, because
    Daniel asked for it on 2026-09-04. It starts in paper. The measured
    expectation (EVIDENCE.md, Fourth run) is a premium worth about a point a
    year over cash at 5% exposure, plus the trend filter's drawdown control —
    not an income. Read the ledger report before believing anything else.

CREDENTIALS
    As broker.py reads them: the shell environment (ALPACA_KEY_ID,
    ALPACA_SECRET_KEY) or the macOS login keychain. Never in a file in this
    repository, never as arguments, never in the scheduler entry that is
    committed. README.md shows the cron line.

USAGE
    python3 autopilot.py --dry-run                        # decide, send nothing
    python3 autopilot.py                                  # paper
    python3 autopilot.py --mode live --confirm-live       # real money, by hand
    python3 autopilot.py --universe universe.txt --strategy trend_or_dip:200,14,30,5 --qty 1
"""

import argparse
import datetime as dt
import inspect
import math
import os
import sys
import time

import bars as B
import barqc
import ledger
import replay
import strategies

HERE = os.path.dirname(os.path.abspath(__file__))
STOP_FILE = os.path.join(HERE, "STOP")
LIVE_ROOT = os.path.join(HERE, "bars", "live")
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
            # Without a start Alpaca hands back only the current day; with one
            # too early the IEX daily history is full of holes and barqc blocks
            # it. 600 calendar days covers the 200-bar warm-up twice over.
            since = (dt.datetime.now(B.UTC) - dt.timedelta(days=600)).strftime("%Y-%m-%d")
            s = fetch.fetch_alpaca(symbol, "1d", start=since, adjustment="all")
        else:
            return None, f"unknown source {source}"
    except Exception as e:                       # NETWORK / PARSE: no bars means no bars
        return None, f"{type(e).__name__}: {e}"
    B.to_csv(s, B.bars_path(symbol, "1d", root))
    return s, f"{len(s.bars)} bars to {s.last.ts:%Y-%m-%d}"


def decide(series, strategy, now=None, position=0.0):
    """
    Target after the last closed bar, or a refusal. Returns (target, note).
    target None = do not act. `position` is what the broker says is held, as
    a fraction (1.0 = the position this loop sizes), so a strategy that
    reads cursor.position sees the truth rather than a fresh process.
    """
    qc = barqc.inspect(series)
    if qc["verdict"] == "blocked":
        return None, "BLOCKED: " + ", ".join(qc["failed"])
    now = now or dt.datetime.now(B.UTC)
    # A daily bar dated today, seen before the close has printed, is the
    # session in progress, not a closed bar. Yahoo and Alpaca both hand it
    # out. 21:05 UTC is after the 16:00 New York close in both winter and
    # summer, so before that a same-day bar is dropped, and the decision is
    # made on yesterday's close — which is what the rule was measured on.
    if series.last.ts.date() == now.date() and now.time() < dt.time(21, 5):
        if len(series.bars) < 2:
            return None, "only an in-progress bar"
        series = type(series)(series.symbol, series.timeframe, list(series.bars)[:-1],
                              dict(series.provenance))
    st = barqc.check_staleness(series, now)
    age = now - series.last.ts
    if age / series.period > barqc.STALE_PERIODS:
        return None, f"STALE: {st['value']}"
    cur = replay.Cursor(series, len(series), position=position)
    if len(cur) < strategy.warmup:
        return None, f"warm-up: {len(cur)} of {strategy.warmup} bars"
    raw = float(strategy(cur))
    if not math.isfinite(raw):
        # max(-1, min(1, nan)) is 1.0: a NaN target used to become a full BUY
        return None, f"the strategy returned {raw!r}, not a number — no decision"
    return max(-1.0, min(1.0, raw)), "ok"


BAND = 0.10


def reconcile(target, held, qty):
    """(side, qty) or (None, reason). Long-only. Never adds to a position."""
    if target is None:
        return None, "no decision"
    if target > 0 and held <= 0:
        return "buy", qty
    if target <= 0 and held > 0:
        return "sell", held
    return None, "aligned"


def last_target(mode, symbol):
    """
    The target the loop last sent for this symbol in this mode, from the
    ledger, or None if it never has. This — not the marked-to-market value —
    is what replay's cursor.position means: the last FILLED target. Reading
    it from the ledger keeps the loop stateless across processes and makes
    the backtest and the live loop agree on what "position" is.
    """
    ev = [e for e in _orders(mode, symbol) if e.get("status") not in UNSETTLED]
    if not ev:
        return None
    try:
        return float(ev[-1].get("signal"))
    except (TypeError, ValueError):
        return None


# An order whose fate a failure hid is recorded 'unknown'; the next run asks the
# broker and records what it holds, or 'not_sent' when it holds nothing.
UNSETTLED = ("unknown", "not_sent")


def _orders(mode, symbol):
    """This loop's order records for a symbol, without any order that turned
    out never to have reached the broker."""
    ev = [e for e in ledger.events(mode, symbol=symbol) if e.get("autopilot")]
    never = {e["client_order_id"] for e in ev
             if e.get("status") == "not_sent" and e.get("client_order_id")}
    return [e for e in ev if not (e.get("client_order_id") and e["client_order_id"] in never)]


def unresolved(mode, symbol):
    """'unknown' order records with nothing recorded after them."""
    last = {}
    for e in ledger.events(mode, symbol=symbol):
        if e.get("autopilot") and e.get("client_order_id"):
            last[e["client_order_id"]] = e
    return [e for e in last.values() if e.get("status") == "unknown"]


def reconcile_notional(target, last, held_qty, notional, band=BAND):
    """
    Trade only when the TARGET changes — exactly as replay does — never
    because the price moved. `last` is the last target sent (last_target()).
    Returns (side, {"qty": q} | {"notional": d}) or (None, reason).

        flat, target > 0            buy target × D
        held, target 0              sell every share held
        held, |target − last| < band nothing (price drift is not a signal)
        held, target up             buy (target − last) × D
        held, target down           sell the same FRACTION of the held shares,
                                    (last − target) / last, so a fallen price
                                    is never re-bought and never over-sold
    """
    if target is None:
        return None, "no decision"
    target = max(0.0, min(1.0, target))
    if held_qty <= 0:
        if target > 0:
            return "buy", {"notional": round(target * notional, 2)}
        return None, "aligned"
    if target <= 0:
        return "sell", {"qty": held_qty}
    base = last if (last is not None and last > 0) else 1.0
    delta = target - base
    if abs(delta) < band:
        return None, "aligned"
    if delta > 0:
        return "buy", {"notional": round(delta * notional, 2)}
    return "sell", {"qty": round(held_qty * (-delta / base), 6)}


def drawdown_halt(mode, equity, max_drawdown):
    """
    Record this run's equity; return a halt message if it is more than
    max_drawdown below the highest equity ever recorded for this mode.
    """
    if equity is None:
        return None
    prior = [e.get("equity") for e in ledger.events("autopilot_run", mode=mode)
             if isinstance(e.get("equity"), (int, float)) and math.isfinite(e.get("equity"))]
    peak = max(prior + [equity])
    ledger.record("autopilot_run", mode=mode, equity=equity, peak=peak)
    if peak > 0 and equity < peak * (1.0 - max_drawdown):
        return (f"equity {equity:,.2f} is {1 - equity / peak:.1%} below the recorded peak "
                f"{peak:,.2f}; limit {max_drawdown:.0%}")
    return None


def gate(mode, strategy_name, symbol, confirm_live):
    """The same gate as run.py, with no bypass. Returns a refusal or None."""
    bt = ledger.latest("backtest", strategy=strategy_name, symbol=symbol)
    if bt is None:
        return "no recorded backtest for this strategy on this symbol"
    why = ledger.leak_refusal(bt)
    if why:
        return (f"the latest recorded backtest {why}; "
                f"record one that passes with run.py --mode backtest")
    if mode == "live":
        if not confirm_live:
            return "live needs --confirm-live"
        if not ledger.filled_paper_runs(strategy_name, symbol):
            return "live needs a paper run that filled"
    return None


def already_acted(mode, symbol, bar_date):
    """One order per symbol per bar date, whatever strategy sent it. An order
    that never reached the broker does not count: the bar is still open to it."""
    return any(e.get("bar_date") == bar_date for e in _orders(mode, symbol))


def settle(mode, symbol, broker_api, base, hdr):
    """
    Ask the broker about every order this loop recorded as 'unknown' for the
    symbol, and record what it holds. Returns None when all are settled, or
    the reason this symbol must wait: an order whose fate is still unknown is
    a position the loop would otherwise act blind to.
    """
    for e in unresolved(mode, symbol):
        try:
            o = broker_api.order_by_client_id(base, hdr, e["client_order_id"])
        except Exception as err:
            return (f"none: an earlier {e.get('side')} (bar {e.get('bar_date')}) is still "
                    f"UNKNOWN and the broker could not be asked ({err})")
        carry = {k: e[k] for k in ("strategy", "symbol", "signal", "endpoint", "account",
                                   "autopilot", "bar_date", "client_order_id") if k in e}
        if o is None:
            ledger.record(mode, **carry, status="not_sent", filled_qty=0.0)
        else:
            ledger.record(mode, **carry, **broker_api.summarise(o))
    return None


LOCK_FILE = os.path.join(HERE, "out", "autopilot.lock")
LOCK_WAIT = 600          # seconds a run waits for an earlier one before giving up


def lock_path(mode):
    """One lock per mode: a paper run and a live run never share a slot."""
    root, ext = os.path.splitext(LOCK_FILE)
    return f"{root}-{mode}{ext}"


def _lock(mode):
    """An exclusive lock for one run of this mode, waited for up to LOCK_WAIT
    seconds, or None when an earlier run still holds it then. A cron tick that
    meets a slow run queues behind it instead of vanishing."""
    try:
        import fcntl
    except ImportError:                          # not POSIX: no lock, as before
        return open(os.devnull)
    os.makedirs(os.path.dirname(LOCK_FILE), exist_ok=True)
    f = open(lock_path(mode), "a")
    deadline = time.monotonic() + LOCK_WAIT
    while True:
        try:
            fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return f
        except OSError:
            if time.monotonic() >= deadline:
                f.close()
                return None
            time.sleep(1)


def run(*args, **kwargs):
    """
    One pass over the universe — see _run_once. A run that can send orders
    holds an exclusive lock: two overlapping runs (cron and a hand run, or a
    slow run and the next tick) both passed already_acted and both sent.
    """
    bound = inspect.signature(_run_once).bind(*args, **kwargs)
    bound.apply_defaults()
    if bound.arguments["dry_run"]:
        return _run_once(*args, **kwargs)
    lock = _lock(bound.arguments["mode"])
    if lock is None:
        return [{"symbol": "*", "action": f"another {bound.arguments['mode']} autopilot run held "
                                          f"the lock for {LOCK_WAIT}s — nothing run"}]
    try:
        return _run_once(*args, **kwargs)
    finally:
        lock.close()


def _run_once(universe, strategy_spec, mode="paper", qty=1.0, max_positions=3,
              confirm_live=False, dry_run=False, root=None, fetch_fn=refresh,
              broker_api=None, now=None, out_dir=None, notional=None, max_drawdown=0.15):
    """
    One pass over the universe. Returns the list of per-symbol records.
    `fetch_fn(symbol, root)` and `broker_api` are injectable for tests; the
    broker object needs credentials(), account(), positions(), place_order(),
    wait_for_fill(), summarise(), PAPER, LIVE.
    """
    if os.path.lexists(STOP_FILE):     # a dangling symlink named STOP halts too
        return [{"symbol": "*", "action": "STOP file present — nothing run"}]
    try:
        ledger.load()
    except ledger.Corrupt as e:
        return [{"symbol": "*", "action": f"ledger unreadable — nothing run: {e}"}]
    if not (isinstance(max_drawdown, (int, float)) and 0 < max_drawdown < 1):
        return [{"symbol": "*", "action": f"max_drawdown {max_drawdown!r} is not between 0 and 1, "
                                          f"so the halt could never fire — nothing run"}]
    if mode not in ("paper", "live"):
        raise ValueError("mode must be paper or live")
    strat = strategies.make(strategy_spec)
    # Its own folder: the research files in bars/ (21 years of Stooq SPY, the
    # replication set) must never be overwritten by a 600-day live fetch.
    root = root or LIVE_ROOT
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
        try:
            equity = float(acct.get("equity")) if acct and acct.get("equity") is not None else None
        except (TypeError, ValueError):
            equity = None
        if equity is not None and not math.isfinite(equity):
            equity = None           # "NaN" parsed as a reading and, once recorded, disabled the halt
        if equity is None:
            return [{"symbol": "*", "action": "no equity reading from the broker — the drawdown "
                                             "guard cannot run, so nothing is traded"}]
        halt = drawdown_halt(mode, equity, max_drawdown)
        if halt:
            with open(STOP_FILE, "w") as f:
                f.write(f"drawdown halt {dt.datetime.now(B.UTC):%Y-%m-%d %H:%M} UTC: {halt}\n")
            return [{"symbol": "*", "action": f"HALTED, STOP written — {halt}"}]
    open_positions = sum(1 for q in held.values() if q > 0)

    for sym in universe:
        rec = {"symbol": sym, "action": "none"}
        s, note = fetch_fn(sym, root)
        rec["fetch"] = note
        if s is None:
            rec["action"] = "skipped: no bars"
            recs.append(rec)
            continue
        if not dry_run:
            stuck = settle(mode, sym, broker_api, base, hdr)
            if stuck:
                rec["action"] = stuck
                recs.append(rec)
                continue
        held_qty = held.get(sym, 0.0)
        last = last_target(mode, sym) if held_qty > 0 else None
        if held_qty <= 0:
            pos = 0.0
        elif notional:
            pos = last if (last is not None and last > 0) else 1.0
        else:
            pos = 1.0
        target, why = decide(s, strat, now, position=pos)
        rec["target"], rec["decision"] = target, why
        rec["bar_date"] = f"{s.last.ts:%Y-%m-%d}"
        if notional:
            side, amount = reconcile_notional(target, last, held_qty, notional)
        else:
            side, amount = reconcile(target, held_qty, qty)
        rec["held"] = held_qty
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
        if already_acted(mode, sym, rec["bar_date"]):
            rec["action"] = f"none: already acted on {rec['bar_date']}"
            recs.append(rec)
            continue
        order = amount if isinstance(amount, dict) else {"qty": amount}
        desc = (f"{order['qty']:g} sh" if "qty" in order else f"${order['notional']:,.2f}")
        if dry_run:
            rec["action"] = f"would {side} {desc} ({mode})"
            recs.append(rec)
            continue
        import broker as broker_ids        # the pure id helper; no network at import
        coid = broker_ids.client_order_id("autopilot", mode, strat.__name__, sym,
                                          rec["bar_date"], side)
        common = dict(strategy=strat.__name__, symbol=sym, signal=target, endpoint=base,
                      account=acct["account_number"], autopilot=True, bar_date=rec["bar_date"],
                      client_order_id=coid)
        try:
            o = broker_api.place_order(base, hdr, sym, side, client_order_id=coid, **order)
        except Exception as e:
            # A refusal, or a failure AFTER the broker accepted (a timeout, a
            # lost reply, an id it has already seen): ask the broker. Treating
            # every exception as "refused" let the next run send it again.
            try:
                o = broker_api.order_by_client_id(base, hdr, coid)
            except Exception as e2:
                # Recorded, so this bar counts as acted on and the target it
                # meant stands; the next run asks the broker before anything
                # else for this symbol. Unrecorded, the next run read the
                # position as unexplained and traded against it.
                ledger.record(mode, **common, status="unknown", side=side, filled_qty=0.0,
                              **({"qty": float(order["qty"])} if "qty" in order
                                 else {"notional": float(order["notional"])}))
                rec["action"] = (f"UNKNOWN whether {side} {desc} was sent ({e}; lookup: {e2}). "
                                 f"Recorded as unknown; the next run asks the broker first")
                recs.append(rec)
                continue
            if o is None:
                rec["action"] = f"broker refused: {e}"
                recs.append(rec)
                continue
        # Recorded the moment the broker accepts it, BEFORE the fill poll: an
        # order that exists at the broker and not in the ledger would be sent
        # again by the next run. The fill, when it comes, is a second record.
        first = broker_api.summarise(o)
        ledger.record(mode, **common, **first)
        try:
            o = broker_api.wait_for_fill(base, hdr, o["id"])
        except Exception as e:
            rec["action"] = f"{side} {desc}: sent, fill unknown ({e}); recorded as it stood"
            recs.append(rec)
            continue
        summary = broker_api.summarise(o)
        # A second record only for a fill the first did not already show: a
        # lookup that found the order filled used to be written twice.
        if (summary.get("filled_qty") or 0) > (first.get("filled_qty") or 0):
            ledger.record(mode, **common, **summary)
        rec["action"] = (f"{side} {desc}: {summary['status']}, filled "
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
                 f"{('-' if t is None else format(t, '+.2f')):>7}"
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
    ap.add_argument("--notional", type=float, help="dollars per symbol; fractional targets held as a share of it")
    ap.add_argument("--max-drawdown", type=float, default=0.15,
                    help="halt (write STOP) when equity is this far below the recorded peak")
    ap.add_argument("--max-positions", type=int, default=3)
    ap.add_argument("--confirm-live", action="store_true")
    ap.add_argument("--dry-run", action="store_true", help="decide and print; send nothing")
    ap.add_argument("--source", default="alpaca", choices=["yahoo", "alpaca"],
                    help="alpaca (keys in the shell; 600 days, adjustment all) or yahoo (keyless, rate-limited)")
    a = ap.parse_args()
    for name, v in (("--qty", a.qty), ("--notional", a.notional)):
        if v is not None and not (math.isfinite(v) and v > 0):
            sys.exit(f"REFUSING {name} {v}: it must be a positive, finite number "
                     f"(--notional 0 used to fall back silently to whole shares)")
    if a.mode == "live" and not a.confirm_live:
        sys.exit("REFUSING --mode live without --confirm-live. Real money. Say so explicitly.")
    universe = read_universe(a.universe)
    recs = run(universe, a.strategy, a.mode, a.qty, a.max_positions, a.confirm_live,
               a.dry_run, fetch_fn=lambda sym, root: refresh(sym, root, a.source),
               out_dir=os.path.join(HERE, "out"), notional=a.notional,
               max_drawdown=a.max_drawdown)
    print(render(recs, a.mode, strategies.make(a.strategy).__name__))


if __name__ == "__main__":
    main()
