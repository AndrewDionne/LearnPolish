import Foundation

/// Source-constrained guided cadence. Each first-words group introduces its
/// ORIGINAL Polish phrase and audio through Speak before an optional recap.
/// Only 3+ distinct source English meanings justify 3-choice matching; the
/// opening 2-word group never fabricates distractors.
enum GuidedExercisePhase: String, Codable {
    case introduce
    case recap
}

enum GuidedExercisePlan {
    static func choices(for step: GuidedFoundationStep, index: Int) -> [String] {
        guard step.items.indices.contains(index) else { return [] }
        let target = step.items[index].english
        var seen = Set([target])
        let alternatives = step.items.compactMap { item -> String? in
            guard seen.insert(item.english).inserted else { return nil }
            return item.english
        }
        guard alternatives.count >= 2 else { return [] }
        let offset = index % alternatives.count
        let rotated = Array(alternatives[offset...]) + Array(alternatives[..<offset])
        let others = Array(rotated.prefix(2))
        let slot = index % 3
        var result = others
        result.insert(target, at: slot)
        return result
    }

    static func hasRecap(_ step: GuidedFoundationStep) -> Bool {
        step.items.indices.allSatisfy { choices(for: step, index: $0).count == 3 }
    }

    /// Original V3 guided learning recorded self-rated Learn only.
    /// Preserve that history as prior introduction, without converting it
    /// into objective quiz evidence. New Speak attempts are distinct records.
    static func introduced(_ item: GuidedRecordedItem,
                           records: [String: PracticeRecord]) -> Bool {
        (records["speak:" + item.id]?.attempts ?? 0) > 0 ||
        (records["learn:" + item.id]?.attempts ?? 0) > 0
    }

    static func needsRecap(_ item: GuidedRecordedItem,
                           records: [String: PracticeRecord]) -> Bool {
        // An original legacy Learn self-rating already credits participation
        // in the guided group. Never retrofit a new quiz into prior progress.
        let learn = records["learn:" + item.id]
        return (learn?.attempts ?? 0) == 0 &&
               (learn?.objectiveAttempts ?? 0) == 0
    }

    static func nextPhase(step: GuidedFoundationStep,
                          records: [String: PracticeRecord]) -> (GuidedExercisePhase, Int)? {
        if let i = step.items.firstIndex(where: { !introduced($0, records: records) }) {
            return (.introduce, i)
        }
        guard hasRecap(step) else { return nil }
        if let i = step.items.firstIndex(where: { needsRecap($0, records: records) }) {
            return (.recap, i)
        }
        return nil
    }

    static func isComplete(step: GuidedFoundationStep,
                           records: [String: PracticeRecord]) -> Bool {
        nextPhase(step: step, records: records) == nil
    }
}
