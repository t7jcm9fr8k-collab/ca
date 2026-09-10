// Copyright (c) 2026 the HUDKit authors
//
// The value types the HUD components draw. Nothing here does date arithmetic
// or holds state — a host app decides what a day *is* and hands the result
// over; the views only render what these say.
//
// Only the `launchReadoutsLive` environment key at the bottom needs SwiftUI.
// The model types themselves are Foundation-only on purpose: `kind` and
// `state` name a meaning and the view decides the colour, so the model stays
// free of presentation.

import Foundation
import SwiftUI

// MARK: - Scheduled items (AgendaCell)

/// Something the host app knows is scheduled, on a given day.
public struct ScheduledItem: Identifiable, Equatable {
    /// `calendar` is somebody else's obligation rather than one of the
    /// user's own commitments, and the view colours it accordingly — the
    /// user's are tinted, the world's are muted. Context, not accountability.
    public enum Kind: Equatable { case commitment, punchList, calendar }

    /// The single character that identifies the item in a strip cell.
    public let letter: String
    public let label: String
    public let hour: Int
    public let minute: Int
    public let kind: Kind

    public var id: String { "\(letter)\(hour):\(minute)" }

    public init(letter: String, label: String, hour: Int, minute: Int, kind: Kind) {
        self.letter = letter
        self.label = label
        self.hour = hour
        self.minute = minute
        self.kind = kind
    }
}

// MARK: - Week strip (DayCell)

/// What one day of the rolling tracker means, already decided by the host.
public enum DayState: Equatable {
    case rest         // not a scheduled day
    case pending      // scheduled, not yet done, still before the deadline — or still ahead
    case late         // scheduled, not yet done, past the deadline, today
    case done         // logged
    case missed       // scheduled, the day is over, nothing was logged
    case critical     // scheduled, not done, AND the last scheduled day was missed
}

// MARK: - Month grid (MonthGrid)

/// One cell of the month grid, already decided.
///
/// The view does no date arithmetic and makes no judgements — it draws what
/// this says. Padding cells carry a nil date.
public struct MonthDay: Identifiable {
    /// A string, not the grid index.
    ///
    /// `MonthGrid` puts two `ForEach` blocks in one `LazyVGrid` — the seven
    /// weekday headings keyed `0...6`, then the days. With an `Int` id the
    /// two namespaces collided and SwiftUI warned that an ID "is used by
    /// multiple child views, this will give undefined results".
    public let id: String
    public let date: Date?
    public let number: String
    public let logged: Bool
    public let scheduled: Bool
    public let isToday: Bool
    public let inFuture: Bool

    public init(id: String, date: Date?, number: String, logged: Bool,
                scheduled: Bool, isToday: Bool, inFuture: Bool) {
        self.id = id
        self.date = date
        self.number = number
        self.logged = logged
        self.scheduled = scheduled
        self.isToday = isToday
        self.inFuture = inFuture
    }
}

/// A month laid out Sunday→Saturday, with its own adherence summary.
public struct MonthView {
    public let title: String
    public let days: [MonthDay]
    public let logged: Int
    public let possible: Int
    public let bonus: Int

    public init(title: String, days: [MonthDay], logged: Int, possible: Int, bonus: Int) {
        self.title = title
        self.days = days
        self.logged = logged
        self.possible = possible
        self.bonus = bonus
    }

    /// "9 of 13 scheduled days · +4 off-day"
    public var summary: String {
        let base = "\(logged) of \(possible) scheduled days"
        return bonus > 0 ? "\(base) · +\(bonus) off-day" : base
    }
}

// MARK: - Punch-list marks (StateMark)

/// The three punch-list states. Three marks, readable in a raw checklist:
/// `[ ]` to do, `[~]` in progress, `[x]` done.
public enum PunchState: Equatable { case done, inProgress, todo }

// MARK: - Launch readout gate (Readout)

/// Read by `Readout` for the roll-from-zero beat. Default TRUE on purpose:
/// previews, secondary windows and every tree that is not mid-power-on show
/// real figures and never know this exists. A host that stages a power-on
/// sets it false on the tree and flips it inside `withAnimation`, so
/// `numericText` rolls every figure up from 0.
public struct LaunchReadoutsLiveKey: EnvironmentKey {
    public static let defaultValue = true
}

public extension EnvironmentValues {
    var launchReadoutsLive: Bool {
        get { self[LaunchReadoutsLiveKey.self] }
        set { self[LaunchReadoutsLiveKey.self] = newValue }
    }
}
