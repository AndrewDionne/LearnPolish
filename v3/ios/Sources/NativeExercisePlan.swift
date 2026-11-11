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
            let mode = mode(for: lesson, item: item)
            return (records[mode.rawValue + ":" + item.id]?.attempts ?? 0) == 0
        } ?? 0
    }
}
