# CorpalCaptain shirt pipeline

Five tools that take a public-domain plate to a live, searchable Etsy listing
with a posting schedule behind it. Python 3 + Pillow, offline, no API, no
account credentials — the same posture as `Design/render/render_shirt.py`,
which does the text designs this pipeline does not.

```
sources/          the downloaded plates (see SOURCING.md)
recipes/*.json    one per composition — layers, palette, provenance
catalogue.json    source of truth: designs, titles, tags, prices, status
out/              everything generated
```

| Tool | Does |
|---|---|
| `render_plate.py` | one plate → print file. Lifts the paper ground, rebuilds tone for DTG, typesets a caption. |
| `compose.py` | several plates → **one original composition**. Cut out, unified to a single ink palette, masked, composed. |
| `listing.py` | title, 13 tags and description — with validators that fail loudly. |
| `schedule.py` | the release calendar and the daily posting calendar. Markdown + `.ics`. |
| `rival.py` | competitor counts over time. Runs on the Mac; needs network. |
| `mockup.py` | print file → garment mockups at true physical scale. **Refuses v2 without an inspection of v1.** |
| `inspect.py` | the QC gate — nine checks, each reporting a number |
| `history.py` | append-only ledger + the change history you can look at |
| `demo.sh` | the whole loop end to end, reproducibly |
| `test_tools.py` | 109 checks. `python3 test_tools.py` |

## The order

```bash
# 1. download sources and fill in each recipe's provenance — see SOURCING.md
python3 compose.py --list-recipes            # what is still BLOCKED

# 2. build a composition, draft first
python3 compose.py --recipe recipes/orchid-skull.json --draft --report
#    LOOK at out/*-preview.png and out/*-silhouette.png, then drop --draft

# 3. copy and searchability
python3 listing.py --catalogue catalogue.json --id orchid-skull

# 4. the calendars
python3 schedule.py --ics

# 5. on the Mac, with network
python3 rival.py --catalogue catalogue.json
```

## The mockup gate

```
v1  →  inspect  →  v2
```

`mockup.py --version 2` refuses to run without a recorded inspection of v1, and
refuses again if no `--change` is given. A second mockup exists to answer
findings from the first; without them it is a second guess, and a version with
no recorded change cannot be read as a revision later.

Run `./demo.sh` to watch the whole loop. On the stand-in plates it goes:
v1 blocked at **2.69:1 contrast on black** (under the 3:1 WCAG floor) → inks
lightened → v2 passes at **4.71:1**.

## Three things this pipeline refuses to do

**Render without provenance.** Every layer needs a source URL, a licence and a
traced date. `Etsy-Art/SOURCES.md`'s rule — *no entry, no listing* — moved out of
memory and into code. CC-BY-SA, NC and ND are rejected outright, and so is any
licence string it cannot positively recognise as merchandise-safe.

**Report a zero it did not measure.** `rival.py` keeps NETWORK failure, PARSE
failure and a genuine count strictly apart. A scraper that cannot read the page
returns zero results, and zero results looks exactly like an empty niche — which
is how you end up designing into a saturated category. Only a real read produces
a number, and a failed run never touches the history.

**Describe work that did not happen.** `--report` on both renderers prints only
the transformations that actually ran. Etsy's August 2026 Creativity Standards
require items made with computerized tools to be based on the seller's original
design; the listing copy has to be true, and copy claiming design labour that
never happened is worse than no copy at all.

## Four defects worth knowing about

Both were invisible in the code and obvious in the render. They are why
`--preview` exists and why the tests pin them.

1. **`render_plate.py` left the paper trapped between the tentacles.** A border
   flood fill cannot reach an enclosed gap, so it printed as cream blobs on a
   coloured shirt. Fixed with a saturation/value second pass: 19% of the scan
   cleared before, 42% after.
2. **`compose.py` turned a colour lithograph into faint pencil.** A litho's
   subject sits at mid luminance, so mapping it linearly to ink density produced
   weak alpha. Fixed by auto-levelling each source against its own 2–98
   percentile range, measured over the opaque region only.
3. **Two QC checks fired on clean files.** The halo check assumed "clean means
   alpha 0 or 255" and reported 98% halo on a file where only 0.6% of pixels
   were near-full alpha — because ink density is *supposed* to be continuous.
   The palette check counted density blends as separate inks, reporting 8 on a
   two-ink file. Fixed by measuring a fringe annulus rather than global
   mid-alpha, and by clustering HUE rather than RGB.
4. **The diff heatmap reported 0.0% on a file that plainly changed.** It compared
   alpha only, reasoning that "what moved is a change in where ink is" — and the
   very first change it was asked to show was a *recolour*. Fixed by diffing
   what a viewer actually sees: both versions composited onto the same ground.

## One check that is deliberately not a blocker

`edge halo` is **reported, never blocking**. The annulus test separates a fringe
from artwork on isolated shapes (a clean disc reads 0%, the same disc feathered
reads 100%) but not on dense linework, where the ring fills with neighbouring
lines. A blocking check that fires on every good file trains you to ignore the
gate, which costs more than the defect it was meant to catch. Mid-tone garment
contrast is reported for the same reason — you have not decided whether you
stock Sport Grey or Navy, so the number waits for you.

## Numbers this depends on

From `CorpalCaptain_Margin_Calculator.xlsx`, verified against Printify
2026-08-15 and pinned by tests:

- production **$9.79** flat S–XL (SwiftPOD, Gildan 5000)
- fees on retail **plus** shipping, not retail alone
- break-even **$11.81**; at $23.99 you keep **$11.02** (45.9%)

⚠ `Prompts/etsy-listing.md:12` still says **$13.55**. It is wrong, and it is an
active prompt template. Four other files carry the same stale figure;
`CONTRACTS.md:3-7` requires all of them to change in one sitting.
