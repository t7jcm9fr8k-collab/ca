# Queue runner — the network-dependent items, for a fresh cloud session

*Written 2026-09-06 by the parent session
(https://claude.ai/code/session_01KFA4Hu3AkjsvcsKNh8xmQa). A new cloud session
on this branch reads this file and carries it out, top to bottom. The parent
session's container cannot reach any market or archive host; a session started
after the environment's network access was widened can.*

Work on branch `claude/10k-revenue-slack-agents-iu8xu0` only. Always
`git pull origin claude/10k-revenue-slack-agents-iu8xu0` before each push (the
parent pushes to the same branch). Never force-push, never rewrite history,
never open a pull request.

## Step 0 — probe first; do nothing else until you have the answer

```
for u in "https://commons.wikimedia.org/w/api.php?action=query&format=json&list=search&srsearch=Posada%20calavera&srnamespace=6&srlimit=3" "https://collectionapi.metmuseum.org/public/collection/v1/search?q=Posada" "https://www.biodiversitylibrary.org/" "https://api.wellcomecollection.org/catalogue/v2/images?query=Vesalius" "https://query1.finance.yahoo.com/v8/finance/chart/SPY?range=5d&interval=1d" "https://api.nasdaq.com/api/quote/SPY/historical?assetclass=etf&fromdate=2020-07-01&limit=9999&todate=2026-09-06" "https://stooq.com/q/d/l/?s=eem.us&i=d"; do printf '%s  %s\n' "$(curl -sS -m 20 -o /dev/null -w '%{http_code}' -A 'Mozilla/5.0' "$u" 2>/dev/null | tail -c 3)" "$u"; done
```

If every line prints `000`: make no changes, commit nothing, and end with one
line, `NETWORK STILL BLOCKED: <hosts>`. If some hosts answer, do the steps
whose hosts answered and report the rest as blocked.

## Standing rules from the owner (they override convenience)

- Never paste or commit API keys or secrets; never put credentials in any file
  or argument. Never disable TLS verification. Never circumvent a site's bot
  check (Stooq shows a JavaScript verification page to scripts: if you get it,
  that route is closed — say so, do not try to defeat it).
- Never place a broker order of any kind; never touch `--mode live`; no
  `--force` anywhere; no new trading rules; every number written into a
  document comes from a file saved in this session, quoted by name.
- Anonymity is brand-only: never write the owner's name, town, or any personal
  identifier into anything committed. "Designed by me in Connecticut" is the
  most that may be said, and only where copy already says it.
- Provenance is enforced, never invented: `compose.py` refuses to render a
  layer whose provenance lacks a real URL, a real licence string read from the
  file's own page or API record, a traced date, and a credit. Do not fabricate
  any of these. Public domain or CC0 only; CC-BY-SA, NC and ND are rejected by
  the tool and by the owner.
- Do not modify or delete existing files under `tools/market/bars/` (research
  data); adding new files there is fine. `bars/` and `tools/etsy/sources/` are
  gitignored: add new data files with `git add -f`, one file at a time, each
  under a few MB. Never commit minute-bar files.
- Do not touch `trackA/` (the parent is building it). Edit
  `tools/market/EVIDENCE.md` only by appending the paragraphs described below.
- Commit messages end with the two lines
  `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>` and
  `Claude-Session: <this session's own claude.ai/code URL>`.

Read first: `tools/etsy/WEEKEND.md` (section 1, the plates table),
`tools/etsy/SOURCING.md`, `tools/etsy/README.md`,
`tools/etsy/recipes/marigold-calavera.json` and `orchid-skull.json`,
`tools/market/README.md` (the `--source yahoo`, nasdaq browser-route and
trial 3 passages), and the tail of `tools/market/EVIDENCE.md` (sections E and
E-15).

## Step A — plates (only if the archive hosts answered)

For each of the five slots in WEEKEND.md's table (`posada-calavera.jpg`,
`marigold-wreath.jpg`, `anatomy-skull.jpg`, `orchid-a.jpg`, `orchid-b.jpg`)
find a plate matching the description through the archives' APIs: Wikimedia
Commons (API, then the file page's licence template — public-domain or CC0
templates only), the Met Open Access API (`isPublicDomain` must be true; use
`primaryImage`), the Biodiversity Heritage Library (public-domain / no-known-
copyright items only), the Wellcome Collection API (licence `pdm` or `cc0`
only). Take the largest available image; the short edge should be at least
1500 px. Save to `tools/etsy/sources/<slot>.jpg` (convert with Pillow if the
source is PNG or TIFF; never upscale). Fill the matching layer's provenance in
the two recipes: `url` (the file page or API record, not the raw image),
`licence` (the exact string the page states, e.g. "Public domain" or
"CC0 1.0"), `traced` (today's ISO date), `credit` (institution and work title;
no personal names of living people).

Then, from `tools/etsy`:

```
python3 compose.py --recipe recipes/marigold-calavera.json --draft --report
```

Open and LOOK at the draft PNG (Read tool). If the silhouette is unreadable,
adjust only recipe geometry (scale, offset, rotation) and re-draft, at most
three tries. Then the full compose, `qc.py --file out/marigold-calavera-onlight.png --recipe recipes/marigold-calavera.json`,
`mockup.py --design marigold-calavera --version 1 --print out/marigold-calavera-onlight.png`,
`qc.py --design marigold-calavera --version 1`, and look at the mockup. Same
for `orchid-skull`. Never `--force`. Run `python3 test_tools.py` in
`tools/etsy` and keep it green. Commit the five plates (`git add -f`), the two
recipes, and only the outputs the README says are tracked. Push.

## Step B — SPY raw closes and trial 3 (only if Yahoo or Nasdaq answered)

From `tools/market`: `python3 fetch.py --source yahoo --symbol SPY --out bars/SPY-1d-raw.csv`
(no `--adjusted-close`). If it ends in NETWORK (HTTP 429), try Nasdaq:
`GET https://api.nasdaq.com/api/quote/SPY/historical?assetclass=etf&fromdate=2020-07-01&limit=9999&todate=<today>`
with headers `User-Agent: Mozilla/5.0` and `Accept: application/json`. If it
returns JSON with `data.tradesTable.rows` (fields date, close, volume, open,
high, low; dollar signs on prices; newest first), write `tools/market/nasdaq_json.py`
that converts it into the plain CSV form with the same semantics as
`bars.parse_nasdaq` (reverse to oldest-first, strip dollar signs, source
"nasdaq", adjusted False) and writes `bars/SPY-1d-raw.csv`; add three checks
to `test_tools.py` and keep the suite green.

Then `python3 barqc.py --csv bars/SPY-1d-raw.csv --symbol SPY --source <yahoo|nasdaq>`
and trial 3:

```
python3 intraday.py --sessions-from bars/SPY-sessions.csv --rule first30 --close-from bars/SPY-1d-raw.csv --close-source <yahoo|nasdaq> --no-record
```

Save the complete outputs to `tools/market/runs/trial3-2026-09-06-barqc.txt`
and `tools/market/runs/trial3-2026-09-06.txt` (create `runs/`; commit them).
If the basis guard REFUSES the file, that is the tool working: record the
refusal verbatim and stop this step. Otherwise append to
`tools/market/EVIDENCE.md` a section `## Trial 3 — the official close
(2026-09-06)` with the command, the tool's verdict lines verbatim, the numbers
only as printed in the saved files, and one paragraph reading it against
trials 1 and 2 (their numbers are in EVIDENCE.md's "First real data" and
"Second and third runs" sections; quote them from there). Update README.md's
trial 3 lines to say it ran. Commit (`git add -f bars/SPY-1d-raw.csv` plus the
rest). Push.

## Step C — EEM long file (only if stooq.com answered)

`curl -sS -A 'Mozilla/5.0' 'https://stooq.com/q/d/l/?s=eem.us&i=d' -o /tmp/eem.csv`.
If the file is HTML or mentions JavaScript, the bot check closed the route:
say so and stop this step. If it is a CSV with the header
`Date,Open,High,Low,Close,Volume`, copy it to `bars/EEM-1d-long.csv`, run
`python3 barqc.py --csv bars/EEM-1d-long.csv --symbol EEM --source stooq --adjusted yes`,
and if it PASSES re-run the replication with all nine long files:

```
python3 nulltest.py --rule rsi_oversold --horizon 5 --csv bars/DIA-1d-long.csv bars/EEM-1d-long.csv bars/EFA-1d-long.csv bars/GLD-1d-long.csv bars/IWM-1d-long.csv bars/QQQ-1d-long.csv bars/TLT-1d-long.csv bars/XLE-1d-long.csv bars/XLF-1d-long.csv --symbol DIA EEM EFA GLD IWM QQQ TLT XLE XLF --source stooq --adjusted yes --no-record
```

Save the full output to `tools/market/runs/E15-nine-2026-09-06.txt` and append
one paragraph to the end of EVIDENCE.md's section E-15, titled "EEM landed",
with the tool's verdict line verbatim and EEM's table row as printed. Commit
(`git add -f bars/EEM-1d-long.csv` plus `runs/` and EVIDENCE.md). Push.

## Step D — report

Write `tools/market/runs/queue-runner-2026-09-06.md`: which hosts answered,
what landed (files, commits), every tool verdict verbatim, what was blocked
and the exact reason, and what still needs the owner's hands. Commit and push
it. Your final message is the same content. Every claim traceable to a saved
file. If anything you are about to do would break a standing rule above, do
not do it; write down why and move on.
