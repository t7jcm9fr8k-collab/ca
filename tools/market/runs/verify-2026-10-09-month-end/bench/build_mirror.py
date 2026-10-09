"""SYNTHETIC. A mirror of tools/market/ for checking the frozen invocation end to end without the real
bar files: the code and the frozen inputs are copied; bars/SPY-1d.csv and bars/QQQ-1d-long.csv are
SYNTHETIC prices laid on the scheduled NYSE calendar minus the dates the real files are known to lack
(the same construction as the round-2 timing run; no real bar file is opened)."""
import datetime as dt, os, shutil, sys
REPO = "/home/user/ca/tools/market"
M = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mirror")
if os.path.exists(M):
    shutil.rmtree(M)
os.makedirs(os.path.join(M, "bars"))
os.makedirs(os.path.join(M, "runs"))
for f in ("edgelab.py", "bars.py", "barqc.py", "replay.py", "combine.py", "ledger.py", "strategies.py",
          "features.py", "PREREG-2026-10-09-month-end.md", "trials.json"):
    shutil.copy(os.path.join(REPO, f), M)
P = os.path.join(M, "prereg-2026-10-09")
os.makedirs(os.path.join(P, "deliberation", "data", "events"))
for f in ("invocation.sh", "windows-S1-SPY.csv", "windows-G7-QQQ.csv", "spy-distributions-2025-2026.csv"):
    shutil.copy(os.path.join(REPO, "prereg-2026-10-09", f), P)
shutil.copy(os.path.join(REPO, "prereg-2026-10-09", "deliberation", "data", "events", "fomc-statements-2005-2026.csv"),
            os.path.join(P, "deliberation", "data", "events"))
sys.path.insert(0, M)
import bars as B, barqc, edgelab as E

def write(path, start, end, missing, seed, symbol):
    dates = [d for d in barqc.sessions_between(start, end) if d not in missing]
    s = E.synthetic_like(dates, seed=seed, symbol=symbol)
    B.to_csv(s, path)
    return len(dates)

spy_missing = {dt.date(2007, 1, 2), dt.date(2012, 10, 29), dt.date(2012, 10, 30), dt.date(2018, 12, 5),
               dt.date(2025, 1, 9), dt.date(2011, 2, 17)}
qqq_missing = {dt.date(2001, 9, 11), dt.date(2001, 9, 12), dt.date(2001, 9, 13), dt.date(2001, 9, 14),
               dt.date(2004, 6, 11), dt.date(1999, 11, 16)}
print("SPY rows", write(os.path.join(M, "bars", "SPY-1d.csv"), dt.date(2005, 2, 25), dt.date(2026, 9, 2),
                        spy_missing, 31, "SPY"))
print("QQQ rows", write(os.path.join(M, "bars", "QQQ-1d-long.csv"), dt.date(1999, 3, 10), dt.date(2005, 2, 24),
                        qqq_missing, 32, "QQQ"))
print("mirror", M)
