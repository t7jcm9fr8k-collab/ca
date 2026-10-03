#!/usr/bin/env python3
"""
basis.py — measure whether two bar files sit on the same dividend basis.

`--adjusted` records what you tell it; nothing else in this pipeline measures
it (README, "If Stooq returns a web page"). This does. For each symbol it loads
two files through bars.load_csv, intersects their dates, and prints the gap
between their closes on every shared date:

    gap% = (A - B) / B x 100

A total-return series sits BELOW a price-only one in the past and converges to
it at the last bar, stepping down on ex-dividend dates. So a gap near zero
throughout says "same basis"; one that starts at several percent and shrinks
to zero says one file carries reinvested distributions and the other does not,
and its sign says which. A symbol that pays nothing (GLD) is the control: it
should read 0.000 whatever the files are, and if it does not, something other
than dividends is scaling them apart. Like barqc, this reports numbers, not a
verdict — what a 2.9% median gap means is the reader's call.

    python3 basis.py --a 'bars/{s}-1d-long.csv' --a-source stooq \\
                     --b 'bars/{s}-1d.csv' --b-source alpaca \\
                     --symbols DIA EEM EFA GLD IWM QQQ TLT XLE XLF
    python3 basis.py --a bars/SPY-1d.csv --a-source stooq \\
                     --b bars/SPY-1d-raw.csv --b-source nasdaq --symbols SPY
    python3 basis.py --a 'bars/{s}-1d-long.csv' --windows \\
                     --symbols DIA EEM EFA GLD IWM QQQ TLT XLE XLF SPY=bars/SPY-1d.csv
    python3 basis.py ... --rank

`{s}` in a path is replaced by each symbol; `SYM=path` in --symbols overrides
the --a path for that one symbol (SPY's long file is not named like the rest).

--windows   the date intersection a universe of --a files gets when it is
            aligned (portfolio.align intersects, never forward-fills), and for
            each file where its unshared dates sit: before the shared start,
            after the shared end, or inside it — a hole in someone else's file.
--rank      drives portfolio.PortfolioCursor and portfolio.xsmom() exactly as
            implemented — the definition is theirs, not this file's — over the
            dates where both bases exist, and reports how often the two pick
            the same top-3 book. No return, no Sharpe, no p-value, nothing
            recorded to the ledger: it measures the signal's INPUT.

A pair that shares no dates is REFUSED (exit 2). Two files with nothing in
common have no basis to compare, and an empty table reads as agreement.
"""
import argparse
import statistics
import sys

import bars as B
import portfolio as P


class NoOverlap(Exception):
    pass


def _closes(series):
    return {b.ts.date(): b.close for b in series.bars}


def gap(a, b):
    """gap% of A against B on every shared date. Raises NoOverlap when none."""
    ca, cb = _closes(a), _closes(b)
    common = sorted(set(ca) & set(cb))
    if not common:
        raise NoOverlap(f"{a.symbol}: the two files share no dates — nothing to compare")
    g = []
    for d in common:
        if cb[d] <= 0:
            raise ValueError(f"{b.symbol}: non-positive close on {d}")
        g.append((ca[d] - cb[d]) / cb[d] * 100.0)
    return {"symbol": a.symbol, "common": len(common), "from": common[0], "to": common[-1],
            "median": statistics.median(g), "first": g[0], "last": g[-1],
            "min": min(g), "max": max(g)}


def windows(serieses):
    """The shared window of an aligned universe, and where each file's other dates sit."""
    sets = {s.symbol: {b.ts.date() for b in s.bars} for s in serieses}
    shared = set.intersection(*sets.values())
    if not shared:
        raise NoOverlap("the files share no dates — an aligned run would have nothing to walk")
    lo, hi = min(shared), max(shared)
    per = {}
    for sym, ds in sets.items():
        extra = ds - shared
        per[sym] = {"dates": len(ds),
                    "before": sum(1 for d in extra if d < lo),
                    "after": sum(1 for d in extra if d > hi),
                    "inside": sorted(d for d in extra if lo <= d <= hi)}
    return {"shared": len(shared), "from": lo, "to": hi, "per": per}


def _ranks(vals):
    order = sorted(range(len(vals)), key=lambda i: vals[i])
    r, i = [0.0] * len(vals), 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and vals[order[j + 1]] == vals[order[i]]:
            j += 1
        for k in range(i, j + 1):
            r[order[k]] = (i + j) / 2.0 + 1.0
        i = j + 1
    return r


def spearman(a, b):
    ra, rb = _ranks(a), _ranks(b)
    n = len(a)
    ma, mb = sum(ra) / n, sum(rb) / n
    num = sum((ra[i] - ma) * (rb[i] - mb) for i in range(n))
    da = sum((x - ma) ** 2 for x in ra) ** 0.5
    db = sum((x - mb) ** 2 for x in rb) ** 0.5
    return num / (da * db) if da and db else float("nan")


def rank(a_series, b_series, top=3):
    """
    How much the basis moves portfolio.xsmom()'s book. Same symbols on both
    sides; walked over the dates every one of the 2N files shares.
    """
    syms = [s.symbol for s in a_series]
    if sorted(syms) != sorted(s.symbol for s in b_series):
        raise ValueError("--rank needs the same symbols on both sides")
    if len(syms) <= top:
        raise ValueError(f"--rank needs more than {top} symbols to rank")
    by_a = {s.symbol: {b.ts: b for b in s.bars} for s in a_series}
    by_b = {s.symbol: {b.ts: b for b in s.bars} for s in b_series}
    common = set.intersection(*[set(m) for m in list(by_a.values()) + list(by_b.values())])
    if not common:
        raise NoOverlap("the two bases share no dates — nothing to rank")
    dates = sorted(common)
    al_a = {s: tuple(by_a[s][d] for d in dates) for s in syms}
    al_b = {s: tuple(by_b[s][d] for d in dates) for s in syms}
    weigh = P.xsmom(top=top)
    rows = []
    for i in P.month_end_indices(dates):
        ca = P.PortfolioCursor(al_a, dates, i + 1)
        cb = P.PortfolioCursor(al_b, dates, i + 1)
        sa = [ca.trailing_return(s, 12, skip_months=1) for s in syms]
        sb = [cb.trailing_return(s, 12, skip_months=1) for s in syms]
        if None in sa or None in sb:
            continue
        ta, tb = set(weigh(ca)), set(weigh(cb))
        if not ta or not tb:
            continue
        rows.append({"date": dates[i], "rho": spearman(sa, sb), "same": ta == tb,
                     "a": sorted(ta), "b": sorted(tb)})
    if not rows:
        raise NoOverlap("no month end has a full 13-month window on both bases")
    return {"sessions": len(dates), "from": dates[0], "to": dates[-1], "rows": rows,
            "weigh": weigh.__name__}


def render_gap(rows):
    out = ["gap% = (A - B) / B x 100, per shared date",
           f"{'SYM':5} {'COMMON':>7} {'MEDIAN%':>9} {'FIRST%':>9} {'LAST%':>9} {'MIN%':>9} {'MAX%':>9}",
           "-" * 62]
    for r in rows:
        out.append(f"{r['symbol']:5} {r['common']:>7} {r['median']:>9.3f} {r['first']:>9.3f} "
                   f"{r['last']:>9.3f} {r['min']:>9.3f} {r['max']:>9.3f}")
    return "\n".join(out)


def render_windows(w):
    out = [f"shared window: {w['shared']} dates, {w['from']} -> {w['to']}",
           f"{'SYM':5} {'DATES':>6} {'BEFORE':>7} {'AFTER':>6} {'INSIDE':>7}  inside, unshared",
           "-" * 62]
    for sym, p in w["per"].items():
        ins = ", ".join(str(d) for d in p["inside"][:4]) + (" ..." if len(p["inside"]) > 4 else "")
        out.append(f"{sym:5} {p['dates']:>6} {p['before']:>7} {p['after']:>6} {len(p['inside']):>7}  {ins}")
    return "\n".join(out)


def render_rank(r):
    rows = r["rows"]
    rhos = [x["rho"] for x in rows]
    same = sum(1 for x in rows if x["same"])
    out = [f"basis sensitivity of {r['weigh']} over {r['sessions']} shared sessions, "
           f"{r['from']:%Y-%m-%d} -> {r['to']:%Y-%m-%d}",
           f"rebalances with a full 13-month window on both bases: {len(rows)} "
           f"({rows[0]['date']:%Y-%m-%d} -> {rows[-1]['date']:%Y-%m-%d})",
           f"Spearman rank correlation, A vs B: median {statistics.median(rhos):.4f}   "
           f"min {min(rhos):.4f}   max {max(rhos):.4f}   mean {statistics.mean(rhos):.4f}",
           f"top-{len(rows[0]['a'])} book identical: {same} of {len(rows)} "
           f"({100.0 * same / len(rows):.1f}%)",
           "", f"{'DATE':12} {'RHO':>7}  {'A picks':28} {'B picks':28}", "-" * 80]
    for x in rows:
        if not x["same"]:
            out.append(f"{x['date']:%Y-%m-%d}   {x['rho']:>7.4f}  {','.join(x['a']):28} {','.join(x['b']):28}")
    out.append("No return, no Sharpe, no p-value, nothing recorded: the signal's input only.")
    return "\n".join(out)


def _load(template, sym, source, override=None):
    path = override or template.replace("{s}", sym)
    return B.load_csv(path, sym, "1d", source, None)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--a", required=True, help="path or {s} template — the file under test")
    ap.add_argument("--b", help="path or {s} template — the reference")
    ap.add_argument("--a-source")
    ap.add_argument("--b-source")
    ap.add_argument("--symbols", nargs="+", required=True, help="SYM, or SYM=path to override --a")
    ap.add_argument("--windows", action="store_true", help="the aligned universe's shared window")
    ap.add_argument("--rank", action="store_true", help="does the basis move xsmom's book?")
    a = ap.parse_args()

    pairs = [s.split("=", 1) if "=" in s else (s, None) for s in a.symbols]
    try:
        side_a = [_load(a.a, sym.upper(), a.a_source, ov) for sym, ov in pairs]
        side_b = [_load(a.b, sym.upper(), a.b_source) for sym, _ in pairs] if a.b else None
        if a.windows:
            print(render_windows(windows(side_a)))
        if side_b is not None and not a.windows:
            print(render_gap([gap(x, y) for x, y in zip(side_a, side_b)]))
        if a.rank:
            if side_b is None:
                sys.exit("REFUSED: --rank needs --b")
            print()
            print(render_rank(rank(side_a, side_b)))
        if side_b is None and not a.windows:
            sys.exit("REFUSED: give --b to measure a gap, or --windows")
    except (B.Unparseable, B.NoProvenance, NoOverlap, ValueError, FileNotFoundError) as e:
        print(f"REFUSED: {e}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
