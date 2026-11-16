import XCTest
@testable import PathToPolish

@MainActor final class NativeDailyReviewQueueTests: XCTestCase {
    private let now = Date(timeIntervalSince1970: 1_760_000_000)

    private func source() throws -> [Lesson] {
        try CatalogLoader.load()
    }

    private func eligible() throws -> [(Lesson, LessonItem)] {
        let lessons = try source()
        return lessons.filter {
            $0.kind != "reading" && $0.availableModes.contains(.learn)
        }.flatMap { lesson in lesson.items.map { (lesson, $0) } }
    }

    private func due(_ at: Date) -> PracticeRecord {
        PracticeRecord(attempts: 1, completed: 1,
                       reviewLevel: 1, lastAttempt: at.addingTimeInterval(-86_400),
                       nextReview: at)
    }

    func testOldestDueFirstAcrossOriginalLessonsAndFutureExcluded() throws {
        let lessons = try source()
        let eligibleItems = try eligible()
        let first = try XCTUnwrap(eligibleItems.first)
        let second = try XCTUnwrap(eligibleItems.first(where: {
            $0.0.id != first.0.id
        }))
        let third = try XCTUnwrap(eligibleItems.first(where: {
            $0.1.id != first.1.id && $0.1.id != second.1.id
        }))
        var records: [String: PracticeRecord] = [
            "learn:" + first.1.id: due(now.addingTimeInterval(-3_600)),
            "learn:" + second.1.id: due(now.addingTimeInterval(-7_200)),
            "learn:" + third.1.id: due(now.addingTimeInterval(3_600))
        ]
        let frozen = NativeDailyReviewQueue.snapshot(
            lessons: lessons, records: records, now: now)
        XCTAssertEqual(frozen.map(\.id), [second.1.id, first.1.id])
        XCTAssertEqual(frozen[0].lesson.id, second.0.id)
        // Snapshot remains frozen even after the first answer is graded.
        records["learn:" + second.1.id] = due(now.addingTimeInterval(86_400))
        XCTAssertEqual(frozen.map(\.id), [second.1.id, first.1.id])
        XCTAssertEqual(NativeDailyReviewQueue.snapshot(
            lessons: lessons, records: records, now: now).map(\.id),
                       [first.1.id])
    }

    func testTwentyCardBatchIsBoundedAndStableForEqualDueTimes() throws {
        let lessons = try source()
        let items = try eligible()
        XCTAssertGreaterThan(items.count, NativeDailyReviewQueue.batchLimit)
        var records: [String: PracticeRecord] = [:]
        for (_, item) in items {
            records["learn:" + item.id] = due(now.addingTimeInterval(-1))
        }
        let first = NativeDailyReviewQueue.snapshot(
            lessons: lessons, records: records, now: now)
        let second = NativeDailyReviewQueue.snapshot(
            lessons: lessons, records: records, now: now)
        XCTAssertEqual(first.count, 20)
        XCTAssertEqual(first.map(\.id), second.map(\.id))
        XCTAssertEqual(Set(first.map(\.id)).count, 20)
        XCTAssertEqual(first.map(\.id), Array(items.prefix(20).map { $0.1.id }))
        XCTAssertEqual(NativeDailyReviewQueue.snapshot(
            lessons: lessons, records: records, now: now, limit: 3).count, 3)
    }

    func testNoUnseenFutureReadingOnlyOrUnreviewedAttemptsLeak() throws {
        let lessons = try source()
        let learn = try XCTUnwrap(try eligible().first)
        let reading = try XCTUnwrap(lessons.first(where: {
            $0.kind == "reading"
        })?.items.first)
        let records: [String: PracticeRecord] = [
            "learn:" + learn.1.id: PracticeRecord(attempts: 0,
                completed: 0, nextReview: now.addingTimeInterval(-10)),
            "learn:" + reading.id: due(now.addingTimeInterval(-10))
        ]
        XCTAssertTrue(NativeDailyReviewQueue.snapshot(
            lessons: lessons, records: records, now: now).isEmpty)
        XCTAssertTrue(NativeDailyReviewQueue.snapshot(
            lessons: lessons,
            records: ["learn:" + learn.1.id: due(now.addingTimeInterval(10))],
            now: now).isEmpty)
        XCTAssertTrue(NativeDailyReviewQueue.snapshot(
            lessons: lessons,
            records: ["learn:" + learn.1.id: due(now.addingTimeInterval(-10))],
            now: now, limit: 0).isEmpty)
    }

    func testRealMissKeepsCardDueWhileSuccessSchedulesFutureReview() throws {
        let base = FileManager.default.temporaryDirectory
            .appendingPathComponent(UUID().uuidString)
        defer { try? FileManager.default.removeItem(at: base) }
        let store = LocalLearningStore(storageURL: base.appendingPathComponent("learner.json"))
        let item = try XCTUnwrap(store.lessons.first(where: {
            $0.availableModes.contains(.learn)
        })?.items.first)
        XCTAssertTrue(store.recordAttempt(item: item, mode: .learn, understood: false))
        let before = NativeDailyReviewQueue.snapshot(
            lessons: store.lessons, records: store.profile.records, now: Date())
        XCTAssertTrue(before.map(\.id).contains(item.id))
        XCTAssertTrue(store.recordAttempt(item: item, mode: .learn, understood: true))
        let after = NativeDailyReviewQueue.snapshot(
            lessons: store.lessons, records: store.profile.records, now: Date())
        XCTAssertFalse(after.map(\.id).contains(item.id))
        // A previously opened session still holds its original cards.
        XCTAssertTrue(before.map(\.id).contains(item.id))
    }
}
