import XCTest
@testable import PathToPolish

@MainActor final class NativeExercisePlanTests: XCTestCase {
    private func testStore() -> (LocalLearningStore, URL) {
        let folder = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        return (LocalLearningStore(storageURL: folder.appendingPathComponent("learner.json")), folder)
    }

    func testFirstSourcePhraseUsesSpeakWithAlternatingMatching() throws {
        let (learner, folder) = testStore()
        defer { try? FileManager.default.removeItem(at: folder) }
        let lesson = try XCTUnwrap(learner.lessons.first(where: { $0.id == "Conversation_1" }))
        XCTAssertEqual(lesson.items[0].polish, "Dzień dobry")
        XCTAssertEqual(NativeExercisePlan.mode(for: lesson, sourceIndex: 0), .speak)
        XCTAssertEqual(NativeExercisePlan.mode(for: lesson, sourceIndex: 1), .speak)
        XCTAssertEqual(NativeExercisePlan.mode(for: lesson, sourceIndex: 2), .speak)
        XCTAssertEqual(NativeExercisePlan.mode(for: lesson, sourceIndex: 4), .learn)
        XCTAssertTrue(NativeExercisePlan.choices(for: lesson, itemIndex: 1).isEmpty)
        let item = lesson.items[4]
        let choices = NativeExercisePlan.choices(for: lesson, itemIndex: 4)
        XCTAssertEqual(choices.count, 3)
        XCTAssertEqual(choices.filter { $0 == item.english }.count, 1)
        for choice in choices where choice != item.english {
            XCTAssertTrue(lesson.items.prefix(4).contains { $0.english == choice },
                          "Quiz choices must never leak a later card")
        }
    }

    func testPlanDoesNotMakeAudioPlayOrFlashRevealAGradedAttempt() throws {
        let (learner, folder) = testStore()
        defer { try? FileManager.default.removeItem(at: folder) }
        let lesson = try XCTUnwrap(learner.lessons.first(where: { $0.id == "Conversation_1" }))
        XCTAssertEqual(learner.attempts, 0)
        XCTAssertEqual(learner.expedition.totalXP, 0)
        XCTAssertEqual(NativeExercisePlan.nextUnattemptedIndex(
            items: lesson.items, lesson: lesson, records: learner.profile.records), 0)
        for index in 0..<4 {
            XCTAssertEqual(NativeExercisePlan.mode(for: lesson, sourceIndex: index), .speak)
            XCTAssertTrue(learner.recordAttempt(item: lesson.items[index],
                                                mode: .speak, understood: nil))
        }
        XCTAssertTrue(learner.recordAttempt(item: lesson.items[4],
                                          mode: .learn, understood: true, evidence: .matching))
        XCTAssertEqual(NativeExercisePlan.nextUnattemptedIndex(
            items: lesson.items, lesson: lesson, records: learner.profile.records), 5)
        XCTAssertEqual(learner.record(for: lesson.items[4], mode: .learn).objectiveAttempts, 1)
        XCTAssertEqual(learner.record(for: lesson.items[4], mode: .learn).objectiveCorrect, 1)
        XCTAssertNil(learner.record(for: lesson.items[0], mode: .speak).objectiveAttempts)
    }

    func testLegacySelfRatingDoesNotMasqueradeAsObjectiveMatching() throws {
        let (learner, folder) = testStore()
        defer { try? FileManager.default.removeItem(at: folder) }
        let lesson = try XCTUnwrap(learner.lessons.first(where: { $0.id == "Conversation_1" }))
        let source = lesson.items[1]
        XCTAssertTrue(learner.recordAttempt(item: source, mode: .learn, understood: true))
        let record = learner.record(for: source, mode: .learn)
        XCTAssertEqual(record.attempts, 1)
        XCTAssertEqual(record.completed, 1)
        XCTAssertNil(record.objectiveAttempts)
        let collection = NativeJourneyCollection(
            id: "check", title: "Check", subtitle: "", lessons: [lesson])
        let old = NativeJourneyCatalog.snapshot(collection, records: learner.profile.records)
        XCTAssertEqual(old.recallPercentage, 100)
        XCTAssertNil(old.objectivePercentage)
        XCTAssertTrue(learner.recordAttempt(item: source, mode: .learn,
                                          understood: false, evidence: .matching))
        let fresh = NativeJourneyCatalog.snapshot(collection, records: learner.profile.records)
        XCTAssertEqual(fresh.objectiveAttempts, 1)
        XCTAssertEqual(fresh.objectiveCorrect, 0)
        XCTAssertEqual(fresh.objectivePercentage, 0)
        XCTAssertEqual(fresh.recallPercentage, 50)
    }

    func testSourceAuthoredDialoguesPlayOriginalRecordedTurns() throws {
        let lessons = try CatalogLoader.load()
        let greeting = try XCTUnwrap(lessons.first(where: { $0.id == "Basic_01R" }))
        let grocery = try XCTUnwrap(lessons.first(where: {
            $0.id == "Grocery_store_very_basic_shopping"
        }))
        XCTAssertEqual(greeting.microDialogues?.count, 2)
        XCTAssertEqual(grocery.microDialogues?.count, 1)
        var seen = Set<String>()
        for lesson in [greeting, grocery] {
            for scene in try XCTUnwrap(lesson.microDialogues) {
                XCTAssertGreaterThanOrEqual(scene.turns.count, 2)
                XCTAssertEqual(scene.comprehension.options.count, 3)
                for turn in scene.turns {
                    let original = try XCTUnwrap(lesson.items.first(where: { $0.id == turn.itemId }))
                    XCTAssertNotNil(original.audio)
                    XCTAssertTrue(seen.insert(turn.itemId).inserted)
                }
            }
        }
    }

    func testObjectiveMatchingAndDialogueEvidenceProjectsAcrossJournal() throws {
        let (learner, folder) = testStore()
        defer { try? FileManager.default.removeItem(at: folder) }
        let words = try XCTUnwrap(learner.lessons.first(where: { $0.id == "Conversation_1" }))
        let reading = try XCTUnwrap(learner.lessons.first(where: { $0.id == "Basic_01R" }))
        let last = try XCTUnwrap(reading.microDialogues?.first?.turns.last)
        let dialogueItem = try XCTUnwrap(reading.items.first(where: { $0.id == last.itemId }))
        XCTAssertTrue(learner.recordAttempt(item: words.items[1], mode: .learn,
                                          understood: true, evidence: .matching))
        XCTAssertTrue(learner.recordAttempt(item: dialogueItem, mode: .listen,
                                          understood: false, evidence: .dialogue))
        let journal = try XCTUnwrap(learner.profile.practiceJournal)
        XCTAssertEqual(journal.events.map(\.evidence), [.matching, .dialogue])
        let projection = try journal.projectedRecords(lessons: learner.lessons)
        let matched = try XCTUnwrap(projection["learn:" + words.items[1].id])
        XCTAssertEqual(matched.objectiveAttempts, 1)
        XCTAssertEqual(matched.objectiveCorrect, 1)
        let heard = try XCTUnwrap(projection["listen:" + dialogueItem.id])
        XCTAssertEqual(heard.objectiveAttempts, 1)
        XCTAssertEqual(heard.objectiveCorrect ?? 0, 0)
        let reopened = LocalLearningStore(storageURL: folder.appendingPathComponent("learner.json"))
        XCTAssertEqual(reopened.record(for: dialogueItem, mode: .listen).objectiveAttempts, 1)
        XCTAssertEqual(reopened.record(for: words.items[1], mode: .learn).objectiveCorrect, 1)
    }
}
