import XCTest
@testable import PathToPolish

@MainActor final class NativeDialoguePreparationTests: XCTestCase {
    func testOriginalAuthoredDialogueFlagsOnlyUnpractisedLines() throws {
        let root = FileManager.default.temporaryDirectory
            .appendingPathComponent(UUID().uuidString)
        defer { try? FileManager.default.removeItem(at: root) }
        let learner = LocalLearningStore(
            storageURL: root.appendingPathComponent("learner.json"))
        let lesson = try XCTUnwrap(learner.lessons.first { $0.id == "Basic_01R" })
        let scene = try XCTUnwrap(lesson.microDialogues?.first)
        let originalIDs = scene.turns.map(\.itemId)
        XCTAssertEqual(NativeDialoguePreparation.unpractisedTurnIDs(
            scene: scene, records: learner.profile.records), originalIDs)
        XCTAssertEqual(learner.attempts, 0)
        XCTAssertEqual(learner.expedition.totalXP, 0)
        let first = try XCTUnwrap(lesson.items.first { $0.id == originalIDs[0] })
        XCTAssertTrue(learner.recordAttempt(item: first, mode: .read,
                                            understood: false))
        XCTAssertEqual(NativeDialoguePreparation.unpractisedTurnIDs(
            scene: scene, records: learner.profile.records),
                       Array(originalIDs.dropFirst()))
        XCTAssertEqual(learner.record(for: first, mode: .listen).attempts, 0)
        XCTAssertNil(learner.record(for: first, mode: .listen).objectiveAttempts)
    }

    func testPreviousSourceAttemptsWorkWithoutNewDialogueScores() throws {
        let root = FileManager.default.temporaryDirectory
            .appendingPathComponent(UUID().uuidString)
        defer { try? FileManager.default.removeItem(at: root) }
        let learner = LocalLearningStore(
            storageURL: root.appendingPathComponent("learner.json"))
        let lesson = try XCTUnwrap(learner.lessons.first { $0.id == "Basic_01R" })
        let scene = try XCTUnwrap(lesson.microDialogues?.first)
        for turn in scene.turns {
            let original = try XCTUnwrap(lesson.items.first { $0.id == turn.itemId })
            XCTAssertTrue(learner.recordAttempt(item: original, mode: .read,
                                                understood: false))
        }
        XCTAssertTrue(NativeDialoguePreparation.unpractisedTurnIDs(
            scene: scene, records: learner.profile.records).isEmpty)
        XCTAssertFalse(learner.profile.practiceJournal?.events.contains {
            $0.evidence == .dialogue
        } ?? false)
    }
}
