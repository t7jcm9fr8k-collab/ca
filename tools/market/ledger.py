#!/usr/bin/env python3
"""
ledger.py — the append-only record, and the report you can look at.

WHY APPEND-ONLY
    A run is never edited in place. If a backtest could be overwritten by a
    better one, there would be no record that the worse one happened, and the
    gate in run.py — paper needs a backtest, live needs a paper run — would
    become a formality. A live run sitting below a paper run should PROVE the
    paper run happened.

WHAT IT HOLDS
    Events. Each has a `kind`:
        backtest   a replay result: return, drawdown, fills, the bars' source
        paper      an order sent to a paper endpoint and what came back
        live       an order sent for real money and what came back
        bypass     the gate was skipped with --force, and the stated reason
    Nothing is ever removed.

WHAT IT PRODUCES
    out/ledger.html — every strategy/symbol pair, its backtests, paper runs and
    live runs in order, with bypasses in the same red as a failed check, because
    a reader scanning the ledger needs to see at once which runs earned their
    place and which went around the gate.

USAGE
    python3 ledger.py --report
    python3 ledger.py --show sma_cross_10_30 AAPL
"""

import argparse
import datetime as dt
import contextlib
import html as _html
import json
import os
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
LEDGER = os.path.join(HERE, "out", "ledger.json")
UTC = dt.timezone.utc


def _now():
    return dt.datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")


class Corrupt(Exception):
    """The ledger exists and cannot be read. Nothing may be written over it."""


def _name():
    return os.path.join(os.path.basename(os.path.dirname(LEDGER)), os.path.basename(LEDGER))


def load():
    """
    The ledger, or an empty one when the file does not exist yet. A file that
    EXISTS but cannot be read raises Corrupt instead of reading as empty: an
    empty ledger means "never backtested, never traded, no equity peak", and
    the next record() used to save that over the whole history — silently
    resetting the drawdown peak and the paper evidence the live gate reads.
    """
    if not os.path.exists(LEDGER):
        return {"events": []}
    try:
        with open(LEDGER) as f:
            led = json.load(f)
    except Exception as e:
        raise Corrupt(f"{_name()} exists but cannot be read ({type(e).__name__}: {e}). "
                      f"Nothing was written. Every gate reads it, so nothing that "
                      f"records or trades runs until it is repaired or moved aside.")
    if not isinstance(led, dict) or not isinstance(led.get("events"), list):
        raise Corrupt(f"{_name()} is not a ledger (no 'events' list). Nothing was written.")
    return led


def save(led):
    d = os.path.dirname(LEDGER)
    os.makedirs(d, exist_ok=True)
    # A tmp name of its own: two writers sharing one fixed '.tmp' could each
    # replace the ledger with the other's half-written file.
    fd, tmp = tempfile.mkstemp(dir=d, prefix=".ledger-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(led, f, indent=2, default=str)
        os.replace(tmp, LEDGER)     # atomic; a half-written ledger is worse than none
    except BaseException:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise


@contextlib.contextmanager
def _locked():
    """One writer at a time: record() is read-append-write, and two overlapping
    runs (a cron run and a hand run) used to lose each other's events."""
    try:
        import fcntl
    except ImportError:                       # not POSIX: no lock, as before
        yield
        return
    os.makedirs(os.path.dirname(LEDGER), exist_ok=True)
    with open(LEDGER + ".lock", "a") as lk:
        fcntl.flock(lk, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lk, fcntl.LOCK_UN)


def record(kind, **fields):
    with _locked():
        led = load()
        entry = {"kind": kind, "at": _now(), **fields}
        led["events"].append(entry)
        save(led)
    return entry


def events(kind=None, **match):
    out = []
    for e in load()["events"]:
        if kind and e.get("kind") != kind:
            continue
        if all(e.get(k) == v for k, v in match.items()):
            out.append(e)
    return out


def latest(kind, **match):
    got = events(kind, **match)
    return got[-1] if got else None


def filled_paper_runs(strategy, symbol):
    """The live gate's evidence: paper orders that actually filled."""
    return [e for e in events("paper", strategy=strategy, symbol=symbol)
            if (e.get("filled_qty") or 0) > 0]


REGISTER = os.path.join(HERE, "trials.json")


def prior_trials():
    """
    The trials any new deflated Sharpe must count, and a note saying where the
    number came from.

    out/ledger.json is gitignored, so a fresh clone has none and load() rightly
    reports no events — which crosstest.py used to read as "0 prior trials",
    deflating against 2 where the record says 39. The committed register
    (trials.json) fixes the floor: entries the ledger itself holds are a
    snapshot the live ledger replaces once it has at least as many; entries
    that never reached the ledger are always added on top.
    """
    reg = json.load(open(REGISTER)) if os.path.exists(REGISTER) else {"entries": []}
    snapshot = sum(e["count"] for e in reg["entries"] if e.get("in_ledger"))
    off_ledger = sum(e["count"] for e in reg["entries"] if not e.get("in_ledger"))
    live = len(events("backtest"))
    if live >= snapshot:
        base = f"{live} from out/ledger.json"
    else:
        base = f"{snapshot} from trials.json, out/ledger.json has {live}"
    return max(live, snapshot) + off_ledger, f"{base}; +{off_ledger} recorded only in trials.json"


def leak_refusal(backtest):
    """
    The paper gate's evidence: why this backtest does NOT show the strategy is
    free of look-ahead, or None when it does.

    Only a check that ran and found nothing counts. Both gates used to ask
    "did it fail?" rather than "did it pass?", so a record with no check at all
    read as clean — and combine.py records its trials without one. A combine
    run after a FAILED check therefore made the newest record checkless and
    the gate waved the strategy through; a check that sampled zero bars passed
    the same way. One definition here, so run.py and autopilot.py cannot drift.
    """
    lk = backtest.get("leak_check")
    if not lk:
        return "has no leak check (combine.py records its trials without one)"
    if not lk.get("checked"):
        return "has a leak check that sampled 0 bars"
    if lk.get("differences"):
        return (f"failed its leak check ({len(lk['differences'])} of "
                f"{lk['checked']} bars decided differently with the future removed)")
    return None


# ---------------------------------------------------------------- report

CSS = """
:root{--paper:#faf8f4;--plate:#fffefb;--rule:#e3ded2;--ink:#16150f;--muted:#6e685c;
  --amber:#b8701c;--pass:#2f6e45;--block:#a83232;--wash:#f3efe6;
  --mono:ui-monospace,SFMono-Regular,Menlo,monospace;--body:system-ui,sans-serif}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--paper:#131210;
  --plate:#1b1a16;--rule:#33302a;--ink:#efece4;--muted:#9a9384;--amber:#e0a24e;
  --pass:#63b183;--block:#e08078;--wash:#211f1a}}
:root[data-theme="dark"]{--paper:#131210;--plate:#1b1a16;--rule:#33302a;--ink:#efece4;
  --muted:#9a9384;--amber:#e0a24e;--pass:#63b183;--block:#e08078;--wash:#211f1a}
*{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);
  font:16px/1.6 var(--body)}.sheet{max-width:1040px;margin:0 auto;padding:48px 24px 80px}
h1{font-size:28px;margin:0 0 6px;border-bottom:2px solid var(--ink);padding-bottom:14px}
.meta{font:12px/1 var(--mono);color:var(--muted);margin:10px 0 36px;display:flex;gap:20px}
.legend{background:var(--wash);border-left:3px solid var(--amber);padding:14px 18px;
  margin:0 0 36px;font-size:14.5px;max-width:66ch}
.plate{background:var(--plate);border:1px solid var(--rule);border-radius:3px;
  padding:26px;margin-bottom:22px}.plate h2{margin:0 0 2px;font-size:20px}
.slug{font:11.5px/1 var(--mono);color:var(--muted);margin-bottom:18px;letter-spacing:.04em}
table{width:100%;border-collapse:collapse;font-variant-numeric:tabular-nums;margin:8px 0 18px}
th{text-align:left;font:600 10px/1 var(--mono);letter-spacing:.12em;text-transform:uppercase;
  color:var(--muted);padding:0 10px 8px;border-bottom:1px solid var(--ink)}
td{padding:8px 10px;border-bottom:1px solid var(--rule);font-size:14px}
td.n,th.n{text-align:right;font-family:var(--mono);font-size:12.5px}
h3{font:600 12px/1 var(--mono);letter-spacing:.1em;text-transform:uppercase;margin:16px 0 6px}
.kind{display:inline-block;font:600 10px/1 var(--mono);letter-spacing:.12em;
  text-transform:uppercase;padding:4px 8px;border-radius:2px}
.kind.paper{color:var(--amber);background:color-mix(in srgb,var(--amber) 14%,transparent)}
.kind.live{color:var(--block);background:color-mix(in srgb,var(--block) 14%,transparent)}
.kind.backtest{color:var(--pass);background:color-mix(in srgb,var(--pass) 12%,transparent)}
.bypass{background:color-mix(in srgb,var(--block) 10%,transparent);
  border-left:3px solid var(--block);color:var(--block);padding:12px 16px;margin:10px 0;
  font-size:14px;max-width:70ch}.bypass strong{font-weight:600}
.none{color:var(--muted);font-style:italic}
"""


def _pct(x):
    return f"{x:+.1%}" if isinstance(x, (int, float)) else ""


def build_report(led, out_dir):
    groups = {}
    for e in led.get("events", []):
        # Escaped once, here: bypass reasons, broker statuses and ids are free
        # text and used to be interpolated into the HTML as they came.
        e = {k: (_html.escape(v) if isinstance(v, str) else v) for k, v in e.items()}
        key = (e.get("strategy") or "?", e.get("symbol") or "?")
        groups.setdefault(key, []).append(e)

    plates = []
    for (strat, sym), evs in sorted(groups.items()):
        p = [f'<section class="plate"><h2>{strat} · {sym}</h2>'
             f'<div class="slug">{len(evs)} event(s)</div>']

        bts = [e for e in evs if e["kind"] == "backtest"]
        if bts:
            p.append('<h3>Backtests</h3><table><thead><tr><th>when</th>'
                     '<th class="n">bars</th><th class="n">return</th>'
                     '<th class="n">buy&amp;hold</th><th class="n">max dd</th>'
                     '<th class="n">fills</th><th class="n">bps</th><th>source</th>'
                     '</tr></thead><tbody>')
            for e in bts:
                p.append(f'<tr><td>{e["at"]}</td><td class="n">{e.get("bars","")}</td>'
                         f'<td class="n">{_pct(e.get("return"))}</td>'
                         f'<td class="n">{_pct(e.get("benchmark"))}</td>'
                         f'<td class="n">{_pct(e.get("max_drawdown"))}</td>'
                         f'<td class="n">{e.get("fills","")}</td>'
                         f'<td class="n">{e.get("cost_bps","")}</td>'
                         f'<td>{e.get("source","")}</td></tr>')
            p.append("</tbody></table>")

        for kind in ("paper", "live"):
            runs = [e for e in evs if e["kind"] == kind]
            if runs:
                p.append(f'<h3><span class="kind {kind}">{kind}</span></h3>'
                         '<table><thead><tr><th>when</th><th>side</th>'
                         '<th class="n">qty</th><th>status</th>'
                         '<th class="n">filled</th><th class="n">avg price</th>'
                         '<th>order id</th></tr></thead><tbody>')
                for e in runs:
                    p.append(f'<tr><td>{e["at"]}</td><td>{e.get("side","")}</td>'
                             f'<td class="n">{e.get("qty","")}</td>'
                             f'<td>{e.get("status","")}</td>'
                             f'<td class="n">{e.get("filled_qty","")}</td>'
                             f'<td class="n">{e.get("filled_avg_price","")}</td>'
                             f'<td><code>{e.get("order_id","")}</code></td></tr>')
                p.append("</tbody></table>")

        for e in [e for e in evs if e["kind"] == "bypass"]:
            p.append(f'<div class="bypass"><strong>Gate bypassed</strong> '
                     f'{e["at"]} — <code>--mode {e.get("mode")}</code> ran without '
                     f'{e.get("missing", "its required record")}. '
                     f'Stated reason: {e.get("reason") or "none given"}</div>')

        p.append("</section>")
        plates.append("".join(p))

    n = len(led.get("events", []))
    html = f"""<title>Run Ledger</title>
<style>{CSS}</style>
<div class="sheet">
  <h1>Run ledger</h1>
  <div class="meta"><span>{len(groups)} strategy/symbol pair(s)</span>
    <span>{n} event(s)</span><span>{_now()}</span></div>
  <p class="legend"><strong>How to read this.</strong> Every event is appended,
  never edited. A paper run sits below the backtest that earned it and a live run
  below the paper run that earned it; if one is missing, the run above it should
  not exist. A <strong>Gate bypassed</strong> block means it exists anyway, and
  says why. Backtest returns are after the stated per-fill cost and model nothing
  else — no order book, no partial fills, no dividends.</p>
  {"".join(plates) or '<p class="none">Ledger is empty.</p>'}
</div>"""
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "ledger.html")
    open(path, "w").write(html)
    return path


def _mask(number):
    """As broker.mask_account: the last four characters."""
    s = str(number or "")
    return ("…" + s[-4:]) if len(s) > 4 else s


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--show", nargs=2, metavar=("STRATEGY", "SYMBOL"))
    ap.add_argument("--out", default=os.path.join(HERE, "out"))
    a = ap.parse_args()

    try:
        led = load()
    except Corrupt as e:                 # a clean refusal, not a traceback
        raise SystemExit(f"REFUSED: {e}")
    if a.show:
        # The account number stays in out/ledger.json; what is printed may end
        # up in a transcript or a committed runs/ file, so it is masked as
        # run.py masks it.
        got = [{**e, "account": _mask(e["account"])} if e.get("account") else e
               for e in events(strategy=a.show[0], symbol=a.show[1])]
        print(json.dumps(got, indent=2, default=str, ensure_ascii=False) if got else
              f"no events for {a.show[0]} {a.show[1]}")
        return
    path = build_report(led, a.out)
    print(f"wrote {path}")
    kinds = {}
    for e in led["events"]:
        kinds[e["kind"]] = kinds.get(e["kind"], 0) + 1
    for k, v in sorted(kinds.items()):
        print(f"  {k:<10} {v}")


if __name__ == "__main__":
    main()
