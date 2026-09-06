# HUD design mockups

Static HTML studies that accompany the HUDKit package. Each uses the same palette as
`Theme.swift` (the 2026-08-15 AA pass) and the same cut-corner, hairline and monospaced-numeral
grammar the Swift views implement. Open any file directly in a browser; none needs a server.
Several honour `prefers-reduced-motion` — flip it on and reload to see the settled frames.

Event names, room labels, task strings and wordmarks in these files are placeholders; the
layouts, timings and contrast reasoning are what they exist to show.

## Shipped

| File | Shows |
|---|---|
| `motion-grammar-demo.html` | The six motion demos from the motion spec: destination smear/cascade, panel materialise (trim-drawn outline, fill wipe, row cascade), the four-beat log event, the reserved impact frame with a live WCAG 2.3.1 flash ledger, the three-tone dial, and the pointer-as-torch hover pool. |
| `graphs-textures-launch-mockup.html` | Three chart upgrades in the house discipline (range chart with draw-in and a labelled win line, week-vs-week with a dashed context line measured at 6.2:1, a twelve-week rhythm heatmap with a monotonic lime ramp), a measured 3.5% texture-grain gate, and the 850ms launch power-on sequence. |
| `hud-mockups.html` | The component sheet: status ribbon with hatched spacers, a state-chip table, bar meters and a segmented loader, the node/branch grammar, a card grammar with scopers and hero numbers, sidebar badges, the adherence ramp and its cost, and two evidence-gated panels. |
| `day-detail-placements.html` | Four placements for a selected-day detail beside a month grid (side panel, below the grid, popover, own destination), with the irregular-mark contrast figures and the cost of each placement. |
| `locked-grid-demo.html` | Interactive comparison of a reflowing panel grid against a locked grid that leaves holes — the spatial-persistence argument. |
| `surfaces-comparison.html` | The same panel on four slabs (cut-corner near-black, frosted glass over a starfield, warm paper, flat black rounded) with the performance and identity cost of each. |
| `sky-radar-options.html` | Four procedural sky treatments (spiral, sprite blob, nebula bloom, dense clusters) over the same seeded star field, and three diagnostics-radar behaviours (continuous, sweep-while-checking, line sweep). |
| `start-page-looks.html` | Four starting-page looks (plaque, cold frame, ready room, cold boot) and the composite built from three of them, each clickable to enter. |

## Excluded

Five files from the original design folder are not shipped:

- Two castle/shop simulation mockups — a business simulation unrelated to the HUD; they carry
  the owner's business figures and embedded character artwork.
- A throne-room render study — unrelated to the HUD; it embeds third-party library code and the
  owner's sprite art.
- A second component ledger — predominantly the owner's business, finance and privacy data,
  and its reusable graphs are already covered by `graphs-textures-launch-mockup.html`.
- A behavioural-copy test — notification copy for the owner's personal habit rule, not HUD design.
