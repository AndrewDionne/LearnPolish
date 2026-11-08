import XCTest
@testable import PathToPolish

@MainActor final class GuidedFoundationTests: XCTestCase {
    private func makeStore() -> (LocalLearningStore, URL) {
        let directory = FileManager.default.temporaryDirectory
            .appendingPathComponent(UUID().uuidString)
        return (LocalLearningStore(storageURL: directory.appendingPathComponent("learner.json")),
                directory)
    }

    func testSixteenNativeStepsAndSixtyEightOriginalRecordedReferences() throws {
        let lessons = try CatalogLoader.load()
        let steps = try GuidedFoundationPath.load(lessons: lessons)
        XCTAssertEqual(steps.count, 16)
        XCTAssertEqual(steps.reduce(0) { $0 + $1.items.count }, 68)
        XCTAssertEqual(steps.map(\.order), Array(1...16))
        XCTAssertEqual(steps.filter(\.isGrammar).count, 7)
        XCTAssertEqual(steps.first?.id, "simple-replies")
        XCTAssertEqual(steps[6].id, "grammar:requests")
        XCTAssertEqual(steps.last?.id, "location-questions")
        XCTAssertEqual(steps[0].items[0].polish, "Tak")
        XCTAssertEqual(steps[0].items[0].id, "Conversation_1:14")
        XCTAssertEqual(steps[2].items[1].polish, "Cześć")
        XCTAssertEqual(Set(steps.flatMap { $0.items.map(\.id) }).count < 68, true,
                       "Original items may repeat between intro and practice without new IDs")
    }

    func testEveryGuidedExampleMatchesOriginalSourceAndReferenceAudio() throws {
        let lessons = try CatalogLoader.load()
        let steps = try GuidedFoundationPath.load(lessons: lessons)
        let original = Dictionary(uniqueKeysWithValues: lessons.flatMap(\.items).map { ($0.id, $0) })
        for step in steps {
            for reference in step.items {
                let item = try XCTUnwrap(original[reference.id])
                XCTAssertEqual(item.polish, reference.polish)
                XCTAssertEqual(item.english, reference.english)
                XCTAssertEqual(item.audio, reference.audio)
                XCTAssertNil(item.referenceReview)
                XCTAssertNotNil(AudioFiles.referenceURL(for: reference.audio))
                if step.isGrammar {
                    let focus = try XCTUnwrap(reference.focus)
                    XCTAssertEqual(reference.polish.components(separatedBy: focus).count, 2)
                }
            }
        }
    }

    func testPrerequisiteConceptsAreIntroducedBeforeUseAndNoOutsideStudy() throws {
        let steps = try GuidedFoundationPath.load(lessons: CatalogLoader.load())
        var available = Set<String>()
        for step in steps {
            XCTAssertTrue(step.requires.allSatisfy(available.contains),
                          "Forward prerequisite in \(step.id)")
            XCTAssertTrue(step.introduces.allSatisfy { !available.contains($0) })
            available.formUnion(step.introduces)
        }
        XCTAssertTrue(available.contains("can-i"))
        XCTAssertTrue(available.contains("location-phrases"))
    }

    func testGuidedCursorPersistsAcrossRestartWithoutMovingCourse() throws {
        let (learner, folder) = makeStore()
        defer { try? FileManager.default.removeItem(at: folder) }
        XCTAssertNil(learner.catalogError)
        let firstCourse = try XCTUnwrap(learner.nextLesson?.id)
        let step = try XCTUnwrap(learner.guidedFoundations.first)
        let second = try XCTUnwrap(step.items.last)
        learner.rememberGuidedPosition(stepID: step.id, itemID: second.id)
        XCTAssertEqual(learner.nextGuidedStep?.id, step.id)
        XCTAssertEqual(learner.nextLesson?.id, firstCourse)
        let reopened = LocalLearningStore(storageURL: folder.appendingPathComponent("learner.json"))
        XCTAssertEqual(reopened.profile.guidedStepID, step.id)
        XCTAssertEqual(reopened.profile.guidedItemID, second.id)
        XCTAssertEqual(reopened.nextLesson?.id, firstCourse)
        reopened.finishedGuidedStep(step.id)
        XCTAssertEqual(reopened.nextGuidedStep?.id, "politeness")
        let next = LocalLearningStore(storageURL: folder.appendingPathComponent("learner.json"))
        XCTAssertEqual(next.nextGuidedStep?.id, "politeness")
    }

    func testGuidedPracticeReusesLearnReviewAndDailyXPOnlyOnce() throws {
        let (learner, folder) = makeStore()
        defer { try? FileManager.default.removeItem(at: folder) }
        let step = try XCTUnwrap(learner.guidedFoundations.first)
        let reference = try XCTUnwrap(step.items.first)
        let original = try XCTUnwrap(learner.sourceItem(for: reference))
        XCTAssertEqual(learner.guidedPractisedCount(step), 0)
        XCTAssertEqual(learner.expedition.totalXP, 0)
        learner.rememberGuidedPosition(stepID: step.id, itemID: reference.id)
        XCTAssertEqual(learner.expedition.totalXP, 0,
                       "Navigation and playback are not evidence of practice")
        learner.recordAttempt(item: original, mode: .learn, understood: false)
        XCTAssertEqual(learner.guidedPractisedCount(step), 1)
        XCTAssertEqual(learner.expedition.totalXP, 10)
        XCTAssertNotNil(learner.record(for: original, mode: .learn).nextReview)
        learner.recordAttempt(item: original, mode: .learn, understood: true)
        XCTAssertEqual(learner.expedition.totalXP, 10,
                       "The guided step must not claim the same daily reward twice")
        let reopened = LocalLearningStore(storageURL: folder.appendingPathComponent("learner.json"))
        XCTAssertEqual(reopened.expedition.totalXP, 10)
        XCTAssertEqual(reopened.guidedPractisedCount(step), 1)
        XCTAssertEqual(reopened.record(for: original, mode: .learn).attempts, 2)
    }
}
