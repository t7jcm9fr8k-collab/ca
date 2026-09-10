import SwiftUI
// ⚠ Combine must be imported by name: `ObservableObject` and `@Published` are
// Combine's, and the macOS 26 SDK's stricter module visibility no longer lets
// them ride in through SwiftUI — which is exactly the pair of errors this file
// shipped with on 2026-08-19 ("does not conform to ObservableObject" +
// "init(wrappedValue:) … missing import of defining module 'Combine'").
import Combine

/// One observable wrapper around `ProcessInfo.thermalState`, shared by
/// everything that draws continuously.
///
/// A fanless laptop has no fan curve between "warm" and "throttled", so the
/// app's job is to keep *average* power low and to back off the moment the
/// machine reports pressure. The ladder, from the 2026-08-19 thermal pass:
///
/// | state      | orb                    | fight                       |
/// |------------|------------------------|-----------------------------|
/// | nominal    | 30fps, full            | 60fps, full                 |
/// | fair       | 30fps, no bolt glow    | 60fps, full                 |
/// | serious    | frozen honest frame    | 30fps, smears shed          |
/// | critical   | frozen honest frame    | parked on the idle frame    |
///
/// Costs nothing when cool: the notification fires on change, and reads are
/// a plain property. Nothing polls.
public final class ThermalWatch: ObservableObject {
    public static let shared = ThermalWatch()

    @Published public private(set) var state: ProcessInfo.ThermalState

    /// LOW HEAT — a manual floor under the ladder (2026-08-19, for
    /// long sessions on the lap). While on, `level` reports at least
    /// `.serious` regardless of the sensors: the sky freezes, the reactor
    /// rests on its honest frame, the planets park, the fight sheds to 30fps
    /// — every consumer already obeys the ladder, so one floor governs all
    /// of them. It only ever LOWERS activity, which is what keeps it on the
    /// right side of the Settings boundary; Reduce Motion and Low Power stay
    /// the system's and are never touched.
    @Published public var lowHeat: Bool {
        didSet { UserDefaults.standard.set(lowHeat, forKey: "power.lowHeat") }
    }

    /// `rawValue` as a rung: 0 nominal, 1 fair, 2 serious, 3 critical —
    /// the order `ProcessInfo.ThermalState` declares them in — floored at
    /// 2 while LOW HEAT is on.
    public var level: Int { max(state.rawValue, lowHeat ? 2 : 0) }

    /// The block-based observer stays registered for the app's lifetime —
    /// the singleton never deinits, so the token is deliberately dropped.
    private init() {
        state = ProcessInfo.processInfo.thermalState
        lowHeat = UserDefaults.standard.bool(forKey: "power.lowHeat")
        _ = NotificationCenter.default.addObserver(
            forName: ProcessInfo.thermalStateDidChangeNotification,
            object: nil, queue: .main
        ) { [weak self] _ in
            self?.state = ProcessInfo.processInfo.thermalState
        }
    }
}
