import Foundation
import XCTest
@testable import PathToPolish

@MainActor final class LocalProgressArchiveTests: XCTestCase {
    private func fresh() -> (LocalLearningStore, URL, URL) {
        let folder = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        let path = folder.appendingPathComponent("local-learner.json")
        return (LocalLearningStore(storageURL: path), folder, path)
    }

    func testUserExportRoundTripsActualOfflineCourseProgressWithoutNetworkFields() throws {
        let (store, folder, path) = fresh()
        defer { try? FileManager.default.removeItem(at: folder) }
        XCTAssertNil(store.catalogError)
        let lesson = try XCTUnwrap(store.lessons.first { $0.availableModes.contains(.learn) })
        let item = try XCTUnwrap(lesson.items.first)
        store.recordAttempt(item: item, mode: .learn, understood: true)
        store.rememberPosition(lesson: lesson, item: item, mode: .learn)
        let savedBefore = try Data(contentsOf: path)

        let document = try store.makeLocalExport()
        let encoded = try document.archive.encoded()
        let restored = try LocalProgressArchive.decode(encoded)
        XCTAssertEqual(restored.schemaVersion, 1)
        XCTAssertEqual(restored.format, LocalProgressArchive.currentFormat)
        XCTAssertEqual(restored.sourceLessonIDs.count, 26)
        XCTAssertEqual(restored.profile.localID, store.profile.localID)
        XCTAssertEqual(restored.profile.lastLessonID, lesson.id)
        XCTAssertEqual(restored.profile.records["learn:" + item.id]?.attempts, 1)
        XCTAssertEqual(restored.profile.expedition?.totalXP, store.expedition.totalXP)
        XCTAssertEqual(try Data(contentsOf: path), savedBefore,
                       "Export must not mutate the active progress file")
        let json = try XCTUnwrap(String(data: encoded, encoding: .utf8))
        XCTAssertFalse(json.contains("\"sessionToken\""))
        XCTAssertFalse(json.contains("\"password\""))
        XCTAssertFalse(json.contains("\"bearerToken\""))
        XCTAssertFalse(json.contains("\"microphoneRecording\""))
        XCTAssertFalse(json.contains("\"familyMembership\""))
    }

    func testExplicitResetAtomicallyClearsOnlyLocalProgressAndRotatesIdentity() throws {
        let (store, folder, path) = fresh()
        defer { try? FileManager.default.removeItem(at: folder) }
        let lesson = try XCTUnwrap(store.lessons.first { $0.availableModes.contains(.learn) })
        let item = try XCTUnwrap(lesson.items.first)
        store.rememberPosition(lesson: lesson, item: item, mode: .learn)
        store.recordAttempt(item: item, mode: .learn, understood: false)
        let formerID = store.profile.localID
        XCTAssertGreaterThan(store.expedition.totalXP, 0)
        XCTAssertGreaterThan(store.attempts, 0)
        XCTAssertTrue(FileManager.default.fileExists(atPath: path.path))

        XCTAssertTrue(store.resetLocalProgress())
        XCTAssertNil(store.saveError)
        XCTAssertNotEqual(store.profile.localID, formerID)
        XCTAssertEqual(store.attempts, 0)
        XCTAssertEqual(store.expedition.totalXP, 0)
        XCTAssertEqual(store.dueReviews.count, 0)
        XCTAssertNil(store.profile.lastLessonID)
        XCTAssertNil(store.profile.lastCoreLessonID)
        XCTAssertNil(store.profile.lastItemID)
        XCTAssertNil(store.profile.guidedStepID)
        XCTAssertNil(store.profile.tourist)
        XCTAssertEqual(store.lessons.count, 26, "Bundled curriculum must not be erased")

        let reopened = LocalLearningStore(storageURL: path)
        XCTAssertNil(reopened.catalogError)
        XCTAssertEqual(reopened.profile.localID, store.profile.localID)
        XCTAssertEqual(reopened.attempts, 0)
        XCTAssertEqual(reopened.expedition.totalXP, 0)
        XCTAssertEqual(reopened.profile.records.count, 0)
        XCTAssertNotNil(reopened.nextLesson)
    }

    func testCorruptedSavedProgressCannotBeOverwrittenByResetOrExport() throws {
        let (_, folder, path) = fresh()
        defer { try? FileManager.default.removeItem(at: folder) }
        try FileManager.default.createDirectory(at: folder, withIntermediateDirectories: true)
        let broken = Data("{not a learner record".utf8)
        try broken.write(to: path)
        let learner = LocalLearningStore(storageURL: path)
        XCTAssertNotNil(learner.saveError)
        XCTAssertThrowsError(try learner.makeLocalExport())
        XCTAssertFalse(learner.resetLocalProgress())
        XCTAssertEqual(try Data(contentsOf: path), broken)
    }

    func testFailedAtomicResetNeverPublishesNewLearnerOrClaimsSuccess() throws {
        let root = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        defer { try? FileManager.default.removeItem(at: root) }
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
        let blockedParent = root.appendingPathComponent("regular-file")
        try Data("not a directory".utf8).write(to: blockedParent)
        let learner = LocalLearningStore(storageURL: blockedParent.appendingPathComponent("learner.json"))
        let before = learner.profile.localID
        XCTAssertFalse(learner.resetLocalProgress())
        XCTAssertEqual(learner.profile.localID, before)
        XCTAssertNotNil(learner.saveError)
        XCTAssertEqual(try Data(contentsOf: blockedParent), Data("not a directory".utf8))
    }

    func testUnknownFutureArchiveAndInvalidProgressFailClosed() throws {
        let (learner, folder, _) = fresh()
        defer { try? FileManager.default.removeItem(at: folder) }
        let original = try learner.makeLocalExport().archive.encoded()
        var json = try XCTUnwrap(JSONSerialization.jsonObject(with: original) as? [String: Any])
        json["schemaVersion"] = 999
        XCTAssertThrowsError(try LocalProgressArchive.decode(
            JSONSerialization.data(withJSONObject: json)))

        var corruptedProfile = learner.profile
        corruptedProfile.records["learn:invalid"] = PracticeRecord(
            attempts: 1, completed: 2, reviewLevel: 0)
        let corrupted = LocalProgressArchive(
            profile: corruptedProfile, sourceLessonIDs: learner.lessons.map(\.id))
        XCTAssertThrowsError(try corrupted.encoded())
    }
}
