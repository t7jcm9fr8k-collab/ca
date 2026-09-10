> **PRIVATE — NEVER PUBLISH THIS FILE.**
> It is the audit record for the extraction. It quotes no personal value, but it
> enumerates, category by category, what kinds of personal material the original
> app contained — which tells a reader what to go looking for and confirms who the
> author is. It lives in `trackA/_private/` and is excluded from the published
> package by `trackA/PUBLISHING.md`. Keep it; do not ship it.

# EXTRACTION — HUDKit from the source app

What was copied, what was changed, and what has not been checked. Source files are named
without paths; line numbers are those of the SOURCE file at the commit the extraction was taken
from. Every edit falls into one of three classes: (a) a coupling point cut, (b) a comment
rewritten to a neutral voice, (c) access control opened for a package consumer. Nothing else was
touched — no renames, no refactors — with two recorded exceptions: the `Glyphs.table` entries in
`BlockLetters.swift` were re-sorted alphabetically (see that section) and `ReactorOrb.swift`
gained an `import Combine` line (see that section).

Deleted lines shift subsequent line numbers in the shipped copies; the numbers below always
refer to the source.

## Package layout

```
HUDKit/
  Package.swift              tools 5.9, macOS 14, library HUDKit + executable HUDDemo
  LICENSE                    MIT, "Copyright (c) 2026 the HUDKit authors"
  README.md
  Sources/HUDKit/
    Theme.swift              from Theme.swift
    Motion.swift             from Motion.swift
    HUDComponents.swift      from HUDComponents.swift
    BlockLetters.swift       from BlockLetters.swift
    SpaceBackdrop.swift      from SpaceBackdrop.swift
    ReactorOrb.swift         from ReactorOrb.swift
    Models.swift             new — the hoisted value types + environment key
    ThermalWatch.swift       from ThermalWatch.swift (a required non-extension dependency)
  Sources/HUDDemo/
    HUDDemoApp.swift         new
```

No `Extensions.swift` and no `Resources/`: every extension the six files rely on is declared
inside one of them (see "Flagged symbols"), and no named asset is referenced by any of the six.

---

## Theme.swift

**Coupling points cut:** none (the file was self-contained).

**Deleted:** :52-54 — one palette constant and its two-line comment: a third-party brand colour
named after that party and used by nothing that
ships. Reversible from the hex if ever wanted.

**Comments rewritten (new wording):**
- :5-6 → "One file on purpose: the Settings screen needs something real to toggle, and nothing
  built later should have to be re-themed by hand."
- :31-32 → "…added 2026-08-17 at the owner's call after seeing the alternatives rendered."
- :95-96 → "…the row read as decoration rather than a control — the owner reported it as "link
  isn't intuitive" twice before the cause was measured."
- :101 → "The mood hologram colours, verbatim from the original spec."
- :108-109 → "Canonical values, lifted verbatim from `EMOTION_COLORS` in the original castle build."
- :144 → "2026-08-15: global density tighten (~20%), the owner's call."

All WCAG / contrast reasoning (:16-20, :30-49, :56-71, :78-97) is verbatim apart from the two
name substitutions above. The host-view names at :163-164 and the "iOS app" note at :103 are not
identifying and were left as they are.

**Made public:** `Theme` (:7); `Theme.Color` (:15) and every `static let` in it (:21-28, :50,
:72-73, :75-76, :98); `Theme.Mood` (:105), `color` (:115), `label` (:126); `Theme.Metric` (:140)
and its five constants (:141-146); `Theme.Font` (:154), `scale` (:175), `label`/`data`/`readout`/
`body` (:180-191); `Color.init(hex:opacity:)` (:199); `CutCorner` (:211), `cut` (:212), `corners`
(:214), `path(in:)` (:216). **Added:** `public init(cut:corners:)` on `CutCorner` with the same
defaults as the stored properties, since the memberwise init would be internal.

## Motion.swift

**Coupling points cut:** none.

**Comments rewritten:**
- :4 → "First build slice 2026-08-19 (the owner's pick: demos 1, 2, 3, 5-standard, 6)."

References to `RootView`, `StickFight`, `scriptCache`, `ThermalWatch`, `MOTION-OVERHAUL.md` and
`CONTRACTS §12` are internal cross-references, not identifying; left as they are.

**Made public:** `Motion` (:13) and every static in it (:20-21, :24, :26, :34, :37, :39, :41,
:48-49); `Motion.Tone` (:61); `destination` (:67); `destinationTransition(_:)` (:84). `Smear`
(:121), `amount`/`travel` (:123-124), `animatableData` (:126), `body(content:)` (:137).
`CascadeIn` (:155), `order`/`base`/`step`/`active` (:156-158, :166), `body(content:)` (:173).
`extension View` → `public extension View` for `cascadeIn` (:187-193). `FlareRing` (:201),
`trigger`/`tint` (:202-203), `body` (:205). `FlashLedger` (:247), `lastGrant` (:248),
`fightLive` (:252), `Grade` (:254), `request()` (:256). `ImpactFlash` (:272), `trigger`/`tint`
(:273-274), `body` (:276). `FlareRingShot` and `ImpactFlashShot` stay private.
**Added:** `public init(amount:travel:)` on `Smear`; `public init(order:base:step:active:)` on
`CascadeIn`; `public init(trigger:tint:)` on `FlareRing` and `ImpactFlash`.

## HUDComponents.swift

**Coupling points cut (the six):**
The five nested types were qualified with the app's store class name (`<Store>.` below); that
qualifier was deleted and the types are now top-level in `Models.swift`.
- :94 `@Environment(\.launchReadoutsLive)` — key now declared in `Models.swift`; no textual change.
- :147 `var state: <Store>.DayState` → `public var state: DayState`
- :227 `var items: [ScheduledItem]` — type now declared in `Models.swift`; no textual change.
- :370 `var month: <Store>.MonthView` → `public var month: MonthView`
- :476 `monthCell(_ day: <Store>.MonthDay)` → `monthCell(_ day: MonthDay)`
- :501 `var day: <Store>.MonthDay` → `var day: MonthDay` (private `MonthDayCell`)
- :615 `var state: <Store>.PunchState` → `public var state: PunchState`

**Comments rewritten:**
- :38-40 → "Panel codes ("H4", "R4", "FN03") retired 2026-08-15 at the owner's request. The
  parameter survives so call sites don't churn; nothing reads it."
- :220-221 → "2026-08-20, owner feedback: "the weekly calendar tries shoving multiple letters
  into one box" — it did, …" (rest of the paragraph unchanged, reflowed).
- :971-972 → "The red→amber→green gradient was removed 2026-08-18 at the owner's request, …"
- :978-979 → "2026-08-20, owner feedback again: the 15pt solid-lime slab was "too intrusive",
  and the point stands — it was the loudest block of colour on the screen, …"

**Made public:** `HUDPanel` (:11) and `title`/`accent`/`code`/`enterOrder`/`content` (:12-16),
`body` (:27). `Readout` (:82), :83-88, `body` (:96). `TickRail` (:119), :120-122, `body` (:124).
`DayCell` (:145), `date`/`state`/`onToggle` (:146-150), `body` (:176). `AgendaCell` (:225),
:226-231, `body` (:259). `MonthGrid` (:369), every stored var (:370-373, :376, :385, :388, :398,
:403-405, :410, :416), `body` (:429). `IrregularMark` (:593), `path(in:)` (:594). `StateMark`
(:614), `state` (:615), `body` (:635). `HUDButton` (:650), :651-654, `body` (:668).
`HUDPillToggle` (:696), `title` (:697), `isOn` binding (:698), `accent` (:701), `body` (:705).
`Breathing` (:758), :759-761, `body(content:)` (:770). `PeriodicSweep` (:787), :788-790,
`body(content:)` (:796). `extension View` → `public extension View` (:824-831). `StatusRibbon`
(:839), `items` (:840), `body` (:842). `Hatch` (:857), `body` (:858). `MeterRow` (:876),
:877-880, `body` (:882). `SegmentedMeter` (:910), :911-913, `body` (:915). `StateChip` (:927),
:928-930, `body` (:932). `AdherenceRamp` (:958), :959-960, `body` (:967). `MonthDayCell` stays
private.
**Added public memberwise initialisers** (parameter order = declaration order, defaults
preserved) on: `HUDPanel` (`@ViewBuilder content` closure), `Readout`, `TickRail`, `DayCell`,
`AgendaCell`, `MonthGrid`, `IrregularMark` (`init()`), `StateMark`, `HUDButton`, `HUDPillToggle`
(takes `Binding<Bool>`), `Breathing`, `PeriodicSweep`, `StatusRibbon`, `Hatch` (`init()`),
`MeterRow`, `SegmentedMeter`, `StateChip`, `AdherenceRamp`.

## BlockLetters.swift

**Coupling points cut:** none.

**Comments rewritten:**
- :4 → "The wordmark, cut from stone."
- :19 → "Extrusion depth. 1:1 with `cell` is the setting the owner picked."

**Made public:** `BlockLetters` (:14), `lines`/`cell`/`depthRatio`/`base`/`seed` (:16-23),
`body` (:27); `Glyphs` (:212) and `table` (:213) so a consumer can see which characters exist.
`GridPoint`, `StoneRNG` and `Color.shaded(_:)` stay internal. **Added:**
`public init(lines:cell:depthRatio:base:seed:)`.

**Reordered, not changed:** the sixteen entries of `Glyphs.table` (:213-230) are byte-for-byte
the originals, but they are now listed in alphabetical order. In the source the keys were listed
in the order of the wordmark's letters, so the key order itself spelled the app name; the
re-sort removes that. A dictionary literal's order has no runtime effect. The letter *set* is
still only the wordmark's letters plus T U Y L — see "Flagged symbols".

## SpaceBackdrop.swift

**Coupling points cut:** none in the text; `ThermalWatch` (:38, :57) is now supplied by
`ThermalWatch.swift` in the package.

**Comments rewritten:**
- :46-48 → "On a fanless laptop that is a steady drain all day while the app sits behind other
  windows — exactly the "hot after ten minutes" report."
- :551-552 → "…which is why the owner reported it as not moving at all. That report was right,
  and the fix was never "slide faster":"

The reference-clip filename at :547 is not identifying and was left.

**Made public:** `SpaceBackdrop` (:18), `parallax` (:23), `body` (:73). `Streak`, `StarFlash`,
and every private type stay as they were. **Added:** `public init(parallax:)`.

## ReactorOrb.swift

**Coupling points cut:** none in the text; `ThermalWatch` (:44, :361) now comes from the package.

**Comments rewritten:** none needed.

**Added (not one of the three edit classes):** `import Combine` at :2, with a trailing comment,
as a precaution for `@ObservedObject` at :53 — see "Not verified" item 4. The source built
without it; the line is safe to delete if strict fidelity is preferred.

**Made public:** `ReactorOrb` (:29), `mood`/`charge`/`diameter`/`staticFrame` (:30-40), `body`
(:55). Every layer struct, `SeededRNG`, `makeBolt` and `cageBands` stay private. The two
`#Preview` blocks are kept verbatim. **Added:** `public init(mood:charge:diameter:staticFrame:)`.

## ThermalWatch.swift (dependency, not one of the six)

**Comments rewritten:**
- :12 → "A fanless laptop has no fan curve between "warm" and "throttled", so the app's job is
  to keep *average* power low and to back off the moment the machine reports pressure."
- :31 → "LOW HEAT — the owner's manual floor under the ladder (2026-08-19, for long sessions on
  the lap)."

**Made public:** the class (:26), `shared` (:27), `state` as `public private(set)` (:29),
`lowHeat` (:39), `level` (:46). `init` stays private (singleton).

## Models.swift (new)

The models mapper's paste-ready source, unchanged except that it now lives at
`Sources/HUDKit/Models.swift`. Declares `ScheduledItem` + `ScheduledItem.Kind`, `DayState`,
`MonthDay`, `MonthView` (with `summary`), `PunchState`, `LaunchReadoutsLiveKey` and
`EnvironmentValues.launchReadoutsLive` (default `true`). All public, all with public
initialisers. Top-level names were chosen so the five store-class qualifiers in
`HUDComponents.swift` became pure deletions.

---

## Flagged symbols and how each was resolved

| Symbol | Flagged by | Resolution |
|---|---|---|
| `ThermalWatch` (`.shared`, `.level`) | deps | Copied to `Sources/HUDKit/ThermalWatch.swift`, scrubbed, made public. Keeps `import Combine`. |
| `EnvironmentValues.launchReadoutsLive` / `LaunchReadoutsLiveKey` | deps, models | Re-declared in `Models.swift`, default `true`. |
| `<Store>.DayState` | deps, models, scrub | Top-level `public enum DayState` in `Models.swift`; qualifier deleted at :147. |
| `<Store>.MonthView` | deps, models, scrub | Top-level `public struct MonthView` (all five stored members + `summary`); qualifier deleted at :370. |
| `<Store>.MonthDay` | deps, models, scrub | Top-level `public struct MonthDay` (all seven members); qualifiers deleted at :476, :501. |
| `<Store>.PunchState` | deps, models, scrub | Top-level `public enum PunchState: Equatable`; qualifier deleted at :615. |
| `ScheduledItem` / `ScheduledItem.Kind` | deps, models | Copied into `Models.swift` with `letter` kept (it feeds `id`); comment on `Kind` in neutral voice. |
| `Color(hex:opacity:)` | deps | Ships in `Theme.swift`; made public. |
| `Color.shaded(_:)` | deps | Ships in `BlockLetters.swift`; internal (file-local use only). |
| `View.cascadeIn(_:base:step:active:)` | deps | Ships in `Motion.swift`; extension made public. |
| `View.breathing(...)`, `View.periodicSweep(...)` | deps | Ship in `HUDComponents.swift`; extension made public. |
| `NSCursor`, `NSColor` | deps | Platform pinned to macOS 14 in `Package.swift`; `BlockLetters.swift` keeps `import AppKit`. |
| Named assets (`Image("…")`, `Color("…")`, custom fonts) | deps, scrub | None referenced by the six; no resource bundle. The product icon and the third-party logo imageset were not copied. |
| `UserDefaults "type.scale"` | deps | Unchanged; documented in README as the type-scale contract. |
| `UserDefaults "power.lowHeat"` | deps | Travels with `ThermalWatch`; documented in README. |
| Third-party-brand palette constant in `Theme.Color` (:52-54) | deps, scrub | Deleted (no shipped caller). |
| The same colour as a CSS variable in mockups | scrub | Removed from the two shipped files that declared it; the one meter that used it recoloured to `var(--earned)`. |
| Glyph table spelling the app name by omission | scrub | Entries kept verbatim but re-sorted alphabetically so the key order no longer spells the name; the letter set was not extended (an alphabet redraw is a design change). Recorded as an open issue. |
| Internal doc refs (`MOTION-OVERHAUL.md`, `CONTRACTS §12`, `SKILL-TREE.md`, `VISION.md`, reference clip) | scrub | Kept; not identifying. |
| Host view names in comments (`RootView`, `StickFight`, `DashboardView`, `StudyLibrary`, `DiagnosticsPanel`, `TrendsView`) | scrub | Kept; not identifying. |

---

## Not verified

Nothing here has been compiled — this container has no Swift toolchain. The places most likely
to need a fix on a Mac, in rough order of likelihood:

1. **`FlashLedger` modifier order.** `nonisolated(unsafe) public static var` was written by
   prefixing `public` to the existing modifier chain. If the compiler objects to the order, swap
   to `public nonisolated(unsafe) static var`.
2. **`HUDPillToggle` public init.** `@Binding public var isOn` plus `self._isOn = isOn` in an
   explicit init is standard, but a property-wrapper access-level warning is possible.
3. **`HUDPanel` init.** `@ViewBuilder public var content: Content` as a stored property with an
   explicit init that assigns `content()` — matches the original (which relied on the synthesised
   init). If the wrapper on a stored property is rejected, drop `@ViewBuilder` from the property
   and keep it on the init parameter.
4. **`ReactorOrb.swift` and `Combine`.** The source used `@ObservedObject` without
   `import Combine` and built; the shipped copy adds `import Combine` at the top anyway (the
   compile audit's one precautionary edit), so the macOS 26 SDK's stricter visibility cannot
   bite here.
5. **`#Preview` macros in a package.** Fine in Xcode 15+ / tools 5.9; if a bare `swift build`
   on an older toolchain rejects them, wrap both blocks in `#if DEBUG` or delete them.
6. **`MonthGrid.onChange(of:) { old, new in }`** and `.contentTransition(.symbolEffect(.replace))`
   need macOS 14, which the platform floor provides.
7. **Demo activation.** `HUDDemoApp.init()` promotes the process with
   `setActivationPolicy(.regular)` and activates on the next runloop turn; if the window still
   opens behind the terminal, activate again from `onAppear`.
8. **Demo layout widths.** The demo's fixed panel widths were chosen without rendering; some
   panels may want to be wider or the window minimum larger.
9. **Demo `DateFormatter.localizedString`** — used with `dateStyle: .medium, timeStyle: .none`;
   correct signature but unexercised.
10. **`Theme.Font.scale`** in the demo's Settings panel is formatted with `String(format:)` from
    a `CGFloat` — fine on 64-bit macOS.
11. **Duplicate type names across modules.** `MonthView`, `DayState` etc. are top-level in
    `HUDKit`; a host app that already declares the same names must qualify (`HUDKit.MonthView`).
12. **`MonthDay.id` uniqueness** in the demo's generated month — padding ids `pad-n` and day ids
    `d-n` never collide, but SwiftUI will warn if they ever do.
