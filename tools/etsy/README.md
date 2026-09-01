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
| `test_tools.py` | 66 checks. `python3 test_tools.py` |

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

## Two defects worth knowing about

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

## Numbers this depends on

From `CorpalCaptain_Margin_Calculator.xlsx`, verified against Printify
2026-08-15 and pinned by tests:

- production **$9.79** flat S–XL (SwiftPOD, Gildan 5000)
- fees on retail **plus** shipping, not retail alone
- break-even **$11.81**; at $23.99 you keep **$11.02** (45.9%)

⚠ `Prompts/etsy-listing.md:12` still says **$13.55**. It is wrong, and it is an
active prompt template. Four other files carry the same stale figure;
`CONTRACTS.md:3-7` requires all of them to change in one sitting.
