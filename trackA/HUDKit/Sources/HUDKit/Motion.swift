import SwiftUI

/// The shared motion vocabulary — `Design/MOTION-OVERHAUL.md` §3, standard
/// tone. First build slice 2026-08-19 (the owner's pick: demos 1, 2, 3,
/// 5-standard, 6).
///
/// One author for every timing, so the app moves as one instrument. Views ask
/// for a plan and apply it on the compositor — opacity, offset, scale, trim.
/// The Canvas surfaces (sky, orb, fight) never read these; their budgets are
/// governed separately (`ThermalWatch`, CONTRACTS §12).
///
/// 2026-08-20: menu item J landed, so the flash ledger below is no longer
/// scaffolding — `ImpactFlash` asks it before every reserved impact frame.
public enum Motion {

    // MARK: Cascade

    /// Delay between siblings arriving, and the cap that keeps a long list
    /// from stretching its entrance past the point of patience — past the cap
    /// the step compresses rather than the entrance growing.
    public static let step: Double = 0.024
    public static let cascadeCap: Double = 0.32

    /// Panels stagger wider than rows — a panel is a bigger thought.
    public static let panelStep: Double = 0.05

    public static func cascadeDelay(_ order: Int, base: Double = 0, step: Double = Motion.step) -> Double {
        base + min(cascadeCap, Double(max(0, order)) * step)
    }

    // MARK: Curves — FAOF's beats live in the springs

    /// Entrances. The spring supplies the overshoot (third beat), so nobody
    /// hand-types a fourth keyframe anywhere in the app.
    public static let enter: Animation = .spring(response: 0.32, dampingFraction: 0.74)
    /// Exits are cheaper than entrances on purpose — the game-UI rule:
    /// `animateOut` is quick, `animateIn` carries the character.
    public static let exit: Animation = .easeIn(duration: 0.11)
    /// Value changes — numeral rolls, dot pops, arc moves.
    public static let event: Animation = .spring(response: 0.34, dampingFraction: 0.72)
    /// Hover and other micro-life. Matches the 0.14s already shipped.
    public static let micro: Animation = .easeOut(duration: 0.14)

    // MARK: The grain

    /// The 25° axis the sky drifts on. Entrances arrive along it and exits
    /// leave along it, so content finally moves *with* the parallax nudge
    /// `SpaceBackdrop` has been making alone since 08-18.
    public static let grainIn = CGSize(width: 26, height: -12)
    public static let grainOut = CGSize(width: -30, height: 14)

    // MARK: The tone dial (§3.2)

    /// Three renderings of the same event, from clip 2's editing rules.
    ///
    /// - `deliberate` — no overshoot. It arrives and stops. For acts that
    ///   undo or refuse: Undo today, permission failures, corrupt-store notices.
    /// - `standard` — the full four beats. Mouse-driven motion.
    /// - `fast` — antic dropped, the travel replaced by a smear. Keyboard-driven
    ///   motion: ⌘K and ⌘1–⌘8. An instrument answers the hand (H7); it does not
    ///   perform for it.
    public enum Tone {
        case deliberate, standard, fast
    }

    /// The destination-change transition (Design/MOTION-OVERHAUL.md §4.2):
    /// arrive along the grain with spring overshoot, leave fast and low.
    public static var destination: AnyTransition {
        .asymmetric(
            insertion: .offset(x: grainIn.width, y: grainIn.height)
                .combined(with: .opacity)
                .animation(enter),
            removal: .offset(x: grainOut.width, y: grainOut.height)
                .combined(with: .opacity)
                .animation(exit)
        )
    }

    /// The same change, rendered in one of the three tones.
    ///
    /// ⚠ Kept as a function beside the `destination` property rather than
    /// replacing it — `Motion.destination` is the standard tone and is already
    /// referenced from `RootView`. One name, two spellings, would be the kind
    /// of ambiguity this file exists to prevent.
    public static func destinationTransition(_ tone: Tone) -> AnyTransition {
        switch tone {
        case .standard:
            return destination

        // Keyboard. The smear replaces the travel: the panel stretches along
        // the grain as it goes and is gone before the eye resolves it, which
        // is the whole trick — a thing that moves A to B with no in-between
        // reads as teleporting, and 60ms of stretch is the in-between.
        case .fast:
            return .asymmetric(
                insertion: .modifier(active: Smear(amount: 1, travel: grainIn),
                                     identity: Smear(amount: 0, travel: grainIn))
                    .animation(.easeOut(duration: 0.17)),
                removal: .modifier(active: Smear(amount: 1, travel: grainOut),
                                   identity: Smear(amount: 0, travel: grainOut))
                    .animation(.easeIn(duration: 0.085)))

        // No overshoot, no grain travel. A reversal should not feel eager.
        case .deliberate:
            return .asymmetric(
                insertion: .opacity.animation(.easeOut(duration: 0.20)),
                removal: .opacity.animation(.easeIn(duration: 0.12)))
        }
    }
}

// MARK: - Smear

/// A stretched, fading copy of an element along its travel axis — the fight's
/// own trick (silhouettes at t−0.028/−0.058/−0.092) applied to rectangles.
///
/// The stretch runs along the sky's 25° grain, not along x, so it is built as
/// rotate-into-the-axis → scale → rotate back. The two rotations cancel, so the
/// content lands upright; only the scale happened in the tilted frame. All
/// three are compositor transforms, which is the point — nothing here asks a
/// Canvas to redraw.
public struct Smear: ViewModifier, Animatable {
    /// 0 at rest, 1 fully smeared away.
    public var amount: Double
    public var travel: CGSize

    public init(amount: Double, travel: CGSize) {
        self.amount = amount
        self.travel = travel
    }

    public var animatableData: Double {
        get { amount }
        set { amount = newValue }
    }

    // ⚠ Two constants rather than one and a unary minus. `Angle` conforms to
    // `AdditiveArithmetic`, which gives it binary `-` but not the prefix form,
    // so `-Self.grain` does not compile.
    private static let intoGrain = Angle(degrees: -25)
    private static let outOfGrain = Angle(degrees: 25)

    public func body(content: Content) -> some View {
        content
            .rotationEffect(Self.intoGrain)
            .scaleEffect(x: 1 + amount * 0.16, y: 1 - amount * 0.05, anchor: .center)
            .rotationEffect(Self.outOfGrain)
            .offset(x: travel.width * amount, y: travel.height * amount)
            .opacity(1 - amount)
    }
}

// MARK: - Cascade-in

/// Staggered arrival for one member of a collection: opacity plus a short
/// travel along the grain, overshoot from the spring, `order` steps of delay.
///
/// Fires on `onAppear`, which is exactly once per arrival — destination
/// changes recreate the tree (`.id(destination)` in RootView), so every visit
/// replays the entrance and an in-place data refresh replays nothing.
public struct CascadeIn: ViewModifier {
    public var order: Int
    public var base: Double = 0
    public var step: Double = Motion.step
    /// `false` renders the row at rest with no entrance at all.
    ///
    /// ⚠ This exists for the ⌘K list and matters more than it looks. Rows there
    /// are created and destroyed on every keystroke as the filter changes, and
    /// `onAppear` fires for each new one — so without this the list re-deals
    /// itself letter by letter. Typing should feel like carving away, not like
    /// being handed a fresh hand of cards each time (§4.8).
    public var active: Bool = true

    public init(order: Int, base: Double = 0, step: Double = Motion.step, active: Bool = true) {
        self.order = order
        self.base = base
        self.step = step
        self.active = active
    }

    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @State private var shown = false

    private var visible: Bool { shown || reduceMotion || !active }

    public func body(content: Content) -> some View {
        content
            .opacity(visible ? 1 : 0)
            .offset(x: visible ? 0 : 14, y: visible ? 0 : -6)
            .onAppear {
                guard active, !reduceMotion, !shown else { return }
                withAnimation(Motion.enter.delay(
                    Motion.cascadeDelay(order, base: base, step: step))) {
                    shown = true
                }
            }
    }
}

public extension View {
    /// Rows: `.cascadeIn(i)`. Panels: `.cascadeIn(n, step: Motion.panelStep)`.
    func cascadeIn(_ order: Int, base: Double = 0, step: Double = Motion.step,
                   active: Bool = true) -> some View {
        modifier(CascadeIn(order: order, base: base, step: step, active: active))
    }
}

// MARK: - One-shot flare ring

/// A single expanding ring, fired by bumping `trigger` — the orb's
/// acknowledgement that a session just landed (§3.4: secondary action, one
/// step, never a chain). Same one-shot pattern as `StarCollision`: the view
/// exists only for the life of the animation, so idle cost is zero.
public struct FlareRing: View {
    public var trigger: Int
    public var tint: Color

    public init(trigger: Int, tint: Color) {
        self.trigger = trigger
        self.tint = tint
    }

    public var body: some View {
        ZStack {
            if trigger > 0 {
                FlareRingShot(tint: tint).id(trigger)
            }
        }
        .allowsHitTesting(false)
    }
}

private struct FlareRingShot: View {
    let tint: Color
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @State private var go = false

    var body: some View {
        Circle()
            .stroke(tint.opacity(go ? 0 : 0.75), lineWidth: go ? 1 : 3)
            .frame(width: go ? 214 : 122, height: go ? 214 : 122)
            .onAppear {
                guard !reduceMotion else { return }
                withAnimation(.easeOut(duration: 0.55)) { go = true }
            }
            .opacity(reduceMotion ? 0 : 1)
    }
}

// MARK: - The flash ledger (menu J, §3.3)

/// One counter for every reserved impact frame in the app, so the WCAG 2.2
/// SC 2.3.1 arithmetic stays app-wide rather than per-surface. The criterion
/// is the fight's own (CONTRACTS §12.1): a flash is a luminance rise counted
/// at threshold 0.80 with 0.12s merges, ceiling 3/s, house budget 2.
///
/// The fight already spends up to two inside its worst one-second window, so
/// while a bout is live every other impact is downgraded to its glow-only
/// rendering — no white frame, no ink dip, just the tinted decay. Between
/// bouts, grants are spaced a full second apart, which keeps any two chrome
/// impacts out of the same counting window by construction.
///
/// Main-thread only — every caller is a view event or an `onAppear`, which is
/// what the `nonisolated(unsafe)` asserts. Same discipline as `scriptCache`.
public enum FlashLedger {
    nonisolated(unsafe) public static var lastGrant: TimeInterval = -1_000
    /// Written by `StickFight`'s loop: true while a bout is running. The rest
    /// windows inside a bout are not distinguished — a conservative reading
    /// that costs a few downgrades a day and can never overspend the budget.
    nonisolated(unsafe) public static var fightLive = false

    public enum Grade { case full, glow }

    public static func request() -> Grade {
        let now = ProcessInfo.processInfo.systemUptime
        if fightLive || now - lastGrant < 1.0 { return .glow }
        lastGrant = now
        return .full
    }
}

/// The reserved impact frame (§3.3, clips 6 + 23): normal → one washed-white
/// frame → one ink-dip frame → a two-tone glow decay in the event's colour.
/// Fired by bumping `trigger`, exactly like `FlareRing` — the view exists only
/// for the life of the shot, so idle cost is zero.
///
/// Reduce Motion never flashes: the RM rendering is the glow decay alone,
/// which is a fade, not a luminance spike. The ledger is still consulted so
/// the accounting stays truthful either way.
public struct ImpactFlash: View {
    public var trigger: Int
    public var tint: Color

    public init(trigger: Int, tint: Color) {
        self.trigger = trigger
        self.tint = tint
    }

    public var body: some View {
        ZStack {
            if trigger > 0 {
                ImpactFlashShot(tint: tint).id(trigger)
            }
        }
        .allowsHitTesting(false)
    }
}

private struct ImpactFlashShot: View {
    let tint: Color
    @Environment(\.accessibilityReduceMotion) private var reduceMotion

    private enum Phase { case idle, white, ink, glow, done }
    @State private var phase: Phase = .idle

    var body: some View {
        ZStack {
            switch phase {
            case .white:
                Rectangle().fill(.white.opacity(0.42))
            case .ink:
                Rectangle().fill(Color(hex: 0x0A0E16).opacity(0.60))
            case .glow, .idle:
                // The anime-glow pair: a dark warm under-wash and a brighter
                // core stroke, decaying together. Two tones, no white.
                Rectangle()
                    .fill(tint.opacity(phase == .glow ? 0.16 : 0))
                    .overlay(
                        Rectangle().stroke(tint.opacity(phase == .glow ? 0.9 : 0),
                                           lineWidth: 2)
                    )
            case .done:
                EmptyView()
            }
        }
        .animation(phase == .glow ? .easeOut(duration: 0.34) : nil, value: phase == .done)
        .task {
            let grade = FlashLedger.request()
            if grade == .full && !reduceMotion {
                phase = .white
                try? await Task.sleep(for: .milliseconds(50))
                phase = .ink
                try? await Task.sleep(for: .milliseconds(50))
            }
            phase = .glow
            try? await Task.sleep(for: .milliseconds(30))
            withAnimation(.easeOut(duration: 0.34)) { phase = .done }
        }
    }
}
