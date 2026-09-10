import SwiftUI

/// A framed panel with cut corners and a label tab, as in the reference HUDs.
///
/// With `enterOrder` set, the panel materialises on arrival instead of
/// popping (the motion spec): the outline draws itself in 160ms — the
/// FUI trim move — the body wipes in behind it, and the whole thing carries
/// `order` × 50ms of stagger so a destination's panels arrive as a cascade
/// rather than a block. Nil (the default) is exactly the old static panel;
/// twenty-plus existing call sites pay nothing.
public struct HUDPanel<Content: View>: View {
    public var title: String
    public var accent: Color = Theme.Color.primary
    public var code: String? = nil          // retired 2026-08-15 — no longer rendered
    public var enterOrder: Int? = nil
    @ViewBuilder public var content: Content

    public init(title: String, accent: Color = Theme.Color.primary, code: String? = nil,
                enterOrder: Int? = nil, @ViewBuilder content: () -> Content) {
        self.title = title
        self.accent = accent
        self.code = code
        self.enterOrder = enterOrder
        self.content = content()
    }

    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @State private var strokeOn = false
    @State private var bodyOn = false

    /// Visible immediately when the entrance is off or refused; hidden on the
    /// first frame when it is on, so nothing flashes before its own arrival.
    private var strokeShown: Bool { enterOrder == nil || reduceMotion || strokeOn }
    private var bodyShown: Bool { enterOrder == nil || reduceMotion || bodyOn }

    public var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            HStack(spacing: 8) {
                Rectangle()
                    .fill(accent)
                    .frame(width: 3, height: 11)
                Text(title.uppercased())
                    .font(Theme.Font.label())
                    .tracking(1.6)
                    .foregroundStyle(Theme.Color.text)
                Spacer(minLength: 8)
                // Panel codes ("H4", "R4", "FN03") retired 2026-08-15 at
                // a design decision. The parameter survives so call sites
                // don't churn; nothing reads it.
            }
            .padding(.horizontal, Theme.Metric.panelPad)
            .padding(.vertical, 10)
            .background(Theme.Color.panelHi.opacity(0.6))

            Rectangle()
                .fill(Theme.Color.structure.opacity(0.5))
                .frame(height: Theme.Metric.hairline)

            content
                .padding(Theme.Metric.panelPad)
                .frame(maxWidth: .infinity, alignment: .leading)
        }
        .background(Theme.Color.panel.opacity(0.85))
        .clipShape(CutCorner())
        // Fill and content wipe in while the freshly-drawn outline holds
        // position — travel belongs to the rows (`cascadeIn`), not the frame.
        .opacity(bodyShown ? 1 : 0)
        .overlay(
            // The outline is drawn by trim so it can draw itself in. At rest
            // this is the same stroked CutCorner as always.
            CutCorner()
                .trim(from: 0, to: strokeShown ? 1 : 0)
                .stroke(Theme.Color.structure.opacity(0.75),
                        lineWidth: Theme.Metric.hairline)
        )
        .onAppear {
            guard let order = enterOrder, !reduceMotion, !bodyOn else { return }
            let d = Double(order) * Motion.panelStep
            withAnimation(.easeOut(duration: 0.16).delay(d)) { strokeOn = true }
            withAnimation(Motion.enter.delay(d + 0.10)) { bodyOn = true }
        }
    }
}

/// A labelled numeric readout. Monospaced, because it's an instrument.
///
/// Pass `roll` (the value as a number) and changes arrive as a directional
/// numeral roll instead of a string swap — digits climb when it rises, fall
/// when it drops. The mutation has to happen inside `withAnimation`, which is
/// where the log button already puts it.
public struct Readout: View {
    public var label: String
    public var value: String
    public var suffix: String? = nil
    public var accent: Color = Theme.Color.primary
    public var size: CGFloat = 26
    public var roll: Double? = nil

    public init(label: String, value: String, suffix: String? = nil,
                accent: Color = Theme.Color.primary, size: CGFloat = 26,
                roll: Double? = nil) {
        self.label = label
        self.value = value
        self.suffix = suffix
        self.accent = accent
        self.size = size
        self.roll = roll
    }

    /// L's third beat (launch power-on, the host's shell view): until the
    /// launch clock says live, the figure renders 0; the flip to the real value
    /// happens inside the conductor's withAnimation, so numericText rolls it up.
    /// Defaults true — only a tree mid-power-on ever zeros a figure.
    @Environment(\.launchReadoutsLive) private var launchLive

    public var body: some View {
        VStack(alignment: .leading, spacing: 3) {
            Text(label.uppercased())
                .font(Theme.Font.label(9))
                .tracking(1.4)
                .foregroundStyle(Theme.Color.textMuted)
            HStack(alignment: .firstTextBaseline, spacing: 3) {
                Text(launchLive ? value : "0")
                    .font(Theme.Font.data(size))
                    .foregroundStyle(accent)
                    .contentTransition(.numericText(value: launchLive ? (roll ?? 0) : 0))
                if let suffix {
                    Text(suffix)
                        .font(Theme.Font.data(11))
                        .foregroundStyle(Theme.Color.textFaint)
                }
            }
        }
    }
}

/// The vertical tick rails that frame the references. Pure structure —
/// they imply a larger system continuing off-screen.
public struct TickRail: View {
    public var prefix: String = "FN"
    public var count: Int = 22
    public var highlighted: Set<Int> = [3, 9, 17]

    public init(prefix: String = "FN", count: Int = 22, highlighted: Set<Int> = [3, 9, 17]) {
        self.prefix = prefix
        self.count = count
        self.highlighted = highlighted
    }

    public var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            ForEach(0..<count, id: \.self) { i in
                HStack(spacing: 5) {
                    Rectangle()
                        .fill(highlighted.contains(i)
                              ? Theme.Color.alert
                              : Theme.Color.structure.opacity(0.55))
                        .frame(width: highlighted.contains(i) ? 10 : 5, height: 1.5)
                    // The FN_xx / SR_xx labels are gone (2026-08-15) — the
                    // rails stay as pure geometry, per the no-fake-codes call.
                }
                .frame(maxWidth: .infinity, alignment: .leading)
                Spacer(minLength: 0)
            }
        }
        .frame(width: Theme.Metric.railWidth * 2)
    }
}

/// One cell of the rolling 7-day tracker.
public struct DayCell: View {
    public var date: Date
    public var state: DayState
    /// Supplied only for days that may be corrected. Nil leaves the cell inert,
    /// which is how future days stay unclickable without a second flag.
    public var onToggle: (() -> Void)? = nil

    public init(date: Date, state: DayState, onToggle: (() -> Void)? = nil) {
        self.date = date
        self.state = state
        self.onToggle = onToggle
    }

    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @State private var hovering = false

    private var glyph: String {
        let f = DateFormatter(); f.dateFormat = "EEEEE"      // single letter
        return f.string(from: date)
    }

    private var tint: Color {
        switch state {
        case .done:     return Theme.Color.logged
        case .missed:   return Theme.Color.missed
        case .critical: return Theme.Color.alert
        case .late:     return Theme.Color.missed.opacity(0.75)
        case .pending:  return Theme.Color.primary
        case .rest:     return Theme.Color.structure
        }
    }

    /// Fill and dot are reserved for a logged day. That treatment, not the hue
    /// alone, is what keeps lime and yellow apart at a glance — and what keeps
    /// a yellow miss from being confused with gold used as an accent nearby.
    private var filled: Bool { state == .done }

    public var body: some View {
        VStack(spacing: 6) {
            Text(glyph)
                .font(Theme.Font.data(9))
                .foregroundStyle(Theme.Color.textFaint)
            ZStack {
                // Locked-but-visible, the same grammar as the skill tree:
                // you always see the shape of what's possible.
                CutCorner(cut: 4, corners: [.topLeading, .bottomTrailing])
                    .fill(filled ? tint.opacity(0.22) : Color.clear)
                CutCorner(cut: 4, corners: [.topLeading, .bottomTrailing])
                    .stroke(tint.opacity(filled ? 1 : 0.5), lineWidth: 1)
                if filled {
                    // The splash beat of a log (§3.4): the dot arrives through
                    // the event spring, so it pops past size and settles. The
                    // transition plays whenever `filled` flips — log, undo,
                    // backfill — because the animation below owns the change.
                    Circle().fill(tint).frame(width: 5, height: 5)
                        .shadow(color: tint, radius: 4)
                        .transition(.scale(scale: 0.15).combined(with: .opacity))
                }
            }
            .frame(width: 30, height: 30)
            .animation(reduceMotion ? nil : Motion.event, value: filled)
            .overlay(
                CutCorner(cut: 4, corners: [.topLeading, .bottomTrailing])
                    .stroke(Theme.Color.text.opacity(hovering ? 0.85 : 0), lineWidth: 1)
            )
            .contentShape(Rectangle())
            .onTapGesture { onToggle?() }
            .onHover { inside in
                guard onToggle != nil else { return }
                hovering = inside
                if inside { NSCursor.pointingHand.push() } else { NSCursor.pop() }
            }
        }
        .help(onToggle == nil ? "" : (filled ? "Logged — click to clear"
                                             : "Not logged — click to backfill"))
    }
}

/// A day on the agenda strip: what is scheduled, not whether it was done.
///
/// Same cut-corner grammar as `DayCell` so the two strips read as one family.
/// 2026-08-20: the weekly calendar was shoving multiple letters into one
/// box — three letters and a +n crammed into 30pt.
/// The cell now carries a count and up to three kind-tinted ticks, and the
/// detail moved to where detail fits: a hover card listing every item with its
/// time. An empty day is drawn, not omitted — the shape of the week stays
/// legible.
public struct AgendaCell: View {
    public var date: Date
    public var items: [ScheduledItem]
    public var isToday: Bool
    /// Yesterday on the strip is history — it recedes rather than competing
    /// with today (agenda states, 2026-08-15).
    public var isPast: Bool = false

    public init(date: Date, items: [ScheduledItem], isToday: Bool, isPast: Bool = false) {
        self.date = date
        self.items = items
        self.isToday = isToday
        self.isPast = isPast
    }

    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @State private var hovering = false

    private var glyph: String {
        let f = DateFormatter(); f.dateFormat = "EEEEE"          // single letter
        return f.string(from: date)
    }

    private var dayNumber: String {
        let f = DateFormatter(); f.dateFormat = "d"
        return f.string(from: date)
    }

    private func tint(_ kind: ScheduledItem.Kind) -> Color {
        switch kind {
        case .commitment: return Theme.Color.primary
        case .punchList:  return Theme.Color.earned
        case .calendar:   return Theme.Color.textMuted
        }
    }

    private var stroke: Color {
        if isToday { return Theme.Color.primary }
        return items.isEmpty ? Theme.Color.structure.opacity(0.45) : Theme.Color.structure
    }

    public var body: some View {
        VStack(spacing: 6) {
            Text("\(glyph) \(dayNumber)")
                .font(Theme.Font.data(9))
                .foregroundStyle(isToday ? Theme.Color.primary : Theme.Color.textFaint)
            ZStack {
                CutCorner(cut: 4, corners: [.topLeading, .bottomTrailing])
                    .fill(items.isEmpty ? Color.clear : Theme.Color.panelHi)
                CutCorner(cut: 4, corners: [.topLeading, .bottomTrailing])
                    .stroke(stroke, lineWidth: isToday ? 2 : 1)

                if items.isEmpty {
                    Text("·")
                        .font(Theme.Font.data(11))
                        .foregroundStyle(Theme.Color.structure)
                } else {
                    // The count is the fact; the ticks are the mix. Both fit
                    // 30pt at any load, so the cell can never spill again.
                    VStack(spacing: 3) {
                        Text("\(items.count)")
                            .font(Theme.Font.data(11))
                            .foregroundStyle(Theme.Color.text)
                        HStack(spacing: 2) {
                            ForEach(items.prefix(3)) { item in
                                Rectangle()
                                    .fill(tint(item.kind))
                                    .frame(width: 5, height: 2)
                            }
                        }
                    }
                }
            }
            .frame(width: 30, height: 30)
        }
        .opacity(isPast ? 0.55 : 1)
        .contentShape(Rectangle())
        .onHover { inside in
            guard !items.isEmpty else { return }
            withAnimation(reduceMotion ? nil : Motion.micro) { hovering = inside }
        }
        // The card drops BELOW the cell on purpose: `HUDPanel` clips to its
        // cut-corner shape, so anything rising above the strip would be cut
        // off at the panel edge. Below it lands over the second strip and the
        // legend, which a transient card may briefly cover.
        .overlay(alignment: .top) {
            if hovering {
                agendaCard
                    .offset(y: 66)
                    .transition(reduceMotion ? .identity
                                : .opacity.combined(with: .offset(y: -5))
                                    .combined(with: .scale(scale: 0.97, anchor: .top)))
            }
        }
        .zIndex(hovering ? 60 : 0)
        .help(items.isEmpty ? "Nothing scheduled"
                            : items.map(\.label).joined(separator: " · "))
    }

    /// Every item on the day, with its time and its kind — the detail the
    /// 30pt cell was being asked to carry and never could.
    private var agendaCard: some View {
        VStack(alignment: .leading, spacing: 5) {
            Text(cardTitle)
                .font(Theme.Font.label(8))
                .tracking(1.4)
                .foregroundStyle(isToday ? Theme.Color.primary : Theme.Color.textMuted)

            ForEach(items.prefix(6)) { item in
                HStack(spacing: 7) {
                    Rectangle()
                        .fill(tint(item.kind))
                        .frame(width: 3, height: 10)
                    Text(String(format: "%02d:%02d", item.hour, item.minute))
                        .font(Theme.Font.data(9))
                        .foregroundStyle(Theme.Color.textMuted)
                    Text(item.label)
                        .font(Theme.Font.body(11))
                        .foregroundStyle(Theme.Color.text)
                        .lineLimit(1)
                    Spacer(minLength: 0)
                }
            }
            if items.count > 6 {
                Text("+ \(items.count - 6) MORE")
                    .font(Theme.Font.data(8))
                    .foregroundStyle(Theme.Color.textFaint)
            }
        }
        .padding(10)
        .frame(width: 236, alignment: .leading)
        .background(CutCorner(cut: 6).fill(Theme.Color.panelHi.opacity(0.97)))
        .overlay(CutCorner(cut: 6).stroke(
            isToday ? Theme.Color.primary.opacity(0.8) : Theme.Color.structure,
            lineWidth: 1))
        .fixedSize()
        .allowsHitTesting(false)
    }

    private var cardTitle: String {
        let f = DateFormatter(); f.dateFormat = "EEEE d MMM"
        return f.string(from: date).uppercased()
    }
}

/// The month grid behind the `+`.
///
/// Deliberately quiet. It exists to show a shape over time, not to be read
/// cell by cell — so a logged day is a filled mark, a missed scheduled day is
/// an outline in alert, and everything else recedes. Arrows only appear when
/// pinned, because you cannot click them while merely hovering.
public struct MonthGrid: View {
    public var month: MonthView
    public var pinned: Bool
    public var onPrev: () -> Void
    public var onNext: () -> Void
    /// Correcting an older day belongs here as much as in the week strip —
    /// this is where you notice a gap from three weeks ago.
    public var onToggle: ((Date) -> Void)? = nil

    /// Hover reports the day under the pointer, or nil on exit.
    ///
    /// ⚠ Deliberately **not** gated on `onToggle`, unlike the cursor and the
    /// hover ring. Toggling is refused on future days — logging a day that has
    /// not happened is a fiction — but *reading* a future day is the entire
    /// point of a day panel. Gating these together would have made the feature
    /// work only on the past.
    public var onHoverDay: ((Date?) -> Void)? = nil

    /// Days carrying a calendar irregularity, as `startOfDay` values.
    public var irregularDays: Set<Date> = []

    /// Clicking a **future** day pins its plan.
    ///
    /// ⚠ Corrected 2026-08-18. A previous note claimed the click was already
    /// spoken for and framed the day panel as a contested gesture. **That was
    /// only half true.** `onToggle` is nil on future days, because logging a
    /// day that has not happened is a fiction — so the click was free there the
    /// whole time. Past days keep backfill; future days get the list. The two
    /// never compete, because no day is both.
    public var onSelectDay: ((Date) -> Void)? = nil

    /// Cell metrics. Defaults are the dashboard's peek size; the ⌘, Calendar
    /// destination passes something far larger, because a month grid occupying
    /// 8% of a wide desktop window reads as a widget that escaped.
    public var cellWidth: CGFloat = 30
    public var cellHeight: CGFloat = 26
    public var cellSpacing: CGFloat = 6

    /// Events per day, keyed by `startOfDay`. Rendered as up to three dots
    /// under the number — only worth showing once cells are big enough to
    /// hold them, which is why it is empty by default.
    public var eventCounts: [Date: Int] = [:]

    /// Menu item G. Passing the offset lets paging replay the cell cascade —
    /// the grid re-keys on it — and lets the stagger run in the direction of
    /// travel: paging forward deals top-left first, paging back deals from
    /// the bottom-right, so the cells appear to arrive from where you came.
    public var monthOffset: Int = 0

    public init(month: MonthView, pinned: Bool,
                onPrev: @escaping () -> Void, onNext: @escaping () -> Void,
                onToggle: ((Date) -> Void)? = nil,
                onHoverDay: ((Date?) -> Void)? = nil,
                irregularDays: Set<Date> = [],
                onSelectDay: ((Date) -> Void)? = nil,
                cellWidth: CGFloat = 30, cellHeight: CGFloat = 26, cellSpacing: CGFloat = 6,
                eventCounts: [Date: Int] = [:],
                monthOffset: Int = 0) {
        self.month = month
        self.pinned = pinned
        self.onPrev = onPrev
        self.onNext = onNext
        self.onToggle = onToggle
        self.onHoverDay = onHoverDay
        self.irregularDays = irregularDays
        self.onSelectDay = onSelectDay
        self.cellWidth = cellWidth
        self.cellHeight = cellHeight
        self.cellSpacing = cellSpacing
        self.eventCounts = eventCounts
        self.monthOffset = monthOffset
    }

    @State private var pageDir = 1

    private var columns: [GridItem] {
        Array(repeating: GridItem(.fixed(cellWidth), spacing: cellSpacing), count: 7)
    }
    private let headings = ["S", "M", "T", "W", "T", "F", "S"]

    private func dealOrder(_ i: Int) -> Int {
        pageDir >= 0 ? i : max(0, month.days.count - 1 - i)
    }

    public var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack(spacing: 10) {
                Text(month.title.uppercased())
                    .font(Theme.Font.label(10))
                    .tracking(1.6)
                    .foregroundStyle(Theme.Color.earned)
                Spacer()
                if pinned {
                    Button(action: onPrev) { Image(systemName: "chevron.left") }
                        .buttonStyle(.plain)
                        .foregroundStyle(Theme.Color.textMuted)
                    Button(action: onNext) { Image(systemName: "chevron.right") }
                        .buttonStyle(.plain)
                        .foregroundStyle(Theme.Color.textMuted)
                }
            }

            LazyVGrid(columns: columns, spacing: cellSpacing) {
                ForEach(0..<7, id: \.self) { i in
                    Text(headings[i])
                        .font(Theme.Font.data(9))
                        .foregroundStyle(Theme.Color.textFaint)
                }
                ForEach(Array(month.days.enumerated()), id: \.element.id) { i, day in
                    monthCell(day)
                        .cascadeIn(dealOrder(i), step: 0.003)
                }
            }
            // Re-keying on the offset is what makes a page change an arrival:
            // every cell is fresh, so `cascadeIn`'s onAppear fires again.
            .id(monthOffset)
            .onChange(of: monthOffset) { old, new in
                pageDir = new >= old ? 1 : -1
            }

            Divider().overlay(Theme.Color.structure)

            Text(month.summary)
                .font(Theme.Font.data(10))
                .foregroundStyle(Theme.Color.textMuted)
        }
        .padding(14)
        .background(CutCorner(cut: 8).fill(Theme.Color.panel))
        .overlay(CutCorner(cut: 8).stroke(Theme.Color.earned.opacity(0.45), lineWidth: 1))
    }

    private func monthCell(_ day: MonthDay) -> some View {
        MonthDayCell(
            day: day,
            irregular: day.date.map {
                irregularDays.contains(Calendar.current.startOfDay(for: $0))
            } ?? false,
            onToggle: (day.date != nil && !day.inFuture && onToggle != nil)
                ? { if let d = day.date { onToggle?(d) } }
                : nil,
            onHoverDay: onHoverDay.map { report in
                { inside in report(inside ? day.date : nil) }
            },
            onSelectDay: (day.date != nil && day.inFuture && onSelectDay != nil)
                ? { if let d = day.date { onSelectDay?(d) } }
                : nil,
            width: cellWidth,
            height: cellHeight,
            eventCount: day.date.map {
                eventCounts[Calendar.current.startOfDay(for: $0)] ?? 0
            } ?? 0
        )
    }
}

private struct MonthDayCell: View {
    var day: MonthDay
    var irregular: Bool = false
    var onToggle: (() -> Void)? = nil
    var onHoverDay: ((Bool) -> Void)? = nil
    var onSelectDay: (() -> Void)? = nil
    var width: CGFloat = 30
    var height: CGFloat = 26
    var eventCount: Int = 0

    @State private var hovering = false

    /// A past day toggles, a future day selects, a blank does neither. The
    /// pointer and the hover ring follow this rather than `onToggle` alone —
    /// gating them on toggle made future days look dead when they are not.
    private var isInteractive: Bool { onToggle != nil || onSelectDay != nil }

    private var helpText: String {
        if onToggle != nil {
            return day.logged ? "Logged — click to clear" : "Not logged — click to backfill"
        }
        if onSelectDay != nil { return "Click to pin this day's plan" }
        return ""
    }

    private var tint: Color {
        if day.logged { return Theme.Color.logged }
        if day.scheduled { return day.inFuture ? Theme.Color.primary : Theme.Color.missed }
        return Theme.Color.structure
    }

    var body: some View {
        ZStack {
            if day.date != nil {
                CutCorner(cut: 3, corners: [.topLeading, .bottomTrailing])
                    .fill(day.logged ? tint.opacity(0.22) : Color.clear)
                CutCorner(cut: 3, corners: [.topLeading, .bottomTrailing])
                    .stroke(tint.opacity(day.scheduled || day.logged ? 0.9 : 0.30),
                            lineWidth: day.isToday ? 2 : 1)
                VStack(spacing: 2) {
                    Text(day.number)
                        .font(Theme.Font.data(height >= 40 ? 13 : 10))
                        .foregroundStyle(day.logged ? Theme.Color.logged
                                         : (day.scheduled ? Theme.Color.textMuted
                                            : Theme.Color.textFaint))
                    // Only drawn when the cell is tall enough to hold them
                    // without crowding the number.
                    if eventCount > 0 && height >= 40 {
                        HStack(spacing: 2) {
                            ForEach(0..<min(eventCount, 3), id: \.self) { _ in
                                Circle()
                                    .fill(Theme.Color.primary.opacity(0.75))
                                    .frame(width: 3, height: 3)
                            }
                        }
                    }
                }
                if hovering {
                    CutCorner(cut: 3, corners: [.topLeading, .bottomTrailing])
                        .stroke(Theme.Color.text.opacity(0.85), lineWidth: 1)
                }
                // Corner triangle, never a fill. `irregular` is 3° from
                // `Mood.angry`; a mark this small and this shaped cannot be
                // mistaken for the mood hologram, a filled block could.
                if irregular {
                    IrregularMark()
                        .fill(Theme.Color.irregular)
                        .frame(width: 7, height: 7)
                        .frame(maxWidth: .infinity, maxHeight: .infinity,
                               alignment: .topTrailing)
                        .padding(1)
                }
            }
        }
        .frame(width: width, height: height)
        .contentShape(Rectangle())
        .onTapGesture {
            if let toggle = onToggle { toggle() } else { onSelectDay?() }
        }
        .onHover { inside in
            onHoverDay?(inside)
            guard isInteractive else { return }
            hovering = inside
            if inside { NSCursor.pointingHand.push() } else { NSCursor.pop() }
        }
        .help(helpText)
    }
}

/// A filled triangle in the cell's top-right corner. Its own shape rather than
/// an SF Symbol because at 7pt `exclamationmark.triangle.fill` renders as a
/// smudge — the glyph's internal bar disappears below about 9pt, leaving a
/// blob that reads as a dot.
public struct IrregularMark: Shape {
    public init() {}

    public func path(in r: CGRect) -> Path {
        var p = Path()
        p.move(to: CGPoint(x: r.midX, y: r.minY))
        p.addLine(to: CGPoint(x: r.maxX, y: r.maxY))
        p.addLine(to: CGPoint(x: r.minX, y: r.maxY))
        p.closeSubpath()
        return p
    }
}

/// The three punch-list state marks. Always shape plus color, never color
/// alone — the state has to survive grayscale, small sizes, and color-vision
/// deficiency (states decision, 2026-08-15).
///
/// Menu item M: the mark is one `Image` whose symbol swaps through the
/// replace effect, so todo → in-progress reads as the half-fill sweeping in —
/// the two-frame move §3.5 asks for — instead of one glyph teleporting into
/// another. One view with stable identity is what makes the transition
/// engage; the old `switch` built three different views and nothing could
/// animate between them.
public struct StateMark: View {
    public var state: PunchState

    public init(state: PunchState) {
        self.state = state
    }

    @Environment(\.accessibilityReduceMotion) private var reduceMotion

    private var symbol: String {
        switch state {
        case .done:       return "checkmark.circle.fill"
        case .inProgress: return "circle.lefthalf.filled"
        case .todo:       return "circle"
        }
    }

    private var tint: Color {
        switch state {
        case .done:       return Theme.Color.logged
        case .inProgress: return Theme.Color.primary
        case .todo:       return Theme.Color.textMuted
        }
    }

    public var body: some View {
        Image(systemName: symbol)
            .font(.system(size: 13, weight: state == .todo ? .regular : .semibold))
            .foregroundStyle(tint)
            .contentTransition(.symbolEffect(.replace))
            .animation(reduceMotion ? nil : Motion.event, value: state)
    }
}

/// Primary action button in the HUD language.
///
/// Firing it plays the four beats (the motion spec): a 60ms compress —
/// the lean-away — then a low-damped spring back to rest whose overshoot is
/// the third beat. Nothing is hand-keyed past the antic; the spring does the
/// rest. Reduce Motion presses flat.
public struct HUDButton: View {
    public var title: String
    public var accent: Color = Theme.Color.primary
    public var filled: Bool = false
    public var action: () -> Void

    public init(title: String, accent: Color = Theme.Color.primary, filled: Bool = false,
                action: @escaping () -> Void) {
        self.title = title
        self.accent = accent
        self.filled = filled
        self.action = action
    }

    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @State private var hovering = false
    @State private var beatScale: CGFloat = 1

    private func fourBeat() {
        guard !reduceMotion else { return }
        withAnimation(.easeOut(duration: 0.06)) { beatScale = 0.965 }
        withAnimation(.spring(response: 0.20, dampingFraction: 0.55).delay(0.06)) {
            beatScale = 1.0
        }
    }

    public var body: some View {
        Button(action: { fourBeat(); action() }) {
            Text(title.uppercased())
                .font(Theme.Font.label(10))
                .tracking(1.6)
                .foregroundStyle(filled ? Theme.Color.void : accent)
                .padding(.horizontal, 16)
                .padding(.vertical, 9)
                .background(
                    CutCorner(cut: 6)
                        .fill(filled
                              ? accent.opacity(hovering ? 1 : 0.9)
                              : accent.opacity(hovering ? 0.18 : 0.08))
                )
                .overlay(
                    CutCorner(cut: 6).stroke(accent.opacity(filled ? 0 : 0.7), lineWidth: 1)
                )
        }
        .buttonStyle(.plain)
        .scaleEffect(beatScale)
        .onHover { hovering = $0 }
    }
}

/// The ON/OFF morph from the UpgradesSoon toggle clip: one pill, the knob
/// slides, the word crossfades — a selection is a thing that moves, not a
/// repaint. First use: LOW HEAT in Settings; menu item F grows the rest of
/// the pickers from this.
public struct HUDPillToggle: View {
    public var title: String
    @Binding public var isOn: Bool
    /// Cyan for ordinary preferences; LOW HEAT passes `alert` because that
    /// switch is the one whose ON state is asking for attention.
    public var accent: Color = Theme.Color.primary

    public init(title: String, isOn: Binding<Bool>, accent: Color = Theme.Color.primary) {
        self.title = title
        self._isOn = isOn
        self.accent = accent
    }

    @Environment(\.accessibilityReduceMotion) private var reduceMotion

    public var body: some View {
        Button {
            if reduceMotion { isOn.toggle() }
            else { withAnimation(Motion.event) { isOn.toggle() } }
        } label: {
            HStack(spacing: 10) {
                Text(title)
                    .font(Theme.Font.body(12))
                    .foregroundStyle(Theme.Color.text)
                Spacer(minLength: 8)
                ZStack(alignment: isOn ? .trailing : .leading) {
                    CutCorner(cut: 5)
                        .fill(isOn ? accent.opacity(0.16) : Theme.Color.panelHi)
                    CutCorner(cut: 5)
                        .stroke(isOn ? accent : Theme.Color.structure, lineWidth: 1)
                    Text(isOn ? "ON" : "OFF")
                        .font(Theme.Font.data(7))
                        .tracking(1)
                        .foregroundStyle(isOn ? accent : Theme.Color.textFaint)
                        .frame(maxWidth: .infinity, alignment: isOn ? .leading : .trailing)
                        .padding(.horizontal, 5)
                    CutCorner(cut: 4)
                        .fill(isOn ? accent : Theme.Color.textMuted)
                        .frame(width: 14, height: 14)
                        .padding(2)
                }
                .frame(width: 46, height: 20)
            }
            .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
        .accessibilityLabel(title)
        .accessibilityValue(isOn ? "on" : "off")
    }
}

// MARK: - Motion
//
// One rule governs everything below: **animate on the compositor, never through
// a Canvas.** Opacity, offset, scale and blur are handled by the render server
// and cost almost nothing. A value a `Canvas` reads is different — changing it
// forces a full redraw at 60fps, which is how a "subtle glow" turns into the
// most expensive thing on screen. `SpaceBackdrop` and the host's fight surface
// are Canvas. Nothing here touches them.
//
// The second rule is borrowed from the fight, because it already proved itself:
// **idle motion runs on a duty cycle.** A continuously repeating animation
// keeps the display link alive forever — cheap per frame, never zero. A sweep
// that runs 1.2s every 12s is 10% duty, the same trade the fight makes, and the
// other 90% costs literally nothing because no animation exists.

/// A slow breath on opacity. Compositor-only, and the one place a repeating
/// animation is allowed — a single layer, on the focused element only.
public struct Breathing: ViewModifier {
    public var low: Double = 0.55
    public var high: Double = 1.0
    public var period: Double = 4.2

    public init(low: Double = 0.55, high: Double = 1.0, period: Double = 4.2) {
        self.low = low
        self.high = high
        self.period = period
    }

    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @State private var lit = false

    private var slowed: Double {
        ProcessInfo.processInfo.isLowPowerModeEnabled ? period * 2 : period
    }

    public func body(content: Content) -> some View {
        content
            .opacity(reduceMotion ? high : (lit ? high : low))
            .onAppear {
                guard !reduceMotion else { return }
                withAnimation(.easeInOut(duration: slowed).repeatForever(autoreverses: true)) {
                    lit = true
                }
            }
    }
}

/// A light sweep crossing a panel, then nothing until the next one.
///
/// ⚠ **Not a repeating animation.** The task sleeps, runs one 1.2-second pass,
/// and sleeps again. Between passes there is no animation in flight at all,
/// which is the difference between 10% duty and 100%.
public struct PeriodicSweep: ViewModifier {
    public var every: Double = 12
    public var pass: Double = 1.2
    public var tint: Color = Theme.Color.primary

    public init(every: Double = 12, pass: Double = 1.2, tint: Color = Theme.Color.primary) {
        self.every = every
        self.pass = pass
        self.tint = tint
    }

    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @State private var x: CGFloat = -0.5
    @State private var visible = false

    public func body(content: Content) -> some View {
        content.overlay {
            GeometryReader { geo in
                LinearGradient(colors: [.clear, tint.opacity(0.13), .clear],
                               startPoint: .leading, endPoint: .trailing)
                    .frame(width: geo.size.width * 0.4)
                    .offset(x: x * geo.size.width)
                    .blendMode(.plusLighter)
                    .opacity(visible ? 1 : 0)
                    .allowsHitTesting(false)
            }
            .clipped()
            .allowsHitTesting(false)
        }
        .task {
            guard !reduceMotion else { return }
            while !Task.isCancelled {
                try? await Task.sleep(for: .seconds(every))
                guard !Task.isCancelled else { return }
                x = -0.5; visible = true
                withAnimation(.linear(duration: pass)) { x = 1.4 }
                try? await Task.sleep(for: .seconds(pass))
                visible = false
            }
        }
    }
}

public extension View {
    func breathing(low: Double = 0.55, high: Double = 1.0, period: Double = 4.2) -> some View {
        modifier(Breathing(low: low, high: high, period: period))
    }
    func periodicSweep(every: Double = 12, tint: Color = Theme.Color.primary) -> some View {
        modifier(PeriodicSweep(every: every, tint: tint))
    }
}

// MARK: - Component sheet

/// Bracketed truths across the top of a surface, hatched spacers between.
///
/// From the reference sheet. Carries only facts the app already holds — a
/// ribbon that needs new plumbing to fill has missed its own point.
public struct StatusRibbon: View {
    public var items: [String]

    public init(items: [String]) {
        self.items = items
    }

    public var body: some View {
        HStack(spacing: 10) {
            ForEach(Array(items.enumerated()), id: \.offset) { index, item in
                Text("[ \(item.uppercased()) ]")
                    .font(Theme.Font.data(9))
                    .foregroundStyle(Theme.Color.primary)
                    .fixedSize()
                if index < items.count - 1 { Hatch() }
            }
        }
    }
}

/// Diagonal hatching, used as a spacer. Cheap, characterful, holds no data —
/// which is exactly why it can fill space the ribbon does not need.
public struct Hatch: View {
    public init() {}

    public var body: some View {
        Canvas { ctx, size in
            var path = Path()
            var x: CGFloat = -size.height
            while x < size.width + size.height {
                path.move(to: CGPoint(x: x, y: size.height))
                path.addLine(to: CGPoint(x: x + size.height, y: 0))
                x += 5
            }
            ctx.stroke(path, with: .color(Theme.Color.structure), lineWidth: 1)
        }
        .frame(height: 9)
        .frame(maxWidth: .infinity)
        .allowsHitTesting(false)
    }
}

/// A labelled bar meter. `fn03Geo`'s shape.
public struct MeterRow: View {
    public var label: String
    public var value: String
    public var fraction: Double
    public var tint: Color = Theme.Color.primary

    public init(label: String, value: String, fraction: Double, tint: Color = Theme.Color.primary) {
        self.label = label
        self.value = value
        self.fraction = fraction
        self.tint = tint
    }

    public var body: some View {
        HStack(spacing: 9) {
            Text(label.uppercased())
                .font(Theme.Font.data(9))
                .foregroundStyle(Theme.Color.textMuted)
                .frame(width: 104, alignment: .leading)

            GeometryReader { geo in
                ZStack(alignment: .leading) {
                    Rectangle().fill(Theme.Color.panelHi)
                    Rectangle()
                        .fill(tint)
                        .frame(width: geo.size.width * min(1, max(0, fraction)))
                }
            }
            .frame(height: 7)

            Text(value)
                .font(Theme.Font.data(11))
                .foregroundStyle(Theme.Color.text)
                .frame(width: 52, alignment: .trailing)
                .contentTransition(.numericText())
        }
    }
}

/// A ten-cell segmented loader. Reads as an instrument at a glance where a
/// smooth bar reads as a progress dialog.
public struct SegmentedMeter: View {
    public var filled: Int
    public var total: Int = 10
    public var tint: Color = Theme.Color.primary

    public init(filled: Int, total: Int = 10, tint: Color = Theme.Color.primary) {
        self.filled = filled
        self.total = total
        self.tint = tint
    }

    public var body: some View {
        HStack(spacing: 2) {
            ForEach(0..<total, id: \.self) { i in
                Rectangle()
                    .fill(i < filled ? tint : Theme.Color.panelHi)
                    .frame(width: 7, height: 13)
            }
        }
    }
}

/// A table row carrying an ONLINE / OFFLINE state chip. `r4List`'s shape.
public struct StateChip: View {
    public var online: Bool
    public var onLabel: String = "ONLINE"
    public var offLabel: String = "OFFLINE"

    public init(online: Bool, onLabel: String = "ONLINE", offLabel: String = "OFFLINE") {
        self.online = online
        self.onLabel = onLabel
        self.offLabel = offLabel
    }

    public var body: some View {
        Text(online ? onLabel : offLabel)
            .font(Theme.Font.data(8))
            .tracking(0.8)
            .foregroundStyle(online ? Theme.Color.logged : Theme.Color.alert)
            .padding(.horizontal, 6)
            .padding(.vertical, 2)
            .overlay(
                Rectangle().stroke(online ? Theme.Color.logged : Theme.Color.alert,
                                   lineWidth: Theme.Metric.hairline)
            )
    }
}

/// Adherence as a position on a spectrum rather than a count.
///
/// ⚠ **The marker carries the meaning; the gradient is mood.** This app tells
/// `logged` and `missed` apart by treatment rather than hue precisely so state
/// survives greyscale, and a gradient bar is the one place colour would be
/// doing the work alone. Position is readable with no colour at all, and the
/// number stays beside it — remove either and this becomes decoration that
/// lies.
///
/// Red at zero is not a scold. It is the only point on the ramp where Never
/// Miss Twice has already fired; everywhere else is survivable, and the bar
/// says so by being mostly warm.
public struct AdherenceRamp: View {
    public var logged: Int
    public var possible: Int

    public init(logged: Int, possible: Int) {
        self.logged = logged
        self.possible = possible
    }

    private var fraction: Double {
        guard possible > 0 else { return 0 }
        return min(1, max(0, Double(logged) / Double(possible)))
    }

    public var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            GeometryReader { geo in
                ZStack(alignment: .leading) {
                    // ⚠ The red→amber→green gradient was removed 2026-08-18 at
                    // a design decision, and it resolves the objection this
                    // file already carried: a gradient is colour carrying
                    // meaning on its own, which nothing else in this app does.
                    // Track plus fill plus marker says the same thing and
                    // survives greyscale. **Do not reintroduce the ramp.**
                    //
                    // 2026-08-20: the 15pt solid-lime slab was too
                    // intrusive, and the point stands — it was
                    // the loudest block of colour on the screen, saying
                    // something the marker and the number already say. The
                    // track is now a 4pt hairline, the fill a quarter-strength
                    // wash, and the MARKER keeps full contrast because the
                    // marker is the meaning. Nothing semantic changed; the
                    // volume did.
                    Rectangle()
                        .fill(Theme.Color.panelHi)
                        .frame(height: 4)
                        .offset(y: (geo.size.height - 4) / 2)

                    Rectangle()
                        .fill(Theme.Color.logged.opacity(0.30))
                        .frame(width: max(0, geo.size.width * fraction), height: 4)
                        .offset(y: (geo.size.height - 4) / 2)

                    Rectangle()
                        .fill(Theme.Color.text)
                        .frame(width: 3)
                        .shadow(color: Theme.Color.text, radius: 4)
                        .offset(x: geo.size.width * fraction - 1.5)
                        .frame(height: geo.size.height)
                }
            }
            .frame(height: 15)
            .animation(.spring(response: 0.45, dampingFraction: 0.82), value: fraction)

            HStack {
                Text("0 — COLLAPSED")
                Spacer()
                Text("\(possible) — HELD")
            }
            .font(Theme.Font.data(8))
            .foregroundStyle(Theme.Color.textFaint)
        }
    }
}
