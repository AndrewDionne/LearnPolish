import XCTest
@testable import PathToPolish

@MainActor final class NativeNavigationAndHomeTests: XCTestCase {
    private func learner() -> (LocalLearningStore, URL) {
        let folder = FileManager.default.temporaryDirectory
            .appendingPathComponent(UUID().uuidString)
        return (LocalLearningStore(
            storageURL: folder.appendingPathComponent("learner.json")), folder)
    }

    func testLibraryLaunchChangesToPracticeWithoutDeletingPausedPath() {
        let nav = LearningNavigation()
        XCTAssertEqual(nav.tab, .home)
        XCTAssertTrue(nav.practicePath.isEmpty)
        nav.tab = .library
        nav.openPractice(.guided("simple-replies"))
        XCTAssertEqual(nav.tab, .practice)
        XCTAssertEqual(nav.practicePath, [.guided("simple-replies")])
        nav.tab = .expedition
        nav.showPractice()
        XCTAssertEqual(nav.tab, .practice)
        XCTAssertEqual(nav.practicePath, [.guided("simple-replies")])
        nav.tab = .library
        nav.openPractice(.lesson("Conversation_1"))
        XCTAssertEqual(nav.tab, .practice)
        XCTAssertEqual(nav.practicePath, [.lesson("Conversation_1")])
        nav.openPractice(.lesson("Conversation_1"))
        XCTAssertEqual(nav.practicePath, [.lesson("Conversation_1")])
    }

    func testHomeShowsOnlyPersistedOriginalLearningEvents() throws {
        let (store, folder) = learner()
        defer { try? FileManager.default.removeItem(at: folder) }
        XCTAssertTrue(NativeHomeSnapshot.recent(learner: store).isEmpty)
        XCTAssertNil(NativeHomeSnapshot.todayAttempts(learner: store))
        XCTAssertEqual(NativeHomeSnapshot.todayXP(learner: store), 0)
        let item = try XCTUnwrap(store.lessons.first {
            $0.id == "Conversation_1"
        }?.items.first)
        store.rememberPosition(lesson: try XCTUnwrap(store.lessons.first {
            $0.id == "Conversation_1"
        }), item: item, mode: .speak)
        XCTAssertTrue(NativeHomeSnapshot.recent(learner: store).isEmpty,
                      "Merely navigating to a card must not appear as a real activity")
        XCTAssertTrue(store.recordAttempt(item: item, mode: .speak, understood: nil))
        let events = NativeHomeSnapshot.recent(learner: store)
        XCTAssertEqual(events.count, 1)
        XCTAssertEqual(events[0].polish, item.polish)
        XCTAssertEqual(events[0].mode, .speak)
        XCTAssertEqual(NativeHomeSnapshot.todayAttempts(learner: store), 1)
        XCTAssertGreaterThan(NativeHomeSnapshot.todayXP(learner: store), 0)
        let reread = LocalLearningStore(
            storageURL: folder.appendingPathComponent("learner.json"))
        XCTAssertEqual(NativeHomeSnapshot.recent(learner: reread).count, 1)
        XCTAssertEqual(NativeHomeSnapshot.todayAttempts(learner: reread), 1)
    }

    func testHomeDoesNotInventTeamScoresAndNeverMislabelsSavedXP() throws {
        let (store, folder) = learner()
        defer { try? FileManager.default.removeItem(at: folder) }
        XCTAssertEqual(store.expedition.totalXP, 0)
        XCTAssertTrue(NativeHomeSnapshot.recent(learner: store).isEmpty)
        XCTAssertEqual(store.unifiedJourneyStepsCompleted, 0)
    }
}
