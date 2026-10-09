"""Mutation pass for edgelab: each mutation plants one realistic bug in a scratch
copy; the suite must FAIL on every one. Writes nothing in the repo."""
import os, shutil, subprocess, sys, tempfile

REPO = "/home/user/ca/tools/market"
NEED = ["bars.py", "barqc.py", "replay.py", "combine.py", "ledger.py", "strategies.py",
        "features.py", "edgelab.py", "test_edgelab.py"]

MUTATIONS = [
    ("overnight leg priced close-to-close",
     "r_on = b.open / p.close - 1.0", "r_on = b.close / p.close - 1.0"),
    ("intraday leg priced from the previous close",
     "r_id = b.close / b.open - 1.0", "r_id = b.close / p.close - 1.0"),
    ("cost charged once per round trip (entries only)",
     "            c = n * cost\n            if h <= EPS:\n                entries += 1\n            sides += 1\n            notional += n\n            paid += c\n            paid_frac += c / E\n            E -= c\n            if detail:\n                auctions.append((j, \"close\", n, c))",
     "            c = n * cost if h <= EPS else 0.0\n            if h <= EPS:\n                entries += 1\n            sides += 1\n            notional += n\n            paid += c\n            paid_frac += c / E\n            E -= c\n            if detail:\n                auctions.append((j, \"close\", n, c))"),
    ("cost not charged at the open auction",
     "            c = n * cost\n            if h <= EPS:\n                entries += 1\n            sides += 1\n            notional += n\n            paid += c\n            paid_frac += c / E\n            E -= c\n            if detail:\n                auctions.append((j, \"open\", n, c))",
     "            c = 0.0\n            if h <= EPS:\n                entries += 1\n            sides += 1\n            notional += n\n            paid += c\n            paid_frac += c / E\n            E -= c\n            if detail:\n                auctions.append((j, \"open\", n, c))"),
    ("cash accrued per session, not per calendar day",
     "g = (1.0 + y) ** (D / ACCRUAL_DAYS) - 1.0", "g = (1.0 + y) ** (1 / ACCRUAL_DAYS) - 1.0"),
    ("cash also accrues on the intraday leg",
     "        A *= 1.0 + i_id[j]\n        E = A + C",
     "        A *= 1.0 + i_id[j]\n        C *= 1.0 + g_on[j]\n        E = A + C"),
    ("benchmark bought at bar 0 regardless of warm-up (the EVIDENCE bug)",
     "    s0 = max(r0.warmup, first - 1, 0)\n",
     "    s0 = max(r0.warmup, first - 1, 0)\n    _bench_s0 = max(first - 1, 0)\n"),
    ("open_today allowed at the open auction",
     "        self._open = today_open if auction == \"close\" else None",
     "        self._open = today_open"),
    ("open_today guard removed",
     "        if self.auction != \"close\":\n            raise LookAhead(f\"open_today at the OPEN",
     "        if False:\n            raise LookAhead(f\"open_today at the OPEN"),
    ("view index guard only checks one end",
     "        if k < 0 or k >= self._n:\n            raise LookAhead(f\"bar {k} requested",
     "        if k < 0:\n            raise LookAhead(f\"bar {k} requested"),
    ("leak check reuses one rule instead of rebuilding per sample",
     "        rule = factory()\n        try:\n            got = _weight(",
     "        rule = _REUSED.setdefault(id(factory), factory())\n        try:\n            got = _weight("),
    ("leak check does not truncate at the close auction",
     "            trunc = tuple(bars[:n]) + (_partial(bars[today]),)",
     "            trunc = tuple(bars)"),
    ("leak check does not truncate at the open auction",
     "            trunc = tuple(bars[:n])\n            v = View(trunc, n, \"open\"",
     "            trunc = tuple(bars)\n            v = View(trunc, n, \"open\""),
    ("opex not moved off a holiday Friday",
     "opex = {ym: bisect.bisect_right(self.sessions, third_friday(*ym)) - 1 for ym in months}",
     "opex = {ym: bisect.bisect_left(self.sessions, third_friday(*ym)) for ym in months}"),
    ("pre-holiday rank off by one",
     "                        pre, ahead = j - i, H[hi]", "                        pre, ahead = j - i - 1, H[hi]"),
    ("month ordinal from end off by one",
     "month_ordinal_from_end=k - n,", "month_ordinal_from_end=k - n + 1,"),
    ("leveraged intraday leg naive k*r_id",
     "                i_id = k * r_id * (1.0 + r_on) / base", "                i_id = k * r_id"),
    ("leverage drag without financing",
     "            a = expense_ratio + (k - 1) * y", "            a = expense_ratio"),
    ("deflated Sharpe against zero, not the benchmark",
     "    z = (sr - sr_bench - sr0) * math.sqrt(T - 1) / denom", "    z = (sr - sr0) * math.sqrt(T - 1) / denom"),
    ("halves split at the bar midpoint",
     "    cut = bisect.bisect_right(legs.dates, split)          # sessions [0, cut) are the first half",
     "    cut = len(legs.dates) // 2"),
    ("Sharpe not in excess of cash",
     "    ex = [r - g for r, g in zip(rets, legs.g_on)]\n    years = (legs.dates[-1] - start_date).days / 365.25",
     "    ex = list(rets)\n    years = (legs.dates[-1] - start_date).days / 365.25"),
    ("placebo shift by legs breaks leg types",
     "        u = rng.randrange(1, S)\n        return states[-u:] + states[:-u]",
     "        u = rng.randrange(1, S)\n        flat = [x for s in states for x in s]\n        flat = flat[-1:] + flat[:-1]\n        return [(flat[2*i], flat[2*i+1]) for i in range(S)]"),
    ("placebo seed ignored",
     "    rng = random.Random(f\"edgelab/{seed}/{method}\")", "    rng = random.Random()"),
    ("weight out of range clamped instead of refused",
     "    if not math.isfinite(w) or w < -EPS or w > 1.0 + EPS:", "    if not math.isfinite(w):"),
    ("barqc gate skipped",
     "    if qc[\"verdict\"] == \"blocked\":\n        raise Blocked(f\"barqc blocked",
     "    if False:\n        raise Blocked(f\"barqc blocked"),
    ("calendar ordinal read off bar dates (shifts on a hole)",
     "        self.next_cal = calendar.facts(nxt) if nxt is not None else None\n",
     "        self.next_cal = calendar.facts(nxt) if nxt is not None else None\n"
     "        later = [b.ts.date() for b in bars if b.ts.date() > date]\n"
     "        if later and nxt is not None:\n"
     "            import dataclasses\n"
     "            ym = (later[0].year, later[0].month)\n"
     "            ds = [b.ts.date() for b in bars if (b.ts.date().year, b.ts.date().month) == ym]\n"
     "            self.next_cal = dataclasses.replace(calendar.facts(later[0]), month_ordinal=ds.index(later[0]) + 1)\n"),
    ("drawdown ignores open marks",
     "        m.append((d, \"open\", path[\"opens\"][j]))\n", ""),
    ("bootstrap unpaired (benchmark resampled separately)",
     "            x, y, z = a[i], b[i], g[i]", "            x, y, z = a[i], b[(i * 7 + 3) % n], g[i]"),
    ("dated cash uses the rate at the END of the leg",
     "        y = cash.at(d0)", "        y = cash.at(d1)"),
    ("final-bar partial check never fires",
     "            final[\"suspect_partial\"] = ratio < PARTIAL_BAR_VOLUME", "            final[\"suspect_partial\"] = False"),
]

MUTATIONS += [
    ("engine: close-auction view sees today's full bar (n = u + 1), log agrees",
     "        w = _weight(rule.decide(View(bars, u, \"close\", d, bars[u].open, cal, held, series.symbol,\n                                     leverage)), rule, d, \"close\")\n        log.append((u, \"close\", u, held, w))",
     "        w = _weight(rule.decide(View(bars, u + 1, \"close\", d, bars[u].open, cal, held, series.symbol,\n                                     leverage)), rule, d, \"close\")\n        log.append((u, \"close\", u + 1, held, w))"),
    ("engine: open-auction view one bar short (n = t - 1), log agrees",
     "        w = _weight(rule.decide(View(bars, t, \"open\", d, None, cal, held, series.symbol,\n                                     leverage)), rule, d, \"open\")\n        log.append((t, \"open\", t, held, w))",
     "        w = _weight(rule.decide(View(bars, t - 1, \"open\", d, None, cal, held, series.symbol,\n                                     leverage)), rule, d, \"open\")\n        log.append((t, \"open\", t - 1, held, w))"),
    ("leak check re-decides with held = 0",
     "        today, auction, n, held, w = log[i]", "        today, auction, n, _held, w = log[i]\n        held = 0.0"),
    ("walk keeps drift: trades only on entry or exit",
     "        if dw > EPS or dw < -EPS:", "        if (dw > EPS or dw < -EPS) and (h <= EPS or w <= EPS):", True),
    ("CAGR over bars / 252",
     "    years = (legs.dates[-1] - start_date).days / 365.25\n    st = replay._stats(rets, SESSIONS_PER_YEAR)",
     "    years = len(closes) / 252\n    st = replay._stats(rets, SESSIONS_PER_YEAR)"),
    ("Sortino divides by the count of down sessions",
     "    down = math.sqrt(sum(x * x for x in ex if x < 0) / S) if S else 0.0",
     "    down = math.sqrt(sum(x * x for x in ex if x < 0) / max(1, sum(1 for x in ex if x < 0))) if S else 0.0"),
    ("turnover over final equity instead of mean equity",
     "    mean_eq = sum(closes) / S if S else 0.0", "    mean_eq = closes[-1]"),
    ("leverage weekend drag counted as one day",
     "            delta = (1.0 + a) ** (-D / ACCRUAL_DAYS)", "            delta = (1.0 + a) ** (-1 / ACCRUAL_DAYS)"),
    ("block placebo shuffles gaps and blocks together",
     "        rng.shuffle(b)\n        rng.shuffle(g)\n        a, c = (b, g) if first_block else (g, b)",
     "        allr = b + g\n        rng.shuffle(allr)\n        a, c = allr[:len(b)], allr[len(b):]"),
    ("calendar report calls every missing session a DATA HOLE",
     "                            \"class\": f\"unscheduled closure: {why}\" if why else \"DATA HOLE\"})",
     "                            \"class\": \"DATA HOLE\"})"),
    ("post-holiday rank off by one",
     "                        post = i - j + 1", "                        post = i - j"),
    ("quarter end on any month end",
     "is_quarter_end=last and m in (3, 6, 9, 12),", "is_quarter_end=last,"),
    ("placebo p-value without the +1",
     "    out[\"p_cagr\"] = (1 + sum(1 for x in cagrs if x >= obs_cagr - EPS)) / (1 + draws)\n    out[\"p_sharpe\"] = (1 + sum(1 for x in sharpes if x >= obs_sharpe - EPS)) / (1 + draws)",
     "    out[\"p_cagr\"] = sum(1 for x in cagrs if x >= obs_cagr - EPS) / draws\n    out[\"p_sharpe\"] = sum(1 for x in sharpes if x >= obs_sharpe - EPS) / draws"),
    ("conservative placebo reading takes the smaller p",
     "        res[\"placebo_conservative\"] = {\"p_cagr\": max(pc) if pc else None,\n                                       \"p_sharpe\": max(ps) if ps else None}",
     "        res[\"placebo_conservative\"] = {\"p_cagr\": min(pc) if pc else None,\n                                       \"p_sharpe\": min(ps) if ps else None}"),
    ("test-only rules allowed on files by default",
     "        if factory().test_only and not a.allow_test_rule:", "        if False:"),
    ("default cost silently zero",
     "    if a.cost_bps_per_side is None:\n        ap.error(", "    if a.cost_bps_per_side is None:\n        a.cost_bps_per_side = 0.0\n    if False:\n        ap.error("),
]


def main():
    out = []
    for m in MUTATIONS:
        name, old, new = m[0], m[1], m[2]
        every = len(m) > 3 and m[3]
        d = tempfile.mkdtemp(prefix="edgelab-mut-")
        for f in NEED:
            shutil.copy(os.path.join(REPO, f), d)
        p = os.path.join(d, "edgelab.py")
        src = open(p).read()
        if old not in src:
            out.append(f"NOT APPLIED  {name}  (pattern not found)")
            shutil.rmtree(d)
            continue
        src = src.replace(old, new) if every else src.replace(old, new, 1)
        if name.startswith("benchmark bought at bar 0"):
            # make the benchmark walk use legs from bar 0 by rebuilding them
            src = src.replace("    b_path = walk(ones, ones, legs.r_on, legs.r_id, legs.g_on, cost, detail=True)",
                              "    _bl = build_legs(bars, _bench_s0, last, cash, 1, 0.0, cal)\n"
                              "    _o = [1.0] * len(_bl.r_on)\n"
                              "    b_path = walk(_o, _o, _bl.r_on, _bl.r_id, _bl.g_on, cost, detail=True)\n"
                              "    b_path['closes'] = b_path['closes'][-S:]; b_path['opens'] = b_path['opens'][-S:]\n"
                              "    b_path['start_on'] = b_path['start_on'][-S:]; b_path['start_id'] = b_path['start_id'][-S:]", 1)
        if name.startswith("leak check reuses"):
            src = src.replace("def leak_check(", "_REUSED = {}\n\n\ndef leak_check(", 1)
        open(p, "w").write(src)
        r = subprocess.run([sys.executable, "-B", "test_edgelab.py"], cwd=d, capture_output=True,
                           text=True, timeout=600)
        fails = [l.strip() for l in r.stdout.splitlines() if l.strip().startswith("FAIL")]
        crashed = r.returncode != 0 and not fails
        verdict = ("CAUGHT" if fails else ("CAUGHT (crash)" if crashed else "MISSED"))
        out.append(f"{verdict:<15} {name}  — {len(fails)} failing check(s)"
                   + (f"; first: {fails[0][5:90]}" if fails else "")
                   + (f"; stderr tail: {r.stderr.strip().splitlines()[-1][:120]}" if crashed and r.stderr.strip() else ""))
        shutil.rmtree(d)
    text = "\n".join(out)
    print(text)
    missed = sum(1 for l in out if l.startswith("MISSED") or l.startswith("NOT APPLIED"))
    print(f"\n{len(MUTATIONS)} mutations, {len(MUTATIONS) - missed} caught, {missed} missed/not applied")


if __name__ == "__main__":
    main()
