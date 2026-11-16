import Foundation

/// An authored dialogue may contain original source lines the learner has
/// never practised. This only identifies missing source-item exposure; it
/// makes no morphological, comprehension or phonetic proficiency claim.
/// Preparation is optional, local and ungraded; no new words are invented.
enum NativeDialoguePreparation {
    static func unpractisedTurnIDs(scene: NativeMicroDialogue,
                                   records: [String: PracticeRecord]) -> [String] {
        scene.turns.compactMap { turn in
            let id = turn.itemId
            let known = ["speak:", "learn:", "read:", "listen:"].contains { prefix in
                (records[prefix + id]?.attempts ?? 0) > 0
            }
            return known ? nil : id
        }
    }
}
