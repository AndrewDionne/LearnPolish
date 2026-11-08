import Foundation
import Combine

struct PracticeRecord: Codable {
    var attempts: Int = 0
    var completed: Int = 0
    var reviewLevel: Int = 0
    var lastAttempt: Date?
    var nextReview: Date?
}

struct LocalLearner: Codable {
    // A device-local record identifier, never a login or API credential.
    var localID = UUID()
    var firstOpened = Date()
    // Independent guided pathway cursor: never rewrites source lesson IDs.
    var guidedStepID: String?
    var guidedItemID: String?
    var lastCoreLessonID: String?
    var lastLessonID: String?
    var lastItemID: String?
    var lastMode: PracticeMode?
    var records: [String: PracticeRecord] = [:]
    // Optional for backward-compatible loading of V3 profiles created before XP.
    var expedition: LocalExpedition?
    // Optional so earlier V3 local profiles continue decoding unchanged.
    var tourist: LocalTouristProgress?
}

@MainActor final class LocalLearningStore: ObservableObject {
    @Published private(set) var profile: LocalLearner
    @Published private(set) var lessons: [Lesson] = []
    @Published private(set) var guidedFoundations: [GuidedFoundationStep] = []
    @Published private(set) var soundStudio: NativeSoundStudio?
    @Published private(set) var sourceExposure: NativeSourceExposure?
    @Published private(set) var touristCatalog: TouristCatalog?
    @Published private(set) var coreJourney: CoreJourney?
    @Published private(set) var regions: [PolandRegion] = []
    @Published private(set) var catalogError: String?
    @Published private(set) var saveError: String?

    private let storageURL: URL
    private let canSave: Bool

    init(storageURL overrideURL: URL? = nil, bundle: Bundle = .main) {
        let directory = FileManager.default.urls(for: .applicationSupportDirectory,
                                                 in: .userDomainMask)[0]
        storageURL = overrideURL ?? directory.appendingPathComponent("PathToPolish/local-learner.json")
        let decoder = JSONDecoder()
        decoder.dateDecodingStrategy = .iso8601
        if FileManager.default.fileExists(atPath: storageURL.path) {
            do {
                profile = try decoder.decode(LocalLearner.self, from: Data(contentsOf: storageURL))
                canSave = true
            } catch {
                profile = LocalLearner()
                canSave = false
                saveError = "Saved progress could not be loaded. It has been left untouched; no new data will overwrite it."
            }
        } else {
            profile = LocalLearner()
            canSave = true
        }
        do {
            let source = try CatalogLoader.load(bundle: bundle)
            let journey = try CoreJourney(lessons: source, bundle: bundle)
            let sourceRegions = try PolandRegionCatalog.load(bundle: bundle)
            let guided = try GuidedFoundationPath.load(lessons: source, bundle: bundle)
            let sourceSounds = try NativeSoundStudio.load(lessons: source, bundle: bundle)
            let sourceIntroductions = try NativeSourceExposure.load(lessons: source, bundle: bundle)
            let tourists = try TouristCatalog.load(lessons: source, bundle: bundle)
            lessons = source
            coreJourney = journey
            regions = sourceRegions
            guidedFoundations = guided
            soundStudio = sourceSounds
            sourceExposure = sourceIntroductions
            touristCatalog = tourists
        } catch {
            catalogError = error.localizedDescription
        }
    }

    // Tourist scenarios are metadata through the existing source cards, not
    // a new XP ledger. Unit progress is stored separately from Core Continue.
    var touristProgress: LocalTouristProgress { profile.tourist ?? LocalTouristProgress() }
    var touristUnits: [TouristUnit] { touristCatalog?.units ?? [] }

    var nextTouristUnit: TouristUnit? {
        if let id = touristProgress.unitID,
           let unit = touristUnits.first(where: { $0.id == id }) { return unit }
        return touristUnits.first { unit in
            unit.steps.indices.contains(where: {
                !touristProgress.isComplete(unitID: unit.id, stepIndex: $0)
            })
        }
    }

    func touristStepAttemptCount(unit: TouristUnit, index: Int) -> Int {
        touristProgress.attemptedCount(unitID: unit.id, stepIndex: index)
    }

    func touristStepComplete(unit: TouristUnit, index: Int) -> Bool {
        touristProgress.isComplete(unitID: unit.id, stepIndex: index)
    }

    func originalTouristItem(_ id: String, unit: TouristUnit, stepIndex: Int) -> LessonItem? {
        guard unit.steps.indices.contains(stepIndex),
              let reference = unit.steps[stepIndex].items.first(where: { $0.id == id }),
              let original = lessons.first(where: { $0.id == unit.steps[stepIndex].lessonId })?
                .items.first(where: { $0.id == id }),
              original.polish == reference.polish, original.english == reference.english,
              original.audio == reference.audio, original.referenceReview != "practice_only" else {
            return nil
        }
        return original
    }

    func rememberTouristPosition(unit: TouristUnit, stepIndex: Int, itemID: String) {
        guard touristUnits.contains(where: { $0.id == unit.id }),
              unit.steps.indices.contains(stepIndex),
              unit.steps[stepIndex].items.contains(where: { $0.id == itemID }) else { return }
        var progress = touristProgress
        guard progress.unitID != unit.id || progress.stepIndex != stepIndex ||
              progress.itemID != itemID else { return }
        progress.unitID = unit.id
        progress.stepIndex = stepIndex
        progress.itemID = itemID
        profile.tourist = progress
        save()
    }

    // Only actual self-rated / answered / successfully recorded attempts count.
    // Navigation, playback, previews and skipping do not earn duplicate XP.
    func recordTouristAttempt(unit: TouristUnit, stepIndex: Int,
                              itemID: String, understood: Bool?) {
        guard let confirmed = touristUnits.first(where: { $0.id == unit.id }),
              confirmed.steps.indices.contains(stepIndex),
              let item = originalTouristItem(itemID, unit: confirmed, stepIndex: stepIndex) else {
            return
        }
        let mode = confirmed.steps[stepIndex].mode
        recordAttempt(item: item, mode: mode, understood: understood)
        var progress = touristProgress
        let key = LocalTouristProgress.key(unitID: unit.id, stepIndex: stepIndex)
        progress.attemptedByStep[key, default: []].insert(itemID)
        progress.unitID = unit.id
        progress.stepIndex = stepIndex
        progress.itemID = itemID
        profile.tourist = progress
        save()
    }

    // A skipped or partly answered step is NOT silently certified complete.
    @discardableResult
    func finishTouristStep(unit: TouristUnit, stepIndex: Int) -> Bool {
        guard let confirmed = touristUnits.first(where: { $0.id == unit.id }),
              confirmed.steps.indices.contains(stepIndex) else { return false }
        var progress = touristProgress
        let step = confirmed.steps[stepIndex]
        let key = LocalTouristProgress.key(unitID: unit.id, stepIndex: stepIndex)
        let attempted = progress.attemptedByStep[key] ?? []
        let complete = step.items.allSatisfy { attempted.contains($0.id) }
        if complete {
            progress.completedSteps.insert(key)
            if confirmed.steps.indices.contains(stepIndex + 1) {
                progress.unitID = unit.id
                progress.stepIndex = stepIndex + 1
                progress.itemID = nil
            } else if let next = touristUnits.first(where: { $0.order == unit.order + 1 }) {
                progress.unitID = next.id
                progress.stepIndex = 0
                progress.itemID = nil
            } else {
                progress.unitID = nil
                progress.stepIndex = 0
                progress.itemID = nil
            }
        } else {
            progress.unitID = unit.id
            progress.stepIndex = stepIndex
            progress.itemID = step.items.first(where: { !attempted.contains($0.id) })?.id
        }
        profile.tourist = progress
        save()
        return complete
    }

    var course: [Lesson] { coreJourney?.ordered ?? [] }
    var explore: [Lesson] { coreJourney?.explore ?? [] }

    var nextGuidedStep: GuidedFoundationStep? {
        if let id = profile.guidedStepID,
           let step = guidedFoundations.first(where: { $0.id == id }) {
            return step
        }
        return guidedFoundations.first(where: { step in
            step.items.contains { item in
                (profile.records["learn:" + item.id]?.attempts ?? 0) == 0
            }
        })
    }

    func guidedPractisedCount(_ step: GuidedFoundationStep) -> Int {
        step.items.filter { (profile.records["learn:" + $0.id]?.attempts ?? 0) > 0 }.count
    }

    func sourceItem(for reference: GuidedRecordedItem) -> LessonItem? {
        lessons.lazy.flatMap(\.items).first { $0.id == reference.id }
    }

    func rememberGuidedPosition(stepID: String, itemID: String) {
        guard let step = guidedFoundations.first(where: { $0.id == stepID }),
              step.items.contains(where: { $0.id == itemID }) else { return }
        guard profile.guidedStepID != stepID || profile.guidedItemID != itemID else { return }
        profile.guidedStepID = stepID
        profile.guidedItemID = itemID
        save()
    }

    func finishedGuidedStep(_ stepID: String) {
        guard let index = guidedFoundations.firstIndex(where: { $0.id == stepID }) else { return }
        profile.guidedStepID = guidedFoundations.indices.contains(index + 1)
            ? guidedFoundations[index + 1].id : nil
        profile.guidedItemID = nil
        save()
    }
    var nextLesson: Lesson? {
        if let id = profile.lastCoreLessonID,
           let lesson = course.first(where: { $0.id == id }) { return lesson }
        if let id = profile.lastLessonID,
           let lesson = course.first(where: { $0.id == id }) { return lesson }
        return course.first
    }

    var completedItems: Int {
        Set(profile.records.filter { $0.value.completed > 0 }
            .compactMap { key, _ in key.split(separator: ":", maxSplits: 1).last.map(String.init) }).count
    }

    var attempts: Int { profile.records.values.reduce(0) { $0 + $1.attempts } }

    var expedition: LocalExpedition { profile.expedition ?? LocalExpedition() }

    func chooseRegion(_ id: String) {
        guard regions.contains(where: { $0.id == id }) else { return }
        var map = expedition
        map.choose(id, validRegions: Set(regions.map(\.id)))
        profile.expedition = map
        save()
    }

    var dueReviews: [(Lesson, LessonItem)] {
        let now = Date()
        return lessons.filter { $0.kind != "reading" }.flatMap { lesson in
            lesson.items.compactMap { item -> (Lesson, LessonItem)? in
                guard let record = profile.records["learn:" + item.id],
                      let due = record.nextReview, due <= now else { return nil }
                return (lesson, item)
            }
        }
    }

    func record(for item: LessonItem, mode: PracticeMode) -> PracticeRecord {
        profile.records[mode.rawValue + ":" + item.id] ?? PracticeRecord()
    }

    func rememberPosition(lesson: Lesson, item: LessonItem, mode: PracticeMode) {
        guard profile.lastLessonID != lesson.id ||
              profile.lastItemID != item.id ||
              profile.lastMode != mode else { return }
        profile.lastLessonID = lesson.id
        if coreJourney?.placements[lesson.id] != nil {
            profile.lastCoreLessonID = lesson.id
        }
        profile.lastItemID = item.id
        profile.lastMode = mode
        save()
    }

    /// nil = ungraded Speak attempt; never claims pronunciation success.
    func recordAttempt(item: LessonItem, mode: PracticeMode, understood: Bool?) {
        let key = mode.rawValue + ":" + item.id
        var record = profile.records[key] ?? PracticeRecord()
        record.attempts += 1
        record.lastAttempt = Date()
        if understood == true { record.completed += 1 }
        if mode == .learn, let understood {
            if understood {
                record.reviewLevel = min(record.reviewLevel + 1, 7)
                let days = [1, 3, 7, 14, 30, 60, 90][record.reviewLevel - 1]
                // V2 review.ts uses elapsed 24-hour days, not calendar-day DST shifts.
                record.nextReview = Date().addingTimeInterval(TimeInterval(days) * 86_400)
            } else {
                record.reviewLevel = 0
                record.nextReview = Date()
            }
        }
        profile.records[key] = record
        // Each actual answered/rated card or finished usable Speak take earns
        // base effort XP once per mode/item/local-day, never on reveal/skip.
        if let owner = lessons.first(where: { lesson in
            lesson.items.contains(where: { $0.id == item.id })
        }) {
            var map = expedition
            _ = map.award(itemID: item.id, mode: mode,
                          tier: owner.difficultyTier.flatMap { (1...5).contains($0) ? $0 : nil } ?? 1)
            profile.expedition = map
        }
        save()
    }

    private func save() {
        guard canSave else { return }
        do {
            let folder = storageURL.deletingLastPathComponent()
            try FileManager.default.createDirectory(at: folder,
                                                    withIntermediateDirectories: true)
            let encoder = JSONEncoder()
            encoder.dateEncodingStrategy = .iso8601
            let bytes = try encoder.encode(profile)
            try bytes.write(to: storageURL, options: [.atomic, .completeFileProtectionUnlessOpen])
            saveError = nil
        } catch {
            saveError = "Progress could not be saved on this device. Check available storage."
        }
    }
}
