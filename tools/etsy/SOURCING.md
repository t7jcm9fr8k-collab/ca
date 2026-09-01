# Sourcing manifest

What to download, where from, and what to check before it goes near a shirt.
Roughly 20 files across 8 compositions. Do this on the Mac — the cloud session
that wrote these tools cannot reach any archive.

---

## The rule this runs on

`Etsy-Art/SOURCES.md`: **no entry, no listing.** One entry per file — filename,
origin URL, what the licence said, date pulled. `compose.py` enforces it: a
recipe with an empty `provenance.url`, `provenance.licence` or
`provenance.traced` refuses to render. That is deliberate. Fill it from the
**file's own page**, never from a search-result thumbnail.

## Search by artist, not by subject

`WHERE-TO-LOOK.md` learned this the hard way — the Met's subject search returned
six porcelain dinner plates for `moth insect plate`, and `Hokusai` returned 715
usable prints. **Type a person.**

## What makes a file usable

- **Biggest version offered.** Under ~1500px on the short edge goes soft at chest
  size. `render_plate.py` warns but will not stop you.
- **Hard edges, few colours, a clear silhouette across a room.** Line engravings
  qualify by construction; colour lithographs need the tone rebuild.
- **Portrait or square.** Crop, never stretch.
- **Read the licence box on the file page.** Commons files carry *individual*
  licences. `compose.py` rejects CC-BY-SA, NC and ND outright, and refuses
  anything it cannot recognise as merchandise-safe.

## Two artists that need extra care

- **Gustave Doré** (d. 1883) — the engravings are long clear, but many scans in
  circulation are modern reproductions with their own claims attached. Take a
  museum open-access copy, not a search-result image.
- **Yoshitoshi** (d. 1892) — clear on the artist, but later-block ukiyo-e
  reprints are common and some carry modern rights. Use a museum copy and read
  the object page.

## Where to look

| Collection | Licence | URL pattern |
|---|---|---|
| The Met Open Access | CC0 — commercial use, no permission, no fee | `metmuseum.org/art/collection/search?showOnly=openAccess&q=ARTIST` |
| Wikimedia Commons | **individual per file — read the box** | `commons.wikimedia.org` |
| Wellcome Collection | CC0 or CC-BY — check per item | anatomy, medical plates |
| Biodiversity Heritage Library | mostly no known copyright | botanical and zoological plates |
| Rijksmuseum | public domain, high-res | Dutch masters, ships, birds |
| Art Institute of Chicago | CC0 on public-domain works | Japanese woodblock |
| NYPL Digital Collections | public-domain sets | maps, charts, celestial |
| Smithsonian Open Access | CC0, 4.5M+ items | natural history |

**Do not use:** Pixabay (its licence forbids printing on merchandise for sale,
outright), Unsplash or Pexels (silent on the image being the whole product —
silence is not permission), Google Images "labeled for reuse" (a suggestion, not
a guarantee).

---

## The files, by composition

Each row is one layer in a recipe. `slot` is the `source` filename the recipe
expects — save it under `tools/etsy/sources/` with exactly that name.

### 1 · Orchid Skull — `recipes/orchid-skull.json`

| slot | what | search |
|---|---|---|
| `anatomy-skull.jpg` | anatomical skull, front or three-quarter, strong line | Wellcome → `Vesalius`; or Met → `Vesalius` |
| `orchid-a.jpg` | orchid plate, one clear specimen | BHL → `Bateman Orchidaceae`; Met → `Redouté` |
| `orchid-b.jpg` | a second orchid, different species | same source, different plate |

The orchids are masked by the skull's inverse alpha, so they read as growing
*through* the cranium rather than sitting on it. Pick specimens with visible
stems — a stem crossing the jaw is what sells the effect.

### 2 · Overgrown Prison — `recipes/overgrown-prison.json`

| slot | what | search |
|---|---|---|
| `piranesi-carceri.jpg` | a Carceri plate with a clear staircase | Met → `Piranesi` |
| `ivy-climbing.jpg` | ivy, vine or creeper | BHL → `Hedera`, `climbing plants` |
| `fern-frond.jpg` | one fern frond | BHL → `Pteridophyta`, `fern` |

Piranesi rated **low saturation** in your own research. Pick a plate where the
architecture reads at small scale — the busiest ones turn to noise on cotton.

### 3 · Moonlit Ghost — `recipes/moonlit-ghost.json`

| slot | what | search |
|---|---|---|
| `cellarius-chart.jpg` | a constellation plate | NYPL / Commons → `Cellarius Harmonia Macrocosmica` |
| `yoshitoshi-figure.jpg` | one figure, isolated | Art Institute of Chicago → `Yoshitoshi` |

Yoshitoshi is the **"low — best bet"** row in your saturation table. Read the
Doré/Yoshitoshi warning above before downloading.

### 4 · Marigold Calavera — `recipes/marigold-calavera.json`

| slot | what | search |
|---|---|---|
| `posada-calavera.jpg` | calavera, skull or full skeleton | Commons → `Posada calavera` |
| `marigold-wreath.jpg` | marigold / Tagetes plate | BHL → `Tagetes` |

**Ships before Nov 1.** Día de Muertos is Nov 1–2 and this needs to be ranking
before it, not launching into it.

### 5 · Metamorphosis — `recipes/metamorphosis.json`

| slot | what | search |
|---|---|---|
| `merian-plate.jpg` | plant with caterpillar, chrysalis and moth | BHL → `Merian Metamorphosis Insectorum` |
| `merian-moth.jpg` | a second moth for the corner | same book, another plate |

`Etsy-Art/candidates/pick-3.png` is already a Merian — trace that one properly
and it may serve.

### 6 · Doré's Descent — `recipes/dore-descent.json`

| slot | what | search |
|---|---|---|
| `dore-figure.jpg` | a falling or descending figure | Met → `Doré`; Commons → `Doré Paradise Lost` |
| `thorn-branch.jpg` | thorned branch or bramble | BHL → `Rubus`, `bramble` |

Highest-contrast source in the set. Museum copy only — see the warning above.

### 7 · Fungi Codex — `recipes/fungi-codex.json`

| slot | what | search |
|---|---|---|
| `fungi-plate-a.jpg` | one mushroom species, clean ground | BHL → `Bulliard Champignons` |
| `fungi-plate-b.jpg` | second species, similar scale | same |
| `fungi-plate-c.jpg` | third species | same |
| `moth-small.jpg` | a small moth to break the grid | Millot or Merian |

Four specimens on a grid. Pick ones with **different silhouettes** — three
lookalike caps read as a repeat, not a collection.

### 8 · Kraken Chart — `recipes/kraken-chart.json`

| slot | what | search |
|---|---|---|
| `nautical-chart.jpg` | antique sea chart, visible rhumb lines | NYPL → `sea chart`; Rijksmuseum → `zeekaart` |
| `montfort-octopus.jpg` | the colossal octopus, 1801 | Commons → `Denys de Montfort poulpe colossal` |

The chart is a background at low ink weight — pick one where the linework is
even, not one with a heavy cartouche competing for attention.

---

## After each download

1. Save it into `tools/etsy/sources/` under the exact `slot` filename.
2. Open the recipe and fill that layer's `provenance`:
   ```json
   "provenance": {
     "url": "https://…the file page, not the search result…",
     "licence": "public domain",
     "traced": "2026-09-05",
     "credit": "Piranesi, Carceri plate VII, 1750"
   }
   ```
   `licence` must read as public domain, PD, CC0, or no known copyright.
   Anything else is refused, including anything vague.
3. Log the same entry in `Etsy-Art/SOURCES.md`.
4. `python3 compose.py --recipe recipes/<id>.json --draft --report`
5. **Look at the previews and the silhouette.** Both real defects in this
   pipeline were invisible in the code and obvious in the render.
6. When it reads well, drop `--draft` for the full 4500 × 5400 file.
