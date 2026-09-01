#!/usr/bin/env python3
"""
rival.py — count the competition for each design, and track it over time.

Runs on the Mac. It cannot run from a cloud session; etsy.com is unreachable
from there, which is exactly why the failure path below matters.

WHAT THIS IS FOR
    The 2026-08-17 competition check was done by hand: fetch Etsy search results
    for a phrase, count the titles genuinely selling that idea. It worked, and
    then it was a one-off — the method survived in DESIGN-CONCEPTS.md, the
    mechanics did not. This makes it repeatable and adds the thing a one-off
    cannot have: HISTORY. A niche that was empty in September and crowded in
    November is a fact you can only see by looking twice.

    It matters more now than it did. The composite categories — botanical skull,
    moth, dark academia, cottagecore — have real demand AND real competition,
    where the old text phrases had neither.

WHAT IT DELIBERATELY DOES NOT DO
    No revenue estimates. REFERENCE-PRODUCTS.md settled this: no third-party
    tool has Etsy backend access, every EverBee/eRank/Alura number is inferred
    from public signals, and the Etsy Open API is seller-scoped with no
    competitor data at all. Counting titles is a thing you can actually verify.
    Guessing a competitor's revenue is not.

    And it never edits a listing, never posts, never buys. It reports; you act.

THE FAILURE MODE THIS FILE IS BUILT AROUND
    A scraper that cannot parse the page reports zero results. Zero results looks
    exactly like an empty niche. Acting on that would mean designing into a
    category that is actually saturated.

    So three outcomes are kept strictly separate:
        NETWORK   could not reach Etsy at all
        PARSE     reached the page, extracted no titles — the markup moved
        OK        extracted N titles, of which M match
    Only OK ever produces a count. The other two are loud.

⚠ BEFORE YOU RUN IT
    Automated fetching of Etsy search pages may be against their terms of
    service. This is built for low-volume personal research — one pass over a
    handful of phrases, with a delay between each — not for bulk collection.
    Check the current terms and decide for yourself.

    The sanctioned alternative your own research already identified: eRank's
    free tier plus EverBee Hobby costs $0 and was judged enough at this stage.
    Use `--manual` to record counts you read yourself, and get the history
    tracking without any fetching at all.

USAGE
    python3 rival.py --dry-run                    # prove the failure path
    python3 rival.py --catalogue catalogue.json
    python3 rival.py --manual orchid-skull=14     # record a hand count
    python3 rival.py --history                    # what changed since last time
"""

import argparse
import datetime as dt
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
HISTORY = os.path.join(HERE, "rival-history.json")

SEARCH_URL = "https://www.etsy.com/search?q={q}"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/122.0 Safari/537.36")
DELAY_SECONDS = 6.0          # be a good citizen; this is not a crawler
TIMEOUT = 25

# The caveat the original check wrote about itself. It goes in every report,
# because it is the thing most likely to be forgotten and most likely to cost
# money if it is.
CAVEAT = ("Zero competition proves the ground is unclaimed. It does NOT prove "
          "anyone searches for it. A phrase nobody has claimed may simply be a "
          "phrase nobody wants.")


class Unreachable(Exception):
    """Could not reach Etsy at all."""


class Unparseable(Exception):
    """Reached the page and could not read it. NOT the same as zero results."""


def fetch(phrase):
    url = SEARCH_URL.format(q=urllib.parse.quote_plus(phrase))
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "en-US,en;q=0.9",
    })
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            body = r.read()
            if r.status != 200:
                raise Unreachable(f"HTTP {r.status}")
            return body.decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        raise Unreachable(f"HTTP {e.code}") from e
    except Exception as e:
        raise Unreachable(f"{type(e).__name__}: {e}") from e


def extract_titles(html):
    """
    Pull listing titles out of a search page.

    Several strategies, because Etsy's markup moves and a single selector is a
    time bomb. If every strategy comes back empty on a page that clearly has
    content, that is a PARSE failure and must be raised — never returned as an
    empty list, which the caller would read as 'no competitors'.
    """
    strategies = [
        # data attribute used on listing cards
        lambda h: re.findall(r'data-listing-id="[^"]*"[^>]*title="([^"]{8,200})"', h),
        # the visible title element
        lambda h: re.findall(r'<h3[^>]*class="[^"]*v2-listing-card__title[^"]*"[^>]*>\s*([^<]{8,200})\s*<', h),
        # generic listing-link title attribute
        lambda h: re.findall(r'class="[^"]*listing-link[^"]*"[^>]*title="([^"]{8,200})"', h),
        # JSON-LD embedded results
        lambda h: re.findall(r'"name"\s*:\s*"([^"]{8,200})"[^}]*?"@type"\s*:\s*"Product"', h),
    ]
    for s in strategies:
        try:
            found = [re.sub(r"\s+", " ", t).strip() for t in s(html)]
        except re.error:
            continue
        found = [t for t in found if t]
        if len(found) >= 3:
            return found

    if len(html) < 2000:
        raise Unreachable("response too short to be a search page — blocked or redirected")
    raise Unparseable(
        "reached the page but no listing titles matched any known pattern. "
        "Etsy's markup has probably changed. Fix the selectors in extract_titles "
        "before trusting any number from this tool.")


def count_matches(titles, keyword):
    """
    Count titles genuinely selling this idea.

    The original method's words: 'Exact means a title genuinely selling that
    idea, not a loose relevance match.' Etsy pads results with anything vaguely
    related, so requiring the distinctive keyword in the TITLE is what makes the
    number mean something.
    """
    k = keyword.lower().strip()
    return sum(1 for t in titles if k in t.lower())


def load_history():
    if os.path.exists(HISTORY):
        try:
            return json.load(open(HISTORY))
        except Exception:
            return {"runs": []}
    return {"runs": []}


def save_history(h):
    tmp = HISTORY + ".tmp"
    with open(tmp, "w") as f:
        json.dump(h, f, indent=2)
    os.replace(tmp, HISTORY)     # atomic; a half-written history is worse than none


def previous(hist, design_id):
    for run in reversed(hist.get("runs", [])):
        for r in run.get("results", []):
            if r.get("id") == design_id and r.get("status") == "ok":
                return r, run.get("ran_at")
    return None, None


def heartbeat(state, note, agents_path):
    """
    Write into Automation/agents.json per AGENTS-SETUP.md:35-63.

    Atomic, ISO-8601, every other agent's entry preserved. A half-written JSON
    would make the whole fleet render as dead.
    """
    if not agents_path:
        return
    entry = {"id": "rival-watch", "name": "RIVAL WATCH", "cluster": "alpha",
             "state": state, "note": note[:140],
             "updatedAt": dt.datetime.now(dt.timezone.utc)
                            .strftime("%Y-%m-%dT%H:%M:%SZ")}
    data = {"agents": []}
    if os.path.exists(agents_path):
        try:
            data = json.load(open(agents_path))
        except Exception:
            pass
    agents = [a for a in data.get("agents", []) if a.get("id") != "rival-watch"]
    agents.append(entry)
    tmp = agents_path + ".tmp"
    with open(tmp, "w") as f:
        json.dump({"agents": agents}, f, indent=2)
    os.replace(tmp, agents_path)


def render_report(results, hist, ran_at):
    L = [f"# Rival watch — {ran_at}\n"]
    ok = [r for r in results if r["status"] == "ok"]
    bad = [r for r in results if r["status"] != "ok"]

    if bad:
        L.append(f"## {len(bad)} query did not produce a number\n")
        L.append("These are NOT zeroes. A failed read and an empty niche look "
                 "identical if you let them.\n")
        for r in bad:
            L.append(f"- **{r['id']}** — `{r['status'].upper()}`: {r.get('detail','')}")
        L.append("")

    if ok:
        L.append("## Counts\n")
        L.append("| Design | Phrase | Titles seen | Selling this idea | Change |")
        L.append("|---|---|---|---|---|")
        for r in sorted(ok, key=lambda x: -x["matches"]):
            prev, when = previous(hist, r["id"])
            if prev is None:
                delta = "first run"
            else:
                d = r["matches"] - prev["matches"]
                delta = ("no change" if d == 0
                         else f"{d:+d} since {str(when)[:10]}")
            L.append(f"| {r['id']} | `{r['phrase']}` | {r['scanned']} | "
                     f"**{r['matches']}** | {delta} |")
        L.append("")

        risen = [r for r in ok
                 if (p := previous(hist, r['id'])[0]) and r["matches"] - p["matches"] >= 3]
        if risen:
            L.append("### Filling up\n")
            for r in risen:
                p, when = previous(hist, r["id"])
                L.append(f"- **{r['id']}** {p['matches']} → {r['matches']} since "
                         f"{str(when)[:10]}. Worth a look before you invest more in it.")
            L.append("")

    L.append(f"---\n\n⚠ {CAVEAT}\n")
    L.append("Counts are titles on the first results page, not market size, not "
             "revenue. They rank opportunities against each other and nothing more.\n")
    L.append("This tool reports. It never edits a listing, posts, or buys.\n")
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--catalogue", default=os.path.join(HERE, "catalogue.json"))
    ap.add_argument("--out", default=os.path.join(HERE, "out"))
    ap.add_argument("--agents", default="", help="path to Automation/agents.json")
    ap.add_argument("--dry-run", action="store_true",
                    help="no network; proves failures are reported as failures")
    ap.add_argument("--manual", action="append", default=[], metavar="ID=N",
                    help="record a count you read yourself; repeatable")
    ap.add_argument("--history", action="store_true", help="show past runs and exit")
    ap.add_argument("--delay", type=float, default=DELAY_SECONDS)
    a = ap.parse_args()

    hist = load_history()

    if a.history:
        if not hist["runs"]:
            print("no runs recorded yet")
            return
        for run in hist["runs"]:
            ok = [r for r in run["results"] if r["status"] == "ok"]
            print(f"{run['ran_at']}  {len(ok)} counted, "
                  f"{len(run['results']) - len(ok)} failed")
            for r in sorted(ok, key=lambda x: -x["matches"]):
                print(f"    {r['id']:<22} {r['matches']:>4}")
        return

    cat = json.load(open(a.catalogue))
    designs = cat.get("designs", [])
    ran_at = dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    results = []

    manual = {}
    for m in a.manual:
        if "=" not in m:
            sys.exit(f"--manual wants ID=N, got '{m}'")
        k, v = m.split("=", 1)
        manual[k.strip()] = int(v)

    heartbeat("working", f"counting {len(designs)} phrases", a.agents)

    for i, d in enumerate(designs):
        did, phrase = d.get("id"), d.get("phrase", "")
        if not phrase:
            continue

        if did in manual:
            results.append({"id": did, "phrase": phrase, "status": "ok",
                            "scanned": -1, "matches": manual[did], "source": "manual"})
            print(f"  {did:<22} {manual[did]:>4}  (hand count)")
            continue

        if a.dry_run:
            results.append({"id": did, "phrase": phrase, "status": "network",
                            "detail": "dry run — no fetch attempted"})
            print(f"  {did:<22}    -  DRY RUN, no number produced")
            continue

        try:
            html = fetch(phrase)
            titles = extract_titles(html)
            n = count_matches(titles, phrase)
            results.append({"id": did, "phrase": phrase, "status": "ok",
                            "scanned": len(titles), "matches": n, "source": "fetch"})
            print(f"  {did:<22} {n:>4}  of {len(titles)} titles seen")
        except Unparseable as e:
            results.append({"id": did, "phrase": phrase, "status": "parse",
                            "detail": str(e)})
            print(f"  {did:<22}    -  PARSE FAILURE — not a zero", file=sys.stderr)
        except Unreachable as e:
            results.append({"id": did, "phrase": phrase, "status": "network",
                            "detail": str(e)})
            print(f"  {did:<22}    -  UNREACHABLE — not a zero ({e})", file=sys.stderr)

        if i < len(designs) - 1 and not a.dry_run:
            time.sleep(a.delay)

    report = render_report(results, hist, ran_at)
    os.makedirs(a.out, exist_ok=True)
    path = os.path.join(a.out, "rival-report.md")
    open(path, "w").write(report)
    print(f"\nwrote {path}")

    counted = [r for r in results if r["status"] == "ok"]
    if counted:
        hist.setdefault("runs", []).append({"ran_at": ran_at, "results": results})
        save_history(hist)
        print(f"recorded {len(counted)} count(s) to {HISTORY}")
    else:
        print("nothing counted — history not touched, so a failed run cannot "
              "masquerade as a real one", file=sys.stderr)

    failed = len(results) - len(counted)
    heartbeat("done" if counted else "error",
              f"{len(counted)} counted, {failed} failed", a.agents)

    print(f"\n⚠ {CAVEAT}")
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
