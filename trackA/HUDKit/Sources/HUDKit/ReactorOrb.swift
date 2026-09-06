import SwiftUI
import Combine   // `@ObservedObject` below; imported by name, as in ThermalWatch.swift

// MARK: - Deterministic randomness

private struct SeededRNG: RandomNumberGenerator {
    private var state: UInt64
    init(seed: UInt64) { state = seed == 0 ? 0x9E3779B97F4A7C15 : seed }
    mutating func next() -> UInt64 {
        state ^= state << 13
        state ^= state >> 7
        state ^= state << 17
        return state
    }
}

// MARK: - Reactor
//
// NOTE ON STRUCTURE — this is why the file looks over-decomposed.
//
// Every layer is its own small struct rather than a computed property on one
// big view. Swift type-checks each struct's `body` independently, and mixing
// CGFloat with Double inside a single large expression makes the solver explore
// an exploding number of overloads. That is what produced
// "unable to type-check this expression in reasonable time".
//
// Two rules held throughout: geometry is CGFloat, time and angles are Double,
// and every conversion between them is written out. No implicit bridging.

public struct ReactorOrb: View {
    public var mood: Theme.Mood
    public var charge: Double
    public var diameter: CGFloat = 190

    /// Render one frame and stop.
    ///
    /// An Xcode preview cannot afford a 60fps timeline driving a fractal
    /// lightning `Canvas` and three blurred `.plusLighter` blobs — the canvas
    /// gives up at five seconds. The dashboard passes this so its own preview
    /// stays inside the budget; nothing at runtime sets it.
    public var staticFrame: Bool = false

    public init(mood: Theme.Mood, charge: Double, diameter: CGFloat = 190,
                staticFrame: Bool = false) {
        self.mood = mood
        self.charge = charge
        self.diameter = diameter
        self.staticFrame = staticFrame
    }

    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @Environment(\.scenePhase) private var scenePhase
    @ObservedObject private var thermal = ThermalWatch.shared

    /// The orb was the app's one always-on 60fps consumer — running behind
    /// other windows, on battery, on a hot chassis, all day. The 2026-08-19
    /// governor: it breathes at 30 (the breath is ~0.1Hz; sixty bought
    /// nothing), parks behind other windows exactly as the fight does, and
    /// freezes to its honest frame under `.serious` thermal pressure.
    private var frozen: Bool {
        reduceMotion || staticFrame || scenePhase != .active || thermal.level >= 2
    }

    public var body: some View {
        TimelineView(.animation(minimumInterval: 1.0 / 30.0, paused: frozen)) { tl in
            OrbBody(
                mood: mood,
                charge: charge,
                diameter: diameter,
                // 2.53 is where `breath` peaks, so the frozen frame is the
                // brightest honest one rather than whatever the clock landed on.
                t: frozen ? 2.53 : tl.date.timeIntervalSince1970
            )
        }
        .frame(width: diameter, height: diameter)
    }
}

// MARK: - Assembly

private struct OrbBody: View {
    let mood: Theme.Mood
    let charge: Double
    let diameter: CGFloat
    let t: Double

    private var coreR: CGFloat { diameter * 0.30 }
    private var cageR: CGFloat { diameter * 0.40 }

    /// One slow breath drives every layer, so the object pulses as a single body
    /// instead of several parts drifting out of phase.
    private var breath: Double { 0.5 + 0.5 * sin(t * 0.62) }
    private var pulse: CGFloat { CGFloat(1.0 + 0.035 * breath) }
    private var flare: Double { 0.72 + 0.28 * breath }

    var body: some View {
        ZStack {
            MistLayer(mood: mood, diameter: diameter, t: t, flare: flare, pulse: pulse)
            CageLayer(diameter: diameter, radius: cageR, t: t, flare: flare, front: false)
            SphereLayer(radius: coreR, pulse: pulse)
            LightningLayer(mood: mood, diameter: diameter, radius: coreR, t: t, flare: flare)
            RimLayer(mood: mood, diameter: diameter, radius: coreR, t: t, flare: flare)
            CageLayer(diameter: diameter, radius: cageR, t: t, flare: flare, front: true)
            BatteryArc(mood: mood, charge: charge, diameter: diameter, flare: flare)
        }
        .frame(width: diameter, height: diameter)
        .animation(.easeInOut(duration: 1.1), value: mood)
    }
}

// MARK: - Preview
//
// All six moods side by side, because the mist triad is the one thing you
// cannot check by running the app: ELEVATED only appears at 100% adherence on
// scheduled days, so a fix to it is otherwise unverifiable until you have a
// perfect week. This makes it a five-second look in the canvas.
//
// Watch for hue collision. Each orb should show three distinguishable colour
// zones. `.angry` is the deliberate exception — 24° of separation, so it reads
// as one hot mass on purpose.

#Preview("Reactor · all six moods") {
    ScrollView {
        LazyVGrid(columns: [GridItem(.adaptive(minimum: 170), spacing: 14)], spacing: 18) {
            ForEach(Theme.Mood.allCases, id: \.self) { mood in
                VStack(spacing: 10) {
                    OrbBody(mood: mood, charge: 0.72, diameter: 140, t: 2.53)
                        .frame(height: 165)
                    Text(mood.label)
                        .font(Theme.Font.label(11))
                        .tracking(3)
                        .foregroundStyle(mood.color)
                    Text(mood.rawValue)
                        .font(Theme.Font.data(9))
                        .foregroundStyle(Theme.Color.textMuted)
                }
            }
        }
        .padding(24)
    }
    .frame(width: 620, height: 560)
    .background(Theme.Color.void)
    .preferredColorScheme(.dark)
}

// It draws `OrbBody` directly rather than `ReactorOrb`, which is deliberate.
//
// `ReactorOrb` wraps everything in a 60fps `TimelineView`; six of those at once,
// each driving a fractal-lightning `Canvas` and three blurred `.plusLighter`
// blobs, overruns the preview's update budget — the canvas gives up with
// "Updating took more than 5 seconds". `OrbBody` takes `t` as a plain value, so
// pinning it renders one frame and stops.
//
// `t = 2.53` is chosen, not arbitrary: `breath` peaks at `sin(t · 0.62) = 1`,
// which puts flare at maximum and catches the lightning early in its decay.
// The brightest honest frame, and identical across all six so the only thing
// varying is colour.
//
// (`.environment(\.accessibilityReduceMotion, true)` would have been tidier but
// does not compile — that key path is read-only.)

// MARK: - Iridescent mist
//
// The reference burns cyan, magenta and gold at once. Three offset blobs on
// .plusLighter, each drifting on its own period so the colour boundaries never
// settle into a fixed pattern.

private struct MistLayer: View {
    let mood: Theme.Mood
    let diameter: CGFloat
    let t: Double
    let flare: Double
    let pulse: CGFloat

    private var triad: [Color] {
        let m: Color = mood.color
        switch mood {
        case .neutral: return [Color(hex: 0x6FE3FF), Color(hex: 0xC86BFF), Color(hex: 0xFFD37A)]
        // Gold leads (happy = earned), then mint and magenta at 126°/105°/129°.
        // Was [m, 0xFF8A3D, 0x7FE9FF] — gold at 47° and orange at 24° sit 23°
        // apart, and two warm blobs 23° apart on .plusLighter under a 0.055·d
        // blur add into one undifferentiated smear. That left ELEVATED, the
        // best week you can have, as the only mood with no iridescence.
        case .happy:   return [m, Color(hex: 0x5FF0E0), Color(hex: 0xC86BFF)]
        case .sad:     return [m, Color(hex: 0x8A6BFF), Color(hex: 0x5FF0E0)]
        case .angry:   return [m, Color(hex: 0xFF8A3D), Color(hex: 0xFF5FA8)]
        case .disgust: return [m, Color(hex: 0xC8FF6B), Color(hex: 0x5FF0E0)]
        case .worried: return [m, Color(hex: 0xC86BFF), Color(hex: 0x7FB2FF)]
        }
    }

    var body: some View {
        let colors: [Color] = triad
        let blurR: CGFloat = diameter * 0.055
        let alpha: Double = 0.62 * flare + 0.30
        // ⚠ Baked per blob, 2026-08-19 heat pass. The half-second clock
        // quantisation this replaced still re-blurred the whole stack twice a
        // second; blurring INSIDE each blob (before its offset) bakes three
        // textures once per mood and then only *moves* them — zero filter
        // work per frame, and the drift is smooth again instead of stepped.
        // Gaussian blur is linear and plusLighter is additive, so per-blob
        // blur then merge is the same image the merged blur produced.
        // Breath stays live: opacity and scale ride the baked textures.
        return ZStack {
            Blob(color: colors[0], angle: t * 0.11,
                 dist: diameter * 0.10, size: diameter * 1.15, blur: blurR)
            Blob(color: colors[1], angle: -t * 0.08 + 2.1,
                 dist: diameter * 0.13, size: diameter * 1.00, blur: blurR)
            Blob(color: colors[2], angle: t * 0.06 + 4.2,
                 dist: diameter * 0.09, size: diameter * 0.90, blur: blurR)
        }
        // compositingGroup keeps the blobs blending into EACH OTHER the way
        // the old flattened raster did (normal-over within the group,
        // plusLighter onto the scene). Without it each baked blob would add
        // onto its siblings too and the overlaps would bloom hotter than
        // shipped. A group flatten is a compositor pass, not a filter.
        .compositingGroup()
        .blendMode(.plusLighter)
        .opacity(alpha)
        .scaleEffect(pulse)
    }
}

private struct Blob: View {
    let color: Color
    let angle: Double
    let dist: CGFloat
    let size: CGFloat
    let blur: CGFloat

    var body: some View {
        let dx: CGFloat = CGFloat(cos(angle)) * dist
        let dy: CGFloat = CGFloat(sin(angle)) * dist
        let inner: CGFloat = size * 0.05
        let outer: CGFloat = size * 0.52
        let stops: [Color] = [color.opacity(0.95), color.opacity(0.35), Color.clear]

        return Circle()
            .fill(
                RadialGradient(
                    colors: stops,
                    center: .center,
                    startRadius: inner,
                    endRadius: outer
                )
            )
            .frame(width: size, height: size)
            // Padding gives the blur room inside the raster — a drawingGroup
            // clips at its own bounds, and an unpadded bake would put a hard
            // edge where the glow crosses the frame (the star layers solve
            // the same problem with oversized frames).
            .padding(blur * 2.5)
            .blur(radius: blur)
            .drawingGroup()
            .offset(x: dx, y: dy)
    }
}

// MARK: - The sphere
//
// Matte, near-black, lit only along one edge. It should read as a hole with
// weather on its surface, not as a glossy ball.

private struct SphereLayer: View {
    let radius: CGFloat
    let pulse: CGFloat

    var body: some View {
        let d: CGFloat = radius * 2
        let endR: CGFloat = radius * 1.25
        let shadowR: CGFloat = radius * 0.25
        let stops: [Color] = [Color(hex: 0x0B0F1C), Color(hex: 0x05070E), Color.black]

        // Shadow first, then bake, then scale — the old order scaled first
        // and shadowed after, which recomputed the drop shadow thirty times a
        // second for a 3.5% pulse nobody can see in the shadow itself.
        return Circle()
            .fill(
                RadialGradient(
                    colors: stops,
                    center: UnitPoint(x: 0.40, y: 0.34),
                    startRadius: 1,
                    endRadius: endR
                )
            )
            .frame(width: d, height: d)
            .shadow(color: Color.black.opacity(0.9), radius: shadowR)
            .padding(shadowR * 2.5)
            .drawingGroup()
            .scaleEffect(pulse)
    }
}

private struct RimLayer: View {
    let mood: Theme.Mood
    let diameter: CGFloat
    let radius: CGFloat
    let t: Double
    let flare: Double

    var body: some View {
        let d: CGFloat = radius * 2 + 2
        let lw: CGFloat = max(1.5, diameter * 0.011)
        let m: Color = mood.color
        let stops: [Color] = [Color.clear,
                              m.opacity(0.9),
                              Color.white.opacity(0.75),
                              m.opacity(0.5),
                              Color.clear]

        // The ring is rotationally uniform in shape, so spinning the VIEW is
        // the same picture as spinning the gradient's angle — but the view
        // spin is a compositor transform of a baked raster, where the angle
        // change was a gradient re-render plus a live blur every frame.
        return Circle()
            .strokeBorder(
                AngularGradient(colors: stops, center: .center, angle: .zero),
                lineWidth: lw
            )
            .frame(width: d, height: d)
            .blur(radius: 0.6)
            .padding(3)
            .drawingGroup()
            .rotationEffect(.degrees(t * 14))
            .opacity(flare)
    }
}

// MARK: - Lightning
//
// Fractal midpoint displacement, clipped to the sphere. Each bolt holds for a
// beat then re-rolls, which is what makes it crackle rather than sit there as a
// fixed decal.

private struct LightningLayer: View {
    let mood: Theme.Mood
    let diameter: CGFloat
    let radius: CGFloat
    let t: Double
    let flare: Double

    var body: some View {
        let strike: Int = Int(t * 3.2)
        let phase: Double = t * 3.2 - Double(strike)
        let maskD: CGFloat = radius * 1.94
        let glowW: CGFloat = diameter * 0.020
        let coreW: CGFloat = max(1.0, diameter * 0.006)
        let blurR: CGFloat = diameter * 0.022
        let m: Color = mood.color
        let r: CGFloat = radius
        let f: Double = flare

        return Canvas { ctx, size in
            let c = CGPoint(x: size.width * 0.5, y: size.height * 0.5)

            for i in 0..<3 {
                let seed = UInt64(bitPattern: Int64(strike &* 31 &+ i))
                var rng = SeededRNG(seed: seed)
                let path: Path = makeBolt(center: c, radius: r, rng: &rng)

                // Fade in fast, decay slow — an arc, not a blink.
                let life: Double = 1.0 - pow(phase, 1.6)
                let alpha: Double = life * (0.55 + 0.45 * f)
                if alpha <= 0.02 { continue }

                // The glow pass is a live blur in an offscreen layer — the
                // single most expensive stroke in the app. From `.fair`
                // upward the bolt keeps its bright core and sheds the halo;
                // a slightly drier crackle on a warming machine is the trade.
                if ThermalWatch.shared.level < 1 {
                    ctx.drawLayer { layer in
                        layer.addFilter(.blur(radius: blurR))
                        layer.stroke(
                            path,
                            with: .color(m.opacity(alpha * 0.85)),
                            style: StrokeStyle(lineWidth: glowW, lineCap: .round, lineJoin: .round)
                        )
                    }
                }
                ctx.stroke(
                    path,
                    with: .color(Color.white.opacity(alpha)),
                    style: StrokeStyle(lineWidth: coreW, lineCap: .round, lineJoin: .round)
                )
            }
        }
        .frame(width: diameter, height: diameter)
        .mask(Circle().frame(width: maskD, height: maskD))
        .blendMode(.screen)
    }
}

/// A chord across the sphere, roughened by midpoint displacement, with two
/// branches. Every vertex is clamped inside the silhouette so nothing spikes out
/// of the body.
private func makeBolt(center c: CGPoint, radius r: CGFloat, rng: inout SeededRNG) -> Path {
    let twoPi: Double = 6.283185307179586
    let a0: Double = Double.random(in: 0..<twoPi, using: &rng)
    let a1: Double = a0 + Double.random(in: 1.9...4.4, using: &rng)
    let rr: CGFloat = r * 0.88
    let limit: CGFloat = r * 0.92

    let p0 = CGPoint(x: c.x + CGFloat(cos(a0)) * rr, y: c.y + CGFloat(sin(a0)) * rr)
    let p1 = CGPoint(x: c.x + CGFloat(cos(a1)) * rr, y: c.y + CGFloat(sin(a1)) * rr)

    var pts: [CGPoint] = [p0, p1]
    var offset: CGFloat = r * 0.42

    for _ in 0..<5 {
        var next: [CGPoint] = [pts[0]]
        for i in 0..<(pts.count - 1) {
            let a: CGPoint = pts[i]
            let b: CGPoint = pts[i + 1]
            let mx: CGFloat = (a.x + b.x) * 0.5
            let my: CGFloat = (a.y + b.y) * 0.5
            let dx: CGFloat = b.x - a.x
            let dy: CGFloat = b.y - a.y
            let len: CGFloat = max(0.0001, sqrt(dx * dx + dy * dy))
            let nx: CGFloat = -dy / len
            let ny: CGFloat = dx / len
            let jitter: CGFloat = CGFloat(Double.random(in: -1...1, using: &rng)) * offset

            var px: CGFloat = mx + nx * jitter
            var py: CGFloat = my + ny * jitter
            let vx: CGFloat = px - c.x
            let vy: CGFloat = py - c.y
            let vlen: CGFloat = sqrt(vx * vx + vy * vy)
            if vlen > limit {
                px = c.x + vx / vlen * limit
                py = c.y + vy / vlen * limit
            }
            next.append(CGPoint(x: px, y: py))
            next.append(b)
        }
        pts = next
        offset *= 0.55
    }

    var path = Path()
    path.addLines(pts)

    if pts.count > 8 {
        for _ in 0..<2 {
            let idx: Int = Int.random(in: 3..<(pts.count - 3), using: &rng)
            let root: CGPoint = pts[idx]
            let dir: Double = Double.random(in: 0..<twoPi, using: &rng)
            let seg: CGFloat = r * CGFloat(Double.random(in: 0.16...0.34, using: &rng))

            var tx: CGFloat = root.x + CGFloat(cos(dir)) * seg
            var ty: CGFloat = root.y + CGFloat(sin(dir)) * seg
            let wx: CGFloat = tx - c.x
            let wy: CGFloat = ty - c.y
            let wlen: CGFloat = sqrt(wx * wx + wy * wy)
            if wlen > limit {
                tx = c.x + wx / wlen * limit
                ty = c.y + wy / wlen * limit
            }

            let jx: CGFloat = CGFloat(Double.random(in: -1...1, using: &rng)) * seg * 0.35
            let jy: CGFloat = CGFloat(Double.random(in: -1...1, using: &rng)) * seg * 0.35
            let kink = CGPoint(x: (root.x + tx) * 0.5 + jx, y: (root.y + ty) * 0.5 + jy)

            path.move(to: root)
            path.addLines([root, kink, CGPoint(x: tx, y: ty)])
        }
    }
    return path
}

// MARK: - Armillary cage
//
// Gold bands, not hairlines. Each is an ellipse squashed on the vertical axis
// and rotated — how a tilted circle projects in 2D. Drawn twice: a dim pass
// behind the sphere and a bright pass in front masked to its lower half, so the
// bands read as passing around a solid body.

private struct BandSpec {
    let squash: CGFloat
    let tilt: Double
    let speed: Double
    let width: CGFloat
}

private let cageBands: [BandSpec] = [
    BandSpec(squash: 1.00, tilt:   0, speed:  0.0, width: 1.00),
    BandSpec(squash: 0.30, tilt:  18, speed:  6.5, width: 0.85),
    BandSpec(squash: 0.42, tilt: -34, speed: -4.8, width: 0.95),
    BandSpec(squash: 0.22, tilt:  72, speed:  3.4, width: 0.70),
]

private struct CageLayer: View {
    let diameter: CGFloat
    let radius: CGFloat
    let t: Double
    let flare: Double
    let front: Bool

    private var gold: LinearGradient {
        let stops: [Color] = [Color(hex: 0xFFE9A8), Color(hex: 0xC9942A),
                              Color(hex: 0x6E4E12), Color(hex: 0xFFD470)]
        return LinearGradient(colors: stops, startPoint: .topLeading, endPoint: .bottomTrailing)
    }

    var body: some View {
        let w: CGFloat = radius * 2
        let glowR: CGFloat = front ? diameter * 0.02 : diameter * 0.01
        // ⚠ Constant now, deliberately — it was `0.55 * flare`, which made
        // every band's baked shadow invalid on every frame. 0.47 is the glow
        // at mean breath; the breathing the cage loses here is still carried
        // by the mist, the rim and the pulse, and what it buys is eight
        // shadow filters per frame becoming eight baked textures.
        let glowA: Double = front ? 0.47 : 0.18
        // The far pass is the whole ring seen dimly around the sphere; the near
        // pass is the half that crosses in front of it.
        let layerAlpha: Double = front ? 1.0 : 0.55
        let bands: [BandSpec] = cageBands

        return ZStack {
            ForEach(0..<bands.count, id: \.self) { i in
                CageBand(
                    band: bands[i],
                    width: w,
                    lineWidth: max(1.6, diameter * 0.018 * bands[i].width),
                    rotation: bands[i].tilt + t * bands[i].speed,
                    gold: gold,
                    glowRadius: glowR,
                    glowAlpha: glowA,
                    nearHalfOnly: front
                )
            }
        }
        .frame(width: diameter, height: diameter)
        .opacity(layerAlpha)
    }
}

private struct CageBand: View {
    let band: BandSpec
    let width: CGFloat
    let lineWidth: CGFloat
    let rotation: Double
    let gold: LinearGradient
    let glowRadius: CGFloat
    let glowAlpha: Double
    /// True for the front pass: show only the half of this ring nearest the
    /// viewer, so it reads as crossing in front of the sphere.
    let nearHalfOnly: Bool

    var body: some View {
        let h: CGFloat = width * band.squash
        // Mask in the band's OWN frame, before rotation. The near half of a
        // tilted ring is the lower half of that ring — not the lower half of
        // the screen. Masking after rotation cut every band along the same
        // horizontal line and erased the top of the cage.
        let maskH: CGFloat = h * 0.5 + lineWidth
        let maskY: CGFloat = h * 0.25

        // Glow before rotation, then bake — the glow is omnidirectional, so
        // it is rotation-invariant, and the old order recomputed it per band
        // per frame. The rotation that remains is a transform of the raster.
        return Ellipse()
            .strokeBorder(gold, lineWidth: lineWidth)
            .frame(width: width, height: h)
            .mask(
                Rectangle()
                    .frame(
                        width: width + lineWidth * 2,
                        height: nearHalfOnly ? maskH : h + lineWidth * 2
                    )
                    .offset(y: nearHalfOnly ? maskY : 0)
            )
            .shadow(color: Color(hex: 0xFFD470).opacity(glowAlpha), radius: glowRadius)
            .padding(glowRadius * 2.5)
            .drawingGroup()
            .rotationEffect(.degrees(rotation))
    }
}

// MARK: - Battery arc

private struct BatteryArc: View {
    let mood: Theme.Mood
    let charge: Double
    let diameter: CGFloat
    let flare: Double

    var body: some View {
        let d: CGFloat = diameter * 1.06
        let trim: CGFloat = CGFloat(max(0.01, min(charge, 1.0)))   // floors at 1%, per spec
        let m: Color = mood.color

        return ZStack {
            Circle()
                .stroke(Theme.Color.structure.opacity(0.5), lineWidth: 2)
            Circle()
                .trim(from: 0, to: trim)
                .stroke(m.opacity(0.9), style: StrokeStyle(lineWidth: 2.5, lineCap: .round))
                .rotationEffect(.degrees(-90))
                .shadow(color: m.opacity(0.75 * flare), radius: 6)
        }
        .frame(width: d, height: d)
        .animation(.easeInOut(duration: 0.6), value: charge)
    }
}

#Preview {
    HStack(spacing: 44) {
        ReactorOrb(mood: .neutral, charge: 0.66, diameter: 210)
        ReactorOrb(mood: .happy,   charge: 1.00, diameter: 210)
        ReactorOrb(mood: .worried, charge: 0.20, diameter: 210)
    }
    .padding(70)
    .background(Theme.Color.void)
}
