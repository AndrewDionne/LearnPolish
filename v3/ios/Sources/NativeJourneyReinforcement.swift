import Foundation

/// A small optional interleaved Learn exercise using only original recorded
/// words ALREADY attempted in preceding Journey 1 chapters. It is NOT a new
/// lesson, scheduled due card, proficiency certification or source duplicate.
struct NativeJourneyReinforcementCard: Identifiable {
    let lesson: Lesson
    let item: LessonItem
    let chapterID: String
    let options: [String]

    var id: String { item.id }
}

/// Cross-chapter retrieval uses only actual saved source-item attempts.
/// A learner cannot unlock an answer by browsing, skipping or playing audio.
/// It is independent of the V2 due schedule: reviewed answers still commit
/// to the same original Learn item and thereby enter the existing schedule.
enum NativeJourneyReinforcementQueue {
    static let batchLimit = 6

    static func snapshot(journey: NativeUnifiedJourney,
                         guided: [GuidedFoundationStep],
                         core: CoreJourney,
                         lessons: [Lesson],
                         records: [String: PracticeRecord],
                         limit: Int = batchLimit) -> [NativeJourneyReinforcementCard] {
        guard limit > 0 else { return [] }
        let currentIndex = journey.chapters.firstIndex { chapter in
            chapter.nodes.contains { node in
                !journey.progress(node, guided: guided, core: core,
                                  records: records).complete
            }
        } ?? journey.chapters.count
        guard currentIndex > 0 else { return [] }

        // The original source-ID lookup is authoritative; no clone item ID,
        // synthetic Polish, English option or audio link can enter the pool.
        let byID: [String: (Lesson, LessonItem)] = Dictionary(
            uniqueKeysWithValues: lessons.flatMap { lesson in
                lesson.items.map { ($0.id, (lesson, $0)) }
            })
        var seen = Set<String>()
        var eligible: [(lesson: Lesson, item: LessonItem, chapterID: String,
                        record: PracticeRecord?)] = []
        for chapter in journey.chapters.prefix(currentIndex) {
            for node in chapter.nodes {
                for id in node.sourceIDs {
                    guard seen.insert(id).inserted,
                          let (lesson, item) = byID[id],
                          lesson.kind == "vocabulary",
                          item.audio != nil, item.referenceReview != "practice_only",
                          NativeExercisePlan.introduced(item, records: records)
                    else { continue }
                    eligible.append((lesson, item, chapter.id, records["learn:" + id]))
                }
            }
        }
        let availableMeanings = Set(eligible.map { $0.item.english })
        guard availableMeanings.count >= 3 else { return [] }

        // Stable priority: words without any objective match first, then
        // objectively missed words, then older attempted words. The saved
        // attempt timestamps are data, not an invented review-due date.
        let ranked = eligible.enumerated().sorted { a, b in
            let aObjective = (a.element.record?.objectiveAttempts ?? 0) > 0
            let bObjective = (b.element.record?.objectiveAttempts ?? 0) > 0
            if aObjective != bObjective { return !aObjective }
            let aMissed = (a.element.record?.objectiveCorrect ?? 0) <
                          (a.element.record?.objectiveAttempts ?? 0)
            let bMissed = (b.element.record?.objectiveCorrect ?? 0) <
                          (b.element.record?.objectiveAttempts ?? 0)
            if aMissed != bMissed { return aMissed }
            let aTime = a.element.record?.lastAttempt ?? .distantPast
            let bTime = b.element.record?.lastAttempt ?? .distantPast
            return aTime == bTime ? a.offset < b.offset : aTime < bTime
        }

        var cards: [NativeJourneyReinforcementCard] = []
        for entry in ranked {
            let target = entry.element.item.english
            var meanings = Set([target])
            let distractors = eligible.compactMap { candidate -> String? in
                guard meanings.insert(candidate.item.english).inserted
                else { return nil }
                return candidate.item.english
            }
            guard distractors.count >= 2 else { continue }
            let offset = entry.offset % distractors.count
            let rotated = Array(distractors[offset...]) + Array(distractors[..<offset])
            var options = Array(rotated.prefix(2))
            options.insert(target, at: entry.offset % 3)
            cards.append(NativeJourneyReinforcementCard(
                lesson: entry.element.lesson, item: entry.element.item,
                chapterID: entry.element.chapterID, options: options))
            if cards.count == min(limit, batchLimit) { break }
        }
        return cards
    }
}
