import Foundation

/// A deterministic, source-backed exercise plan. No learner-facing mode
/// switch: the course selects a response type at each original source item.
/// These are provisional native cadence rules, not an editorial certification
/// of prerequisite mastery or a reason to invent Polish words.
enum NativeExercisePlan {
    /// Only use ORIGINAL English translations of earlier source cards as
    /// distractors. Selecting a meaning from a future lesson card was a
    /// prerequisite leak in the provisional UX-02A cadence. The first two
    /// source cards cannot support a 3-choice matching question and remain
    /// Speak introductions. This is source-order safety, not mastery proof.
    static func choices(for lesson: Lesson, itemIndex: Int) -> [String] {
        guard lesson.items.indices.contains(itemIndex) else { return [] }
        let target = lesson.items[itemIndex].english
        var seen = Set([target])
        let earlier = lesson.items.prefix(itemIndex).compactMap { item -> String? in
            guard seen.insert(item.english).inserted else { return nil }
            return item.english
        }
        guard earlier.count >= 2 else { return [] }
        let offset = itemIndex % earlier.count
        let options = Array(earlier[offset...]) +
            Array(earlier[..<offset])
        var results = Array(options.prefix(2))
        results.insert(target, at: itemIndex % 3)
        return results
    }

    /// A first-contact phrase must be introduced before it can be tested.
    /// Historical Learn attempts count as prior exposure (not as a new
    /// objective quiz score); this preserves earlier local learner progress.
    static func introduced(_ item: LessonItem,
                           records: [String: PracticeRecord]) -> Bool {
        (records["speak:" + item.id]?.attempts ?? 0) > 0 ||
        (records["learn:" + item.id]?.attempts ?? 0) > 0
    }

    /// Runtime matching is stricter than the authored text-order audit:
    /// every distractor must have been *actually practised*, not merely
    /// viewed or passed over using Skip. The correct phrase must already
    /// have had an introductory attempt too.
    static func readyChoices(for lesson: Lesson, itemIndex: Int,
                             records: [String: PracticeRecord]) -> [String] {
        guard lesson.kind == "vocabulary",
              lesson.items.indices.contains(itemIndex),
              introduced(lesson.items[itemIndex], records: records)
        else { return [] }
        let target = lesson.items[itemIndex].english
        var seen = Set([target])
        let earlier = lesson.items.prefix(itemIndex).compactMap { item -> String? in
            guard introduced(item, records: records),
                  seen.insert(item.english).inserted else { return nil }
            return item.english
        }
        guard earlier.count >= 2 else { return [] }
        let offset = itemIndex % earlier.count
        let rotated = Array(earlier[offset...]) + Array(earlier[..<offset])
        var results = Array(rotated.prefix(2))
        results.insert(target, at: itemIndex % 3)
        return results
    }

    /// Scheduled recall can reuse *any* previously practised original
    /// source meaning (including a later source index), but must not expose
    /// an unintroduced card as a distractor. With fewer than two distinct
    /// practised alternatives, the UI falls back to a self-rated flip card
    /// rather than fabricating a graded answer.
    static func reviewChoices(for lesson: Lesson, itemIndex: Int,
                              records: [String: PracticeRecord]) -> [String] {
        guard lesson.items.indices.contains(itemIndex),
              introduced(lesson.items[itemIndex], records: records)
        else { return [] }
        let target = lesson.items[itemIndex].english
        var seen = Set([target])
        let known = lesson.items.compactMap { item -> String? in
            guard introduced(item, records: records),
                  seen.insert(item.english).inserted else { return nil }
            return item.english
        }
        guard known.count >= 2 else { return [] }
        let offset = itemIndex % known.count
        let rotated = Array(known[offset...]) + Array(known[..<offset])
        var result = Array(rotated.prefix(2))
        result.insert(target, at: itemIndex % 3)
        return result
    }

    /// What the learner actually sees. The source cadence expresses where
    /// matching can occur, but never bypasses the first-contact requirement.
    static func mode(for lesson: Lesson, sourceIndex: Int,
                     records: [String: PracticeRecord]) -> PracticeMode {
        let proposed = mode(for: lesson, sourceIndex: sourceIndex)
        guard proposed == .learn else { return proposed }
        return readyChoices(for: lesson, itemIndex: sourceIndex,
                            records: records).count == 3 ? .learn : .speak
    }

    static func mode(for lesson: Lesson, item: LessonItem,
                     records: [String: PracticeRecord]) -> PracticeMode {
        guard let sourceIndex = lesson.items.firstIndex(where: { $0.id == item.id }) else {
            return lesson.kind == "reading" ? .read : .speak
        }
        return mode(for: lesson, sourceIndex: sourceIndex, records: records)
    }

    static func mode(for lesson: Lesson, sourceIndex: Int) -> PracticeMode {
        guard lesson.items.indices.contains(sourceIndex) else { return .learn }
        if lesson.kind == "reading" { return .read }
        if lesson.kind == "sounds" { return .speak }
        // First contact with a new phrase is always Speak (original MP3,
        // meaning, recording/replay). Later entries alternate with objective
        // Polish -> English matching against original lesson translations.
        if sourceIndex % 3 == 1,
           choices(for: lesson, itemIndex: sourceIndex).count == 3 {
            return .learn
        }
        return lesson.availableModes.contains(.speak) ? .speak : .learn
    }

    static func mode(for lesson: Lesson, item: LessonItem) -> PracticeMode {
        guard let index = lesson.items.firstIndex(where: { $0.id == item.id }) else {
            return lesson.kind == "reading" ? .read : .speak
        }
        return mode(for: lesson, sourceIndex: index)
    }

    static func nextUnattemptedIndex(items: [LessonItem], lesson: Lesson,
                                      records: [String: PracticeRecord]) -> Int {
        items.firstIndex { item in
            if lesson.kind == "vocabulary" {
                // Find first genuinely unintroduced original word. A planned
                // Learn position never hides a previously saved Speak attempt.
                return !introduced(item, records: records)
            }
            let mode = mode(for: lesson, item: item)
            return (records[mode.rawValue + ":" + item.id]?.attempts ?? 0) == 0
        } ?? 0
    }

    static func firstUnvisitedBatch(for lesson: Lesson,
                                    records: [String: PracticeRecord]) -> Int {
        let sections = NativePracticeRules.sections(for: lesson, mode: .learn)
        guard sections.count > 1 else { return 0 }
        return sections.firstIndex { section in
            section.items.contains { item in
                !introduced(item, records: records)
            }
        } ?? 0
    }
}
