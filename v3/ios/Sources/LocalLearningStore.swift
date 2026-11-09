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
    // The anonymous learner follows a deliberately restored profile. This
    // separate actor stays specific to the receiving device and must never
    // be copied from another phone's archive.
    var deviceActorID: UUID?
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
    // Optional keeps prior local V3 files byte-compatible. A journal opened
    // after existing attempts explicitly flags historical aggregates as legacy.
    var practiceJournal: NativePracticeJournal?
}

struct LocalRestorePreview: Identifiable {
    let id = UUID()
    let archive: LocalProgressArchive
    let expectedLocalProfile: Data
    let source: String
    var importedAttempts: Int {
        archive.profile.records.values.reduce(0) { $0 + $1.attempts }
    }
    var importedXP: Int { archive.profile.expedition?.totalXP ?? 0 }
}

struct LocalProgressBackup: Identifiable {
    let url: URL
    let savedAt: Date
    var id: URL { url }
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
            // Source-drifted or malformed journals must not be saved over,
            // including unknown newer event region IDs. Old nil-region
            // snapshots are compatible but not cloud-map eligible.
            try profile.practiceJournal?.validateSource(
                lessons: source, regions: sourceRegions)
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
        // Browsing completed lessons must not replace the next unfinished
        // scenario shown on Home.
        if let id = touristProgress.unitID,
           let unit = touristUnits.first(where: { $0.id == id }),
           unit.steps.indices.contains(where: {
               !touristProgress.isComplete(unitID: id, stepIndex: $0)
           }) { return unit }
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
        guard recordAttempt(item: item, mode: mode, understood: understood) else { return }
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
    /// Each actual card attempt has one immutable UUID in the local journal.
    /// The existing aggregate review and daily XP logic remains authoritative
    /// for this device until safe cross-device reconciliation is certified.
    @discardableResult
    func recordAttempt(item: LessonItem, mode: PracticeMode, understood: Bool?) -> Bool {
        guard canSave, let owner = lessons.first(where: { lesson in
            lesson.items.contains(where: { $0.id == item.id })
        }), owner.availableModes.contains(mode),
        mode != .listen || (item.audio != nil && item.referenceReview != "practice_only"),
        regions.contains(where: { $0.id == expedition.selectedRegion }) else {
            return false
        }
        let now = Date()
        var next = profile
        var journal = next.practiceJournal ?? NativePracticeJournal(
            startedAt: now,
            // Older XP-only data is also history, even if record counters are
            // absent. It cannot be silently attributed to new journal events.
            hasLegacyHistory: !next.records.isEmpty ||
                !(next.expedition?.events.isEmpty ?? true))
        let outcome: NativePracticeEvent.Outcome = mode == .speak ? .recorded :
            (understood == true ? .understood : .needsPractice)
        let entry = NativePracticeEvent(id: UUID(),
            actorID: next.deviceActorID ?? next.localID,
            itemID: item.id, mode: mode, at: now, outcome: outcome,
            regionID: (next.expedition ?? LocalExpedition()).selectedRegion)
        do {
            try journal.append(entry)
        } catch {
            saveError = "Practice journal is full or unavailable. No new attempt was recorded."
            return false
        }

        let key = mode.rawValue + ":" + item.id
        var record = next.records[key] ?? PracticeRecord()
        record.attempts += 1
        record.lastAttempt = now
        if understood == true { record.completed += 1 }
        if mode == .learn, let understood {
            if understood {
                record.reviewLevel = min(record.reviewLevel + 1, 7)
                let days = [1, 3, 7, 14, 30, 60, 90][record.reviewLevel - 1]
                // V2 review.ts uses elapsed 24-hour days, not calendar-day DST shifts.
                record.nextReview = now.addingTimeInterval(TimeInterval(days) * 86_400)
            } else {
                record.reviewLevel = 0
                record.nextReview = now
            }
        }
        next.records[key] = record
        next.practiceJournal = journal
        // The same atomic profile snapshot includes XP, review and the event.
        // Local daily dedup remains unchanged; family XP remains independent.
        var map = next.expedition ?? LocalExpedition()
        _ = map.award(itemID: item.id, mode: mode,
                      tier: owner.difficultyTier.flatMap { (1...5).contains($0) ? $0 : nil } ?? 1,
                      at: now)
        next.expedition = map
        do {
            try persist(next)
            profile = next
            saveError = nil
            return true
        } catch {
            saveError = "Progress could not be saved. No new attempt or XP was recorded."
            return false
        }
    }

    private var localBackupDirectory: URL {
        storageURL.deletingLastPathComponent()
            .appendingPathComponent("RestoreBackups", isDirectory: true)
    }

    private func encodedProfile(_ candidate: LocalLearner) throws -> Data {
        let encoder = JSONEncoder()
        encoder.dateEncodingStrategy = .iso8601
        encoder.outputFormatting = [.sortedKeys]
        return try encoder.encode(candidate)
    }

    /// UI-controlled file access. A maliciously large document is rejected
    /// *before* decoding or opening a confirmation dialog.
    private func readBoundedData(from file: URL) throws -> Data {
        let handle = try FileHandle(forReadingFrom: file)
        defer { try? handle.close() }
        var data = Data()
        while data.count <= 16_000_000 {
            let available = min(65_536, 16_000_001 - data.count)
            let chunk = try handle.read(upToCount: available) ?? Data()
            if chunk.isEmpty { break }
            data.append(chunk)
        }
        guard data.count <= 16_000_000 else {
            throw LocalProgressArchiveError.invalid
        }
        return data
    }

    private func verifyRestoreArchive(_ archive: LocalProgressArchive) throws {
        guard canSave, catalogError == nil, saveError == nil else {
            throw LocalProgressArchiveError.unavailable
        }
        try LocalRestoreValidation.validate(archive,
            lessons: lessons, regions: regions,
            guided: guidedFoundations, touristUnits: touristUnits,
            core: coreJourney)
    }

    private func preview(_ archive: LocalProgressArchive,
                         source: String) throws -> LocalRestorePreview {
        try verifyRestoreArchive(archive)
        return LocalRestorePreview(archive: archive,
                                   expectedLocalProfile: try encodedProfile(profile),
                                   source: source)
    }

    func previewImportedProgress(from file: URL) throws -> LocalRestorePreview {
        let accessed = file.startAccessingSecurityScopedResource()
        defer { if accessed { file.stopAccessingSecurityScopedResource() } }
        let archive = try LocalProgressArchive.decode(readBoundedData(from: file))
        return try preview(archive, source: "Selected progress file")
    }

    /// RestoreBackups are private internal JSON archives, not CloudKit
    /// records. No automatic restore or deletion ever occurs.
    var localRestoreBackups: [LocalProgressBackup] {
        let manager = FileManager.default
        guard let urls = try? manager.contentsOfDirectory(
            at: localBackupDirectory,
            includingPropertiesForKeys: [.isRegularFileKey, .isSymbolicLinkKey,
                                         .creationDateKey],
            options: [.skipsHiddenFiles]) else { return [] }
        return urls.compactMap { file -> LocalProgressBackup? in
            guard file.lastPathComponent.hasPrefix("local-backup-"),
                  file.pathExtension == "json",
                  let values = try? file.resourceValues(forKeys:
                      [.isRegularFileKey, .isSymbolicLinkKey, .creationDateKey]),
                  values.isRegularFile == true, values.isSymbolicLink != true else { return nil }
            return LocalProgressBackup(url: file, savedAt: values.creationDate ?? .distantPast)
        }
        .sorted { $0.savedAt > $1.savedAt }
        .prefix(20)
        .map { $0 }
    }

    /// Explicitly deletes app-owned restore backups ONLY. The current local
    /// learner and user-exported files outside the app remain untouched.
    /// The delete action is separate from resetting active learning progress.
    @discardableResult
    func deleteLocalRestoreBackups() throws -> Int {
        let dir = localBackupDirectory
        let manager = FileManager.default
        guard manager.fileExists(atPath: dir.path) else { return 0 }
        let candidates = try manager.contentsOfDirectory(
            at: dir, includingPropertiesForKeys: [.isRegularFileKey, .isSymbolicLinkKey],
            options: [.skipsHiddenFiles])
        var deleted = 0
        for file in candidates {
            guard file.deletingLastPathComponent().standardizedFileURL ==
                      dir.standardizedFileURL,
                  file.lastPathComponent.hasPrefix("local-backup-"),
                  file.pathExtension == "json",
                  let values = try? file.resourceValues(forKeys:
                      [.isRegularFileKey, .isSymbolicLinkKey]),
                  values.isRegularFile == true, values.isSymbolicLink != true else { continue }
            try manager.removeItem(at: file)
            deleted += 1
        }
        return deleted
    }

    func previewLocalBackup(_ backup: LocalProgressBackup) throws -> LocalRestorePreview {
        // File-system scope is restricted to the private app-owned directory;
        // a symbolic link to an arbitrary user document is never accepted.
        guard backup.url.deletingLastPathComponent().standardizedFileURL ==
                  localBackupDirectory.standardizedFileURL,
              localRestoreBackups.contains(where: { $0.url == backup.url }) else {
            throw LocalProgressArchiveError.invalid
        }
        let archive = try LocalProgressArchive.decode(readBoundedData(from: backup.url))
        return try preview(archive, source: "Earlier local backup")
    }

    /// User-confirmed FULL REPLACEMENT only. This deliberately cannot merge
    /// XP, account identity, tourist state or a CloudKit sync epoch.
    /// A recoverable verified backup is written BEFORE any replacement.
    @discardableResult
    func restoreLocalProgress(_ candidate: LocalRestorePreview) throws -> URL {
        try verifyRestoreArchive(candidate.archive)
        guard try encodedProfile(profile) == candidate.expectedLocalProfile else {
            throw LocalProgressArchiveError.changedSincePreview
        }
        if FileManager.default.fileExists(atPath: storageURL.path) {
            let diskBytes = try readBoundedData(from: storageURL)
            let decoder = JSONDecoder()
            decoder.dateDecodingStrategy = .iso8601
            guard let diskProfile = try? decoder.decode(LocalLearner.self, from: diskBytes),
                  try encodedProfile(diskProfile) == candidate.expectedLocalProfile else {
                throw LocalProgressArchiveError.changedSincePreview
            }
        }
        // Refuse to replace an invalid existing profile with a seemingly good
        // incoming file. An archive must always be exportable for recovery.
        let current = LocalProgressArchive(profile: profile,
            sourceLessonIDs: lessons.map(\.id))
        try LocalRestoreValidation.validate(current, lessons: lessons, regions: regions,
            guided: guidedFoundations, touristUnits: touristUnits, core: coreJourney)
        let priorBytes = try current.encoded()
        let backupURL = localBackupDirectory.appendingPathComponent(
            "local-backup-" + UUID().uuidString + ".json")
        do {
            try FileManager.default.createDirectory(at: localBackupDirectory,
                                                    withIntermediateDirectories: true)
            try priorBytes.write(to: backupURL,
                                 options: [.atomic, .completeFileProtectionUnlessOpen])
            guard try readBoundedData(from: backupURL) == priorBytes else {
                throw LocalProgressArchiveError.backupFailed
            }
        } catch {
            throw LocalProgressArchiveError.backupFailed
        }
        // The imported learner identity and journal epoch are owner-chosen,
        // but never import the source phone's actor identity. The receiving
        // device keeps its own actor across all future attempts.
        var restored = candidate.archive.profile
        restored.deviceActorID = profile.deviceActorID ?? profile.localID
        do {
            try persist(restored)
        } catch {
            // The backup remains available even if an atomic replacement fails.
            throw LocalProgressArchiveError.restoreFailed
        }
        profile = restored
        saveError = nil
        return backupURL
    }

    /// A file export is a user-controlled plaintext copy of *local* learning
    /// only, not a CloudKit upload. An unreadable saved file is never silently
    /// replaced by a new anonymous profile.
    func makeLocalExport() throws -> LocalProgressArchiveDocument {
        guard canSave, catalogError == nil, saveError == nil else {
            throw LocalProgressArchiveError.unavailable
        }
        try profile.practiceJournal?.validateSource(
            lessons: lessons, regions: regions)
        let snapshot = LocalProgressArchive(profile: profile,
            sourceLessonIDs: lessons.map(\.id))
        return try LocalProgressArchiveDocument(archive: snapshot)
    }

    /// Explicit local-only reset. A new, empty profile is published ONLY
    /// after atomic replacement of the existing JSON has succeeded.
    /// A corrupt existing file is never overwritten by this operation.
    /// It does not delete any server-held family data or a user-exported copy.
    @discardableResult
    func resetLocalProgress() -> Bool {
        guard canSave else {
            saveError = "Saved progress needs recovery and has not been erased."
            return false
        }
        let fresh = LocalLearner()
        do {
            try persist(fresh)
            profile = fresh
            saveError = nil
            return true
        } catch {
            saveError = "Local progress could not be erased. The original saved file was left untouched."
            return false
        }
    }

    private func persist(_ value: LocalLearner) throws {
        let folder = storageURL.deletingLastPathComponent()
        try FileManager.default.createDirectory(at: folder,
                                                withIntermediateDirectories: true)
        let encoder = JSONEncoder()
        encoder.dateEncodingStrategy = .iso8601
        let bytes = try encoder.encode(value)
        try bytes.write(to: storageURL, options: [.atomic, .completeFileProtectionUnlessOpen])
    }

    private func save() {
        guard canSave else { return }
        do {
            try persist(profile)
            saveError = nil
        } catch {
            saveError = "Progress could not be saved on this device. Check available storage."
        }
    }
}
