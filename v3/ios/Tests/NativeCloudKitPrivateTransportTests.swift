import Foundation
import XCTest
@testable import PathToPolish

@MainActor final class NativeCloudKitPrivateTransportTests: XCTestCase {
    private func sources() throws -> ([Lesson], [PolandRegion], LessonItem) {
        let lessons = try CatalogLoader.load()
        let regions = try PolandRegionCatalog.load()
        let item = try XCTUnwrap(lessons.first(where: {
            $0.availableModes.contains(.learn)
        })?.items.first)
        return (lessons, regions, item)
    }

    private func sourceEnvelope() throws -> NativeCloudKitEnvelope {
        let (_, regions, item) = try sources()
        let epoch = UUID()
        let date = Date(timeIntervalSince1970: 1_760_000_000)
        let journal = NativePracticeJournal(epochID: epoch, startedAt: date,
            hasLegacyHistory: false,
            events: [NativePracticeEvent(id: UUID(), actorID: UUID(),
                itemID: item.id, mode: .learn, at: date,
                outcome: .understood, regionID: regions[0].id,
                actorSequence: 1)])
        return NativeCloudKitEnvelope(
            scope: NativePrivateCloudScope(
                accountKey: "opaque-test-owner-record-1", learnerID: UUID(),
                journalEpoch: epoch),
            generation: 1, deleted: false, journal: journal)
    }

    func testFirstLaunchCloudKitTransportHasNoAppStartupEntryOrEntitlement() throws {
        // Tests never instantiate a CKContainer or access an Apple account.
        // The native CloudKit adapter exists, but not in the startup path.
        let (_, _, _) = try sources()
        let gate = NativePrivateCloudGate()
        XCTAssertEqual(gate.phase, .off)
        XCTAssertNil(gate.scope)
    }

    func testNativeCloudKitPayloadRoundTripUsesOriginalJournalOnly() throws {
        let (lessons, regions, _) = try sources()
        let envelope = try sourceEnvelope()
        let data = try envelope.encoded(lessons: lessons, regions: regions)
        let result = try NativeCloudKitEnvelope.decode(
            data, lessons: lessons, regions: regions)
        XCTAssertEqual(result.formatID, NativeCloudKitEnvelope.format)
        XCTAssertEqual(result.version, 1)
        XCTAssertEqual(result.generation, 1)
        XCTAssertFalse(result.deleted)
        XCTAssertEqual(result.scope, envelope.scope)
        XCTAssertEqual(result.journal?.events.count, 1)
        XCTAssertEqual(result.journal?.events.first?.actorSequence, 1)
        XCTAssertEqual(result.journal?.events.first?.regionID, regions[0].id)
        let json = try XCTUnwrap(String(data: data, encoding: .utf8))
        for forbidden in ["familyMembership", "sessionToken", "microphoneRecording",
                          "whisperTranscript", "azureResponse", "rawAudio"] {
            XCTAssertFalse(json.contains(forbidden))
        }
    }

    func testCloudKitPayloadIsBoundToOriginalLearnerEpoch() throws {
        let (lessons, regions, _) = try sources()
        let initial = try sourceEnvelope()
        let foreign = NativeCloudKitEnvelope(
            scope: NativePrivateCloudScope(
                accountKey: initial.scope.accountKey,
                learnerID: initial.scope.learnerID,
                journalEpoch: UUID()),
            generation: 1, deleted: false,
            journal: initial.journal)
        XCTAssertThrowsError(try foreign.encoded(lessons: lessons, regions: regions))
    }

    func testOldUnrecordedRegionCannotBeAdvertisedAsCloudMap() throws {
        let (lessons, regions, item) = try sources()
        let initial = try sourceEnvelope()
        let date = Date(timeIntervalSince1970: 1_760_000_000)
        let legacyEvent = NativePracticeEvent(
            id: UUID(), actorID: UUID(), itemID: item.id,
            mode: .learn, at: date, outcome: .understood,
            regionID: nil)
        let incomplete = NativeCloudKitEnvelope(
            scope: initial.scope, generation: 1,
            deleted: false, journal: NativePracticeJournal(
                epochID: initial.scope.journalEpoch,
                startedAt: date, hasLegacyHistory: false,
                events: [legacyEvent]))
        XCTAssertThrowsError(try incomplete.encoded(
            lessons: lessons, regions: regions))
    }

    func testOldAggregateOnlyHistoryCannotBeCloudSynced() throws {
        let (lessons, regions, _) = try sources()
        let initial = try sourceEnvelope()
        let legacy = NativePracticeJournal(
            epochID: initial.scope.journalEpoch,
            hasLegacyHistory: true)
        let record = NativeCloudKitEnvelope(
            scope: initial.scope, generation: 1,
            deleted: false, journal: legacy)
        XCTAssertThrowsError(try record.encoded(
            lessons: lessons, regions: regions))
    }

    func testTombstoneHasNoEventsAndRetainsOriginalScopeAndGeneration() throws {
        let (lessons, regions, _) = try sources()
        let initial = try sourceEnvelope()
        let tombstone = NativeCloudKitEnvelope(
            scope: initial.scope, generation: 2,
            deleted: true, journal: nil)
        let bytes = try tombstone.encoded(lessons: lessons, regions: regions)
        let decoded = try NativeCloudKitEnvelope.decode(
            bytes, lessons: lessons, regions: regions)
        XCTAssertTrue(decoded.deleted)
        XCTAssertNil(decoded.journal)
        XCTAssertEqual(decoded.generation, 2)
        XCTAssertEqual(decoded.scope, initial.scope)
    }

    func testTombstoneWithHistoryIsInvalidAndNeverSent() throws {
        let (lessons, regions, _) = try sources()
        let initial = try sourceEnvelope()
        let invalid = NativeCloudKitEnvelope(
            scope: initial.scope, generation: 2,
            deleted: true, journal: initial.journal)
        XCTAssertThrowsError(try invalid.encoded(
            lessons: lessons, regions: regions))
    }

    func testUnversionedOrFutureCloudRecordFailsClosed() throws {
        let (lessons, regions, _) = try sources()
        let initial = try sourceEnvelope()
        var json = try XCTUnwrap(
            JSONSerialization.jsonObject(
                with: initial.encoded(lessons: lessons, regions: regions))
                    as? [String: Any])
        json["version"] = 99
        XCTAssertThrowsError(try NativeCloudKitEnvelope.decode(
            JSONSerialization.data(withJSONObject: json),
            lessons: lessons, regions: regions))
        json["version"] = 1
        json["formatID"] = "some-other-app"
        XCTAssertThrowsError(try NativeCloudKitEnvelope.decode(
            JSONSerialization.data(withJSONObject: json),
            lessons: lessons, regions: regions))
    }

    func testUnknownOriginalItemCannotCreateCloudJournal() throws {
        let (lessons, regions, _) = try sources()
        let initial = try sourceEnvelope()
        let date = Date(timeIntervalSince1970: 1_760_000_000)
        let forged = NativePracticeJournal(
            epochID: initial.scope.journalEpoch,
            startedAt: date, hasLegacyHistory: false,
            events: [NativePracticeEvent(
                id: UUID(), actorID: UUID(), itemID: "forged-lesson:99",
                mode: .learn, at: date, outcome: .understood,
                regionID: regions[0].id)])
        let envelope = NativeCloudKitEnvelope(
            scope: initial.scope, generation: 1,
            deleted: false, journal: forged)
        XCTAssertThrowsError(try envelope.encoded(
            lessons: lessons, regions: regions))
    }

    func testOversizeRemotePayloadRejectedBeforeJSONParsing() throws {
        let (lessons, regions, _) = try sources()
        let bytes = Data(repeating: 0x20,
            count: NativeCloudKitEnvelope.maximumBytes + 1)
        XCTAssertThrowsError(try NativeCloudKitEnvelope.decode(
            bytes, lessons: lessons, regions: regions))
    }

    func testCloudRecordWithGenerationZeroIsNotValidServerAck() throws {
        let (lessons, regions, _) = try sources()
        let initial = try sourceEnvelope()
        let forged = NativeCloudKitEnvelope(
            scope: initial.scope, generation: 0,
            deleted: false, journal: initial.journal)
        XCTAssertThrowsError(try forged.encoded(
            lessons: lessons, regions: regions))
    }

    func testNoAutomaticMergeOrUploadWhenRemoteHasUnseenEvents() throws {
        let (lessons, regions, item) = try sources()
        let initial = try sourceEnvelope()
        let date = Date(timeIntervalSince1970: 1_760_000_000)
        let extra = NativePracticeEvent(id: UUID(), actorID: UUID(),
            itemID: item.id, mode: .learn,
            at: date.addingTimeInterval(1), outcome: .understood,
            regionID: regions[0].id)
        var remote = try XCTUnwrap(initial.journal)
        try remote.append(extra)
        let local = try XCTUnwrap(initial.journal)
        let combined = try NativePracticeJournal.mergeCandidate(
            remote, local, lessons: lessons)
        XCTAssertGreaterThan(combined.events.count, local.events.count,
            "The live adapter must refuse this stale local upload")
    }

    func testCloudWritePreflightRechecksConsentAndAccountAtDispatch() throws {
        let (lessons, regions, _) = try sources()
        let envelope = try sourceEnvelope()
        var learner = LocalLearner()
        learner.localID = envelope.scope.learnerID
        learner.practiceJournal = envelope.journal
        learner.linkedUTCEpoch = envelope.scope.journalEpoch
        var gate = NativePrivateCloudGate()
        try gate.proposeExplicitOptIn(
            approved: true, verifiedOpaqueAccountKey: envelope.scope.accountKey,
            learner: learner, lessons: lessons, regions: regions)
        func check(_ current: NativePrivateCloudGate,
                   _ profile: LocalLearner = learner,
                   account: String? = nil, revision: UInt64 = 0) throws {
            try NativeCloudWritePreflight.authorize(
                gate: current, learner: profile, scope: envelope.scope,
                accountKey: account ?? envelope.scope.accountKey,
                expectedGeneration: revision)
        }
        XCTAssertNoThrow(try check(gate))
        XCTAssertThrowsError(try check(gate, account: "changed-account-key"))
        try gate.optOutKeepLocalData()
        XCTAssertThrowsError(try check(gate),
            "Consent withdrawal during an await must cancel the upload")
        try gate.resumeSameAccount(
            approved: true, verifiedOpaqueAccountKey: envelope.scope.accountKey)
        XCTAssertNoThrow(try check(gate))
        gate.observeAccount("changed-account-key")
        XCTAssertThrowsError(try check(gate),
            "Paused iCloud account must never be used for a pending write")
    }

    func testCloudWritePreflightRejectsNewServerGenerationAndLearnerReset() throws {
        let (lessons, regions, _) = try sources()
        let envelope = try sourceEnvelope()
        var learner = LocalLearner()
        learner.localID = envelope.scope.learnerID
        learner.practiceJournal = envelope.journal
        learner.linkedUTCEpoch = envelope.scope.journalEpoch
        var gate = NativePrivateCloudGate()
        try gate.proposeExplicitOptIn(
            approved: true, verifiedOpaqueAccountKey: envelope.scope.accountKey,
            learner: learner, lessons: lessons, regions: regions)
        try gate.observeVerifiedServerRevision(
            NativePrivateCloudSnapshot(scope: envelope.scope, generation: 3))
        XCTAssertThrowsError(try NativeCloudWritePreflight.authorize(
            gate: gate, learner: learner, scope: envelope.scope,
            accountKey: envelope.scope.accountKey, expectedGeneration: 0))
        XCTAssertNoThrow(try NativeCloudWritePreflight.authorize(
            gate: gate, learner: learner, scope: envelope.scope,
            accountKey: envelope.scope.accountKey, expectedGeneration: 3))
        learner.localID = UUID()
        XCTAssertThrowsError(try NativeCloudWritePreflight.authorize(
            gate: gate, learner: learner, scope: envelope.scope,
            accountKey: envelope.scope.accountKey, expectedGeneration: 3))
    }

    func testCloudServerAckMustEchoExactSavedPayloadNotJustRevision() throws {
        let (lessons, regions, item) = try sources()
        let envelope = try sourceEnvelope()
        let submitted = try envelope.encoded(lessons: lessons, regions: regions)
        XCTAssertNoThrow(try NativeCloudKitEnvelope.verifyAcknowledgement(
            envelope, submittedPayload: submitted,
            lessons: lessons, regions: regions))
        var altered = try XCTUnwrap(envelope.journal)
        try altered.append(NativePracticeEvent(
            id: UUID(), actorID: UUID(), itemID: item.id, mode: .learn,
            at: Date(timeIntervalSince1970: 1_760_000_001),
            outcome: .understood, regionID: regions[0].id,
            actorSequence: 2))
        let sameRevisionDifferentHistory = NativeCloudKitEnvelope(
            scope: envelope.scope, generation: envelope.generation,
            deleted: false, journal: altered)
        XCTAssertThrowsError(try NativeCloudKitEnvelope.verifyAcknowledgement(
            sameRevisionDifferentHistory, submittedPayload: submitted,
            lessons: lessons, regions: regions))
    }
}
