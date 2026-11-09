import Foundation
import XCTest
@testable import PathToPolish

@MainActor final class NativeRestoreTests: XCTestCase {
    private func fresh(_ filename: String = "local-learner.json") -> (LocalLearningStore, URL, URL) {
        let dir = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        let url = dir.appendingPathComponent(filename)
        return (LocalLearningStore(storageURL: url), dir, url)
    }

    private func source(_ learner: LocalLearningStore) throws -> (Lesson, LessonItem) {
        let lesson = try XCTUnwrap(learner.lessons.first { $0.availableModes.contains(.learn) })
        return (lesson, try XCTUnwrap(lesson.items.first))
    }

    private func archive(_ profile: LocalLearner, on learner: LocalLearningStore) -> LocalProgressArchive {
        LocalProgressArchive(profile: profile, sourceLessonIDs: learner.lessons.map(\.id))
    }

    func testImportedExportReplacesOnlyAfterConfirmationAndPreservesSavedEvents() throws {
        let (sourceStore, sourceDir, _) = fresh()
        defer { try? FileManager.default.removeItem(at: sourceDir) }
        let (target, targetDir, targetPath) = fresh()
        defer { try? FileManager.default.removeItem(at: targetDir) }
        let (lesson, item) = try source(sourceStore)
        XCTAssertTrue(sourceStore.recordAttempt(item: item, mode: .learn, understood: true))
        sourceStore.rememberPosition(lesson: lesson, item: item, mode: .learn)
        let exported = try sourceStore.makeLocalExport().archive.encoded()
        let importedFile = sourceDir.appendingPathComponent("export.json")
        try exported.write(to: importedFile)

        let (oldLesson, oldItem) = try source(target)
        XCTAssertTrue(target.recordAttempt(item: oldItem, mode: .speak, understood: nil))
        let previousIdentity = target.profile.localID
        let oldXP = target.expedition.totalXP
        let targetBefore = try Data(contentsOf: targetPath)
        let preview = try target.previewImportedProgress(from: importedFile)
        XCTAssertEqual(preview.importedAttempts, 1)
        XCTAssertEqual(preview.importedXP, 10)
        XCTAssertEqual(target.profile.localID, previousIdentity)
        XCTAssertEqual(try Data(contentsOf: targetPath), targetBefore,
                       "Opening a file or previewing must never change local progress")

        let backupURL = try target.restoreLocalProgress(preview)
        XCTAssertTrue(FileManager.default.fileExists(atPath: backupURL.path))
        XCTAssertEqual(target.localRestoreBackups.count, 1)
        XCTAssertEqual(target.profile.localID, sourceStore.profile.localID)
        XCTAssertEqual(target.profile.lastLessonID, lesson.id)
        XCTAssertEqual(target.profile.lastItemID, item.id)
        XCTAssertEqual(target.profile.practiceJournal?.events.first?.id,
                       sourceStore.profile.practiceJournal?.events.first?.id)
        XCTAssertEqual(target.expedition.totalXP, sourceStore.expedition.totalXP)
        XCTAssertEqual(target.attempts, sourceStore.attempts)

        let reopened = LocalLearningStore(storageURL: targetPath)
        XCTAssertNil(reopened.catalogError)
        XCTAssertEqual(reopened.profile.localID, sourceStore.profile.localID)
        XCTAssertEqual(reopened.profile.practiceJournal?.events.first?.id,
                       sourceStore.profile.practiceJournal?.events.first?.id)
        let protectedPrior = try LocalProgressArchive.decode(Data(contentsOf: backupURL))
        XCTAssertEqual(protectedPrior.profile.localID, previousIdentity)
        XCTAssertEqual(protectedPrior.profile.expedition?.totalXP, oldXP)
        XCTAssertNotEqual(protectedPrior.profile.localID, target.profile.localID)
        XCTAssertEqual(lesson.id, oldLesson.id)
    }

    func testEarlierPrivateBackupRestoresPreviousProgressWithoutMergeOrDoubleXP() throws {
        let (store, folder, _) = fresh()
        defer { try? FileManager.default.removeItem(at: folder) }
        let (_, item) = try source(store)
        XCTAssertTrue(store.recordAttempt(item: item, mode: .learn, understood: true))
        let originalIdentity = store.profile.localID
        let originalXP = store.expedition.totalXP
        let imported = archive(LocalLearner(), on: store)
        let candidate = try store.previewImportedProgress(
            from: saveArchive(imported, in: folder, name: "clean.json"))
        _ = try store.restoreLocalProgress(candidate)
        XCTAssertEqual(store.expedition.totalXP, 0)
        XCTAssertEqual(store.attempts, 0)
        let backup = try XCTUnwrap(store.localRestoreBackups.first)
        let prior = try store.previewLocalBackup(backup)
        XCTAssertEqual(prior.importedXP, originalXP)
        XCTAssertEqual(prior.importedAttempts, 1)
        _ = try store.restoreLocalProgress(prior)
        XCTAssertEqual(store.expedition.totalXP, originalXP)
        XCTAssertEqual(store.attempts, 1)
        XCTAssertEqual(store.profile.localID, originalIdentity)
        XCTAssertEqual(store.localRestoreBackups.count, 2)
        XCTAssertEqual(store.profile.practiceJournal?.events.count, 1)
    }

    private func saveArchive(_ value: LocalProgressArchive, in folder: URL,
                             name: String = "progress.json") throws -> URL {
        let url = folder.appendingPathComponent(name)
        try FileManager.default.createDirectory(at: folder,
                                                withIntermediateDirectories: true)
        try value.encoded().write(to: url)
        return url
    }

    func testInvalidForeignCatalogCannotOverwriteOrCreateBackup() throws {
        let (store, folder, path) = fresh()
        defer { try? FileManager.default.removeItem(at: folder) }
        let (_, item) = try source(store)
        XCTAssertTrue(store.recordAttempt(item: item, mode: .learn, understood: false))
        let before = try Data(contentsOf: path)
        var foreignIDs = store.lessons.map(\.id)
        foreignIDs[0] = "unrecognized-lesson"
        let foreign = LocalProgressArchive(profile: store.profile,
                                           sourceLessonIDs: foreignIDs)
        let file = try saveArchive(foreign, in: folder)
        XCTAssertThrowsError(try store.previewImportedProgress(from: file))
        XCTAssertEqual(try Data(contentsOf: path), before)
        XCTAssertTrue(store.localRestoreBackups.isEmpty)
    }

    func testMismatchedSourcePracticeAndForgedPersonalXPAreRejected() throws {
        let (store, folder, path) = fresh()
        defer { try? FileManager.default.removeItem(at: folder) }
        let (_, item) = try source(store)
        XCTAssertTrue(store.recordAttempt(item: item, mode: .learn, understood: true))
        let before = try Data(contentsOf: path)

        var invalidRecord = store.profile
        invalidRecord.records["learn:invented:0"] =
            PracticeRecord(attempts: 3, completed: 2, reviewLevel: 2)
        XCTAssertThrowsError(try store.previewImportedProgress(from:
            saveArchive(archive(invalidRecord, on: store), in: folder, name: "bad-record.json")))

        var invalidXP = store.profile
        var expedition = try XCTUnwrap(invalidXP.expedition)
        let initial = try XCTUnwrap(expedition.events.first)
        expedition.events[0] = LocalXPEvent(
            id: initial.id, itemID: initial.itemID, mode: initial.mode,
            at: initial.at, xp: 10_000, baseXP: 10_000,
            expeditionXP: initial.expeditionXP, tier: initial.tier,
            regionID: initial.regionID)
        invalidXP.expedition = expedition
        XCTAssertThrowsError(try store.previewImportedProgress(from:
            saveArchive(archive(invalidXP, on: store), in: folder, name: "forged-xp.json")))

        var mismatchedJournal = store.profile
        let real = try XCTUnwrap(mismatchedJournal.records["learn:" + item.id])
        mismatchedJournal.records["learn:" + item.id] = PracticeRecord(
            attempts: real.attempts + 1, completed: real.completed,
            reviewLevel: real.reviewLevel, lastAttempt: real.lastAttempt,
            nextReview: real.nextReview)
        XCTAssertThrowsError(try store.previewImportedProgress(from:
            saveArchive(archive(mismatchedJournal, on: store), in: folder,
                        name: "mismatched-journal.json")))
        XCTAssertEqual(try Data(contentsOf: path), before)
        XCTAssertTrue(store.localRestoreBackups.isEmpty)
    }

    func testChangedCurrentProgressSincePreviewStopsReplacement() throws {
        let (store, folder, path) = fresh()
        defer { try? FileManager.default.removeItem(at: folder) }
        let sourceFile = try saveArchive(archive(LocalLearner(), on: store), in: folder)
        let candidate = try store.previewImportedProgress(from: sourceFile)
        let (_, item) = try source(store)
        XCTAssertTrue(store.recordAttempt(item: item, mode: .learn, understood: true))
        let before = try Data(contentsOf: path)
        XCTAssertThrowsError(try store.restoreLocalProgress(candidate))
        XCTAssertEqual(try Data(contentsOf: path), before)
        XCTAssertEqual(store.attempts, 1)
        XCTAssertTrue(store.localRestoreBackups.isEmpty)
    }

    func testBackupCreationFailureKeepsOriginalProfileExactly() throws {
        let (store, folder, path) = fresh()
        defer { try? FileManager.default.removeItem(at: folder) }
        let (_, item) = try source(store)
        XCTAssertTrue(store.recordAttempt(item: item, mode: .learn, understood: true))
        let before = try Data(contentsOf: path)
        let profileID = store.profile.localID
        let backupDirectory = folder.appendingPathComponent("RestoreBackups")
        try Data("not a backup directory".utf8).write(to: backupDirectory)
        let file = try saveArchive(archive(LocalLearner(), on: store), in: folder)
        let candidate = try store.previewImportedProgress(from: file)
        XCTAssertThrowsError(try store.restoreLocalProgress(candidate))
        XCTAssertEqual(try Data(contentsOf: path), before)
        XCTAssertEqual(store.profile.localID, profileID)
        XCTAssertEqual(store.attempts, 1)
        XCTAssertEqual(store.expedition.totalXP, 10)
    }

    func testCorruptExistingProgressCannotBeReplacedEvenWithValidArchive() throws {
        let (_, dir, path) = fresh()
        defer { try? FileManager.default.removeItem(at: dir) }
        let original = Data("{broken original".utf8)
        try FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)
        try original.write(to: path)
        let store = LocalLearningStore(storageURL: path)
        let validArchive = try saveArchive(archive(LocalLearner(), on: store), in: dir)
        XCTAssertThrowsError(try store.previewImportedProgress(from: validArchive))
        XCTAssertEqual(try Data(contentsOf: path), original)
        XCTAssertTrue(store.localRestoreBackups.isEmpty)
    }

    func testUntrustedBackupOutsideAppDirectoryCannotBeOpened() throws {
        let (store, folder, _) = fresh()
        defer { try? FileManager.default.removeItem(at: folder) }
        let foreignFile = try saveArchive(archive(LocalLearner(), on: store), in: folder)
        let fake = LocalProgressBackup(url: foreignFile, savedAt: Date())
        XCTAssertThrowsError(try store.previewLocalBackup(fake))
    }

    func testOversizedImportRefusedBeforeDecoding() throws {
        let (store, folder, _) = fresh()
        defer { try? FileManager.default.removeItem(at: folder) }
        let oversized = folder.appendingPathComponent("oversized.json")
        try FileManager.default.createDirectory(at: folder, withIntermediateDirectories: true)
        let chunk = Data(repeating: 0x20, count: 16_000_002)
        try chunk.write(to: oversized)
        XCTAssertThrowsError(try store.previewImportedProgress(from: oversized))
        XCTAssertEqual(store.attempts, 0)
        XCTAssertTrue(store.localRestoreBackups.isEmpty)
    }

    func testLegacyUnjournalledProgressIsRestoredWithoutManufacturedEvents() throws {
        let (store, folder, _) = fresh()
        defer { try? FileManager.default.removeItem(at: folder) }
        let (_, item) = try source(store)
        var legacy = LocalLearner()
        legacy.records["learn:" + item.id] = PracticeRecord(
            attempts: 5, completed: 3, reviewLevel: 1,
            lastAttempt: Date(timeIntervalSince1970: 1_760_000_000),
            nextReview: Date(timeIntervalSince1970: 1_760_086_400))
        XCTAssertNil(legacy.practiceJournal)
        let file = try saveArchive(archive(legacy, on: store), in: folder)
        let pending = try store.previewImportedProgress(from: file)
        _ = try store.restoreLocalProgress(pending)
        XCTAssertEqual(store.attempts, 5)
        XCTAssertEqual(store.record(for: item, mode: .learn).completed, 3)
        XCTAssertNil(store.profile.practiceJournal)
        XCTAssertEqual(store.expedition.totalXP, 0)
        XCTAssertTrue(store.recordAttempt(item: item, mode: .learn, understood: false))
        XCTAssertTrue(store.profile.practiceJournal?.hasLegacyHistory == true)
        XCTAssertEqual(store.profile.practiceJournal?.events.count, 1)
    }
}
