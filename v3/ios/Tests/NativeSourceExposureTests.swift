import XCTest
@testable import PathToPolish

@MainActor final class NativeSourceExposureTests: XCTestCase {
    func testOriginalSixReadingDialoguesAndSevenBasicListeningIntroductions() throws {
        let lessons = try CatalogLoader.load()
        let exposure = try NativeSourceExposure.load(lessons: lessons)
        XCTAssertEqual(exposure.reading.count, 6)
        XCTAssertEqual(exposure.listening.count, 7)
        XCTAssertEqual(exposure.reading.reduce(0) { $0 + $1.items.count }, 51)
        XCTAssertTrue(exposure.reading.allSatisfy { $0.mode == .read })
        XCTAssertTrue(exposure.listening.allSatisfy { $0.mode == .listen })
        XCTAssertEqual(exposure.reading.first?.lessonId, "Basic_01R")
        XCTAssertTrue(exposure.reading.first?.items.first?.teachingCue?.count ?? 0 > 40)
    }

    func testPreparationsKeepExactOriginalWholeTurnTextAndBundledAudio() throws {
        let lessons = try CatalogLoader.load()
        let exposure = try NativeSourceExposure.load(lessons: lessons)
        let map = Dictionary(uniqueKeysWithValues: lessons.flatMap(\.items).map { ($0.id, $0) })
        for entry in exposure.reading + exposure.listening {
            for turn in entry.items {
                let source = try XCTUnwrap(map[turn.id])
                XCTAssertEqual(turn.polish, source.polish)
                XCTAssertEqual(turn.english, source.english)
                XCTAssertEqual(turn.audio, source.audio)
                XCTAssertNotNil(AudioFiles.referenceURL(for: turn.audio))
                XCTAssertNil(source.referenceReview)
            }
        }
    }

    func testSourceFirstPrecedesReadOrListenButNotLearnSpeakOrReview() throws {
        let lessons = try CatalogLoader.load()
        let exposure = try NativeSourceExposure.load(lessons: lessons)
        for lesson in lessons where lesson.kind == "reading" {
            XCTAssertNotNil(exposure.preparation(for: lesson, mode: .read))
            XCTAssertNotNil(exposure.preparation(for: lesson, mode: .listen))
            XCTAssertNil(exposure.preparation(for: lesson, mode: .learn))
            XCTAssertNil(exposure.preparation(for: lesson, mode: .speak))
        }
        let words = try XCTUnwrap(lessons.first { $0.id == "Conversation_1" })
        XCTAssertNotNil(exposure.preparation(for: words, mode: .listen))
        XCTAssertNil(exposure.preparation(for: words, mode: .learn))
    }

    func testExposureOnlyDoesNotAwardXPOrWriteProgress() throws {
        let dir = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        defer { try? FileManager.default.removeItem(at: dir) }
        let store = LocalLearningStore(storageURL: dir.appendingPathComponent("learner.json"))
        XCTAssertNil(store.catalogError)
        let reading = try XCTUnwrap(store.lessons.first { $0.id == "Basic_01R" })
        XCTAssertNotNil(store.sourceExposure?.preparation(for: reading, mode: .read))
        XCTAssertEqual(store.expedition.totalXP, 0)
        XCTAssertTrue(store.profile.records.isEmpty)
        let reopened = LocalLearningStore(storageURL: dir.appendingPathComponent("learner.json"))
        XCTAssertEqual(reopened.expedition.totalXP, 0)
        XCTAssertTrue(reopened.profile.records.isEmpty)
    }
}
