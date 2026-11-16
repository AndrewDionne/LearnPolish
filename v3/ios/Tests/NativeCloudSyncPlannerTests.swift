import Foundation
import XCTest
@testable import PathToPolish

@MainActor final class NativeCloudSyncPlannerTests: XCTestCase {
    private let start = Date(timeIntervalSince1970: 1_760_000_000)

    private func source() throws -> ([Lesson], [PolandRegion], LessonItem) {
        let lessons = try CatalogLoader.load()
        let regions = try PolandRegionCatalog.load()
        let item = try XCTUnwrap(lessons.first {
            $0.availableModes.contains(.learn)
        }?.items.first)
        return (lessons, regions, item)
    }

    private func entry(_ item: LessonItem, region: PolandRegion,
                       id: UUID = UUID(), actor: UUID = UUID(),
                       seconds: TimeInterval = 1,
                       outcome: NativePracticeEvent.Outcome = .understood)
        -> NativePracticeEvent {
        NativePracticeEvent(id: id, actorID: actor, itemID: item.id,
                            mode: .learn, at: start.addingTimeInterval(seconds),
                            outcome: outcome, regionID: region.id,
                            actorSequence: nil)
    }

    private func profile(_ journal: NativePracticeJournal) -> LocalLearner {
        var learner = LocalLearner()
        learner.localID = UUID(uuidString: "aaaaaaaa-0000-0000-0000-000000000001")!
        learner.practiceJournal = journal
        learner.linkedUTCEpoch = journal.epochID
        return learner
    }

    private func journal(_ entries: [NativePracticeEvent],
                         epoch: UUID = UUID(), legacy: Bool = false)
        -> NativePracticeJournal {
        NativePracticeJournal(epochID: epoch, startedAt: start,
                              hasLegacyHistory: legacy, events: entries)
    }

    private func scope(_ learner: LocalLearner) -> NativePrivateCloudScope {
        NativePrivateCloudScope(accountKey: "opaque-private-account-test",
            learnerID: learner.localID,
            journalEpoch: learner.linkedUTCEpoch!)
    }

    private func remote(_ learner: LocalLearner, entries: [NativePracticeEvent],
                        generation: UInt64 = 1, deleted: Bool = false)
        -> NativeCloudKitEnvelope {
        let current = learner.practiceJournal!
        return NativeCloudKitEnvelope(
            scope: scope(learner), generation: generation,
            deleted: deleted,
            journal: deleted ? nil : journal(entries, epoch: current.epochID))
    }

    func testFreshLinkedOwnerMayCreateFirstRecordButNeverFirstLaunchAnonymousLearner() throws {
        let (lessons, regions, item) = try source()
        let original = journal([entry(item, region: regions[0])])
        let learner = profile(original)
        XCTAssertEqual(try NativeCloudSyncPlanner.decide(
            local: learner, scope: scope(learner), remote: nil,
            knownGeneration: 0, lessons: lessons, regions: regions),
                       .create)
        var unlinked = learner
        unlinked.linkedUTCEpoch = nil
        XCTAssertThrowsError(try NativeCloudSyncPlanner.decide(
            local: unlinked, scope: scope(learner), remote: nil,
            knownGeneration: 0, lessons: lessons, regions: regions))
    }

    func testPreviouslySeenRemoteRecordCannotBeRecreatedWhenMissing() throws {
        let (lessons, regions, item) = try source()
        let learner = profile(journal([entry(item, region: regions[0])]))
        XCTAssertThrowsError(try NativeCloudSyncPlanner.decide(
            local: learner, scope: scope(learner), remote: nil,
            knownGeneration: 2, lessons: lessons, regions: regions))
    }

    func testIdenticalHistoryRequiresNoCloudWriteOrGenerationIncrement() throws {
        let (lessons, regions, item) = try source()
        let saved = entry(item, region: regions[0])
        let learner = profile(journal([saved]))
        XCTAssertEqual(try NativeCloudSyncPlanner.decide(
            local: learner, scope: scope(learner),
            remote: remote(learner, entries: [saved], generation: 4),
            knownGeneration: 3, lessons: lessons, regions: regions),
                       .alreadyCurrent)
    }

    func testLocalOnlyNewEventsPermitConditionalUpload() throws {
        let (lessons, regions, item) = try source()
        let a = entry(item, region: regions[0], seconds: 1)
        let b = entry(item, region: regions[0], seconds: 2)
        let learner = profile(journal([a,b]))
        XCTAssertEqual(try NativeCloudSyncPlanner.decide(
            local: learner, scope: scope(learner),
            remote: remote(learner, entries: [a], generation: 1),
            knownGeneration: 0, lessons: lessons, regions: regions),
                       .uploadLocalAdditions(count: 1))
    }

    func testRemoteOnlyNewEventsRequireReviewWithoutOverwriting() throws {
        let (lessons, regions, item) = try source()
        let a = entry(item, region: regions[0], seconds: 1)
        let b = entry(item, region: regions[1], seconds: 2)
        let learner = profile(journal([a]))
        let originalEventIDs = learner.practiceJournal!.events.map(\.id)
        XCTAssertEqual(try NativeCloudSyncPlanner.decide(
            local: learner, scope: scope(learner),
            remote: remote(learner, entries: [a,b], generation: 5),
            knownGeneration: 3, lessons: lessons, regions: regions),
                       .reviewRemoteAdditions(count: 1))
        XCTAssertEqual(learner.practiceJournal?.events.map(\.id), originalEventIDs)
    }

    func testDivergentPhonesBothHavingNewWorkMustReviewRemoteBeforeUpload() throws {
        let (lessons, regions, item) = try source()
        let shared = entry(item, region: regions[0], seconds: 1)
        let phoneOne = entry(item, region: regions[0], seconds: 2)
        let phoneTwo = entry(item, region: regions[1], seconds: 3)
        let learner = profile(journal([shared, phoneOne]))
        XCTAssertEqual(try NativeCloudSyncPlanner.decide(
            local: learner, scope: scope(learner),
            remote: remote(learner, entries: [shared, phoneTwo], generation: 6),
            knownGeneration: 4, lessons: lessons, regions: regions),
                       .reviewRemoteAdditions(count: 1))
    }

    func testSameUUIDWithChangedPayloadFailsRatherThanPickingWinner() throws {
        let (lessons, regions, item) = try source()
        let id = UUID()
        let actor = UUID()
        let valid = entry(item, region: regions[0], id: id, actor: actor,
                          outcome: .understood)
        let forged = entry(item, region: regions[0], id: id, actor: actor,
                           outcome: .needsPractice)
        let learner = profile(journal([valid]))
        XCTAssertThrowsError(try NativeCloudSyncPlanner.decide(
            local: learner, scope: scope(learner),
            remote: remote(learner, entries: [forged]),
            knownGeneration: 0, lessons: lessons, regions: regions))
    }

    func testAuthoritativeTombstoneCannotBeOverwrittenByOfflineHistory() throws {
        let (lessons, regions, item) = try source()
        let learner = profile(journal([entry(item, region: regions[0])]))
        XCTAssertThrowsError(try NativeCloudSyncPlanner.decide(
            local: learner, scope: scope(learner),
            remote: remote(learner, entries: [], generation: 9, deleted: true),
            knownGeneration: 3, lessons: lessons, regions: regions))
    }

    func testForeignAnonymousOwnerCannotAccessAnotherOwnersHistory() throws {
        let (lessons, regions, item) = try source()
        let learner = profile(journal([entry(item, region: regions[0])]))
        let other = NativePrivateCloudScope(accountKey: "other-opaque-account-id",
                                            learnerID: UUID(),
                                            journalEpoch: scope(learner).journalEpoch)
        XCTAssertThrowsError(try NativeCloudSyncPlanner.decide(
            local: learner, scope: other, remote: nil,
            knownGeneration: 0, lessons: lessons, regions: regions))
        let wrongRemote = NativeCloudKitEnvelope(scope: other,
            generation: 2, deleted: true, journal: nil)
        XCTAssertThrowsError(try NativeCloudSyncPlanner.decide(
            local: learner, scope: scope(learner), remote: wrongRemote,
            knownGeneration: 0, lessons: lessons, regions: regions))
    }

    func testServerRevisionRollbackIsNotAValidUploadPreflight() throws {
        let (lessons, regions, item) = try source()
        let a = entry(item, region: regions[0])
        let learner = profile(journal([a]))
        XCTAssertThrowsError(try NativeCloudSyncPlanner.decide(
            local: learner, scope: scope(learner),
            remote: remote(learner, entries: [a], generation: 2),
            knownGeneration: 3, lessons: lessons, regions: regions))
    }

    func testLegacyOrUnrecordedRegionHistoryCannotBeUploaded() throws {
        let (lessons, regions, item) = try source()
        let a = entry(item, region: regions[0])
        let legacy = profile(journal([a], legacy: true))
        XCTAssertThrowsError(try NativeCloudSyncPlanner.decide(
            local: legacy, scope: scope(legacy), remote: nil,
            knownGeneration: 0, lessons: lessons, regions: regions))
        let unlocated = NativePracticeEvent(
            id: a.id, actorID: a.actorID, itemID: a.itemID,
            mode: a.mode, at: a.at, outcome: a.outcome, regionID: nil)
        let incomplete = profile(journal([unlocated]))
        XCTAssertThrowsError(try NativeCloudSyncPlanner.decide(
            local: incomplete, scope: scope(incomplete), remote: nil,
            knownGeneration: 0, lessons: lessons, regions: regions))
    }

    func testOriginalSourceValidationRefusesForgedRemoteEvent() throws {
        let (lessons, regions, item) = try source()
        let real = entry(item, region: regions[0])
        let learner = profile(journal([real]))
        let forged = NativePracticeEvent(
            id: UUID(), actorID: UUID(), itemID: "not-original-source:99",
            mode: .learn, at: start.addingTimeInterval(3),
            outcome: .understood, regionID: regions[0].id)
        XCTAssertThrowsError(try NativeCloudSyncPlanner.decide(
            local: learner, scope: scope(learner),
            remote: remote(learner, entries: [forged]),
            knownGeneration: 0, lessons: lessons, regions: regions))
    }
}
