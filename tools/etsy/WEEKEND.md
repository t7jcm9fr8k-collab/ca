# This weekend — Sat Sept 5 · Sun Sept 6 · Mon Sept 7 (Labor Day)

Written 2026-09-04. Everything the cloud could do without plates is done and
pushed; every dollar in the plan now sits behind the first three items here.
About five to six hours in total, all of it yours because it needs your
accounts or your download folder.

Rules that do not bend: no agent posts, lists, publishes or buys — you press
every Publish button. Brand only: "Designed by me in Connecticut", never the
town, never a name, never a face. Nothing below asks for either.

---

## 1 · Five plates (Saturday, under two hours)

Save each under `tools/etsy/sources/` with **exactly** the slot name. Read the
licence box on the file's own page, not the thumbnail. Fill `provenance`
(url, licence, traced, credit) in the recipe. Log each in `Etsy-Art/SOURCES.md`.
`compose.py` refuses to render until all four fields are filled — that is the
rule working, not a bug.

| slot | design | what | where |
|---|---|---|---|
| `posada-calavera.jpg` | Marigold Calavera | a Posada calavera broadside — skull or full skeleton | Commons: search `José Guadalupe Posada`; Met Open Access: `Posada` |
| `marigold-wreath.jpg` | Marigold Calavera | a marigold plate, botanical, clear silhouette | BHL: `Tagetes`; Met: `Redouté` |
| `anatomy-skull.jpg` | Orchid Skull | anatomical skull, front or three-quarter, strong line | Wellcome: `Vesalius`; Met: `Vesalius` |
| `orchid-a.jpg` | Orchid Skull | one clear orchid specimen with a visible stem | BHL: `Bateman Orchidaceae`; Met: `Redouté` |
| `orchid-b.jpg` | Orchid Skull | a second orchid, different species, stem visible | same source, different plate |

Biggest version offered; under ~1500 px on the short edge goes soft at chest
size. Licence must say public domain or CC0 — `compose.py` rejects BY-SA, NC
and ND and refuses anything it cannot recognise.

## 2 · Two Printify facts (Saturday, ten minutes)

In Printify → Product Creator → Gildan 5000: the front print area in pixels,
and an exported white blank and black blank PNG. Paste the number and commit
the two PNGs with the plates. `mockup.py:47` carries the 15×18 in assumption in
one place; the cloud changes it the moment the real number lands.

## 3 · Run the loop (Saturday or Sunday, about ninety minutes)

From `tools/etsy`, one design at a time. Look at every render; both real
defects in this pipeline were invisible in code and obvious on screen.

```
git pull
python3 compose.py --recipe recipes/marigold-calavera.json --draft --report
python3 compose.py --recipe recipes/marigold-calavera.json
python3 qc.py --file out/marigold-calavera-onlight.png --recipe recipes/marigold-calavera.json
python3 mockup.py --design marigold-calavera --version 1 --print out/marigold-calavera-onlight.png
python3 qc.py --design marigold-calavera --version 1
python3 mockup.py --design marigold-calavera --version 2 --print out/marigold-calavera-onlight.png --change "what you changed and why"
python3 history.py --report
```

Then the same for `orchid-skull`. If v1 passes clean, v2 still needs a
`--change`; "no change — v1 passed, v2 is the listing file" is an honest one.

## 4 · List (Sunday or Monday, about ninety minutes)

Printify: two products each, **white and black only** — Sport Grey read
1.41:1 on the proof and will not print. Etsy: the copy below, verbatim.
**Publish Marigold on Monday Sept 7. Hold Orchid Skull until Wednesday Sept 9.**
Each new listing gets its own visibility boost; spend them one at a time.
Etsy Ads stay OFF.

### Marigold Calavera — $23.99

Title:
`Calavera T Shirt, Day of the Dead Marigold Tee, Posada Skeleton Folk Art, Dia de los Muertos Unisex Cotton Gift Shirt`

Tags (13):
`calavera shirt`, `day of the dead tee`, `dia de muertos`, `posada skeleton art`, `marigold skull tee`, `mexican folk art`, `sugar skull gift`, `unisex graphic tee`, `made to order shirt`, `heavy cotton tshirt`, `printed in usa tee`, `gift for him`, `gift for her`

Description: the full text is in `out/listings.txt` (regenerate with
`python3 listing.py --catalogue catalogue.json --id marigold-calavera`).

### Orchid Skull — $23.99

Title:
`Botanical Skull T Shirt, Vintage Anatomy Orchid Tee, Skeleton and Flowers Art, Unisex Heavy Cotton Goth Gift Shirt`

Tags (13):
`botanical skull tee`, `skull and flowers`, `vintage anatomy art`, `orchid skull tshirt`, `goth botanical tee`, `skeleton flower gift`, `memento mori shirt`, `unisex graphic tee`, `made to order shirt`, `heavy cotton tshirt`, `printed in usa tee`, `gift for him`, `gift for her`

Description: `python3 listing.py --catalogue catalogue.json --id orchid-skull`.

Once listed, put each listing id into `catalogue.json` (`listing_id`, and
`status` to `live`) so the posting calendar links to it.

## 5 · The stale number (Sunday, twenty minutes)

`Prompts/etsy-listing.md:12` in your tree still prices from a $13.55 cost.
The real cost is $9.79 and break-even is $11.81. `CONTRACTS.md:3-7` lists all
five files that repeat it; change them in one sitting.

## 6 · Only if 1–5 are done: hand over Track A (Monday, thirty minutes)

Push the seven Swift files, the imageset and the eighteen HTML mockups to a
branch the cloud can reach. Do no extraction yourself; the cloud does the
copy-never-move, the coupling cuts, the scrub and the demo app, and you verify
the scrub by grep on Saturday Sept 12.

## 7 · Optional: start the Lemon Squeezy signup

Payout KYC is private (it is the merchant of record) but takes days. Loses
nothing if it waits until Oct 3.

---

## Next week's posting slots (Sept 8–12), paste-ready

Regenerate after the listings are live so the links fill in:

```
python3 schedule.py --start 2026-09-08 --end 2026-11-18 --ics
```

Until then, from the current calendar (Pinterest only ever carries a live
design; TikTok may tease an unreleased one — hands only, never a face):

- **Tue Sept 8, 10:30, Pinterest — Haeckel Blue Jellyfish**, detail crop.
  Title `Jellyfish T Shirt — detail crop`. Link `etsy.com/listing/4562151062`.
- **Wed Sept 9, 21:30, Pinterest — Haeckel Compass Jellyfish**, on-body
  mockup squared for mobile. Link `etsy.com/listing/4562151082`.
- **Thu Sept 10, 19:30, TikTok — Orchid Skull**, layer reveal: sources fading
  in one at a time until the composite lands. Caption
  `layer reveal · Orchid Skull`. Hashtags `#printondemand #publicdomain
  #vintageart #botanicalskulltee #skullandflowers #vintageanatomyart`.
- **Fri Sept 11, 20:30, Pinterest** — after regenerating, this becomes
  Marigold (live Monday). Before that it is a jellyfish slot.
- **Sat Sept 12, 20:00, Pinterest — Haeckel Blue Jellyfish**, "what it is made
  from — the two archives named".

Then Sept 13–29 is the wall: no posting, no HUD, no re-plan. Etsy messages
within 24 h; Printify fulfils on its own.

---

## Trading housekeeping, whenever convenient (from `tools/market`)

Trial 3 needs the raw closes — no `--adjusted-close`:

```
python3 fetch.py --source yahoo --symbol SPY --out bars/SPY-1d-raw.csv
git add -f bars/SPY-1d-raw.csv
git commit -m "SPY raw closes for trial 3"
git push
```

The 21-year runs were done in the cloud and are in `EVIDENCE.md`; your own
ledger does not have them. To record them on the Mac:

```
python3 run.py --mode backtest --strategy trend_filter:200 --csv bars/SPY-1d.csv --symbol SPY --source stooq --cash-yield 0.03
python3 nulltest.py --csv bars/SPY-1d.csv --symbol SPY --source stooq --horizon 1
python3 combine.py --csv bars/SPY-1d-agg.csv --symbol SPY --source alpaca-1m-aggregated --adjusted yes --signals sma_cross:10,30 breakout:20 trend_filter:200 vwap_reclaim:20 --holdout-from 2024-01-01 --cost-bps 5 --count-ledger
```

---

## Built this session and waiting for plates

- `schedule.py` now puts designs that can actually be rendered first and
  labels the rest BLOCKED; Pinterest never carries a blocked design.
- `printable.py` — the November printables: 8×10, 11×14, A3, 16×20 at 300
  DPI, never stretched, never enlarged, PNG and a hand-written PDF that carry
  no metadata at all, scrubbed against strings you pass with `--forbid` on
  your own machine, gated on a recorded inspection. Not to be listed before
  November; the export exists so that step is ten minutes when it comes.

The ladder says $0 through week 5 is on plan. Count actions this month, not
sales: plates in, listings live, slots posted.
