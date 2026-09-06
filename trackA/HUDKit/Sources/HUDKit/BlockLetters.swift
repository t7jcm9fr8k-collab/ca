import SwiftUI
import AppKit

/// The wordmark, cut from stone.
///
/// **Solid slabs, not a wall of cubes.** The reference logo builds each letter
/// as one carved block with pixel-stepped edges — the bevel, the grain and the
/// extrude all follow the *silhouette*, never the internal grid. Bevelling every
/// cell separately (the first attempt) turns the letterform into graph paper.
///
/// Strokes are two cells thick on a seven-cell cap height. That weight is where
/// the presence comes from; one-cell strokes read as a terminal font no matter
/// how much texture is piled on.
public struct BlockLetters: View {

    public var lines: [String]
    /// Size of one cell. Cap height is 7 × this.
    public var cell: CGFloat = 4
    /// Extrusion depth. 1:1 with `cell` is the setting the owner picked.
    public var depthRatio: CGFloat = 1.0
    public var base: Color = Color(hex: 0x969698)
    /// Fixed so the stone never shimmers between redraws.
    public var seed: UInt64 = 0x5701_4E5

    public init(lines: [String], cell: CGFloat = 4, depthRatio: CGFloat = 1.0,
                base: Color = Color(hex: 0x969698), seed: UInt64 = 0x5701_4E5) {
        self.lines = lines
        self.cell = cell
        self.depthRatio = depthRatio
        self.base = base
        self.seed = seed
    }

    private static let rows = 7

    public var body: some View {
        Canvas { ctx, _ in draw(&ctx) }
            .frame(width: width, height: height)
            .accessibilityLabel(lines.joined(separator: " "))
    }

    // MARK: - Geometry

    private var depth: CGFloat { cell * depthRatio }
    private var pad: CGFloat { max(2, cell * 0.6) }

    private var widestLine: Int {
        lines.map { Self.cellWidth($0) }.max() ?? 0
    }

    private var width: CGFloat {
        CGFloat(widestLine) * cell + depth + pad * 2
    }

    /// Lines overlap by a cell — the descender space of a block alphabet is
    /// dead air, and closing it is what makes a stacked wordmark read as one
    /// object rather than two labels.
    private var height: CGFloat {
        CGFloat(lines.count * Self.rows) * cell
            - CGFloat(max(0, lines.count - 1)) * cell * 0.15
            + depth + pad * 2
    }

    private static func cellWidth(_ text: String) -> Int {
        var w = 0
        for ch in text {
            guard let g = Glyphs.table[ch] else { w += 3 + 1; continue }
            w += g[0].count + 1
        }
        return max(0, w - 1)
    }

    private static func cells(_ text: String) -> Set<GridPoint> {
        var out: Set<GridPoint> = []
        var x = 0
        for ch in text {
            guard let g = Glyphs.table[ch] else { x += 4; continue }
            for (r, row) in g.enumerated() {
                for (c, v) in row.enumerated() where v == "1" {
                    out.insert(GridPoint(x: x + c, y: r))
                }
            }
            x += g[0].count + 1
        }
        return out
    }

    // MARK: - Drawing

    private func draw(_ ctx: inout GraphicsContext) {
        var rng = StoneRNG(seed: seed)
        var originY = pad

        for line in lines {
            let S = Self.cells(line)
            drawLine(&ctx, cells: S, originY: originY, rng: &rng)
            originY += CGFloat(Self.rows) * cell - cell * 0.15
        }
    }

    private func drawLine(_ ctx: inout GraphicsContext,
                          cells S: Set<GridPoint>,
                          originY: CGFloat,
                          rng: inout StoneRNG) {

        func rect(_ x: CGFloat, _ y: CGFloat, _ w: CGFloat, _ h: CGFloat) -> Path {
            Path(CGRect(x: x, y: y, width: w, height: h))
        }
        func origin(_ g: GridPoint) -> CGPoint {
            CGPoint(x: pad + CGFloat(g.x) * cell, y: originY + CGFloat(g.y) * cell)
        }

        // 1 — extruded sides, drawn back to front. Two tones: the right face
        //     catches a little light, the underside gets none.
        for g in S.sorted(by: { ($0.x + $0.y) < ($1.x + $1.y) }) {
            let o = origin(g)
            if !S.contains(GridPoint(x: g.x + 1, y: g.y)) {
                var p = Path()
                p.move(to: CGPoint(x: o.x + cell, y: o.y))
                p.addLine(to: CGPoint(x: o.x + cell + depth, y: o.y + depth))
                p.addLine(to: CGPoint(x: o.x + cell + depth, y: o.y + cell + depth))
                p.addLine(to: CGPoint(x: o.x + cell, y: o.y + cell))
                p.closeSubpath()
                ctx.fill(p, with: .color(base.shaded(0.40)))
            }
            if !S.contains(GridPoint(x: g.x, y: g.y + 1)) {
                var p = Path()
                p.move(to: CGPoint(x: o.x, y: o.y + cell))
                p.addLine(to: CGPoint(x: o.x + depth, y: o.y + cell + depth))
                p.addLine(to: CGPoint(x: o.x + cell + depth, y: o.y + cell + depth))
                p.addLine(to: CGPoint(x: o.x + cell, y: o.y + cell))
                p.closeSubpath()
                ctx.fill(p, with: .color(base.shaded(0.24)))
            }
        }

        // 2 — the face, lit from above.
        for g in S {
            let o = origin(g)
            let fall = 1.18 - 0.26 * (CGFloat(g.y) / CGFloat(Self.rows - 1))
            ctx.fill(rect(o.x, o.y, cell, cell), with: .color(base.shaded(fall)))
        }

        // 3 — stone: big irregular patches, not dust. The patch grid is
        //     deliberately finer than a cell so the texture ignores the
        //     letter grid, and coarsens at small sizes so a sidebar-sized
        //     wordmark doesn't turn to static.
        let q = cell < 6 ? cell : cell * 0.5
        for g in S.sorted(by: { $0.y == $1.y ? $0.x < $1.x : $0.y < $1.y }) {
            let o = origin(g)
            let fall = 1.10 - 0.20 * (CGFloat(g.y) / CGFloat(Self.rows - 1))
            var oy: CGFloat = 0
            while oy < cell {
                var ox: CGFloat = 0
                while ox < cell {
                    let r = rng.unit()
                    let f: CGFloat
                    if r < 0.22 { f = 1.34 }
                    else if r < 0.36 { f = 1.18 }
                    else if r < 0.52 { f = 0.78 }
                    else if r < 0.60 { f = 0.58 }
                    else { ox += q; continue }
                    ctx.fill(rect(o.x + ox, o.y + oy,
                                  min(q, cell - ox), min(q, cell - oy)),
                             with: .color(base.shaded(f * fall)))
                    ox += q
                }
                oy += q
            }
        }

        // 4 — silhouette bevel. Bright along the top and left, dark along the
        //     bottom and right; only on edges, never inside the letter.
        let b = max(1, cell / 3)
        for g in S {
            let o = origin(g)
            if !S.contains(GridPoint(x: g.x, y: g.y - 1)) {
                ctx.fill(rect(o.x, o.y, cell, b), with: .color(base.shaded(1.78)))
            }
            if !S.contains(GridPoint(x: g.x - 1, y: g.y)) {
                ctx.fill(rect(o.x, o.y, b, cell), with: .color(base.shaded(1.52)))
            }
            if !S.contains(GridPoint(x: g.x, y: g.y + 1)) {
                ctx.fill(rect(o.x, o.y + cell - b, cell, b), with: .color(base.shaded(0.50)))
            }
            if !S.contains(GridPoint(x: g.x + 1, y: g.y)) {
                ctx.fill(rect(o.x + cell - b, o.y, b, cell), with: .color(base.shaded(0.60)))
            }
        }

        // 5 — the hard outline. This is most of the contrast: without it the
        //     slabs dissolve into a dark background.
        let ow = max(1, cell / 3)
        let ink = Color(hex: 0x060709)
        for g in S {
            let o = origin(g)
            if !S.contains(GridPoint(x: g.x, y: g.y - 1)) {
                ctx.fill(rect(o.x - ow, o.y - ow, cell + ow * 2, ow), with: .color(ink))
            }
            if !S.contains(GridPoint(x: g.x - 1, y: g.y)) {
                ctx.fill(rect(o.x - ow, o.y - ow, ow, cell + ow * 2), with: .color(ink))
            }
            if !S.contains(GridPoint(x: g.x, y: g.y + 1)) {
                ctx.fill(rect(o.x - ow, o.y + cell, cell, ow), with: .color(ink))
            }
            if !S.contains(GridPoint(x: g.x + 1, y: g.y)) {
                ctx.fill(rect(o.x + cell, o.y - ow, ow, cell), with: .color(ink))
            }
        }
    }
}

struct GridPoint: Hashable {
    let x: Int
    let y: Int
}

/// Two-cell strokes on a seven-row cap height. Widths vary per letter, as they
/// do in a real display face — M is wider than E and forcing them equal is what
/// makes hand-built alphabets look like a spreadsheet.
public enum Glyphs {
    public static let table: [Character: [String]] = [
        "A": ["011110","111111","110011","111111","111111","110011","110011"],
        "C": ["011110","111111","110000","110000","110000","111111","011110"],
        "D": ["111100","111110","110011","110011","110011","111110","111100"],
        "E": ["111111","111111","110000","111110","110000","111111","111111"],
        "I": ["111111","111111","001100","001100","001100","111111","111111"],
        "L": ["110000","110000","110000","110000","110000","111111","111111"],
        "M": ["1100011","1110111","1111111","1101011","1100011","1100011","1100011"],
        "N": ["110011","111011","111111","110111","110011","110011","110011"],
        "O": ["011110","111111","110011","110011","110011","111111","011110"],
        "P": ["111110","111111","110011","111111","111110","110000","110000"],
        "R": ["111110","111111","110011","111111","111110","110110","110011"],
        "S": ["011110","111111","110000","111110","000011","111111","011110"],
        "T": ["111111","111111","001100","001100","001100","001100","001100"],
        "U": ["110011","110011","110011","110011","110011","111111","011110"],
        "Y": ["110011","110011","111111","011110","001100","001100","001100"],
        " ": ["000","000","000","000","000","000","000"],
    ]
}

/// Fixed-sequence noise, so the stone is identical on every redraw. Plain
/// `Double.random` would make the texture crawl every time the view refreshes.
struct StoneRNG {
    private var state: UInt64
    init(seed: UInt64) {
        state = seed &* 6_364_136_223_846_793_005 &+ 1_442_695_040_888_963_407
    }
    mutating func unit() -> CGFloat {
        state = state &* 6_364_136_223_846_793_005 &+ 1_442_695_040_888_963_407
        var z = state
        z = (z ^ (z >> 30)) &* 0xBF58_476D_1CE4_E5B9
        z = (z ^ (z >> 27)) &* 0x94D0_49BB_1331_11EB
        z = z ^ (z >> 31)
        return CGFloat(z % 10_000) / 10_000
    }
}

extension Color {
    /// Multiply brightness, clamped. Used all through the stone renderer.
    func shaded(_ f: CGFloat) -> Color {
        let ns = NSColor(self).usingColorSpace(.sRGB) ?? .gray
        return Color(.sRGB,
                     red: min(1, Double(ns.redComponent * f)),
                     green: min(1, Double(ns.greenComponent * f)),
                     blue: min(1, Double(ns.blueComponent * f)),
                     opacity: Double(ns.alphaComponent))
    }
}
