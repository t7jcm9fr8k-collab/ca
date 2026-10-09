"""Two independent calendar builds must agree: edgelab.Calendar (scheduled)
against the Quartermaster's nyse-sessions-1999-2026.csv and opex-1999-2026.csv.
Dates only — no prices."""
import csv, datetime as dt, sys
sys.path.insert(0, "/home/user/ca/tools/market")
import edgelab as E
C = "/tmp/claude-0/-home-user-ca/2758dbcb-e96c-587b-81c2-e59b0c402304/scratchpad/edge/data/calendar"
rows = list(csv.DictReader(open(f"{C}/nyse-sessions-1999-2026.csv")))
cal = E.Calendar(dt.date(1999, 1, 4), dt.date(2026, 12, 31))
mism = {"session": 0, "ord_start": 0, "ord_end": 0, "n_month": 0, "quarter_end": 0, "year_end": 0,
        "pre_holiday": 0, "post_holiday": 0, "opex": 0}
ex = []
n = 0
for r in rows:
    d = dt.date.fromisoformat(r["date"])
    sched = r["scheduled_session"] == "1"
    if sched != cal.is_session(d):
        mism["session"] += 1; ex.append(("session", r["date"])); continue
    if not sched:
        continue
    n += 1
    f = cal.facts(d)
    chk = [("ord_start", int(r["ord_from_start_sched"]), f.month_ordinal),
           ("ord_end", int(r["ord_from_end_sched"]), f.month_ordinal_from_end),
           ("n_month", int(r["sessions_in_month_sched"]), f.month_sessions),
           ("quarter_end", r["quarter_end"] == "1", f.is_quarter_end),
           ("year_end", r["year_end"] == "1", f.is_year_end),
           ("pre_holiday", bool(r["last_session_before_holiday"]), f.pre_holiday_rank == 1),
           ("post_holiday", bool(r["first_session_after_holiday"]), f.post_holiday_rank == 1),
           ("opex", r["monthly_opex"] == "1", f.is_opex)]
    for k, a, b in chk:
        if a != b:
            mism[k] += 1
            if len(ex) < 12:
                ex.append((k, r["date"], a, b))
op = list(csv.DictReader(open(f"{C}/opex-1999-2026.csv")))
opex_mis = [o["expiration_trading_date"] for o in op
            if cal.opex(*map(int, o["expiration_trading_date"][:7].split("-"))).isoformat() != o["expiration_trading_date"]]
print(f"rows {len(rows)}, scheduled sessions compared {n}")
print("mismatches by field:", mism)
print("examples:", ex)
print(f"opex rows {len(op)}, mismatches {len(opex_mis)} {opex_mis[:5]}")
