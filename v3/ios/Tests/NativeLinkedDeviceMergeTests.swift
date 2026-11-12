import Foundation
import XCTest
@testable import PathToPolish

@MainActor final class NativeLinkedDeviceMergeTests: XCTestCase {
    private func fresh() -> (LocalLearningStore, URL, URL) {
        let dir = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        let file = dir.appendingPathComponent("learner.json")
        return (LocalLearningStore(storageURL: file), dir, file)
    }

    private func source(_ learner: LocalLearningStore) throws -> LessonItem {
        try XCTUnwrap(learner.lessons.first(where: {
            $0.availableModes.contains(.learn)
        })?.items.first)
    }

    private func export(_ learner: LocalLearningStore, to dir: URL,
                        filename: String) throws -> URL {
        try FileManager.default.createDirectory(at: dir,
                                                withIntermediateDirectories: true)
        let result = dir.appendingPathComponent(filename)
        try learner.makeLocalExport().archive.encoded().write(to: result)
        return result
    }

    /// Transfer the anonymous learner with the existing explicit Restore
    /// path. This must not carry the originating phone's per-device actor ID.
    private func link(_ origin: LocalLearningStore, to second: LocalLearningStore,
                      at directory: URL) throws {
        let path = try export(origin, to: directory, filename: "initial-link.json")
        let originalSecondID = second.profile.localID
        _ = try second.restoreLocalProgress(second.previewImportedProgress(from: path))
        XCTAssertEqual(second.profile.localID, origin.profile.localID)
        XCTAssertEqual(second.profile.deviceActorID, originalSecondID)
        XCTAssertNotEqual(second.profile.deviceActorID,
                          origin.profile.deviceActorID ?? origin.profile.localID)
    }

    func testOwnerLinkedTwoDeviceMergeIsReviewedBackedUpAndIdempotent() throws {
        let (first, folderA, pathA) = fresh()
        let (second, folderB, _) = fresh()
        defer { try? FileManager.default.removeItem(at: folderA) }
        defer { try? FileManager.default.removeItem(at: folderB) }
        let item = try source(first)
        XCTAssertTrue(first.recordAttempt(item: item, mode: .learn, understood: true))
        try link(first, to: second, at: folderB)
        let originalLearner = first.profile.localID
        let firstActor = try XCTUnwrap(first.profile.practiceJournal?.events.first?.actorID)

        XCTAssertTrue(second.recordAttempt(item: item, mode: .speak, understood: nil))
        XCTAssertTrue(first.recordAttempt(item: item, mode: .speak, understood: nil))
        let secondActor = try XCTUnwrap(second.profile.practiceJournal?.events.last?.actorID)
        XCTAssertNotEqual(firstActor, secondActor)
        let incomingFile = try export(second, to: folderA, filename: "second-device.json")
        let originalFile = try Data(contentsOf: pathA)
        let review = try first.previewLinkedDeviceMerge(from: incomingFile)
        XCTAssertEqual(review.plan.originalEventCount, 2)
        XCTAssertEqual(review.plan.incomingEventCount, 2)
        XCTAssertEqual(review.plan.mergedEventCount, 3)
        XCTAssertEqual(review.plan.newEvents, 1)
        XCTAssertEqual(review.plan.mergedEffortXP, 20)
        XCTAssertEqual(first.attempts, 2)
        XCTAssertEqual(try Data(contentsOf: pathA), originalFile)

        let recoverable = try first.applyLinkedDeviceMerge(review)
        XCTAssertTrue(FileManager.default.fileExists(atPath: recoverable.path))
        XCTAssertEqual(first.profile.localID, originalLearner)
        XCTAssertEqual(first.profile.practiceJournal?.events.count, 3)
        XCTAssertEqual(first.attempts, 3)
        XCTAssertEqual(first.record(for: item, mode: .speak).attempts, 2)
        XCTAssertEqual(first.expedition.totalXP, 20)
        XCTAssertEqual(first.profile.linkedUTCEpoch, first.profile.practiceJournal?.epochID)
        XCTAssertTrue(first.profile.deviceActorID == firstActor)
        XCTAssertEqual(try LocalProgressArchive.decode(Data(contentsOf: recoverable))
                           .profile.records["speak:" + item.id]?.attempts, 1)

        let reopened = LocalLearningStore(storageURL: pathA)
        XCTAssertNil(reopened.catalogError)
        XCTAssertEqual(reopened.profile.practiceJournal?.events.count, 3)
        XCTAssertEqual(reopened.profile.linkedUTCEpoch,
                       reopened.profile.practiceJournal?.epochID)

        // A repeat export is safe and does not duplicate attempts or XP.
        let repeated = try first.previewLinkedDeviceMerge(from: incomingFile)
        XCTAssertEqual(repeated.plan.newEvents, 0)
        XCTAssertEqual(repeated.plan.mergedEffortXP, 20)
        XCTAssertEqual(first.attempts, 3)
    }

    func testIndependentAnonymousLearnersCannotBeLinkedByMergeButton() throws {
        let (one, folderA, _) = fresh()
        let (two, folderB, _) = fresh()
        defer { try? FileManager.default.removeItem(at: folderA) }
        defer { try? FileManager.default.removeItem(at: folderB) }
        let item = try source(one)
        XCTAssertTrue(one.recordAttempt(item: item, mode: .learn, understood: true))
        XCTAssertTrue(two.recordAttempt(item: item, mode: .learn, understood: true))
        let file = try export(two, to: folderA, filename: "foreign.json")
        let localID = one.profile.localID
        XCTAssertThrowsError(try one.previewLinkedDeviceMerge(from: file))
        XCTAssertEqual(one.profile.localID, localID)
        XCTAssertEqual(one.attempts, 1)
        XCTAssertTrue(one.localRestoreBackups.isEmpty)
    }

    func testHistoricalLegacyProgressCannotInventMergedReviewOrXP() throws {
        let (one, folderA, _) = fresh()
        let (two, folderB, _) = fresh()
        defer { try? FileManager.default.removeItem(at: folderA) }
        defer { try? FileManager.default.removeItem(at: folderB) }
        let item = try source(one)
        XCTAssertTrue(one.recordAttempt(item: item, mode: .learn, understood: true))
        try link(one, to: two, at: folderB)
        var changed = two.profile
        changed.practiceJournal = nil
        let sourceArchive = LocalProgressArchive(
            profile: changed, sourceLessonIDs: two.lessons.map(\.id))
        let file = folderA.appendingPathComponent("no-journal.json")
        try sourceArchive.encoded().write(to: file)
        XCTAssertThrowsError(try one.previewLinkedDeviceMerge(from: file))
        XCTAssertTrue(one.localRestoreBackups.isEmpty)
    }

    func testChangedCurrentProgressAfterReviewCannotBeOverwritten() throws {
        let (one, folderA, _) = fresh()
        let (two, folderB, _) = fresh()
        defer { try? FileManager.default.removeItem(at: folderA) }
        defer { try? FileManager.default.removeItem(at: folderB) }
        let item = try source(one)
        XCTAssertTrue(one.recordAttempt(item: item, mode: .learn, understood: true))
        try link(one, to: two, at: folderB)
        XCTAssertTrue(two.recordAttempt(item: item, mode: .speak, understood: nil))
        let incoming = try export(two, to: folderA, filename: "peer.json")
        let review = try one.previewLinkedDeviceMerge(from: incoming)
        XCTAssertTrue(one.recordAttempt(item: item, mode: .speak, understood: nil))
        let before = one.profile.practiceJournal?.events.count
        XCTAssertThrowsError(try one.applyLinkedDeviceMerge(review))
        XCTAssertEqual(one.profile.practiceJournal?.events.count, before)
        XCTAssertTrue(one.localRestoreBackups.isEmpty)
    }

    func testBadBackupDirectoryCannotPublishMergedXPOrReviews() throws {
        let (one, folderA, pathA) = fresh()
        let (two, folderB, _) = fresh()
        defer { try? FileManager.default.removeItem(at: folderA) }
        defer { try? FileManager.default.removeItem(at: folderB) }
        let item = try source(one)
        XCTAssertTrue(one.recordAttempt(item: item, mode: .learn, understood: true))
        try link(one, to: two, at: folderB)
        XCTAssertTrue(two.recordAttempt(item: item, mode: .speak, understood: nil))
        let incoming = try export(two, to: folderA, filename: "peer.json")
        let preview = try one.previewLinkedDeviceMerge(from: incoming)
        let before = try Data(contentsOf: pathA)
        try Data("not a directory".utf8).write(
            to: folderA.appendingPathComponent("RestoreBackups"))
        XCTAssertThrowsError(try one.applyLinkedDeviceMerge(preview))
        XCTAssertEqual(try Data(contentsOf: pathA), before)
        XCTAssertEqual(one.attempts, 1)
        XCTAssertEqual(one.expedition.totalXP, 10)
        XCTAssertNil(one.profile.linkedUTCEpoch)
    }

    func testDifferentSourceRegionOnPeerIsRetainedAfterMergeAndLocalSelectionPersists() throws {
        let (one, folderA, _) = fresh()
        let (two, folderB, _) = fresh()
        defer { try? FileManager.default.removeItem(at: folderA) }
        defer { try? FileManager.default.removeItem(at: folderB) }
        let item = try source(one)
        XCTAssertTrue(one.recordAttempt(item: item, mode: .learn, understood: true))
        try link(one, to: two, at: folderB)
        let otherRegion = try XCTUnwrap(one.regions.first { $0.id != "mazowieckie" })
        two.chooseRegion(otherRegion.id)
        XCTAssertTrue(two.recordAttempt(item: item, mode: .speak, understood: nil))
        let incoming = try export(two, to: folderA, filename: "peer.json")
        let review = try one.previewLinkedDeviceMerge(from: incoming)
        _ = try one.applyLinkedDeviceMerge(review)
        XCTAssertEqual(one.expedition.selectedRegion, "mazowieckie")
        // Both phones may record attempts within the same second. In that
        // case the immutable UUID tie-break, not device ownership or the
        // order of two exported files, decides the first region goal.
        let orderedRegions = one.expedition.events.map(\.regionID)
        XCTAssertEqual(Set(orderedRegions), Set(["mazowieckie", otherRegion.id]))
        XCTAssertEqual(one.expedition.regionGoals[orderedRegions[0]], 300)
        let secondGoal = Int((300.0 * pow(1 + 0.22, 1.35) / 10).rounded()) * 10
        XCTAssertEqual(one.expedition.regionGoals[orderedRegions[1]], secondGoal)
        XCTAssertEqual(one.expedition.regionTotal(otherRegion.id), 10)
        XCTAssertTrue(one.profile.practiceJournal?.events.contains(where: {
            $0.regionID == otherRegion.id
        }) == true)
    }

    func testProfileAfterMergeUsesUTCRewardDatesForNewAttempts() throws {
        let (one, folderA, _) = fresh()
        let (two, folderB, _) = fresh()
        defer { try? FileManager.default.removeItem(at: folderA) }
        defer { try? FileManager.default.removeItem(at: folderB) }
        let item = try source(one)
        XCTAssertTrue(one.recordAttempt(item: item, mode: .learn, understood: true))
        try link(one, to: two, at: folderB)
        XCTAssertTrue(two.recordAttempt(item: item, mode: .speak, understood: nil))
        let incoming = try export(two, to: folderA, filename: "peer.json")
        _ = try one.applyLinkedDeviceMerge(one.previewLinkedDeviceMerge(from: incoming))
        let priorXP = one.expedition.totalXP
        XCTAssertTrue(one.recordAttempt(item: item, mode: .learn, understood: true))
        XCTAssertEqual(one.expedition.totalXP, priorXP,
                       "Same mode/item/UTC day must not gain another award")
        XCTAssertEqual(one.record(for: item, mode: .learn).attempts, 2)
        XCTAssertEqual(one.profile.practiceJournal?.events.count, 3)
    }

    func testMismatchedUUIDPayloadInManualHistoryIsRejectedBeforeBackup() throws {
        let (one, folderA, _) = fresh()
        let (two, folderB, _) = fresh()
        defer { try? FileManager.default.removeItem(at: folderA) }
        defer { try? FileManager.default.removeItem(at: folderB) }
        let item = try source(one)
        XCTAssertTrue(one.recordAttempt(item: item, mode: .learn, understood: true))
        try link(one, to: two, at: folderB)
        let a = try XCTUnwrap(one.profile.practiceJournal)
        var b = a
        let old = try XCTUnwrap(b.events.first)
        b.events[0] = NativePracticeEvent(
            id: old.id, actorID: old.actorID, itemID: old.itemID,
            mode: old.mode, at: old.at, outcome: .needsPractice,
            regionID: old.regionID)
        XCTAssertThrowsError(try NativePracticeJournal.mergeCandidate(
            a, b, lessons: one.lessons))
        XCTAssertTrue(one.localRestoreBackups.isEmpty)
    }

    func testInvalidLinkedUTCProfileIsRejectedByRestoreIntegrityAudit() throws {
        let (one, folder, _) = fresh()
        defer { try? FileManager.default.removeItem(at: folder) }
        let item = try source(one)
        XCTAssertTrue(one.recordAttempt(item: item, mode: .learn, understood: true))
        var fabricated = one.profile
        fabricated.linkedUTCEpoch = UUID()
        let archive = LocalProgressArchive(
            profile: fabricated, sourceLessonIDs: one.lessons.map(\.id))
        let file = folder.appendingPathComponent("forged-link.json")
        try archive.encoded().write(to: file)
        XCTAssertThrowsError(try one.previewImportedProgress(from: file))
        XCTAssertTrue(one.localRestoreBackups.isEmpty)
    }
}
