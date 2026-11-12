import XCTest
@testable import PathToPolish

@MainActor final class GuidedExercisePlanTests: XCTestCase {
    private func store() -> (LocalLearningStore, URL) {
        let directory = FileManager.default.temporaryDirectory
            .appendingPathComponent(UUID().uuidString)
        return (LocalLearningStore(storageURL: directory.appendingPathComponent("learner.json")),
                directory)
    }

    func testEveryOriginalGuidedReferenceSupportsSpeakAndLearn() throws {
        let (learner, directory) = store()
        defer { try? FileManager.default.removeItem(at: directory) }
        XCTAssertEqual(learner.guidedFoundations.count, 16)
        var referenced = Set<String>()
        for step in learner.guidedFoundations {
            for entry in step.items {
                let source = try XCTUnwrap(learner.sourceItem(for: entry))
                let owner = try XCTUnwrap(learner.lessons.first {
                    $0.items.contains(where: { $0.id == source.id })
                })
                XCTAssertTrue(owner.availableModes.contains(.speak),
                              "Speak mode not available for \(source.id)")
                XCTAssertTrue(owner.availableModes.contains(.learn),
                              "Learn mode not available for \(source.id)")
                XCTAssertEqual(source.audio, entry.audio)
                referenced.insert(source.id)
            }
        }
        XCTAssertEqual(referenced.count, 55,
                       "All guided activities preserve original 55 unique source MP3 IDs")
    }

    func testTwoWordFirstStepDoesNotInventThirdDistractor() throws {
        let (learner, directory) = store()
        defer { try? FileManager.default.removeItem(at: directory) }
        let first = learner.guidedFoundations[0]
        XCTAssertEqual(first.items.map(\.polish), ["Tak", "Nie"])
        XCTAssertFalse(GuidedExercisePlan.hasRecap(first))
        XCTAssertTrue(GuidedExercisePlan.choices(for: first, index: 0).isEmpty)
        XCTAssertEqual(GuidedExercisePlan.nextPhase(step: first, records: [:])?.0,
                       .introduce)
        XCTAssertEqual(GuidedExercisePlan.nextPhase(step: first, records: [:])?.1, 0)
        XCTAssertFalse(GuidedExercisePlan.isComplete(step: first, records: [:]))
        for entry in first.items {
            let original = try XCTUnwrap(learner.sourceItem(for: entry))
            XCTAssertTrue(learner.recordAttempt(
                item: original, mode: .speak, understood: nil))
        }
        XCTAssertTrue(GuidedExercisePlan.isComplete(
            step: first, records: learner.profile.records))
        XCTAssertEqual(learner.guidedPractisedCount(first), 2)
    }

    func testThreeWordGroupRecapUsesOnlyExactEnglishMeanings() throws {
        let (learner, directory) = store()
        defer { try? FileManager.default.removeItem(at: directory) }
        let step = learner.guidedFoundations[1]
        XCTAssertEqual(step.items.count, 3)
        XCTAssertTrue(GuidedExercisePlan.hasRecap(step))
        for (index, item) in step.items.enumerated() {
            let choices = GuidedExercisePlan.choices(for: step, index: index)
            XCTAssertEqual(choices.count, 3)
            XCTAssertEqual(Set(choices).count, 3)
            XCTAssertEqual(choices.filter { $0 == item.english }.count, 1)
            for choice in choices {
                XCTAssertTrue(step.items.contains { $0.english == choice },
                              "Distractor must come from the recorded group")
            }
        }
        for entry in step.items {
            let original = try XCTUnwrap(learner.sourceItem(for: entry))
            XCTAssertTrue(learner.recordAttempt(
                item: original, mode: .speak, understood: nil))
        }
        let pending = GuidedExercisePlan.nextPhase(
            step: step, records: learner.profile.records)
        XCTAssertEqual(pending?.0, .recap)
        XCTAssertEqual(pending?.1, 0)
        XCTAssertFalse(GuidedExercisePlan.isComplete(
            step: step, records: learner.profile.records))
        for entry in step.items {
            let original = try XCTUnwrap(learner.sourceItem(for: entry))
            XCTAssertTrue(learner.recordAttempt(
                item: original, mode: .learn,
                understood: false, evidence: .matching))
        }
        XCTAssertTrue(GuidedExercisePlan.isComplete(
            step: step, records: learner.profile.records))
        XCTAssertEqual(learner.guidedPractisedCount(step), 3)
        let record = try XCTUnwrap(learner.profile.records["learn:" + step.items[0].id])
        XCTAssertEqual(record.objectiveAttempts, 1)
        XCTAssertEqual(record.objectiveCorrect, 0)
    }

    func testEarlierSelfRatingsRemainCompleteWithoutInventedQuizEvidence() throws {
        let (learner, directory) = store()
        defer { try? FileManager.default.removeItem(at: directory) }
        let step = learner.guidedFoundations[1]
        for entry in step.items {
            let original = try XCTUnwrap(learner.sourceItem(for: entry))
            XCTAssertTrue(learner.recordAttempt(
                item: original, mode: .learn, understood: true))
        }
        XCTAssertTrue(GuidedExercisePlan.isComplete(
            step: step, records: learner.profile.records))
        XCTAssertEqual(learner.guidedPractisedCount(step), 3)
        for entry in step.items {
            XCTAssertNil(learner.profile.records["learn:" + entry.id]?.objectiveAttempts)
        }
    }

    func testGuidedResumePersistsRecapWithoutChangingLearningScores() throws {
        let (learner, directory) = store()
        defer { try? FileManager.default.removeItem(at: directory) }
        let step = learner.guidedFoundations[2]
        let item = try XCTUnwrap(step.items.last)
        learner.rememberGuidedPosition(stepID: step.id, itemID: item.id,
                                        phase: .recap)
        let reopened = LocalLearningStore(
            storageURL: directory.appendingPathComponent("learner.json"))
        XCTAssertEqual(reopened.guidedResumePhase(for: step.id), .recap)
        XCTAssertEqual(reopened.guidedResumeItemID(for: step.id), item.id)
        XCTAssertEqual(reopened.attempts, 0)
        XCTAssertEqual(reopened.expedition.totalXP, 0)
    }
}
