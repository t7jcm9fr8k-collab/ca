// Copyright (c) 2026 the HUDKit authors
//
// A one-window tour of every public HUDKit component, on the space backdrop,
// with sample model values built in code. `swift run HUDDemo`.
//
// Nothing here is a reference layout — panels are arranged so each component
// can be seen and poked at, not so the window reads as a product.

import SwiftUI
import AppKit
import Combine
import HUDKit

@main
struct HUDDemoApp: App {
    init() {
        // A SwiftPM executable has no app bundle, so it launches as a
        // background process. Promote it and bring the window forward.
        NSApplication.shared.setActivationPolicy(.regular)
        DispatchQueue.main.async {
            NSApplication.shared.activate(ignoringOtherApps: true)
        }
    }

    var body: some Scene {
        WindowGroup("HUDKit Demo") {
            DemoRoot()
                .frame(minWidth: 1180, minHeight: 780)
                .preferredColorScheme(.dark)
        }
        .windowStyle(.hiddenTitleBar)
    }
}

// MARK: - Sample data

enum DemoData {
    static let calendar = Calendar.current
    static var today: Date { calendar.startOfDay(for: Date()) }

    static func day(_ offset: Int) -> Date {
        calendar.date(byAdding: .day, value: offset, to: today) ?? today
    }

    /// Seven days ending tomorrow, one of each `DayState`, plus a repeat.
    /// Offsets −5…+1 so today is the sixth cell and tomorrow is pending.
    static let weekOffsets: [Int] = [-5, -4, -3, -2, -1, 0, 1]
    static let week: [DayState] = [.done, .rest, .missed, .critical, .done, .late, .pending]

    /// Three kinds on the agenda strip, so every tint appears.
    static func agenda(for offset: Int) -> [ScheduledItem] {
        switch offset {
        case -1: return [ScheduledItem(letter: "C", label: "Ten-minute session", hour: 7, minute: 50, kind: .commitment)]
        case 0:  return [
            ScheduledItem(letter: "C", label: "Ten-minute session", hour: 7, minute: 50, kind: .commitment),
            ScheduledItem(letter: "P", label: "Punch item 5", hour: 12, minute: 0, kind: .punchList),
            ScheduledItem(letter: "E", label: "Standing meeting", hour: 14, minute: 0, kind: .calendar),
        ]
        case 2:  return [ScheduledItem(letter: "E", label: "Review", hour: 9, minute: 30, kind: .calendar)]
        case 3:  return [
            ScheduledItem(letter: "C", label: "Ten-minute session", hour: 7, minute: 50, kind: .commitment),
            ScheduledItem(letter: "P", label: "Punch item 6", hour: 16, minute: 15, kind: .punchList),
        ]
        default: return []
        }
    }

    /// A month laid out Sunday→Saturday with Mon/Wed/Fri scheduled, most
    /// hit, a few missed, and the odd off-day session — the shape the grid is
    /// built to show.
    static func month(offset: Int) -> MonthView {
        let cal = calendar
        let anchor = cal.date(byAdding: .month, value: offset, to: today) ?? today
        let comps = cal.dateComponents([.year, .month], from: anchor)
        let first = cal.date(from: comps) ?? anchor
        let range = cal.range(of: .day, in: .month, for: first) ?? 1..<31
        let leading = cal.component(.weekday, from: first) - 1   // Sunday = 1

        var days: [MonthDay] = []
        for i in 0..<leading {
            days.append(MonthDay(id: "pad-\(i)", date: nil, number: "",
                                 logged: false, scheduled: false,
                                 isToday: false, inFuture: false))
        }

        var logged = 0, possible = 0, bonus = 0
        for n in range {
            guard let date = cal.date(byAdding: .day, value: n - 1, to: first) else { continue }
            let weekday = cal.component(.weekday, from: date)
            let scheduled = [2, 4, 6].contains(weekday)
            let inFuture = date > today
            let isToday = cal.isDate(date, inSameDayAs: today)
            let didLog = !inFuture && (scheduled ? n % 5 != 0 : n % 9 == 0)
            if scheduled && !inFuture {
                possible += 1
                if didLog { logged += 1 }
            } else if didLog {
                bonus += 1
            }
            days.append(MonthDay(id: "d-\(n)", date: date, number: "\(n)",
                                 logged: didLog, scheduled: scheduled,
                                 isToday: isToday, inFuture: inFuture))
        }

        let f = DateFormatter(); f.dateFormat = "MMMM yyyy"
        return MonthView(title: f.string(from: first), days: days,
                         logged: logged, possible: possible, bonus: bonus)
    }

    static let punchItems: [(String, PunchState)] = [
        ("4 — draft the announcement", .done),
        ("5 — photograph the new items", .inProgress),
        ("6 — publish and verify", .todo),
    ]
}

// MARK: - Root

struct DemoRoot: View {
    @ObservedObject private var thermal = ThermalWatch.shared

    @State private var mood: Theme.Mood = .neutral
    @State private var charge: Double = 0.66
    @State private var minutes: Double = 225
    @State private var streak: Double = 12
    @State private var week: [DayState] = DemoData.week
    @State private var monthOffset = 0
    @State private var pinned = true
    @State private var hoveredDay: Date? = nil
    @State private var punch: [PunchState] = DemoData.punchItems.map(\.1)
    @State private var flare = 0
    @State private var impact = 0
    @State private var parallax: Double = 0
    @State private var tone: Motion.Tone = .standard
    @State private var showChip = true
    @State private var sweepOn = true
    @State private var online = true
    @State private var launchLive = false

    private var monthView: MonthView { DemoData.month(offset: monthOffset) }

    var body: some View {
        ZStack {
            Theme.Color.void.ignoresSafeArea()
            SpaceBackdrop(parallax: parallax).ignoresSafeArea()

            HStack(spacing: 0) {
                TickRail()
                    .padding(.leading, 8)
                ScrollView(.vertical) {
                    content
                        .padding(.vertical, 22)
                        .padding(.horizontal, 6)
                }
                TickRail(prefix: "SR", count: 22, highlighted: [5, 12, 20])
                    .padding(.trailing, 8)
            }
        }
        // The launch gate: readouts render 0 until this flips inside
        // withAnimation, then numericText rolls them up.
        .environment(\.launchReadoutsLive, launchLive)
        .onAppear {
            withAnimation(Motion.event.delay(0.7)) { launchLive = true }
        }
    }

    private var content: some View {
        VStack(alignment: .leading, spacing: Theme.Metric.gutter) {
            header

            HStack(alignment: .top, spacing: Theme.Metric.gutter) {
                reactorPanel
                commitmentPanel
                trackerColumn
            }

            HStack(alignment: .top, spacing: Theme.Metric.gutter) {
                monthPanel
                punchPanel
                settingsColumn
            }

            HStack(alignment: .top, spacing: Theme.Metric.gutter) {
                wordmarkPanel
                motionPanel
            }
        }
    }

    // MARK: Header

    private var header: some View {
        HStack(spacing: 14) {
            StatusRibbon(items: ["tracker online", "term t−8", "10 days tracked"])
            HUDButton(title: "⌘1", filled: parallax == 0) { withAnimation { parallax = 0 } }
            HUDButton(title: "⌘2", filled: parallax == 1) { withAnimation { parallax = 1 } }
            HUDButton(title: "⌘3", filled: parallax == 2) { withAnimation { parallax = 2 } }
        }
    }

    // MARK: Panels

    private var reactorPanel: some View {
        HUDPanel(title: "Reactor", enterOrder: 0) {
            VStack(spacing: 12) {
                ZStack {
                    ReactorOrb(mood: mood, charge: charge, diameter: 190)
                    FlareRing(trigger: flare, tint: mood.color)
                }
                .frame(width: 230, height: 230)

                Text(mood.label)
                    .font(Theme.Font.label(11))
                    .tracking(3)
                    .foregroundStyle(mood.color)

                HStack(spacing: 6) {
                    ForEach(Theme.Mood.allCases, id: \.self) { m in
                        Button {
                            withAnimation(Motion.event) { mood = m }
                        } label: {
                            Circle()
                                .fill(m.color)
                                .frame(width: 12, height: 12)
                                .overlay(Circle().stroke(Theme.Color.text.opacity(mood == m ? 0.9 : 0), lineWidth: 1.5))
                        }
                        .buttonStyle(.plain)
                        .help(m.label)
                    }
                }

                HUDButton(title: "Log 10 min", accent: Theme.Color.earned, filled: true) {
                    withAnimation(Motion.event) {
                        minutes += 10
                        charge = min(1, charge + 0.06)
                        flare += 1
                    }
                }
            }
            .frame(maxWidth: .infinity)
        }
        .frame(width: 290)
    }

    private var commitmentPanel: some View {
        HUDPanel(title: "The commitment", accent: Theme.Color.earned, enterOrder: 1) {
            VStack(alignment: .leading, spacing: 14) {
                HStack(alignment: .top, spacing: 28) {
                    Readout(label: "Minutes this week", value: "\(Int(minutes))",
                            suffix: "MIN", roll: minutes)
                    Readout(label: "Streak", value: "\(Int(streak))", suffix: "DAYS",
                            accent: Theme.Color.earned, roll: streak)
                    Readout(label: "Charge", value: "\(Int(charge * 100))", suffix: "%",
                            accent: mood.color, size: 20, roll: charge * 100)
                }

                AdherenceRamp(logged: week.filter { $0 == .done }.count, possible: 5)

                MeterRow(label: "Adherence", value: "\(week.filter { $0 == .done }.count)/5",
                         fraction: Double(week.filter { $0 == .done }.count) / 5)
                MeterRow(label: "Punch list", value: "64%", fraction: 0.64, tint: Theme.Color.earned)

                HStack(spacing: 12) {
                    Text("00:10:00")
                        .font(Theme.Font.readout(19))
                        .foregroundStyle(Theme.Color.text)
                    SegmentedMeter(filled: 5)
                    Spacer()
                    StateChip(online: online)
                        .onTapGesture { online.toggle() }
                }
            }
        }
        .frame(minWidth: 420)
    }

    private var trackerColumn: some View {
        VStack(alignment: .leading, spacing: Theme.Metric.gutter) {
            HUDPanel(title: "Rolling 7-day tracker", enterOrder: 2) {
                HStack(spacing: 8) {
                    ForEach(Array(DemoData.weekOffsets.enumerated()), id: \.offset) { i, offset in
                        DayCell(date: DemoData.day(offset), state: week[i],
                                onToggle: offset <= 0 ? {
                                    withAnimation(Motion.event) {
                                        week[i] = (week[i] == .done) ? .missed : .done
                                    }
                                } : nil)
                    }
                }
            }

            HUDPanel(title: "Agenda", accent: Theme.Color.textMuted, enterOrder: 3) {
                HStack(spacing: 8) {
                    ForEach(-1...5, id: \.self) { offset in
                        AgendaCell(date: DemoData.day(offset),
                                   items: DemoData.agenda(for: offset),
                                   isToday: offset == 0,
                                   isPast: offset < 0)
                    }
                }
                .padding(.bottom, 70)   // room for the hover card below the strip
            }
        }
        .frame(width: 330)
    }

    private var monthPanel: some View {
        VStack(alignment: .leading, spacing: 8) {
            MonthGrid(
                month: monthView,
                pinned: pinned,
                onPrev: { withAnimation { monthOffset -= 1 } },
                onNext: { withAnimation { monthOffset += 1 } },
                onToggle: { _ in },
                onHoverDay: { hoveredDay = $0 },
                irregularDays: [DemoData.day(-3), DemoData.day(4)],
                onSelectDay: { hoveredDay = $0 },
                cellWidth: 34, cellHeight: 30, cellSpacing: 6,
                eventCounts: [DemoData.day(0): 3, DemoData.day(3): 2],
                monthOffset: monthOffset
            )
            HStack {
                HUDPillToggle(title: "Pinned (arrows)", isOn: $pinned)
                    .frame(width: 180)
                Spacer()
                Text(hoveredDay.map { DateFormatter.localizedString(from: $0, dateStyle: .medium, timeStyle: .none) } ?? "—")
                    .font(Theme.Font.data(9))
                    .foregroundStyle(Theme.Color.textMuted)
            }
        }
        .frame(width: 320)
    }

    private var punchPanel: some View {
        HUDPanel(title: "Punch list", accent: Theme.Color.earned, enterOrder: 4) {
            VStack(alignment: .leading, spacing: 10) {
                ForEach(Array(DemoData.punchItems.enumerated()), id: \.offset) { i, item in
                    HStack(spacing: 10) {
                        StateMark(state: punch[i])
                        Text(item.0)
                            .font(Theme.Font.body(12))
                            .foregroundStyle(punch[i] == .done ? Theme.Color.textMuted : Theme.Color.text)
                        Spacer()
                        HUDButton(title: "Advance") {
                            withAnimation(Motion.event) {
                                switch punch[i] {
                                case .todo:       punch[i] = .inProgress
                                case .inProgress: punch[i] = .done; impact += 1
                                case .done:       punch[i] = .todo
                                }
                            }
                        }
                    }
                    .cascadeIn(i)
                }
                Hatch()
                HStack(spacing: 8) {
                    IrregularMark()
                        .fill(Theme.Color.irregular)
                        .frame(width: 9, height: 9)
                    Text("Irregular mark — a corner triangle, never a fill")
                        .font(Theme.Font.data(9))
                        .foregroundStyle(Theme.Color.textMuted)
                }
            }
        }
        .overlay(ImpactFlash(trigger: impact, tint: Theme.Color.earned))
        .frame(minWidth: 380)
    }

    private var settingsColumn: some View {
        HUDPanel(title: "Settings", accent: Theme.Color.alert, enterOrder: 5) {
            VStack(alignment: .leading, spacing: 10) {
                HUDPillToggle(title: "LOW HEAT", isOn: $thermal.lowHeat, accent: Theme.Color.alert)
                HUDPillToggle(title: "Periodic sweep", isOn: $sweepOn)
                Text("Thermal level \(thermal.level) · sky and orb freeze at 2")
                    .font(Theme.Font.data(9))
                    .foregroundStyle(Theme.Color.textFaint)
                Text("Type scale \(String(format: "%.2f", Theme.Font.scale)) (UserDefaults \"type.scale\")")
                    .font(Theme.Font.data(9))
                    .foregroundStyle(Theme.Color.textFaint)
            }
        }
        .frame(width: 300)
    }

    private var wordmarkPanel: some View {
        HUDPanel(title: "Block letters", accent: Theme.Color.textMuted, enterOrder: 6) {
            HStack(alignment: .top, spacing: 26) {
                BlockLetters(lines: ["SYSTEM", "READY"], cell: 6)
                BlockLetters(lines: ["REACTOR"], cell: 4, depthRatio: 1.4,
                             base: Theme.Color.earned)
                Spacer()
            }
        }
        .frame(minWidth: 480)
    }

    private var motionPanel: some View {
        HUDPanel(title: "Motion grammar", enterOrder: 7) {
            VStack(alignment: .leading, spacing: 12) {
                HStack(spacing: 8) {
                    HUDButton(title: "Deliberate", filled: tone == .deliberate) { tone = .deliberate }
                    HUDButton(title: "Standard", filled: tone == .standard) { tone = .standard }
                    HUDButton(title: "Fast", filled: tone == .fast) { tone = .fast }
                    Spacer()
                    HUDButton(title: showChip ? "Leave" : "Arrive", accent: Theme.Color.earned) {
                        withAnimation { showChip.toggle() }
                    }
                }

                ZStack(alignment: .leading) {
                    Rectangle()
                        .stroke(Theme.Color.structure.opacity(0.5),
                                style: StrokeStyle(lineWidth: 1, dash: [4, 3]))
                        .frame(height: 44)
                    if showChip {
                        Text("DESTINATION")
                            .font(Theme.Font.data(9))
                            .tracking(1.4)
                            .foregroundStyle(Theme.Color.primary)
                            .padding(.horizontal, 12)
                            .padding(.vertical, 8)
                            .background(CutCorner(cut: 5).fill(Theme.Color.primary.opacity(0.16)))
                            .overlay(CutCorner(cut: 5).stroke(Theme.Color.primary, lineWidth: 1))
                            .padding(.leading, 10)
                            .transition(Motion.destinationTransition(tone))
                    }
                }

                HStack(spacing: 14) {
                    Circle()
                        .fill(Theme.Color.primary)
                        .frame(width: 8, height: 8)
                        .breathing()
                    Text("breathing() — the one repeating animation allowed")
                        .font(Theme.Font.data(9))
                        .foregroundStyle(Theme.Color.textMuted)
                }

                Text("Flash ledger: last grant \(String(format: "%.1f", FlashLedger.lastGrant))s uptime · ceiling 3/s · budget 2")
                    .font(Theme.Font.data(9))
                    .foregroundStyle(Theme.Color.textFaint)
            }
        }
        .modifier(PeriodicSweep(every: sweepOn ? 6 : 3600, pass: 1.2, tint: Theme.Color.primary))
        .frame(minWidth: 480)
    }
}
