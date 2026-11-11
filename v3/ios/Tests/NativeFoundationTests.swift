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

    func testRealCourseSequenceMatchesV2WithoutInventingJourneyThree() throws {
        let lessons = try CatalogLoader.load()
        let journey = try CoreJourney(lessons: lessons)
        XCTAssertEqual(journey.ordered.count, 21)
        XCTAssertEqual(journey.explore.count, 5)
        XCTAssertEqual(journey.ordered.first?.id, "Conversation_1")
        XCTAssertEqual(journey.ordered[6].id, "numbers_1-20")
        XCTAssertEqual(journey.ordered.last?.id, "H_M_clothes_shop_trying_on_a_T-shirt")
        XCTAssertEqual(journey.next(after: "Conversation_1")?.id, "contrast_l_lstroked")
        XCTAssertNil(journey.next(after: journey.ordered.last!.id))
        XCTAssertFalse(journey.placements.values.contains(where: { $0.journey == 3 }))
    }

    func testExactNumbersBatchSectionsAndSourceItems() throws {
        let lessons = try CatalogLoader.load()
        let numbers = try XCTUnwrap(lessons.first { $0.id == "numbers_1-20" })
        let sections = NativePracticeRules.sections(for: numbers, mode: .learn)
        XCTAssertEqual(sections.map(\.title), ["Numbers 1–10", "Numbers 11–20"])
        XCTAssertEqual(sections.map { $0.items.count }, [10, 10])
        XCTAssertEqual(sections[0].items.first?.polish, "Jeden")
        XCTAssertEqual(sections[0].items.last?.polish, "Dziesięć")
        XCTAssertEqual(sections[1].items.first?.polish, "Jedenaście")
        XCTAssertEqual(sections[1].items.last?.polish, "Dwadzieścia")
        XCTAssertEqual(NativePracticeRules.firstUnvisitedBatch(for: numbers, progress: [:]), 0)
        var progress: [String: PracticeRecord] = [:]
        for item in numbers.items.prefix(10) { progress["learn:" + item.id] = PracticeRecord(attempts: 1) }
        XCTAssertEqual(NativePracticeRules.firstUnvisitedBatch(for: numbers, progress: progress), 1)
        XCTAssertEqual(NativePracticeRules.sections(for: numbers, mode: .listen).count, 2)
        let other = try XCTUnwrap(lessons.first { $0.id == "Conversation_1" })
        XCTAssertEqual(NativePracticeRules.sections(for: other, mode: .learn).count, 1)
    }

    func testRestrictedAudioNeverEntersListenAndNoInventedComprehension() throws {
        let lessons = try CatalogLoader.load()
        for lesson in lessons {
            let listen = NativePracticeRules.items(for: lesson, mode: .listen)
            XCTAssertTrue(listen.allSatisfy { $0.audio != nil && $0.referenceReview != "practice_only" })
            XCTAssertEqual(lesson.availableModes.contains(.listen), !listen.isEmpty)
            if lesson.kind == "reading" {
                XCTAssertFalse(lesson.availableModes.contains(.speak))
                XCTAssertFalse(lesson.availableModes.contains(.learn))
                for (index, item) in lesson.items.enumerated() where item.comprehension == nil {
                    XCTAssertTrue(NativePracticeRules.choices(for: lesson, item: item,
                                                              itemIndex: index, reading: true).isEmpty)
                }
                for (index, item) in lesson.items.enumerated() where item.comprehension != nil {
                    XCTAssertEqual(NativePracticeRules.choices(for: lesson, item: item,
                                                               itemIndex: index, reading: true),
                                   item.comprehension?.options)
                }
            } else {
                XCTAssertTrue(lesson.availableModes.contains(.learn))
                XCTAssertTrue(lesson.availableModes.contains(.speak))
            }
        }
    }

    func testLibraryBrowsingDoesNotRedirectCourseContinue() throws {
        let directory = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        let location = directory.appendingPathComponent("learner.json")
        defer { try? FileManager.default.removeItem(at: directory) }
        let learner = LocalLearningStore(storageURL: location)
        let first = try XCTUnwrap(learner.course.first)
        XCTAssertEqual(learner.nextLesson?.id, first.id)
        let item = try XCTUnwrap(first.items.first)
        learner.rememberPosition(lesson: first, item: item, mode: .learn)
        let explore = try XCTUnwrap(learner.explore.first)
        learner.rememberPosition(lesson: explore, item: explore.items[0], mode: .learn)
        XCTAssertEqual(learner.nextLesson?.id, first.id)
        let reloaded = LocalLearningStore(storageURL: location)
        XCTAssertEqual(reloaded.nextLesson?.id, first.id)
        XCTAssertEqual(reloaded.profile.lastLessonID, explore.id)
    }

    func testV2ReviewUsesElapsedDaysAndMissedCardsRemainDue() throws {
        let directory = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        let location = directory.appendingPathComponent("learner.json")
        defer { try? FileManager.default.removeItem(at: directory) }
        let learner = LocalLearningStore(storageURL: location)
        let lesson = try XCTUnwrap(learner.course.first(where: { $0.kind == "vocabulary" }))
        let item = try XCTUnwrap(lesson.items.first)
        let start = Date()
        learner.recordAttempt(item: item, mode: .learn, understood: true)
        let first = try XCTUnwrap(learner.record(for: item, mode: .learn).nextReview)
        XCTAssertEqual(first.timeIntervalSince(start), 86_400, accuracy: 2)
        learner.recordAttempt(item: item, mode: .learn, understood: false)
        XCTAssertEqual(learner.record(for: item, mode: .learn).reviewLevel, 0)
        XCTAssertTrue(learner.dueReviews.contains { $0.1.id == item.id })
    }

    func testOriginalSixteenPolandRegionsDrawAndRemainSelectable() throws {
        let regions = try PolandRegionCatalog.load()
        XCTAssertEqual(regions.count, 16)
        XCTAssertEqual(Set(regions.map(\.id)).count, 16)
        XCTAssertTrue(regions.contains { $0.id == "mazowieckie" })
        for region in regions {
            XCTAssertFalse(RegionOutline(definition: region.path)
                .path(in: CGRect(x: 0, y: 0, width: 585, height: 555)).isEmpty,
                "Empty original region polygon: \(region.id)")
        }
        var state = LocalExpedition()
        let available = Set(regions.map(\.id))
        state.choose("małopolskie", validRegions: available)
        XCTAssertEqual(state.selectedRegion, "małopolskie")
        state.choose("invalid-region", validRegions: available)
        XCTAssertEqual(state.selectedRegion, "małopolskie")
    }

    func testOriginalDailyXPAndRegionProgressTaperWithoutInventedImprovement() throws {
        var state = LocalExpedition()
        let dayOne = Date(timeIntervalSince1970: 1_750_000_000)
        XCTAssertEqual(state.selectedRegion, "mazowieckie")
        let first = try XCTUnwrap(state.award(itemID: "numbers_1-20:0", mode: .learn,
                                              tier: 1, at: dayOne))
        XCTAssertEqual(first.xp, 10)
        XCTAssertEqual(first.expeditionXP, 10)
        XCTAssertEqual(state.regionGoals["mazowieckie"], 300)
        XCTAssertNil(state.award(itemID: "numbers_1-20:0", mode: .learn,
                                 tier: 1, at: dayOne.addingTimeInterval(30)))
        let secondDay = try XCTUnwrap(Calendar.current.date(byAdding: .day, value: 1, to: dayOne))
        let second = try XCTUnwrap(state.award(itemID: "numbers_1-20:0", mode: .learn,
                                               tier: 1, at: secondDay))
        XCTAssertEqual(second.expeditionXP, 5)
        let thirdDay = try XCTUnwrap(Calendar.current.date(byAdding: .day, value: 2, to: dayOne))
        let third = try XCTUnwrap(state.award(itemID: "numbers_1-20:0", mode: .learn,
                                              tier: 1, at: thirdDay))
        XCTAssertEqual(third.expeditionXP, 0)
        XCTAssertEqual(state.totalXP, 30)
        XCTAssertEqual(state.regionTotal("mazowieckie"), 15)
        XCTAssertTrue(state.unlocked.isEmpty)
    }

    func testLocalExpeditionPersistsAndDoesNotRequireAccount() throws {
        let directory = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        let location = directory.appendingPathComponent("learner.json")
        defer { try? FileManager.default.removeItem(at: directory) }
        let first = LocalLearningStore(storageURL: location)
        XCTAssertNil(first.catalogError)
        let word = try XCTUnwrap(first.course.first(where: { $0.kind == "vocabulary" }))
        first.chooseRegion("małopolskie")
        first.recordAttempt(item: word.items[0], mode: .learn, understood: false)
        XCTAssertEqual(first.expedition.totalXP, 10)
        XCTAssertEqual(first.expedition.selectedRegion, "małopolskie")
        let reopened = LocalLearningStore(storageURL: location)
        XCTAssertNil(reopened.catalogError)
        XCTAssertEqual(reopened.expedition.selectedRegion, "małopolskie")
        XCTAssertEqual(reopened.expedition.totalXP, 10)
        XCTAssertEqual(reopened.expedition.regionTotal("małopolskie"), 10)
        XCTAssertNil(reopened.profile.lastCoreLessonID)
    }

    func testHomeHasOneGuidedPrimaryRouteAndSkipNeverSuggestsCore() throws {
        let folder = FileManager.default.temporaryDirectory
            .appendingPathComponent(UUID().uuidString)
        defer { try? FileManager.default.removeItem(at: folder) }
        let learner = LocalLearningStore(storageURL: folder.appendingPathComponent("profile.json"))
        guard case .guided(let first)? = learner.homeLearningRoute else {
            return XCTFail("First launch must recommend recorded first words")
        }
        XCTAssertEqual(first.id, "simple-replies")
        XCTAssertEqual(learner.expedition.totalXP, 0)
        for step in learner.guidedFoundations {
            XCTAssertTrue(learner.finishedGuidedStep(step.id))
        }
        guard case .guided(let revisit)? = learner.homeLearningRoute else {
            return XCTFail("A fully skipped guided path cannot redirect to the core course")
        }
        XCTAssertEqual(revisit.id, first.id)
        XCTAssertEqual(learner.profile.records.count, 0)
        let reopened = LocalLearningStore(storageURL: folder.appendingPathComponent("profile.json"))
        guard case .guided(let resumed)? = reopened.homeLearningRoute else {
            return XCTFail("Anonymous guided resume must survive device restart")
        }
        XCTAssertEqual(resumed.id, "simple-replies")
    }

    func testHomeUsesOriginalLearnRecordsToTransitionFromGuidedToCore() throws {
        let folder = FileManager.default.temporaryDirectory
            .appendingPathComponent(UUID().uuidString)
        defer { try? FileManager.default.removeItem(at: folder) }
        let learner = LocalLearningStore(storageURL: folder.appendingPathComponent("profile.json"))
        var uniqueReferences = Set<String>()
        for guided in learner.guidedFoundations {
            for reference in guided.items where uniqueReferences.insert(reference.id).inserted {
                let original = try XCTUnwrap(learner.sourceItem(for: reference))
                XCTAssertTrue(learner.recordAttempt(item: original, mode: .learn,
                                                    understood: false))
            }
        }
        XCTAssertEqual(uniqueReferences.count, 55)
        XCTAssertNil(learner.nextGuidedStep)
        guard case .core(let lesson)? = learner.homeLearningRoute else {
            return XCTFail("After source-backed practice, offer the existing V2 core course")
        }
        XCTAssertEqual(lesson.id, "Conversation_1")
        let reopened = LocalLearningStore(storageURL: folder.appendingPathComponent("profile.json"))
        guard case .core(let persistent)? = reopened.homeLearningRoute else {
            return XCTFail("Transition must persist without a login")
        }
        XCTAssertEqual(persistent.id, lesson.id)
        XCTAssertEqual(reopened.profile.records["learn:Conversation_1:14"]?.attempts, 1,
                       "The same recorded source is reused, not copied as a new lesson ID")
    }


    func testIndependentLessonCursorsPersistWithoutAwardingXP() throws {
        let folder = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        defer { try? FileManager.default.removeItem(at: folder) }
        let path = folder.appendingPathComponent("learner.json")
        let learner = LocalLearningStore(storageURL: path)
        let first = learner.course[0], second = learner.course[1]
        let firstItem = first.items[0], secondItem = second.items.last!
        let firstMode = first.availableModes[0], secondMode = second.availableModes[0]
        learner.rememberPosition(lesson: first, item: firstItem, mode: firstMode)
        learner.rememberPosition(lesson: second, item: secondItem, mode: secondMode)
        XCTAssertEqual(learner.practiceCursor(for: first.id)?.itemID, firstItem.id)
        XCTAssertEqual(learner.practiceCursor(for: second.id)?.itemID, secondItem.id)
        XCTAssertEqual(learner.attempts, 0)
        XCTAssertEqual(learner.expedition.totalXP, 0)
        let restored = LocalLearningStore(storageURL: path)
        XCTAssertEqual(restored.practiceCursor(for: first.id)?.itemID, firstItem.id)
        XCTAssertEqual(restored.practiceCursor(for: second.id)?.itemID, secondItem.id)
        XCTAssertEqual(Set(restored.activePracticeLessons.map(\.id)),
                       Set([first.id, second.id]))
        XCTAssertEqual(restored.attempts, 0)
    }

    func testIndependentGuidedCursorsKeepSequentialContinue() throws {
        let folder = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        defer { try? FileManager.default.removeItem(at: folder) }
        let path = folder.appendingPathComponent("learner.json")
        let learner = LocalLearningStore(storageURL: path)
        let first = learner.guidedFoundations[0], other = learner.guidedFoundations[4]
        learner.rememberGuidedPosition(stepID: first.id, itemID: first.items.last!.id)
        learner.rememberGuidedPosition(stepID: other.id, itemID: other.items.last!.id)
        XCTAssertEqual(learner.nextGuidedStep?.id, first.id)
        XCTAssertEqual(learner.guidedResumeItemID(for: other.id), other.items.last?.id)
        XCTAssertEqual(learner.activeGuidedSteps.count, 2)
        let restored = LocalLearningStore(storageURL: path)
        XCTAssertEqual(restored.nextGuidedStep?.id, first.id)
        XCTAssertEqual(restored.guidedResumeItemID(for: first.id), first.items.last?.id)
        XCTAssertEqual(restored.guidedResumeItemID(for: other.id), other.items.last?.id)
        XCTAssertEqual(restored.attempts, 0)
    }

    func testSmallJourneyGroupsPreserveSourceOrderAndOnlyMeasuredRecall() throws {
        let folder = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        defer { try? FileManager.default.removeItem(at: folder) }
        let learner = LocalLearningStore(storageURL: folder.appendingPathComponent("learner.json"))
        let groups = NativeJourneyCatalog.collections(
            course: learner.course, placements: learner.coreJourney?.placements ?? [:])
        XCTAssertFalse(groups.isEmpty)
        XCTAssertTrue(groups.allSatisfy { (1...4).contains($0.lessons.count) })
        XCTAssertEqual(groups.flatMap { $0.lessons.map(\.id) }, learner.course.map(\.id))
        let first = try XCTUnwrap(groups.first)
        let fresh = NativeJourneyCatalog.snapshot(first, records: [:])
        XCTAssertNil(fresh.recallPercentage)
        XCTAssertEqual(fresh.practisedLessons, 0)
        let sourceID = first.lessons[0].items[0].id
        var attempt = PracticeRecord()
        attempt.attempts = 3
        attempt.completed = 2
        let snapshot = NativeJourneyCatalog.snapshot(
            first, records: ["learn:" + sourceID: attempt])
        XCTAssertEqual(snapshot.startedLessons, 1)
        XCTAssertEqual(snapshot.recallAttempts, 3)
        XCTAssertEqual(snapshot.recallCorrect, 2)
        XCTAssertEqual(snapshot.recallPercentage, 67)
    }

    func testLibraryLaunchMovesToPracticeWithoutDiscardingOtherPositions() {
        let navigation = LearningNavigation()
        XCTAssertEqual(navigation.tab, .home)
        navigation.openPractice(.lesson("Conversation_1"))
        XCTAssertEqual(navigation.tab, .practice)
        XCTAssertEqual(navigation.practicePath, [.lesson("Conversation_1")])
        navigation.tab = .library
        navigation.openPractice(.guided("simple-replies"))
        XCTAssertEqual(navigation.tab, .practice)
        XCTAssertEqual(navigation.practicePath, [.guided("simple-replies")])
        navigation.showPractice()
        XCTAssertEqual(navigation.practicePath, [.guided("simple-replies")])
    }

}
