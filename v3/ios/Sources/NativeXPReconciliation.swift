import Foundation

/// A speculative award calculated from COMPLETE, original-source-verified
/// journal events. No award in this file changes the phone's local XP,
/// regional expedition, family server balance, or CloudKit.
struct NativeUTCAward: Equatable {
    let eventID: UUID
    let actorID: UUID
    let itemID: String
    let mode: PracticeMode
    let at: Date
    let utcDay: String
    let tier: Int
    let effortXP: Int
    let expeditionXP: Int
}

struct NativeXPReconciliationCandidate {
    let epochID: UUID
    let awards: [NativeUTCAward]

    var totalEffortXP: Int { awards.reduce(0) { $0 + $1.effortXP } }
    var totalExpeditionXP: Int { awards.reduce(0) { $0 + $1.expeditionXP } }

    /// v1 practice events have NO per-attempt region snapshot. This candidate
    /// MUST NOT be applied to a Poland map: region assignment, goals and
    /// selected-region state cannot be reconstructed from the source log.
    var requiresRegionReconciliation: Bool { true }
}

enum NativeXPReconciliation {
    private struct ItemMode: Hashable {
        let itemID: String
        let mode: PracticeMode
    }
    private struct DayKey: Hashable {
        let itemMode: ItemMode
        let day: String
    }

    private static let tierXP = [10, 14, 19, 26, 35]
    private static let maximumAwards = 20_000

    /// Deliberately UTC rather than Calendar.current, which would otherwise
    /// credit simultaneous phone activity differently across time zones.
    static func utcDay(_ date: Date) -> String {
        var utc = Calendar(identifier: .gregorian)
        utc.timeZone = TimeZone(secondsFromGMT: 0)!
        let parts = utc.dateComponents([.year, .month, .day], from: date)
        return String(format: "%04d-%02d-%02d",
                      parts.year ?? 0, parts.month ?? 0, parts.day ?? 0)
    }

    /// This creates a read-only candidate for the complete event history.
    /// Never sum device-local XP records or treat two same-day events as two
    /// awards. The earliest timestamp wins; UUID gives deterministic ties.
    static func candidate(journal: NativePracticeJournal,
                          lessons: [Lesson]) throws -> NativeXPReconciliationCandidate {
        try journal.validateSource(lessons: lessons)
        guard !journal.hasLegacyHistory else {
            throw NativePracticeJournalError.unlinkedOrLegacy
        }

        let lessonByItem = Dictionary(uniqueKeysWithValues: lessons.flatMap { lesson in
            lesson.items.map { ($0.id, lesson) }
        })
        var rewardedDays = Set<DayKey>()
        var repeats: [ItemMode: Int] = [:]
        var awards: [NativeUTCAward] = []
        let ordered = journal.events.sorted {
            $0.at == $1.at ? $0.id.uuidString < $1.id.uuidString : $0.at < $1.at
        }
        for event in ordered {
            guard let lesson = lessonByItem[event.itemID] else {
                throw NativePracticeJournalError.invalidSource
            }
            let itemMode = ItemMode(itemID: event.itemID, mode: event.mode)
            let dateKey = DayKey(itemMode: itemMode, day: utcDay(event.at))
            guard rewardedDays.insert(dateKey).inserted else { continue }

            guard awards.count < maximumAwards else {
                throw NativePracticeJournalError.capacityOrDuplicate
            }
            let tier = lesson.difficultyTier.flatMap {
                (1...5).contains($0) ? $0 : nil
            } ?? 1
            let baseXP = tierXP[tier - 1]
            let rewardedBefore = repeats[itemMode, default: 0]
            let expeditionXP: Int
            switch rewardedBefore {
            case 0: expeditionXP = baseXP
            case 1: expeditionXP = Int((Double(baseXP) / 2).rounded())
            default: expeditionXP = 0
            }
            repeats[itemMode] = rewardedBefore + 1
            awards.append(NativeUTCAward(
                eventID: event.id, actorID: event.actorID,
                itemID: event.itemID, mode: event.mode, at: event.at,
                utcDay: dateKey.day, tier: tier,
                effortXP: baseXP, expeditionXP: expeditionXP))
        }
        return NativeXPReconciliationCandidate(
            epochID: journal.epochID, awards: awards)
    }

    /// Strict identity/legacy/conflict guard is the journal merger's job.
    /// Nothing in this method mutates LocalLearner or claims CloudKit success.
    static func mergedCandidate(_ first: NativePracticeJournal,
                                _ second: NativePracticeJournal,
                                lessons: [Lesson]) throws -> NativeXPReconciliationCandidate {
        let merged = try NativePracticeJournal.mergeCandidate(
            first, second, lessons: lessons)
        return try candidate(journal: merged, lessons: lessons)
    }
}
