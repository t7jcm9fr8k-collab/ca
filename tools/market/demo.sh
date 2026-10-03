#!/usr/bin/env bash
# demo.sh — the whole loop on synthetic bars, refusals included. No network.
#
# What you will see, in order:
#   1. bars load, with provenance
#   2. barqc passes them, every check with a number
#   3. a backtest, recorded
#   4. paper on an UNTESTED strategy is refused   (exit 3)
#   5. --force without a reason is refused        (exit 4)
#   6. --force with a reason is recorded as a bypass, and the dry run proceeds
#   7. live without a filled paper run is refused (exit 3)
#   8. the ledger report, bypass in red
set -u
# Runs in a throwaway copy. The demo records a backtest and a gate bypass, and it
# used to do that into the REAL out/ledger.json after deleting it — wiping the
# paper fills the live gate reads, the drawdown peak and the trial history — and
# it left bars/SYN-1d.csv among the research files.
here="$(cd "$(dirname "$0")" && pwd)"
work="$(mktemp -d "${TMPDIR:-/tmp}/market-demo.XXXXXX")"
cp "$here"/*.py "$here"/universe.txt "$here"/trials.json "$work"/
cd "$work"
mkdir -p bars out

if [ ! -f bars/SYN-1d.csv ]; then
python3 - <<'PY'
import datetime as dt, csv, random, sys
sys.path.insert(0, ".")
import barqc
random.seed(7)
# The values are seeded; the dates end on the latest session, because paper and
# live refuse bars more than three sessions old and the demo's refusals must be
# the gate's, not the calendar's.
today = dt.datetime.now(dt.timezone.utc).date()
sessions = barqc.sessions_between(today - dt.timedelta(days=400), today)[-250:]
p, rows = 100.0, []
for d in sessions:
    o = p * (1 + random.gauss(0, 0.004)); c = o * (1 + random.gauss(0.0004, 0.012))
    hi = max(o, c) * (1 + abs(random.gauss(0, 0.005))); lo = min(o, c) * (1 - abs(random.gauss(0, 0.005)))
    rows.append((d.isoformat(), round(o,4), round(hi,4), round(lo,4), round(c,4), int(random.lognormvariate(14, .3))))
    p = c
with open("bars/SYN-1d.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["Date","Open","High","Low","Close","Volume"]); w.writerows(rows)
print(f"generated bars/SYN-1d.csv — {len(rows)} synthetic sessions, deterministic")
PY
fi

C="--csv bars/SYN-1d.csv --symbol SYN --source synthetic --adjusted yes"
step(){ printf '\n\033[1m%s\033[0m\n' "$*"; }

step "1 · load"
python3 bars.py $C --show 2

step "2 · inspect"
python3 barqc.py $C

step "3 · backtest, recorded"
python3 run.py --mode backtest --strategy sma_cross:10,30 $C --cost-bps 5

step "4 · paper on an untested strategy — REFUSED"
python3 run.py --mode paper --strategy breakout:20 $C --qty 5 --dry-run; echo "exit $?"

step "5 · --force with no reason — REFUSED"
python3 run.py --mode paper --strategy breakout:20 $C --qty 5 --dry-run --force; echo "exit $?"

step "6 · --force with a reason — recorded as a bypass, then proceeds"
python3 run.py --mode paper --strategy breakout:20 $C --qty 5 --dry-run \
  --force --force-reason "demo: showing what a bypass looks like in the ledger"; echo "exit $?"

step "7 · live without a filled paper run — REFUSED"
python3 run.py --mode live --strategy sma_cross:10,30 $C --qty 1 --dry-run --confirm-live; echo "exit $?"

step "8 · the readout — describes, predicts nothing"
python3 watch.py --symbols SYN

step "9 · the null exercises — each pattern against block-shuffled bars"
python3 nulltest.py $C --shuffles 50 --no-record

step "10 · confluence both ways, with the trial count"
python3 combine.py $C --signals sma_cross:10,30 breakout:20 trend_filter:50 vwap_reclaim:20 \
  --holdout-from 2026-03-01 --no-record

step "11 · the one (c)-grade result, on synthetic minute bars with a planted effect"
python3 intraday.py --synth 300 --effect 0.5 --shuffles 200 --holdout-from 2025-01-01 --no-record | tail -8

step "12 · the ledger"
python3 ledger.py --report
echo
echo "open $work/out/ledger.html — the bypass is the red block. (A throwaway copy; nothing in $here was touched.)"
echo "Nothing here touched a broker. Paper and live run on the Mac, by hand, with keys."
echo "Steps 9–11 ran on SYNTHETIC bars: a random walk with drift. On those, nothing should"
echo "hold up, and nothing does. Run them on bars/SPY-1d.csv and read the numbers there."
