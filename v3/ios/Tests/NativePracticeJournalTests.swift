import XCTest
@testable import PathToPolish

@MainActor final class NativePracticeJournalTests: XCTestCase {
    private func catalog() throws -> [Lesson] { try CatalogLoader.load() }
    private func item() throws -> LessonItem {
        try XCTUnwrap(catalog().first(where: { $0.availableModes.contains(.learn) })?.items.first)
    }
    private func storage() -> (URL, URL) {
        let directory = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        return (directory, directory.appendingPathComponent("profile.json"))
    }
    private func makeEvent(id: UUID = UUID(), actorID: UUID = UUID(),
                           itemID: String, at: Date,
                           mode: PracticeMode = .learn,
                           outcome: NativePracticeEvent.Outcome = .understood) -> NativePracticeEvent {
        NativePracticeEvent(id: id, actorID: actorID,
                            itemID: itemID, mode: mode, at: at, outcome: outcome)
    }

    func testRealAttemptsAddExactlyOneUniqueEventAndPreserveXPAndReview() throws {
        let (directory, path) = storage()
        defer { try? FileManager.default.removeItem(at: directory) }
        let store = LocalLearningStore(storageURL: path)
        let source = try item()
        store.recordAttempt(item: source, mode: .learn, understood: true)
        store.recordAttempt(item: source, mode: .speak, understood: nil)
        let log = try XCTUnwrap(store.profile.practiceJournal)
        XCTAssertEqual(log.schemaVersion, 1)
        XCTAssertFalse(log.hasLegacyHistory)
        XCTAssertEqual(log.events.count, 2)
        XCTAssertEqual(Set(log.events.map(\.id)).count, 2)
        XCTAssertTrue(log.events.allSatisfy { $0.itemID == source.id })
        XCTAssertTrue(log.events.allSatisfy { $0.actorID == store.profile.localID })
        XCTAssertEqual(log.events.map(\.mode), [.learn, .speak])
        XCTAssertEqual(log.events.map(\.outcome), [.understood, .recorded])
        XCTAssertEqual(store.record(for: source, mode: .learn).attempts, 1)
        XCTAssertEqual(store.record(for: source, mode: .speak).attempts, 1)
        XCTAssertEqual(store.record(for: source, mode: .speak).completed, 0)
        XCTAssertEqual(store.expedition.totalXP, 20)
        let projected = try log.projectedRecords(lessons: catalog())
        XCTAssertEqual(projected["learn:" + source.id]?.attempts, 1)
        XCTAssertEqual(projected["learn:" + source.id]?.completed, 1)
        XCTAssertEqual(projected["speak:" + source.id]?.attempts, 1)
        XCTAssertEqual(projected["speak:" + source.id]?.completed, 0)
        XCTAssertEqual(projected["learn:" + source.id]?.reviewLevel, 1)
        XCTAssertEqual(projected["learn:" + source.id]?.nextReview,
                       store.record(for: source, mode: .learn).nextReview)
    }

    func testJournalSurvivesRestartAndIsIncludedInManualExportOnly() throws {
        let (directory, path) = storage()
        defer { try? FileManager.default.removeItem(at: directory) }
        let learner = LocalLearningStore(storageURL: path)
        let source = try item()
        learner.recordAttempt(item: source, mode: .learn, understood: false)
        let epoch = try XCTUnwrap(learner.profile.practiceJournal?.epochID)
        let uuid = try XCTUnwrap(learner.profile.practiceJournal?.events.first?.id)
        let reopened = LocalLearningStore(storageURL: path)
        XCTAssertEqual(reopened.profile.practiceJournal?.events.first?.id, uuid)
        XCTAssertEqual(reopened.profile.practiceJournal?.epochID, epoch)
        XCTAssertNil(reopened.catalogError)
        let export = try reopened.makeLocalExport().archive
        XCTAssertEqual(export.profile.practiceJournal?.events.first?.id, uuid)
        XCTAssertEqual(export.profile.practiceJournal?.epochID, epoch)
        XCTAssertEqual(reopened.dueReviews.count, 1)
    }

    func testLegacyAggregateIsNeverRecreatedAsInventedHistoricalEvents() throws {
        let (directory, path) = storage()
        defer { try? FileManager.default.removeItem(at: directory) }
        try FileManager.default.createDirectory(at: directory,
                                                withIntermediateDirectories: true)
        let source = try item()
        var historical = LocalLearner()
        historical.records["learn:" + source.id] = PracticeRecord(attempts: 7,
            completed: 6, reviewLevel: 2, lastAttempt: Date(timeIntervalSince1970: 1_750_000_000),
            nextReview: Date(timeIntervalSince1970: 1_750_250_000))
        let encoder = JSONEncoder()
        encoder.dateEncodingStrategy = .iso8601
        try encoder.encode(historical).write(to: path)
        let store = LocalLearningStore(storageURL: path)
        XCTAssertNil(store.profile.practiceJournal)
        XCTAssertEqual(store.record(for: source, mode: .learn).attempts, 7)
        store.recordAttempt(item: source, mode: .learn, understood: true)
        let journal = try XCTUnwrap(store.profile.practiceJournal)
        XCTAssertTrue(journal.hasLegacyHistory)
        XCTAssertEqual(journal.events.count, 1)
        XCTAssertEqual(store.record(for: source, mode: .learn).attempts, 8)
        XCTAssertThrowsError(try journal.projectedRecords(lessons: catalog()))
        XCTAssertThrowsError(try NativePracticeJournal.mergeCandidate(
            journal, journal, lessons: catalog()))
        let reopened = LocalLearningStore(storageURL: path)
        XCTAssertTrue(reopened.profile.practiceJournal?.hasLegacyHistory == true)
        XCTAssertEqual(reopened.record(for: source, mode: .learn).attempts, 8)
    }

    func testOfflineTwoDeviceCandidateMergeIsCommutativeIdempotentAndSourceBound() throws {
        let source = try item()
        let start = Date(timeIntervalSince1970: 1_760_000_000)
        let sameEpoch = UUID()
        let alice = makeEvent(itemID: source.id, at: start.addingTimeInterval(2),
                              outcome: .needsPractice)
        let bob = makeEvent(itemID: source.id, at: start.addingTimeInterval(4),
                            outcome: .understood)
        let x = NativePracticeJournal(epochID: sameEpoch, startedAt: start,
                                      hasLegacyHistory: false, events: [alice])
        let y = NativePracticeJournal(epochID: sameEpoch, startedAt: start,
                                      hasLegacyHistory: false, events: [bob])
        let xy = try NativePracticeJournal.mergeCandidate(x, y, lessons: catalog())
        let yx = try NativePracticeJournal.mergeCandidate(y, x, lessons: catalog())
        XCTAssertEqual(xy.events, yx.events)
        XCTAssertEqual(xy.events.count, 2)
        XCTAssertEqual(try NativePracticeJournal.mergeCandidate(xy, xy,
                                                                 lessons: catalog()).events,
                       xy.events)
        let reduced = try xy.projectedRecords(lessons: catalog())
        XCTAssertEqual(reduced["learn:" + source.id]?.attempts, 2)
        XCTAssertEqual(reduced["learn:" + source.id]?.completed, 1)
        XCTAssertEqual(reduced["learn:" + source.id]?.reviewLevel, 1)
        XCTAssertEqual(reduced["learn:" + source.id]?.nextReview,
                       bob.at.addingTimeInterval(86_400))
        XCTAssertEqual(reduced["learn:" + source.id]?.lastAttempt, bob.at)
    }

    func testUnrelatedDevicesRequireExplicitSharedEpochAndNeverOverwrite() throws {
        let source = try item()
        let time = Date(timeIntervalSince1970: 1_760_000_000)
        let left = NativePracticeJournal(startedAt: time, hasLegacyHistory: false,
                                         events: [makeEvent(itemID: source.id, at: time)])
        let right = NativePracticeJournal(startedAt: time, hasLegacyHistory: false,
                                          events: [makeEvent(itemID: source.id, at: time)])
        XCTAssertNotEqual(left.epochID, right.epochID)
        XCTAssertThrowsError(try NativePracticeJournal.mergeCandidate(
            left, right, lessons: catalog()))
        XCTAssertEqual(left.events.count, 1)
        XCTAssertEqual(right.events.count, 1)
    }

    func testSameUUIDDifferentPayloadIsAHardConflictNotAWinningWriter() throws {
        let source = try item()
        let at = Date(timeIntervalSince1970: 1_760_000_000)
        let uuid = UUID()
        let epoch = UUID()
        let x = NativePracticeJournal(epochID: epoch, startedAt: at,
            hasLegacyHistory: false, events: [makeEvent(id: uuid, itemID: source.id, at: at,
                                                        outcome: .understood)])
        let y = NativePracticeJournal(epochID: epoch, startedAt: at,
            hasLegacyHistory: false, events: [makeEvent(id: uuid, itemID: source.id, at: at,
                                                        outcome: .needsPractice)])
        XCTAssertThrowsError(try NativePracticeJournal.mergeCandidate(
            x, y, lessons: catalog()))
    }

    func testUnknownSourceItemAndForbiddenModeFailValidation() throws {
        let source = try item()
        let at = Date(timeIntervalSince1970: 1_760_000_000)
        let invalid = NativePracticeJournal(startedAt: at, hasLegacyHistory: false,
            events: [makeEvent(itemID: "not-a-valid-v2-source:0", at: at)])
        XCTAssertThrowsError(try invalid.validateSource(lessons: catalog()))

        let spoken = NativePracticeJournal(startedAt: at, hasLegacyHistory: false,
            events: [makeEvent(itemID: source.id, at: at, mode: .speak,
                               outcome: .understood)])
        XCTAssertThrowsError(try spoken.validateSource(lessons: catalog()))
        let recordedLearn = NativePracticeJournal(startedAt: at, hasLegacyHistory: false,
            events: [makeEvent(itemID: source.id, at: at, mode: .learn,
                               outcome: .recorded)])
        XCTAssertThrowsError(try recordedLearn.validateSource(lessons: catalog()))
    }

    func testLocalResetRotatesEpochAndDropsOnlyOnDeviceJournal() throws {
        let (directory, path) = storage()
        defer { try? FileManager.default.removeItem(at: directory) }
        let store = LocalLearningStore(storageURL: path)
        let source = try item()
        store.recordAttempt(item: source, mode: .learn, understood: true)
        let prior = try XCTUnwrap(store.profile.practiceJournal)
        XCTAssertTrue(store.resetLocalProgress())
        XCTAssertNil(store.profile.practiceJournal)
        store.recordAttempt(item: source, mode: .learn, understood: true)
        let after = try XCTUnwrap(store.profile.practiceJournal)
        XCTAssertNotEqual(prior.epochID, after.epochID)
        XCTAssertNotEqual(prior.events.first?.actorID, after.events.first?.actorID)
        XCTAssertEqual(store.expedition.totalXP, 10)
    }

    func testStorageFailureCannotPublishAttemptEventReviewOrXP() throws {
        let (directory, _) = storage()
        defer { try? FileManager.default.removeItem(at: directory) }
        try FileManager.default.createDirectory(at: directory,
                                                withIntermediateDirectories: true)
        let parent = directory.appendingPathComponent("not-a-folder")
        try Data("preserve".utf8).write(to: parent)
        let learner = LocalLearningStore(storageURL: parent.appendingPathComponent("profile.json"))
        let source = try item()
        let initial = learner.profile.localID
        XCTAssertFalse(learner.recordAttempt(item: source, mode: .learn, understood: true))
        XCTAssertEqual(learner.profile.localID, initial)
        XCTAssertTrue(learner.profile.records.isEmpty)
        XCTAssertNil(learner.profile.practiceJournal)
        XCTAssertEqual(learner.expedition.totalXP, 0)
        XCTAssertNotNil(learner.saveError)
        XCTAssertEqual(try Data(contentsOf: parent), Data("preserve".utf8))
    }

    func testOldXPOnlyProfileDoesNotClaimCompleteEventHistory() throws {
        let (directory, path) = storage()
        defer { try? FileManager.default.removeItem(at: directory) }
        try FileManager.default.createDirectory(at: directory,
                                                withIntermediateDirectories: true)
        let source = try item()
        var profile = LocalLearner()
        var map = LocalExpedition()
        _ = map.award(itemID: source.id, mode: .learn, tier: 1)
        profile.expedition = map
        let encoder = JSONEncoder()
        encoder.dateEncodingStrategy = .iso8601
        try encoder.encode(profile).write(to: path)
        let learner = LocalLearningStore(storageURL: path)
        XCTAssertTrue(learner.profile.records.isEmpty)
        XCTAssertEqual(learner.expedition.totalXP, 10)
        XCTAssertTrue(learner.recordAttempt(item: source, mode: .speak, understood: nil))
        XCTAssertTrue(learner.profile.practiceJournal?.hasLegacyHistory == true)
        XCTAssertEqual(learner.profile.practiceJournal?.events.count, 1)
    }

    func testRecordedRegionSnapshotIsAtomicAndSurvivesRegionSwitchRestartAndExport() throws {
        let (folder, path) = storage()
        defer { try? FileManager.default.removeItem(at: folder) }
        let learner = LocalLearningStore(storageURL: path)
        let item = try item()
        let otherRegion = try XCTUnwrap(learner.regions.first { $0.id != "mazowieckie" })
        learner.chooseRegion(otherRegion.id)
        XCTAssertTrue(learner.recordAttempt(item: item, mode: .learn, understood: true))
        let event = try XCTUnwrap(learner.profile.practiceJournal?.events.first)
        XCTAssertEqual(event.regionID, otherRegion.id)
        XCTAssertEqual(learner.expedition.events.first?.regionID, otherRegion.id)

        learner.chooseRegion("mazowieckie")
        XCTAssertEqual(learner.profile.practiceJournal?.events.first?.regionID, otherRegion.id,
                       "A later map selection must not rewrite past source metadata")
        let reopened = LocalLearningStore(storageURL: path)
        XCTAssertNil(reopened.catalogError)
        XCTAssertEqual(reopened.profile.practiceJournal?.events.first?.regionID, otherRegion.id)
        let json = try reopened.makeLocalExport().archive.encoded()
        let restored = try LocalProgressArchive.decode(json)
        XCTAssertEqual(restored.profile.practiceJournal?.events.first?.regionID, otherRegion.id)
        XCTAssertNoThrow(try reopened.profile.practiceJournal?.validateSource(
            lessons: reopened.lessons, regions: reopened.regions))
    }

    func testUnknownRegionInJournalCannotBeUsedByArchivedOrLoadedProgress() throws {
        let (folder, path) = storage()
        defer { try? FileManager.default.removeItem(at: folder) }
        let original = LocalLearningStore(storageURL: path)
        let item = try item()
        XCTAssertTrue(original.recordAttempt(item: item, mode: .learn, understood: true))
        var altered = original.profile
        var journal = try XCTUnwrap(altered.practiceJournal)
        let old = try XCTUnwrap(journal.events.first)
        journal.events[0] = NativePracticeEvent(
            id: old.id, actorID: old.actorID, itemID: old.itemID,
            mode: old.mode, at: old.at, outcome: old.outcome,
            regionID: "invented-region")
        altered.practiceJournal = journal
        XCTAssertThrowsError(try journal.validateSource(
            lessons: original.lessons, regions: original.regions))
        let before = try Data(contentsOf: path)
        let invalidArchive = LocalProgressArchive(
            profile: altered, sourceLessonIDs: original.lessons.map(\.id))
        let restored = LocalProgressArchive(profile: original.profile,
                                           sourceLessonIDs: original.lessons.map(\.id))
        XCTAssertNoThrow(try restored.encoded())
        XCTAssertThrowsError(try LocalRestoreValidation.validate(
            invalidArchive, lessons: original.lessons, regions: original.regions,
            guided: original.guidedFoundations, touristUnits: original.touristUnits,
            core: original.coreJourney))
        XCTAssertEqual(try Data(contentsOf: path), before)
    }

    func testSameSecondRatingsFollowRecordedActorSequenceNotRandomUUID() throws {
        let original = try item()
        let actor = UUID(uuidString: "aaaaaaaa-0000-0000-0000-000000000001")!
        let second = Date(timeIntervalSince1970: 1_760_000_001)
        // The first action's UUID sorts LAST to prove we never reorder
        // two fast ratings of the same flashcard by random UUID.
        let first = NativePracticeEvent(
            id: UUID(uuidString: "ffffffff-0000-0000-0000-000000000001")!,
            actorID: actor, itemID: original.id, mode: .learn,
            at: second, outcome: .needsPractice,
            regionID: "mazowieckie", actorSequence: 1)
        let last = NativePracticeEvent(
            id: UUID(uuidString: "00000000-0000-0000-0000-000000000001")!,
            actorID: actor, itemID: original.id, mode: .learn,
            at: second, outcome: .understood,
            regionID: "mazowieckie", actorSequence: 2)
        let journal = NativePracticeJournal(
            startedAt: second, hasLegacyHistory: false, events: [last, first])
        try journal.validateSource(lessons: catalog())
        let projected = try journal.projectedRecords(lessons: catalog())
        XCTAssertEqual(projected["learn:" + original.id]?.attempts, 2)
        XCTAssertEqual(projected["learn:" + original.id]?.completed, 1)
        XCTAssertEqual(projected["learn:" + original.id]?.reviewLevel, 1)
        XCTAssertEqual(projected["learn:" + original.id]?.nextReview,
                       second.addingTimeInterval(86_400))
        let awards = try NativeXPReconciliation.candidate(
            journal: journal, lessons: catalog())
        XCTAssertEqual(awards.awards.count, 1)
        XCTAssertEqual(awards.awards.first?.eventID, first.id,
                       "First recorded answer owns the single daily XP award")
    }

    func testDuplicateOrForgedActorSequenceFailsSourceValidation() throws {
        let original = try item()
        let actor = UUID()
        let moment = Date(timeIntervalSince1970: 1_760_000_000)
        func entry(_ id: UUID, _ position: Int) -> NativePracticeEvent {
            NativePracticeEvent(id: id, actorID: actor,
                                itemID: original.id, mode: .learn,
                                at: moment, outcome: .understood,
                                regionID: "mazowieckie", actorSequence: position)
        }
        let duplicate = NativePracticeJournal(startedAt: moment,
            hasLegacyHistory: false, events: [entry(UUID(), 1), entry(UUID(), 1)])
        XCTAssertThrowsError(try duplicate.validateSource(lessons: catalog()))
        let zero = NativePracticeJournal(startedAt: moment,
            hasLegacyHistory: false, events: [entry(UUID(), 0)])
        XCTAssertThrowsError(try zero.validateSource(lessons: catalog()))
    }

    func testPreviousExportWithoutActorSequenceIsReadable() throws {
        let original = try item()
        let time = Date(timeIntervalSince1970: 1_760_000_000)
        let historical = NativePracticeEvent(id: UUID(), actorID: UUID(),
            itemID: original.id, mode: .learn, at: time,
            outcome: .understood, regionID: "mazowieckie")
        let data = try JSONEncoder().encode(historical)
        var json = try XCTUnwrap(JSONSerialization.jsonObject(with: data) as? [String:Any])
        json.removeValue(forKey: "actorSequence")
        let decoded = try JSONDecoder().decode(NativePracticeEvent.self,
            from: JSONSerialization.data(withJSONObject: json))
        XCTAssertNil(decoded.actorSequence)
        let journal = NativePracticeJournal(startedAt: time,
            hasLegacyHistory: false, events: [decoded])
        XCTAssertNoThrow(try journal.validateSource(lessons: catalog()))
    }

    func testRealLocalAttemptsPersistIncreasingPerActorSequence() throws {
        let (dir, url) = storage()
        defer { try? FileManager.default.removeItem(at: dir) }
        let learner = LocalLearningStore(storageURL: url)
        let source = try item()
        XCTAssertTrue(learner.recordAttempt(item: source, mode: .learn, understood: false))
        XCTAssertTrue(learner.recordAttempt(item: source, mode: .learn, understood: true))
        XCTAssertEqual(learner.profile.practiceJournal?.events.map(\.actorSequence), [1, 2])
        let reloaded = LocalLearningStore(storageURL: url)
        XCTAssertNil(reloaded.catalogError)
        XCTAssertEqual(reloaded.profile.practiceJournal?.events.map(\.actorSequence), [1, 2])
        XCTAssertEqual(reloaded.record(for: source, mode: .learn).reviewLevel, 1)
        XCTAssertNoThrow(try reloaded.profile.practiceJournal?.projectedRecords(
            lessons: reloaded.lessons))
    }
}
