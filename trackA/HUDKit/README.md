# HUDKit

A sci-fi HUD design system for SwiftUI on macOS. It is the visual layer of a working
instrument-style app, extracted as a standalone Swift package: one palette with a strict
discipline, tick rails, monospaced readouts, a stone-cut block-letter wordmark, a procedural
space backdrop, a reactor orb, and a single motion grammar that every component obeys.

Everything in it is built from SwiftUI primitives — `Canvas`, `Shape`, `drawingGroup()`,
compositor transforms. No chart framework, no assets, no custom fonts.

## What ships

**Palette and metrics** — `Theme`
- `Theme.Color` — the palette: `void`, `panel`, `panelHi` surfaces; `primary` (cyan, resting),
  `alert` (orange, attention), `earned` (gold, achieved); `structure` for strokes and rails;
  `logged` / `missed` tracker states; `irregular` for calendar marks; `text`, `textMuted`,
  `textFaint`. The discipline: cyan is the resting state, orange means attention, gold means
  earned. Nothing else gets a colour.
- `Theme.Mood` — six mood states, each with a hologram colour and an uppercase label.
- `Theme.Metric` — rail width, corner cut, hairline, gutter, panel padding.
- `Theme.Font` — `label`, `data`, `readout`, `body`, all multiplied by one `scale` read once at
  launch from `UserDefaults` key `"type.scale"` (default 1.2). Anything numeric is monospaced.
- `CutCorner` — the angular clipped-corner shape. The references cut corners; they never round them.
- `Color(hex:opacity:)`.

**Components** — `HUDComponents.swift`
- `HUDPanel` — framed panel with a label tab; with `enterOrder` set it draws its own outline in
  and wipes its body in behind, staggered per panel.
- `Readout` — labelled monospaced figure with directional numeral roll; honours the
  `launchReadoutsLive` environment key for a roll-from-zero power-on.
- `TickRail` — the vertical tick rails that frame the references.
- `DayCell`, `AgendaCell`, `MonthGrid` — the rolling 7-day tracker cell, the agenda-strip cell
  with a hover card, and the month grid with cascading cells, irregular marks and paging.
- `StateMark` — the three punch-list marks, shape plus colour, never colour alone.
- `HUDButton` — the four-beat press. `HUDPillToggle` — the ON/OFF morph.
- `StatusRibbon`, `Hatch`, `MeterRow`, `SegmentedMeter`, `StateChip`, `AdherenceRamp`,
  `IrregularMark` — the component-sheet pieces.
- `Breathing` / `.breathing()` and `PeriodicSweep` / `.periodicSweep()` — the two sanctioned idle
  motions: one repeating opacity breath, and a duty-cycled light sweep.

**Motion** — `Motion`
- One author for every timing: `enter`, `exit`, `event`, `micro` curves; cascade `step`,
  `cascadeCap`, `panelStep`; the 25° `grainIn` / `grainOut` axis everything arrives and leaves
  along; `destination` and `destinationTransition(_:)` in three tones (`deliberate`, `standard`,
  `fast`); `Smear`, `CascadeIn` / `.cascadeIn(_:)`, `FlareRing`, `ImpactFlash`, and the
  `FlashLedger` that keeps reserved impact frames inside the WCAG 2.2 SC 2.3.1 budget.

**Wordmark** — `BlockLetters`
- Letters cut from stone: solid slabs with an extruded side, a lit face, seeded stone texture, a
  silhouette bevel and a hard outline, drawn once into a `Canvas`. The glyph table (`Glyphs`)
  currently covers A C D E I L M N O P R S T U Y and space; unknown characters render as a gap.

**Backdrop** — `SpaceBackdrop`
- Nebula washes, a galactic plane, two spinning galaxies, three star layers at different depths,
  clusters, thirty twinkling stars, shooting stars and collisions. Every layer is rasterised once
  and then moved by the GPU; it parks behind other windows and under thermal pressure.

**Reactor** — `ReactorOrb`
- Iridescent mist, a matte sphere, fractal lightning, a rotating rim, a gold armillary cage and a
  battery arc, all driven by one breath at 30fps, frozen to an honest frame when it should be.

**Models** — `Models.swift`
- Plain value types the views draw: `ScheduledItem` (with `Kind`), `DayState`, `MonthDay`,
  `MonthView`, `PunchState`, and the `launchReadoutsLive` environment key (default `true`).
  The host decides what a day *is*; the views only render what these say.

**Thermal governor** — `ThermalWatch`
- One observable wrapper around `ProcessInfo.thermalState` with a manual LOW HEAT floor
  (`UserDefaults` key `"power.lowHeat"`). The sky and the orb read its `level`.

## The contrast pass

The palette was re-measured on 2026-08-15 and the comments in `Theme.swift` carry the figures.
In substance:

- Every readable tier measures at least **4.5:1** against every surface it sits on. The lowest
  pair is `alert` on `panelHi` at **6.5:1**. Surfaces were separated further from the void at the
  same time.
- `textMuted` (`#9AB2D0`) measures 6.59:1 on `void`, 6.22:1 on `panel`, 5.68:1 on `panelHi`
  (8.4:1 by an earlier measurement on `panel`).
- `textFaint` (`#4A5F7A`) is the one tier left unchanged and it cannot reach 4.5:1 anywhere:
  3.03:1 on `void`, 2.86:1 on `panel`, 2.61:1 on `panelHi`. It is for structural marks only —
  panel codes, rail numerals, the dim scaffolding that gives the HUD its depth. Never text the
  user has to read. The row that once used it for a link destination read as decoration until
  the cause was measured; if a user must read it to act, use `textMuted` or brighter.
- `irregular` (`#FF3B30`) was checked numerically as a **graphical object** under WCAG 2.2
  SC 1.4.11, whose floor is 3:1, not the 4.5:1 text floor: 5.14:1 on `panel`, 4.27:1 on
  `panelHi`, 5.59:1 on `void`. That distinction is the whole reason the colour exists — scored
  as text, every real red failed and only pinks at hue 339° survived. It sits 3° from
  `Mood.angry` and survives that only by never sharing a form: it is a corner triangle on a
  30×26 cell, never a filled block or a banner. And never text: at 4.27:1 on `panelHi` it is
  below the reading floor.
- `logged` (lime, hue 92°) and `missed` (yellow, hue 52°) both clear 11:1 on `panelHi`. `missed`
  sits 10° from `earned` gold, which every yellow does; the two are told apart by treatment
  rather than hue — a logged cell is filled and carries a dot, a missed cell is outline only.
- State always survives greyscale: shape plus colour for the punch marks, fill plus dot for a
  logged day, a marker rather than a gradient for adherence. The old red→amber→green ramp was
  removed for exactly that reason, and the comment on `AdherenceRamp` says not to bring it back.

Motion has its own accessibility rules: Reduce Motion renders the settled frame everywhere, the
reserved impact frame never flashes under Reduce Motion, and `FlashLedger` keeps every flash in
the app inside a ceiling of 3 per second with a house budget of 2 (WCAG 2.2 SC 2.3.1).

## Install

Swift Package Manager, macOS 14 or later:

```swift
// Package.swift
dependencies: [
    .package(path: "../HUDKit"),          // or a git URL once published
],
targets: [
    .target(name: "YourApp", dependencies: ["HUDKit"]),
]
```

Or in Xcode: File → Add Package Dependencies… and point it at the package directory.

## Minimal usage

```swift
import SwiftUI
import HUDKit

struct Dashboard: View {
    @State private var minutes: Double = 225

    var body: some View {
        ZStack {
            Theme.Color.void.ignoresSafeArea()
            SpaceBackdrop().ignoresSafeArea()

            HUDPanel(title: "The commitment", accent: Theme.Color.earned, enterOrder: 0) {
                VStack(alignment: .leading, spacing: 12) {
                    Readout(label: "Minutes this week", value: "\(Int(minutes))",
                            suffix: "MIN", roll: minutes)
                    HStack(spacing: 8) {
                        ForEach(0..<7, id: \.self) { i in
                            DayCell(date: Calendar.current.date(byAdding: .day, value: i - 6, to: .now)!,
                                    state: i == 6 ? .pending : (i % 2 == 0 ? .done : .rest))
                        }
                    }
                    HUDButton(title: "Log 10 min", accent: Theme.Color.earned, filled: true) {
                        withAnimation(Motion.event) { minutes += 10 }
                    }
                }
            }
            .padding(40)
        }
        .preferredColorScheme(.dark)
    }
}
```

Set `Theme`'s type scale before launch if you want something other than 1.2:
`UserDefaults.standard.set(1.0, forKey: "type.scale")`. It is read once, so it applies on the
next launch.

## The demo

```
cd HUDKit
swift run HUDDemo
```

`HUDDemo` is a single window that exercises every public component on the space backdrop with
sample model values built in code: a week of `DayState`, an agenda strip, a generated `MonthView`,
three punch-list rows, the reactor at each mood, the tone dial, the flash ledger, and the LOW HEAT
floor. It promotes itself to a regular app on launch, since a SwiftPM executable has no bundle.

## Notes

- The `#Preview` blocks in `ReactorOrb.swift` are kept for the Xcode canvas; they build with any
  Xcode 15+ toolchain (`swift build` included) and do nothing at runtime.
- `BlockLetters` draws only the characters in `Glyphs.table`; extend the table (two-cell strokes
  on a seven-row cap height) for a fuller alphabet.
- `ThermalWatch`, `SpaceBackdrop` and `ReactorOrb` are macOS-only by construction (`NSCursor`,
  `NSColor`, `scenePhase`, `ProcessInfo.thermalState`).

## Licence

MIT — see `LICENSE`. Copyright (c) 2026 the HUDKit authors.
