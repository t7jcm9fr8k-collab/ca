#!/usr/bin/env python3
"""cash_probe.py — four low-volume GETs to api.nasdaq.com through fetch.py's own
_get (repo User-Agent, verifying TLS, its retry policy). Saves each raw body.
Run: python3 -I -B cash_probe.py <tools/market> <out dir>"""
import datetime as dt, json, os, sys, time
TOOLS, OUT = sys.argv[1:3]
sys.path.insert(0, TOOLS)
import fetch as F
H = {"User-Agent": F.BROWSER_UA, "Accept": "application/json"}
probes = [
    ("SHV-dividends", "https://api.nasdaq.com/api/quote/SHV/dividends?assetclass=etf"),
    ("TLT-dividends", "https://api.nasdaq.com/api/quote/TLT/dividends?assetclass=etf"),
    ("BIL-dividends", "https://api.nasdaq.com/api/quote/BIL/dividends?assetclass=etf"),
    ("IRX-index-historical", "https://api.nasdaq.com/api/quote/IRX/historical?assetclass=index&fromdate=2016-01-01&limit=9999&todate=2026-10-09"),
]
log = []
for name, url in probes:
    t = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    try:
        body = F._get(url, headers=H)
        open(os.path.join(OUT, f"{name}.json"), "w").write(body)
        try:
            j = json.loads(body)
            msg = (j.get("message") or "") if isinstance(j, dict) else ""
            data = j.get("data") if isinstance(j, dict) else None
            rows = None
            if isinstance(data, dict):
                d = data.get("dividends") or data.get("tradesTable") or {}
                rows = d.get("rows") if isinstance(d, dict) else None
            summary = f"OK  rows={len(rows) if rows else 0}  message={msg!r}  status={j.get('status')}"
        except Exception as e:
            summary = f"OK  (not JSON: {type(e).__name__}) starts {body[:80]!r}"
    except F.Unreachable as e:
        summary = f"NETWORK  {e}"
    log.append(f"{t}  {name}  {url}\n    {summary}")
    print(log[-1])
    time.sleep(3)
open(os.path.join(OUT, "probe-log.txt"), "w").write("\n".join(log) + "\n")
