import Foundation
import XCTest
@testable import PathToPolish

@MainActor final class NativePrivateCloudGateStoreTests: XCTestCase {
    private let account = "opaque-private-owner-only-account"

    private func storage() -> (URL, URL) {
        let folder = FileManager.default.temporaryDirectory
            .appendingPathComponent(UUID().uuidString)
        return (folder, folder.appendingPathComponent("PrivateCloudPolicy.json"))
    }

    private func linked() -> LocalLearner {
        var learner = LocalLearner()
        let journal = NativePracticeJournal(
            startedAt: Date(timeIntervalSince1970: 1_760_000_000),
            hasLegacyHistory: false)
        learner.practiceJournal = journal
        learner.linkedUTCEpoch = journal.epochID
        return learner
    }

    private func activate(_ store: NativePrivateCloudGateStore,
                          learner: LocalLearner) throws {
        let lessons = try CatalogLoader.load()
        let regions = try PolandRegionCatalog.load()
        try store.commit {
            try $0.proposeExplicitOptIn(approved: true,
                verifiedOpaqueAccountKey: account,
                learner: learner, lessons: lessons, regions: regions)
        }
    }

    func testFirstLaunchDoesNotCreateAccountOrPolicyFile() throws {
        let (folder, file) = storage()
        defer { try? FileManager.default.removeItem(at: folder) }
        let store = try NativePrivateCloudGateStore(storageURL: file)
        XCTAssertEqual(store.gate.phase, .off)
        XCTAssertNil(store.gate.scope)
        XCTAssertFalse(FileManager.default.fileExists(atPath: file.path))
        let again = try NativePrivateCloudGateStore(storageURL: file)
        XCTAssertEqual(again.gate.phase, .off)
    }

    func testOptInIsCommittedBeforePublicationAndSurvivesRestart() throws {
        let (folder, file) = storage()
        defer { try? FileManager.default.removeItem(at: folder) }
        let learner = linked()
        let store = try NativePrivateCloudGateStore(storageURL: file)
        try activate(store, learner: learner)
        XCTAssertEqual(store.gate.phase, .active)
        let recovered = try NativePrivateCloudGateStore(storageURL: file)
        XCTAssertEqual(recovered.gate.phase, .active)
        XCTAssertEqual(recovered.gate.scope?.accountKey, account)
        XCTAssertEqual(recovered.gate.scope?.learnerID, learner.localID)
        XCTAssertEqual(recovered.gate.scope?.journalEpoch, learner.linkedUTCEpoch)
        XCTAssertNoThrow(try recovered.gate.authorizeRemoteOperation(
            verifiedOpaqueAccountKey: account, learner: learner,
            snapshot: NativePrivateCloudSnapshot(
                scope: try XCTUnwrap(recovered.gate.scope), generation: 0)))
    }

    func testLogoutAndExplicitResumePersistButNeverEraseLocalLearning() throws {
        let (folder, file) = storage()
        defer { try? FileManager.default.removeItem(at: folder) }
        let learner = linked()
        let store = try NativePrivateCloudGateStore(storageURL: file)
        try activate(store, learner: learner)
        try store.commit { try $0.optOutKeepLocalData() }
        let off = try NativePrivateCloudGateStore(storageURL: file)
        XCTAssertEqual(off.gate.phase, .off)
        XCTAssertEqual(off.gate.scope?.learnerID, learner.localID)
        XCTAssertThrowsError(try off.gate.authorizeRemoteOperation(
            verifiedOpaqueAccountKey: account, learner: learner,
            snapshot: NativePrivateCloudSnapshot(
                scope: try XCTUnwrap(off.gate.scope), generation: 0)))
        XCTAssertThrowsError(try off.commit {
            try $0.resumeSameAccount(
                approved: false, verifiedOpaqueAccountKey: account)
        })
        XCTAssertEqual(off.gate.phase, .off)
        try off.commit {
            try $0.resumeSameAccount(approved: true,
                                      verifiedOpaqueAccountKey: account)
        }
        XCTAssertEqual(try NativePrivateCloudGateStore(storageURL: file).gate.phase,
                       .active)
        XCTAssertNotNil(learner.practiceJournal)
    }

    func testChangedAccountPauseRemainsPausedAfterAppRestart() throws {
        let (folder, file) = storage()
        defer { try? FileManager.default.removeItem(at: folder) }
        let learner = linked()
        let store = try NativePrivateCloudGateStore(storageURL: file)
        try activate(store, learner: learner)
        try store.commit { $0.observeAccount("different-private-account") }
        let restarted = try NativePrivateCloudGateStore(storageURL: file)
        XCTAssertEqual(restarted.gate.phase, .pausedAccountChange)
        XCTAssertThrowsError(try restarted.commit {
            try $0.resumeSameAccount(
                approved: true, verifiedOpaqueAccountKey: "different-private-account")
        })
        XCTAssertEqual(restarted.gate.phase, .pausedAccountChange)
        try restarted.commit {
            try $0.resumeSameAccount(
                approved: true, verifiedOpaqueAccountKey: account)
        }
        XCTAssertEqual(restarted.gate.phase, .active)
    }

    func testDeletionPendingPersistsAndBlocksStaleWritesAfterRelaunch() throws {
        let (folder, file) = storage()
        defer { try? FileManager.default.removeItem(at: folder) }
        let learner = linked()
        let store = try NativePrivateCloudGateStore(storageURL: file)
        try activate(store, learner: learner)
        var pending: NativePrivateCloudTombstone?
        try store.commit {
            pending = try $0.requestRemoteErase(
                approved: true, verifiedOpaqueAccountKey: account)
        }
        let request = try XCTUnwrap(pending)
        let reopened = try NativePrivateCloudGateStore(storageURL: file)
        XCTAssertEqual(reopened.gate.phase, .deletionPending)
        XCTAssertEqual(reopened.gate.requestedTombstone, request)
        XCTAssertThrowsError(try reopened.gate.authorizeRemoteOperation(
            verifiedOpaqueAccountKey: account, learner: learner,
            snapshot: NativePrivateCloudSnapshot(
                scope: request.scope, generation: 0)))
        XCTAssertThrowsError(try reopened.commit {
            try $0.optOutKeepLocalData()
        })
        XCTAssertEqual(reopened.gate.phase, .deletionPending)
        try reopened.commit {
            try $0.acknowledgeServerTombstone(request)
        }
        let deleted = try NativePrivateCloudGateStore(storageURL: file)
        XCTAssertEqual(deleted.gate.phase, .remotelyDeleted)
        XCTAssertEqual(deleted.gate.knownGeneration, 1)
        XCTAssertThrowsError(try deleted.gate.authorizeRemoteOperation(
            verifiedOpaqueAccountKey: account, learner: learner,
            snapshot: NativePrivateCloudSnapshot(
                scope: request.scope, generation: 0)))
        XCTAssertNotNil(learner.practiceJournal)
    }

    func testCorruptOrImpossiblePhaseCannotResetDeletionProtection() throws {
        let (folder, file) = storage()
        defer { try? FileManager.default.removeItem(at: folder) }
        let learner = linked()
        let store = try NativePrivateCloudGateStore(storageURL: file)
        try activate(store, learner: learner)
        try store.commit {
            _ = try $0.requestRemoteErase(
                approved: true, verifiedOpaqueAccountKey: account)
        }
        let protected = try Data(contentsOf: file)
        var json = try XCTUnwrap(JSONSerialization.jsonObject(with: protected)
                                as? [String: Any])
        json["phase"] = "remotelyDeleted"
        json["knownGeneration"] = 0
        json.removeValue(forKey: "requestedTombstone")
        let invalid = try JSONSerialization.data(withJSONObject: json)
        try invalid.write(to: file)
        XCTAssertThrowsError(try NativePrivateCloudGateStore(storageURL: file))
        XCTAssertEqual(try Data(contentsOf: file), invalid,
                       "Never silently overwrite an invalid pending-delete file")
        try protected.write(to: file)
        let restored = try NativePrivateCloudGateStore(storageURL: file)
        XCTAssertEqual(restored.gate.phase, .deletionPending)
    }

    func testOversizePolicyFileRejectedWithoutTruncationOrReset() throws {
        let (folder, file) = storage()
        defer { try? FileManager.default.removeItem(at: folder) }
        try FileManager.default.createDirectory(at: folder,
                                                withIntermediateDirectories: true)
        let excess = Data(repeating: 0x20, count: 16_385)
        try excess.write(to: file)
        XCTAssertThrowsError(try NativePrivateCloudGateStore(storageURL: file))
        XCTAssertEqual(try Data(contentsOf: file), excess)
    }

    func testFailedFileCommitKeepsOldPolicyUnpublished() throws {
        let (folder, _) = storage()
        defer { try? FileManager.default.removeItem(at: folder) }
        try FileManager.default.createDirectory(at: folder,
                                                withIntermediateDirectories: true)
        let parent = folder.appendingPathComponent("not-a-directory")
        try Data("leave unchanged".utf8).write(to: parent)
        let nested = parent.appendingPathComponent("PrivateCloudPolicy.json")
        let store = try NativePrivateCloudGateStore(storageURL: nested)
        XCTAssertThrowsError(try activate(store, learner: linked()))
        XCTAssertEqual(store.gate.phase, .off)
        XCTAssertNil(store.gate.scope)
        XCTAssertEqual(try Data(contentsOf: parent), Data("leave unchanged".utf8))
    }

    func testCloudStateNeverAppearsInExportedLocalProgress() throws {
        let (folder, file) = storage()
        defer { try? FileManager.default.removeItem(at: folder) }
        let learner = linked()
        let store = try NativePrivateCloudGateStore(storageURL: file)
        try activate(store, learner: learner)
        let archive = LocalProgressArchive(
            profile: learner,
            sourceLessonIDs: try CatalogLoader.load().map(\.id))
        let exported = try XCTUnwrap(String(
            data: archive.encoded(), encoding: .utf8))
        XCTAssertFalse(exported.contains(account))
        XCTAssertFalse(exported.contains("requestedTombstone"))
        XCTAssertFalse(exported.contains("PrivateCloudPolicy"))
        XCTAssertEqual(store.gate.phase, .active)
    }
}
