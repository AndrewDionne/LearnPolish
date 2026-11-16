import XCTest
@testable import PathToPolish

@MainActor final class NativeJourneyReinforcementTests: XCTestCase {
    private func fixture() throws -> (LocalLearningStore, NativeUnifiedJourney, CoreJourney, URL) {
        let directory = FileManager.default.temporaryDirectory
            .appendingPathComponent(UUID().uuidString)
        let learner = LocalLearningStore(
            storageURL: directory.appendingPathComponent("learner.json"))
        return (learner, try XCTUnwrap(learner.unifiedJourney),
                try XCTUnwrap(learner.coreJourney), directory)
    }

    private func completedFirstChapter(_ learner: LocalLearningStore) throws {
        for step in learner.guidedFoundations.prefix(3) {
            for guidedItem in step.items {
                let item = try XCTUnwrap(learner.sourceItem(for: guidedItem))
                XCTAssertTrue(learner.recordAttempt(
                    item: item, mode: .speak, understood: nil))
                if GuidedExercisePlan.hasRecap(step) {
                    XCTAssertTrue(learner.recordAttempt(
                        item: item, mode: .learn, understood: true,
                        evidence: .matching))
                }
            }
        }
    }

    private func snapshot(_ learner: LocalLearningStore,
                          _ journey: NativeUnifiedJourney,
                          _ core: CoreJourney) -> [NativeJourneyReinforcementCard] {
        NativeJourneyReinforcementQueue.snapshot(
            journey: journey, guided: learner.guidedFoundations,
            core: core, lessons: learner.lessons,
            records: learner.profile.records)
    }

    func testNotAvailableBeforeRealEarlierChapterPractice() throws {
        let (learner, journey, core, folder) = try fixture()
        defer { try? FileManager.default.removeItem(at: folder) }
        XCTAssertTrue(snapshot(learner, journey, core).isEmpty)
        let first = try XCTUnwrap(learner.guidedFoundations.first)
        learner.rememberGuidedPosition(stepID: first.id,
                                       itemID: try XCTUnwrap(first.items.last).id)
        XCTAssertTrue(snapshot(learner, journey, core).isEmpty)
        XCTAssertEqual(learner.attempts, 0)
        XCTAssertEqual(learner.expedition.totalXP, 0)
    }

    func testOnlyEarlierPractisedRecordedSourceItemsAndDistinctMeanings() throws {
        let (learner, journey, core, folder) = try fixture()
        defer { try? FileManager.default.removeItem(at: folder) }
        try completedFirstChapter(learner)
        let cards = snapshot(learner, journey, core)
        XCTAssertFalse(cards.isEmpty)
        XCTAssertLessThanOrEqual(cards.count, 6)
        XCTAssertEqual(Set(cards.map(\.id)).count, cards.count)
        let firstChapterSources = Set(journey.chapters[0].nodes.flatMap(\.sourceIDs))
        let allRecorded = Dictionary(uniqueKeysWithValues: learner.lessons.flatMap { lesson in
            lesson.items.map { ($0.id, (lesson, $0)) }
        })
        for card in cards {
            XCTAssertEqual(card.chapterID, journey.chapters[0].id)
            XCTAssertTrue(firstChapterSources.contains(card.item.id))
            let original = try XCTUnwrap(allRecorded[card.item.id])
            XCTAssertEqual(card.item.polish, original.1.polish)
            XCTAssertEqual(card.item.english, original.1.english)
            XCTAssertEqual(card.item.audio, original.1.audio)
            XCTAssertNotNil(card.item.audio)
            XCTAssertEqual(card.options.count, 3)
            XCTAssertEqual(Set(card.options).count, 3)
            XCTAssertEqual(card.options.filter { $0 == card.item.english }.count, 1)
            for option in card.options {
                XCTAssertTrue(learner.guidedFoundations.prefix(3).flatMap(\.items)
                    .contains { $0.english == option &&
                        (learner.profile.records["speak:" + $0.id]?.attempts ?? 0) > 0 })
            }
        }
    }

    func testReinforcementCommitsUnderOriginalIDAndEntersExistingReviewSchedule() throws {
        let (learner, journey, core, folder) = try fixture()
        defer { try? FileManager.default.removeItem(at: folder) }
        try completedFirstChapter(learner)
        let card = try XCTUnwrap(snapshot(learner, journey, core).first)
        let before = learner.record(for: card.item, mode: .learn)
        XCTAssertTrue(learner.recordAttempt(item: card.item, mode: .learn,
                                           understood: false, evidence: .matching))
        let after = learner.record(for: card.item, mode: .learn)
        XCTAssertEqual(after.attempts, before.attempts + 1)
        XCTAssertEqual(after.objectiveAttempts, (before.objectiveAttempts ?? 0) + 1)
        XCTAssertEqual(after.objectiveCorrect, before.objectiveCorrect ?? 0)
        XCTAssertNotNil(after.nextReview)
        XCTAssertLessThanOrEqual(try XCTUnwrap(after.nextReview), Date())
        let reopened = LocalLearningStore(
            storageURL: folder.appendingPathComponent("learner.json"))
        XCTAssertEqual(reopened.record(for: card.item, mode: .learn).objectiveAttempts,
                       after.objectiveAttempts)
        XCTAssertEqual(reopened.record(for: card.item, mode: .learn).nextReview,
                       after.nextReview)
        XCTAssertTrue(reopened.profile.practiceJournal?.events.contains(where: {
            $0.itemID == card.item.id &&
            $0.mode == .learn &&
            $0.evidence == .matching &&
            $0.outcome == .needsPractice
        }) == true)
    }

    func testReinforcementNeverIncludesUnintroducedFutureChapterItems() throws {
        let (learner, journey, core, folder) = try fixture()
        defer { try? FileManager.default.removeItem(at: folder) }
        try completedFirstChapter(learner)
        let later = Set(journey.chapters.dropFirst().flatMap { chapter in
            chapter.nodes.flatMap(\.sourceIDs)
        })
        let earlier = Set(journey.chapters[0].nodes.flatMap(\.sourceIDs))
        let laterOnly = later.subtracting(earlier)
        let cards = snapshot(learner, journey, core)
        XCTAssertFalse(cards.isEmpty)
        XCTAssertTrue(cards.allSatisfy { !laterOnly.contains($0.id) })
        XCTAssertEqual(snapshot(learner, journey, core).map(\.id),
                       snapshot(learner, journey, core).map(\.id),
                       "Queue order must be stable without navigation changes")
    }

    func testCorePracticeDoesNotRegressWhenItBecomesEligibleForMatching() throws {
        let (learner, journey, core, folder) = try fixture()
        defer { try? FileManager.default.removeItem(at: folder) }
        let lesson = try XCTUnwrap(learner.lessons.first { $0.id == "Conversation_1" })
        let node = try XCTUnwrap(journey.node(for: .lesson(lesson.id)))
        for i in [0, 1, 4] {
            XCTAssertTrue(learner.recordAttempt(item: lesson.items[i],
                                                mode: .speak, understood: nil))
        }
        let before = journey.progress(node, guided: learner.guidedFoundations,
                                      core: core, records: learner.profile.records)
        XCTAssertEqual(before.practised, 3)
        XCTAssertEqual(NativeExercisePlan.mode(
            for: lesson, sourceIndex: 4,
            records: learner.profile.records), .learn)
        XCTAssertTrue(learner.recordAttempt(item: lesson.items[4], mode: .learn,
                                           understood: false, evidence: .matching))
        let after = journey.progress(node, guided: learner.guidedFoundations,
                                     core: core, records: learner.profile.records)
        XCTAssertEqual(after.practised, before.practised,
                       "Same source word cannot be counted twice or lose prior credit")
    }

    func testNumbersSubsectionsUseActualSpeakProgress() throws {
        let (learner, _, _, folder) = try fixture()
        defer { try? FileManager.default.removeItem(at: folder) }
        let lesson = try XCTUnwrap(learner.lessons.first { $0.id == "numbers_1-20" })
        XCTAssertEqual(NativeExercisePlan.firstUnvisitedBatch(
            for: lesson, records: learner.profile.records), 0)
        for item in lesson.items.prefix(10) {
            XCTAssertTrue(learner.recordAttempt(item: item, mode: .speak,
                                               understood: nil))
        }
        XCTAssertEqual(NativeExercisePlan.firstUnvisitedBatch(
            for: lesson, records: learner.profile.records), 1,
                       "Numbers must remain 1–10 then 11–20, without redoing Speak")
        XCTAssertEqual(NativeExercisePlan.nextUnattemptedIndex(
            items: lesson.items, lesson: lesson,
            records: learner.profile.records), 10)
    }
}
