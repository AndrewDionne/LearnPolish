import XCTest
@testable import PathToPolish

@MainActor final class NativeFoundationTests: XCTestCase {
    func testRealCurriculumAndBundledAudioResolveOffline() throws {
        let lessons = try CatalogLoader.load()
        XCTAssertEqual(lessons.count, 26)
        XCTAssertEqual(lessons.reduce(0) { $0 + $1.items.count }, 482)
        XCTAssertEqual(lessons.flatMap(\.items).filter { $0.audio != nil }.count, 481)
        XCTAssertEqual(lessons.filter { $0.curriculum?.stage == "fundamentals" }.count, 12)
        XCTAssertEqual(lessons.filter { $0.curriculum?.stage == "basic" }.count, 7)
        XCTAssertEqual(lessons.filter { $0.curriculum?.stage == "learning" }.count, 6)
        XCTAssertTrue(lessons.allSatisfy { !$0.availableModes.isEmpty })
    }

    func testAnonymousLocalProgressSurvivesRestartAndSeparatesModes() throws {
        let directory = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        let location = directory.appendingPathComponent("learner.json")
        defer { try? FileManager.default.removeItem(at: directory) }
        let first = LocalLearningStore(storageURL: location)
        XCTAssertNil(first.catalogError)
        XCTAssertNil(first.profile.lastLessonID)
        let lesson = try XCTUnwrap(first.lessons.first(where: { $0.availableModes.contains(.learn) }))
        let item = try XCTUnwrap(lesson.items.first)

        first.rememberPosition(lesson: lesson, item: item, mode: .learn)
        first.recordAttempt(item: item, mode: .learn, understood: true)
        first.recordAttempt(item: item, mode: .speak, understood: nil)
        XCTAssertNil(first.saveError)
        XCTAssertEqual(first.record(for: item, mode: .learn).completed, 1)
        XCTAssertEqual(first.record(for: item, mode: .speak).completed, 0)

        let reopened = LocalLearningStore(storageURL: location)
        XCTAssertEqual(reopened.profile.localID, first.profile.localID)
        XCTAssertEqual(reopened.profile.lastLessonID, lesson.id)
        XCTAssertEqual(reopened.profile.lastItemID, item.id)
        XCTAssertEqual(reopened.profile.lastMode, .learn)
        XCTAssertEqual(reopened.record(for: item, mode: .learn).attempts, 1)
        XCTAssertEqual(reopened.record(for: item, mode: .speak).attempts, 1)
        XCTAssertNotNil(reopened.record(for: item, mode: .learn).nextReview)
        XCTAssertNil(reopened.record(for: item, mode: .speak).nextReview)
    }

    func testIncorrectRecallRemainsDueWithoutFakeScore() throws {
        let directory = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        let location = directory.appendingPathComponent("learner.json")
        defer { try? FileManager.default.removeItem(at: directory) }
        let learner = LocalLearningStore(storageURL: location)
        let lesson = try XCTUnwrap(learner.lessons.first(where: { $0.availableModes.contains(.learn) }))
        let item = try XCTUnwrap(lesson.items.first)
        learner.recordAttempt(item: item, mode: .learn, understood: false)
        let record = learner.record(for: item, mode: .learn)
        XCTAssertEqual(record.reviewLevel, 0)
        XCTAssertEqual(record.completed, 0)
        XCTAssertNotNil(record.nextReview)
        XCTAssertTrue(learner.dueReviews.contains { $0.1.id == item.id })
    }

    func testNoUnsafeAudioOrInventedPhoneticSegmentation() throws {
        let lessons = try CatalogLoader.load()
        let items = lessons.flatMap(\.items)
        XCTAssertFalse(items.contains { $0.audio?.contains("https://") == true })
        XCTAssertEqual(items.filter { $0.referenceReview == "practice_only" }.count, 14)
        for item in items {
            if let segments = item.pronunciationSegments {
                XCTAssertEqual(segments.segments.joined(), item.polish)
            }
        }
    }
}
