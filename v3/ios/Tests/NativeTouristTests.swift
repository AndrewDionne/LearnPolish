import XCTest
@testable import PathToPolish

@MainActor final class NativeTouristTests: XCTestCase {
    private func newStore() -> (LocalLearningStore, URL) {
        let folder = FileManager.default.temporaryDirectory
            .appendingPathComponent(UUID().uuidString)
        return (LocalLearningStore(storageURL: folder.appendingPathComponent("learner.json")), folder)
    }

    func testEightOriginalScenariosAndOrdered22PracticeStages() throws {
        let lessons = try CatalogLoader.load()
        let source = try TouristCatalog.load(lessons: lessons)
        XCTAssertEqual(source.units.map(\.id), ["T01","T02","T03","T04","T05","T06","T07","T08"])
        XCTAssertEqual(source.units.reduce(0) { $0 + $1.steps.count }, 22)
        XCTAssertEqual(source.units.filter { $0.steps.count == 2 }.count, 2)
        for (index, unit) in source.units.enumerated() {
            XCTAssertEqual(unit.order, index + 1)
            XCTAssertEqual(unit.steps[0].mode, .listen)
            XCTAssertEqual(unit.steps[1].mode, .speak)
            if unit.steps.count == 3 { XCTAssertEqual(unit.steps[2].mode, .read) }
        }
        XCTAssertEqual(source.units[2].title, "Numbers, prices and payment")
        XCTAssertNil(source.units[2].steps.first(where: { $0.mode == .read }))
        XCTAssertNotNil(source.units[2].gaps)
    }

    func testOriginalTouristItemsAndLocalAudioResolveWithoutInventedSpeech() throws {
        let lessons = try CatalogLoader.load()
        let source = try TouristCatalog.load(lessons: lessons)
        let originals = Dictionary(uniqueKeysWithValues: lessons.flatMap(\.items).map { ($0.id, $0) })
        for unit in source.units {
            for step in unit.steps {
                for item in step.items {
                    let original = try XCTUnwrap(originals[item.id])
                    XCTAssertEqual(item.polish, original.polish)
                    XCTAssertEqual(item.english, original.english)
                    XCTAssertEqual(item.audio, original.audio)
                    XCTAssertNil(original.referenceReview)
                    XCTAssertNotNil(AudioFiles.referenceURL(for: item.audio))
                }
            }
        }
    }

    func testTouristSkipDoesNotCompleteOrAwardXPAndDoesNotMoveMainJourney() throws {
        let (store, folder) = newStore()
        defer { try? FileManager.default.removeItem(at: folder) }
        XCTAssertNil(store.catalogError)
        XCTAssertEqual(store.touristUnits.count, 8)
        let first = try XCTUnwrap(store.touristUnits.first)
        let originalCourse = try XCTUnwrap(store.nextLesson?.id)
        let item = try XCTUnwrap(first.steps[0].items.first)
        XCTAssertFalse(store.touristStepComplete(unit: first, index: 0))
        store.rememberTouristPosition(unit: first, stepIndex: 0, itemID: item.id)
        XCTAssertFalse(store.finishTouristStep(unit: first, stepIndex: 0))
        XCTAssertEqual(store.touristStepAttemptCount(unit: first, index: 0), 0)
        XCTAssertEqual(store.expedition.totalXP, 0)
        XCTAssertEqual(store.profile.records.count, 0)
        XCTAssertEqual(store.nextLesson?.id, originalCourse)
        let reopened = LocalLearningStore(storageURL: folder.appendingPathComponent("learner.json"))
        XCTAssertEqual(reopened.touristProgress.unitID, first.id)
        XCTAssertFalse(reopened.touristStepComplete(unit: first, index: 0))
        XCTAssertEqual(reopened.nextLesson?.id, originalCourse)
    }

    func testOnlyActualAnswersCompleteScenarioStagesAndMoveCursor() throws {
        let (store, folder) = newStore()
        defer { try? FileManager.default.removeItem(at: folder) }
        let first = try XCTUnwrap(store.touristUnits.first)
        let firstItem = try XCTUnwrap(first.steps[0].items.first)
        store.recordTouristAttempt(unit: first, stepIndex: 0,
                                   itemID: firstItem.id, understood: true)
        XCTAssertFalse(store.finishTouristStep(unit: first, stepIndex: 0))
        XCTAssertEqual(store.touristStepAttemptCount(unit: first, index: 0), 1)
        XCTAssertEqual(store.expedition.totalXP, 10)
        for reference in first.steps[0].items.dropFirst() {
            store.recordTouristAttempt(unit: first, stepIndex: 0,
                                       itemID: reference.id, understood: false)
        }
        XCTAssertTrue(store.finishTouristStep(unit: first, stepIndex: 0))
        XCTAssertTrue(store.touristStepComplete(unit: first, index: 0))
        XCTAssertEqual(store.touristProgress.unitID, first.id)
        XCTAssertEqual(store.touristProgress.stepIndex, 1)
        let reopened = LocalLearningStore(storageURL: folder.appendingPathComponent("learner.json"))
        XCTAssertTrue(reopened.touristStepComplete(unit: first, index: 0))
        XCTAssertEqual(reopened.touristStepAttemptCount(unit: first, index: 0),
                       first.steps[0].items.count)
        XCTAssertEqual(reopened.touristProgress.stepIndex, 1)
    }

    func testReusedSourceItemsCannotMintDuplicateDailyXPOrMastery() throws {
        let (store, folder) = newStore()
        defer { try? FileManager.default.removeItem(at: folder) }
        let unit = try XCTUnwrap(store.touristUnits.first)
        let first = try XCTUnwrap(unit.steps[0].items.first)
        store.recordTouristAttempt(unit: unit, stepIndex: 0,
                                   itemID: first.id, understood: false)
        let before = store.expedition.totalXP
        store.recordTouristAttempt(unit: unit, stepIndex: 0,
                                   itemID: first.id, understood: true)
        XCTAssertEqual(store.expedition.totalXP, before)
        XCTAssertEqual(store.touristStepAttemptCount(unit: unit, index: 0), 1)
        let original = try XCTUnwrap(store.originalTouristItem(first.id, unit: unit, stepIndex: 0))
        XCTAssertEqual(store.record(for: original, mode: .listen).attempts, 2)
        XCTAssertEqual(store.record(for: original, mode: .speak).attempts, 0)
        XCTAssertEqual(store.nextLesson?.id, store.course.first?.id)
    }

    func testTouristIntroductionReusesSourceMeaningAndNeverChangesProgress() throws {
        let (store, folder) = newStore()
        defer { try? FileManager.default.removeItem(at: folder) }
        let unit = try XCTUnwrap(store.touristUnits.first)
        let subset = unit.steps[0].sourceIntroduction(from: store.sourceExposure)
        XCTAssertEqual(subset.mode, .listen)
        XCTAssertEqual(subset.items.map(\.id), unit.steps[0].items.map(\.id))
        XCTAssertEqual(subset.items.map(\.polish), unit.steps[0].items.map(\.polish))
        XCTAssertEqual(store.profile.records.count, 0)
        XCTAssertEqual(store.expedition.totalXP, 0)
    }

    func testBrowsingCompletedScenarioCannotHijackContinueCursor() throws {
        let (store, folder) = newStore()
        defer { try? FileManager.default.removeItem(at: folder) }
        let first = try XCTUnwrap(store.touristUnits.first)
        let second = try XCTUnwrap(store.touristUnits.dropFirst().first)
        for index in first.steps.indices {
            for item in first.steps[index].items {
                store.recordTouristAttempt(unit: first, stepIndex: index,
                                           itemID: item.id, understood: index == 1 ? nil : true)
            }
            XCTAssertTrue(store.finishTouristStep(unit: first, stepIndex: index))
        }
        XCTAssertEqual(store.nextTouristUnit?.id, second.id)
        store.rememberTouristPosition(unit: first, stepIndex: 0,
                                      itemID: first.steps[0].items[0].id)
        XCTAssertEqual(store.nextTouristUnit?.id, second.id)
        let reopened = LocalLearningStore(storageURL: folder.appendingPathComponent("learner.json"))
        XCTAssertEqual(reopened.nextTouristUnit?.id, second.id)
        XCTAssertEqual(reopened.touristProgress.completedSteps.count, first.steps.count)
    }
}
