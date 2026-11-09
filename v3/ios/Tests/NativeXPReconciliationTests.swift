import Foundation
import XCTest
@testable import PathToPolish

@MainActor final class NativeXPReconciliationTests: XCTestCase {
    private let epoch = UUID(uuidString: "10000000-0000-0000-0000-000000000001")!
    private let actorA = UUID(uuidString: "20000000-0000-0000-0000-000000000002")!
    private let actorB = UUID(uuidString: "30000000-0000-0000-0000-000000000003")!
    private let firstID = UUID(uuidString: "00000000-0000-0000-0000-000000000010")!
    private let secondID = UUID(uuidString: "00000000-0000-0000-0000-000000000020")!

    private func date(_ text: String) -> Date {
        ISO8601DateFormatter().date(from: text)!
    }

    private func source() throws -> ([Lesson], LessonItem, Int) {
        let lessons = try CatalogLoader.load()
        let lesson = try XCTUnwrap(lessons.first { $0.availableModes.contains(.learn) })
        let item = try XCTUnwrap(lesson.items.first)
        let tier = lesson.difficultyTier.flatMap { (1...5).contains($0) ? $0 : nil } ?? 1
        return (lessons, item, [10, 14, 19, 26, 35][tier - 1])
    }

    private func event(_ item: LessonItem, id: UUID, actor: UUID,
                       at: Date, mode: PracticeMode = .learn,
                       outcome: NativePracticeEvent.Outcome = .understood)
        -> NativePracticeEvent {
        NativePracticeEvent(id: id, actorID: actor, itemID: item.id,
                            mode: mode, at: at, outcome: outcome)
    }

    private func journal(_ events: [NativePracticeEvent],
                         start: Date, epochID: UUID? = nil,
                         legacy: Bool = false) -> NativePracticeJournal {
        NativePracticeJournal(epochID: epochID ?? epoch,
                              startedAt: start,
                              hasLegacyHistory: legacy, events: events)
    }

    func testOneUTCRewardAcrossTwoDevicesOnSameDay() throws {
        let (lessons, item, baseXP) = try source()
        let start = date("2026-11-08T10:00:00Z")
        let earlier = event(item, id: firstID, actor: actorA,
                            at: date("2026-11-09T10:00:00Z"))
        let later = event(item, id: secondID, actor: actorB,
                          at: date("2026-11-09T17:00:00Z"))
        let projected = try NativeXPReconciliation.mergedCandidate(
            journal([earlier], start: start), journal([later], start: start),
            lessons: lessons)
        XCTAssertEqual(projected.awards.count, 1)
        XCTAssertEqual(projected.awards.first?.eventID, firstID)
        XCTAssertEqual(projected.awards.first?.utcDay, "2026-11-09")
        XCTAssertEqual(projected.totalEffortXP, baseXP)
        XCTAssertEqual(projected.totalExpeditionXP, baseXP)
        XCTAssertTrue(projected.requiresRegionReconciliation)
    }

    func testUTCPolicyDisagreesWithLocalMidnightButDoesNotDoubleAward() throws {
        let (lessons, item, baseXP) = try source()
        let start = date("2026-11-08T00:00:00Z")
        let left = date("2026-11-09T04:59:30Z")
        let right = date("2026-11-09T05:00:30Z")
        var toronto = Calendar(identifier: .gregorian)
        toronto.timeZone = TimeZone(identifier: "America/Toronto")!
        let localDayOne = toronto.dateComponents([.day], from: left).day
        let localDayTwo = toronto.dateComponents([.day], from: right).day
        XCTAssertNotEqual(localDayOne, localDayTwo,
                          "Events straddle Toronto local midnight")
        XCTAssertEqual(NativeXPReconciliation.utcDay(left), "2026-11-09")
        XCTAssertEqual(NativeXPReconciliation.utcDay(right), "2026-11-09")
        let candidate = try NativeXPReconciliation.mergedCandidate(
            journal([event(item, id: firstID, actor: actorA, at: left)], start: start),
            journal([event(item, id: secondID, actor: actorB, at: right)], start: start),
            lessons: lessons)
        XCTAssertEqual(candidate.awards.count, 1)
        XCTAssertEqual(candidate.totalEffortXP, baseXP)
    }

    func testUTCDateChangeAllowsSecondAwardAndHalvesRegionEffort() throws {
        let (lessons, item, baseXP) = try source()
        let start = date("2026-11-08T00:00:00Z")
        let first = event(item, id: firstID, actor: actorA,
                          at: date("2026-11-09T23:59:30Z"))
        let second = event(item, id: secondID, actor: actorB,
                           at: date("2026-11-10T00:00:30Z"))
        let candidate = try NativeXPReconciliation.mergedCandidate(
            journal([first], start: start), journal([second], start: start),
            lessons: lessons)
        XCTAssertEqual(candidate.awards.map(\.utcDay),
                       ["2026-11-09", "2026-11-10"])
        XCTAssertEqual(candidate.awards.map(\.effortXP), [baseXP, baseXP])
        let half = Int((Double(baseXP) / 2).rounded())
        XCTAssertEqual(candidate.awards.map(\.expeditionXP), [baseXP, half])
        XCTAssertEqual(candidate.totalEffortXP, 2 * baseXP)
        XCTAssertEqual(candidate.totalExpeditionXP, baseXP + half)
    }

    func testThirdRewardKeepsBaseEffortButZeroRegionalBonus() throws {
        let (lessons, item, baseXP) = try source()
        let start = date("2026-11-08T00:00:00Z")
        let first = event(item, id: firstID, actor: actorA,
                          at: date("2026-11-09T10:00:00Z"))
        let second = event(item, id: secondID, actor: actorB,
                           at: date("2026-11-10T10:00:00Z"))
        let third = event(item, id: UUID(), actor: actorA,
                          at: date("2026-11-11T10:00:00Z"))
        let candidate = try NativeXPReconciliation.candidate(
            journal([third, first, second], start: start), lessons: lessons)
        XCTAssertEqual(candidate.awards.count, 3)
        XCTAssertEqual(candidate.totalEffortXP, 3 * baseXP)
        XCTAssertEqual(candidate.awards.map(\.expeditionXP),
                       [baseXP, Int((Double(baseXP) / 2).rounded()), 0])
    }

    func testChronologicalOrderIsIndependentOfDeviceInputOrder() throws {
        let (lessons, item, _) = try source()
        let start = date("2026-11-08T00:00:00Z")
        let a = event(item, id: firstID, actor: actorA,
                      at: date("2026-11-09T10:00:00Z"))
        let b = event(item, id: secondID, actor: actorB,
                      at: date("2026-11-10T10:00:00Z"))
        let one = try NativeXPReconciliation.mergedCandidate(
            journal([b], start: start), journal([a], start: start),
            lessons: lessons)
        let two = try NativeXPReconciliation.mergedCandidate(
            journal([a], start: start), journal([b], start: start),
            lessons: lessons)
        XCTAssertEqual(one.awards, two.awards)
        XCTAssertEqual(one.totalEffortXP, two.totalEffortXP)
        XCTAssertEqual(one.totalExpeditionXP, two.totalExpeditionXP)
    }

    func testSameTimestampUsesUUIDToChooseAwardedEvent() throws {
        let (lessons, item, _) = try source()
        let start = date("2026-11-08T00:00:00Z")
        let moment = date("2026-11-09T10:00:00Z")
        let lower = event(item, id: firstID, actor: actorA, at: moment)
        let higher = event(item, id: secondID, actor: actorB, at: moment)
        let candidate = try NativeXPReconciliation.mergedCandidate(
            journal([higher], start: start), journal([lower], start: start),
            lessons: lessons)
        XCTAssertEqual(candidate.awards.count, 1)
        XCTAssertEqual(candidate.awards.first?.eventID, firstID)
    }

    func testIdenticalRetriesAreIdempotentByUUID() throws {
        let (lessons, item, baseXP) = try source()
        let start = date("2026-11-08T00:00:00Z")
        let attempted = event(item, id: firstID, actor: actorA,
                              at: date("2026-11-09T10:00:00Z"))
        let one = journal([attempted], start: start)
        let candidate = try NativeXPReconciliation.mergedCandidate(
            one, one, lessons: lessons)
        XCTAssertEqual(candidate.awards.count, 1)
        XCTAssertEqual(candidate.totalEffortXP, baseXP)
    }

    func testIndependentModesReceiveIndependentDailyEffortXP() throws {
        let (lessons, item, baseXP) = try source()
        let start = date("2026-11-08T00:00:00Z")
        let time = date("2026-11-09T10:00:00Z")
        let learning = event(item, id: firstID, actor: actorA, at: time)
        let speaking = event(item, id: secondID, actor: actorA, at: time,
                             mode: .speak, outcome: .recorded)
        let candidate = try NativeXPReconciliation.candidate(
            journal([speaking, learning], start: start), lessons: lessons)
        XCTAssertEqual(candidate.awards.count, 2)
        XCTAssertEqual(candidate.totalEffortXP, 2 * baseXP)
        XCTAssertEqual(candidate.totalExpeditionXP, 2 * baseXP)
    }

    func testLegacyAndUnlinkedHistoriesRefuseRewardsRatherThanGuess() throws {
        let (lessons, item, _) = try source()
        let start = date("2026-11-08T00:00:00Z")
        let one = journal([event(item, id: firstID, actor: actorA,
                                 at: date("2026-11-09T10:00:00Z"))],
                          start: start, legacy: true)
        XCTAssertThrowsError(try NativeXPReconciliation.candidate(
            journal: one, lessons: lessons))
        let other = journal([event(item, id: secondID, actor: actorB,
                                   at: date("2026-11-09T10:10:00Z"))],
                            start: start, epochID: UUID())
        XCTAssertThrowsError(try NativeXPReconciliation.mergedCandidate(
            one, other, lessons: lessons))
        let complete = journal(one.events, start: start)
        XCTAssertThrowsError(try NativeXPReconciliation.mergedCandidate(
            complete, other, lessons: lessons))
    }

    func testConflictingPayloadForSameEventUUIDIsNeverCredited() throws {
        let (lessons, item, _) = try source()
        let start = date("2026-11-08T00:00:00Z")
        let a = event(item, id: firstID, actor: actorA,
                      at: date("2026-11-09T10:00:00Z"), outcome: .understood)
        let b = event(item, id: firstID, actor: actorA,
                      at: date("2026-11-09T10:00:00Z"), outcome: .needsPractice)
        XCTAssertThrowsError(try NativeXPReconciliation.mergedCandidate(
            journal([a], start: start), journal([b], start: start),
            lessons: lessons))
    }

    func testForgedItemIDCannotGenerateSpeculativeXP() throws {
        let (lessons, item, _) = try source()
        let start = date("2026-11-08T00:00:00Z")
        let invalid = NativePracticeEvent(id: firstID, actorID: actorA,
            itemID: "unapproved-source:999", mode: .learn,
            at: date("2026-11-09T10:00:00Z"), outcome: .understood)
        XCTAssertThrowsError(try NativeXPReconciliation.candidate(
            journal: journal([invalid], start: start), lessons: lessons))
        XCTAssertNotEqual(invalid.itemID, item.id)
    }

    func testV2LocalParityWhenAllEventsAreClearlyWithinSameCalendarDays() throws {
        let (lessons, item, baseXP) = try source()
        let start = date("2026-11-08T00:00:00Z")
        let times = ["2026-11-09T12:00:00Z", "2026-11-10T12:00:00Z",
                     "2026-11-11T12:00:00Z"].map(date)
        let events = times.map {
            event(item, id: UUID(), actor: actorA, at: $0)
        }
        var local = LocalExpedition()
        let earned = times.compactMap {
            local.award(itemID: item.id, mode: .learn,
                        tier: lessons.first(where: {
                            $0.items.contains(where: { $0.id == item.id })
                        })?.difficultyTier ?? 1, at: $0)
        }
        XCTAssertEqual(earned.count, 3)
        let candidate = try NativeXPReconciliation.candidate(
            journal: journal(events, start: start), lessons: lessons)
        XCTAssertEqual(local.totalXP, candidate.totalEffortXP)
        XCTAssertEqual(candidate.totalEffortXP, 3 * baseXP)
        XCTAssertEqual(earned.map(\.expeditionXP),
                       candidate.awards.map(\.expeditionXP))
        // The candidate deliberately does NOT reconcile regionGoals,
        // selectedRegion or unlocks: v1 event metadata lacks region.
        XCTAssertTrue(candidate.requiresRegionReconciliation)
    }

    func testEmptyFreshJournalHasZeroXPWithoutInventedAchievements() throws {
        let (lessons, _, _) = try source()
        let candidate = try NativeXPReconciliation.candidate(
            journal: journal([], start: date("2026-11-08T00:00:00Z")),
            lessons: lessons)
        XCTAssertTrue(candidate.awards.isEmpty)
        XCTAssertEqual(candidate.totalEffortXP, 0)
        XCTAssertEqual(candidate.totalExpeditionXP, 0)
    }
}
