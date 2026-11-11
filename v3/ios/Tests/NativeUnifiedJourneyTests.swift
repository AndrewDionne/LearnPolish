import XCTest
@testable import PathToPolish

@MainActor final class NativeUnifiedJourneyTests: XCTestCase {
    private func setup() -> (LocalLearningStore, URL) {
        let directory = FileManager.default.temporaryDirectory
            .appendingPathComponent(UUID().uuidString)
        let store = LocalLearningStore(
            storageURL: directory.appendingPathComponent("learner.json"))
        return (store, directory)
    }

    func testOnePathContainsExactlySourceApprovedSixteenGuidedAndNineteenCore() throws {
        let (learner, folder) = setup()
        defer { try? FileManager.default.removeItem(at: folder) }
        let path = try XCTUnwrap(learner.unifiedJourney)
        XCTAssertEqual(path.chapters.map { $0.nodes.count }, [3, 5, 5, 7, 4, 4, 4, 3])
        XCTAssertEqual(path.nodes.count, 35)
        let guided = path.nodes.compactMap { node -> String? in
            if case .guided(let id) = node.route { return id }
            return nil
        }
        let lessons = path.nodes.compactMap { node -> String? in
            if case .lesson(let id) = node.route { return id }
            return nil
        }
        XCTAssertEqual(guided, learner.guidedFoundations.map(\.id),
                       "The existing guided dependency order is unchanged")
        let expectedCore = Set(learner.course.filter {
            learner.coreJourney?.placements[$0.id]?.journey == 1
        }.map(\.id))
        XCTAssertEqual(Set(lessons), expectedCore)
        XCTAssertEqual(guided.count, 16)
        XCTAssertEqual(lessons.count, 19)
        XCTAssertEqual(Set(lessons).count, 19)
        XCTAssertFalse(lessons.contains("Grocery_store_very_basic_shopping"),
                       "Journey 2 remains separate")
        XCTAssertEqual(path.nodes.first?.route, .guided("simple-replies"))
        XCTAssertEqual(path.nodes.last?.route,
                       .lesson("Museum_buying_tickets_and_basic_info"))
    }

    func testOriginalSourceIDsAreReusedRatherThanCopiedIntoNewLessonIdentifiers() throws {
        let (learner, folder) = setup()
        defer { try? FileManager.default.removeItem(at: folder) }
        let path = try XCTUnwrap(learner.unifiedJourney)
        let authoritative = Set(learner.lessons.flatMap { $0.items.map(\.id) })
        for node in path.nodes {
            XCTAssertFalse(node.sourceIDs.isEmpty)
            XCTAssertTrue(Set(node.sourceIDs).isSubset(of: authoritative),
                          "Every path entry must be an original source item")
        }
        let repeated = path.nodes.first { $0.route == .lesson("Conversation_1") }
        XCTAssertGreaterThan(try XCTUnwrap(repeated).repeatedSourceCount, 0,
                             "First-words source recordings are reused, never cloned")
        XCTAssertEqual(learner.profile.records.count, 0)
    }

    func testNextActivityMovesAcrossGuidedAndCoreWithoutTwoParallelPaths() throws {
        let (learner, folder) = setup()
        defer { try? FileManager.default.removeItem(at: folder) }
        let path = try XCTUnwrap(learner.unifiedJourney)
        XCTAssertEqual(path.next(after: .guided("greetings"))?.route,
                       .lesson("contrast_l_lstroked"))
        XCTAssertEqual(path.next(after: .lesson("contrast_krzy_przy"))?.route,
                       .guided("street-words"))
        XCTAssertEqual(path.next(after: .lesson("Basic_01R"))?.route,
                       .guided("food-requests"))
        XCTAssertEqual(path.next(after: .guided("location-questions"))?.route,
                       .lesson("Numbers_20-100"))
        XCTAssertNil(path.next(after:
            .lesson("Museum_buying_tickets_and_basic_info")))
        XCTAssertNil(path.next(after: .lesson("Grocery_store_very_basic_shopping")))
    }

    func testSkipsAndBrowsingDoNotAdvanceSingleRecommendedContinue() throws {
        let (learner, folder) = setup()
        defer { try? FileManager.default.removeItem(at: folder) }
        let path = try XCTUnwrap(learner.unifiedJourney)
        let first = learner.guidedFoundations[0]
        learner.rememberGuidedPosition(stepID: first.id,
                                        itemID: first.items.last!.id)
        for group in learner.guidedFoundations {
            XCTAssertTrue(learner.finishedGuidedStep(group.id))
        }
        XCTAssertEqual(path.nextUnpractised(
            guided: learner.guidedFoundations, core: try XCTUnwrap(learner.coreJourney),
            records: learner.profile.records)?.route, .guided("simple-replies"))
        XCTAssertEqual(learner.unifiedJourneyStepsCompleted, 0)
        XCTAssertEqual(learner.expedition.totalXP, 0)
        XCTAssertEqual(learner.attempts, 0)
        let reopened = LocalLearningStore(
            storageURL: folder.appendingPathComponent("learner.json"))
        XCTAssertEqual(reopened.homeLearningRoute?.routeForTest,
                       .guided("simple-replies"))
        XCTAssertEqual(reopened.unifiedJourneyStepsCompleted, 0)
    }

    func testPriorSelfRatedFirstWordsCanLeadIntoOriginalSoundLessons() throws {
        let (learner, folder) = setup()
        defer { try? FileManager.default.removeItem(at: folder) }
        for step in learner.guidedFoundations.prefix(3) {
            for entry in step.items {
                let original = try XCTUnwrap(learner.sourceItem(for: entry))
                XCTAssertTrue(learner.recordAttempt(
                    item: original, mode: .learn, understood: false))
            }
        }
        XCTAssertEqual(learner.unifiedJourneyStepsCompleted, 1 + 1 + 1)
        XCTAssertEqual(learner.homeLearningRoute?.routeForTest,
                       .lesson("contrast_l_lstroked"))
        let next = try XCTUnwrap(learner.course.first {
            $0.id == "contrast_l_lstroked"
        })
        for entry in next.items {
            XCTAssertTrue(learner.recordAttempt(item: entry, mode: .speak,
                                                understood: nil))
        }
        XCTAssertEqual(learner.homeLearningRoute?.routeForTest,
                       .lesson("contrast_c_cz_cie"))
        XCTAssertEqual(learner.unifiedJourneyStepsCompleted, 4)
    }

    func testMatchingGradeIsAbsentUntilARealObjectiveResponse() throws {
        let (learner, folder) = setup()
        defer { try? FileManager.default.removeItem(at: folder) }
        let path = try XCTUnwrap(learner.unifiedJourney)
        let chapter = path.chapters[0]
        XCTAssertNil(path.matchingAccuracy(for: chapter, records: [:]))
        let first = learner.guidedFoundations[0].items[0]
        let original = try XCTUnwrap(learner.sourceItem(for: first))
        XCTAssertTrue(learner.recordAttempt(item: original, mode: .learn,
                                           understood: true))
        XCTAssertNil(path.matchingAccuracy(for: chapter,
                                            records: learner.profile.records),
                     "Old self-ratings are not objective quiz scores")
        XCTAssertTrue(learner.recordAttempt(item: original, mode: .learn,
                                           understood: false, evidence: .matching))
        XCTAssertEqual(path.matchingAccuracy(for: chapter,
                                              records: learner.profile.records), 0)
    }
}

private extension NativeHomeLearningRoute {
    var routeForTest: PracticeRoute {
        switch self {
        case .guided(let step): return .guided(step.id)
        case .core(let lesson): return .lesson(lesson.id)
        }
    }
}
