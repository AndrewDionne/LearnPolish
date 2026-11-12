import XCTest
@testable import PathToPolish

@MainActor final class NativeSoundTests: XCTestCase {
    func testCompleteRecordedAlphabetAndCombinationsFromOriginalWords() throws {
        let source = try CatalogLoader.load()
        let studio = try NativeSoundStudio.load(lessons: source)
        XCTAssertEqual(studio.letters.count, 32)
        XCTAssertEqual(studio.combinations.count, 13)
        XCTAssertEqual(studio.letters.first?.label, "A")
        XCTAssertEqual(studio.letters.last?.label, "Ż")
        XCTAssertEqual(studio.combinations.first?.label, "CZ")
        XCTAssertEqual(studio.combinations.last?.label, "DZ")
        XCTAssertEqual(studio.letters[0].polish, "Autobus")
        XCTAssertEqual(studio.letters[0].focus, "A")
        XCTAssertEqual(studio.editorialStatus,
                       "source_only_no_isolated_letter_audio_or_acoustic_certification")
    }

    func testAllSoundExamplesResolveToBundledOriginalMP3sAndSourceIDs() throws {
        let lessons = try CatalogLoader.load()
        let studio = try NativeSoundStudio.load(lessons: lessons)
        let map = Dictionary(uniqueKeysWithValues:
            lessons.flatMap(\.items).map { ($0.id, $0) })
        for record in studio.letters + studio.combinations {
            let original = try XCTUnwrap(map[record.id])
            XCTAssertEqual(record.polish, original.polish)
            XCTAssertEqual(record.english, original.english)
            XCTAssertEqual(record.audio, original.audio)
            XCTAssertNotNil(AudioFiles.referenceURL(for: record.audio))
            XCTAssertEqual(record.polish.components(separatedBy: record.focus).count, 2)
        }
    }

    func testFiveCuratedSoundContrastsContainTwentyFiveValidRecognitionCards() throws {
        let lessons = try CatalogLoader.load()
        let studio = try NativeSoundStudio.load(lessons: lessons)
        XCTAssertEqual(studio.soundLessons.count, 5)
        XCTAssertEqual(studio.soundLessons.flatMap(\.questions).count, 25)
        let map = Dictionary(uniqueKeysWithValues: lessons.map { ($0.id, $0) })
        for deck in studio.soundLessons {
            let lesson = try XCTUnwrap(map[deck.lessonId])
            XCTAssertEqual(lesson.kind, "sounds")
            XCTAssertGreaterThanOrEqual(deck.groups.count, 2)
            XCTAssertGreaterThanOrEqual(Set(deck.questions.compactMap(\.groupId)).count, 2)
            for card in deck.questions {
                let original = try XCTUnwrap(lesson.items.first { $0.id == card.id })
                XCTAssertEqual(card.focus, original.soundFocus)
                XCTAssertEqual(card.groupId, original.soundGroupId)
                XCTAssertEqual(card.audio, original.audio)
                XCTAssertNotNil(AudioFiles.referenceURL(for: card.audio))
                let group = try XCTUnwrap(deck.groups.first { $0.id == card.groupId })
                XCTAssertTrue(group.itemIds.contains(card.id))
            }
        }
    }

    func testBrowsingAndSoundEarQuizCannotAwardXPOrAdvanceCourse() throws {
        let directory = FileManager.default.temporaryDirectory
            .appendingPathComponent(UUID().uuidString)
        let location = directory.appendingPathComponent("learner.json")
        defer { try? FileManager.default.removeItem(at: directory) }
        let learner = LocalLearningStore(storageURL: location)
        XCTAssertNil(learner.catalogError)
        XCTAssertNotNil(learner.soundStudio)
        let firstCourse = try XCTUnwrap(learner.nextLesson?.id)
        let studio = try XCTUnwrap(learner.soundStudio)
        XCTAssertEqual(studio.soundLessons.count, 5)
        XCTAssertEqual(learner.expedition.totalXP, 0)
        XCTAssertTrue(learner.profile.records.isEmpty)
        XCTAssertEqual(learner.nextLesson?.id, firstCourse)
        let reopened = LocalLearningStore(storageURL: location)
        XCTAssertEqual(reopened.expedition.totalXP, 0)
        XCTAssertTrue(reopened.profile.records.isEmpty)
    }
}
