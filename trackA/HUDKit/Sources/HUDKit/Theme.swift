import SwiftUI

/// Every colour, metric, and font in the app lives here.
///
/// One file on purpose: the Settings screen needs something real to toggle,
/// and nothing built later should have to be re-themed by hand.
public enum Theme {

    // MARK: - Palette
    //
    // Read from the seven reference images. The discipline that makes them all
    // feel like one world: cyan is the resting state, orange means attention,
    // gold means earned. Nothing else gets a colour.

    public enum Color {
        // 2026-08-15 — the AA contrast pass. Every readable tier now measures
        // ≥ 4.5:1 against every surface it sits on (lowest pair: alert on
        // panelHi, 6.5:1). Surfaces separated further from the void at the
        // same time. textFaint alone is unchanged: decorative marks stay dim
        // on purpose, and legibility beats mood everywhere something is read.
        public static let void      = SwiftUI.Color(hex: 0x050A14)  // base — unchanged
        public static let panel     = SwiftUI.Color(hex: 0x0D1526)  // raised surfaces (was 0B1220)
        public static let panelHi   = SwiftUI.Color(hex: 0x18263F)  // hover / active (was 111C2E)

        public static let primary   = SwiftUI.Color(hex: 0x5FDDFF)  // cyan — resting (was 4FD8FF)
        public static let structure = SwiftUI.Color(hex: 0x3A5A82)  // strokes, rails (was 2A4A6B)
        public static let alert     = SwiftUI.Color(hex: 0xFF8A55)  // orange — attention (was FF6B2C)
        public static let earned    = SwiftUI.Color(hex: 0xFFCF57)  // gold — achieved (was FFC53D)

        /// Calendar irregularity. **The one colour outside the cyan-resting /
        /// orange-attention / gold-earned discipline**, added because every
        /// alternative read worse once it was rendered.
        ///
        /// Checked numerically, not by eye: **5.14:1 on `panel`, 4.27:1 on
        /// `panelHi`, 5.59:1 on `void`.** That clears WCAG 2.2 SC 1.4.11, which
        /// is the **3:1** floor for graphical objects — not the 4.5:1 text
        /// floor. That distinction is the whole reason this colour exists: a
        /// first pass scored it as text, rejected every real red, and left only
        /// pinks at hue 339° that did not read as an alarm.
        ///
        /// ⚠ **Sits 3° from `Mood.angry` (0xFF4A4A).** They survive that
        /// collision by never sharing a form — this is a corner triangle on a
        /// 30×26 cell, `angry` is a labelled mood chip carrying the word
        /// AGITATED. **Do not use this for anything that renders as a filled
        /// block or a banner**, or the two become the same thing on screen.
        ///
        /// ⚠ **Never for text.** At 4.27:1 on `panelHi` it is below the 4.5:1
        /// reading floor. Marks and strokes only — same rule as `textFaint`,
        /// for the same measured reason.
        public static let irregular = SwiftUI.Color(hex: 0xFF3B30)

        /// Tracker states. Green you did it, yellow you did not.
        ///
        /// This reads as a traffic light on purpose, and it fits the design
        /// rather than fighting it: the whole premise is that one miss is noise
        /// worth one point, not a catastrophe. Yellow understates a miss
        /// correctly and leaves `alert` orange reserved for the single thing
        /// the host app is meant to raise its voice about.
        ///
        /// Hues 92° and 52°, 40° apart, both clearing 11:1 against `panelHi`.
        ///
        /// ⚠ `missed` sits 10° from `earned` gold, which is unavoidable — every
        /// yellow does. They are told apart by treatment rather than hue: a
        /// logged cell is filled and carries a dot, a missed cell is outline
        /// only. If gold and yellow ever read as the same thing on screen, the
        /// fix is to move the agenda strip's E glyph off gold, not to nudge
        /// this value.
        public static let logged    = SwiftUI.Color(hex: 0x97F04A)  // lime — logged (was 8FE83F)
        public static let missed    = SwiftUI.Color(hex: 0xF2DC45)  // yellow — missed (was EFD52E)

        public static let text      = SwiftUI.Color(hex: 0xECF3FC)  // (was DDE8F5)
        public static let textMuted = SwiftUI.Color(hex: 0x9AB2D0)  // (was 7E97B5) — 8.4:1 on panel

        /// ⚠ **Structural marks only. Never text the user has to read.**
        ///
        /// Measured against every surface in this file, `textFaint` cannot reach
        /// the WCAG 2.2 AA floor of 4.5:1 anywhere:
        ///
        /// | on | textFaint | textMuted |
        /// |---|---|---|
        /// | `void`    | 3.03:1 | 6.59:1 |
        /// | `panel`   | 2.86:1 | 6.22:1 |
        /// | `panelHi` | 2.61:1 | 5.68:1 |
        ///
        /// That is fine for what it exists for — panel codes, rail numerals, the
        /// dim scaffolding that gives the HUD its depth. Those are decorative and
        /// the design depends on them receding.
        ///
        /// It is not fine for anything load-bearing. The Next Action row used it
        /// for the line naming the link's destination, at 2.7:1, and the row read
        /// as decoration rather than a control — it was reported twice as "link
        /// isn't intuitive" before the cause was measured. If a user must
        /// read it to act, use `textMuted` or brighter.
        public static let textFaint = SwiftUI.Color(hex: 0x4A5F7A)
    }

    /// The mood hologram colours, verbatim from the original spec.
    ///
    /// Note `neutral` is WHITE, not purple. The iOS app drifted to purple; the
    /// spec says white default. Five of the six already matched.
    public enum Mood: String, CaseIterable, Codable {
        case neutral, happy, sad, angry, disgust, worried

        /// Canonical values, lifted verbatim from `EMOTION_COLORS` in the
        /// original build. These were previously guessed from the written spec;
        /// these are the real ones.
        ///
        /// Name mapping: the original spec calls them `mad` and `grossed`. The
        /// backend and this app use `angry` and `disgust`. Same six states, and
        /// the backend's vocabulary wins because it's already wired end to end.
        public var color: SwiftUI.Color {
            switch self {
            case .neutral: return SwiftUI.Color(hex: 0xE8ECFF)   // white
            case .happy:   return SwiftUI.Color(hex: 0xFFD84A)   // yellow
            case .sad:     return SwiftUI.Color(hex: 0x4A9EFF)   // blue
            case .angry:   return SwiftUI.Color(hex: 0xFF4A4A)   // red   (original: mad)
            case .disgust: return SwiftUI.Color(hex: 0x57FF8A)   // green (original: grossed)
            case .worried: return SwiftUI.Color(hex: 0xFF7AD9)   // pink
            }
        }

        public var label: String {
            switch self {
            case .neutral: return "NOMINAL"
            case .happy:   return "ELEVATED"
            case .sad:     return "SUBDUED"
            case .angry:   return "AGITATED"
            case .disgust: return "AVERSE"
            case .worried: return "CONCERNED"
            }
        }
    }

    // MARK: - Metrics

    public enum Metric {
        public static let railWidth: CGFloat   = 28    // edge tick rails
        public static let cut: CGFloat         = 10    // corner clip — cut, not rounded
        public static let hairline: CGFloat    = 1
        // 2026-08-15: global density tighten (~20%).
        public static let gutter: CGFloat      = 13    // was 16
        public static let panelPad: CGFloat    = 14    // was 18
    }

    // MARK: - Type
    //
    // Anything numeric is monospaced. Timers, counts, scores. Non-negotiable —
    // it's what makes an interface read as an instrument rather than a document.

    public enum Font {
        /// One dial for the whole app's type, added 2026-08-16.
        ///
        /// Ninety-nine call sites pass an explicit size — `Theme.Font.data(9)`
        /// and so on — so raising the defaults would have changed almost
        /// nothing. Multiplying inside these functions steps every label at
        /// once and stays a single number to tune later.
        ///
        /// ⚠ Raising this can clip fixed-width columns. The ones that were
        /// widened for 1.2 are other fixed-width tables in the host app;
        /// check them again if the scale is pushed further.
        /// Read from storage **once at launch**, not per call.
        ///
        /// A computed `static var` would hit `UserDefaults` on every one of the
        /// 99 call sites, every render, including inside per-frame Canvas views.
        /// A lazy `static let` evaluates once and costs nothing after.
        ///
        /// ⚠ **The consequence is that changing it applies on relaunch.** That
        /// is a deliberate trade and the Settings screen says so in words —
        /// making it live means moving the value into something observable, and
        /// a silent no-op would be worse than an honest "restart to apply".
        public static let scale: CGFloat = {
            let stored = UserDefaults.standard.double(forKey: "type.scale")
            return stored > 0 ? stored : 1.2
        }()

        public static func label(_ size: CGFloat = 10) -> SwiftUI.Font {
            .system(size: size * scale, weight: .semibold, design: .default)
        }
        public static func data(_ size: CGFloat = 14) -> SwiftUI.Font {
            .system(size: size * scale, weight: .medium, design: .monospaced)
        }
        public static func readout(_ size: CGFloat = 46) -> SwiftUI.Font {
            .system(size: size * scale, weight: .light, design: .monospaced)
        }
        public static func body(_ size: CGFloat = 13) -> SwiftUI.Font {
            .system(size: size * scale, weight: .regular)
        }
    }
}

// MARK: - Helpers

extension Color {
    /// Hex literal init, e.g. Color(hex: 0x4FD8FF)
    public init(hex: UInt32, opacity: Double = 1) {
        self.init(
            .sRGB,
            red:     Double((hex >> 16) & 0xFF) / 255,
            green:   Double((hex >>  8) & 0xFF) / 255,
            blue:    Double( hex        & 0xFF) / 255,
            opacity: opacity
        )
    }
}

/// Angular clipped corners. The references cut corners; they never round them.
public struct CutCorner: Shape {
    public var cut: CGFloat = Theme.Metric.cut
    /// Which corners to clip. Default is the diagonal pair, as in the HUD panels.
    public var corners: [UnitPoint] = [.topLeading, .bottomTrailing]

    public init(cut: CGFloat = Theme.Metric.cut,
                corners: [UnitPoint] = [.topLeading, .bottomTrailing]) {
        self.cut = cut
        self.corners = corners
    }

    public func path(in r: CGRect) -> Path {
        var p = Path()
        let tl = corners.contains(.topLeading)     ? cut : 0
        let tr = corners.contains(.topTrailing)    ? cut : 0
        let br = corners.contains(.bottomTrailing) ? cut : 0
        let bl = corners.contains(.bottomLeading)  ? cut : 0

        p.move(to: CGPoint(x: r.minX + tl, y: r.minY))
        p.addLine(to: CGPoint(x: r.maxX - tr, y: r.minY))
        if tr > 0 { p.addLine(to: CGPoint(x: r.maxX, y: r.minY + tr)) }
        p.addLine(to: CGPoint(x: r.maxX, y: r.maxY - br))
        if br > 0 { p.addLine(to: CGPoint(x: r.maxX - br, y: r.maxY)) }
        p.addLine(to: CGPoint(x: r.minX + bl, y: r.maxY))
        if bl > 0 { p.addLine(to: CGPoint(x: r.minX, y: r.maxY - bl)) }
        p.addLine(to: CGPoint(x: r.minX, y: r.minY + tl))
        p.closeSubpath()
        return p
    }
}
