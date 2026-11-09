import Foundation

/// Source-bound, append-only metadata for a *real* card attempt. This is NOT
/// an Azure assessment, personal XP award or family activity receipt.
struct NativePracticeEvent: Codable, Identifiable, Equatable {
    enum Outcome: String, Codable {
        case understood
        case needsPractice
        case recorded
    }

    let id: UUID
    let actorID: UUID
    let itemID: String
    let mode: PracticeMode
    let at: Date
    let outcome: Outcome
    /// Added after journal v1 adoption; nil means the original recorded
    /// attempt predates region snapshots and MUST NOT be assigned a region
    /// during a future cross-device merge.
    let regionID: String?

    init(id: UUID, actorID: UUID, itemID: String, mode: PracticeMode,
         at: Date, outcome: Outcome, regionID: String? = nil) {
        self.id = id
        self.actorID = actorID
        self.itemID = itemID
        self.mode = mode
        self.at = at
        self.outcome = outcome
        self.regionID = regionID
    }
}

struct NativePracticeJournal: Codable {
    static let currentSchema = 1
    static let maximumEvents = 50_000

    let schemaVersion: Int
    /// Distinct anonymous local resets create distinct generations. Linking
    /// two devices must share an epoch only after explicit owner consent.
    let epochID: UUID
    let startedAt: Date
    let hasLegacyHistory: Bool
    var events: [NativePracticeEvent]

    init(epochID: UUID = UUID(), startedAt: Date = Date(),
         hasLegacyHistory: Bool, events: [NativePracticeEvent] = []) {
        schemaVersion = Self.currentSchema
        self.epochID = epochID
        self.startedAt = startedAt
        self.hasLegacyHistory = hasLegacyHistory
        self.events = events
    }

    mutating func append(_ event: NativePracticeEvent) throws {
        guard events.count < Self.maximumEvents,
              !events.contains(where: { $0.id == event.id }) else {
            throw NativePracticeJournalError.capacityOrDuplicate
        }
        events.append(event)
    }

    func validateSource(lessons: [Lesson],
                        regions: [PolandRegion]? = nil) throws {
        guard schemaVersion == Self.currentSchema,
              events.count <= Self.maximumEvents else {
            throw NativePracticeJournalError.invalidSource
        }
        let byItem = Dictionary(uniqueKeysWithValues: lessons.flatMap { lesson in
            lesson.items.map { ($0.id, (lesson, $0)) }
        })
        // Every new region ID must be checked against the source-backed 16
        // regions whenever those resources are available. Older events with
        // a nil snapshot remain valid but cannot project a complete map.
        let permittedRegions = regions.map { Set($0.map(\.id)) }
        var identities = Set<UUID>()
        for event in events {
            guard identities.insert(event.id).inserted,
                  event.itemID.count > 0, event.itemID.count <= 180,
                  event.at.isFiniteDate,
                  event.at >= startedAt.addingTimeInterval(-1),
                  event.regionID.map { !$0.isEmpty && $0.count <= 60 } ?? true,
                  event.regionID.map { region in
                      permittedRegions?.contains(region) ?? true
                  } ?? true,
                  let (lesson, item) = byItem[event.itemID],
                  lesson.availableModes.contains(event.mode),
                  (event.mode != .listen ||
                    (item.audio != nil && item.referenceReview != "practice_only")),
                  (event.mode == .speak) == (event.outcome == .recorded) else {
                throw NativePracticeJournalError.invalidSource
            }
        }
    }

    /// Deterministic, commutative and idempotent *candidate* merge. This is
    /// deliberately not applied to LocalLearner, XP or CloudKit. Divergent
    /// epochs, legacy aggregate history and conflicted UUIDs fail closed.
    static func mergeCandidate(_ first: Self, _ second: Self,
                               lessons: [Lesson]) throws -> Self {
        try first.validateSource(lessons: lessons)
        try second.validateSource(lessons: lessons)
        guard first.epochID == second.epochID,
              first.startedAt == second.startedAt,
              !first.hasLegacyHistory, !second.hasLegacyHistory else {
            throw NativePracticeJournalError.unlinkedOrLegacy
        }
        var byID: [UUID: NativePracticeEvent] = [:]
        for event in first.events + second.events {
            if let prior = byID[event.id], prior != event {
                throw NativePracticeJournalError.conflictingEvent
            }
            byID[event.id] = event
        }
        guard byID.count <= Self.maximumEvents else {
            throw NativePracticeJournalError.capacityOrDuplicate
        }
        let ordered = byID.values.sorted(by: eventOrder)
        let result = NativePracticeJournal(epochID: first.epochID,
                                          startedAt: first.startedAt,
                                          hasLegacyHistory: false,
                                          events: ordered)
        try result.validateSource(lessons: lessons)
        return result
    }

    /// Projection for a journal with complete post-creation history ONLY.
    /// Does not merge older aggregates or mutate XP; it is a pure baseline
    /// for future authorized private two-device synchronization.
    func projectedRecords(lessons: [Lesson]) throws -> [String: PracticeRecord] {
        try validateSource(lessons: lessons)
        guard !hasLegacyHistory else {
            throw NativePracticeJournalError.unlinkedOrLegacy
        }
        var records: [String: PracticeRecord] = [:]
        for event in events.sorted(by: Self.eventOrder) {
            let key = event.mode.rawValue + ":" + event.itemID
            var record = records[key] ?? PracticeRecord()
            record.attempts += 1
            record.lastAttempt = event.at
            if event.outcome == .understood { record.completed += 1 }
            if event.mode == .learn {
                if event.outcome == .understood {
                    record.reviewLevel = min(record.reviewLevel + 1, 7)
                    let days = [1, 3, 7, 14, 30, 60, 90][record.reviewLevel - 1]
                    record.nextReview = event.at.addingTimeInterval(TimeInterval(days) * 86_400)
                } else if event.outcome == .needsPractice {
                    record.reviewLevel = 0
                    record.nextReview = event.at
                }
            }
            records[key] = record
        }
        return records
    }

    private static func eventOrder(_ a: NativePracticeEvent,
                                   _ b: NativePracticeEvent) -> Bool {
        if a.at != b.at { return a.at < b.at }
        return a.id.uuidString < b.id.uuidString
    }
}

private extension Date {
    var isFiniteDate: Bool { timeIntervalSince1970.isFinite }
}

enum NativePracticeJournalError: LocalizedError, Equatable {
    case invalidSource, capacityOrDuplicate, unlinkedOrLegacy, conflictingEvent

    var errorDescription: String? {
        switch self {
        case .invalidSource:
            return "Practice history does not match the verified Polish lesson catalog."
        case .capacityOrDuplicate:
            return "The bounded practice journal cannot safely add this event."
        case .unlinkedOrLegacy:
            return "These histories cannot be combined without an explicit account link and legacy review."
        case .conflictingEvent:
            return "The same practice event has conflicting data on two devices."
        }
    }
}
