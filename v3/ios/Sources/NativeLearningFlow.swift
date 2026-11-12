import Foundation

// Exact native projections of the approved V2 progression and item-selection
// contracts. No invented journey placements, mastery, or learner tiers.

struct CoreJourneyManifest: Decodable {
    let schemaVersion: Int
    let editorialStatus: String
    let placements: [JourneyPlacement]
}

struct JourneyPlacement: Decodable {
    let lessonId: String
    let journey: Int
    let position: String
    let order: Int

    var rank: Int {
        switch position {
        case "beginning": return 0
        case "middle": return 1
        default: return 2
        }
    }
}

struct CoreJourney {
    let ordered: [Lesson]
    let explore: [Lesson]
    let placements: [String: JourneyPlacement]

    init(lessons: [Lesson], bundle: Bundle = .main) throws {
        guard let url = bundle.url(forResource: "core-journey", withExtension: "json",
                                   subdirectory: "generated") else {
            throw CatalogLoadError.invalid("Missing V2 core journey source")
        }
        let data = try JSONDecoder().decode(CoreJourneyManifest.self, from: Data(contentsOf: url))
        guard data.schemaVersion == 1,
              data.editorialStatus == "source-mapped-pilot_not_native-audio-certified",
              data.placements.count == 21 else {
            throw CatalogLoadError.invalid("Journey source inventory or editorial status changed")
        }
        let byLesson = Dictionary(uniqueKeysWithValues: lessons.map { ($0.id, $0) })
        var seen = Set<String>()
        var positions = Set<String>()
        for placement in data.placements {
            guard let lesson = byLesson[placement.lessonId],
                  lesson.source != "personal",
                  lesson.curriculum?.stage != "practice",
                  (1...3).contains(placement.journey),
                  ["beginning", "middle", "end"].contains(placement.position),
                  placement.order >= 1,
                  seen.insert(placement.lessonId).inserted,
                  positions.insert("\(placement.journey):\(placement.position):\(placement.order)").inserted else {
                throw CatalogLoadError.invalid("Duplicated, invalid or unsupported journey placement")
            }
        }
        for journey in 1...3 {
            for position in ["beginning", "middle", "end"] {
                let sequence = data.placements.filter {
                    $0.journey == journey && $0.position == position
                }.map(\.order).sorted()
                guard sequence.isEmpty || sequence == Array(1...sequence.count) else {
                    throw CatalogLoadError.invalid("Journey step order is not contiguous")
                }
            }
        }
        placements = Dictionary(uniqueKeysWithValues: data.placements.map { ($0.lessonId, $0) })
        ordered = data.placements.sorted {
            if $0.journey != $1.journey { return $0.journey < $1.journey }
            if $0.rank != $1.rank { return $0.rank < $1.rank }
            return $0.order < $1.order
        }.compactMap { byLesson[$0.lessonId] }
        explore = lessons.filter { !seen.contains($0.id) && $0.source != "personal" }
            .sorted { $0.title.localizedCaseInsensitiveCompare($1.title) == .orderedAscending }
    }

    func next(after lessonID: String) -> Lesson? {
        guard let position = ordered.firstIndex(where: { $0.id == lessonID }),
              ordered.indices.contains(position + 1) else { return nil }
        return ordered[position + 1]
    }

    func sectionTitle(for lesson: Lesson) -> String? {
        guard let placement = placements[lesson.id] else { return nil }
        return "Journey \(placement.journey)"
    }
}

struct PracticeSection: Identifiable {
    let id: Int
    let title: String
    let items: [LessonItem]
}

enum NativePracticeRules {
    static func items(for lesson: Lesson, mode: PracticeMode) -> [LessonItem] {
        switch mode {
        case .listen:
            return lesson.items.filter { $0.audio != nil && $0.referenceReview != "practice_only" }
        default:
            return lesson.items
        }
    }

    static func sections(for lesson: Lesson, mode: PracticeMode) -> [PracticeSection] {
        let available = items(for: lesson, mode: mode)
        guard lesson.id == "numbers_1-20", lesson.kind == "vocabulary",
              lesson.items.count == 20,
              lesson.items.enumerated().allSatisfy({ index, item in
                  item.id == "numbers_1-20:\(index)" && item.audio != nil
              }),
              lesson.items[0].polish == "Jeden",
              lesson.items[9].polish == "Dziesięć",
              lesson.items[10].polish == "Jedenaście",
              lesson.items[19].polish == "Dwadzieścia" else {
            return [PracticeSection(id: 0, title: lesson.title, items: available)]
        }
        let firstIDs = Set(lesson.items.prefix(10).map(\.id))
        let secondIDs = Set(lesson.items.suffix(10).map(\.id))
        return [
            PracticeSection(id: 0, title: "Numbers 1–10",
                            items: available.filter { firstIDs.contains($0.id) }),
            PracticeSection(id: 1, title: "Numbers 11–20",
                            items: available.filter { secondIDs.contains($0.id) })
        ]
    }

    static func choices(for lesson: Lesson, item: LessonItem, itemIndex: Int,
                        reading: Bool = false) -> [String] {
        if reading && item.comprehension == nil { return [] }
        if let authored = item.comprehension { return authored.options }
        let sources = items(for: lesson, mode: .listen)
        var seen = Set<String>()
        let alternatives = sources.compactMap { entry -> String? in
            guard entry.english != item.english, seen.insert(entry.english).inserted else {
                return nil
            }
            return entry.english
        }
        guard !alternatives.isEmpty else { return [] }
        let offset = ((itemIndex % alternatives.count) + alternatives.count) % alternatives.count
        let rotated = Array(alternatives[offset...]) + Array(alternatives[..<offset])
        var choices = Array(rotated.prefix(2))
        let slot = ((itemIndex % (choices.count + 1)) + (choices.count + 1)) % (choices.count + 1)
        choices.insert(item.english, at: slot)
        return choices
    }

    static func firstUnvisitedBatch(for lesson: Lesson, progress: [String: PracticeRecord]) -> Int {
        let sections = sections(for: lesson, mode: .learn)
        guard sections.count > 1 else { return 0 }
        guard let next = lesson.items.first(where: {
            (progress["learn:" + $0.id]?.attempts ?? 0) == 0
        }) else { return 0 }
        return sections.firstIndex(where: { section in
            section.items.contains(where: { $0.id == next.id })
        }) ?? 0
    }

    static func nextUnseenIndex(items: [LessonItem], progress: [String: PracticeRecord],
                                mode: PracticeMode) -> Int {
        items.firstIndex { (progress[mode.rawValue + ":" + $0.id]?.attempts ?? 0) == 0 } ?? 0
    }
}

 
/// Native answer submission must persist the actual practice journal, review
/// record and daily XP atomically before the UI marks an option answered or
/// moves to another card. A failed write keeps the current card actionable.
/// This is separate from the explicit Skip/Next navigation (no reward).
@MainActor
enum NativePracticeSubmission {
    @discardableResult
    static func commit(store: LocalLearningStore,
                       item: LessonItem, mode: PracticeMode,
                       understood: Bool?,
                       evidence: NativePracticeEvent.Evidence? = nil,
                       onSaved: () -> Void) -> Bool {
        guard store.recordAttempt(item: item, mode: mode,
                                  understood: understood,
                                  evidence: evidence) else { return false }
        onSaved()
        return true
    }
}
