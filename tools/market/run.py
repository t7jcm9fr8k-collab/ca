#!/usr/bin/env python3
"""
run.py — the gate. signals → backtest → paper → live, each earned past the last.

THE GATE, WHICH IS THE POINT OF THIS FILE
    --mode paper  refuses without a recorded backtest of this strategy on this
                  symbol.
    --mode live   refuses without BOTH a recorded backtest AND a paper run that
                  actually filled — and needs --confirm-live on top, because a
                  real-money order should not be one typo away from a paper one.

    If you find yourself wanting to skip the gate, that is the gate working.

    There is an escape hatch, and it is deliberately awkward: --force skips the
    record requirement, but only with --force-reason. Without one it exits 4 and
    does nothing. With one, the bypass is written to the ledger and rendered in
    red in the report — a forced run that looked identical to an earned one
    would make the ledger lie, and the ledger's only value is that a live run
    sitting below a paper run proves the paper run happened.

MODES
    signal     what the strategy says NOW, on the last closed bar. No gate.
    backtest   replay over the whole series; record the result. No gate — this
               IS the first piece of evidence.
    paper      send the strategy's order to the paper endpoint; record the fill.
    live       the same, for real money.

    paper and live derive the order from the strategy's current signal: long
    means buy --qty, flat means nothing to buy. Override with --side to reduce
    or reverse; the record keeps both the signal and what was sent.

    --dry-run on paper/live passes the gate and stops before the broker. Nothing
    is sent and nothing is recorded as a run; a forced dry run still records the
    bypass, because the bypass is what needs auditing.

ONE DECISION, ONE ORDER
    Every order carries an id made from the decision — mode, strategy, symbol,
    bar, side, size — and the broker refuses an id it has seen. Running the
    same decision again therefore sends NOTHING and says so (exit 8); --repeat N
    sends a deliberate Nth copy. An order whose fate a failure hid is recorded
    as 'unknown', and the next run asks the broker about it before sending
    anything for that symbol. Paper and live refuse bars more than three
    sessions old: an order on them would be trading the past.

EXIT CODES
    2  data refused (unparseable, barqc blocked it, or stale for paper/live)
    3  gate refused (no backtest / no filled paper run / no --confirm-live /
       --force on live / a STOP file present / a sell larger than the position)
    4  --force without --force-reason
    5  no broker credentials
    6  broker unreachable or order rejected
    7  the ledger exists but cannot be read — nothing that records or trades runs
    8  NOT SENT: this decision's order (or an earlier one whose outcome was
       unknown) is already at the broker; what it holds is recorded

USAGE
    python3 run.py --mode signal   --strategy sma_cross:10,30 --csv bars/AAPL-1d.csv --symbol AAPL
    python3 run.py --mode backtest --strategy sma_cross:10,30 --csv bars/AAPL-1d.csv --symbol AAPL --cost-bps 5
    python3 run.py --mode paper    --strategy sma_cross:10,30 --csv bars/AAPL-1d.csv --symbol AAPL --qty 10
    python3 run.py --mode live     --strategy sma_cross:10,30 --csv bars/AAPL-1d.csv --symbol AAPL --qty 1 --confirm-live
"""

import argparse
import math
import os
import sys

import bars as B
import barqc
import ledger
import replay
import strategies

HERE = os.path.dirname(os.path.abspath(__file__))


def refuse(code, *lines):
    print(*lines, sep="\n", file=sys.stderr)
    sys.exit(code)


def load(a):
    path = a.csv or B.bars_path(a.symbol, a.timeframe)
    try:
        s = B.load_csv(path, a.symbol, a.timeframe, a.source,
                       {"yes": True, "no": False}.get(a.adjusted))
    except (B.Unparseable, B.NoProvenance) as e:
        refuse(2, f"REFUSED: {e}")
    qc = barqc.inspect(s)
    if qc["verdict"] == "blocked":
        refuse(2, f"REFUSED: barqc blocked {s.describe()}",
               f"  failed: {', '.join(qc['failed'])}",
               f"  Run:  python3 barqc.py --csv {path} --symbol {a.symbol}",
               "  A decision on broken bars is a broken decision.")
    return s, qc


def gate(a, strat_name):
    """
    Returns nothing if the run may proceed; refuses otherwise. A --force with a
    reason records the bypass first, then proceeds.
    """
    need = []
    if a.mode in ("paper", "live"):
        bt = ledger.latest("backtest", strategy=strat_name, symbol=a.symbol)
        why = ledger.leak_refusal(bt) if bt is not None else None
        if bt is None:
            need.append("a recorded backtest")
        elif why:
            need.append(f"a backtest that passed its leak check — the latest one {why}")
    if a.mode == "live":
        if not ledger.filled_paper_runs(strat_name, a.symbol):
            need.append("a paper run that filled")
    if not need:
        return
    missing = " and ".join(need)
    if a.force and a.mode == "live":
        refuse(3, "REFUSING to force --mode live.", "",
               f"  {strat_name} on {a.symbol} needs {missing}.",
               "  --force can waive the paper gate, never the live one: real money follows a",
               "  recorded backtest and a filled paper run, every time. Nothing was recorded.")
    if a.force:
        ledger.record("bypass", mode=a.mode, strategy=strat_name, symbol=a.symbol,
                      missing=missing, reason=a.force_reason)
        print(f"⚠ GATE BYPASSED — {a.mode} without {missing}. "
              f"Recorded. Reason: {a.force_reason}", file=sys.stderr)
        return
    refuse(3, f"REFUSING to run --mode {a.mode}.",
           f"",
           f"  {strat_name} on {a.symbol} needs {missing}.",
           f"  {'Paper exists to answer a backtest; without one it is a guess with a fill.' if a.mode == 'paper' else 'Live money follows a paper fill, never a backtest alone.'}",
           f"",
           f"  Run:  python3 run.py --mode {'backtest' if 'backtest' in missing else 'paper'} "
           f"--strategy {a.strategy} --symbol {a.symbol}" +
           ("" if 'backtest' in missing else f" --qty {a.qty or 1:g}"))


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--mode", required=True,
                    choices=["signal", "backtest", "paper", "live"])
    ap.add_argument("--strategy", required=True, help="e.g. sma_cross:10,30")
    ap.add_argument("--symbol", required=True)
    ap.add_argument("--timeframe", default="1d", choices=sorted(B.TIMEFRAMES))
    ap.add_argument("--csv", help="default bars/<SYMBOL>-<tf>.csv")
    ap.add_argument("--source")
    ap.add_argument("--adjusted", choices=["yes", "no"])
    ap.add_argument("--cost-bps", type=float, default=5.0,
                    help="per-fill cost in basis points for backtests (default 5)")
    ap.add_argument("--cash-yield", type=float, default=0.0,
                    help="annual rate earned on idle cash in backtests, e.g. 0.04")
    ap.add_argument("--dividend-yield", type=float, default=0.0,
                    help="annual rate credited on the held position when prices are NOT "
                         "dividend-adjusted (Stooq), e.g. 0.018 for SPY; 0 for total-return data")
    ap.add_argument("--qty", type=float, help="shares, for paper/live")
    ap.add_argument("--side", choices=["buy", "sell"],
                    help="override the side the signal implies")
    ap.add_argument("--dry-run", action="store_true",
                    help="paper/live: pass the gate, send nothing")
    ap.add_argument("--repeat", type=int, metavar="N",
                    help="paper/live: send the same order again on the same bar, as its Nth "
                         "copy. Without it a repeat of a decision is never sent twice")
    ap.add_argument("--confirm-live", action="store_true",
                    help="required for --mode live")
    ap.add_argument("--force", action="store_true",
                    help="skip the record requirement. Requires --force-reason; "
                         "the bypass is recorded in the ledger and shown in the report.")
    ap.add_argument("--force-reason", default="",
                    help="why the gate is being skipped; required with --force")
    a = ap.parse_args()

    if a.force and not a.force_reason.strip():
        refuse(4, "REFUSING to force.", "",
               "  --force skips the gate, so it has to be justified in writing.",
               "  A bypass someone had to explain is a different act from one they",
               "  could take by reflex.", "",
               '  Run:  --force --force-reason "…"')

    try:
        strat = strategies.make(a.strategy)
    except (KeyError, ValueError) as e:
        refuse(2, f"REFUSED: {e}")
    strat_name = getattr(strat, "__name__", a.strategy)
    if a.mode != "signal":
        try:
            ledger.load()
        except ledger.Corrupt as e:
            refuse(7, f"REFUSED: {e}")

    s, qc = load(a)
    if qc["unrun"]:
        print(f"note: unrun checks — {', '.join(qc['unrun'])} (not passes)")

    # ---- signal ---------------------------------------------------------
    cur = replay.Cursor(s, len(s))
    try:
        target = float(strat(cur))
    except replay.LookAhead as e:
        refuse(2, f"REFUSED: strategy reached past the last closed bar — {e}")
    last = s.last
    print(f"signal   {strat_name} on {s.symbol} {s.timeframe}: target {target:+.2f} "
          f"after {last.ts:%Y-%m-%d} close {last.close:g}")
    if a.mode == "signal":
        st = barqc.check_staleness(s)
        print(f"         {st['value']}"
              + (f" — {st['note']}" if st.get("note") else ""))
        # The chart, as numbers, at the last close — what a discretionary
        # trader would read off it, without the picture.
        import features
        d = features.describe(cur[-250:])
        va = d.get("value_area")
        print(f"\nreadings at {last.ts:%Y-%m-%d} close {d['close']:g}")
        print(f"  ema20        {d['ema']:.4g}   {'above' if d['close'] > d['ema'] else 'below'}"
              if d.get("ema") else "  ema20        (not enough bars)")
        print(f"  vwap         {d['vwap_anchored']:.4g}   anchored at the first bar shown"
              if d.get("vwap_anchored") else "  vwap         (no volume)")
        print(f"  atr14        {d['atr']:.4g}" if d.get("atr") else "  atr14        (not enough bars)")
        print(f"  rejection    {d['rejection'] or 'none'}   (pin-bar geometry on the last bar)")
        if d.get("nearest_level") is not None:
            print(f"  level        {d['nearest_level']:.4g}   {d['distance_to_level']:+.2%} away, "
                  f"of {d['levels']} swing level(s)")
        else:
            print(f"  level        none yet   (no confirmed swing in the window)")
        if d.get("poc") is not None:
            print(f"  poc          {d['poc']:.4g}   value area {va[0]:.4g} – {va[1]:.4g}")
        print(f"  cvd proxy    {d['cvd_proxy']:+.3g}   (bar-delta PROXY — not order flow)")
        return

    # ---- backtest -------------------------------------------------------
    if a.mode == "backtest":
        try:
            r = replay.replay(s, strat, cost_bps=a.cost_bps, name=strat_name,
                              cash_yield=a.cash_yield, dividend_yield=a.dividend_yield)
        except replay.Blocked as e:
            refuse(2, f"REFUSED: {e}")
        print(replay.summary(r))
        print(f"         scored from {r['scored_from'][:10]} after a {r['warmup']}-bar warm-up, "
              f"{r['live_bars']} live bars; buy&hold measured from the same bar")
        print(f"         buy&hold over those bars: max drawdown {r['benchmark_max_drawdown']:.1%}, "
              f"sharpe {r['benchmark_sharpe']:.2f}, vol {r['benchmark_volatility']:.1%}")
        print(f"         sharpe {r['sharpe']:.2f}, cagr "
              f"{(format(r['cagr'], '+.1%') if r['cagr'] is not None else 'n/a')}, "
              f"vol {r['volatility']:.1%}, {r['years']:.1f} years"
              + (f", cash yield {a.cash_yield:.1%}" if a.cash_yield else "")
              + (f", dividend yield {a.dividend_yield:.1%} credited to both" if a.dividend_yield else ""))
        lk = replay.leak_check(s, strat, r["targets"], r["warmup"], positions=r["positions"],
                               factory=lambda: strategies.make(a.strategy))
        r["leak_check"] = lk
        if lk["differences"]:
            print(f"LEAK: the strategy decided differently at {len(lk['differences'])} of "
                  f"{lk['checked']} sampled bars when the future was removed "
                  f"(bars {lk['differences'][:5]}). It is reading past the cursor.")
        else:
            print(f"leak check: {lk['checked']} bars re-run with the future removed, "
                  f"0 differences")
        print(f"not modelled: {r['not_modelled']}")
        keep = {k: v for k, v in r.items() if k not in replay.LEDGER_EXCLUDE}
        ledger.record("backtest", **keep)
        print(f"\nrecorded backtest to the ledger")
        print(f"next:  python3 run.py --mode paper --strategy {a.strategy} "
              f"--symbol {a.symbol} --qty N        # on the Mac, with keys")
        print(f"       python3 ledger.py --report")
        return

    # ---- paper / live ---------------------------------------------------
    # --confirm-live is checked BEFORE the gate so that a fat-fingered live
    # command with --force does not leave a bypass in the ledger for a run that
    # never happened.
    if a.mode == "live" and not a.confirm_live:
        refuse(3, "REFUSING --mode live without --confirm-live.",
               "  Real money. Say so explicitly.")
    if not a.dry_run:
        import autopilot
        if os.path.lexists(autopilot.STOP_FILE):
            refuse(3, "REFUSING: a STOP file is present (a drawdown halt, or placed by hand).",
                   "  Nothing is sent while it exists — run.py honours it as autopilot does.",
                   "  Remove it to resume.")
    behind = barqc.sessions_behind(s)
    if behind is not None and behind > barqc.STALE_PERIODS:
        # autopilot refuses stale bars; run.py used to send on a research file
        # months old, and its order id — keyed on the bar — froze with it.
        refuse(2, f"REFUSED: the last bar is {s.last.ts:%Y-%m-%d}, {behind} sessions behind "
                  f"(limit {barqc.STALE_PERIODS}).",
               "  An order on it would be trading the past. Refresh the bars first:",
               f"  python3 fetch.py --symbol {s.symbol}")
    if a.repeat is not None and a.repeat < 2:
        refuse(3, "--repeat N numbers a deliberate copy of an order already sent: N is 2 or more.")
    gate(a, strat_name)

    side = a.side or ("buy" if target > 0 else None)
    if side is None:
        refuse(3, f"strategy says flat ({target:+.2f}); nothing to buy.",
               "  To reduce a position you already hold: --side sell --qty N")
    if a.qty is None or not (math.isfinite(a.qty) and a.qty > 0):
        refuse(3, "--qty is required for paper/live and must be positive")

    if a.dry_run:
        print(f"gate     passed for --mode {a.mode}")
        print(f"dry run  would send: {side} {a.qty:g} {s.symbol} market/day → "
              f"{'PAPER' if a.mode == 'paper' else 'LIVE'}. Nothing sent, nothing recorded.")
        return

    import broker
    base = broker.PAPER if a.mode == "paper" else broker.LIVE
    # The same decision — mode, strategy, symbol, bar, side, size — always gets
    # the same order id, so re-running after any failure below cannot send it
    # twice: the broker refuses an id it has already seen. --repeat N makes a
    # deliberate copy a different decision.
    coid = broker.client_order_id("run", a.mode, strat_name, s.symbol,
                                  f"{s.last.ts:%Y-%m-%d}", side, a.qty,
                                  *(("repeat", a.repeat) if a.repeat else ()))
    try:
        hdr = broker.credentials()
        acct = broker.account(base, hdr)
    except broker.NoCredentials as e:
        refuse(5, f"REFUSED: {e}")
    except (broker.Rejected, broker.Unreachable) as e:
        refuse(6, f"NETWORK  {e}", "  Nothing sent.")
    print(f"account  {broker.mask_account(acct['account_number'])} {'PAPER' if acct['paper'] else 'LIVE'} "
          f"status {acct['status']}, equity {acct['equity']}, "
          f"buying power {acct['buying_power']}")
    common = dict(strategy=strat_name, symbol=s.symbol, signal=target, endpoint=base,
                  account=acct["account_number"])

    # 1. Orders an earlier run sent without learning whether they landed. Each
    #    is settled before anything new goes out: an order that did land is
    #    a position this run must not act blind to.
    for ev in unresolved(a.mode, s.symbol):
        c = ev["client_order_id"]
        try:
            o = broker.order_by_client_id(base, hdr, c)
        except broker.Unreachable as e:
            refuse(6, f"NETWORK  {e}",
                   f"  An earlier {ev.get('side')} {ev.get('qty')} {s.symbol} is still UNKNOWN and the",
                   "  broker could not be asked about it. Nothing sent.")
        if o is None:
            ledger.record(a.mode, **{**common, **_carry(ev)}, client_order_id=c,
                          status="not_sent", filled_qty=0.0)
            print(f"         an earlier {ev.get('side')} {ev.get('qty')} {s.symbol} whose outcome was "
                  f"unknown never reached the broker; recorded as not sent")
            continue
        ledger.record(a.mode, **{**common, **_carry(ev)}, client_order_id=c, **broker.summarise(o))
        if c != coid:
            refuse(8, f"NOT SENT — an earlier {o.get('side')} {o.get('qty')} {s.symbol}, whose outcome "
                      f"was unknown, DID reach the broker ({o.get('status')}).",
                   "  It is recorded now. This run sent nothing; re-run to send this order.")

    # 2. This decision's own order may already exist — sent by an earlier run
    #    that crashed, or deliberately run twice. Asked BEFORE the position
    #    check: a full sell that filled leaves nothing held, and the re-run
    #    meant to record it used to be refused as a short.
    try:
        o = broker.order_by_client_id(base, hdr, coid)
    except broker.Unreachable as e:
        refuse(6, f"NETWORK  {e}", "  Nothing sent: the broker could not say whether this "
               "decision's order already exists.")
    sent_now = o is None
    if sent_now:
        if side == "sell":
            try:
                held = broker.positions(base, hdr).get(s.symbol.upper(), 0.0)
            except (broker.Rejected, broker.Unreachable) as e:
                refuse(6, f"NETWORK  {e}", "  Nothing sent: the position could not be read.")
            if not (math.isfinite(held) and a.qty <= held):
                refuse(3, f"REFUSING to sell {a.qty:g} {s.symbol}: {held:g} held.",
                       "  A sell larger than the position opens a short; these tools are long-only.")
        try:
            o = broker.place_order(base, hdr, s.symbol, side, a.qty, client_order_id=coid)
        except (broker.Rejected, broker.Unreachable) as e:
            if isinstance(e, broker.Rejected) and not broker.is_duplicate(e):
                refuse(6, f"REJECTED by broker: {e}", "  Nothing sent.")
            # A failure that may have happened AFTER the broker accepted the
            # order (a timeout, a lost reply), or a duplicate: ask the broker.
            sent_now = not broker.is_duplicate(e)
            lookup_failed = None
            try:
                o = broker.order_by_client_id(base, hdr, coid)
            except broker.Unreachable as e2:
                o, lookup_failed = None, e2
            if o is None and lookup_failed is None and sent_now:
                refuse(6, f"NETWORK  {e}", "  Nothing sent: the broker has no order under this "
                       "decision's id. Safe to re-run.")
            if o is None:
                # Not known either way. Recorded, so the next run asks the
                # broker before it sends anything for this symbol.
                ledger.record(a.mode, **common, client_order_id=coid, status="unknown",
                              side=side, qty=float(a.qty), filled_qty=0.0)
                refuse(6, f"NETWORK  {e}; lookup: "
                          f"{lookup_failed or 'refused as a duplicate, yet no order under its id'}",
                       "  UNKNOWN whether the order reached the broker. Recorded as unknown;",
                       "  the next run asks the broker about it before sending anything.")

    # Recorded the moment it exists at the broker, BEFORE the fill poll: a poll
    # that fails used to end "Nothing recorded" for an order that was live, and
    # the natural retry sent it again.
    wrote = False
    if not settled(a.mode, s.symbol, coid):
        ledger.record(a.mode, **common, client_order_id=coid, **broker.summarise(o))
        wrote = True
    try:
        o = broker.wait_for_fill(base, hdr, o["id"])
    except (broker.Rejected, broker.Unreachable) as e:
        print(f"{a.mode:<8} {side} {a.qty:g} {s.symbol}: "
              f"{'SENT' if sent_now else 'NOT SENT (already at the broker)'}, fill unknown ({e}). "
              f"Recorded as it stood; the broker's order page has the truth.", file=sys.stderr)
        sys.exit(0 if sent_now else 8)

    rec = broker.summarise(o)
    # A fill is recorded when it is MORE than the ledger already holds for this
    # order: once per order, and again when a partial fill completes.
    have = max((ev.get("filled_qty") or 0) for ev in settled(a.mode, s.symbol, coid))
    if rec["filled_qty"] > have:
        ledger.record(a.mode, **common, client_order_id=coid, **rec)
        wrote = True
    if not sent_now:
        print(f"NOT SENT — this decision's order already exists at the broker "
              f"(order {rec['order_id']}, submitted {rec['submitted_at']}): this run sent nothing.")
        print(f"         to send the same order again on purpose: --repeat 2")
    print(f"{a.mode:<8} {rec['side']} {rec['qty']:g} {s.symbol}: {rec['status']}, "
          f"filled {rec['filled_qty']:g}"
          + (f" @ {rec['filled_avg_price']}" if rec["filled_avg_price"] else ""))
    if rec["filled_qty"] <= 0:
        print("         not filled yet — this run does NOT count as paper evidence "
              "for the live gate until it fills", file=sys.stderr)
    print(f"\nrecorded {a.mode} run to the ledger" if wrote else "\nnothing new to record")
    print(f"       python3 ledger.py --report")
    if not sent_now:
        sys.exit(8)


UNSETTLED = ("unknown", "not_sent")


def settled(mode, symbol, coid):
    """This order's records that say what the broker holds — not the 'unknown'
    marker an ambiguous failure leaves, nor the 'not_sent' that resolves one."""
    return [ev for ev in ledger.events(mode, symbol=symbol)
            if ev.get("client_order_id") == coid and ev.get("status") not in UNSETTLED]


def unresolved(mode, symbol):
    """run.py's 'unknown' records for this symbol with nothing after them."""
    last = {}
    for ev in ledger.events(mode, symbol=symbol):
        if ev.get("client_order_id") and not ev.get("autopilot"):
            last[ev["client_order_id"]] = ev
    return [ev for ev in last.values() if ev.get("status") == "unknown"]


def _carry(ev):
    """What an 'unknown' record knew about the order it stands for."""
    return {k: ev[k] for k in ("strategy", "signal") if k in ev}

if __name__ == "__main__":
    main()
