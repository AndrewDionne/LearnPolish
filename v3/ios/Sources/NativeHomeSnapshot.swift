import Foundation

/// All Home numbers and recent activity come from the device's own persisted
/// original-source practice journal. This is NOT a family/group score and
/// does not infer assessments or mastery from navigation.
struct NativeHomeActivity: Identifiable {
    let id: UUID
    let polish: String
    let mode: PracticeMode
    let at: Date
}

@MainActor enum NativeHomeSnapshot {
    static func recent(learner: LocalLearningStore,
                       limit: Int = 3) -> [NativeHomeActivity] {
        guard limit > 0, let journal = learner.profile.practiceJournal else { return [] }
        let original = Dictionary(uniqueKeysWithValues: learner.lessons.flatMap {
            $0.items.map { ($0.id, $0.polish) }
        })
        return journal.events
            .sorted {
                if $0.at != $1.at { return $0.at > $1.at }
                if $0.actorSequence != $1.actorSequence {
                    return ($0.actorSequence ?? 0) > ($1.actorSequence ?? 0)
                }
                return $0.id.uuidString < $1.id.uuidString
            }
            .prefix(min(limit, 10))
            .compactMap { event in
                guard let polish = original[event.itemID] else { return nil }
                return NativeHomeActivity(id: event.id, polish: polish,
                                          mode: event.mode, at: event.at)
            }
    }

    static func todayAttempts(learner: LocalLearningStore,
                              now: Date = Date(),
                              calendar: Calendar = .current) -> Int? {
        guard let journal = learner.profile.practiceJournal else { return nil }
        return journal.events.filter { calendar.isDate($0.at, inSameDayAs: now) }.count
    }

    static func todayXP(learner: LocalLearningStore,
                        now: Date = Date(),
                        calendar: Calendar = .current) -> Int {
        // Personal effort XP is not shared team XP.
        learner.expedition.events.filter {
            calendar.isDate($0.at, inSameDayAs: now)
        }.reduce(0) { $0 + $1.xp }
    }
}
