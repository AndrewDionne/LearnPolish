import Foundation
import XCTest
@testable import PathToPolish

@MainActor final class NativePrivateCloudGateTests: XCTestCase {
    private let keyA = "opaque-cloud-record-owner-a1"
    private let keyB = "opaque-cloud-record-owner-b2"

    private func sources() throws -> ([Lesson], [PolandRegion]) {
        (try CatalogLoader.load(), try PolandRegionCatalog.load())
    }

    private func linkedLearner() -> LocalLearner {
        var learner = LocalLearner()
        let journal = NativePracticeJournal(
            startedAt: Date(timeIntervalSince1970: 1_760_000_000),
            hasLegacyHistory: false)
        learner.practiceJournal = journal
        learner.linkedUTCEpoch = journal.epochID
        return learner
    }

    private func activate(_ gate: inout NativePrivateCloudGate,
                          learner: LocalLearner) throws {
        let (lessons, regions) = try sources()
        try gate.proposeExplicitOptIn(
            approved: true, verifiedOpaqueAccountKey: keyA,
            learner: learner, lessons: lessons, regions: regions)
    }

    private func head(_ gate: NativePrivateCloudGate,
                      revision: UInt64 = 0) throws -> NativePrivateCloudSnapshot {
        NativePrivateCloudSnapshot(scope: try XCTUnwrap(gate.scope),
                                    generation: revision)
    }

    func testFirstLaunchAndUnapprovedCloudAccessStayOff() throws {
        let learner = linkedLearner()
        let (lessons, regions) = try sources()
        var gate = NativePrivateCloudGate()
        XCTAssertEqual(gate.phase, .off)
        XCTAssertNil(gate.scope)
        XCTAssertThrowsError(try gate.proposeExplicitOptIn(
            approved: false, verifiedOpaqueAccountKey: keyA,
            learner: learner, lessons: lessons, regions: regions))
        XCTAssertEqual(gate.phase, .off)
        XCTAssertNil(gate.scope)
        let fake = NativePrivateCloudScope(accountKey: keyA,
            learnerID: learner.localID,
            journalEpoch: try XCTUnwrap(learner.linkedUTCEpoch))
        XCTAssertThrowsError(try gate.authorizeRemoteOperation(
            verifiedOpaqueAccountKey: keyA, learner: learner,
            snapshot: NativePrivateCloudSnapshot(scope: fake, generation: 0)))
    }

    func testIncompleteLegacyOrUnlinkedProfilesCannotConnect() throws {
        let (lessons, regions) = try sources()
        for variant in 0..<3 {
            var learner = linkedLearner()
            switch variant {
            case 0: learner.linkedUTCEpoch = nil
            case 1: learner.practiceJournal = nil
            default:
                learner.practiceJournal = NativePracticeJournal(
                    startedAt: Date(), hasLegacyHistory: true)
            }
            var gate = NativePrivateCloudGate()
            XCTAssertThrowsError(try gate.proposeExplicitOptIn(
                approved: true, verifiedOpaqueAccountKey: keyA,
                learner: learner, lessons: lessons, regions: regions))
            XCTAssertNil(gate.scope)
            XCTAssertEqual(gate.phase, .off)
        }
    }

    func testUnverifiedAccountStringsAndAppleEmailAreRejected() throws {
        let (lessons, regions) = try sources()
        let learner = linkedLearner()
        let wrongKeys: [String?] = [nil, "", "a", "person@example.com", "account with spaces"]
        for wrongKey in wrongKeys {
            var gate = NativePrivateCloudGate()
            XCTAssertThrowsError(try gate.proposeExplicitOptIn(
                approved: true, verifiedOpaqueAccountKey: wrongKey,
                learner: learner, lessons: lessons, regions: regions))
            XCTAssertNil(gate.scope)
        }
    }

    func testAccountChangePausesAllRemoteUseUntilExplicitSameOwnerResume() throws {
        let learner = linkedLearner()
        var gate = NativePrivateCloudGate()
        try activate(&gate, learner: learner)
        let initial = try head(gate)
        XCTAssertNoThrow(try gate.authorizeRemoteOperation(
            verifiedOpaqueAccountKey: keyA, learner: learner, snapshot: initial))
        gate.observeAccount(keyB)
        XCTAssertEqual(gate.phase, .pausedAccountChange)
        XCTAssertThrowsError(try gate.authorizeRemoteOperation(
            verifiedOpaqueAccountKey: keyB, learner: learner, snapshot: initial))
        gate.observeAccount(keyA)
        XCTAssertEqual(gate.phase, .pausedAccountChange,
                       "Returning Apple account must not silently restart writes")
        XCTAssertThrowsError(try gate.resumeSameAccount(
            approved: false, verifiedOpaqueAccountKey: keyA))
        XCTAssertThrowsError(try gate.resumeSameAccount(
            approved: true, verifiedOpaqueAccountKey: keyB))
        try gate.resumeSameAccount(
            approved: true, verifiedOpaqueAccountKey: keyA)
        XCTAssertNoThrow(try gate.authorizeRemoteOperation(
            verifiedOpaqueAccountKey: keyA, learner: learner, snapshot: initial))
    }

    func testOptOutKeepsLocalHistoryAndRequiresFreshApprovalForResume() throws {
        let learner = linkedLearner()
        var gate = NativePrivateCloudGate()
        try activate(&gate, learner: learner)
        let copy = learner
        try gate.optOutKeepLocalData()
        XCTAssertEqual(gate.phase, .off)
        XCTAssertEqual(copy.localID, learner.localID)
        XCTAssertEqual(copy.practiceJournal?.epochID, learner.practiceJournal?.epochID)
        XCTAssertThrowsError(try gate.authorizeRemoteOperation(
            verifiedOpaqueAccountKey: keyA, learner: learner,
            snapshot: head(gate)))
        XCTAssertThrowsError(try gate.resumeSameAccount(
            approved: false, verifiedOpaqueAccountKey: keyA))
        try gate.resumeSameAccount(
            approved: true, verifiedOpaqueAccountKey: keyA)
        XCTAssertEqual(gate.phase, .active)
    }

    func testForeignLearnerOrEpochCannotReadOrWritePrivateHistory() throws {
        let learner = linkedLearner()
        var gate = NativePrivateCloudGate()
        try activate(&gate, learner: learner)
        let snapshot = try head(gate)
        var differentLearner = learner
        differentLearner.localID = UUID()
        XCTAssertThrowsError(try gate.authorizeRemoteOperation(
            verifiedOpaqueAccountKey: keyA, learner: differentLearner, snapshot: snapshot))
        var wrongEpoch = learner
        wrongEpoch.linkedUTCEpoch = UUID()
        XCTAssertThrowsError(try gate.authorizeRemoteOperation(
            verifiedOpaqueAccountKey: keyA, learner: wrongEpoch, snapshot: snapshot))
        let foreignScope = NativePrivateCloudScope(
            accountKey: keyB, learnerID: learner.localID,
            journalEpoch: try XCTUnwrap(learner.linkedUTCEpoch))
        XCTAssertThrowsError(try gate.authorizeRemoteOperation(
            verifiedOpaqueAccountKey: keyA, learner: learner,
            snapshot: NativePrivateCloudSnapshot(scope: foreignScope, generation: 0)))
    }

    func testRemoteEraseRequestLocksAllUploadsUntilAuthoritativeAck() throws {
        let learner = linkedLearner()
        var gate = NativePrivateCloudGate()
        try activate(&gate, learner: learner)
        let old = try head(gate)
        XCTAssertThrowsError(try gate.requestRemoteErase(
            approved: false, verifiedOpaqueAccountKey: keyA))
        let tombstone = try gate.requestRemoteErase(
            approved: true, verifiedOpaqueAccountKey: keyA)
        XCTAssertEqual(tombstone.generation, 1)
        XCTAssertEqual(gate.phase, .deletionPending)
        XCTAssertThrowsError(try gate.authorizeRemoteOperation(
            verifiedOpaqueAccountKey: keyA, learner: learner, snapshot: old))
        XCTAssertThrowsError(try gate.optOutKeepLocalData(),
                             "Cannot discard an unacknowledged server deletion")
        XCTAssertThrowsError(try gate.acknowledgeServerTombstone(
            NativePrivateCloudTombstone(scope: tombstone.scope, generation: 0)))
        XCTAssertEqual(gate.phase, .deletionPending)
        try gate.acknowledgeServerTombstone(tombstone)
        XCTAssertEqual(gate.phase, .remotelyDeleted)
        XCTAssertEqual(gate.knownGeneration, 1)
        XCTAssertThrowsError(try gate.authorizeRemoteOperation(
            verifiedOpaqueAccountKey: keyA, learner: learner, snapshot: old))
        XCTAssertThrowsError(try gate.resumeSameAccount(
            approved: true, verifiedOpaqueAccountKey: keyA))
        XCTAssertEqual(learner.localID, tombstone.scope.learnerID,
                       "Remote erase never implicitly wipes the local learner")
    }

    func testServerConfirmedDeleteOnSecondPhoneBlocksStaleResurrection() throws {
        let learner = linkedLearner()
        var phoneOne = NativePrivateCloudGate()
        try activate(&phoneOne, learner: learner)
        var phoneTwo = phoneOne
        let stale = try head(phoneTwo)
        let serverRequest = try phoneOne.requestRemoteErase(
            approved: true, verifiedOpaqueAccountKey: keyA)
        try phoneOne.acknowledgeServerTombstone(serverRequest)
        try phoneTwo.observeVerifiedServerDeletion(serverRequest)
        XCTAssertEqual(phoneTwo.phase, .remotelyDeleted)
        XCTAssertThrowsError(try phoneTwo.authorizeRemoteOperation(
            verifiedOpaqueAccountKey: keyA, learner: learner, snapshot: stale))
        XCTAssertThrowsError(try phoneTwo.proposeExplicitOptIn(
            approved: true, verifiedOpaqueAccountKey: keyA,
            learner: learner, lessons: sources().0, regions: sources().1))
    }

    func testForeignTombstonesCannotEraseAnotherAccountOrLearner() throws {
        let learner = linkedLearner()
        var gate = NativePrivateCloudGate()
        try activate(&gate, learner: learner)
        let different = NativePrivateCloudScope(accountKey: keyB,
            learnerID: learner.localID, journalEpoch: try XCTUnwrap(learner.linkedUTCEpoch))
        XCTAssertThrowsError(try gate.observeVerifiedServerDeletion(
            NativePrivateCloudTombstone(scope: different, generation: 999)))
        XCTAssertEqual(gate.phase, .active)
        XCTAssertEqual(gate.knownGeneration, 0)
    }

    func testCloudGateIsNotIncludedInPlaintextLearnerExport() throws {
        let learner = linkedLearner()
        var gate = NativePrivateCloudGate()
        try activate(&gate, learner: learner)
        let archive = LocalProgressArchive(
            profile: learner,
            sourceLessonIDs: try CatalogLoader.load().map(\.id))
        let text = try XCTUnwrap(String(data: archive.encoded(), encoding: .utf8))
        XCTAssertFalse(text.contains(keyA))
        XCTAssertFalse(text.contains("NativePrivateCloudScope"))
        XCTAssertFalse(text.contains("requestedTombstone"))
        XCTAssertEqual(gate.phase, .active)
    }
}
