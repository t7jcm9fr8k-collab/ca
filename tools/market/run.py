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

EXIT CODES
    2  data refused (unparseable, or barqc blocked it)
    3  gate refused (no backtest / no filled paper run / no --confirm-live)
    4  --force without --force-reason
    5  no broker credentials
    6  broker unreachable or order rejected

USAGE
    python3 run.py --mode signal   --strategy sma_cross:10,30 --csv bars/AAPL-1d.csv --symbol AAPL
    python3 run.py --mode backtest --strategy sma_cross:10,30 --csv bars/AAPL-1d.csv --symbol AAPL --cost-bps 5
    python3 run.py --mode paper    --strategy sma_cross:10,30 --csv bars/AAPL-1d.csv --symbol AAPL --qty 10
    python3 run.py --mode live     --strategy sma_cross:10,30 --csv bars/AAPL-1d.csv --symbol AAPL --qty 1 --confirm-live
"""

import argparse
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
        if ledger.latest("backtest", strategy=strat_name, symbol=a.symbol) is None:
            need.append("a recorded backtest")
    if a.mode == "live":
        if not ledger.filled_paper_runs(strat_name, a.symbol):
            need.append("a paper run that filled")
    if not need:
        return
    missing = " and ".join(need)
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
    gate(a, strat_name)

    side = a.side or ("buy" if target > 0 else None)
    if side is None:
        refuse(3, f"strategy says flat ({target:+.2f}); nothing to buy.",
               "  To reduce a position you already hold: --side sell --qty N")
    if not a.qty or a.qty <= 0:
        refuse(3, "--qty is required for paper/live and must be positive")

    if a.dry_run:
        print(f"gate     passed for --mode {a.mode}")
        print(f"dry run  would send: {side} {a.qty:g} {s.symbol} market/day → "
              f"{'PAPER' if a.mode == 'paper' else 'LIVE'}. Nothing sent, nothing recorded.")
        return

    import broker
    base = broker.PAPER if a.mode == "paper" else broker.LIVE
    try:
        hdr = broker.credentials()
        acct = broker.account(base, hdr)
        print(f"account  {acct['account_number']} {'PAPER' if acct['paper'] else 'LIVE'} "
              f"status {acct['status']}, equity {acct['equity']}, "
              f"buying power {acct['buying_power']}")
        o = broker.place_order(base, hdr, s.symbol, side, a.qty)
        o = broker.wait_for_fill(base, hdr, o["id"])
    except broker.NoCredentials as e:
        refuse(5, f"REFUSED: {e}")
    except broker.Rejected as e:
        refuse(6, f"REJECTED by broker: {e}", "  Nothing recorded.")
    except broker.Unreachable as e:
        refuse(6, f"NETWORK  {e}", "  Nothing recorded. Unreachable is not a fill.")

    rec = broker.summarise(o)
    ledger.record(a.mode, strategy=strat_name, symbol=s.symbol, signal=target,
                  endpoint=base, account=acct["account_number"], **rec)
    print(f"{a.mode:<8} {rec['side']} {rec['qty']:g} {s.symbol}: {rec['status']}, "
          f"filled {rec['filled_qty']:g}"
          + (f" @ {rec['filled_avg_price']}" if rec["filled_avg_price"] else ""))
    if rec["filled_qty"] <= 0:
        print("         not filled yet — this run does NOT count as paper evidence "
              "for the live gate until it fills", file=sys.stderr)
    print(f"\nrecorded {a.mode} run to the ledger")
    print(f"       python3 ledger.py --report")


if __name__ == "__main__":
    main()
