# render_plate.py

The image half of the shirt pipeline. `Design/render/render_shirt.py` in the
Cortana repo renders **text** designs; this renders **illustration plates** —
a Haeckel medusa, a Kuniyoshi print, an Audubon bird — into the same
4500×5400 @ 300 DPI Printify front-print file, in the same two colourways.

## Why it exists

Etsy's Creativity Standards were revised in August 2026. The language permitting
sale of digital files of scanned vintage content was removed, and items produced
with computerized tools must be based on the seller's **original design**.
Public-domain art on a physical product is still fine — but there has to be a
design step. This is that step, and `--report` prints a listing-ready sentence
describing only the transformations that actually ran.

It also fixes the most visible tell of an amateur POD shirt: the cream rectangle
of aged paper printed around the artwork.

## Run it

```bash
python3 render_plate.py \
  --src Haeckel-Cyanea-annasethe-1.jpg \
  --slug jellyfish-blue \
  --binomial "Cyanea annasethe" --year 1904 \
  --report
```

Writes `out/<slug>-onlight.png`, `out/<slug>-ondark.png`, and a small
`-preview.png` of each composited on grey so the cutout is checkable.

## What it does, in order

1. **Lifts the paper ground** — flood fill inward from the border, then a
   saturation/value pass for the paper trapped *between* tentacles that the
   border fill cannot reach. That second pass is the difference between fine
   linework and cream blobs; see the two previews in the commit that added it.
2. **Rebuilds tones for DTG** — lithographic plates scan flat and print muddy on
   cotton at chest scale.
3. **Recomposes** for the 15×18in print area. Crops, never stretches.
4. **Typesets** the species binomial and year as a set framing.

## Knobs worth knowing

| Flag | Why |
|---|---|
| `--sat-max` / `--val-min` | Tune the second pass. Too aggressive punches holes through light areas inside the subject; too shy leaves cream between tentacles. Check the preview. |
| `--no-key-enclosed` | Turn the second pass off entirely for a plate with a light-toned subject. |
| `--halo` | Soft light backing on the dark-garment file. A plate with fine dark linework disappears on black without it. |
| `--no-lift` | Keep the paper ground, for a design where it is the point. |

## Before you sell anything it makes

- **Fonts.** OFL files in `fonts/` are preferred; a system-font fallback prints a
  warning and must not be used commercially. Same rule as `render_shirt.py`, for
  the same licensing reason.
- **Source resolution.** Under ~1500px on the short edge goes soft at chest size.
  The script warns but does not stop you.
- **The dark-garment file.** Check it on a real Printify mockup, not on screen.
- **The `--report` copy.** Verify every clause is true of the file you upload.
  Copy claiming design work that did not happen is worse than no copy.

Pillow only. No network, no API, no numpy.
