import SwiftUI
import Combine

/// The dashboard's sky: nebula, three star layers each drifting its own way,
/// and the occasional collision.
///
/// **Why it costs almost nothing.** Each layer is drawn once into a `Canvas`,
/// rasterised by `drawingGroup()`, and then *moved* — the GPU slides a finished
/// texture and the CPU never redraws a star. Collisions are ordinary SwiftUI
/// animations on a few shapes, so they run on the render server too.
///
/// ⚠ **Two things made the first version look frozen, both fixed here.**
/// The drift ran over 100–210 seconds for a couple of dozen points of travel —
/// real motion, far below the threshold of noticing. And Low Power Mode
/// disabled the animation outright, so on battery the sky simply stopped.
/// Low Power now halves the speed instead of killing it; only Reduce Motion
/// brings everything to a stop, which is what that setting is actually for.
public struct SpaceBackdrop: View {

    /// Destination index from the shell. Changing tabs pushes the sky along
    /// its own 25° grain — far layers barely, near layers noticeably. Costs
    /// nothing at rest: it is one offset per layer, animated once per change.
    public var parallax: Double = 0

    public init(parallax: Double = 0) {
        self.parallax = parallax
    }

    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @Environment(\.scenePhase) private var scenePhase
    @State private var drift = false
    @State private var flashes: [StarFlash] = []
    @State private var streaks: [Streak] = []
    @State private var breathe = false
    @State private var spin = false

    private let collisions = Timer.publish(every: 6.5, on: .main, in: .common).autoconnect()
    /// Shooting stars are rarer than collisions on purpose — a streak every few
    /// seconds stops reading as an event and starts reading as weather.
    private let meteors = Timer.publish(every: 26, on: .main, in: .common).autoconnect()

    @ObservedObject private var thermal = ThermalWatch.shared

    private var lowPower: Bool { ProcessInfo.processInfo.isLowPowerModeEnabled }

    /// ⚠ The 2026-08-19 heat finding. The sky is six to ten window-sized
    /// layers composited every frame — cheap per frame and never zero, and
    /// until this date it ran at full behind other windows and on a hot
    /// chassis. The orb and the fight both park on `scenePhase`; the biggest
    /// continuous consumer in the app did not. On a fanless laptop that is a
    /// steady drain all day while the app sits behind other windows — exactly
    /// the "hot after ten minutes" report.
    ///
    /// So the sky now runs only while the app is front and the chassis is
    /// under `.serious`. Freezing is done by `sky.id(active)` — teardown, not
    /// `.animation(nil)` — because a `repeatForever` already in flight keeps
    /// running when its modifier's animation later turns nil; only identity
    /// death actually stops it. The restart on refocus begins from base
    /// offsets: a one-frame jump in a random starfield, at the exact moment
    /// the whole chrome is changing anyway.
    private var active: Bool { scenePhase == .active && thermal.level < 2 }
    private var moves: Bool { !reduceMotion && active }
    /// On battery-saver everything takes twice as long. Slower, never stopped.
    /// (Thermal pressure is handled by `active` above — a slowed animation
    /// composites just as many frames, so slowing was never a watt saving.)
    private var pace: Double { lowPower ? 2.0 : 1.0 }

    /// tan(25°). Every parallax nudge travels the same axis the stars drift on,
    /// so switching destinations pushes the sky *along* its own grain rather
    /// than across it.
    private static let axisSlope: Double = 0.466

    private func nudge(_ depth: Double) -> CGSize {
        CGSize(width: parallax * depth, height: -parallax * depth * Self.axisSlope)
    }

    public var body: some View {
        GeometryReader { geo in
            ZStack {
                nebula(geo.size).offset(nudge(2))
                // The plane dollies too, but barely — it is the furthest
                // thing in the sky and should look almost fixed.
                Dolly(period: 130, maxScale: 1.35, moves: moves) {
                    galacticPlane(geo.size)
                }
                .offset(nudge(3))
                galaxies(geo.size).offset(nudge(5))

                // Far: more of them, blurred, cooled. Depth-of-field is baked
                // into the drawingGroup, so it costs one blur at launch and
                // nothing per frame — a live blur here would be the single
                // most expensive thing in the app.
                // Far, slowest dolly. Depth is speed here: the far field
                // expands over 78 seconds, the near field over 40.
                Dolly(period: 78, maxScale: 1.75, moves: moves) {
                    starLayer(geo.size, count: 300, seed: 0x5EED_1111,
                              radius: 0.35...0.85, opacity: 0.30...0.65,
                              dx: 97, dy: -45, duration: 68,
                              blurRadius: 0.6, cool: true)
                }
                .offset(nudge(4))

                Dolly(period: 56, maxScale: 1.9, moves: moves) {
                    starLayer(geo.size, count: 200, seed: 0x5EED_2222,
                              radius: 0.55...1.15, opacity: 0.35...0.80,
                              dx: -127, dy: 59, duration: 52)
                }
                .offset(nudge(8))

                Dolly(period: 46, maxScale: 2.0, moves: moves) {
                    clusters(geo.size)
                }
                .offset(nudge(11))

                // Near, fastest — a star at the frame edge crosses roughly
                // 26 pt/sec at this rate, which is squarely in the band a
                // starfield reads as travel rather than as drift.
                Dolly(period: 40, maxScale: 2.15, moves: moves) {
                    starLayer(geo.size, count: 100, seed: 0x5EED_3333,
                              radius: 0.90...1.90, opacity: 0.50...0.95,
                              dx: 154, dy: -72, duration: 41,
                              warm: true)
                }
                .offset(nudge(13))

                twinkle(geo.size).offset(nudge(14))

                ForEach(streaks) { streak in
                    ShootingStar(streak: streak, canvas: geo.size)
                }
                ForEach(flashes) { flash in
                    StarCollision(flash: flash, canvas: geo.size)
                }
            }
            .animation(.easeOut(duration: 0.42), value: parallax)
            .onAppear {
                guard moves else { return }
                drift = true
                breathe = true
                spin = true
            }
            // ⚠ Everything above must stay INSIDE the `.id(active)` boundary
            // below — identity death is what stops in-flight repeatForevers,
            // and this onAppear is what restarts them on refocus.
            .onReceive(collisions) { _ in
                guard moves else { return }
                let flash = StarFlash(x: .random(in: 0.08...0.92),
                                      y: .random(in: 0.08...0.92),
                                      tilt: .random(in: -0.5...0.5))
                flashes.append(flash)
                DispatchQueue.main.asyncAfter(deadline: .now() + 1.6) {
                    flashes.removeAll { $0.id == flash.id }
                }
            }
            .onReceive(meteors) { _ in
                guard moves else { return }
                let streak = Streak(x: .random(in: -0.05...0.55),
                                    y: .random(in: 0.25...0.95))
                streaks.append(streak)
                DispatchQueue.main.asyncAfter(deadline: .now() + 1.8) {
                    streaks.removeAll { $0.id == streak.id }
                }
            }
            // The freeze switch (2026-08-19). Behind another window or on a
            // hot chassis the whole animated subtree is torn down and rebuilt
            // static; on refocus it rebuilds animated, from onAppear.
            .id(active)
        }
    }

    // MARK: - Nebula

    private func nebula(_ size: CGSize) -> some View {
        ZStack {
            wash(color: Color(hex: 0x4632A0), at: UnitPoint(x: 0.22, y: 0.30), scale: 0.62, in: size)
            wash(color: Color(hex: 0x145A96), at: UnitPoint(x: 0.78, y: 0.66), scale: 0.70, in: size)
            wash(color: Color(hex: 0x8C3C96), at: UnitPoint(x: 0.55, y: 0.16), scale: 0.46, in: size)
            wash(color: Theme.Color.primary, at: UnitPoint(x: 0.14, y: 0.86), scale: 0.40, in: size)
            // Blooms — smaller, dimmer, irregular. Structure without objects.
            wash(color: Color(hex: 0x2E5FB4), at: UnitPoint(x: 0.38, y: 0.52), scale: 0.26, in: size)
            wash(color: Color(hex: 0x6B3FA8), at: UnitPoint(x: 0.88, y: 0.22), scale: 0.22, in: size)
            wash(color: Color(hex: 0x1E7C8C), at: UnitPoint(x: 0.66, y: 0.90), scale: 0.24, in: size)
            wash(color: Color(hex: 0x53307F), at: UnitPoint(x: 0.06, y: 0.44), scale: 0.20, in: size)
        }
        .blur(radius: 34)
        // Breath: one opacity value over ninety seconds. Invisible frame to
        // frame; the sky is never quite the same twice across a minute.
        .opacity(breathe ? 0.39 : 0.30)
        .animation(moves ? .easeInOut(duration: 90 * pace).repeatForever(autoreverses: true) : nil,
                   value: breathe)
        .scaleEffect(drift ? 1.07 : 1.0)
        .offset(x: drift ? 26 : -26, y: drift ? -16 : 16)
        .animation(moves ? .easeInOut(duration: 38 * pace).repeatForever(autoreverses: true) : nil,
                   value: drift)
    }

    private func wash(color: Color, at point: UnitPoint,
                      scale: CGFloat, in size: CGSize) -> some View {
        RadialGradient(colors: [color.opacity(0.85), .clear],
                       center: point, startRadius: 0,
                       endRadius: max(size.width, size.height) * scale)
    }

    // MARK: - Galactic plane

    /// A dense, dim band on the 25° axis with dust lanes cut through it.
    ///
    /// The biggest single change to the sky and the cheapest: one Canvas drawn
    /// once, rotated by a GPU transform. It is what turns a scatter of stars
    /// into a sky that has a direction.
    private func galacticPlane(_ size: CGSize) -> some View {
        let w = size.width * 1.7
        let h = size.height * 1.7
        return Canvas { ctx, canvasSize in
            var rng = StarRNG(seed: 0x9A11_ACC7)
            let mid = canvasSize.height / 2
            let spread = canvasSize.height * 0.085

            for _ in 0..<1400 {
                let x = Double.random(in: 0...1, using: &rng) * canvasSize.width
                // Sum of three uniforms ≈ gaussian. Dense at the spine, thin
                // at the edges, no hard boundary anywhere.
                let g = (Double.random(in: 0...1, using: &rng)
                       + Double.random(in: 0...1, using: &rng)
                       + Double.random(in: 0...1, using: &rng)) / 3 - 0.5
                let y = mid + g * spread * 4
                let r = 0.28 + Double.random(in: 0...1, using: &rng) * 0.62
                let fade = max(0, 1 - abs(g) * 2.4)
                let o = (0.10 + Double.random(in: 0...1, using: &rng) * 0.38) * fade
                ctx.fill(Path(ellipseIn: CGRect(x: x - r, y: y - r, width: r * 2, height: r * 2)),
                         with: .color(Color(hex: 0xDCE8FF).opacity(o)))
            }

            // Dust lanes: voids, drawn in the base colour over the band.
            for _ in 0..<7 {
                let x = Double.random(in: 0...1, using: &rng) * canvasSize.width
                let lw = 90 + Double.random(in: 0...1, using: &rng) * 260
                let lh = 5 + Double.random(in: 0...1, using: &rng) * 13
                let dy = (Double.random(in: 0...1, using: &rng) - 0.5) * spread * 2.4
                ctx.fill(Path(ellipseIn: CGRect(x: x, y: mid + dy, width: lw, height: lh)),
                         with: .color(Theme.Color.void.opacity(0.55)))
            }
        }
        .frame(width: w, height: h)
        .blur(radius: 0.4)
        .drawingGroup()
        .rotationEffect(.degrees(-25))
        .offset(x: drift ? 34 : -34, y: drift ? -16 : 16)
        .animation(moves ? .linear(duration: 96 * pace).repeatForever(autoreverses: true) : nil,
                   value: drift)
    }

    // MARK: - Galaxies

    private func galaxies(_ size: CGSize) -> some View {
        ZStack {
            galaxy(scale: 17, seed: 0x6A1A_0001, tint: Color(hex: 0xBECDFF), period: 420)
                .position(x: size.width * 0.74, y: size.height * 0.28)
            galaxy(scale: 9, seed: 0x6A1A_0002, tint: Color(hex: 0xA8C8FF), period: 610)
                .position(x: size.width * 0.19, y: size.height * 0.74)
        }
    }

    /// Two logarithmic arms plus a core bloom, rasterised once and then spun by
    /// a GPU transform — one revolution every seven to ten minutes, which is
    /// imperceptible in a glance and unmistakable across a session.
    private func galaxy(scale: Double, seed: UInt64, tint: Color, period: Double) -> some View {
        let box = scale * 8
        return Canvas { ctx, canvasSize in
            var rng = StarRNG(seed: seed)
            let cx = canvasSize.width / 2
            let cy = canvasSize.height / 2

            for arm in 0..<2 {
                for i in 0..<620 {
                    let t = Double(i) / 620 * 3.4
                    let r = scale * exp(0.26 * t)
                    let a = t + Double(arm) * .pi
                    let jx = (Double.random(in: 0...1, using: &rng) - 0.5) * r * 0.30
                    let jy = (Double.random(in: 0...1, using: &rng) - 0.5) * r * 0.30
                    let px = cx + cos(a) * r + jx
                    let py = cy + sin(a) * r * 0.42 + jy
                    let o = max(0, 0.52 - t * 0.13)
                    let rad = 0.32 + Double.random(in: 0...1, using: &rng) * 0.5
                    ctx.fill(Path(ellipseIn: CGRect(x: px - rad, y: py - rad,
                                                    width: rad * 2, height: rad * 2)),
                             with: .color(tint.opacity(o)))
                }
            }

            ctx.fill(Path(ellipseIn: CGRect(x: cx - scale * 2.6, y: cy - scale * 1.2,
                                            width: scale * 5.2, height: scale * 2.4)),
                     with: .radialGradient(
                        Gradient(colors: [tint.opacity(0.42), tint.opacity(0)]),
                        center: CGPoint(x: cx, y: cy),
                        startRadius: 0, endRadius: scale * 2.6))
        }
        .frame(width: box, height: box)
        .drawingGroup()
        .rotationEffect(.degrees(spin ? 360 : 0))
        .animation(moves ? .linear(duration: period * pace).repeatForever(autoreverses: false) : nil,
                   value: spin)
    }

    // MARK: - Clusters

    /// Three knots of stars. No new drawing technique — the same dots at a
    /// different distribution, which is why this was the cheapest option on
    /// the board and still reads as depth.
    private func clusters(_ size: CGSize) -> some View {
        Canvas { ctx, canvasSize in
            var rng = StarRNG(seed: 0xC1F5_7E12)
            let knots: [(Double, Double, Int)] = [(0.76, 0.34, 90), (0.24, 0.62, 70), (0.52, 0.86, 60)]
            for (fx, fy, n) in knots {
                let cx = fx * canvasSize.width
                let cy = fy * canvasSize.height
                for _ in 0..<n {
                    let a = Double.random(in: 0...1, using: &rng) * 2 * .pi
                    let g = abs(Double.random(in: 0...1, using: &rng)
                              + Double.random(in: 0...1, using: &rng)
                              + Double.random(in: 0...1, using: &rng) - 1.5)
                    let d = g * 46
                    let px = cx + cos(a) * d
                    let py = cy + sin(a) * d * 0.8
                    let o = max(0.14, 0.95 - d / 56)
                    let r = 0.32 + Double.random(in: 0...1, using: &rng) * 0.7
                    ctx.fill(Path(ellipseIn: CGRect(x: px - r, y: py - r, width: r * 2, height: r * 2)),
                             with: .color(Color(hex: 0xEBF5FF).opacity(o)))
                }
            }
        }
        .drawingGroup()
        .offset(x: drift ? 62 : -62, y: drift ? -29 : 29)
        .animation(moves ? .linear(duration: 47 * pace).repeatForever(autoreverses: true) : nil,
                   value: drift)
    }

    // MARK: - Twinkle

    private struct Twinkler: Identifiable {
        let id: Int
        let x: Double
        let y: Double
        let size: Double
        let period: Double
    }

    /// Thirty real views over the baked Canvas.
    ///
    /// ⚠ **Canvas stars physically cannot twinkle** — they are one rasterised
    /// texture, and animating any value inside it forces a full redraw. These
    /// thirty are ordinary SwiftUI circles, so the render server fades them and
    /// the CPU never wakes. Thirty views is nothing; three hundred would not be.
    private static let twinklers: [Twinkler] = {
        var rng = StarRNG(seed: 0x7B1D_C1E5)
        return (0..<30).map { i in
            Twinkler(id: i,
                     x: Double.random(in: 0.02...0.98, using: &rng),
                     y: Double.random(in: 0.02...0.98, using: &rng),
                     size: Double.random(in: 1.3...2.6, using: &rng),
                     period: Double.random(in: 2.4...6.2, using: &rng))
        }
    }()

    // MARK: - Star layers

    /// One rasterised depth, sliding along its own heading.
    ///
    /// The travel autoreverses rather than looping: a one-way translate has to
    /// snap back at the end and the snap is visible, where a reversal spread
    /// over a minute is not.
    ///
    /// ⚠ **`blur` sits before `drawingGroup`, deliberately.** In that order the
    /// blur is baked into the texture once; after it, the GPU would re-blur a
    /// moving layer every frame — which is the single most expensive thing this
    /// app could do to itself.
    private func starLayer(_ size: CGSize, count: Int, seed: UInt64,
                           radius: ClosedRange<Double>,
                           opacity: ClosedRange<Double>,
                           dx: CGFloat, dy: CGFloat, duration: Double,
                           blurRadius: CGFloat = 0,
                           cool: Bool = false,
                           warm: Bool = false) -> some View {
        let padX = abs(dx) + 24
        let padY = abs(dy) + 24

        return Canvas { ctx, canvasSize in
            var rng = StarRNG(seed: seed)
            for _ in 0..<count {
                let x = Double.random(in: 0...1, using: &rng) * Double(canvasSize.width)
                let y = Double.random(in: 0...1, using: &rng) * Double(canvasSize.height)
                let r = Double.random(in: radius, using: &rng)
                let o = Double.random(in: opacity, using: &rng)
                let t = Double.random(in: 0...1, using: &rng)

                // Colour temperature by depth: the far field runs cool and
                // slightly blue, the near field keeps its warm outliers. Free —
                // it is a different constant in a loop that already runs.
                let color: Color
                if cool {
                    color = t > 0.88 ? Theme.Color.primary : Color(hex: 0xC6D8FF)
                } else if warm {
                    color = t > 0.90 ? Color(hex: 0xFFD9C0)
                          : (t > 0.84 ? Theme.Color.primary : .white)
                } else {
                    color = t > 0.93 ? Theme.Color.primary
                          : (t > 0.87 ? Color(hex: 0xFFD9C0) : .white)
                }

                ctx.fill(Path(ellipseIn: CGRect(x: x - r, y: y - r,
                                                width: r * 2, height: r * 2)),
                         with: .color(color.opacity(o)))
            }
        }
        // Oversized and re-centred, so the travel never drags an edge into view.
        .frame(width: size.width + padX * 2, height: size.height + padY * 2)
        .offset(x: -padX, y: -padY)
        .blur(radius: blurRadius)
        .drawingGroup()
        .offset(x: drift ? dx / 2 : -dx / 2, y: drift ? dy / 2 : -dy / 2)
        .animation(moves ? .linear(duration: duration * pace).repeatForever(autoreverses: true) : nil,
                   value: drift)
    }

    private func twinkle(_ size: CGSize) -> some View {
        ZStack {
            ForEach(Self.twinklers) { t in
                let dot = Circle()
                    .fill(Color.white)
                    .frame(width: t.size, height: t.size)
                    .shadow(color: Theme.Color.primary.opacity(0.5), radius: 2)
                    .position(x: t.x * size.width, y: t.y * size.height)
                // Thirty breathing opacities is thirty animations keeping the
                // compositor awake — while the sky is frozen they hold still
                // at a fixed mid-brightness instead (gated here because
                // `breathing()` itself only knows about Reduce Motion).
                if moves {
                    dot.breathing(low: 0.14, high: 0.92, period: t.period)
                } else {
                    dot.opacity(0.55)
                }
            }
        }
        .allowsHitTesting(false)
    }
}

/// One shooting star, travelling the 25° axis like everything else.
struct Streak: Identifiable, Equatable {
    let id = UUID()
    let x: Double
    let y: Double
}

private struct ShootingStar: View {
    let streak: Streak
    let canvas: CGSize

    @State private var go = false

    var body: some View {
        Capsule()
            .fill(LinearGradient(colors: [.clear, .white.opacity(0.9)],
                                 startPoint: .leading, endPoint: .trailing))
            .frame(width: 116, height: 1.5)
            .rotationEffect(.degrees(-25))
            .shadow(color: .white.opacity(0.55), radius: 3)
            .position(x: (streak.x + (go ? 0.42 : 0)) * canvas.width,
                      y: (streak.y - (go ? 0.196 : 0)) * canvas.height)
            .opacity(go ? 0 : 0.95)
            .onAppear {
                withAnimation(.easeIn(duration: 1.25)) { go = true }
            }
    }
}

/// One scheduled collision. Position is normalised so it survives a resize.
struct StarFlash: Identifiable, Equatable {
    let id = UUID()
    let x: Double
    let y: Double
    let tilt: Double
}

/// Two stars meeting: a white core, an expanding shock ring, and four struck
/// sparks. Pure SwiftUI animation — no timeline, no per-frame work.
private struct StarCollision: View {
    let flash: StarFlash
    let canvas: CGSize

    @State private var go = false

    var body: some View {
        ZStack {
            Circle()
                .stroke(Color.white.opacity(go ? 0 : 0.9), lineWidth: go ? 0.5 : 2.2)
                .frame(width: go ? 78 : 3, height: go ? 78 : 3)

            Circle()
                .stroke(Theme.Color.primary.opacity(go ? 0 : 0.7), lineWidth: go ? 0.5 : 1.6)
                .frame(width: go ? 44 : 2, height: go ? 44 : 2)

            Circle()
                .fill(RadialGradient(colors: [.white, Theme.Color.earned.opacity(0.6), .clear],
                                     center: .center, startRadius: 0, endRadius: 14))
                .frame(width: go ? 30 : 4, height: go ? 30 : 4)
                .opacity(go ? 0 : 1)

            ForEach(0..<4, id: \.self) { i in
                Capsule()
                    .fill(Color.white.opacity(go ? 0 : 0.85))
                    .frame(width: go ? 13 : 2, height: 1.4)
                    .offset(x: go ? 30 : 0)
                    .rotationEffect(.radians(Double(i) * .pi / 2 + flash.tilt))
            }
        }
        .position(x: flash.x * canvas.width, y: flash.y * canvas.height)
        .onAppear {
            withAnimation(.easeOut(duration: 1.15)) { go = true }
        }
    }
}

/// Deterministic star placement.
///
/// `Double.random(in:)` on its own would reshuffle the entire sky on every
/// redraw — a resize would rearrange the stars. Seeding fixes each layer in
/// place for the life of the app.
///
/// ⚠ Named `StarRNG`, not `SeededRNG`: `ReactorOrb.swift` already declares a
/// type by that name, and two at file scope collide. `private` keeps this one
/// out of everyone else's lookup for good.
private struct StarRNG: RandomNumberGenerator {
    private var state: UInt64

    init(seed: UInt64) {
        state = seed &* 6_364_136_223_846_793_005 &+ 1_442_695_040_888_963_407
    }

    mutating func next() -> UInt64 {
        state = state &* 6_364_136_223_846_793_005 &+ 1_442_695_040_888_963_407
        var z = state
        z = (z ^ (z >> 30)) &* 0xBF58_476D_1CE4_E5B9
        z = (z ^ (z >> 27)) &* 0x94D0_49BB_1331_11EB
        return z ^ (z >> 31)
    }
}

/// Forward flight, not a pan.
///
/// **Measured from `Design/References/Universebackground.mp4` on 2026-08-18.**
/// That clip has **zero translation** between frames — it dollies forward at
/// **+1.00% scale per second**, expanding radially from centre. Every previous
/// version of this sky slid sideways at 1.6–4.2 px/s and reversed after 7–12%
/// of the screen, which is why it was reported as not moving at all.
/// That report was right, and the fix was never "slide faster":
///
/// - A uniform sideways slide of a random dot field is nearly invisible. Every
///   star looks the same, so there is no reference frame and nothing registers.
/// - **Radial expansion is unmistakable.** Stars separate from each other and
///   accelerate toward the edges, which reads as depth and forward motion
///   instantly — at the centre almost nothing moves, exactly as in the clip.
///
/// **How the loop hides.** One copy scaling 1→2 forever has to snap back, and
/// the snap is glaring. So two copies run half a period apart, and opacity
/// breathes on a **half-period autoreverse** — which puts each copy at zero
/// opacity precisely when its scale resets. The reset happens while invisible.
/// Two standard animations per copy, both compositor transforms on an already
/// rasterised texture. No `Canvas` is ever redrawn.
private struct Dolly<Content: View>: View {
    var period: Double
    var maxScale: Double
    var moves: Bool
    @ViewBuilder var content: Content

    var body: some View {
        if moves {
            ZStack {
                DollyPhase(period: period, maxScale: maxScale, delay: 0) { content }
                DollyPhase(period: period, maxScale: maxScale, delay: period / 2) { content }
            }
        } else {
            // Reduce Motion: one copy, still, fully visible. Rendering both
            // would double every star.
            content
        }
    }
}

private struct DollyPhase<Content: View>: View {
    var period: Double
    var maxScale: Double
    var delay: Double
    @ViewBuilder var content: Content

    @State private var zoom = false
    @State private var fade = false

    var body: some View {
        content
            .scaleEffect(zoom ? maxScale : 1.0)
            .opacity(fade ? 1.0 : 0.0)
            .onAppear {
                withAnimation(.linear(duration: period)
                    .repeatForever(autoreverses: false).delay(delay)) {
                    zoom = true
                }
                withAnimation(.easeInOut(duration: period / 2)
                    .repeatForever(autoreverses: true).delay(delay)) {
                    fade = true
                }
            }
    }
}
