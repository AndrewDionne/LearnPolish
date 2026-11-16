import XCTest
@testable import PathToPolish

/// Same submit boundary used by guided foundations and native Learn,
/// Listen, Read and Speak. Tests use the authoritative bundled V2 catalog.
@MainActor final class NativePracticeSubmissionTests: XCTestCase {
    private func source(for mode: PracticeMode,
                        store: LocalLearningStore) throws -> LessonItem {
        let lesson = try XCTUnwrap(store.lessons.first { lesson in
            lesson.availableModes.contains(mode) &&
            !NativePracticeRules.items(for: lesson, mode: mode).isEmpty
        })
        return try XCTUnwrap(NativePracticeRules.items(
            for: lesson, mode: mode).first)
    }

    func testFailedDiskWriteNeverAcknowledgesOrNavigatesAnyPracticeMode() throws {
        let base = FileManager.default.temporaryDirectory
            .appendingPathComponent(UUID().uuidString)
        defer { try? FileManager.default.removeItem(at: base) }
        try FileManager.default.createDirectory(
            at: base, withIntermediateDirectories: true)
        let blockingFile = base.appendingPathComponent("not-a-folder")
        try Data("untouched".utf8).write(to: blockingFile)
        let store = LocalLearningStore(
            storageURL: blockingFile.appendingPathComponent("learner.json"))
        let originalID = store.profile.localID
        for mode in [PracticeMode.learn, .listen, .read, .speak] {
            let item = try source(for: mode, store: store)
            var shownAsAnswered = false
            let committed = NativePracticeSubmission.commit(
                store: store, item: item, mode: mode,
                understood: mode == .speak ? nil : true) {
                    shownAsAnswered = true
                }
            XCTAssertFalse(committed, "\(mode.rawValue) must not advance without storage")
            XCTAssertFalse(shownAsAnswered)
            XCTAssertEqual(store.record(for: item, mode: mode).attempts, 0)
            XCTAssertEqual(store.expedition.totalXP, 0)
            XCTAssertNil(store.profile.practiceJournal)
            XCTAssertNotNil(store.saveError)
        }
        XCTAssertEqual(store.profile.localID, originalID)
        XCTAssertEqual(try Data(contentsOf: blockingFile),
                       Data("untouched".utf8))
    }

    func testSavedAnswerNotifiesOnceAndPersistsBeforeShowingNextCard() throws {
        let base = FileManager.default.temporaryDirectory
            .appendingPathComponent(UUID().uuidString)
        defer { try? FileManager.default.removeItem(at: base) }
        let path = base.appendingPathComponent("learner.json")
        let store = LocalLearningStore(storageURL: path)
        for mode in [PracticeMode.learn, .listen, .read, .speak] {
            let item = try source(for: mode, store: store)
            var callbacks = 0
            let committed = NativePracticeSubmission.commit(
                store: store, item: item, mode: mode,
                understood: mode == .speak ? nil : true) {
                    callbacks += 1
                    // The callback simulates accepting an answer or moving
                    // cards: the disk write must already be durable.
                    let reloaded = LocalLearningStore(storageURL: path)
                    XCTAssertEqual(reloaded.record(for: item, mode: mode).attempts, 1)
                    XCTAssertEqual(reloaded.profile.practiceJournal?.events
                        .filter { $0.itemID == item.id && $0.mode == mode }.count, 1)
                }
            XCTAssertTrue(committed)
            XCTAssertEqual(callbacks, 1)
            XCTAssertEqual(store.record(for: item, mode: mode).attempts, 1)
        }
        XCTAssertEqual(store.profile.practiceJournal?.events.count, 4)
        XCTAssertNil(store.saveError)
    }
}
