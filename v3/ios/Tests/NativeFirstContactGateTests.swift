import XCTest
@testable import PathToPolish

@MainActor final class NativeFirstContactGateTests: XCTestCase {
    private func setup() throws -> (LocalLearningStore, Lesson, URL) {
        let directory = FileManager.default.temporaryDirectory
            .appendingPathComponent(UUID().uuidString)
        let learner = LocalLearningStore(
            storageURL: directory.appendingPathComponent("learner.json"))
        let lesson = try XCTUnwrap(learner.lessons.first {
            $0.id == "Conversation_1"
        })
        return (learner, lesson, directory)
    }

    func testSourceCadenceNeverTestsAnUnintroducedTarget() throws {
        let (learner, lesson, directory) = try setup()
        defer { try? FileManager.default.removeItem(at: directory) }
        XCTAssertEqual(NativeExercisePlan.mode(for: lesson, sourceIndex: 4),
                       .learn, "The authored cadence includes a recap here")
        XCTAssertEqual(NativeExercisePlan.mode(for: lesson, sourceIndex: 4,
                                               records: learner.profile.records),
                       .speak, "Unseen original Polish must be introduced first")
        XCTAssertTrue(NativeExercisePlan.readyChoices(for: lesson, itemIndex: 4,
                                                      records: learner.profile.records).isEmpty)
        XCTAssertEqual(learner.attempts, 0)
        XCTAssertEqual(learner.expedition.totalXP, 0)
    }

    func testSkipCannotMakePreviouslyDisplayedMeaningAnEligibleDistractor() throws {
        let (learner, lesson, directory) = try setup()
        defer { try? FileManager.default.removeItem(at: directory) }
        let target = lesson.items[4]
        XCTAssertTrue(learner.recordAttempt(item: target, mode: .speak,
                                           understood: nil))
        XCTAssertEqual(NativeExercisePlan.mode(for: lesson, sourceIndex: 4,
                                               records: learner.profile.records),
                       .speak, "Only the target is introduced; other cards were skipped")
        XCTAssertTrue(NativeExercisePlan.readyChoices(for: lesson, itemIndex: 4,
                                                      records: learner.profile.records).isEmpty)
        XCTAssertEqual(learner.attempts, 1)
        XCTAssertEqual(learner.record(for: target, mode: .learn).attempts, 0)
    }

    func testRecordedOriginalMeaningsEnableImmediateSourceBackedMatching() throws {
        let (learner, lesson, directory) = try setup()
        defer { try? FileManager.default.removeItem(at: directory) }
        for i in [0, 1] {
            XCTAssertTrue(learner.recordAttempt(item: lesson.items[i],
                                               mode: .speak, understood: nil))
        }
        XCTAssertEqual(NativeExercisePlan.mode(for: lesson, sourceIndex: 4,
                                               records: learner.profile.records),
                       .speak, "The phrase itself has not yet been introduced")
        XCTAssertTrue(learner.recordAttempt(item: lesson.items[4],
                                           mode: .speak, understood: nil))
        let options = NativeExercisePlan.readyChoices(for: lesson, itemIndex: 4,
                                                       records: learner.profile.records)
        XCTAssertEqual(options.count, 3)
        XCTAssertEqual(Set(options).count, 3)
        XCTAssertEqual(options.filter { $0 == lesson.items[4].english }.count, 1)
        let earlier = Set([lesson.items[0].english, lesson.items[1].english])
        XCTAssertEqual(Set(options.filter { $0 != lesson.items[4].english }), earlier)
        XCTAssertEqual(NativeExercisePlan.mode(for: lesson, sourceIndex: 4,
                                               records: learner.profile.records), .learn)
        XCTAssertNil(learner.record(for: lesson.items[4],
                                    mode: .learn).objectiveAttempts)
        XCTAssertTrue(learner.recordAttempt(item: lesson.items[4], mode: .learn,
                                           understood: false, evidence: .matching))
        XCTAssertEqual(learner.record(for: lesson.items[4], mode: .learn).objectiveCorrect, 0)
        XCTAssertEqual(learner.record(for: lesson.items[4], mode: .learn).objectiveAttempts, 1)
    }

    func testStartedPhraseAndRecapResumesFromOriginalIdentityAfterRestart() throws {
        let (learner, lesson, directory) = try setup()
        defer { try? FileManager.default.removeItem(at: directory) }
        for i in [0, 1, 4] {
            XCTAssertTrue(learner.recordAttempt(item: lesson.items[i],
                                               mode: .speak, understood: nil))
        }
        learner.rememberPosition(lesson: lesson, item: lesson.items[4], mode: .learn)
        let reopened = LocalLearningStore(
            storageURL: directory.appendingPathComponent("learner.json"))
        let original = try XCTUnwrap(reopened.lessons.first { $0.id == lesson.id })
        XCTAssertEqual(reopened.practiceCursor(for: original.id)?.itemID,
                       original.items[4].id)
        XCTAssertEqual(NativeExercisePlan.mode(for: original, sourceIndex: 4,
                                               records: reopened.profile.records), .learn)
        XCTAssertEqual(NativeExercisePlan.readyChoices(
            for: original, itemIndex: 4, records: reopened.profile.records).count, 3)
        XCTAssertEqual(reopened.record(for: original.items[4],
                                       mode: .learn).attempts, 0)
        XCTAssertEqual(reopened.attempts, 3)
    }

    func testScheduledReviewNeverUsesUnpractisedLaterMeanings() throws {
        let (learner, lesson, directory) = try setup()
        defer { try? FileManager.default.removeItem(at: directory) }
        let target = lesson.items[4]
        XCTAssertTrue(learner.recordAttempt(item: target,
                                            mode: .learn, understood: false))
        XCTAssertTrue(NativeExercisePlan.reviewChoices(
            for: lesson, itemIndex: 4, records: learner.profile.records).isEmpty)
        XCTAssertTrue(learner.recordAttempt(item: lesson.items[0],
                                            mode: .speak, understood: nil))
        XCTAssertTrue(NativeExercisePlan.reviewChoices(
            for: lesson, itemIndex: 4, records: learner.profile.records).isEmpty)
        XCTAssertTrue(learner.recordAttempt(item: lesson.items[1],
                                            mode: .speak, understood: nil))
        let known = NativeExercisePlan.reviewChoices(
            for: lesson, itemIndex: 4, records: learner.profile.records)
        XCTAssertEqual(known.count, 3)
        XCTAssertEqual(Set(known), Set([
            target.english, lesson.items[0].english, lesson.items[1].english
        ]))
        XCTAssertFalse(known.contains(lesson.items[5].english))
        XCTAssertNil(learner.record(for: target, mode: .learn).objectiveAttempts)
    }

    func testLegacyLearnerSelfRatingsCountAsExposureButNeverAsObjectiveProof() throws {
        let (learner, lesson, directory) = try setup()
        defer { try? FileManager.default.removeItem(at: directory) }
        for i in [0, 1, 4] {
            XCTAssertTrue(learner.recordAttempt(item: lesson.items[i],
                                               mode: .learn, understood: true))
        }
        let record = learner.record(for: lesson.items[4], mode: .learn)
        XCTAssertNil(record.objectiveAttempts)
        XCTAssertEqual(NativeExercisePlan.mode(for: lesson, sourceIndex: 4,
                                               records: learner.profile.records), .learn)
        XCTAssertEqual(NativeExercisePlan.readyChoices(
            for: lesson, itemIndex: 4, records: learner.profile.records).count, 3)
        XCTAssertGreaterThan(learner.expedition.totalXP, 0)
    }
}
