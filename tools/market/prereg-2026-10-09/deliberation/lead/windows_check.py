"""Lead's third, independent build of the month-end window list (calendar and bar DATES only; no price is read)."""
import csv, datetime as dt, sys
sys.path.insert(0, "/home/user/ca/tools/market")
import barqc

def bar_dates(path):
    with open(path) as f:
        r = csv.reader(f)
        head = next(r)
        i = [h.lower() for h in head].index("date")
        return sorted(dt.date.fromisoformat(row[i][:10]) for row in r if row and row[i][:1].isdigit())

def windows(bars_path, first_month, last_month, last_scored_bar):
    bd = [d for d in bar_dates(bars_path) if d <= last_scored_bar]
    sched = barqc.sessions_between(dt.date(first_month[0], first_month[1], 1) - dt.timedelta(days=40),
                                   dt.date(last_month[0], last_month[1], 28) + dt.timedelta(days=40))
    pos = {d: i for i, d in enumerate(sched)}
    out = []
    y, m = first_month
    while (y, m) <= last_month:
        T = max(d for d in sched if (d.year, d.month) == (y, m))
        ent_s, ext_s = sched[pos[T] - 4], sched[pos[T] + 3]
        nxt = lambda d: next((b for b in bd if b >= d), None)
        ent_e, ext_e = nxt(ent_s), nxt(ext_s)
        complete = bd[0] <= ent_s and ext_e is not None
        out.append((f"{y:04d}-{m:02d}", T, ent_s, ent_e, ext_s, ext_e, complete))
        y, m = (y + (m == 12), m % 12 + 1)
    return out

def compare(mine, qm_csv):
    qm = list(csv.DictReader(open(qm_csv)))
    diffs = 0
    for a, b in zip(mine, qm):
        got = (a[0], str(a[1]), str(a[2]), str(a[3]), str(a[4]), str(a[5]), str(a[6]))
        exp = (b["month"], b["T"], b["entry_sched"], b["entry_exec"], b["exit_sched"], b["exit_exec"], b["complete"])
        if got != exp:
            diffs += 1
            print("DIFF", got, exp)
    print(f"{qm_csv.split('/')[-1]}: mine {len(mine)} rows, quartermaster {len(qm)} rows, differences {diffs + abs(len(mine) - len(qm))}")
    return [w for w in mine if w[6]]

S = sys.argv[1]
spy = windows("bars/SPY-1d.csv", (2005, 2), (2026, 8), dt.date(2026, 9, 1))
cs = compare(spy, f"{S}/quartermaster/r2/windows-S1-SPY.csv")
print("S1 complete windows:", len(cs), "first entry", cs[0][3], "last complete exit", cs[-1][5])
qqq = windows("bars/QQQ-1d-long.csv", (1999, 2), (2005, 2), dt.date(2005, 2, 24))
cq = compare(qqq, f"{S}/quartermaster/r2/windows-G7-QQQ.csv")
print("G7 complete windows:", len(cq), "first entry", cq[0][3], "last complete exit", cq[-1][5])
for w in spy:
    if w[2] != w[3] or w[4] != w[5]:
        print("S1 boundary moved:", w)
