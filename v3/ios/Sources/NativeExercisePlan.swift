import Foundation

/// A deterministic, source-backed exercise plan. No learner-facing mode
/// switch: the course selects a response type at each original source item.
/// These are provisional native cadence rules, not an editorial certification
/// of prerequisite mastery or a reason to invent Polish words.
enum NativeExercisePlan {
    static func mode(for lesson: Lesson, sourceIndex: Int) -> PracticeMode {
        guard lesson.items.indices.contains(sourceIndex) else { return .learn }
        if lesson.kind == "reading" { return .read }
        if lesson.kind == "sounds" { return .speak }
        // First contact with a new phrase is always Speak (original MP3,
        // meaning, recording/replay). Later entries alternate with objective
        // Polish -> English matching against original lesson translations.
        if sourceIndex % 3 == 1,
           NativePracticeRules.choices(for: lesson,
                item: lesson.items[sourceIndex], itemIndex: sourceIndex).count == 3 {
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
