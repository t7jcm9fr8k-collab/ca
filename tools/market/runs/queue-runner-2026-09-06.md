# Queue runner report — 2026-09-06

Carried out `tools/QUEUE-RUNNER.md` top to bottom from cloud session
https://claude.ai/code/session_01MtriMy1Nu5NbNEJHgSEzDe. Every number below is
quoted from a file named beside it.

**Branch.** The queue says to work on `claude/10k-revenue-slack-agents-iu8xu0`;
this session was started on, and is required by its harness to push to,
`claude/queue-runner-task-oiyzbm`. So: the parent branch was fast-forwarded
into this one before each push (its only new commit, `59dbd0c`, touches
`trackA/` alone, which was not modified), and everything here sits on
`claude/queue-runner-task-oiyzbm`, two commits ahead of the parent plus this
report. Nothing was force-pushed, no history rewritten, no pull request
opened. Merging this branch into the parent is the owner's call.

## Step 0 — which hosts answered (`runs/queue-runner-2026-09-06-probe.txt`)

| host | code | outcome |
|---|---|---|
| commons.wikimedia.org (API) | 200 first probe, 429 on the saved re-probe | answered; rate-limits bursts (see "Commons" below) |
| collectionapi.metmuseum.org | 200 | answered |
| www.biodiversitylibrary.org | 403 | **blocked**: front page 403; `api3` answers 401 without an API key, and no key was available or asked for |
| api.wellcomecollection.org | 200 | answered |
| query1.finance.yahoo.com | 200 to the probe | answered the probe, but `fetch.py --source yahoo` got HTTP 429 three times (`runs/trial3-2026-09-06-fetch.txt`) |
| api.nasdaq.com | 200 | answered |
| stooq.com | 000 | **blocked** at the proxy: `curl: (56) CONNECT tunnel failed, response 403`; the proxy status log records `connect_rejected … gateway answered 403 to CONNECT (policy denial or upstream failure), host stooq.com:443` at 23:07:22, 23:07:39 and 23:41:22 UTC |

So Step A ran (Commons, Met, Wellcome in place of BHL), Step B ran (Nasdaq
route), Step C did not.

## Step A — plates (commit `484a9b1`)

**Landed:** `tools/etsy/sources/` (five files, `git add -f`, 1.9–3.5 MB each)
and provenance in `recipes/marigold-calavera.json` and `recipes/orchid-skull.json`.

| slot | record read | licence as stated | pixels saved |
|---|---|---|---|
| `posada-calavera.jpg` | Met API object 735936, `isPublicDomain: True`, `primaryImage` DP869423 — Posada, *A skeleton holding a bone and leaping over a pile of skulls…*, zincograph ca. 1907 | CC0 | 1596 × 1907 after cropping to the print (source 1877 × 2143) |
| `marigold-wreath.jpg` | Commons `File:Tagetes erecta001.png`, licence template `{{PD-old}}` — Step & Watson, *Favourite Flowers*, vol. 2 pl. 144, 1897 | Public domain | 4726 × 6534 after crop (PNG 5251 × 7778, converted, never upscaled; caption and two dissection figures removed) |
| `anatomy-skull.jpg` | Wellcome works/zs6gser7, image V0007916, *Skull: anterior view. Line engraving* | Public Domain Mark | 2017 × 2566 after cropping inside the frame line (2373 × 2949) |
| `orchid-a.jpg` | Commons `File:The Orchidaceae of Mexico and Guatemala (Tab. XIII) BHL769175.jpg`, template `{{PD-scan\|PD-old-70-1923}}` — Bateman, *Cattleya skinneri*, 1837–43 | Public domain | 3529 × 4789 after cropping the caption (3677 × 5504) |
| `orchid-b.jpg` | Commons `File:Cattleya mossiae - Curtis' 65 (N.S. 12) pl. 3669 (1839).jpg`, template `{{PD-Art\|PD-old-auto-expired}}` | Public domain | 3011 × 3681 after cropping margins and letterpress (3220 × 3979) |

The first Posada choice, the Library of Congress scan *Calavera oaxaqueña*
on Commons (PD-old-100, 2546 × 1610), drafted as a grey block: its paper is
toned and the lift cleared only 43–67% of it (`runs/queue-runner-2026-09-06-etsy-verdicts.txt`,
"draft, first pass"). It was replaced by the Met print before any full
render. Crops removed page furniture only (frame line, captions, plate
numbers, dissection details); nothing was stretched or enlarged.

**Geometry, within the three-try rule:** marigold layer scale 0.86 → 0.78,
offset [0, 0.02] → [0, 0] (one try; it clipped both canvas edges). Orchid
layers 0.34 → 0.48 and 0.30 → 0.42, offsets moved twice (two tries; at the
recipe's sizes they were specks behind the cranium). Palette, gamma, lift and
masks untouched. Every draft and silhouette was looked at.

**Tool verdicts, verbatim** (`runs/queue-runner-2026-09-06-etsy-verdicts.txt`):

`compose.py --recipe recipes/orchid-skull.json --report` → `ink coverage 21.2%`,
`layer 0: ground lifted (34%)`, `layer 1: ground lifted (72%)`,
`layer 2: ground lifted (39%)`.

`qc.py --file out/orchid-skull-onlight.png --recipe recipes/orchid-skull.json` and
`qc.py --design orchid-skull --version 1`, identical:

```
FAIL  stroke width         65% lost                  <=35%
FAIL  contrast on black    1.16:1                    >=3.0:1
VERDICT: BLOCKED
blocked by: stroke width, contrast on black
```
(all other checks `ok`: ink coverage 21.2%, edge halo ring 38% reported,
edge bleed 0 px, palette 1 hue cluster, contrast on white 16.14:1, sport
grey 5.74:1, navy 1.13:1 reported, provenance 0 problems.)

`compose.py --recipe recipes/marigold-calavera.json --report` → `ink coverage 21.1%`,
`layer 0: ground lifted (62%)`, `layer 1: ground lifted (69%)`.

`qc.py --file out/marigold-calavera-onlight.png …` and `qc.py --design marigold-calavera --version 1`, identical:

```
FAIL  stroke width         36% lost                  <=35%
FAIL  contrast on black    1.97:1                    >=3.0:1
VERDICT: BLOCKED
blocked by: stroke width, contrast on black
```
(ink coverage 21.1%, edge halo ring 50% reported, contrast on white 9.50:1,
sport grey 3.38:1, navy 1.50:1 reported, provenance 0 problems.)

`mockup.py … --version 1` for both: `recorded v1 to the ledger`; each
inspection: `recorded to the ledger — v2 may proceed and must answer the
failures above`. `history.py --report`: `marigold-calavera 1 version(s),
1 inspection(s)`, `orchid-skull 1 version(s), 1 inspection(s)`. Both v1
mockups were looked at: on white both read (the skull with orchids growing
through the cranium; the leaping calavera with the marigold behind it), on
black the near-black ink vanishes exactly as the contrast check says.

`test_tools.py` in `tools/etsy`: 156 checks `ok`, 1 `FAIL`:
`demo ledger present (run ./demo.sh first)`. That check needs
`./demo.sh`, which needs the stand-in plates `pick-4.png` and `pick-2.png`
in `sources/` — not in the repository (`sources/` is gitignored) — and it
begins with `rm -rf out/history.json`, which would delete the two v1
inspections just recorded. So it was not run here; the failure is a fixture
condition of this container, not a regression, and all 156 checks that do
not need the demo pass.

**Not committed, by the queue's rule:** everything under `tools/etsy/out/`
(prints, previews, silhouettes, mockups, `history.json`) is gitignored and
the README lists no tracked outputs. The two v1 ledger entries therefore
exist only in this container. `Etsy-Art/SOURCES.md`, named in
WEEKEND.md, is not in this repository, so no entry was logged there.

**Commons rate limit, for the record:** the API and `upload.wikimedia.org`
answered 429 to bursts of parallel requests; everything was re-done
serially with a descriptive User-Agent and waits of 5–90 s. No bot check
was circumvented; a 429 is "not now", and it was honoured.

## Step B — SPY raw closes and trial 3 (commit `4d33a3d`)

**Landed:** `tools/market/nasdaq_json.py` (new), three checks in
`test_tools.py` (suite: `all checks passed`), `bars/SPY-1d-raw.csv`
(`git add -f`, 79 KB, 1,553 rows), `runs/trial3-2026-09-06-fetch.txt`,
`runs/trial3-2026-09-06-nasdaq-fetch.txt`, `runs/trial3-2026-09-06-barqc.txt`,
`runs/trial3-2026-09-06.txt`, the section `## Trial 3 — the official close
(2026-09-06)` appended to `EVIDENCE.md`, and README.md's trial 3 lines.

`fetch.py --source yahoo --symbol SPY --out bars/SPY-1d-raw.csv`
(`runs/trial3-2026-09-06-fetch.txt`):

```
HTTP 429 — waiting 2 s, retry 1 of 3
HTTP 429 — waiting 5 s, retry 2 of 3
HTTP 429 — waiting 12 s, retry 3 of 3
NETWORK  HTTP 429 after 3 retries
Nothing was written. No bars means no bars, not zero bars.
```

The Nasdaq GET (browser User-Agent, `Accept: application/json`) returned
`data.tradesTable.rows` with 1,553 rows, newest first, fields date, close,
volume, open, high, low; on this day the JSON carried no dollar signs
(the converter strips them when present, as the CSV download has them).
`nasdaq_json.py --symbol SPY --out bars/SPY-1d-raw.csv`
(`runs/trial3-2026-09-06-nasdaq-fetch.txt`):
`SPY 1d: 1553 bars, 2020-07-01 → 2026-09-04, source nasdaq` …
`wrote bars/SPY-1d-raw.csv: 1553 bars, oldest first, unadjusted official closes`.

`barqc.py --csv bars/SPY-1d-raw.csv --symbol SPY --source nasdaq`
(`runs/trial3-2026-09-06-barqc.txt`): `1553 bars, 1554 sessions, 1 missing`
(`missing 2025-01-09`), `0 off-calendar bar(s)`, `1 zero/negative` volume
reported not blocking (2026-04-20 in the file), `adjustment NOT stated`
(reported), **`VERDICT: PASS`**.

`intraday.py --sessions-from bars/SPY-sessions.csv --rule first30 --close-from bars/SPY-1d-raw.csv --close-source nasdaq --no-record`
(`runs/trial3-2026-09-06.txt`) — the basis guard did **not** refuse:

```
exit: official close from nasdaq (trial 3); median gap to this feed's last print 0.010%
gross -0.32 ± 0.67 bp/session (95% CI -1.64 to +1.00); the published effect of about +2.7 bp/session is EXCLUDED by this sample
3 session(s) had no 15:30 bar; the fill moved to the next bar's open (later, never earlier)
permutation null, 1000 shuffles: p = 0.669 (all), p = 0.641 (holdout)
pre-registered: the published rule, nothing searched
```

Table as printed: `all n 1512, gross -0.32 ± 0.67, net -2.32, hit 49.9%,
t -0.47, ann. net -5.8%`; by year gross 2020 −0.40, 2021 −0.67, 2022 −1.97,
2023 +1.63, 2024 −1.42, 2025 +1.21, 2026 −0.74 bp. Against trial 1 (gross
−0.5 ± 0.67, CI [−1.8, +0.8], EVIDENCE "First real data") and trial 2 (gross
−0.22 ± 0.67, CI [−1.52, +1.09], p = 0.63, "Second and third runs"), the
official-close exit moved the mean by about 0.2 bp and nothing else; the
reading paragraph is in EVIDENCE.md. `--no-record` was set; the ledger is
untouched.

## Step C — EEM long file: blocked

`curl -sS -A 'Mozilla/5.0' 'https://stooq.com/q/d/l/?s=eem.us&i=d' -o /tmp/eem.csv`
→ `curl: (56) CONNECT tunnel failed, response 403`, `HTTP 000 bytes 0`, no
file written. The proxy's own log (`__agentproxy/status`) shows
`connect_rejected` for `stooq.com:443`, "policy denial or upstream failure",
three times. This is the session's network policy, not Stooq's JavaScript
check — the request never reached stooq.com. Nothing under Step C was
attempted further: no `bars/EEM-1d-long.csv`, no nine-symbol `nulltest.py`
run, no "EEM landed" paragraph. EEM stays the one open item of E-15.

## What still needs the owner's hands

1. **Merge or cherry-pick** `claude/queue-runner-task-oiyzbm` into
   `claude/10k-revenue-slack-agents-iu8xu0` (three commits: `484a9b1`,
   `4d33a3d`, and this report).
2. **v2 for both designs.** Both v1 inspections are BLOCKED on stroke width
   (65% and 36% lost, floor 35%) and contrast on black (1.16:1 and 1.97:1,
   floor 3:1). Answering them means a lighter palette and/or gamma, which is
   a design decision outside this queue's geometry-only remit — the same
   move `demo.sh` documents (`#1A1A1A → #4A4A4A`, `#C4661F → #E8A94A`, gamma
   0.8). The v1 ledger entries live in this container's gitignored `out/`;
   on the Mac, re-run `compose.py`, `mockup.py --version 1` and `qc.py
   --version 1` from the committed plates and recipes (about two minutes)
   to re-create the gate state, then v2 with `--change`.
3. **EEM** from Stooq's browser download on the Mac, then `barqc.py` and the
   nine-file `nulltest.py` line in QUEUE-RUNNER.md Step C.
4. **BHL** plates for the other six compositions still need either a BHL API
   key on the Mac or Commons' mirrored BHL scans (which worked here for the
   Bateman plate).
5. `Etsy-Art/SOURCES.md` entries for the five plates, if that log lives
   outside this repository.
6. `tools/etsy/test_tools.py`'s `demo ledger present` check wants
   `./demo.sh` run once on a machine that has the stand-in plates.
